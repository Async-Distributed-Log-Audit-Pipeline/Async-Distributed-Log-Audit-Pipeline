# Cloud Cost Analysis Report

**Project:** Distributed Systems Mini Project 
**Billing period analysed:** 6 Oct 2026 – 20 Oct 2026 (15 days)
**Data source:** AWS cost export (`costs 2.csv`)

---

## 1. Summary

| Metric | Value |
|---|---|
| Total cost, 6–20 Oct 2026 | **$0.00** |
| Services with billing activity | 6 (Glue, KMS, Secrets Manager, SNS, S3, SQS) |
| Services with any non-zero charge | 0 |
| Days with a non-zero daily total | 0 of 15 |
| Project budget ceiling (AWS) | ≤ $200 credit + always-free allowances |
| Budget consumed | $0.00 (0.0%) |

The deployment stayed entirely within the free tier for the whole observed period. No service incurred a charge on any day, so the project's requirement to show that usage stayed within free-tier limits is met by this data.

## 2. Cost by service

| Service | Days with a billing line | Total cost ($) | Share of total |
|---|---|---|---|
| Glue | 14 | 0.00 | – |
| Key Management Service (KMS) | 3 | 0.00 | – |
| S3 | 3 | 0.00 | – |
| Secrets Manager | 1 | 0.00 | – |
| SNS | 1 | 0.00 | – |
| SQS | 1 | 0.00 | – |
| **Total** | – | **0.00** | – |

Because every figure is zero, percentage shares and cost rankings are not meaningful. The "days with a billing line" column shows only where AWS recorded activity, not spend.

## 3. Daily trend

Every daily total from 6 Oct to 20 Oct is $0.00. There is no upward trend, spike or anomaly. Notes on the raw data:

- **Glue** appears on 14 of 15 days, so it is the most continuously active service in the export.
- **S3** has entries on 8 Oct, 9 Oct and 19 Oct, which fits periods of upload and testing.
- **SQS** (9 Oct), **SNS** and **Secrets Manager** (both 8 Oct) show a single day each, which suggests short setup or test sessions rather than steady use.
- **KMS** appears on 6, 11 and 16 Oct.
- **20 Oct** is a partial day (the export was taken that morning). Its Glue cell is blank and the day's total is $0, so treat it as incomplete.

## 4. Observations and risks

These points go beyond the raw numbers and rest on general knowledge of AWS pricing, so confirm them in your own Billing console.

1. **Glue is not part of the project's stack.** The project calls for S3, SQS, Lambda and DynamoDB. Glue is billed per DPU-hour for ETL jobs and crawlers, and it is the only service showing activity almost daily. It costs nothing so far, but confirm whether a job, crawler or Data Catalog resource is deliberately in use and delete anything idle.
2. **Secrets Manager normally has a charge after its free trial.** It is typically billed per secret per month once the 30-day trial ends. A $0 reading on 8 Oct is consistent with the trial. If you keep secrets beyond about 30 days, expect a small recurring cost, or switch to environment variables or SSM Parameter Store for the project.
3. **KMS customer-managed keys carry a monthly fee.** The zero here suggests only AWS-managed keys or very low request volume. Avoid creating customer-managed keys unless needed.
4. **Lambda, DynamoDB and API Gateway do not appear in the export.** These are core to the project. Either they were not used in this window, or they sit within free allowances and produced no billing rows. If your system calls them, check that the export covers all services.
5. **Usage is light.** The free-tier outcome reflects development-scale traffic. The stress and performance testing planned for Weeks 11–12 should be the point to re-check costs, especially for SQS requests, Lambda invocations and S3 requests.

## 5. Recommendations

- Set an **AWS Budgets alert** at a low threshold such as $1 and $5, so any charge is flagged immediately.
- Turn on **Cost Anomaly Detection** or check Cost Explorer weekly through the final demonstration.
- **Delete unused resources** after the demo: Glue jobs and crawlers, secrets, KMS keys, S3 test objects, and any idle queues or topics.
- Re-run this analysis after stress testing and again before submission to confirm the zero-cost result still holds.

## 6. Cost report text for submission

> During 6–20 October 2026 the project incurred **$0.00** across all AWS services used (S3, SQS, SNS, Glue, Key Management Service and Secrets Manager). All usage remained within the AWS free tier, and no charges were drawn from the $200 credit. Monthly cost at the current usage level is estimated at $0, subject to Secrets Manager and KMS key fees if those resources are retained beyond their free-trial periods.

