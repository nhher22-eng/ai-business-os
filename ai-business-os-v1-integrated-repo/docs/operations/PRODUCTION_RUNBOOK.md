# AI Business OS v1 — Production Runbook

## Scope

Production operations for the validated single-EC2 Docker Compose deployment.

Repository:

    ~/ai-business-os/ai-business-os-v1-integrated-repo

Always enter the repository first:

    cd ~/ai-business-os/ai-business-os-v1-integrated-repo

## 1. Service Status

    docker compose ps

Expected services:

    api
    postgres
    redis
    scheduler
    worker

## 2. Readiness

    curl -fsS http://localhost:8000/health/ready && echo

Healthy state:

    status=ok
    postgres=ok
    redis=ok
    queue_depth=0

## 3. Recent Application Errors

    docker compose logs --since=10m api worker scheduler 2>&1 | grep -Ei 'traceback|exception|fatal|panic|operationalerror' || true

No output is the expected healthy result.

## 4. Redis Queue

    docker compose exec -T redis redis-cli LLEN aios:run:queue

Normal idle state:

    0

A persistent non-zero queue requires worker investigation.

## 5. Database Check

    docker compose exec -T postgres psql -U aios -d aios -P pager=off -c "SELECT id,status,task,created_at,updated_at FROM runs ORDER BY created_at DESC LIMIT 20;"

## 6. Controlled Service Restart

Restart one application component when possible:

    docker compose restart api
    docker compose restart worker
    docker compose restart scheduler

Verify after restart:

    docker compose ps
    curl -fsS http://localhost:8000/health/ready && echo

Avoid restarting PostgreSQL or Redis unless required by the incident.

## 7. Full Application Recovery

    docker compose up -d
    docker compose ps
    curl -fsS http://localhost:8000/health/ready && echo

## 8. Manual Database Backup

    ./scripts/backup-postgres.sh

Verify latest backup:

    LATEST=$(ls -1t backups/*.dump | head -1)
    sha256sum -c "${LATEST}.sha256"

## 9. Automatic Backup

Check timer:

    systemctl is-enabled aios-postgres-backup.timer
    systemctl is-active aios-postgres-backup.timer
    systemctl list-timers --all --no-pager | grep aios-postgres-backup

Check backup execution logs:

    journalctl -u aios-postgres-backup.service -n 50 --no-pager

## 10. Database Restore Procedure

Do not overwrite the production database as the first recovery action.

Create an isolated restore database:

    docker compose exec -T postgres psql -U aios -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS aios_restore_test;" -c "CREATE DATABASE aios_restore_test OWNER aios;"

Restore the latest verified backup:

    LATEST=$(ls -1t backups/*.dump | head -1)
    cat "$LATEST" | docker compose exec -T postgres pg_restore -U aios -d aios_restore_test --no-owner --no-privileges --exit-on-error

Validate tables:

    docker compose exec -T postgres psql -U aios -d aios_restore_test -P pager=off -c '\dt'

Only promote a restored database after validation and an explicit recovery decision.

Cleanup test restore database:

    docker compose exec -T postgres psql -U aios -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS aios_restore_test;"

## 11. EC2 Reboot Recovery

After an EC2 reboot:

    cd ~/ai-business-os/ai-business-os-v1-integrated-repo
    docker compose ps
    curl -fsS http://localhost:8000/health/ready && echo

Then verify queue:

    docker compose exec -T redis redis-cli LLEN aios:run:queue

## 12. Secret Handling

Never commit:

    .env
    .env.backup*
    .env.pre-ga-*
    database passwords
    secret keys
    backup database dumps

The production .env file must remain mode 600.

Check:

    stat -c '%a %U %G %n' .env

Expected mode:

    600

## 13. Incident Escalation Rule

Do not perform destructive database recovery solely because readiness fails.

First determine whether the failure is:

1. API
2. Worker
3. Scheduler
4. Redis
5. PostgreSQL
6. Host/infrastructure

Preserve logs and create or verify a database backup before destructive recovery whenever possible.

## 14. GA Baseline

GA runtime hardening baseline:

    f5826f1 release: certify AI Business OS v1.0.0 GA

Release:

    v1.0.0

See:

    docs/release/GA_RELEASE_MANIFEST.md
