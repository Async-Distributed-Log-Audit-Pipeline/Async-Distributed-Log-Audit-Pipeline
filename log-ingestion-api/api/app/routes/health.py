"""
Health and liveness probe route.
Provides a simple endpoint to verify the service is running and accepting traffic.
"""

from fastapi import APIRouter
from app.models.ingestion import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Liveness Probe",
    description="Returns HTTP 200 with status 'ok' if the API service is up and responsive. Does not check downstream dependencies.",
)
def get_health() -> HealthResponse:
    """
    Liveness check endpoint.
    Used by container orchestrators, load balancers, and monitoring agents.
    """
    return HealthResponse(status="ok")
