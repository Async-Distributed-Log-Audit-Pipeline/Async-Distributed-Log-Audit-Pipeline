import gzip
import json
import os
import tempfile
import pytest

from errors import InvalidLogFileError
from parser.analytics import analyze_file
from parser.log_parser import normalize_message, parse_timestamp


def create_temp_log_file(lines: list[str], is_gzip: bool = False) -> str:
    """Helper utility to create temporary test log files."""
    suffix = ".jsonl.gz" if is_gzip else ".jsonl"
    with tempfile.NamedTemporaryFile(mode="wb", suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name

    content = "\n".join(lines).encode("utf-8")
    if is_gzip:
        with gzip.open(tmp_path, "wb") as f:
            f.write(content)
    else:
        with open(tmp_path, "wb") as f:
            f.write(content)

    return tmp_path


def test_level_bucketing(tmp_path):
    lines = [
        json.dumps({"level": "FATAL", "message": "Fatal error"}),
        json.dumps({"level": "CRITICAL", "message": "Critical error"}),
        json.dumps({"level": "ERROR", "message": "Regular error"}),
        json.dumps({"level": "WARN", "message": "Warning 1"}),
        json.dumps({"level": "WARNING", "message": "Warning 2"}),
        json.dumps({"level": "INFO", "message": "Info log"}),
        json.dumps({"level": "DEBUG", "message": "Debug log"}),
        json.dumps({"level": "TRACE", "message": "Trace log"}),
        json.dumps({"level": "UNKNOWN_LEVEL", "message": "Other log 1"}),
        json.dumps({"message": "Missing level log"}),
    ]
    file_path = create_temp_log_file(lines)
    try:
        metrics, report, top_error = analyze_file(file_path)
        assert metrics["total_logs"] == 10
        assert metrics["critical_count"] == 2
        assert metrics["error_count"] == 1
        assert metrics["warning_count"] == 2
        assert metrics["info_count"] == 1
        assert metrics["debug_count"] == 2
        assert metrics["other_count"] == 2
        assert report["health"] == "critical"
    finally:
        os.remove(file_path)


def test_tolerated_malformed_lines():
    lines = [
        json.dumps({"level": "INFO", "message": "Valid 1"}),
        "THIS IS NOT VALID JSON",
        json.dumps([1, 2, 3]),  # Non-dict JSON
        json.dumps({"level": "ERROR", "message": "Valid 2"}),
        json.dumps({"level": "INFO", "message": "Valid 3"}),
        json.dumps({"level": "INFO", "message": "Valid 4"}),
    ]
    file_path = create_temp_log_file(lines)
    try:
        metrics, report, top_error = analyze_file(file_path)
        assert metrics["total_logs"] == 4
        assert report["skipped_lines"] == 2
        assert report["health"] == "degraded"
    finally:
        os.remove(file_path)


def test_gzip_input():
    lines = [
        json.dumps({"level": "INFO", "message": "Gzipped log message 1"}),
        json.dumps({"level": "WARN", "message": "Gzipped warning log"}),
    ]
    file_path = create_temp_log_file(lines, is_gzip=True)
    try:
        metrics, report, top_error = analyze_file(file_path)
        assert metrics["total_logs"] == 2
        assert metrics["info_count"] == 1
        assert metrics["warning_count"] == 1
    finally:
        os.remove(file_path)


def test_over_threshold_failure(monkeypatch):
    monkeypatch.setenv("MAX_SKIPPED_RATIO", "0.5")
    lines = [
        json.dumps({"level": "INFO", "message": "Valid log"}),
        "INVALID LINE 1",
        "INVALID LINE 2",
        "INVALID LINE 3",
    ]
    file_path = create_temp_log_file(lines)
    try:
        with pytest.raises(InvalidLogFileError, match="exceeds maximum threshold"):
            analyze_file(file_path)
    finally:
        os.remove(file_path)


def test_empty_file_failure():
    file_path = create_temp_log_file([])
    try:
        with pytest.raises(InvalidLogFileError, match="contains zero valid log entries"):
            analyze_file(file_path)
    finally:
        os.remove(file_path)


def test_banner_message_normalization():
    banner_msg = "\n\n*********************************\n\nActual log message after banner"
    norm = normalize_message(banner_msg)
    assert norm == "Actual log message after banner"


def test_7_digit_fraction_timestamp():
    ts_7_digits = "2026-09-26T14:42:54.9615012+05:30"
    parsed_dt = parse_timestamp(ts_7_digits)
    assert parsed_dt is not None
    assert parsed_dt.year == 2026
    assert parsed_dt.month == 9
    assert parsed_dt.microsecond == 961501


def test_real_file_if_present():
    real_file = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "../../log sources/SMS-backend/api-gateway/api-gateway/logs/api-gateway.jsonl",
        )
    )
    if os.path.exists(real_file):
        metrics, report, top_error = analyze_file(real_file)
        assert metrics["total_logs"] > 0
        assert "health" in report
        assert "time_range" in report
        assert isinstance(report["top_errors"], list)
