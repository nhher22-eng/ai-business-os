#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "ERROR: .env is missing. Keep the server's existing .env file; do not replace it with .env.example." >&2
  exit 2
fi

BACKUP_DIR="$ROOT/backups"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
BACKUP="$BACKUP_DIR/pre-product-registration-v1-$STAMP.dump"
mkdir -p "$BACKUP_DIR"

echo "[1/9] Starting database services"
docker compose up -d postgres redis

POSTGRES_USER="$(docker compose exec -T postgres sh -lc 'printf %s "${POSTGRES_USER:-aios}"')"
POSTGRES_DB="$(docker compose exec -T postgres sh -lc 'printf %s "${POSTGRES_DB:-aios}"')"

echo "[2/9] Backing up PostgreSQL -> $BACKUP"
docker compose exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$BACKUP"
test -s "$BACKUP"
sha256sum "$BACKUP" > "$BACKUP.sha256"

echo "[3/9] Building application images"
docker compose build api worker scheduler migrate

echo "[4/9] Running regression tests before DB migration"
docker compose run --rm --no-deps \
  --entrypoint python api \
  -m pytest -q -o cache_dir=/tmp/pytest_cache

echo "[5/9] Applying Alembic migrations"
docker compose run --rm migrate

echo "[6/9] Ensuring media volume is writable"
docker compose run --rm --no-deps --user root api sh -lc \
  'mkdir -p /app/data && chown -R 10001:10001 /app/data'

echo "[7/9] Starting updated services"
docker compose up -d api worker scheduler

echo "[8/9] Waiting for API and checking routes"
for _ in $(seq 1 30); do
  if curl -fsS http://localhost:8000/health/live >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

curl -fsS http://localhost:8000/health/live
echo
curl -fsS http://localhost:8000/health/ready
echo
printf 'dashboard HTTP ' && curl -fsS -o /dev/null -w '%{http_code}\n' http://localhost:8000/dashboard
printf 'product-registration HTTP ' && curl -fsS -o /dev/null -w '%{http_code}\n' http://localhost:8000/product-registration
printf 'image-studio HTTP ' && curl -fsS -o /dev/null -w '%{http_code}\n' http://localhost:8000/image-studio
printf 'detail-pages HTTP ' && curl -fsS -o /dev/null -w '%{http_code}\n' http://localhost:8000/detail-pages

echo "[9/9] Migration and service status"
docker compose run --rm migrate alembic current || true
docker compose ps

echo
echo "Product Registration v1 deployment completed."
echo "Database backup: $BACKUP"
echo "Open /dashboard, then use '＋ 새 상품 등록'."
