# 🚀 Asynchronous Distributed Log & Audit Analytics Pipeline

An event-driven, decoupled distributed system that ingests raw application/audit logs from microservices, parses them **asynchronously**, computes severity metrics and shows live analytics on a dashboard.

Built for the **CS32102 Distributed Systems Mini-Project** — General Sir John Kotelawala Defence University.

The same architecture is delivered in **two deployments**:

| | 🐳 Docker (local prototype) | ☁️ AWS (cloud deployment) |
| :--- | :--- | :--- |
| Where | repository root | [`aws/`](aws/) folder |
| API | FastAPI container | FastAPI on **Lambda** + **API Gateway** |
| Object storage | MinIO | **Amazon S3** |
| Message queue | RabbitMQ (+ dead-letter queue) | **Amazon SQS** (+ dead-letter queue) |
| Worker | Python consumer container | **Lambda** triggered by SQS |
| Metadata DB | MongoDB | **DynamoDB** |
| Dashboard | Streamlit container | Streamlit Cloud / EC2 / Local |
| Run with | `docker compose up --build -d` | `sam deploy` — see [`aws/DEPLOY_AWS.md`](aws/DEPLOY_AWS.md) |

---

## 📊 Live Dashboards

*   **Cloud Deployment (Streamlit Community Cloud):** [https://async-distributed-log-audit-pipeline-6nuqu4le73zbavvntefnwp.streamlit.app/](https://async-distributed-log-audit-pipeline-6nuqu4le73zbavvntefnwp.streamlit.app/)
*   **Local Deployment:** `http://localhost:8501` (when running via Docker Compose)

---

## 👥 Team Roles & Responsibilities

| Role | Team Member | Primary Responsibilities |
| :--- | :--- | :--- |
| **Project Lead / Integrator** | THN Dewindi | Team coordination, repo setup, system integration, AWS cost management |
| **API Developer** | LSY Liyanage | REST API design (FastAPI), endpoint logic, request validation |
| **Backend Dev & DBA** | BASA Wijesekara | Metadata DB schema (MongoDB / DynamoDB), aggregation queries |
| **Worker / Processing Dev** | AHS Kavinda | Queue consumer, JSONL parsing, idempotency, DLQ handling |
| **Frontend / DevOps** | KLI Sathsarani | Streamlit dashboard, Docker Compose, AWS deployment & monitoring |

---

## 🏗 Architecture

1. **Ingestion (synchronous):** client uploads a log file → API validates it → stores the raw file in **object storage** → inserts a `pending` record in the **metadata DB** → publishes a job to the **queue** → returns `201 Created` immediately.
2. **Processing (asynchronous):** a **worker** takes the job, downloads the file, parses severity levels (INFO / WARN / ERROR / CRITICAL), computes metrics and a report, and sets the record to `completed` or `failed`.
3. **Analytics:** the **dashboard** reads status, history and per-service health from the API.
Dashboard (Streamlit)
│  HTTP
▼
Ingestion API (FastAPI) ──1) raw file──► Object storage   (MinIO  |  S3)
│  ──2) pending record──────────► Metadata DB      (MongoDB | DynamoDB)
│  ──3) job message──► Queue (RabbitMQ | SQS) ──► Worker (container | Lambda)
▼                            │                │ download file,
201 {ingest_id, status: pending}            ▼                │ parse, compute metrics
Dead-letter queue        ▼
update status/metrics in Metadata DB
### Reliability features (both deployments)
- **Decoupling** — the API never waits for parsing; each component deploys and scales independently.
- **Idempotency** — status changes are conditional (`pending|processing → completed|failed`), so duplicate deliveries are skipped and a finished record never regresses.
- **Retries with exponential backoff + jitter** for transient failures (storage/DB outage), up to `MAX_RETRIES=3`, then **dead-letter queue** and the record is marked `failed`.
- **Permanent errors** (corrupt / unparseable file) → `failed` immediately with a reason, no retries.
- **Rollback on partial failure** — S3/MinIO object is deleted if the DB write fails; the record is marked `failed` if queuing fails.
- **Validation** — file extension, size cap (streamed), service-name sanitising, gzip/JSON sanity check.

---

## 📌 API Endpoints

| Method & path | Description |
| :--- | :--- |
| `POST /logs/upload` | multipart: `file` (`.json`, `.jsonl`, `.json.gz`, `.jsonl.gz`), `service_name`, `environment` → `201 {ingest_id, status:"pending"}` |
| `GET /logs/status?id={ingest_id}` | status, metrics, top error and report of one batch (`404` if unknown) |
| `GET /logs` | history, newest first; filters `service_name`, `status`, `environment`; paging `limit` (≤ 200), `skip` |
| `GET /metrics/summary` | per-service totals and health; filters `service_name`, `from`, `to` |
| `GET /health` | liveness probe |
| `GET /docs` | interactive Swagger UI |

Health rule: `critical` if any CRITICAL logs → else `degraded` if any ERROR → else `warning` if any WARN → else `healthy`.
Upload limits: **10 MB** on Docker, **4 MB** on AWS (API Gateway + Lambda request limit).

Example:
```bash
curl -F "file=@sample.jsonl" -F "service_name=auth-service" -F "environment=dev" http://localhost:8000/logs/upload
curl "http://localhost:8000/logs/status?id=<ingest_id>"
curl http://localhost:8000/metrics/summary
Expected log line format (one JSON object per line):JSON{"@timestamp":"2026-10-20T09:00:09Z","level":"ERROR","message":"Connection refused to database host","logger_name":"demo.db"}
🐳 Option 1 — Run locally with DockerPrerequisite: Docker Desktop with Docker Compose.Bashgit clone [https://github.com/](https://github.com/)<your-user>/Async-Distributed-Log-Audit-Pipeline.git
cd Async-Distributed-Log-Audit-Pipeline
docker compose up --build -d       # starts RabbitMQ, MongoDB, MinIO, API, worker, dashboard
docker compose ps                  # all services should be "running" / "healthy"
ServiceURLDashboardhttp://localhost:8501API Swagger UIhttp://localhost:8000/docsRabbitMQ consolehttp://localhost:15672 (guest / guest)MinIO consolehttp://localhost:9001 (minioadmin / minioadmin)Useful commands:Bashdocker compose logs -f log-worker                      # watch the worker process jobs
docker compose up -d --scale log-worker=2              # run two worker replicas
docker compose run --rm db-init python seed_services.py # optional demo data
docker compose down                                    # stop (add -v to delete stored data)
The first start builds all images and applies the MongoDB schema/indexes and creates the raw-logs bucket automatically (db-init). Settings are in docker-compose.yml; copy .env.example to .env only when running a component outside Docker.☁️ Option 2 — Deploy to AWSEverything lives in aws/ and is created by one SAM/CloudFormation stack: API Gateway, 2 Lambda functions, SQS + DLQ, DynamoDB, IAM roles, CloudWatch logs/dashboard/alarm. S3 uses your existing bucket.Bashcd aws
./build.sh                          # packages the two Lambda functions (no Docker needed)
sam deploy --stack-name log-audit-pipeline --region us-east-1 --capabilities CAPABILITY_IAM \
  --resolve-s3 --no-confirm-changeset --parameter-overrides BucketName=<your-bucket>
./scripts/smoke_test.sh <ApiUrl>    # upload → worker → completed → metrics
Full step-by-step (CloudShell, dashboard on EC2, failure demos, clean-up): aws/DEPLOY_AWS.md.AWS-specific architecture, monitoring and free-tier cost report: aws/README.md.Security: the Lambdas use IAM roles — never commit access keys. If a key was ever shared in chat or committed, delete it in IAM and create a new one.🧪 TestingBash# Docker version
(cd log-ingestion-api/api && pip install -r requirements.txt && python -m pytest)   # API unit tests (in-memory fakes)
(cd log-worker && pip install -r requirements-dev.txt && python -m pytest)          # worker unit tests
(cd db && pip install -r requirements.txt && python -m pytest)                      # aggregation tests

# AWS version (no AWS account needed: S3/SQS/DynamoDB are emulated)
cd aws
pip install -r log-ingestion-api/api/requirements-dev.txt -r log-worker/requirements-dev.txt
(cd log-ingestion-api/api && python -m pytest)
(cd log-worker && python -m pytest)
python scripts/e2e_moto_test.py       # full pipeline: upload, worker, duplicates, retries, DLQ, metrics
📂 Repository Structure.
├── docker-compose.yml          # Docker deployment: whole stack
├── log-ingestion-api/api/      # FastAPI ingestion API (RabbitMQ / MongoDB / MinIO)
├── log-worker/                 # Queue consumer, parser, analytics, retry policy
├── db/                         # MongoDB schema, indexes, aggregations, seed scripts
├── dashboard/                  # Streamlit dashboard
├── infra/                      # Dashboard-only compose (demo mode)
├── docs/                       # Data-layer documentation
├── log sources/                # Sample microservices that produce test logs
└── aws/                        # AWS deployment (self-contained)
    ├── template.yaml           #   SAM / CloudFormation stack
    ├── build.sh                #   builds the Lambda packages
    ├── DEPLOY_AWS.md           #   step-by-step guide
    ├── log-ingestion-api/api/  #   API on Lambda (S3 / SQS / DynamoDB)
    ├── log-worker/             #   worker Lambda (SQS-triggered)
    ├── dashboard/              #   dashboard (AWS-tuned timeouts / limits)
    └── scripts/                #   e2e (moto) test and deployed smoke test
💰 AWS Cost Report (free-tier usage)ServiceConfigurationExpected usageFree allowanceLambda (2 functions)512 MB / 256 MB, Python 3.12< 5 000 invocations/month1 M requests + 400 000 GB-sAPI Gateway (HTTP API)1 API< 5 000 calls/month1 M calls/month (12 months)SQS (queue + DLQ)standard, encrypted< 20 000 requests/month1 M requests/monthDynamoDBprovisioned 5 RCU/5 WCU on table + 2 indexes (15/15 total)< 1 MB data25 RCU/25 WCU, 25 GBS31 bucket, SSE-S3< 100 MB5 GB (12 months)CloudWatch2 log groups (14 days), 1 dashboard, 1 alarm–5 GB logs, 3 dashboards, 10 alarmsEC2 (dashboard only)1 × t3.micro, stopped when idle≤ 750 h750 h/month (12 months / free-plan credits)Estimated monthly cost ≈ $0. Set a billing budget alert and delete the stack (sam delete) after grading.⚠️ Known LimitationsThe API has no authentication (add an API Gateway authorizer / API key for production).AWS uploads are limited to ~4 MB; larger files would use S3 pre-signed URLs.The dashboard on EC2 is served over HTTP; use CloudFront/ALB for HTTPS.Dashboard and parser code is duplicated between the root and aws/ folders so each deployment stays self-contained.
