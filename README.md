# 🚀 Asynchronous Distributed Log & Audit Analytics Pipeline

An event-driven, decoupled distributed system designed to ingest raw application/audit logs from microservices, parse them asynchronously, compute severity metrics, and present real-time analytics via a live dashboard[cite: 14].

Developed for CS32102 Distributed Systems Mini-Project at General Sir John Kotelawala Defence University[cite: 14].

---

## 👥 Team Roles & Responsibilities

| Role | Team Member | Primary Responsibilities |
| :--- | :--- | :--- |
| **Project Lead / Integrator** | THN Dewindi | Team coordination, Repo setup, System Integration, AWS Cost Management[cite: 14] |
| **API Developer** | LSY Liyanage | REST API Design (FastAPI), Endpoint logic, Request validation[cite: 14] |
| **Backend Dev & DBA** | AHS Kavinda | Metadata DB Schema (DynamoDB/Mongo), Aggregation queries[cite: 14] |
| **Worker / Processing Dev** | BASA Wijesekara | SQS/Queue consumer, JSONL Parsing, Idempotency, DLQ handling[cite: 14] |
| **Frontend / DevOps** | KLI Sathsarani | Streamlit Dashboard UI, Docker Compose orchestration, Cloud deployment[cite: 14] |

---

## 🏗 System Architecture

The pipeline uses an **Event-Driven, Microservice-style Pattern**[cite: 14]:
1. **Ingestion Phase (Synchronous):** Client uploads JSONL logs $\rightarrow$ API saves raw file to Object Storage & DB (Status: `pending`) $\rightarrow$ API enqueues job to Message Queue $\rightarrow$ API returns `201 Created` immediately[cite: 14].
2. **Processing Phase (Asynchronous):** Queue triggers Worker $\rightarrow$ Worker downloads log archive, parses severity levels (INFO, WARN, ERROR, CRITICAL), computes metrics, and updates Metadata DB to `completed` or `failed`[cite: 14].
3. **Analytics Phase:** Dashboard fetches real-time health metrics and top errors from Metadata DB[cite: 14].
[ Client / Dashboard ]
│
▼ (POST /logs/upload)
[ Ingestion API ] ──(Save Raw Log)──► [ Object Storage (S3 / MinIO) ]
│                                     ▲
(Enqueue Job)                              │ (Fetch File)
▼                                     │
[ Message Queue (SQS / RabbitMQ) ] ──► [ Worker Pool (Lambda / Python) ]
│
(Update Status/Metrics)
▼
[ Metadata DB (DynamoDB / Mongo) ]
---

## 🛠 Technology Stack Mapping

| Layer | Local Prototype (Docker) | Cloud Deployment (AWS) |
| :--- | :--- | :--- |
| **API Server** | FastAPI / Flask | AWS Lambda + API Gateway / EC2[cite: 14] |
| **Object Storage** | MinIO[cite: 14] | Amazon S3[cite: 14] |
| **Message Queue** | RabbitMQ[cite: 14] | Amazon SQS (with Dead Letter Queue)[cite: 14] |
| **Worker Compute** | Python Consumer | AWS Lambda (Event-driven)[cite: 14] |
| **Metadata Database** | MongoDB[cite: 14] | Amazon DynamoDB[cite: 14] |
| **Dashboard UI** | Streamlit[cite: 14] | Streamlit / S3 Static Web |

---

## 📌 API Endpoints Summary

* `POST /logs/upload` - Accepts `.json` or `.json.gz` log archive with `service_name` and `environment`. Returns `ingest_id` and status `pending`[cite: 14].
* `GET /logs/status?id={ingest_id}` - Fetches processing status and computed metrics for a single ingestion batch[cite: 14].
* `GET /metrics/summary` - Returns aggregated health metrics, severity breakdowns, and top errors grouped by service[cite: 14].

---

## 🚀 Getting Started (Local Prototype)

### Prerequisites
* Docker Desktop & Docker Compose installed.

### Running Locally
```bash
# 1. Clone the repository
git clone [https://github.com/nikeshala-3258/Async-Distributed-Log-Audit-Pipeline.git](https://github.com/nikeshala-3258/Async-Distributed-Log-Audit-Pipeline.git)
cd Async-Distributed-Log-Audit-Pipeline

# 2. Run with Docker Compose
docker-compose up --build



