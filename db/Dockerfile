FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# No CMD baked in — the docker-compose command: key specifies which script to run.
# Normal startup:  python setup_schema_and_indexes.py
# Manual seeding:  docker compose run --rm db-init python seed_services.py
# Inspection:      docker compose run --rm db-init python inspect_collection.py
