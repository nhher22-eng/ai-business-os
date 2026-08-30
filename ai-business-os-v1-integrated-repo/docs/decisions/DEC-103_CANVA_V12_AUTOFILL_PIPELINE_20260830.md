# DEC-103 · Canva v1.2 상세페이지 자동화

## 결정

- 원본 디자인 `DAHTw4sMcVM`과 브랜드 템플릿 `EAHTvwXU8Ig`를 v1.2 기준본으로 사용한다.
- 템플릿 계약은 텍스트 72개와 이미지 22개, 총 94개 필드다.
- 문안은 확정 FACT와 승인 문안만 사용한다. AI 후보는 개별 승인 전까지 반영하지 않는다.
- 이미지는 같은 상품의 `final + approved + QA pass + approved_at` 자산만 사용한다.
- 이미지 슬롯은 이름이나 파일명으로 추정하지 않고 사용자가 명시적으로 지정한다.
- 내부 자산 ID는 Canva 자산 ID로 취급하지 않는다. Canva 업로드 성공 후 받은 ID만 Autofill에 사용한다.
- 이미지 업로드와 Autofill 생성은 각각 사용자 실행 승인을 받아야 한다.
- 실행 직전에 브랜드 템플릿 데이터셋을 다시 읽고 94개 이름·유형이 일치하지 않으면 중단한다.

## Canva 연결

- OAuth 2.0 Authorization Code + PKCE(S256)를 사용한다.
- 요청 권한은 `asset:read`, `asset:write`, `brandtemplate:meta:read`, `design:content:write`다.
- OAuth `state`와 PKCE verifier는 Redis에 30분만 보관한다.
- 액세스·리프레시 토큰은 암호화 저장하며 화면과 API에 원문을 반환하지 않는다.
- 토큰 갱신 실패 시 자동 실행하지 않고 재인증 필요 상태로 전환한다.

## 실행 흐름

1. 상품 FACT와 승인 문안으로 텍스트 72/72 확인
2. 승인 이미지 22개 슬롯 지정 및 22/22 확인
3. 사용자 승인 후 Canva 자산 업로드
4. 업로드 작업 동기화 및 Canva 자산 ID 저장
5. 94필드 최종 준비 확인
6. 템플릿 데이터셋 재검증
7. 사용자 최종 승인 후 Autofill 작업 생성
8. 작업 결과 동기화 및 생성 디자인 링크 제공

## 배포 전 경계

- 이 변경은 아직 실서버에 배포하지 않는다.
- Canva Developer Portal의 실제 자격증명은 코드·문서·채팅에 기록하지 않는다.
- 실제 이미지 업로드와 디자인 생성은 배포 후 사용자가 화면에서 직접 승인한다.
- Canva 플랜 및 개발 시험 할당량이 Autofill 사용을 허용하는지 실제 연결 단계에서 확인한다.

## 배포 필수 설정

- `CANVA_CLIENT_ID`
- `CANVA_CLIENT_SECRET`
- `CANVA_REDIRECT_URI=https://os.gardenfarm.kr/api/v1/integrations/canva/callback`
- Canva Developer Portal에도 위 redirect URI를 동일하게 등록
- 권한 네 가지를 Developer Portal에서 사전 활성화
- 마이그레이션 `0020_canva_connections`, `0021_canva_autofill_runs` 적용

## 배포 후 통합시험 기준 상품

- 상품: `8mm 자동 관수키트`
- 상품코드: `IRRIGATION-8MM-KIT`
- SKU: `10m`, `20m`, `30m`
- 실제 외부 시험은 테스트용 승인 이미지로 먼저 수행하고, 생성된 디자인을 검토한 뒤 운영 사용 여부를 승인한다.
