# Integration Audit Report: Distributed Log & Audit Analytics Pipeline

**Audit Date:** 2026-09-29  
**Audit Scope:** `log-ingestion-api/api/`, `db/`, `dashboard/`, `infra/`, and Root Orchestration.  
**Reference Baseline Contract:** `log-worker/` (Authoritative contract; immutable).

---

## Executive Summary

This audit evaluates the codebase integration across the four primary components of the distributed log analytics pipeline. The `log-worker` component serves as the authoritative baseline reference for message shapes, database schema, and object storage conventions. 

All three target components (`log-ingestion-api/api/`, `db/`, and `dashboard/`) were analyzed against the reference contract. Key findings include architectural decoupling (such as `db/` being un-wired from `log-ingestion-api/api/`), client-side log validation incompatibilities in `dashboard/`, and missing root-level container orchestration.

---

## Component 1: `log-ingestion-api/api/`

### 1. Component Overview
- **Type:** Standalone running HTTP microservice.
- **Runtime Entrypoint & Port:** ASGI Uvicorn server running `uvicorn app.main:app --host 0.0.0.0 --port 8000` (Exposes port `8000`).
- **Framework & Key Libraries:** Python 3.13, FastAPI (v0.115.0), Uvicorn, Pydantic (v2.7.0), `pydantic-settings`, PyMongo (v4.6.0), `boto3`, `pika`, `python-multipart`.

### 2. Environment Variables Inspection
| Variable Name | Component Default | Matches `log-worker/.env.example`? | Status / Description |
|---|---|---|---|
| `PORT` | `8000` | N/A (API Specific) | Server HTTP binding port |
| `HOST` | `"0.0.0.0"` | N/A (API Specific) | Server HTTP binding host |
| `CORS_ORIGINS` | `"*"` | N/A (API Specific) | Allowed CORS origins string |
| `MAX_UPLOAD_BYTES` | `10485760` (10MB) | N/A (API Specific) | Maximum upload file streaming cap |
| `RABBITMQ_HOST` | `"localhost"` | YES (`RABBITMQ_HOST`) | RabbitMQ broker hostname |
| `RABBITMQ_PORT` | `5672` | YES (`RABBITMQ_PORT`) | RabbitMQ broker port |
| `RABBITMQ_USER` | `"guest"` | YES (`RABBITMQ_USER`) | RabbitMQ username |
| `RABBITMQ_PASSWORD` | `"guest"` | YES (`RABBITMQ_PASSWORD`) | RabbitMQ password |
| `RABBITMQ_QUEUE_NAME` | `"log-ingestion-queue"` | YES (`RABBITMQ_QUEUE_NAME`) | Queue name for ingestion tasks |
| `MONGO_URI` | `"mongodb://localhost:27017"` | YES (`MONGO_URI`) | MongoDB connection URI |
| `MONGO_DB_NAME` | `"log_analytics"` | YES (`MONGO_DB_NAME`) | MongoDB database name |
| `MONGO_COLLECTION` | `"ingestions"` | YES (`MONGO_COLLECTION`) | MongoDB collection name |
| `S3_ENDPOINT_URL` | `"http://localhost:9000"` | YES (`S3_ENDPOINT_URL`) | Object Storage endpoint URL |
| `S3_ACCESS_KEY` | `"minioadmin"` | YES (`S3_ACCESS_KEY`) | MinIO root access key |
| `S3_SECRET_KEY` | `"minioadmin"` | YES (`S3_SECRET_KEY`) | MinIO root secret key |
| `S3_BUCKET_NAME` | `"raw-logs"` | YES (`S3_BUCKET_NAME`) | Object storage bucket name |
| `S3_REGION` | `"us-east-1"` | YES (`S3_REGION`) | S3 region identifier |

### 3. Messaging, Storage & Database Contracts
- **RabbitMQ Integration:** Declares durable queue (`durable=True`), enables publisher confirms, and publishes persistent messages (`delivery_mode=2`) with payload `{"ingest_id": str, "service_name": str, "object_key": str}`. **Fully matches contract.**
- **MongoDB Integration:** Reads/writes database `"log_analytics"`, collection `"ingestions"`. Documents are looked up by the string field `"ingest_id"` (explicitly excluding MongoDB internal `_id`). Field schema matches the worker contract. **Fully matches contract.**
- **Object Storage Integration:** Connects to MinIO/S3 using `boto3` path-style addressing (`addressing_style: "path"`), target bucket `"raw-logs"`, object key format `raw-logs/{service_name}-{ingest_id}{ext}`. **Fully matches contract.**

### 4. HTTP Endpoints Specification
| Method | Path | Request Shape | Response Shape (JSON Fields) |
|---|---|---|---|
| `GET` | `/health` | None | `{"status": "ok"}` |
| `POST` | `/logs/upload` | Multipart form: `file` (UploadFile), `service_name` (str), `environment` (str, default `"dev"`) | `{"ingest_id": str, "status": "pending"}` (HTTP 201) |
| `GET` | `/logs/status` | Query param: `id` (str UUID) | `{"ingest_id", "service_name", "environment", "object_key", "status", "metrics", "top_error", "report", "error_reason", "created_at", "processed_at", "processing_started_at"}` |
| `GET` | `/logs` | Query params: `service_name`, `status`, `environment`, `limit` (default 50), `skip` (default 0) | `List[LogRecord]` (Array of full log records) |
| `GET` | `/metrics/summary` | Query params: `service_name`, `from` (datetime), `to` (datetime) | `List[ServiceMetricsSummary]` (`service_name`, `total_logs`, `error_count`, `warning_count`, `critical_count`, `health`) |

### 5. Hardcoded Values & Test Artifacts
- **Hardcoded Infrastructure Defaults:** Fallbacks for `"localhost"` endpoints in `app/config.py`, `app/clients/queue_client.py`, `app/clients/storage_client.py`, and `app/repositories/ingestion_repository.py`.
- **Test Artifacts:** `api/openapi.json` (exported spec) and unit tests under `api/tests/` (`test_health.py`, `test_logs.py`, `test_metrics.py`, `fakes/`).

---

## Component 2: `db/`

### 1. Component Overview
- **Type:** Standalone database administration, schema setup, data seeding, and aggregation helper module. (Not a running HTTP service; no listening port).
- **Framework & Key Libraries:** Python, PyMongo (v4.6+), `python-dotenv`, `boto3`, `pika`, `pytest`.

### 2. Environment Variables Inspection
| Variable Name | Component Default | Matches `log-worker/.env.example`? | Status / Description |
|---|---|---|---|
| `MONGO_URI` | `"mongodb://localhost:27017"` | YES (`MONGO_URI`) | Target MongoDB URI |
| `MONGO_DB_NAME` | `"log_analytics"` | YES (`MONGO_DB_NAME`) | Target MongoDB database name |
| `MONGO_COLLECTION` | `"ingestions"` | YES (`MONGO_COLLECTION`) | Target MongoDB collection name |
| `S3_ENDPOINT_URL` | `"http://localhost:9000"` | YES (`S3_ENDPOINT_URL`) | Target MinIO endpoint for seeding |
| `S3_ACCESS_KEY` | `"minioadmin"` | YES (`S3_ACCESS_KEY`) | MinIO access key |
| `S3_SECRET_KEY` | `"minioadmin"` | YES (`S3_SECRET_KEY`) | MinIO secret key |
| `S3_BUCKET_NAME` | `"raw-logs"` | YES (`S3_BUCKET_NAME`) | Target S3 bucket for seeding |
| `S3_REGION` | `"us-east-1"` | YES (`S3_REGION`) | S3 region |
| `RABBITMQ_HOST` | `"localhost"` | YES (`RABBITMQ_HOST`) | RabbitMQ host for seeding |
| `RABBITMQ_PORT` | `5672` | YES (`RABBITMQ_PORT`) | RabbitMQ port for seeding |
| `RABBITMQ_USER` | `"guest"` | YES (`RABBITMQ_USER`) | RabbitMQ user |
| `RABBITMQ_PASSWORD` | `"guest"` | YES (`RABBITMQ_PASSWORD`) | RabbitMQ password |
| `RABBITMQ_QUEUE_NAME` | `"log-ingestion-queue"` | YES (`RABBITMQ_QUEUE_NAME`) | Target RabbitMQ queue for seeding |

### 3. Exposed Functions/Classes & API Wiring Status
| File | Exposed Function / Class | Purpose | Current Integration with `log-ingestion-api/api/` |
|---|---|---|---|
| `setup_schema_and_indexes.py` | `apply_schema_and_indexes()` | Creates unique index on `ingest_id`, compound index on `(service_name, created_at)`, index on `status`, and applies JSON Schema validation. | **Not wired.** Never imported or invoked by `log-ingestion-api/api/`. |
| `aggregations.py` | `get_metrics_summary()`, `get_health_breakdown()`, `get_top_errors_by_service()`, `get_pipeline_status_counts()`, `get_time_based_trends()`, `get_ingestion_status()`, `get_db()` | High-performance PyMongo aggregation query helper functions. | **Not wired.** `log-ingestion-api/api/` re-implements its own MongoDB query logic inside `api/app/repositories/ingestion_repository.py` instead of importing this module. |
| `seed_services.py` | `seed_services()`, `get_s3_client()`, `ensure_bucket()` | CLI tool to seed 6 microservices logs into MinIO, MongoDB, and RabbitMQ. | Standalone CLI seeder script. |
| `inspect_collection.py` | `inspect_collection()` | CLI diagnostic tool to print collection schema and stats. | Standalone CLI tool. |

### 4. Contracts & Integrity Validation
- **RabbitMQ:** `seed_services.py` publishes persistent messages to `"log-ingestion-queue"` with `durable=True` and shape `{"ingest_id": str, "service_name": str, "object_key": str}`. **Matches contract.**
- **MongoDB Schema:** `setup_schema_and_indexes.py` defines BSON schema matching fields `ingest_id`, `service_name`, `environment`, `object_key`, `status` (`pending`|`processing`|`completed`|`failed`), `created_at`, `processing_started_at`, `processed_at`, `error_reason`, `top_error`, `metrics`, `report`. Creates unique index on `ingest_id`. **Matches contract.**
- **Object Storage:** Uploads to bucket `"raw-logs"` with path-style keys `raw-logs/{service_name}-{ingest_id}.jsonl`. **Matches contract.**

### 5. Hardcoded Values & Test Artifacts
- **Hardcoded Infrastructure Defaults:** Localhost connection fallbacks (`localhost:27017`, `http://localhost:9000`, `localhost:5672`) in `aggregations.py`, `setup_schema_and_indexes.py`, `seed_services.py`, and `inspect_collection.py`.
- **Test Artifacts & Scripts:** `inspect_collection.py`, `run_aggregations.py`, `seed_services.py`, and unit test suite `db/tests/test_aggregations.py` (which uses `mongomock`).

---

## Component 3: `dashboard/`

### 1. Component Overview
- **Type:** Standalone running Web Frontend Application (Streamlit).
- **Runtime Entrypoint & Port:** `streamlit run app.py --server.port=8501 --server.address=0.0.0.0` (Exposes port `8501`).
- **Framework & Key Libraries:** Python 3.11, Streamlit (>=1.35.0), `requests`, `pandas`, `plotly`.

### 2. Environment Variables Inspection
| Variable Name | Component Default | Matches `log-worker/.env.example`? | Status / Description |
|---|---|---|---|
| `API_BASE_URL` | `"http://localhost:8000"` (in code) / `"http://log-ingestion-api:8000"` (in Dockerfile) | N/A (Dashboard Specific) | Ingestion API base HTTP URL |
| `DEMO_MODE` | `"false"` | N/A (Dashboard Specific) | Toggle for running with mock data |

### 3. Backend Endpoints Called & Expected Response Shapes
| Target Endpoint | HTTP Method | Expected Request Shape | Expected Response JSON Shape |
|---|---|---|---|
| `{API_BASE_URL}/metrics/summary` | `GET` | None (Timeout: 2s / 10s) | List of objects: `[{"service_name": str, "total_logs": int, "error_count": int, "warning_count": int, "critical_count": int, "health": str}]` |
| `{API_BASE_URL}/logs/upload` | `POST` | Multipart Form: `file` (binary), `service_name` (str), `environment` (str) | `{"ingest_id": str, "status": "pending"}` (HTTP 201) |
| `{API_BASE_URL}/logs/status` | `GET` | Query Parameter: `id` (str UUID) | `{"ingest_id": str, "service_name": str, "environment": str, "status": str, "metrics": dict, "top_error": str, "error_reason": str, "created_at": str, "processed_at": str, "report": dict}` |

### 4. Client-Side Log Validation Incompatibility
`dashboard/validation.py` enforces client-side file inspection before submitting to `POST /logs/upload`:
- **Line 6:** `REQUIRED_LOG_FIELDS = ("timestamp", "level", "service", "message")`
- **Conflict with Real Log Format & Worker Parser:** Real Spring Boot log entries (such as those in `runtime-logs/` and `log sources/`) use `"@timestamp"` instead of `"timestamp"` and `"logger_name"` instead of `"service"`. Real log files do not contain a `"service"` field inside each log record line (the service name is provided via form parameters).
- **Result:** `dashboard/validation.py` rejects valid system log files on client-side upload with an error (`Line 1 is missing required field 'timestamp'`).

### 5. Hardcoded Values & Test Artifacts
- **Hardcoded Defaults:** Default fallback `API_BASE_URL = "http://localhost:8000"` in `api.py`. Fallback list of service names `["All services", "product-service", "coupon-service", "api-gateway", "auth-service"]` in `app.py` (Line 84).
- **Test / Mock Artifacts:** `mock.py` (complete mock data generator and demo state manager) and `generate_sample_logs()` sample download generator.

---

## Component 4: Root & Orchestration Infrastructure

### 1. Root-Level Docker Compose
- **Status:** **Missing.** No `docker-compose.yml` file exists at the repository root (`/docker-compose.yml`).

### 2. Infrastructure Directory (`infra/docker-compose.yml`)
- **Location:** `infra/docker-compose.yml`.
- **Contents:** Configures **only** the `dashboard` service (Port `8501`).
- **Missing Services:** `log-ingestion-api`, `log-worker`, `rabbitmq`, `mongodb`, and `minio` are only present as commented-out placeholder text.
- **Obsolete Image Reference:** The commented-out placeholder for MinIO references `image: minio/minio`, which has been removed from public container registries. (The reference implementation in `log-worker/docker-compose.yml` uses `pgsty/minio:latest`).

---

## MISMATCH SUMMARY

Concrete integration conflicts and architectural discrepancies across the repository, ordered from **highest integration impact** (system breakages) to **lowest impact** (cosmetic / leftover code):

| Priority | Component(s) Involved | Mismatch Description | Integration Impact |
|---|---|---|---|
| **CRITICAL** | `dashboard` vs `log-worker` / `log-ingestion-api` | **Client-Side Validation Rejection of Real Logs:** `dashboard/validation.py` requires `"timestamp"` and `"service"` in every line of uploaded files. Real log files produced by Spring Boot microservices use `"@timestamp"` and `"logger_name"`. | Users cannot upload real log files through the Dashboard interface; uploads fail client-side before reaching the API. |
| **CRITICAL** | Root / `infra` Orchestration | **Missing Unified `docker-compose.yml`:** No root `docker-compose.yml` exists. `infra/docker-compose.yml` only launches `dashboard` and contains commented-out placeholders. | Running `docker compose up` at the repository root fails. Services cannot discover each other across a unified container network out of the box. |
| **HIGH** | `log-ingestion-api` vs `db` | **Decoupled Data Layer:** `log-ingestion-api/api/` does not import or use `db/` or `db/aggregations.py`. Instead, `log-ingestion-api/api/app/repositories/ingestion_repository.py` re-implements duplicate MongoDB query logic. | Code duplication; schema validation or index updates in `db/` are not automatically reflected in the running API service. |
| **HIGH** | `infra/docker-compose.yml` vs `log-worker` | **Deprecated Image Reference:** `infra/docker-compose.yml` comments reference `minio/minio`, whereas `log-worker` uses `pgsty/minio:latest`. | Uncommenting `infra/docker-compose.yml` without updating the image tag will cause Docker pull errors for MinIO. |
| **MEDIUM** | `log-ingestion-api` vs `db` / `log-worker` | **Health Calculation Rule Discrepancy:** `log-ingestion-api/api/app/routes/metrics.py` dynamically evaluates health as `critical` (`critical_count > 0`), `degraded` (`error_count > 0`), or `healthy`. It omits the `"warning"` status enum defined in `db/setup_schema_and_indexes.py` and computed by `log-worker/parser/analytics.py`. | The API's aggregated summary endpoints omit `warning` health ratings returned by the worker and stored in MongoDB. |
| **LOW** | `dashboard` | **Hardcoded Fallback Service List:** `dashboard/app.py` contains a hardcoded fallback service list (`["product-service", "coupon-service", ...]`) if the API connection fails, which differs from the project's real microservices (`["api-gateway", "auth-service", ...]`). | Minor UI display discrepancy when running the dashboard disconnected from the API. |
| **COSMETIC** | All Components | **Localhost Fallbacks in Code:** Default environment variables across API, DB, and Dashboard code fallback to `localhost` rather than container service names. | Require environment variable overrides when running inside containerized networks. |

---

*End of Integration Audit Report.*
