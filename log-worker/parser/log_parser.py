import gzip
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, Generator, Tuple
from dotenv import load_dotenv

from errors import InvalidLogFileError

load_dotenv()

# Case-insensitive mapping of level strings to target level buckets
LEVEL_BUCKETS = {
    "FATAL": "critical",
    "CRITICAL": "critical",
    "ERROR": "error",
    "WARN": "warning",
    "WARNING": "warning",
    "INFO": "info",
    "DEBUG": "debug",
    "TRACE": "debug",
}


def parse_timestamp(ts_str: Any) -> datetime | None:
    """
    Parses an ISO 8601 timestamp string into a timezone-aware datetime object.
    Truncates 7+ fractional second digits down to 6 digits to satisfy Python's datetime.fromisoformat.
    If parsing fails, returns None (timestamp failure does NOT mark line as malformed).
    """
    if not ts_str or not isinstance(ts_str, str):
        return None

    try:
        # Truncate fractional seconds with more than 6 digits down to 6 digits
        # e.g. "2026-09-26T14:42:54.9615012+05:30" -> "2026-09-26T14:42:54.961501+05:30"
        cleaned_ts = re.sub(r"(\.\d{6})\d+", r"\1", ts_str)
        if cleaned_ts.endswith("Z"):
            cleaned_ts = cleaned_ts[:-1] + "+00:00"
        return datetime.fromisoformat(cleaned_ts)
    except Exception:
        return None


def normalize_message(message: Any) -> str:
    """
    Normalizes log message for grouping/display:
    Finds the first non-empty line with at least one letter or digit (skipping banner asterisks/dashes),
    strips leading/trailing whitespace, and truncates to 200 characters.
    """
    if not message or not isinstance(message, str):
        return ""

    lines = message.splitlines()
    for line in lines:
        stripped = line.strip()
        if any(c.isalnum() for c in stripped):
            return stripped[:200]
    return message.strip()[:200]


def is_gzipped_file(file_path: str) -> bool:
    """
    Inspects the first 2 bytes of a file for gzip magic bytes (0x1f 0x8b).
    """
    try:
        with open(file_path, "rb") as f:
            header = f.read(2)
            return header == b"\x1f\x8b"
    except Exception as e:
        raise InvalidLogFileError(f"Could not read log file header: {e}") from e


def stream_log_file(file_path: str) -> Generator[Dict[str, Any], None, None]:
    """
    Streams a log file line-by-line, validating JSON structure and extracting mapped fields.
    Enforces MAX_SKIPPED_RATIO and minimum valid entries rules at EOF.
    """
    if not os.path.isfile(file_path):
        raise InvalidLogFileError(f"Log file does not exist: '{file_path}'")

    is_gz = is_gzipped_file(file_path)

    try:
        if is_gz:
            file_obj = gzip.open(file_path, "rt", encoding="utf-8", errors="replace")
        else:
            file_obj = open(file_path, "r", encoding="utf-8", errors="replace")
    except Exception as e:
        raise InvalidLogFileError(f"Failed to open log file (corrupt or unreadable): {e}") from e

    skipped_lines = 0
    valid_entries = 0
    non_empty_lines = 0

    try:
        with file_obj:
            for line in file_obj:
                stripped = line.strip()
                if not stripped:
                    continue  # Skip blank lines

                non_empty_lines += 1

                try:
                    data = json.loads(stripped)
                    if not isinstance(data, dict):
                        skipped_lines += 1
                        continue
                except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
                    skipped_lines += 1
                    continue

                # Extract fields with fallbacks
                ts_str = data.get("@timestamp") or data.get("timestamp")
                timestamp_dt = parse_timestamp(ts_str)

                level_raw = data.get("level")
                if level_raw is None:
                    level_bucket = "other"
                else:
                    level_bucket = LEVEL_BUCKETS.get(str(level_raw).upper(), "other")

                message = str(data.get("message") or "")
                logger = str(data.get("logger_name") or data.get("logger") or "unknown")
                stack_trace = data.get("stack_trace")
                if stack_trace is not None:
                    stack_trace = str(stack_trace)

                valid_entries += 1
                yield {
                    "timestamp": timestamp_dt,
                    "level_bucket": level_bucket,
                    "raw_level": str(level_raw) if level_raw is not None else "NONE",
                    "message": message,
                    "logger": logger,
                    "stack_trace": stack_trace,
                    "skipped_lines_count": skipped_lines,
                    "non_empty_lines_count": non_empty_lines,
                }

    except (gzip.BadGzipFile, EOFError, OSError) as e:
        raise InvalidLogFileError(f"Corrupt or unreadable log file during streaming: {e}") from e

    max_skipped_ratio = float(os.getenv("MAX_SKIPPED_RATIO", "0.5"))

    if valid_entries == 0:
        raise InvalidLogFileError("Log file contains zero valid log entries.")

    if non_empty_lines > 0:
        skipped_ratio = skipped_lines / non_empty_lines
        if skipped_ratio > max_skipped_ratio:
            raise InvalidLogFileError(
                f"Skipped lines ratio ({skipped_ratio:.1%}) exceeds maximum threshold ({max_skipped_ratio:.1%})."
            )
