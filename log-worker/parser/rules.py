import re
from typing import Any, Dict, List

# Editable list of finding rules applied to log entries
FINDING_RULES: List[Dict[str, Any]] = [
    {
        "id": "RULE_CONN_REFUSED",
        "title": "Connection Refused",
        "patterns": [r"connection refused", r"ConnectException"],
        "severity": "error",
        "hint": "A target network port or backend service is offline. Check if the target host and port are active.",
    },
    {
        "id": "RULE_TIMEOUT",
        "title": "Operation Timeout",
        "patterns": [r"timeout", r"timed out", r"SocketTimeoutException"],
        "severity": "error",
        "hint": "An operation exceeded its expected response window. Inspect network latency or downstream service performance.",
    },
    {
        "id": "RULE_EUREKA_REGISTRY",
        "title": "Eureka Service Registry Issue",
        "patterns": [r"eureka", r"de-registration failed", r"Cannot execute request on any known server"],
        "severity": "warning",
        "hint": "Microservice discovery/registration failed with Eureka. Check Eureka server status and discovery URLs.",
    },
    {
        "id": "RULE_OUT_OF_MEMORY",
        "title": "Out Of Memory Error",
        "patterns": [r"OutOfMemoryError", r"heap space"],
        "severity": "critical",
        "hint": "The Java process ran out of heap space. Increase JVM heap memory (-Xmx) or analyze heap dumps for leaks.",
    },
    {
        "id": "RULE_NULL_POINTER",
        "title": "Null Pointer Exception",
        "patterns": [r"NullPointerException"],
        "severity": "error",
        "hint": "Unchecked null reference in application code. Check the stack trace to locate the missing null check.",
    },
    {
        "id": "RULE_DB_CONNECTIVITY",
        "title": "Database Connectivity Failure",
        "patterns": [r"SQLException", r"JDBC", r"Communications link failure"],
        "severity": "error",
        "hint": "Database connection failed or was closed. Verify database credentials, host reachability, and pool capacity.",
    },
    {
        "id": "RULE_DEPRECATION",
        "title": "Deprecation Notice",
        "patterns": [r"deprecated"],
        "severity": "warning",
        "hint": "A feature or dependency in use is marked as deprecated. Plan an update to standard non-deprecated alternatives.",
    },
]

# Compile regex patterns once for efficiency
COMPILED_RULES = [
    {
        "id": rule["id"],
        "title": rule["title"],
        "severity": rule["severity"],
        "hint": rule["hint"],
        "compiled_patterns": [re.compile(p, re.IGNORECASE) for p in rule["patterns"]],
    }
    for rule in FINDING_RULES
]
