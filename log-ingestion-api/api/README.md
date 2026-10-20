# Log Ingestion API (AWS Lambda edition)

FastAPI application served on **AWS Lambda** through **API Gateway (HTTP API)** using the Mangum ASGI adapter (`lambda_function.handler`).

Flow of `POST /logs/upload`: validate → **S3** `PutObject` → **DynamoDB** `PutItem` (status `pending`) → **SQS** `SendMessage` → `201`. If a step fails, earlier steps are rolled back (S3 object deleted / record marked `failed`).

Configuration (environment variables, set by `template.yaml`): `SQS_QUEUE_URL`, `DDB_TABLE_NAME`, `S3_BUCKET_NAME`, `AWS_REGION`, `MAX_UPLOAD_BYTES` (default 4 MB), `CORS_ORIGINS`. No credentials are configured — Lambda uses its IAM role.

Run unit tests: `pip install -r requirements-dev.txt && python -m pytest`
Run locally (needs `aws configure` + deployed resources): `uvicorn app.main:app --reload` with the variables above exported.
Interactive docs: `<ApiUrl>/docs`.
