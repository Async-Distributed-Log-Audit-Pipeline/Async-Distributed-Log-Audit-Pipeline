"""
AWS Lambda entry point for the Log Ingestion API.
API Gateway (HTTP API) -> Mangum (ASGI adapter) -> FastAPI app.
Lambda handler setting: lambda_function.handler
"""
from mangum import Mangum

from app.main import app

handler = Mangum(app, lifespan="off")
