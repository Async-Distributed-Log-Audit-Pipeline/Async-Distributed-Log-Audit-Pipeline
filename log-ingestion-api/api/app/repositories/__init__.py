"""Repositories package."""
from app.repositories.ingestion_repository import (
    IngestionRepository,
    get_ingestion_repository,
)

__all__ = ["IngestionRepository", "get_ingestion_repository"]
