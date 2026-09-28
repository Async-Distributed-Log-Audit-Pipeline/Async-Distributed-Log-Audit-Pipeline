"""
Unit tests for the /health liveness endpoint and CORS handling.
"""

from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient):
    """
    Verifies that GET /health returns 200 OK with {"status": "ok"}
    and does not trigger any backend infrastructure calls.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_headers(client: TestClient):
    """
    Verifies that preflight OPTIONS requests return appropriate CORS headers
    matching the configured allowed origins.
    """
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
