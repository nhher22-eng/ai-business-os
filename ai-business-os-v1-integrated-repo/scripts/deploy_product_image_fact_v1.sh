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
BACKUP="$BACKUP_DIR/pre-product-image-fact-v1-$STAMP.dump"
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
docker compose build api worker scheduler migrate

echo "[4/10] Running full regression tests before migration"
docker compose run --rm --no-deps \
  --entrypoint python api \
  -m pytest -q -o cache_dir=/tmp/pytest_cache

echo "[5/10] Applying Alembic migrations through 0010"
docker compose run --rm migrate

echo "[6/10] Ensuring managed media volume is writable"
docker compose run --rm --no-deps --user root api sh -lc \
  'mkdir -p /app/data && chown -R 10001:10001 /app/data'

echo "[7/10] Starting updated services"
docker compose up -d api worker scheduler

echo "[8/10] Waiting for API"
for _ in $(seq 1 40); do
  if curl -fsS http://localhost:8000/health/live >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

curl -fsS http://localhost:8000/health/live
echo
curl -fsS http://localhost:8000/health/ready
echo

echo "[9/10] Checking product image FACT routes and migration"
printf 'dashboard HTTP ' && curl -fsS -o /dev/null -w '%{http_code}\n' http://localhost:8000/dashboard
printf 'product-registration HTTP ' && curl -fsS -o /dev/null -w '%{http_code}\n' http://localhost:8000/product-registration
python - <<'PY'
import urllib.request
spec = urllib.request.urlopen('http://localhost:8000/openapi.json', timeout=10).read().decode('utf-8')
required = [
    '/api/v1/product-image-facts/products/{product_id}/batch-upload',
    '/api/v1/product-image-facts/products/{product_id}',
    '/api/v1/product-image-facts/items/{item_id}',
    '/api/v1/product-image-facts/products/{product_id}/confirm',
]
missing = [path for path in required if path not in spec]
if missing:
    raise SystemExit('Missing M10 OpenAPI routes: ' + ', '.join(missing))
print('M10 OpenAPI routes: PASS')
PY

docker compose run --rm migrate alembic current | tee /tmp/m10-alembic-current.txt
if ! grep -q '0010_product_image_fact' /tmp/m10-alembic-current.txt; then
  echo "ERROR: Alembic is not at 0010_product_image_fact" >&2
  exit 3
fi

echo "[10/10] Service status"
docker compose ps

echo
echo "Product Image FACT v1 deployment completed."
echo "Database backup: $BACKUP"
echo "Open /dashboard -> + 새 상품 등록 -> 상품 이미지 FACT."
