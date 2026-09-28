"""API client and contract layer for communication with log-ingestion-api."""
import os
import requests
import streamlit as st

from mock import mock_upload, mock_status, mock_summary

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
TIMEOUT = 10


def is_demo_mode() -> bool:
    """Return whether the dashboard is running in DEMO_MODE."""
    return DEMO_MODE


def get_api_base_url() -> str:
    """Return the configured API base URL."""
    return API_BASE_URL


def check_api_connection() -> str:
    """Check connectivity to the ingestion API service.

    Returns:
        str: "demo" if DEMO_MODE, "connected" if reachable, "unreachable" otherwise.
    """
    if DEMO_MODE:
        return "demo"
    try:
        r = requests.get(f"{API_BASE_URL}/metrics/summary", timeout=2)
        if r.status_code < 500:
            return "connected"
        return "unreachable"
    except (requests.RequestException, Exception):
        return "unreachable"


def api_upload(file, service_name: str, environment: str) -> dict:
    """Upload a log archive to POST /logs/upload.

    Contract:
        POST {API_BASE_URL}/logs/upload (multipart: file, service_name, environment)
        -> 201 {ingest_id, status: "pending"}
    """
    if DEMO_MODE:
        return mock_upload(file, service_name, environment, st.session_state)

    files = {"file": (file.name, file.getvalue())}
    data = {"service_name": service_name, "environment": environment}
    try:
        r = requests.post(
            f"{API_BASE_URL}/logs/upload",
            files=files,
            data=data,
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except requests.Timeout:
        raise RuntimeError("Request timed out while uploading log file. Please verify network latency and file size.")
    except requests.ConnectionError:
        raise RuntimeError(f"Connection failed: unable to reach Ingestion API at {API_BASE_URL}. Ensure the service is running.")
    except requests.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else "Unknown"
        detail = e.response.text if e.response is not None else str(e)
        raise RuntimeError(f"Upload rejected by API (HTTP {status_code}): {detail}")
    except requests.RequestException as e:
        raise RuntimeError(f"Unexpected error during log upload: {e}")


def api_status(ingest_id: str) -> dict:
    """Fetch status and metrics for an ingestion batch via GET /logs/status?id=<ingest_id>.

    Contract:
        GET {API_BASE_URL}/logs/status?id=<ingest_id>
        -> {ingest_id, service_name, status, metrics, top_error, error_reason, created_at, processed_at}
    """
    if DEMO_MODE:
        return mock_status(ingest_id, st.session_state)

    try:
        r = requests.get(
            f"{API_BASE_URL}/logs/status",
            params={"id": ingest_id},
            timeout=TIMEOUT,
        )
        if r.status_code == 404:
            return {
                "ingest_id": ingest_id,
                "status": "failed",
                "error_reason": f"Batch record with ID '{ingest_id}' was not found in the metadata store.",
            }
        r.raise_for_status()
        return r.json()
    except requests.Timeout:
        raise RuntimeError("Request timed out while querying batch status.")
    except requests.ConnectionError:
        raise RuntimeError(f"Unable to reach Ingestion API at {API_BASE_URL} to fetch status.")
    except requests.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else "Unknown"
        raise RuntimeError(f"API returned error {status_code} while querying batch status.")
    except requests.RequestException as e:
        raise RuntimeError(f"Error fetching ingestion status: {e}")


def api_summary() -> list[dict]:
    """Fetch aggregated metrics for all services via GET /metrics/summary.

    Contract:
        GET {API_BASE_URL}/metrics/summary
        -> [{service_name, total_logs, error_count, warning_count, critical_count, health, top_error?}]
    """
    if DEMO_MODE:
        return mock_summary()

    try:
        r = requests.get(f"{API_BASE_URL}/metrics/summary", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.Timeout:
        raise RuntimeError("Request timed out while loading summary metrics.")
    except requests.ConnectionError:
        raise RuntimeError(f"Unable to connect to Ingestion API at {API_BASE_URL}. Ensure the service is reachable.")
    except requests.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else "Unknown"
        raise RuntimeError(f"API returned HTTP {status_code} while fetching summary metrics.")
    except requests.RequestException as e:
        raise RuntimeError(f"Error loading summary metrics: {e}")
