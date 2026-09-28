import argparse
import json
import os
import sys
from dotenv import load_dotenv

# Ensure root log-worker directory is in python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from repository.ingestion_repository import IngestionRepository

load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(description="Display a log ingestion record from MongoDB by ingest_id.")
    parser.add_argument("ingest_id", help="The unique ingest_id UUID string to look up")
    return parser.parse_args()


def main():
    args = parse_args()
    repo = IngestionRepository()

    record = repo.find_by_id(args.ingest_id)
    if not record:
        print(f"[ERROR] No record found for ingest_id: '{args.ingest_id}'", file=sys.stderr)
        sys.exit(1)

    # Convert ObjectId or datetime objects to string representation for clean JSON output
    clean_record = json.loads(json.dumps(record, default=str))

    print(f"=== Record for ingest_id: {args.ingest_id} ===")
    print(json.dumps(clean_record, indent=2))


if __name__ == "__main__":
    main()
