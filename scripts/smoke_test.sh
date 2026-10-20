#!/usr/bin/env bash
# Smoke test against the DEPLOYED API.   Usage: ./scripts/smoke_test.sh https://<id>.execute-api.<region>.amazonaws.com
set -euo pipefail
API="${1:?usage: $0 <api-base-url>}"; API="${API%/}"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
cat > "$TMP/sample.jsonl" <<'LOG'
{"@timestamp":"2026-10-20T09:00:00Z","level":"INFO","message":"service started","logger_name":"demo.app"}
{"@timestamp":"2026-10-20T09:00:05Z","level":"WARN","message":"slow response from payment-gateway","logger_name":"demo.app"}
{"@timestamp":"2026-10-20T09:00:09Z","level":"ERROR","message":"Connection refused to database host","logger_name":"demo.db"}
{"@timestamp":"2026-10-20T09:00:10Z","level":"ERROR","message":"Connection refused to database host","logger_name":"demo.db"}
{"@timestamp":"2026-10-20T09:00:12Z","level":"FATAL","message":"out of memory","logger_name":"demo.app"}
LOG
echo "1) health";  curl -fsS "$API/health"; echo
echo "2) upload";  RESP=$(curl -fsS -F "file=@$TMP/sample.jsonl" -F "service_name=demo-service" -F "environment=dev" "$API/logs/upload"); echo "$RESP"
ID=$(echo "$RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin)["ingest_id"])')
echo "3) waiting for the worker Lambda..."
for i in $(seq 1 20); do
  S=$(curl -fsS "$API/logs/status?id=$ID" | python3 -c 'import sys,json; print(json.load(sys.stdin)["status"])')
  echo "   status=$S"; [ "$S" = "completed" ] || [ "$S" = "failed" ] && break; sleep 3
done
echo "4) final record"; curl -fsS "$API/logs/status?id=$ID" | python3 -m json.tool
echo "5) metrics summary"; curl -fsS "$API/metrics/summary" | python3 -m json.tool
[ "$S" = "completed" ] && echo "SMOKE TEST PASSED" || { echo "SMOKE TEST FAILED (status=$S)"; exit 1; }
