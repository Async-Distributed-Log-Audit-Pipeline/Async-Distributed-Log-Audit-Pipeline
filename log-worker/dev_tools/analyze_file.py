import argparse
import json
import os
import sys
from dotenv import load_dotenv

# Ensure log-worker directory is in python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from parser.analytics import analyze_file

load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(description="Analyze a log file directly and output metrics, report, and top_error.")
    parser.add_argument("path", help="Path to local log file (.jsonl or .jsonl.gz)")
    return parser.parse_args()


def main():
    args = parse_args()

    if not os.path.isfile(args.path):
        print(f"[ERROR] File not found: {args.path}", file=sys.stderr)
        sys.exit(1)

    try:
        metrics, report, top_error = analyze_file(args.path)

        output = {
            "metrics": metrics,
            "report": report,
            "top_error": top_error,
        }

        print(json.dumps(output, indent=2))
    except Exception as e:
        print(f"[ERROR] Analysis failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
