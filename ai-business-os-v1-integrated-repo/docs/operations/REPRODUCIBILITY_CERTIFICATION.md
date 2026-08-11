# AI Business OS Reproducibility Certification

## Status

PASS

## Validated Baseline

- GA release: v1.0.0-ga
- Production edge hardening: 7a55e8c
- Container secret exclusion hotfix: bdcddab
- Deployment model: single EC2 / Docker Compose
- Production API binding: 127.0.0.1:8000
- Public edge: Nginx port 80
- Domain/TLS: pending

## Fresh Reconstruction Validation

A clean clone from the GitHub repository was used to validate:

- Fresh source clone
- Fresh Docker image build
- Fresh PostgreSQL instance
- Fresh Redis instance
- Alembic migration from an empty database
- API startup
- Worker startup
- Scheduler startup
- Health/readiness checks
- API -> Redis queue -> Worker -> PostgreSQL execution
- Run persistence and API read-back

Result: PASS

## Isolation Validation

The reconstruction environment used:

- Separate Compose project: aios-repro
- Separate PostgreSQL volume
- Separate Redis volume
- API bound to 127.0.0.1:18000

The production stack remained operational during validation.

Result: PASS

## Security Finding

Fresh reconstruction identified that the Docker build context could include
the production .env file because no .dockerignore existed while the Dockerfile
used COPY . .

A .dockerignore was introduced to exclude runtime secrets and artifacts.

Validated:

- /app/.env absent from rebuilt image
- /app/.env.example retained
- Host production .env remains mode 600

Result: PASS

## Post-Test Production Verification

After removal of the isolated reproduction stack:

- Production PostgreSQL healthy
- Production Redis healthy
- Production API healthy
- Production Worker operational
- Production Scheduler operational
- Production run execution succeeded
- Git working tree clean
- Local main synchronized with origin/main

## Certification

The validated AI Business OS source baseline can reconstruct a functional
application stack from a fresh Git clone without dependence on the existing
production containers or production database state.

Reproducibility / disaster-recovery baseline: PASS
