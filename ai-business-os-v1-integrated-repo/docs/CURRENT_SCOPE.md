# Current Scope

이 통합 저장소의 핵심 목적은:
1. EC2에서 실행 가능한 실제 runtime baseline 제공
2. PostgreSQL/Redis/Worker/Scheduler 실행 확인
3. 기존 HP-02~05 및 GA/live-validation 산출물을 함께 보관
4. 실제 인프라 live validation으로 넘어갈 수 있는 단일 저장소 제공

다음 강화 대상:
- Auth / Tenant / RBAC
- Workflow DAG
- Agent/Tool Registry
- durable lease/retry/idempotency
- SSE/WebSocket
- webhook dispatcher
- secret vault
- observability/evaluation/cost
- enterprise UI
