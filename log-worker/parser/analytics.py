from collections import Counter
from typing import Any, Dict, List, Tuple

from errors import InvalidLogFileError
from parser.log_parser import normalize_message, stream_log_file
from parser.rules import COMPILED_RULES


def extract_stack_trace_head(stack_trace: Any) -> str | None:
    """
    Extracts the first non-empty line of a stack trace, stripped and truncated to 200 characters.
    """
    if not stack_trace or not isinstance(stack_trace, str):
        return None

    for line in stack_trace.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:200]
    return None


def analyze_file(path: str) -> Tuple[Dict[str, Any], Dict[str, Any], str | None]:
    """
    Single-pass aggregator that streams log entries from a file and computes metrics, report, and top_error.
    Does not load all entries into memory.
    
    Returns:
        (metrics, report, top_error)
    """
    # Level metrics counters
    metrics = {
        "total_logs": 0,
        "critical_count": 0,
        "error_count": 0,
        "warning_count": 0,
        "info_count": 0,
        "debug_count": 0,
        "other_count": 0,
    }

    min_ts = None
    max_ts = None

    error_messages = Counter()
    warning_messages = Counter()
    logger_sources = Counter()

    error_samples: List[Dict[str, Any]] = []

    # Rule tracking: rule_id -> count, rule_id -> first matching normalized message
    rule_counts: Dict[str, int] = {r["id"]: 0 for r in COMPILED_RULES}
    rule_examples: Dict[str, str] = {}

    last_skipped_lines = 0

    for entry in stream_log_file(path):
        bucket = entry["level_bucket"]
        metrics["total_logs"] += 1
        metrics[f"{bucket}_count"] += 1

        last_skipped_lines = entry.get("skipped_lines_count", 0)

        # Track timestamp boundaries
        ts = entry["timestamp"]
        if ts is not None:
            if min_ts is None or ts < min_ts:
                min_ts = ts
            if max_ts is None or ts > max_ts:
                max_ts = ts

        norm_msg = normalize_message(entry["message"])
        logger = entry["logger"]
        st_head = extract_stack_trace_head(entry["stack_trace"])

        # Top errors / warnings / sources grouping
        if bucket in ("critical", "error"):
            error_messages[norm_msg] += 1
            logger_sources[logger] += 1

            if len(error_samples) < 3:
                error_samples.append({
                    "timestamp": ts.isoformat() if ts else None,
                    "logger": logger,
                    "message": norm_msg,
                    "stack_trace_head": st_head,
                })
        elif bucket == "warning":
            warning_messages[norm_msg] += 1
            logger_sources[logger] += 1

        # Match finding rules against message + stack_trace
        full_text = f"{entry['message']} {entry['stack_trace'] or ''}"
        for rule in COMPILED_RULES:
            matched = any(pattern.search(full_text) for pattern in rule["compiled_patterns"])
            if matched:
                rule_id = rule["id"]
                rule_counts[rule_id] += 1
                if rule_id not in rule_examples:
                    rule_examples[rule_id] = norm_msg

    # Determine health status based on highest severity encountered
    if metrics["critical_count"] > 0:
        health = "critical"
    elif metrics["error_count"] > 0:
        health = "degraded"
    elif metrics["warning_count"] > 0:
        health = "warning"
    else:
        health = "healthy"

    # Format top 3 lists
    top_errors = [
        {"message": msg, "count": count}
        for msg, count in sorted(error_messages.items(), key=lambda x: (-x[1], x[0]))[:3]
    ]

    top_warnings = [
        {"message": msg, "count": count}
        for msg, count in sorted(warning_messages.items(), key=lambda x: (-x[1], x[0]))[:3]
    ]

    top_sources = [
        {"logger": lgr, "count": count}
        for lgr, count in sorted(logger_sources.items(), key=lambda x: (-x[1], x[0]))[:3]
    ]

    # Format findings list for rules with count > 0, sorted by count desc
    findings = []
    for rule in COMPILED_RULES:
        rule_id = rule["id"]
        cnt = rule_counts[rule_id]
        if cnt > 0:
            findings.append({
                "id": rule_id,
                "title": rule["title"],
                "severity": rule["severity"],
                "hint": rule["hint"],
                "count": cnt,
                "example": rule_examples.get(rule_id, ""),
            })

    findings.sort(key=lambda x: x["count"], reverse=True)

    report = {
        "health": health,
        "time_range": {
            "first": min_ts.isoformat() if min_ts else None,
            "last": max_ts.isoformat() if max_ts else None,
        },
        "top_errors": top_errors,
        "top_warnings": top_warnings,
        "top_sources": top_sources,
        "error_samples": error_samples,
        "findings": findings,
        "skipped_lines": last_skipped_lines,
    }

    top_error = top_errors[0]["message"] if top_errors else None

    return metrics, report, top_error
