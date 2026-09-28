"""
Metrics and Analytics summary routes.
Provides operational health and aggregated log counters computed over completed ingestions.
"""

from datetime import datetime
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.ingestion import ServiceMetricsSummary
from app.repositories.ingestion_repository import (
    DatabaseUnavailableError,
    IngestionRepository,
    get_ingestion_repository,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get(
    "/summary",
    response_model=List[ServiceMetricsSummary],
    summary="Get Aggregated Service Metrics Summary",
    description=(
        "Returns a list of aggregated metric summaries grouped by service_name for all 'completed' ingestion records. "
        "Sums the Worker's recorded counters: total_logs, error_count, warning_count, and critical_count.\n\n"
        "### Operational Health Evaluation Rule:\n"
        "- **critical**: If `critical_count > 0`\n"
        "- **degraded**: Else if `error_count > 0`\n"
        "- **warning**: Else if `warning_count > 0`\n"
        "- **healthy**: Otherwise"
    ),
    responses={
        200: {"description": "List of aggregated metrics per service with computed health."},
        503: {"description": "Database infrastructure is unavailable."},
    },
)
def get_metrics_summary(
    service_name: Optional[str] = Query(None, description="Optional filter for specific service name"),
    from_time: Optional[datetime] = Query(None, alias="from", description="Optional ISO 8601 start timestamp (filter on created_at >= from)"),
    to_time: Optional[datetime] = Query(None, alias="to", description="Optional ISO 8601 end timestamp (filter on created_at <= to)"),
    repo: IngestionRepository = Depends(get_ingestion_repository),
) -> List[ServiceMetricsSummary]:
    """
    Executes a MongoDB aggregation pipeline over completed log jobs to calculate
    per-service metrics and evaluate health status.
    Runs in FastAPI's worker threadpool to handle blocking I/O safely.
    """
    try:
        results = repo.aggregate_completed_metrics(
            service_name=service_name,
            from_time=from_time,
            to_time=to_time,
        )
        return [ServiceMetricsSummary(**item) for item in results]
    except DatabaseUnavailableError as e:
        logger.error("Database error while computing metrics summary: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable while aggregating metrics summary.",
        )
