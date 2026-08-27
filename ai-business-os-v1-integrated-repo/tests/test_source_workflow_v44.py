from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_product_registration_accumulates_and_manages_source_queue():
    text = client.get("/product-registration").text
    for marker in (
        "원본 이미지 선택", "참고문서 선택", "multiple",
        "uploadImages", "uploadDocs", "source_classification','unknown",
    ):
        assert marker in text


def test_registration_is_single_page_and_finishes_in_integrated_management():
    text = client.get("/product-registration").text
    for marker in (
        "1. 기본정보", "2. SKU 초기 구성", "3. 준비된 원본 자료",
        "상품 생성 후 통합관리로 이동", "/commerce-catalog/product/${data.product.id}",
    ):
        assert marker in text
    assert "registrationNext" not in text
    assert "await uploadImages(data.product.id)" in text
    assert "await uploadDocs(data.product.id)" in text


def test_image_asset_generator_reads_registered_sources_and_image_facts():
    text = client.get("/image-assets").text
    for marker in (
        "/api/v1/product-registration/products/${product.value}/images",
        "/api/v1/product-image-facts/products/${product.value}",
        "/api/v1/product-registration-assets/references/${x.id}/content",
        "normalizeRegisteredSource", "[...registeredRows,...factRows]",
    ):
        assert marker in text
