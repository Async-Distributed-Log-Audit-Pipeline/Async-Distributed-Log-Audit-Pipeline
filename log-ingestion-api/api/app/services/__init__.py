"""Services package."""
from app.services.ingestion_service import (
    IngestionService,
    get_ingestion_service,
)

__all__ = ["IngestionService", "get_ingestion_service"]
