# AI Business OS — HP-02 Background Runtime Verification Pack

목적: RC5 → GA 전환 전에 Background Runtime(Worker / Scheduler / Queue / Lease / Webhook Outbox)의
운영 계약을 자동 검증하기 위한 초도 실행 패키지.

## 포함 항목

- Worker heartbeat 검증
- Scheduler overdue / drift 검증
- Queue backlog 및 stale lease 검증
- Webhook outbox pending/dead-letter 검증
- 결과를 JSON evidence로 저장
- 비정상 상태 발생 시 non-zero exit code 반환

## 빠른 실행

```bash
cp .env.example .env
python -m pip install -r requirements.txt
python scripts/hp02_validate.py
```

기본 상태에서는 외부 인프라에 접속하지 않고 `mock` 모드로 동작합니다.

실제 PostgreSQL/Redis 운영 환경 검증 시:

```bash
HP02_MODE=live \
DATABASE_URL='postgresql://...' \
REDIS_URL='redis://...' \
python scripts/hp02_validate.py
```

## GA Gate 기본 규칙

- Worker heartbeat age <= 60 sec
- Scheduler overdue jobs = 0
- Queue stale leases = 0
- Webhook dead letters = 0
- 각 검증 probe는 PASS 또는 WARN/FAIL을 반환
- 하나라도 FAIL이면 프로세스 exit code = 1

초도 패키지이므로 실제 RC5 테이블/키 이름은 `config/hp02_contract.json`에서 매핑하도록 설계되어 있습니다.
