# Multi-stage/Slim production Dockerfile for Log Ingestion API
FROM python:3.13-slim

# Prevent Python from writing .pyc files and enable unbuffered standard out/err
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build/runtime dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-privileged user and group for runtime security
RUN addgroup --system appgroup && adduser --system --group appuser

# Copy application source code and adjust ownership
COPY --chown=appuser:appgroup . /app

# Switch to non-root user
USER appuser

# Expose default HTTP port
EXPOSE 8000

# Launch uvicorn ASGI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
