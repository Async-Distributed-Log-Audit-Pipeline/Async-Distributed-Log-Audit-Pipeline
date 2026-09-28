"""
Pydantic data models for the Log Ingestion API.
Defines request and response schemas with full OpenAPI documentation and examples.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Liveness probe response model."""

    status: str = Field(
        ...,
        description="Health status of the API service",
        json_schema_extra={"example": "ok"},
    )


class UploadResponse(BaseModel):
    """Response returned upon successful acceptance and queuing of a log file."""

    ingest_id: str = Field(
        ...,
        description="Unique UUIDv4 identifier assigned to this ingestion job",
        json_schema_extra={"example": "c7a8e8b0-4dbb-4fd5-8889-bf8d4076722c"},
    )
    status: str = Field(
        default="pending",
        description="Initial lifecycle status of the ingestion job",
        json_schema_extra={"example": "pending"},
    )


class LogRecord(BaseModel):
    """
    Complete ingestion job record stored in MongoDB.
    Nullable fields accommodate the asynchronous worker lifecycle,
    as metrics, reports, and error details are populated post-processing.
    """

    ingest_id: str = Field(
        ...,
        description="Unique UUIDv4 identifier for the ingestion job",
        json_schema_extra={"example": "c7a8e8b0-4dbb-4fd5-8889-bf8d4076722c"},
    )
    service_name: str = Field(
        ...,
        description="Originating service name for the log file",
        json_schema_extra={"example": "api-gateway"},
    )
    environment: str = Field(
        ...,
        description="Deployment environment (e.g., dev, staging, prod)",
        json_schema_extra={"example": "dev"},
    )
    object_key: str = Field(
        ...,
        description="Storage key for the raw log file in S3 / MinIO",
        json_schema_extra={"example": "raw-logs/api-gateway-c7a8e8b0-4dbb-4fd5-8889-bf8d4076722c.jsonl"},
    )
    status: str = Field(
        ...,
        description="Current lifecycle state (pending, processing, completed, failed)",
        json_schema_extra={"example": "pending"},
    )
    metrics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Aggregated log level counters computed by the worker",
        json_schema_extra={
            "example": {
                "total_logs": 120,
                "critical_count": 0,
                "error_count": 5,
                "warning_count": 12,
                "info_count": 100,
                "debug_count": 3,
                "other_count": 0,
            }
        },
    )
    top_error: Optional[str] = Field(
        default=None,
        description="Most frequent normalized error message encountered during processing",
        json_schema_extra={"example": "Connection refused to database host"},
    )
    report: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Detailed analytics report including health rating, top warnings, sources, and rule findings",
        json_schema_extra={
            "example": {
                "health": "degraded",
                "time_range": {"first": "2026-09-26T14:40:00Z", "last": "2026-09-26T15:00:00Z"},
                "top_errors": [{"message": "Connection refused", "count": 5}],
                "top_warnings": [],
                "top_sources": [{"logger": "com.se_project.api_gateway", "count": 120}],
                "findings": [],
                "skipped_lines": 0,
            }
        },
    )
    error_reason: Optional[str] = Field(
        default=None,
        description="Reason for job failure if status is 'failed'",
        json_schema_extra={"example": None},
    )
    created_at: datetime = Field(
        ...,
        description="UTC timestamp when the upload was registered",
        json_schema_extra={"example": "2026-09-28T16:30:00Z"},
    )
    processed_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp when the worker finalized processing",
        json_schema_extra={"example": None},
    )
    processing_started_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp when the worker picked up the job",
        json_schema_extra={"example": None},
    )


class ServiceMetricsSummary(BaseModel):
    """
    Aggregated health and count metrics for a single service across all completed ingestions.
    """

    service_name: str = Field(
        ...,
        description="Name of the service",
        json_schema_extra={"example": "api-gateway"},
    )
    total_logs: int = Field(
        ...,
        description="Cumulative count of all parsed log entries for this service",
        json_schema_extra={"example": 1450},
    )
    error_count: int = Field(
        ...,
        description="Cumulative count of ERROR level logs for this service",
        json_schema_extra={"example": 12},
    )
    warning_count: int = Field(
        ...,
        description="Cumulative count of WARN/WARNING level logs for this service",
        json_schema_extra={"example": 45},
    )
    critical_count: int = Field(
        ...,
        description="Cumulative count of CRITICAL/FATAL level logs for this service",
        json_schema_extra={"example": 0},
    )
    health: str = Field(
        ...,
        description="Computed operational health: 'critical' if critical_count > 0, else 'degraded' if error_count > 0, else 'healthy'",
        json_schema_extra={"example": "degraded"},
    )
