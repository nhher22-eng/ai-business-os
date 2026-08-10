# AI Business OS — HP-03 Kubernetes Security Hardening Pack

목적:
RC5 → GA 전환 전에 Kubernetes 배포 계약을 최소권한·격리·비루트·불변 파일시스템 기준으로 강화하고
정적 검증 Evidence를 생성한다.

## 포함 항목

- Namespace Pod Security Admission labels
- Default-deny NetworkPolicy
- App-specific ingress/egress NetworkPolicy
- Dedicated ServiceAccount
- Minimal RBAC Role / RoleBinding
- Secure Deployment baseline
- PodDisruptionBudget
- ResourceQuota / LimitRange
- Security validation script
- CI release gate
- Evidence JSON

## 빠른 검증

```bash
python scripts/hp03_validate.py
```

정적 검증이 PASS하면:
- privileged=false
- allowPrivilegeEscalation=false
- runAsNonRoot=true
- readOnlyRootFilesystem=true
- capabilities drop ALL
- seccomp RuntimeDefault
- default deny NetworkPolicy 존재
- ServiceAccount 분리
- Resource requests/limits 존재
- image가 latest tag를 사용하지 않음

실제 클러스터 적용 전에는 이미지 digest와 namespace/port/CIDR를 운영값으로 치환해야 한다.
