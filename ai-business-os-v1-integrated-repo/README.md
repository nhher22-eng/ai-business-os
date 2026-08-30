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
- M05 AI 이미지 생성 스튜디오 (`/image-studio`)
- M06 상세페이지 생성 스튜디오 (`/detail-pages`)
- 브랜드 스타일 시트 / 템플릿 / 섹션 버전관리 / QA Gate
- 이미지 Preview → Final 승인 흐름 및 상품 기준사진 보호 정책
- 회사 실제업무 중심 통합 홈 (`/business-home`)
- 상품 기본정보 → 이미지 요소 → 콘텐츠 문안 → 템플릿 → 상세페이지 5단계 연결
- 승인형 콘텐츠 문안 자산 API·UI (`/content-copy-studio`)
- 이미지 요소 자산 자동 파일명·역할·사용처·버전·해시 메타데이터

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

## 2026-08-23 통합 업무 홈

사용자는 `/business-home`에서 실제 업무를 시작합니다. 5개 제작 기능은 회사 업무를
돕는 공통 도구로 연결되며 최상위 업무 메뉴를 대체하지 않습니다.

1. `/product-registration` — 상품 기본정보 및 1차 FACT·원본
2. `/image-assets` — 이미지 요소 자산 생성기
3. `/content-copy-studio` — 콘텐츠 문안 후보·승인 표현 자산
4. `/template-maker` — 템플릿 디자인 제작기
5. `/detail-page-builder` — 상세페이지 조립·검토·승인

AI Agent는 다음 작업을 제안하지만 FACT 확정, 예산 증액, 기본 도구 구조 변경과
외부 게시를 자동 수행하지 않습니다.

## Content Studio v1

M05/M06 구현 범위, 안전 규칙, 제한사항과 배포 검증 내용은 `docs/CONTENT_STUDIO_V1.md`를 참고하세요.

서버에서 기존 `.env`를 보존한 상태로 업데이트한 뒤 다음 스크립트로 DB 백업 → 빌드 → migration → 재기동 → health check를 한 번에 수행할 수 있습니다.

```bash
./scripts/deploy_content_studio_v1.sh
```
