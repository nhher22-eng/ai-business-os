from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_new_front_tool_routes_are_real_pages_and_legacy_generator_is_preserved():
    expected = {
        "/image-assets": "이미지 요소 자산 생성기",
        "/template-maker": "템플릿 제작기",
        "/detail-page-builder": "상세페이지 생성기",
        "/image-studio": "새 이미지 만들기",
    }
    for path, marker in expected.items():
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 200
        assert marker in response.text


def test_product_registration_uses_new_common_front_navigation():
    response = client.get("/product-registration")
    assert response.status_code == 200
    assert "공통 제작도구" in response.text
    assert "원본 이미지 FACT" in response.text
    assert 'href="/image-assets"' in response.text
    for label in (
        "상품 식별정보",
        "객관적 상품 FACT",
        "옵션·규격·구성품",
        "원본 자료 등록",
        "FACT 확인·완료",
    ):
        assert label in response.text
    assert "판매 문안·이미지 활용계획·AI 제안은 상품정보에 포함하지 않음" in response.text


def test_front_tools_use_existing_legacy_tenant_data():
    for path in ("/business-home", "/image-assets", "/template-maker", "/detail-page-builder"):
        response = client.get(path)
        assert "__legacy__" in response.text
        assert "tenant-demo" not in response.text
