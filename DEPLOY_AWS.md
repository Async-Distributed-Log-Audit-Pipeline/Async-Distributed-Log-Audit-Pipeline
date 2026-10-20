# Deploying to AWS — step by step

Everything is created by one CloudFormation/SAM stack (`template.yaml`): API Gateway, 2 Lambdas, SQS + DLQ, DynamoDB, IAM roles, CloudWatch logs/dashboard/alarm.
S3 is your existing bucket **`async-log-audit-bucket-nikeshala`** (region **us-east-1**).

> ### ⚠️ Step 0 — Secure your access keys (do this first)
> The access key you pasted into chat (`AKIA4IYK…`) must be treated as **compromised**.
> 1. AWS Console → **IAM → Users → your user → Security credentials → Access keys** → **Deactivate**, then **Delete** it.
> 2. This guide **does not need access keys at all**: AWS CloudShell runs with your console login.
> 3. Never put keys in code, `.env` files that get committed, README files, or chat. The Lambdas use IAM roles instead.
> 4. Also enable MFA on the account, and never use the root user for daily work.

---

## Step 1 — Prepare the account (5 min)
1. Sign in to the AWS Console. In the top-right region selector choose **US East (N. Virginia) `us-east-1`** and keep it for everything.
2. **Budget alert:** search **Billing → Budgets → Create budget → Zero spend budget** (or monthly $5) and enter your email.
3. **Check the S3 bucket:** S3 → `async-log-audit-bucket-nikeshala` → *Permissions* tab → **Block all public access = On**; *Properties* → Default encryption = SSE-S3.
   If the bucket does not exist yet: S3 → **Create bucket**, name `async-log-audit-bucket-nikeshala`, region us-east-1, leave *Block all public access* ticked.

## Step 2 — Open CloudShell and upload the project (3 min)
1. Click the **CloudShell icon** (`>_`) in the top bar (next to the search box). Wait for the prompt.
2. **Actions → Upload file** → choose the project zip (the one that contains `template.yaml`, `build.sh`, …).
3. Run:
   ```bash
   unzip -o Async-Distributed-Log-Audit-Pipeline*.zip -d app && cd app/Async-Distributed-Log-Audit-Pipeline
   ls            # you should see template.yaml  build.sh  DEPLOY_AWS.md ...
   sam --version || pip3 install --user aws-sam-cli     # SAM is normally pre-installed in CloudShell
   ```

## Step 3 — Build the Lambda packages (1 min)
```bash
./build.sh
```
This downloads Linux/Python-3.12 dependencies into `build/api` and `build/worker` (no Docker required).

## Step 4 — Deploy the stack (3–5 min)
```bash
sam deploy \
  --stack-name log-audit-pipeline \
  --region us-east-1 \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --no-confirm-changeset \
  --parameter-overrides BucketName=async-log-audit-bucket-nikeshala
```
When it finishes, print the outputs:
```bash
aws cloudformation describe-stacks --stack-name log-audit-pipeline --region us-east-1 \
  --query "Stacks[0].Outputs[].[OutputKey,OutputValue]" --output table
```
Copy **`ApiUrl`** (looks like `https://abc123.execute-api.us-east-1.amazonaws.com`).

*If the deploy fails:* open **CloudFormation → Stacks → log-audit-pipeline → Events** and read the first red line. If the stack is in `ROLLBACK_COMPLETE`, run `sam delete --stack-name log-audit-pipeline --region us-east-1` and deploy again.

## Step 5 — Smoke-test the cloud system (2 min)
```bash
./scripts/smoke_test.sh <ApiUrl>
```
Expected: health `ok` → upload `201 pending` → status turns `completed` within a few seconds → metrics summary printed → **SMOKE TEST PASSED**.
Also open `<ApiUrl>/docs` in a browser for the Swagger UI.

Verify each AWS piece in the console (useful screenshots for your report):
| Service | Where to look | What you should see |
| --- | --- | --- |
| S3 | bucket → `raw-logs/` | uploaded `.jsonl` object |
| DynamoDB | Tables → `log-ingestions` → *Explore table items* | record with `status = completed`, `metrics`, `report` |
| SQS | Queues → `log-ingestion-queue` | messages available ≈ 0 (consumed); DLQ empty |
| Lambda | `log-worker` → *Monitor* → *View CloudWatch logs* | `Processing COMPLETED successfully` |
| CloudWatch | Dashboards → `log-audit-pipeline` | queue depth, invocations, errors, duration |

## Step 6 — Run the dashboard
**Option A — on your own PC (fastest, good for the demo video):**
```bash
cd dashboard
docker build -t log-dashboard .
docker run --rm -p 8501:8501 -e API_BASE_URL=<ApiUrl> -e DEMO_MODE=false log-dashboard
```
Open http://localhost:8501.

**Option B — on AWS EC2 (so the whole system is in the cloud):**
1. Push this project to GitHub (see Step 9), or be ready to `scp` the `dashboard/` folder.
2. EC2 → **Launch instance** → name `log-dashboard` → **Amazon Linux 2023** → instance type **t3.micro** (the one marked *Free tier eligible*) → create/choose a key pair → Network settings: *Create security group*, add rule **Custom TCP 8501, Source = My IP** (not 0.0.0.0/0).
3. *Advanced details → User data*, paste (edit the two values):
   ```bash
   #!/bin/bash
   dnf install -y docker git
   systemctl enable --now docker
   git clone https://github.com/<your-user>/Async-Distributed-Log-Audit-Pipeline.git /opt/app
   cd /opt/app/dashboard
   docker build -t log-dashboard .
   docker run -d --restart unless-stopped -p 8501:8501 -e API_BASE_URL=<ApiUrl> -e DEMO_MODE=false log-dashboard
   ```
   (Repo must be public for `git clone`; otherwise connect with *EC2 Instance Connect* and `scp`/copy the `dashboard` folder instead.)
4. Launch, wait ~3 minutes, open `http://<instance-public-IPv4>:8501`.
5. **Stop the instance** (Instance state → Stop) when you are not demoing, to stay inside the free tier.

## Step 7 — Demonstrate reliability for the viva
| Demo | How | Expected result |
| --- | --- | --- |
| Async processing | Upload a file in the dashboard | instant `pending`, then `completed` |
| Idempotency | SQS → `log-ingestion-queue` → *Send and receive messages* → resend the same JSON body (`{"ingest_id":"<id>","service_name":"x","object_key":"<key>"}`) | worker logs `Duplicate delivery skipped`; record unchanged |
| Permanent failure | Upload a file whose lines are mostly not JSON | status `failed`, `error_reason` explains why, no retries |
| Retry → DLQ | Lambda → `log-worker` → *Configuration → Environment variables* → change `S3_BUCKET_NAME` to `wrong-bucket` and save. Upload a file. Then **restore the correct bucket name**. | storage errors are *transient*: worker retries with back-off (2 s, 4 s …), then the message lands in **`log-ingestion-dlq`**, the record becomes `failed` ("Processing failed after 3 retry attempts"), and alarm `log-ingestion-dlq-not-empty` fires |
| Invalid message | Send body `hello` to the queue | goes straight to the DLQ (`failure_type=invalid_message`) |
| Scalability | `for i in $(seq 1 30); do curl -s -F file=@sample.jsonl -F service_name=load$i <ApiUrl>/logs/upload; done` | Lambda scales out (max 5 concurrent workers), queue drains, all 30 `completed` |

## Step 8 — Updating the code later
Edit code → in CloudShell (re-upload the zip, or `git pull`) → `./build.sh` → run the same `sam deploy` command. Only changed resources are updated.

## Step 9 — Git hygiene
```bash
git tag local-prototype            # in your old repo, before merging
git checkout -b aws-cloud
# copy this project's files over the repo, then:
git add -A && git status           # check: no .env, no keys, no build/ folder
git commit -m "Migrate pipeline to AWS (S3, SQS, DynamoDB, Lambda, API Gateway)"
git push -u origin aws-cloud
```

## Step 10 — Clean up (after grading, to avoid charges)
```bash
sam delete --stack-name log-audit-pipeline --region us-east-1      # removes API, Lambdas, SQS, DynamoDB, logs
aws s3 rm s3://async-log-audit-bucket-nikeshala --recursive         # optional: empty your bucket
```
Terminate the EC2 instance and delete any unused security groups/key pairs.

---

### Known limitations (mention in the report)
* The API is public (no authentication). For production add an API Gateway JWT/Lambda authorizer or API key.
* Upload cap is 4 MB because API Gateway + Lambda limit a request to ~6 MB (base64 adds 33%). Larger files would use S3 pre-signed URLs.
* DynamoDB listing uses a single constant partition on one GSI (fine for this scale; shard the key for very high write rates).
* Dashboard on EC2 is HTTP only; put it behind CloudFront/ALB + HTTPS for production.
