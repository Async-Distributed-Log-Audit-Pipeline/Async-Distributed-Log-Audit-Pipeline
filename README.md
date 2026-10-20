# 🚀 Asynchronous Distributed Log & Audit Analytics Pipeline

An event-driven, decoupled distributed system designed to ingest raw application/audit logs from microservices, parse them asynchronously, compute severity metrics, and present real-time analytics via a live dashboard.

Developed for CS32102 Distributed Systems Mini-Project at General Sir John Kotelawala Defence University.

---

## 👥 Team Roles & Responsibilities

| Role | Team Member | Primary Responsibilities |
| :--- | :--- | :--- |
| **Project Lead / Integrator** | THN Dewindi | Team coordination, Repo setup, System Integration, AWS Cost Management |
| **API Developer** | LSY Liyanage | REST API Design (FastAPI), Endpoint logic, Request validation |
| **Backend Dev & DBA** | BASA Wijesekara | Metadata DB Schema (DynamoDB/Mongo), Aggregation queries |
| **Worker / Processing Dev** | AHS Kavinda | SQS/Queue consumer, JSONL Parsing, Idempotency, DLQ handling |
| **Frontend / DevOps** | KLI Sathsarani | Streamlit Dashboard UI, Docker Compose orchestration, Cloud deployment |

---

## 🏗 System Architecture

The pipeline uses an **Event-Driven, Microservice-style Pattern**:

1. **Ingestion Phase (Synchronous):** Client uploads JSONL logs → API saves raw file to Object Storage & DB (Status: `pending`) → API enqueues job to Message Queue → API returns `201 Created` immediately.
2. **Processing Phase (Asynchronous):** Queue triggers Worker → Worker downloads log archive, parses severity levels (INFO, WARN, ERROR, CRITICAL), computes metrics, and updates Metadata DB to `completed` or `failed`.
3. **Analytics Phase:** Dashboard fetches real-time health metrics and top errors from Metadata DB.




[ Client / Dashboard ]
│
▼ (POST /logs/upload)
[ Ingestion API ] ──(Save Raw Log)──► [ Object Storage (S3 / MinIO) ]
│                                         ▲
│ (Enqueue Job)                           │ (Fetch File)
▼                                         │
[ Message Queue (SQS / RabbitMQ) ] ──► [ Worker Pool (Lambda / Python) ]
│
│ (Update Status/Metrics)
▼
[ Metadata DB (DynamoDB / Mongo) ]



---

## 🛠 Technology Stack Mapping

| Layer | Local Prototype (Docker) | Cloud Deployment (AWS) |
| :--- | :--- | :--- |
| **API Server** | FastAPI / Flask | AWS Lambda + API Gateway / EC2 |
| **Object Storage** | MinIO | Amazon S3 |
| **Message Queue** | RabbitMQ | Amazon SQS (with Dead Letter Queue) |
| **Worker Compute** | Python Consumer | AWS Lambda (Event-driven) |
| **Metadata Database** | MongoDB | Amazon DynamoDB |
| **Dashboard UI** | Streamlit | Streamlit / S3 Static Web |

---

## 📌 API Endpoints Summary

* `POST /logs/upload` - Accepts `.json` or `.json.gz` log archive with `service_name` and `environment`. Returns `ingest_id` and status `pending`.
* `GET /logs/status?id={ingest_id}` - Fetches processing status and computed metrics for a single ingestion batch.
* `GET /metrics/summary` - Returns aggregated health metrics, severity breakdowns, and top errors grouped by service.

---

## 🚀 Getting Started (Local Prototype)

### Prerequisites
* Docker Desktop & Docker Compose installed.

### Running Locally

```bash
# 1. Clone the repository
git clone [https://github.com/nikeshala-3258/Async-Distributed-Log-Audit-Pipeline.git](https://github.com/nikeshala-3258/Async-Distributed-Log-Audit-Pipeline.git)
cd Async-Distributed-Log-Audit-Pipeline

# 2. Set up environment variables
cp .env.example .env

# 3. Run with Docker Compose
docker compose up --build -d

# 4. Check container status
docker compose ps

