"""
End-to-end test of the whole AWS pipeline WITHOUT touching real AWS (uses `moto` to emulate S3, SQS, DynamoDB).

    pip install -r log-ingestion-api/api/requirements-dev.txt -r log-worker/requirements-dev.txt
    python scripts/e2e_moto_test.py

It exercises: upload -> S3 + DynamoDB(pending) + SQS -> worker Lambda handler -> DynamoDB(completed),
plus idempotent duplicate delivery, permanent failure, retry -> DLQ, listing/filtering and metrics.
"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "log-ingestion-api", "api"))
sys.path.insert(0, os.path.join(ROOT, "log-worker"))

os.environ.update({
    "AWS_ACCESS_KEY_ID": "testing", "AWS_SECRET_ACCESS_KEY": "testing", "AWS_DEFAULT_REGION": "us-east-1",
    "AWS_REGION": "us-east-1", "DDB_TABLE_NAME": "log-ingestions", "S3_BUCKET_NAME": "test-bucket",
    "MAX_RETRIES": "2", "RETRY_BASE_DELAY_SECONDS": "1", "MAX_SKIPPED_RATIO": "0.5",
})

import boto3
from moto import mock_aws


def create_infra():
    region = "us-east-1"
    boto3.client("s3", region_name=region).create_bucket(Bucket="test-bucket")
    sqs = boto3.client("sqs", region_name=region)
    dlq = sqs.create_queue(QueueName="log-ingestion-dlq")["QueueUrl"]
    q = sqs.create_queue(QueueName="log-ingestion-queue", Attributes={"VisibilityTimeout": "30"})["QueueUrl"]
    os.environ["SQS_QUEUE_URL"], os.environ["QUEUE_URL"], os.environ["DLQ_URL"] = q, q, dlq
    ddb = boto3.client("dynamodb", region_name=region)
    ddb.create_table(
        TableName="log-ingestions", BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[{"AttributeName": n, "AttributeType": "S"} for n in ("ingest_id", "entity", "status", "created_at")],
        KeySchema=[{"AttributeName": "ingest_id", "KeyType": "HASH"}],
        GlobalSecondaryIndexes=[
            {"IndexName": "entity-created_at-index", "Projection": {"ProjectionType": "ALL"},
             "KeySchema": [{"AttributeName": "entity", "KeyType": "HASH"}, {"AttributeName": "created_at", "KeyType": "RANGE"}]},
            {"IndexName": "status-created_at-index", "Projection": {"ProjectionType": "ALL"},
             "KeySchema": [{"AttributeName": "status", "KeyType": "HASH"}, {"AttributeName": "created_at", "KeyType": "RANGE"}]},
        ],
    )
    return sqs, q, dlq


def drain_as_lambda_event(sqs, queue_url):
    """Receive messages like the SQS->Lambda poller does and wrap them in an event."""
    resp = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10, AttributeNames=["All"], WaitTimeSeconds=0, VisibilityTimeout=30)
    recs = [{"messageId": m["MessageId"], "receiptHandle": m["ReceiptHandle"], "body": m["Body"],
             "attributes": m.get("Attributes", {})} for m in resp.get("Messages", [])]
    return {"Records": recs}


LOGS = "\n".join([
    '{"@timestamp":"2026-09-26T14:40:00Z","level":"INFO","message":"started","logger_name":"svc.a"}',
    '{"@timestamp":"2026-09-26T14:41:00Z","level":"ERROR","message":"Connection refused to db","logger_name":"svc.a"}',
    '{"@timestamp":"2026-09-26T14:42:00.9615012+05:30","level":"ERROR","message":"Connection refused to db","logger_name":"svc.a"}',
    '{"@timestamp":"2026-09-26T14:43:00Z","level":"WARN","message":"slow","logger_name":"svc.b"}',
    '{"@timestamp":"2026-09-26T14:44:00Z","level":"FATAL","message":"out of memory","logger_name":"svc.b"}',
]).encode()


@mock_aws
def main():
    sqs, queue_url, dlq_url = create_infra()

    from fastapi.testclient import TestClient
    from app.main import app
    import lambda_function as worker  # log-worker/lambda_function.py

    client = TestClient(app)

    # 1. Upload -> 201 pending
    r = client.post("/logs/upload", files={"file": ("a.jsonl", io.BytesIO(LOGS))}, data={"service_name": "payments", "environment": "prod"})
    assert r.status_code == 201, r.text
    ingest_id = r.json()["ingest_id"]
    assert r.json()["status"] == "pending"
    st = client.get("/logs/status", params={"id": ingest_id}).json()
    assert st["status"] == "pending" and st["metrics"] is None
    print("PASS 1  upload accepted -> pending record + S3 object + SQS message")

    # 2. Worker processes message
    event = drain_as_lambda_event(sqs, queue_url)
    assert len(event["Records"]) == 1
    assert worker.handler(event, None) == {"batchItemFailures": []}
    st = client.get("/logs/status", params={"id": ingest_id}).json()
    assert st["status"] == "completed", st
    assert st["metrics"]["total_logs"] == 5 and st["metrics"]["error_count"] == 2
    assert st["metrics"]["critical_count"] == 1 and st["metrics"]["warning_count"] == 1
    assert st["processed_at"] and st["processing_started_at"]
    print("PASS 2  worker completed job, metrics =", {k: v for k, v in st["metrics"].items() if v})

    # 3. Idempotency: duplicate delivery of the same message must not change anything
    dup_event = {"Records": [{**event["Records"][0], "attributes": {"ApproximateReceiveCount": "2"}}]}
    before = client.get("/logs/status", params={"id": ingest_id}).json()
    assert worker.handler(dup_event, None) == {"batchItemFailures": []}
    assert client.get("/logs/status", params={"id": ingest_id}).json() == before
    print("PASS 3  duplicate delivery is idempotent (status stays completed, nothing rewritten)")

    # 4. Permanent failure: mostly-garbage file -> failed, message ACKed
    bad = b'{"level":"INFO","message":"ok"}\nnot json\nnot json\nnot json\n'
    bid = client.post("/logs/upload", files={"file": ("b.jsonl", io.BytesIO(bad))}, data={"service_name": "auth"}).json()["ingest_id"]
    res = worker.handler(drain_as_lambda_event(sqs, queue_url), None)
    assert res == {"batchItemFailures": []}
    st = client.get("/logs/status", params={"id": bid}).json()
    assert st["status"] == "failed" and "Skipped lines ratio" in st["error_reason"], st
    print("PASS 4  corrupt file -> status failed with reason, message not retried")

    # 5. Retry then DLQ: transient storage outage (object bucket missing) exhausts retries
    cid = client.post("/logs/upload", files={"file": ("c.jsonl", io.BytesIO(LOGS))}, data={"service_name": "orders"}).json()["ingest_id"]
    s3 = boto3.client("s3", region_name="us-east-1")
    real_download = worker._storage.s3_client.download_file
    def broken(*a, **k):
        from botocore.exceptions import EndpointConnectionError
        raise EndpointConnectionError(endpoint_url="https://s3.amazonaws.com")
    worker._storage.s3_client.download_file = broken
    for attempt in (1, 2, 3):                       # MAX_RETRIES=2 -> 3rd delivery goes to DLQ
        ev = drain_as_lambda_event(sqs, queue_url)
        if not ev["Records"]:                       # message hidden by backoff visibility timeout: simulate expiry
            msgs = sqs.receive_message(QueueUrl=queue_url, VisibilityTimeout=0)
            raise AssertionError("message not redelivered")
        ev["Records"][0]["attributes"]["ApproximateReceiveCount"] = str(attempt)
        res = worker.handler(ev, None)
        if attempt < 3:
            assert len(res["batchItemFailures"]) == 1, f"attempt {attempt} should request redelivery"
            # emulate visibility timeout expiring so the next loop can receive it again
            sqs.change_message_visibility(QueueUrl=queue_url, ReceiptHandle=ev["Records"][0]["receiptHandle"], VisibilityTimeout=0)
        else:
            assert res == {"batchItemFailures": []}
    worker._storage.s3_client.download_file = real_download
    dlq_msgs = sqs.receive_message(QueueUrl=dlq_url, MessageAttributeNames=["All"]).get("Messages", [])
    assert len(dlq_msgs) == 1 and dlq_msgs[0]["MessageAttributes"]["failure_type"]["StringValue"] == "retries_exhausted"
    st = client.get("/logs/status", params={"id": cid}).json()
    assert st["status"] == "failed" and "retry attempts" in st["error_reason"], st
    print("PASS 5  transient errors retried with backoff, then dead-lettered + record marked failed")

    # 6. Invalid message -> DLQ immediately
    sqs.send_message(QueueUrl=queue_url, MessageBody="this is not json")
    assert worker.handler(drain_as_lambda_event(sqs, queue_url), None) == {"batchItemFailures": []}
    types = [m["MessageAttributes"]["failure_type"]["StringValue"] for m in sqs.receive_message(QueueUrl=dlq_url, MaxNumberOfMessages=10, MessageAttributeNames=["All"], VisibilityTimeout=0).get("Messages", [])]
    assert "invalid_message" in types
    print("PASS 6  malformed message dead-lettered immediately")

    # 7. Listing, filters, pagination, metrics
    allrows = client.get("/logs").json()
    assert [x["ingest_id"] for x in allrows][0] == cid and len(allrows) == 3          # newest first
    assert len(client.get("/logs", params={"status": "completed"}).json()) == 1
    assert len(client.get("/logs", params={"service_name": "auth"}).json()) == 1
    assert len(client.get("/logs", params={"limit": 1, "skip": 1}).json()) == 1
    summary = client.get("/metrics/summary").json()
    assert summary == [{"service_name": "payments", "total_logs": 5, "error_count": 2, "warning_count": 1, "critical_count": 1, "health": "critical"}], summary
    assert client.get("/metrics/summary", params={"service_name": "nope"}).json() == []
    assert client.get("/metrics/summary", params={"from": "2999-01-01T00:00:00Z"}).json() == []
    print("PASS 7  list (newest-first, filters, pagination) and /metrics/summary correct")

    # 8. Validation errors
    assert client.post("/logs/upload", files={"file": ("x.txt", io.BytesIO(b"hi"))}, data={"service_name": "a"}).status_code == 400
    assert client.get("/logs/status", params={"id": "missing"}).status_code == 404
    print("PASS 8  validation (bad extension 400, unknown id 404)")
    print("\nALL END-TO-END CHECKS PASSED")


if __name__ == "__main__":
    main()
