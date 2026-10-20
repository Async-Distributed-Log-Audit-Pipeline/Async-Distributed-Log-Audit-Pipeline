#!/usr/bin/env bash
# Builds the two Lambda deployment folders (build/api and build/worker).
# Dependencies are downloaded as Linux x86_64 / Python 3.12 wheels, so the result runs on Lambda
# no matter whether you build on Windows (Git Bash), macOS, Linux or AWS CloudShell. No Docker needed.
set -euo pipefail
cd "$(dirname "$0")"

PIP="python3 -m pip install --quiet --upgrade --target"
WHEEL_OPTS="--platform manylinux2014_x86_64 --implementation cp --python-version 3.12 --only-binary=:all:"

rm -rf build
mkdir -p build/api build/worker

echo "==> Building API package"
$PIP build/api $WHEEL_OPTS -r log-ingestion-api/api/requirements.txt
cp -r log-ingestion-api/api/app build/api/app
cp log-ingestion-api/api/lambda_function.py build/api/

echo "==> Building worker package"
$PIP build/worker $WHEEL_OPTS -r log-worker/requirements.txt
cp -r log-worker/parser log-worker/repository log-worker/storage build/worker/
cp log-worker/errors.py log-worker/processor.py log-worker/retry_policy.py log-worker/lambda_function.py build/worker/

find build -name "__pycache__" -type d -prune -exec rm -rf {} +
echo "==> Done. Sizes:"; du -sh build/api build/worker
