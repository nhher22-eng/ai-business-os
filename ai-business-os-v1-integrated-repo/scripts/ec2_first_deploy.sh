#!/usr/bin/env bash
set -euo pipefail

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env. IMPORTANT: edit passwords/secrets before real production use."
fi

docker compose up -d --build
docker compose ps

echo
echo "Health:"
curl -fsS http://localhost:8000/health/live || true
echo
curl -fsS http://localhost:8000/health/ready || true
echo
