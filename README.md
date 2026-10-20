# 🚀 Asynchronous Distributed Log & Audit Analytics Pipeline — AWS Edition

An event-driven, decoupled distributed system that ingests raw application/audit logs, parses them asynchronously, computes severity metrics and shows live analytics on a dashboard.
CS32102 Distributed Systems Mini-Project — General Sir John Kotelawala Defence University.

The system was first built as a local Docker Compose prototype (FastAPI + RabbitMQ + MongoDB + MinIO + Python worker) and is now **migrated to AWS**. The local version is preserved in git history (tag it `local-prototype` before merging this change).

## 👥 Team Roles
| Role | Team Member | Responsibilities |
| :--- | :--- | :--- |
| Project Lead / Integrator | THN Dewindi | Coordination, integration, AWS cost management |
| API Developer | LSY Liyanage | REST API (FastAPI), validation |
| Backend Dev & DBA | BASA Wijesekara | DynamoDB table/index design, aggregations |
| Worker / Processing Dev | AHS Kavinda | SQS-triggered Lambda, parsing, idempotency, DLQ |
| Frontend / DevOps | KLI Sathsarani | Streamlit dashboard, deployment (SAM/CloudFormation), monitoring |

## 🏗 Architecture

```
 Dashboard (Streamlit, EC2 or local)
        │  HTTPS
        ▼
 API Gateway (HTTP API) ──► Lambda: log-ingestion-api (FastAPI + Mangum)
                                │ 1) PutObject            │ 2) PutItem (pending)     │ 3) SendMessage
                                ▼                         ▼                          ▼
                          Amazon S3                  DynamoDB table            SQS: log-ingestion-queue ──(redrive after 5 receives)──► SQS DLQ
                       (raw log files)             log-ingestions                    │  event source mapping
                                ▲                         ▲                          ▼
                                └──── GetObject ──────────┴──── conditional ──── Lambda: log-worker
                                                              updates (status, metrics)
```

| Layer | Local prototype | AWS (this repo) |
| :--- | :--- | :--- |
| API | FastAPI + uvicorn | FastAPI on **Lambda** behind **API Gateway (HTTP API)** via Mangum |
| Object storage | MinIO | **Amazon S3** |
| Queue | RabbitMQ (+ DLQ queue) | **Amazon SQS** + dead-letter queue |
| Worker | Python consumer loop | **Lambda** triggered by SQS (partial-batch failure reporting) |
| Metadata DB | MongoDB | **DynamoDB** (2 GSIs) |
| Dashboard | Streamlit container | Streamlit container on **EC2** (or on your PC) |
| Monitoring | – | **CloudWatch** logs, dashboard `log-audit-pipeline`, DLQ alarm |
| Credentials | static keys in compose | **IAM execution roles** (no keys in code) |

## 🛡 Reliability design
* **Decoupling:** API returns `201 pending` right after S3 + DynamoDB + SQS writes; processing is fully asynchronous.
* **Idempotency:** every worker state change is a DynamoDB *conditional write* (`pending|processing → …`); duplicate SQS deliveries are skipped and terminal states never regress.
* **Retries:** transient errors (S3/DynamoDB outage) → exponential backoff with jitter via SQS visibility timeout, up to `MAX_RETRIES=3`, then the message goes to the **DLQ** and the record is marked `failed`. Permanent errors (corrupt file) → `failed` immediately, not retried. Crashes/timeouts → SQS `maxReceiveCount=5` redrive to the DLQ.
* **Rollback on partial failure:** S3 object deleted if the DB write fails; record marked `failed` if the queue publish fails.

## 📌 API
| Method & path | Description |
| :--- | :--- |
| `POST /logs/upload` | multipart: `file` (`.json/.jsonl/.json.gz/.jsonl.gz`, ≤ 4 MB), `service_name`, `environment` → `201 {ingest_id, status:"pending"}` |
| `GET /logs/status?id=` | status + metrics + report of one batch |
| `GET /logs` | list newest-first; filters `service_name`, `status`, `environment`; `limit`, `skip` |
| `GET /metrics/summary` | per-service totals + health (`critical` > `degraded` > `warning` > `healthy`); filters `service_name`, `from`, `to` |
| `GET /health` | liveness |
| `GET /docs` | Swagger UI |

## ☁️ Deploy to AWS
**Follow [`DEPLOY_AWS.md`](DEPLOY_AWS.md)** (step-by-step, ~20 minutes, no local installs needed — uses AWS CloudShell).

Short version: `./build.sh` → `sam deploy …` → open the printed `ApiUrl` → run the dashboard pointing at it.

## 🧪 Tests
```bash
pip install -r log-ingestion-api/api/requirements-dev.txt -r log-worker/requirements-dev.txt
(cd log-ingestion-api/api && python -m pytest)      # 29 API unit tests
(cd log-worker && python -m pytest)                 # 24 worker unit tests
python scripts/e2e_moto_test.py                     # full pipeline against emulated S3/SQS/DynamoDB (no AWS account needed)
./scripts/smoke_test.sh https://<api-id>.execute-api.us-east-1.amazonaws.com   # against the real deployment
```

## 💰 Cloud cost report (free-tier usage)
| Service | Configuration | Expected usage for the project | Free allowance |
| :--- | :--- | :--- | :--- |
| Lambda (2 functions) | 512 MB / 256 MB, python3.12 | < 5 000 invocations/month | 1 M requests + 400 000 GB-s always free |
| API Gateway HTTP API | 1 API, `$default` stage | < 5 000 calls/month | 1 M calls/month (first 12 months) |
| SQS (queue + DLQ) | standard queues, SSE | < 20 000 requests/month | 1 M requests/month always free |
| DynamoDB | provisioned 5 RCU / 5 WCU on table and on each of 2 GSIs (15 + 15 total), < 1 MB data | – | 25 RCU + 25 WCU and 25 GB always free |
| S3 | 1 bucket, SSE-S3, < 100 MB | – | 5 GB (first 12 months) |
| CloudWatch | 2 log groups (14-day retention), 1 dashboard, 1 alarm | – | 5 GB logs, 3 dashboards, 10 alarms free |
| EC2 (dashboard only) | 1 × t3.micro (free-tier eligible), stop when not demoing | ≤ 750 h | 750 h/month (first 12 months / free-plan credits) |

Estimated monthly cost: **≈ $0**. Always check the AWS Billing console; set a budget alert (see DEPLOY_AWS.md, step 1).
