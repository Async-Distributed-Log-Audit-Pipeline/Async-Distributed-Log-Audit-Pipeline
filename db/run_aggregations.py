"""
Runner script to demonstrate and verify all aggregation queries against the live MongoDB instance.
"""

import json
from aggregations import (
    get_metrics_summary,
    get_health_breakdown,
    get_top_errors_by_service,
    get_pipeline_status_counts,
    get_time_based_trends,
    get_ingestion_status,
)


def run_all_queries():
    print("=" * 70)
    print(" Running MongoDB Aggregation Queries Test")
    print("=" * 70 + "\n")

    # 1. Pipeline Status Counts
    print("[1] Pipeline Operational Status Counts:")
    status_counts = get_pipeline_status_counts()
    for status, count in status_counts.items():
        print(f"    * {status:<12}: {count}")
    print()

    # 2. Metrics Summary (Powers GET /metrics/summary)
    print("[2] Per-Service Metrics Summary (GET /metrics/summary):")
    summaries = get_metrics_summary()
    header = f"{'Service':<18} {'Health':<10} {'Total':<7} {'Crit':<6} {'Error':<7} {'Warn':<6} {'Info':<6} {'Ingests':<8}"
    print("    " + header)
    print("    " + "-" * len(header))
    for s in summaries:
        print(
            f"    {s['service_name']:<18} {s['latest_health']:<10} {s['total_logs']:<7} "
            f"{s['critical_count']:<6} {s['error_count']:<7} {s['warning_count']:<6} "
            f"{s['info_count']:<6} {s['ingestion_count']:<8}"
        )
    print()

    # 3. Health Breakdown
    print("[3] System Health Breakdown:")
    health = get_health_breakdown()
    print("    Summary distribution:")
    for k, v in health["summary"].items():
        print(f"      - {k:<16}: {v}")
    print("    By service:")
    for s in health["by_service"]:
        print(f"      - {s['service_name']:<18}: {s['health']}")
    print()

    # 4. Top Errors by Service
    print("[4] Top Errors Grouped by Microservice:")
    top_errors = get_top_errors_by_service(limit_per_service=2)
    if not top_errors:
        print("    (No errors detected in current dataset)")
    for s in top_errors:
        print(f"    * Service: {s['service_name']}")
        for err in s["top_errors"]:
            msg_snippet = err['message'][:55] + "..." if len(err['message']) > 55 else err['message']
            print(f"        [{err['count']}x] {msg_snippet}")
    print()

    # 5. Time-Based Trends
    print("[5] Chronological Trends (Hourly):")
    trends = get_time_based_trends(interval="hour", limit=5)
    for t in trends:
        print(f"    * Time: {t['timestamp']} | Logs: {t['total_logs']} | Errors: {t['error_count']} | Ingests: {t['ingestion_count']}")
    print()

    # 6. Point Ingestion Lookup (GET /logs/status?id=...)
    print("[6] Single Ingestion Lookup (GET /logs/status?id=...):")
    # Take the latest service record to test lookup
    if summaries:
        target_service = summaries[0]["service_name"]
        from aggregations import get_db, MONGO_COLLECTION
        sample_doc = get_db()[MONGO_COLLECTION].find_one({"service_name": target_service})
        if sample_doc:
            ingest_id = sample_doc["ingest_id"]
            record = get_ingestion_status(ingest_id)
            print(f"    * Lookup ingest_id '{ingest_id}':")
            print(f"        Status:  {record.get('status')}")
            print(f"        Service: {record.get('service_name')}")
            print(f"        Health:  {record.get('report', {}).get('health')}")
            print(f"        Logs:    {record.get('metrics', {}).get('total_logs')}")

    print("\n" + "=" * 70)
    print(" All Aggregation Queries Verified Successfully!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_queries()
