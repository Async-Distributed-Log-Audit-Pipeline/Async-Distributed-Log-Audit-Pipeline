import json
import logging
import os
import sys
import tempfile
import time
import traceback
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

from errors import DatabaseUnavailableError, PermanentError, TransientError
from parser.analytics import analyze_file

logger = logging.getLogger(__name__)


class Outcome(Enum):
    """Enumeration of possible processing outcomes for a log ingestion message."""
    COMPLETED = auto()
    SKIPPED_DUPLICATE = auto()
    FAILED_PERMANENT = auto()
    RETRY_LATER = auto()
    INVALID_MESSAGE = auto()


@dataclass
class ProcessResult:
    """Detailed result of processing a message."""
    outcome: Outcome
    ingest_id: str | None = None
    reason: str | None = None


def process_message(body: bytes, repo: Any, storage: Any) -> ProcessResult:
    """
    Processes a log ingestion message received from RabbitMQ.
    Performs database record lookup, file download, log parsing, and DB updates.
    
    Returns a ProcessResult dataclass containing outcome, ingest_id, and optional reason.
    This function is decoupled from RabbitMQ (no pika dependency) to facilitate unit testing.
    """
    worker_id = os.getenv("WORKER_ID", os.getenv("COMPUTERNAME", "worker-local"))

    # a. Parse JSON message body
    try:
        data = json.loads(body.decode("utf-8"))
        if not isinstance(data, dict):
            reason = "Invalid payload: Message is not a JSON object"
            logger.error("[%s] [NO_ID] %s", worker_id, reason)
            return ProcessResult(Outcome.INVALID_MESSAGE, reason=reason)

        ingest_id = data.get("ingest_id")
        service_name = data.get("service_name")
        object_key = data.get("object_key")

        if not (
            isinstance(ingest_id, str) and ingest_id.strip()
            and isinstance(service_name, str) and service_name.strip()
            and isinstance(object_key, str) and object_key.strip()
        ):
            reason = "Invalid payload: Missing required string fields (ingest_id, service_name, object_key)"
            logger.error("[%s] [NO_ID] %s", worker_id, reason)
            return ProcessResult(Outcome.INVALID_MESSAGE, ingest_id=ingest_id if isinstance(ingest_id, str) else None, reason=reason)

    except Exception as e:
        reason = f"Malformed message JSON: {e}"
        logger.error("[%s] [NO_ID] %s", worker_id, reason)
        return ProcessResult(Outcome.INVALID_MESSAGE, reason=reason)

    start_time = time.monotonic()
    logger.info("[%s] [%s] Message received. Starting processing...", worker_id, ingest_id)

    # b. Find record in DB
    try:
        record = repo.find_by_id(ingest_id)
    except TransientError as e:
        reason = f"Database unavailable while retrieving record: {e}"
        logger.warning("[%s] [%s] %s", worker_id, ingest_id, reason)
        return ProcessResult(Outcome.RETRY_LATER, ingest_id=ingest_id, reason=reason)

    if record is None:
        reason = "Record not found in database"
        logger.warning("[%s] [%s] %s. Treating as invalid message.", worker_id, ingest_id, reason)
        return ProcessResult(Outcome.INVALID_MESSAGE, ingest_id=ingest_id, reason=reason)

    # c. Check status for duplicate delivery
    status = record.get("status")
    if status in ("completed", "failed"):
        reason = f"Duplicate delivery skipped (record status is '{status}')"
        logger.info("[%s] [%s] %s.", worker_id, ingest_id, reason)
        return ProcessResult(Outcome.SKIPPED_DUPLICATE, ingest_id=ingest_id, reason=reason)

    # d. Mark record as processing
    try:
        updated = repo.mark_processing(ingest_id)
        if not updated:
            reason = "Unable to mark processing (already modified or terminal)"
            logger.info("[%s] [%s] %s. Skipping duplicate.", worker_id, ingest_id, reason)
            return ProcessResult(Outcome.SKIPPED_DUPLICATE, ingest_id=ingest_id, reason=reason)
    except TransientError as e:
        reason = f"Database unavailable while marking record as processing: {e}"
        logger.warning("[%s] [%s] %s", worker_id, ingest_id, reason)
        return ProcessResult(Outcome.RETRY_LATER, ingest_id=ingest_id, reason=reason)

    # e. Optional debug processing delay for simulating mid-job worker crashes
    delay_str = os.getenv("DEBUG_PROCESSING_DELAY_SECONDS", "0")
    try:
        delay = float(delay_str)
        if delay > 0:
            logger.info("[%s] [%s] Debug processing delay active: sleeping for %.1f seconds...", worker_id, ingest_id, delay)
            time.sleep(delay)
    except ValueError:
        pass

    # f. Download, analyze, and save results
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_name = os.path.basename(object_key) or "download.log"
            dest_path = os.path.join(temp_dir, file_name)

            logger.info("[%s] [%s] Downloading object '%s' from storage...", worker_id, ingest_id, object_key)
            storage.download_file(object_key, dest_path)
            logger.info("[%s] [%s] Download done.", worker_id, ingest_id)

            logger.info("[%s] [%s] Analyzing log file...", worker_id, ingest_id)
            metrics, report, top_error = analyze_file(dest_path)
            logger.info(
                "[%s] [%s] Analysis done. Total logs: %d, Health: '%s'.",
                worker_id,
                ingest_id,
                metrics.get("total_logs", 0),
                report.get("health", "unknown"),
            )

            logger.info("[%s] [%s] Saving results to database...", worker_id, ingest_id)
            saved = repo.save_results(ingest_id, metrics, report, top_error)
            duration = time.monotonic() - start_time

            if not saved:
                reason = "Record save skipped (already terminal or modified)"
                logger.info(
                    "[%s] [%s] %s. Skipping duplicate. Duration: %.2fs",
                    worker_id,
                    ingest_id,
                    reason,
                    duration,
                )
                return ProcessResult(Outcome.SKIPPED_DUPLICATE, ingest_id=ingest_id, reason=reason)

            logger.info("[%s] [%s] Processing COMPLETED successfully in %.2fs.", worker_id, ingest_id, duration)
            return ProcessResult(Outcome.COMPLETED, ingest_id=ingest_id)

    except PermanentError as e:
        duration = time.monotonic() - start_time
        reason = str(e)
        logger.error("[%s] [%s] Permanent error processing job: %s. Duration: %.2fs", worker_id, ingest_id, reason, duration)
        return _mark_failed_and_return_result(repo, ingest_id, reason, worker_id)

    except TransientError as e:
        duration = time.monotonic() - start_time
        reason = f"Transient error: {e}"
        logger.warning("[%s] [%s] %s. Will retry later. Duration: %.2fs", worker_id, ingest_id, reason, duration)
        return ProcessResult(Outcome.RETRY_LATER, ingest_id=ingest_id, reason=reason)

    except Exception as e:
        duration = time.monotonic() - start_time
        err_msg = f"unexpected error: {type(e).__name__}: {e}"
        logger.error(
            "[%s] [%s] Unexpected error processing job: %s\n%s. Duration: %.2fs",
            worker_id,
            ingest_id,
            err_msg,
            traceback.format_exc(),
            duration,
        )
        return _mark_failed_and_return_result(repo, ingest_id, err_msg, worker_id)


def _mark_failed_and_return_result(repo: Any, ingest_id: str, reason: str, worker_id: str) -> ProcessResult:
    """Helper to mark a record as failed in MongoDB with exception handling."""
    try:
        repo.mark_failed(ingest_id, reason)
        logger.info("[%s] [%s] Record marked as FAILED in database.", worker_id, ingest_id)
        return ProcessResult(Outcome.FAILED_PERMANENT, ingest_id=ingest_id, reason=reason)
    except (DatabaseUnavailableError, TransientError) as db_err:
        retry_reason = f"Failed to mark record failed due to TransientError ({db_err})"
        logger.warning("[%s] [%s] %s. Will retry later.", worker_id, ingest_id, retry_reason)
        return ProcessResult(Outcome.RETRY_LATER, ingest_id=ingest_id, reason=retry_reason)
    except Exception as err:
        logger.error("[%s] [%s] Unexpected error marking record failed: %s", worker_id, ingest_id, err)
        return ProcessResult(Outcome.FAILED_PERMANENT, ingest_id=ingest_id, reason=reason)
