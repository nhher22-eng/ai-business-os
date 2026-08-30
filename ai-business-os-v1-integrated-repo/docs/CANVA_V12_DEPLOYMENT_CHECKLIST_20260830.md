# Canva v1.2 배포 전 체크리스트

## 현재 완료

- [x] Canva 텍스트 72필드 계약
- [x] Canva 이미지 22필드 계약
- [x] 브랜드 템플릿 게시본 94필드 확인
- [x] 승인 문안 생성·검토·승인 흐름
- [x] 승인 이미지 슬롯 선택·검증
- [x] Canva OAuth PKCE 연결 코드
- [x] 비동기 이미지 업로드·동기화 코드
- [x] 비동기 Autofill 생성·동기화 코드
- [x] 서비스 관리 Canva 카드
- [x] 외부 실행 전 사용자 승인 게이트

## 새 채팅에서 실제 배포할 때

- [ ] 현재 EC2 브랜치·커밋·작업트리 확인
- [ ] 배포 전 PostgreSQL 백업
- [ ] Canva Developer Portal integration 생성 또는 기존 integration 확인
- [ ] Redirect URI와 네 가지 scope 등록
- [ ] EC2 `.env`에 Canva 자격증명 안전 입력
- [ ] 코드 반영 전 diff와 배포 대상 재확인
- [ ] 컨테이너 빌드
- [ ] DB 마이그레이션 0020·0021 적용
- [ ] API·worker·scheduler 재기동
- [ ] `/health/live`, `/health/ready` 확인
- [ ] 서비스 관리에서 Canva 연결
- [ ] 연결상태·재인증 상태 확인
- [ ] `8mm 자동 관수키트` 텍스트 준비도 확인
- [ ] 테스트용 승인 이미지 22개 슬롯 확인
- [ ] 사용자 승인 후 Canva 이미지 업로드
- [ ] Canva 자산 22/22 확인
- [ ] 사용자 최종 승인 후 Autofill 1회 실행
- [ ] 생성 디자인 링크·내용·이미지 배치 검토
- [ ] 문제 발생 시 추가 Autofill 실행 중단

## 현재 중지점

실제 배포, 자격증명 등록, Canva 계정 연결, 외부 이미지 업로드 및 Autofill 실행 직전에서 중지한다.
