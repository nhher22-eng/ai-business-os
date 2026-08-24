from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_product_registration_accumulates_and_manages_source_queue():
    text = client.get("/product-registration").text
    for marker in (
        "sourceImageQueue", "appendSourceImages", "sourceImageQueue.push",
        "data-source-remove", "전체 선택 취소", "선택한 원본 이미지 저장",
        "sourceClassificationOptions", "input.value=''",
    ):
        assert marker in text


def test_registration_stage_navigation_and_completion_links():
    text = client.get("/product-registration").text
    for marker in (
        "registration-stage-hidden", "registrationPrev", "registrationNext",
        "← 이전 단계", "다음 단계 →", "v2-registration-complete",
        "이미지 요소 자산 만들기", "콘텐츠 문안 만들기", "홈으로 이동",
    ):
        assert marker in text
    assert "await ensureProductIdentityForSourceUpload(s)" in text


def test_image_asset_generator_reads_registered_sources_and_image_facts():
    text = client.get("/image-assets").text
    for marker in (
        "/api/v1/product-registration/products/${product.value}/images",
        "/api/v1/product-image-facts/products/${product.value}",
        "/api/v1/product-registration-assets/references/${x.id}/content",
        "normalizeRegisteredSource", "[...registeredRows,...factRows]",
    ):
        assert marker in text

