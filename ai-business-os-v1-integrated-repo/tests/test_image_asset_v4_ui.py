from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_image_asset_v4_route_and_four_stage_contract():
    response = client.get("/image-assets")
    assert response.status_code == 200
    text = response.text
    assert text.count('data-stage="') == 4
    for label in ("1 원본 확인", "2 요소 설정", "3 제작·예산", "4 통합 검토·승인"):
        assert label in text
    assert "FACT 기반 제작 실행" not in text
    assert "제작계획 최종 승인·실행" in text


def test_dec_084_element_names_order_and_modes():
    text = client.get("/image-assets").text
    codes = [
        "MAIN", "PRODUCT_FRONT", "PRODUCT_45", "PRODUCT_SIDE", "PRODUCT_TOP",
        "PRODUCT_BOTTOM", "LIFESTYLE", "DETAIL", "COMPONENTS", "GROUP",
        "INFOGRAPHIC", "UNASSIGNED",
    ]
    positions = [text.index("{code:'" + code + "'") for code in codes]
    assert positions == sorted(positions)
    assert "대표 MAIN" in text
    assert "{code:'GROUP',name:'제품군 모음사진'" in text
    assert "{code:'GROUP',name:'제품군 모음사진',rule:'제품군 간 배율·간격·정렬·그림자 통일',on:false,mode:''}" in text
    assert "1차 원본 보정" in text
    assert "2차 요소 조합" in text
    assert "규칙·구도를 직접 입력" in text


def test_product_sources_budget_review_and_per_product_approval_are_connected():
    text = client.get("/image-assets").text
    for marker in (
        "/api/v1/product-image-facts/products/",
        "recalculate()",
        "markProductionReady()",
        "aiosImageAssetV4:",
        "aiosImageAssetsApproved:",
        "previewModal",
        'href="/image-studio"',
        'href="/business-home"',
    ):
        assert marker in text
