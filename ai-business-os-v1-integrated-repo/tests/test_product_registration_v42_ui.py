from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_registration_displays_one_stage_at_a_time():
    text = client.get("/product-registration").text
    assert response_ok(text)
    assert "registration-stage-hidden" in text
    assert "panel.classList.add('registration-stage-hidden')" in text
    assert "target.classList.remove('hidden','registration-stage-hidden')" in text
    for label in ("상품 식별정보", "객관적 상품 FACT", "옵션·규격·구성품", "원본 자료 등록", "FACT 확인·완료"):
        assert label in text


def test_registration_has_previous_next_navigation():
    text = client.get("/product-registration").text
    for marker in ("registrationPrev", "registrationNext", "moveRegistrationStage", "← 이전 단계", "다음 단계 →", "1 / 5"):
        assert marker in text


def test_source_upload_auto_saves_product_identity():
    text = client.get("/product-registration").text
    assert "ensureProductIdentityForSourceUpload" in text
    assert "await window.saveFacts()" in text
    assert "상품 식별정보 자동 저장 중" in text
    assert "await ensureProductIdentityForSourceUpload(s)" in text


def response_ok(text: str) -> bool:
    return "새 상품 등록" in text and "원본 이미지 저장" in text

