"""
Main application module for the Log Ingestion API service.
Initializes FastAPI, configures CORS middleware, and includes API routers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import health, logs, metrics

settings = get_settings()

app = FastAPI(
    title="Log Ingestion API",
    description=(
        "Front-door ingestion service for the Asynchronous Distributed Log & Audit Analytics Pipeline (CS32102). "
        "Validates and accepts log uploads, stores raw files in S3/MinIO, creates pending records in MongoDB, "
        "publishes jobs to RabbitMQ, and provides query interfaces for status, history, and metrics."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(health.router)
app.include_router(logs.router)
app.include_router(metrics.router)


