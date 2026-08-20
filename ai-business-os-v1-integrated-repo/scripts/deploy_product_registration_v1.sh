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
BACKUP="$BACKUP_DIR/pre-product-registration-expanded-$STAMP.dump"
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

echo "[9/10] Verifying registered API and UI contracts inside API container"
docker compose exec -T api python - <<'PY'
from app.main import app
from app import product_registration_ui


def collect_route_paths(routes):
    """Collect paths across FastAPI/Starlette route wrappers safely.

    Newer FastAPI versions may expose internal included-router objects in
    app.routes that do not themselves have a .path attribute. Traverse any
    nested routes/router.routes instead of assuming every entry is an APIRoute.
    """
    paths = set()
    stack = list(routes)
    seen = set()
    while stack:
        route = stack.pop()
        marker = id(route)
        if marker in seen:
            continue
        seen.add(marker)

        path = getattr(route, "path", None)
        if path:
            paths.add(path)

        nested = getattr(route, "routes", None)
        if nested:
            stack.extend(list(nested))

        router = getattr(route, "router", None)
        router_routes = getattr(router, "routes", None) if router is not None else None
        if router_routes:
            stack.extend(list(router_routes))
    return paths


paths = collect_route_paths(app.routes)
required = {
    "/api/v1/product-registration/products/{product_id}/readiness",
    "/api/v1/product-registration/products/{product_id}/image-plan-suggestions",
    "/api/v1/product-registration/products/{product_id}/image-plans/confirm",
    "/api/v1/product-registration/products/{product_id}/image-plans",
    "/api/v1/product-overview/products",
    "/api/v1/product-image-facts/products/{product_id}",
    "/api/v1/product-image-facts/products/{product_id}/batch-async",
}
missing = sorted(required - paths)
if missing:
    raise SystemExit(f"missing routes: {missing}")

html = product_registration_ui.HTML
required_copy = (
    "① 메인 / 히어로",
    "⑤ 간단 사용 / 활용 순서",
    "⑥ 라인드로잉 기본 2종",
    "⑧ 추가 이미지 아이디어",
    "선택한 이미지 기획 확정",
    "실제 이미지 생성은 등록 완료 조건이 아닙니다",
)
missing_copy = [text for text in required_copy if text not in html]
if missing_copy:
    raise SystemExit(f"missing registration UI contract: {missing_copy}")
if "AI 이미지 생성 열기" in html or "nextImageStudio" in html:
    raise SystemExit("direct Image Studio generation link must not exist in registration flow")

print("expanded product registration deployment contract: PASS")
PY

echo "[10/10] Migration and service status"
docker compose run --rm migrate alembic current || true
docker compose ps

echo
echo "Expanded Product Registration + Product Master deployment completed."
echo "Database backup: $BACKUP"
echo "Open /product-registration for the final browser smoke test: FACT -> Image FACT -> text confirmation -> image planning -> registration complete."
