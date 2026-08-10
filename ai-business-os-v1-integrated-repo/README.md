# AI Business OS v1 — Integrated Repository

EC2 + Docker Compose에서 바로 실행할 수 있도록 정리한 통합 배포 베이스라인입니다.

## 포함
- FastAPI API
- PostgreSQL
- Redis
- Worker
- Scheduler
- Webhook Outbox 기본 구조
- Alembic migration
- Docker Compose
- Health / Readiness API
- Run 생성 / 조회 API
- Background queue enqueue/worker 처리
- HP-02 / HP-03 / HP-04 / HP-05 결과물 통합 보관
- Live Validation Pack
- EC2 배포 스크립트

## EC2 빠른 시작

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

DB migration:

```bash
docker compose exec api alembic upgrade head
```

테스트용 Run 생성:

```bash
curl -X POST http://localhost:8000/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{"task":"EC2 deployment smoke test"}'
```

## 주의

이 저장소는 현재 대화에서 확인 가능한 운영/검증 산출물과 실행 가능한 통합 코어를
하나로 정리한 EC2 배포 베이스라인입니다. 과거 여러 대화에 생성되었으나 현재 런타임에
파일 자체가 존재하지 않는 개별 코드 조각을 임의로 "복원 완료"라고 주장하지 않습니다.

실제 GA 승인은 live infrastructure evidence가 필요합니다.
