# Log Ingestion API Service

**Component:** Front-Door Log Ingestion API  
**Project:** Asynchronous Distributed Log & Audit Analytics Pipeline (CS32102)  
**Branch:** `api-developer`  
**Runtime:** Python 3.13.x  

---

## 1. Purpose & Architecture Overview

The **Log Ingestion API** serves as the public "front door" of the distributed audit analytics pipeline. It is responsible for:
1. **Validating & Ingesting Logs**: Accepting multipart uploads of raw JSON / JSONL log files (including gzip-compressed variants), validating filenames, sanitizing service identifiers, enforcing upload size quotas while streaming, and running lightweight syntax checks.
2. **Object Storage Persistence**: Storing raw log files securely in S3 / MinIO object storage (`raw-logs` bucket).
3. **Pipeline Task Registration**: Registering a persistent `pending` tracking record in MongoDB (`log_analytics.ingestions`).
4. **Asynchronous Job Dispatching**: Enqueuing persistent processing messages to RabbitMQ (`log-ingestion-queue`) with publisher confirmations.
5. **Client Query Interface**: Providing low-latency, read-only query endpoints for liveness (`/health`), individual job status (`/logs/status`), historical logs list with pagination and filtering (`/logs`), and operational health metrics aggregations (`/metrics/summary`).

> **Boundary Note:** This service does **NOT** parse entire log files, calculate error distributions, generate analytics reports, or consume RabbitMQ messages. Those responsibilities belong exclusively to the asynchronous **Log Worker** service.

---

## 2. Windows Local Setup (Python 3.13)

### Prerequisites
- Python 3.13 installed on Windows (`python --version`)
- Docker Desktop running (for local MongoDB, MinIO, and RabbitMQ containers)

### Step-by-Step Installation

```powershell
# 1. Navigate to the api directory
cd "c:\Users\L sewmini yasasma\Desktop\Semester 6\Async-Distributed-Log-Audit-Pipeline\log-ingestion-api\api"

# 2. Create a clean Python 3.13 virtual environment
python -m venv venv

# 3. Activate the virtual environment
.\venv\Scripts\Activate.ps1

# 4. Install all runtime and development dependencies
pip install -r requirements.txt

# 5. Create local environment configuration from template
Copy-Item .env.example .env
```

---

## 3. Environment Variables

All environment variables follow the exact naming conventions established across the pipeline repository:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `PORT` | `8000` | Port for the Uvicorn HTTP server |
| `HOST` | `0.0.0.0` | Host bind address |
| `CORS_ORIGINS` | `*` | Comma-separated list of allowed CORS origins or `*` |
| `MAX_UPLOAD_BYTES` | `10485760` | Maximum upload size in bytes (default 10 MB) |
| `RABBITMQ_HOST` | `localhost` | RabbitMQ broker hostname |
| `RABBITMQ_PORT` | `5672` | RabbitMQ AMQP port |
| `RABBITMQ_USER` | `guest` | RabbitMQ username |
| `RABBITMQ_PASSWORD` | `guest` | RabbitMQ password |
| `RABBITMQ_QUEUE_NAME` | `log-ingestion-queue` | Target durable queue name for worker processing |
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection URI |
| `MONGO_DB_NAME` | `log_analytics` | MongoDB database name |
| `MONGO_COLLECTION` | `ingestions` | MongoDB collection name for ingestion documents |
| `S3_ENDPOINT_URL` | `http://localhost:9000` | S3 / MinIO endpoint URL |
| `S3_ACCESS_KEY` | `minioadmin` | MinIO root/access user |
| `S3_SECRET_KEY` | `minioadmin` | MinIO secret password |
| `S3_BUCKET_NAME` | `raw-logs` | Target S3 bucket for uploaded log files |
| `S3_REGION` | `us-east-1` | AWS S3 / MinIO region identifier |

---

## 4. Running Locally Against Infrastructure

### 4.1. Start MongoDB and MinIO
Use the worker's existing development Compose file:
```powershell
docker compose -f "..\..\log-worker\docker-compose.dev.yml" up -d
```

### 4.2. Start RabbitMQ
Run a RabbitMQ container with the management plugin:
```powershell
docker run -d --name pipeline-rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

### 4.3. Run the API Service
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- Interactive Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Alternative ReDoc UI: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- Raw OpenAPI JSON: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 5. Endpoints & API Specification

### 5.1. `GET /health`
Liveness probe endpoint. Returns service status without querying external dependencies.

- **Request:**
  ```http
  GET /health HTTP/1.1
  Host: localhost:8000
  ```
- **Response (200 OK):**
  ```json
  {
    "status": "ok"
  }
  ```

---

### 5.2. `POST /logs/upload`
Accepts a multipart log upload, validates syntax and size, uploads the raw file to MinIO, records a `pending` job in MongoDB, and enqueues a message to RabbitMQ.

- **Request:**
  - Content-Type: `multipart/form-data`
  - Parameters:
    - `file`: Raw log file (`.json`, `.jsonl`, `.json.gz`, `.jsonl.gz`)
    - `service_name`: Alphanumeric service identifier with `-` and `_`
    - `environment`: Optional deployment environment (default: `"dev"`)

  ```bash
  curl -X POST "http://localhost:8000/logs/upload" \
    -F "file=@sample.jsonl" \
    -F "service_name=auth-service" \
    -F "environment=dev"
  ```

- **Response (201 Created):**
  ```json
  {
    "ingest_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "status": "pending"
  }
  ```

- **Error Codes:**
  - `400 Bad Request`: Disallowed extension, empty file, invalid JSON records, corrupt gzip, or unsafe `service_name` containing `/`, `\`, `..`.
  - `413 Content Too Large`: Upload exceeds `MAX_UPLOAD_BYTES` (enforced while streaming).
  - `422 Unprocessable Entity`: Missing required `file` or `service_name`.
  - `503 Service Unavailable`: Downstream storage, database, or RabbitMQ unavailable.

---

### 5.3. `GET /logs/status?id=<ingest_id>`
Retrieves the complete ingestion job record from MongoDB by its unique `ingest_id`. The internal MongoDB `_id` is stripped from every response.

- **Request:**
  ```http
  GET /logs/status?id=9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d HTTP/1.1
  Host: localhost:8000
  ```
- **Response (200 OK - Pending Job):**
  ```json
  {
    "ingest_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "service_name": "auth-service",
    "environment": "dev",
    "object_key": "raw-logs/auth-service-9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d.jsonl",
    "status": "pending",
    "metrics": null,
    "top_error": null,
    "report": null,
    "error_reason": null,
    "created_at": "2026-09-28T16:50:00Z",
    "processed_at": null,
    "processing_started_at": null
  }
  ```
- **Response (200 OK - Worker Completed Job):**
  ```json
  {
    "ingest_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "service_name": "auth-service",
    "environment": "dev",
    "object_key": "raw-logs/auth-service-9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d.jsonl",
    "status": "completed",
    "metrics": {
      "total_logs": 1500,
      "critical_count": 0,
      "error_count": 12,
      "warning_count": 45,
      "info_count": 1400,
      "debug_count": 43,
      "other_count": 0
    },
    "top_error": "Connection reset by peer: redis:6379",
    "report": {
      "health": "degraded",
      "time_range": {
        "first": "2026-09-28T12:00:00Z",
        "last": "2026-09-28T12:30:00Z"
      },
      "top_errors": [
        {"message": "Connection reset by peer: redis:6379", "count": 8}
      ],
      "top_warnings": [],
      "top_sources": [
        {"logger": "com.auth.security", "count": 12}
      ],
      "findings": [],
      "skipped_lines": 0
    },
    "error_reason": null,
    "created_at": "2026-09-28T16:50:00Z",
    "processed_at": "2026-09-28T16:50:03Z",
    "processing_started_at": "2026-09-28T16:50:01Z"
  }
  ```
- **Error Codes:**
  - `404 Not Found`: Ingestion record with given `ingest_id` does not exist.
  - `503 Service Unavailable`: MongoDB unreachable.

---

### 5.4. `GET /logs`
Lists historical log ingestion records sorted newest first (`created_at` descending). Supports filtering and pagination.

- **Query Parameters:**
  - `service_name`: (Optional) Filter by service name.
  - `status`: (Optional) Filter by status (`pending`, `processing`, `completed`, `failed`).
  - `environment`: (Optional) Filter by environment (`dev`, `staging`, `prod`).
  - `limit`: (Optional, default: 50, max: 200) Number of records to return.
  - `skip`: (Optional, default: 0) Number of records to skip.

- **Request:**
  ```http
  GET /logs?service_name=auth-service&status=completed&limit=10 HTTP/1.1
  Host: localhost:8000
  ```
- **Response (200 OK):**
  ```json
  [
    {
      "ingest_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "service_name": "auth-service",
      "environment": "dev",
      "object_key": "raw-logs/auth-service-9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d.jsonl",
      "status": "completed",
      "metrics": { ... },
      "top_error": "Connection reset by peer",
      "report": { ... },
      "error_reason": null,
      "created_at": "2026-09-28T16:50:00Z",
      "processed_at": "2026-09-28T16:50:03Z",
      "processing_started_at": "2026-09-28T16:50:01Z"
    }
  ]
  ```

---

### 5.5. `GET /metrics/summary`
Calculates operational health and aggregated log counts per service across all `completed` jobs using MongoDB aggregation.

- **Query Parameters:**
  - `service_name`: (Optional) Filter for a single service.
  - `from`: (Optional) ISO 8601 start timestamp (`created_at >= from`).
  - `to`: (Optional) ISO 8601 end timestamp (`created_at <= to`).

- **Request:**
  ```http
  GET /metrics/summary HTTP/1.1
  Host: localhost:8000
  ```
- **Response (200 OK):**
  ```json
  [
    {
      "service_name": "auth-service",
      "total_logs": 15000,
      "error_count": 25,
      "warning_count": 120,
      "critical_count": 0,
      "health": "degraded"
    },
    {
      "service_name": "payment-service",
      "total_logs": 8200,
      "error_count": 0,
      "warning_count": 14,
      "critical_count": 0,
      "health": "healthy"
    }
  ]
  ```

---

## 6. Upload Flow Order & Transactional Failure Handling

### Execution Sequence
The upload pipeline enforces a strict sequential order:
```text
Client Upload -> Validation -> MinIO Storage -> MongoDB -> RabbitMQ -> 201 Created
```
**Why this exact order?**
- Enqueuing the message to RabbitMQ *only after* both the raw object in MinIO and the tracking document in MongoDB exist guarantees that the downstream Worker will never pick up a job for a file or database record that does not yet exist.

### Failure Handling & Rollbacks
If any stage fails during the upload pipeline, compensating actions guarantee that no orphaned records or silent hangs occur:

```
[ Step 1 & 2: Validation & UUID Generation ]
       │
       ▼
[ Step 3: S3 / MinIO Upload ] ──(Fails)──> Return HTTP 503; Nothing created in DB or Queue.
       │ (Success)
       ▼
[ Step 4: MongoDB Insert ] ───(Fails)──> Delete uploaded S3 object (best-effort rollback);
       │ (Success)                        Return HTTP 503; Nothing queued.
       ▼
[ Step 5: RabbitMQ Publish ] ──(Fails)──> Atomically mark MongoDB record status='failed'
       │ (Success)                        with error_reason (only if still pending);
       │                                  Return HTTP 503; No job left in 'pending'.
       ▼
[ Step 6: Return HTTP 201 Created ]
```

- **API Modification Invariant:** The Ingestion API never modifies an ingestion document after insertion except for the atomic Step-5 failure fallback. All subsequent status transitions (`processing`, `completed`, `failed`) are owned by the Worker.

---

## 7. Operational Health Rule

Operational health in `/metrics/summary` is computed deterministically from the aggregated error counters:

$$\text{health} = \begin{cases} \mathbf{critical} & \text{if } \text{critical\_count} > 0 \\ \mathbf{degraded} & \text{else if } \text{error\_count} > 0 \\ \mathbf{healthy} & \text{otherwise} \end{cases}$$

---

## 8. Key Engineering & Design Decisions

1. **Synchronous Threadpool Execution (`def` vs `async def`):**
   `pika`, `pymongo`, and `boto3` are synchronous, blocking libraries. Declaring route handlers as standard `def` routes ensures FastAPI dispatches them into an internal AnyIO worker threadpool, preventing event-loop starvation.
2. **RabbitMQ Thread Safety & Publisher Confirms:**
   `pika` connections and channels are **not thread-safe**. Sharing a single channel or connection across concurrent threadpool workers leads to corrupted AMQP frames. The `QueueClient` opens a short-lived connection per publish, declares the queue durable, enables publisher confirmations (`confirm_delivery()`), verifies persistent dispatch, and cleanly closes the connection. This design provides robust thread safety without lock contention.
3. **Streaming Size Enforcement:**
   Rather than loading large uploads into memory with `await file.read()`, the API streams chunks through a `SpooledTemporaryFile` (RAM buffer up to 1 MB, then spooled to disk). If cumulative bytes exceed `MAX_UPLOAD_BYTES`, streaming halts immediately with HTTP 413, defending against DoS attacks.
4. **Lightweight Gzip Verification:**
   For compressed `.gz` uploads, only the magic bytes (`0x1f 0x8b`) and the initial JSON lines are read via a streaming decompressor. The entire compressed file is never unzipped into RAM during validation.
5. **Dependency Injection:**
   All clients, repositories, and services are injected using FastAPI `Depends()`, enabling 100% isolated unit and integration testing via in-memory fakes without live infrastructure.

---

## 9. Open Questions & Repository Alignment

1. **`ingest_id` vs MongoDB `_id`:**
   - *Resolution:* The pipeline standardized on UUID4 strings stored in the `ingest_id` field across MinIO object keys, RabbitMQ payloads, and query parameters. MongoDB's internal `_id` (ObjectId) is explicitly omitted (`{"_id": 0}`) from all API responses to decouple client contracts from database internals.
2. **`.jsonl` Accepted in Addition to `.json`:**
   - *Resolution:* The pipeline accepts both line-delimited JSON (`.jsonl`, `.jsonl.gz`) and standard JSON (`.json`, `.json.gz`).
3. **`GET /logs` Listing & `report` Model Addition:**
   - *Resolution:* The SRS initially focused on single-job status lookup. To support frontend dashboards, `GET /logs` (with pagination and filters) and the Worker's comprehensive `report` object were incorporated into the data model. The SRS should be updated to reflect this.
4. **Metrics Summary Aggregation Ownership:**
   - *Resolution:* While a future dedicated Backend/Analytics service may assume ownership of aggregate reporting, the Ingestion API currently provides `GET /metrics/summary` to immediately unblock dashboard developers.
5. **Environment Defaulting:**
   - *Resolution:* If the optional `environment` field is omitted in `POST /logs/upload`, it defaults to `"dev"`.

---

## 10. Suggested Docker Compose Snippet

To integrate the Ingestion API into the root `docker-compose.yml`, add the following service definition:

```yaml
  log-ingestion-api:
    build:
      context: ./log-ingestion-api/api
      dockerfile: Dockerfile
    container_name: log-ingestion-api
    ports:
      - "8000:8000"
    environment:
      - PORT=8000
      - HOST=0.0.0.0
      - CORS_ORIGINS=*
      - MAX_UPLOAD_BYTES=10485760
      - RABBITMQ_HOST=rabbitmq
      - RABBITMQ_PORT=5672
      - RABBITMQ_USER=guest
      - RABBITMQ_PASSWORD=guest
      - RABBITMQ_QUEUE_NAME=log-ingestion-queue
      - MONGO_URI=mongodb://mongodb:27017
      - MONGO_DB_NAME=log_analytics
      - MONGO_COLLECTION=ingestions
      - S3_ENDPOINT_URL=http://object-storage:9000
      - S3_ACCESS_KEY=minioadmin
      - S3_SECRET_KEY=minioadmin
      - S3_BUCKET_NAME=raw-logs
      - S3_REGION=us-east-1
    depends_on:
      - mongodb
      - object-storage
      - rabbitmq
    restart: unless-stopped
```
