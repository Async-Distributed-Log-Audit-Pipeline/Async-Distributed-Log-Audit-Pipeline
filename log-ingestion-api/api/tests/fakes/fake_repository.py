"""
In-memory fake implementation of IngestionRepository for isolated testing.
"""

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.repositories.ingestion_repository import DatabaseUnavailableError


class FakeIngestionRepository:
    """
    Fake repository that stores documents in an in-memory dictionary.
    Mimics MongoDB sorting, filtering, projection, and aggregation behavior.
    """

    def __init__(self):
        self.records: Dict[str, Dict[str, Any]] = {}
        self.should_fail_insert = False
        self.should_fail_find = False
        self.should_fail_mark_failed = False
        self.should_fail_aggregate = False

    def insert_record(self, record: Dict[str, Any]) -> str:
        if self.should_fail_insert:
            raise DatabaseUnavailableError("Simulated database failure on insert")
        doc = deepcopy(record)
        # Store copy without MongoDB _id or strip it on read
        self.records[doc["ingest_id"]] = doc
        return doc["ingest_id"]

    def find_by_id(self, ingest_id: str) -> Optional[Dict[str, Any]]:
        if self.should_fail_find:
            raise DatabaseUnavailableError("Simulated database failure on find_by_id")
        doc = self.records.get(ingest_id)
        if doc is None:
            return None
        res = deepcopy(doc)
        res.pop("_id", None)
        return res

    def find_all(
        self,
        service_name: Optional[str] = None,
        status: Optional[str] = None,
        environment: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> List[Dict[str, Any]]:
        if self.should_fail_find:
            raise DatabaseUnavailableError("Simulated database failure on find_all")

        filtered = []
        for doc in self.records.values():
            if service_name and doc.get("service_name") != service_name:
                continue
            if status and doc.get("status") != status:
                continue
            if environment and doc.get("environment") != environment:
                continue
            filtered.append(deepcopy(doc))

        # Sort created_at desc (newest first)
        def get_sort_key(d):
            val = d.get("created_at")
            if isinstance(val, datetime):
                return val.timestamp()
            elif isinstance(val, str):
                try:
                    return datetime.fromisoformat(val).timestamp()
                except Exception:
                    return 0
            return 0

        filtered.sort(key=get_sort_key, reverse=True)

        paginated = filtered[skip : skip + min(limit, 200)]
        for doc in paginated:
            doc.pop("_id", None)
        return paginated

    def mark_failed_if_pending(self, ingest_id: str, error_reason: str) -> bool:
        if self.should_fail_mark_failed:
            raise DatabaseUnavailableError("Simulated database failure on mark_failed")

        doc = self.records.get(ingest_id)
        if doc and doc.get("status") == "pending":
            doc["status"] = "failed"
            doc["error_reason"] = error_reason
            doc["processed_at"] = datetime.now(timezone.utc)
            return True
        return False

    def aggregate_completed_metrics(
        self,
        service_name: Optional[str] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        if self.should_fail_aggregate:
            raise DatabaseUnavailableError("Simulated database failure on aggregation")

        groups: Dict[str, Dict[str, int]] = {}

        for doc in self.records.values():
            if doc.get("status") != "completed":
                continue
            s_name = doc.get("service_name")
            if service_name and s_name != service_name:
                continue

            created = doc.get("created_at")
            if isinstance(created, str):
                try:
                    created = datetime.fromisoformat(created)
                except Exception:
                    pass

            if from_time and isinstance(created, datetime):
                c_dt = created if created.tzinfo else created.replace(tzinfo=timezone.utc)
                f_dt = from_time if from_time.tzinfo else from_time.replace(tzinfo=timezone.utc)
                if c_dt < f_dt:
                    continue
            if to_time and isinstance(created, datetime):
                c_dt = created if created.tzinfo else created.replace(tzinfo=timezone.utc)
                t_dt = to_time if to_time.tzinfo else to_time.replace(tzinfo=timezone.utc)
                if c_dt > t_dt:
                    continue

            if s_name not in groups:
                groups[s_name] = {
                    "total_logs": 0,
                    "error_count": 0,
                    "warning_count": 0,
                    "critical_count": 0,
                }

            metrics = doc.get("metrics") or {}
            groups[s_name]["total_logs"] += int(metrics.get("total_logs", 0))
            groups[s_name]["error_count"] += int(metrics.get("error_count", 0))
            groups[s_name]["warning_count"] += int(metrics.get("warning_count", 0))
            groups[s_name]["critical_count"] += int(metrics.get("critical_count", 0))

        output = []
        for s_name in sorted(groups.keys()):
            counts = groups[s_name]
            crit = counts["critical_count"]
            err = counts["error_count"]
            if crit > 0:
                health = "critical"
            elif err > 0:
                health = "degraded"
            else:
                health = "healthy"

            output.append({
                "service_name": s_name,
                "total_logs": counts["total_logs"],
                "error_count": err,
                "warning_count": counts["warning_count"],
                "critical_count": crit,
                "health": health,
            })

        return output
