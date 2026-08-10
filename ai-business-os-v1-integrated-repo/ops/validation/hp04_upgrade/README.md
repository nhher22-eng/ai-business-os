
# HP-04 Upgrade / Rollback Validation Pack

목표
- 배포 전 백업 확인
- Migration 호환성 게이트
- Canary 배포 승인
- SLO 실패 시 자동 Rollback
- Rollback Evidence 생성

구성
- scripts/preflight_check.sh
- scripts/canary_gate.sh
- scripts/rollback.sh
- k8s/rollout-strategy.yaml
- docs/ROLLBACK_RUNBOOK.md
