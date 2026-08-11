#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKUP_DIR="$ROOT/backups"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
TIMESTAMP="$(date -u +%Y%m%d-%H%M%S)"
BACKUP="$BACKUP_DIR/aios-ga-$TIMESTAMP.dump"
CHECKSUM="$BACKUP.sha256"

mkdir -p "$BACKUP_DIR"

echo "[$(date -u +%FT%TZ)] PostgreSQL backup starting"

docker compose exec -T postgres \
  pg_dump -U aios -d aios -Fc > "$BACKUP"

test -s "$BACKUP"

docker compose exec -T postgres \
  pg_restore -l < "$BACKUP" >/dev/null

sha256sum "$BACKUP" > "$CHECKSUM"

echo "Backup: $BACKUP"
echo "Checksum: $CHECKSUM"

find "$BACKUP_DIR" \
  -type f \
  \( -name 'aios-ga-*.dump' -o -name 'aios-ga-*.dump.sha256' \) \
  -mtime "+$RETENTION_DAYS" \
  -delete

echo "[$(date -u +%FT%TZ)] PostgreSQL backup completed"
