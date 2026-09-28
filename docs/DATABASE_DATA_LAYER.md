# Database Data Layer & MongoDB Schema Specification

**Database:** `log_analytics`  
**Collection:** `ingestions`  
**Owner:** Backend Dev & DBA  
**Consumers:** API Developer (`log-ingestion-api/`), Dashboard Developer (`dashboard/`)

---

## 1. Overview & Architecture

The database layer manages ingestion metadata, lifecycle states, computed metrics, and analytics aggregations.
- **API Developer**: Inserts initial `pending` records and reads records via query functions.
- **Worker**: Atomically updates state to `processing` and finally `completed` or `failed`.
- **Dashboard Developer**: Reads aggregated service metrics, time-series trends, and health states.

---

## 2. Ingestion Document Schema

### Lifecycle States (`status` enum)
- `pending`: Registered by API prior to queuing RabbitMQ message.
- `processing`: Worker has claimed the message and started download/analysis.
- `completed`: Successfully processed; contains `metrics` and `report`.
- `failed`: Worker encountered a permanent failure; contains `error_reason`.

### Document Field Reference
| Field | Type | Required | Description |
|---|---|---|---|
| `_id` | `ObjectId` | Auto | MongoDB internal document ID |
| `ingest_id` | `string` (UUID) | Yes | Primary business key (Unique) |
| `service_name` | `string` | Yes | Microservice identifier (e.g. `api-gateway`) |
| `environment` | `string` | Yes | Deployment environment (`dev`, `staging`, `prod`) |
| `object_key` | `string` | Yes | Path in MinIO/S3 (e.g. `raw-logs/api-gateway-<uuid>.jsonl`) |
| `status` | `string` (enum) | Yes | `"pending"`, `"processing"`, `"completed"`, `"failed"` |
| `created_at` | `ISODate` (UTC) | Yes | Ingestion initialization timestamp |
| `processing_started_at` | `ISODate` or `null` | No | Timestamp when worker began processing |
| `processed_at` | `ISODate` or `null` | No | Completion or failure timestamp |
| `error_reason` | `string` or `null` | No | Failure explanation if status is `"failed"` |
| `top_error` | `string` or `null` | No | Primary error message string |
| `metrics` | `object` or `null` | No | Log count counters (defined below) |
| `report` | `object` or `null` | No | Deep analytical breakdown (defined below) |

### Sub-document: `metrics`
```json
{
  "total_logs": 117,
  "critical_count": 0,
  "error_count": 1,
  "warning_count": 8,
  "info_count": 108,
  "debug_count": 0,
  "other_count": 0
}
```

### Sub-document: `report`
```json
{
  "health": "degraded",
  "time_range": {
    "first": "2026-09-26T14:42:54.955533+05:30",
    "last": "2026-09-26T14:53:08.994663+05:30"
  },
  "top_errors": [{"message": "DiscoveryClient de-registration failed", "count": 1}],
  "top_warnings": [{"message": "Request execution failed", "count": 2}],
  "top_sources": [{"logger": "com.netflix.discovery", "count": 2}],
  "error_samples": [
    {
      "timestamp": "2026-09-26T14:46:14.783752+05:30",
      "logger": "com.netflix.discovery.DiscoveryClient",
      "message": "DiscoveryClient de-registration failed",
      "stack_trace_head": "com.netflix.discovery.shared.transport.TransportException..."
    }
  ],
  "findings": [
    {
      "id": "RULE_CONN_REFUSED",
      "title": "Connection Refused",
      "severity": "error",
      "hint": "A target network port or backend service is offline.",
      "count": 4,
      "example": "Request execution error..."
    }
  ],
  "skipped_lines": 0
}
```

---

## 3. Database Indexes

Run `python db/setup_schema_and_indexes.py` to ensure these indexes exist:
1. `idx_ingest_id_unique` on `{"ingest_id": 1}` (`unique=True`): Fast $O(1)$ point lookups.
2. `idx_service_created` on `{"service_name": 1, "created_at": -1}`: Compound index for service chronological queries.
3. `idx_status` on `{"status": 1}`: Pipeline queue state filtering.
4. `idx_created_at` on `{"created_at": -1}`: Time-window queries and system-wide chronological sorting.

---

## 4. Query Functions for FastAPI Developer (`log-ingestion-api/`)

The functions in `db.aggregations` are already JSON-safe (datetimes are converted to ISO-8601 strings and `_id` is converted to a string).

### A. Powering `GET /metrics/summary`
```python
from db.aggregations import get_metrics_summary

# Query all services
summary = get_metrics_summary()

# Or query a specific service with optional time window
summary = get_metrics_summary(service_name="api-gateway", time_window_hours=24)
```

**Return Shape (`list[dict]`):**
```json
[
  {
    "service_name": "api-gateway",
    "total_logs": 234,
    "critical_count": 0,
    "error_count": 2,
    "warning_count": 16,
    "info_count": 216,
    "debug_count": 0,
    "other_count": 0,
    "ingestion_count": 2,
    "latest_health": "degraded",
    "latest_ingest_time": "2026-09-28T16:13:38.072000+00:00"
  }
]
```

### B. Powering `GET /logs/status?id={ingest_id}`
```python
from db.aggregations import get_ingestion_status

record = get_ingestion_status(ingest_id="5357a679-3104-4981-9e1a-53f00ef53f04")
if not record:
    # return 404 Not Found
```
**Return Shape (`dict` or `None`):**
Returns the full JSON-serializable document including `status`, `metrics`, and `report`.

---

## 5. Query Functions for Dashboard Developer (`dashboard/`)

```python
from db.aggregations import (
    get_health_breakdown,
    get_top_errors_by_service,
    get_time_based_trends,
    get_pipeline_status_counts,
)
```

### A. System Health Card Widget
```python
health = get_health_breakdown()
```
**Return Shape:**
```json
{
  "summary": {
    "healthy": 0,
    "warning": 2,
    "degraded": 4,
    "critical": 0,
    "unknown": 0,
    "total_services": 6
  },
  "by_service": [
    {"service_name": "api-gateway", "health": "degraded"},
    {"service_name": "auth-service", "health": "degraded"},
    {"service_name": "course-service", "health": "warning"}
  ]
}
```

### B. Top Errors by Service Table / Charts
```python
top_errors = get_top_errors_by_service(limit_per_service=3)
```
**Return Shape:**
```json
[
  {
    "service_name": "api-gateway",
    "top_errors": [
      {
        "message": "DiscoveryClient_API-GATEWAY: de-registration failed",
        "count": 2
      }
    ]
  }
]
```

### C. Hourly Log Volume & Error Trends (Timeline Chart)
```python
trends = get_time_based_trends(interval="hour", limit=24)
```
**Return Shape:**
```json
[
  {
    "timestamp": "2026-09-28T16:00:00+00:00",
    "ingestion_count": 1,
    "total_logs": 117,
    "error_count": 1,
    "warning_count": 8
  },
  {
    "timestamp": "2026-09-28T17:00:00+00:00",
    "ingestion_count": 6,
    "total_logs": 636,
    "error_count": 4,
    "warning_count": 36
  }
]
```

### D. Pipeline Operational Status
```python
status_counts = get_pipeline_status_counts()
```
**Return Shape:**
```json
{
  "pending": 0,
  "processing": 0,
  "completed": 7,
  "failed": 0,
  "total": 7
}
```

---

## 6. How to Run Scripts & Tests Locally

```cmd
# Activate venv
db\.venv\Scripts\activate

# Apply indexes and schema validation
python db\setup_schema_and_indexes.py

# Seed all 6 microservices
python db\seed_services.py

# Run aggregation verification
python db\run_aggregations.py

# Run automated tests
pytest db\tests -v
```
