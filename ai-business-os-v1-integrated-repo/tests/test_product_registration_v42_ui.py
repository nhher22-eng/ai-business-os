from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_registration_is_approved_single_page():
    text = client.get("/product-registration").text
    for marker in ("신규 상품 등록", "기본정보", "SKU 초기 구성", "준비된 원본 자료", "상품 생성 후 통합관리로 이동"):
        assert marker in text
    assert "대표·45도·정면 지정은 통합상품관리" in text
    assert "registrationNext" not in text


def test_registration_recognizes_common_unit_inputs():
    text = client.get("/product-registration").text
    for marker in ("10m, 20m, 30m", "용량", "중량", "길이", "수량", "입력한 표기는 그대로 초기값"):
        assert marker in text


def test_registration_uploads_images_and_documents_before_redirect():
    text = client.get("/product-registration").text
    assert "uploadImages(data.product.id)" in text
    assert "uploadDocs(data.product.id)" in text
    assert "/commerce-catalog/product/${data.product.id}" in text
