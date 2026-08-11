#!/usr/bin/env bash
set -euo pipefail

UNIT="${1:-unknown}"
HOST="$(hostname)"
NOW="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

MESSAGE="AI Business OS ALERT: health check failed | host=${HOST} | unit=${UNIT} | time=${NOW}"

logger -p user.err -t aios-alert "$MESSAGE"
echo "$MESSAGE"
