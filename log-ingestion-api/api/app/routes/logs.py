"""
Log management and query routes.
Provides endpoints for retrieving ingestion job status and listing historical logs.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.models.ingestion import LogRecord, UploadResponse
from app.repositories.ingestion_repository import (
    DatabaseUnavailableError,
    IngestionRepository,
    get_ingestion_repository,
)
from app.services.ingestion_service import (
    IngestionService,
    get_ingestion_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["Logs"])


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Raw Log File",
    description=(
        "Validates, streams, and uploads a log file (.json, .jsonl, .json.gz, .jsonl.gz) to object storage, "
        "registers a pending job in MongoDB, and enqueues a processing message to RabbitMQ for the Worker."
    ),
    responses={
        201: {"description": "File accepted, persisted, and queued for processing."},
        400: {"description": "Invalid file content, invalid extension, empty file, or unsafe service_name."},
        413: {"description": "File exceeds maximum upload size (MAX_UPLOAD_BYTES)."},
        422: {"description": "Missing required field (such as service_name) or unprocessable entity."},
        503: {"description": "Infrastructure failure (Storage, Database, or Message Queue unavailable)."},
    },
)
def upload_logs(
    file: UploadFile = File(..., description="Multipart raw log file (.json, .jsonl, .json.gz, .jsonl.gz)"),
    service_name: str = Form(..., description="Identifier of the service generating the logs (letters, digits, '-', '_')"),
    environment: str = Form("dev", description="Deployment environment (default: 'dev')"),
    service: IngestionService = Depends(get_ingestion_service),
) -> UploadResponse:
    """
    Accepts log file uploads, validates payload size and syntax, stores to MinIO,
    records state in MongoDB, and dispatches message to RabbitMQ.
    Runs in FastAPI's worker threadpool to handle blocking I/O safely.
    """
    return service.process_upload(
        file=file,
        service_name=service_name,
        environment=environment,
    )



@router.get(
    "/status",
    response_model=LogRecord,
    summary="Get Ingestion Job Status",
    description="Retrieves the full ingestion record for a given ingest_id. Never returns MongoDB internal '_id'.",
    responses={
        200: {"description": "Full ingestion record found and returned."},
        404: {"description": "Ingestion job record not found."},
        503: {"description": "Database infrastructure is unavailable."},
    },
)
def get_log_status(
    id: str = Query(..., description="Unique UUIDv4 ingest_id of the ingestion job"),
    repo: IngestionRepository = Depends(get_ingestion_repository),
) -> LogRecord:
    """
    Looks up a log ingestion job by its unique ingest_id.
    Executes in FastAPI's default worker threadpool to safely handle blocking database I/O.
    """
    try:
        record = repo.find_by_id(id)
    except DatabaseUnavailableError as e:
        logger.error("Database error retrieving status for '%s': %s", id, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable while retrieving record status",
        )

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingestion record '{id}' not found",
        )

    return LogRecord(**record)


@router.get(
    "",
    response_model=List[LogRecord],
    summary="List Ingestion Records",
    description="Lists log ingestion records sorted by created_at in descending order (newest first). Supports filtering and pagination.",
    responses={
        200: {"description": "List of ingestion records."},
        503: {"description": "Database infrastructure is unavailable."},
    },
)
def list_logs(
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (pending, processing, completed, failed)"),
    environment: Optional[str] = Query(None, description="Filter by environment (dev, staging, prod)"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of records to return (1-200, default 50)"),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination (default 0)"),
    repo: IngestionRepository = Depends(get_ingestion_repository),
) -> List[LogRecord]:
    """
    Retrieves a paginated list of log records matching optional filter criteria.
    Executes in FastAPI's default worker threadpool to safely handle blocking database I/O.
    """
    try:
        records = repo.find_all(
            service_name=service_name,
            status=status_filter,
            environment=environment,
            limit=limit,
            skip=skip,
        )
        return [LogRecord(**rec) for rec in records]
    except DatabaseUnavailableError as e:
        logger.error("Database error listing log records: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable while querying log records",
        )
