"""
Ingestion Service layer.
Coordinates file streaming, validation, storage uploads, MongoDB persistence, and queue dispatch.
Implements the required strict call order (Storage -> DB -> Queue) and transactional rollbacks.
"""

from datetime import datetime, timezone
import gzip
import json
import logging
import re
import tempfile
from typing import BinaryIO, Optional
import uuid

from fastapi import Depends, HTTPException, UploadFile, status

from app.clients.queue_client import (
    QueueClient,
    QueueUnavailableError,
    get_queue_client,
)
from app.clients.storage_client import (
    StorageClient,
    StorageUnavailableError,
    get_storage_client,
)
from app.config import Settings, get_settings
from app.models.ingestion import UploadResponse
from app.repositories.ingestion_repository import (
    DatabaseUnavailableError,
    IngestionRepository,
    get_ingestion_repository,
)

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = [".json.gz", ".jsonl.gz", ".json", ".jsonl"]
SERVICE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


class IngestionService:
    """
    Core business logic service orchestrating the log upload and ingestion flow.
    Enforces validation, streaming size enforcement, and safe rollback semantics.
    """

    def __init__(
        self,
        storage_client: StorageClient,
        repository: IngestionRepository,
        queue_client: QueueClient,
        settings: Settings,
    ):
        self.storage = storage_client
        self.repo = repository
        self.queue = queue_client
        self.settings = settings

    def validate_service_name(self, service_name: str) -> None:
        """
        Validates that service_name contains only alphanumeric characters, hyphens, and underscores.
        Explicitly forbids path traversal indicators ('/', '\\', '..').
        """
        if not service_name or not service_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="service_name cannot be empty.",
            )

        trimmed = service_name.strip()
        if "/" in trimmed or "\\" in trimmed or ".." in trimmed or not SERVICE_NAME_PATTERN.match(trimmed):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid service_name. Only letters, digits, '-' and '_' are allowed. Path separators and traversal sequences are forbidden.",
            )

    def extract_and_validate_extension(self, filename: Optional[str]) -> str:
        """
        Extracts and verifies that the uploaded file has an allowed extension (.json, .jsonl, .json.gz, .jsonl.gz).
        """
        if not filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing filename. File must have one of the following extensions: .json, .jsonl, .json.gz, .jsonl.gz",
            )

        fn_lower = filename.lower()
        for ext in ALLOWED_EXTENSIONS:
            if fn_lower.endswith(ext):
                return ext

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension. Allowed extensions are: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    def stream_and_spool_upload(
        self,
        upload_file: UploadFile,
        max_bytes: int,
    ) -> tempfile.SpooledTemporaryFile:
        """
        Streams file content from the incoming multipart request into a SpooledTemporaryFile,
        enforcing the MAX_UPLOAD_BYTES cap while streaming to prevent memory exhaustion attacks.
        """
        spooled = tempfile.SpooledTemporaryFile(max_size=1024 * 1024)  # Spool in RAM up to 1MB, then disk
        total_bytes = 0
        chunk_size = 64 * 1024  # 64 KB chunks

        try:
            while True:
                chunk = upload_file.file.read(chunk_size)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    spooled.close()
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail=f"Uploaded file exceeds maximum allowed size of {max_bytes} bytes.",
                    )
                spooled.write(chunk)

            if total_bytes == 0:
                spooled.close()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded file is empty.",
                )

            spooled.seek(0)
            return spooled

        except HTTPException:
            raise
        except Exception as e:
            spooled.close()
            logger.error("Error reading uploaded file stream: %s", e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to read upload stream: {e}",
            ) from e

    def sanity_check_content(
        self,
        spooled: BinaryIO,
        ext: str,
    ) -> None:
        """
        Performs lightweight content sanity check matching the worker's parser expectations.
        Ensures the first entry is a valid JSON dictionary.
        For gzip files, streams and decompresses only the first few bytes/lines.
        """
        spooled.seek(0)
        is_gz = ext.endswith(".gz")

        try:
            if is_gz:
                # Check gzip magic bytes (0x1f 0x8b)
                magic = spooled.read(2)
                spooled.seek(0)
                if magic != b"\x1f\x8b":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid gzip file: missing gzip magic header bytes.",
                    )

                with gzip.GzipFile(fileobj=spooled, mode="rb") as gz_file:
                    first_line = gz_file.readline()
            else:
                first_line = spooled.readline()

            spooled.seek(0)

            if not first_line or not first_line.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Log file contains no readable content lines.",
                )

            line_text = first_line.decode("utf-8", errors="replace").strip()

            # Support JSON array of objects or single JSON object / JSONL line
            if line_text.startswith("["):
                try:
                    data = json.loads(line_text)
                    if not isinstance(data, list) or (data and not isinstance(data[0], dict)):
                        raise ValueError("JSON array must contain log objects.")
                except Exception:
                    # Attempt reading more if array spans multiple lines
                    spooled.seek(0)
                    sample = spooled.read(4096).decode("utf-8", errors="replace").strip()
                    spooled.seek(0)
                    try:
                        data = json.loads(sample)
                        if not isinstance(data, (dict, list)):
                            raise ValueError()
                    except Exception as json_err:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid log file content: must contain valid JSON object records.",
                        ) from json_err
            else:
                data = json.loads(line_text)
                if not isinstance(data, dict):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid log file content: each log entry must be a JSON object.",
                    )

        except HTTPException:
            raise
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid log file content: must contain valid JSON records ({err}).",
            ) from err
        except (gzip.BadGzipFile, EOFError) as gz_err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Corrupt or invalid gzip log file: {gz_err}",
            ) from gz_err
        finally:
            spooled.seek(0)

    def process_upload(
        self,
        file: UploadFile,
        service_name: str,
        environment: str = "dev",
    ) -> UploadResponse:
        """
        Executes the required upload sequence:
        1. Validate extension, service_name, size cap, and content sanity.
        2. Generate ingest_id (UUID4).
        3. Upload to Object Storage (S3 / MinIO).
        4. Insert 'pending' record into MongoDB.
        5. Publish message to RabbitMQ.
        6. Return HTTP 201 with ingest_id and pending status.

        Transactional failure handling guarantees no orphaned records or silent hangs.
        """
        # Step 1: Validation
        self.validate_service_name(service_name)
        ext = self.extract_and_validate_extension(file.filename)
        spooled_file = self.stream_and_spool_upload(file, self.settings.MAX_UPLOAD_BYTES)

        try:
            self.sanity_check_content(spooled_file, ext)

            # Step 2: Generate unique ingest_id
            ingest_id = str(uuid.uuid4())
            clean_service = service_name.strip()
            clean_env = environment.strip() if environment else "dev"
            object_key = f"raw-logs/{clean_service}-{ingest_id}{ext}"

            # Step 3: Upload file to Object Storage
            try:
                self.storage.upload_fileobj(spooled_file, object_key)
            except StorageUnavailableError as e:
                logger.error("[%s] Step 3 Failed - Storage upload error: %s", ingest_id, e)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Storage service unavailable while uploading log file.",
                )

            # Step 4: Insert 'pending' document into MongoDB
            record = {
                "ingest_id": ingest_id,
                "service_name": clean_service,
                "environment": clean_env,
                "object_key": object_key,
                "status": "pending",
                "metrics": None,
                "top_error": None,
                "report": None,
                "error_reason": None,
                "created_at": datetime.now(timezone.utc),
                "processed_at": None,
                "processing_started_at": None,
            }

            try:
                self.repo.insert_record(record)
            except DatabaseUnavailableError as db_err:
                logger.error("[%s] Step 4 Failed - Database insert error: %s. Initiating storage rollback...", ingest_id, db_err)
                # Rollback Step 3: Best-effort delete of uploaded object
                try:
                    self.storage.delete_file(object_key)
                except Exception as rollback_err:
                    logger.warning("[%s] Storage cleanup error: %s", ingest_id, rollback_err)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database service unavailable while creating ingestion record.",
                )

            # Step 5: Publish job to RabbitMQ
            message_payload = {
                "ingest_id": ingest_id,
                "service_name": clean_service,
                "object_key": object_key,
            }

            try:
                self.queue.publish_job(message_payload)
            except QueueUnavailableError as q_err:
                logger.error("[%s] Step 5 Failed - Queue publish error: %s. Marking record as failed...", ingest_id, q_err)
                # Rollback Step 4: Mark record as failed with reason (only if still pending)
                try:
                    self.repo.mark_failed_if_pending(
                        ingest_id=ingest_id,
                        error_reason=f"Failed to publish to processing queue: {q_err}",
                    )
                except Exception as mark_err:
                    logger.critical("[%s] Failed to mark record as failed in DB: %s", ingest_id, mark_err)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Message queue service unavailable while dispatching job.",
                )

            # Step 6: Return 201 Created immediately
            return UploadResponse(ingest_id=ingest_id, status="pending")

        finally:
            spooled_file.close()


def get_ingestion_service(
    storage_client: StorageClient = Depends(get_storage_client),
    repository: IngestionRepository = Depends(get_ingestion_repository),
    queue_client: QueueClient = Depends(get_queue_client),
    settings: Settings = Depends(get_settings),
) -> IngestionService:
    """FastAPI dependency provider for IngestionService."""
    return IngestionService(
        storage_client=storage_client,
        repository=repository,
        queue_client=queue_client,
        settings=settings,
    )
