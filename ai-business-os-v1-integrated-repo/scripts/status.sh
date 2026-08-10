#!/usr/bin/env bash
set -e
docker compose ps
echo
curl -sS http://localhost:8000/health/live || true
echo
curl -sS http://localhost:8000/health/ready || true
echo
