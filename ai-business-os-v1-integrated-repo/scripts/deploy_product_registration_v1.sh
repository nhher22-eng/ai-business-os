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
BACKUP="$BACKUP_DIR/pre-product-dashboard-final-$STAMP.dump"
mkdir -p "$BACKUP_DIR"

echo "[1/10] Starting database services"
docker compose up -d postgres redis

POSTGRES_USER="$(docker compose exec -T postgres sh -lc 'printf %s "${POSTGRES_USER:-aios}"')"
POSTGRES_DB="$(docker compose exec -T postgres sh -lc 'printf %s "${POSTGRES_DB:-aios}"')"

echo "[2/10] Backing up PostgreSQL -> $BACKUP"
docker compose exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$BACKUP"
test -s "$BACKUP"
sha256sum "$BACKUP" > "$BACKUP.sha256"

echo "[3/10] Building application images"
docker compose build api worker image_worker scheduler migrate

echo "[4/10] Running full regression suite"
docker compose run --rm --no-deps \
  --entrypoint python api \
  -m pytest -q -o cache_dir=/tmp/pytest_cache

echo "[5/10] Applying Alembic migrations"
docker compose run --rm migrate

echo "[6/10] Ensuring media volume is writable"
docker compose run --rm --no-deps --user root api sh -lc \
  'mkdir -p /app/data && chown -R 10001:10001 /app/data'

echo "[7/10] Starting updated services"
docker compose up -d api worker image_worker scheduler

echo "[8/10] Waiting for API and checking public UI routes"
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
printf 'products HTTP ' && curl -fsS -o /dev/null -w '%{http_code}\n' http://localhost:8000/products
printf 'product-registration HTTP ' && curl -fsS -o /dev/null -w '%{http_code}\n' http://localhost:8000/product-registration
printf 'image-studio HTTP ' && curl -fsS -o /dev/null -w '%{http_code}\n' http://localhost:8000/image-studio
printf 'detail-pages HTTP ' && curl -fsS -o /dev/null -w '%{http_code}\n' http://localhost:8000/detail-pages

echo "[9/10] Verifying registered API contracts inside API container"
docker compose exec -T api python - <<'PY'
from app.main import app

paths = {route.path for route in app.routes}
required = {
    "/api/v1/product-registration/products/{product_id}/readiness",
    "/api/v1/product-overview/products",
    "/api/v1/product-image-facts/products/{product_id}",
    "/api/v1/product-image-facts/products/{product_id}/batch-async",
}
missing = sorted(required - paths)
if missing:
    raise SystemExit(f"missing routes: {missing}")
print("product dashboard API contracts: PASS")
PY

echo "[10/10] Migration and service status"
docker compose run --rm migrate alembic current || true
docker compose ps

echo
echo "Product Registration + Product Master + Dashboard deployment completed."
echo "Database backup: $BACKUP"
echo "Open /dashboard -> 상품 업무, /products, and /product-registration for final browser smoke test."
