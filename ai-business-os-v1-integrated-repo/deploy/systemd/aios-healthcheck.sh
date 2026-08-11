#!/usr/bin/env bash
set -euo pipefail

URL="${AIOS_HEALTH_URL:-http://127.0.0.1/health/ready}"
TIMEOUT="${AIOS_HEALTH_TIMEOUT:-10}"

body="$(curl -fsS --max-time "$TIMEOUT" "$URL")"

python3 - "$body" <<'PY'
import json
import sys

body = sys.argv[1]
data = json.loads(body)

if data.get("status") != "ok":
    raise SystemExit(f"health status is not ok: {data!r}")

checks = data.get("checks") or {}
bad = {k: v for k, v in checks.items() if v != "ok"}

if bad:
    raise SystemExit(f"health dependencies failed: {bad!r}")

print("AIOS_HEALTH_OK")
PY
