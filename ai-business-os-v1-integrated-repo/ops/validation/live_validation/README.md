# AI Business OS — Live Validation Execution Pack

목적:
HP-02 → HP-03 → HP-04 → HP-05를 순차 실행해 최종 GA 판정을 자동 생성한다.

## 실행 방식

```bash
cp config/live.env.example .env
python scripts/run_live_validation.py
```

## 동작 원칙

- HP-02: PostgreSQL/Redis background runtime 검증
- HP-03: Kubernetes security hardening 정적/실환경 검증
- HP-04: Upgrade / Canary / Rollback 검증
- HP-05: 위 Evidence를 취합하여 GA 판정

실환경 연결 정보가 없으면 강제로 PASS 처리하지 않는다.
필수 Evidence가 없거나 연결 실패 시 최종 상태는 BLOCKED다.
