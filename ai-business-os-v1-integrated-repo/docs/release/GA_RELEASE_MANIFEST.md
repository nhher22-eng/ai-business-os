# AI Business OS v1 — GA Release Manifest

## Release

- Release: v1.0.0-ga
- Status: GO
- Environment: AWS EC2 / Ubuntu 24.04 LTS
- Runtime: Docker Compose
- Database: PostgreSQL 16
- Queue: Redis 7
- Application components:
  - API
  - Worker
  - Scheduler
  - PostgreSQL
  - Redis

## GA Code Baseline

Validated runtime hardening commit:

    f41b6c1 release: harden GA runtime and backup operations

The final GA tag is created only after this manifest and the production
runbook are committed.

## Migration Baseline

Alembic revision:

    0001_initial

Fresh-database migration was verified against an isolated PostgreSQL
database before GA freeze.

## Release Gate Evidence

The following checks passed on the deployed EC2 environment:

- Docker Compose service startup
- PostgreSQL health
- Redis health
- API readiness
- API -> Redis queue -> Worker -> PostgreSQL E2E execution
- Run persistence
- Worker stop/start recovery
- PostgreSQL stop/start degradation and recovery
- Redis stop/start degradation and recovery
- EC2 reboot recovery
- Scheduler recovery
- Concurrent scheduler locking using FOR UPDATE SKIP LOCKED
- Secret rotation verification
- Fresh database migration
- PostgreSQL backup creation
- SHA-256 backup checksum generation
- Independent database restore
- Restored data integrity verification
- systemd scheduled backup execution

## Final Release Gate

Final task:

    GA FINAL RELEASE GATE

Result:

    succeeded

Final readiness state:

    status=ok
    postgres=ok
    redis=ok
    queue_depth=0

## Backup Contract

Production backup script:

    scripts/backup-postgres.sh

Automation:

    aios-postgres-backup.timer

Retention default:

    14 days

Backup artifacts and runtime environment files are excluded from Git.

## Recovery Contract

A valid database backup has been restored into an isolated database and
the restored application tables/data were verified.

EC2 reboot recovery and post-reboot E2E execution were also verified.

## Known Operational Boundary

This GA approval covers the currently validated single-EC2 Docker Compose
deployment. Infrastructure architectures not exercised by this release
gate require their own deployment validation before being treated as GA.

## Decision

GA RELEASE GATE: PASS

Release decision: GO
