from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


client = TestClient(app)


def test_image_asset_ui_contains_dec085_flow():
    response = client.get("/image-assets")
    assert response.status_code == 200
    html = response.text
    assert "이번 제작에서 제외" in html
    assert "주 원본" in html
    assert "보조 참조" in html
    assert "이번 제작에 선택된 요소" in html
    assert "추가 가능한 요소" in html
    assert "제작계획 최종 승인·실행" in html
    assert "원본 다시 선택" in html
    assert "원본 추가 등록" in html
    assert "registeredRows.length?registeredRows:factRows" in html
    assert "전체 합계" in html
    assert "element-mini" in html
    assert "제작 승인 대상" in html
    assert "보완 대기 · 승인 제외" in html
    assert "data-source-class" in html
    assert "updateAssetSourceClass" in html
    assert "PRODUCT_BACK" in html
    assert "identity=(x,state)" in html
    assert "촬영 분류 변경·저장" in html
    assert "data-element-source" in html
    assert "직접 연결 원본" in html


def test_product_registration_shows_current_confirmed_source_thumbnails():
    response = client.get("/product-registration")
    assert response.status_code == 200
    assert "현재 등록 원본" in response.text
    assert "currentSourceImages" in response.text
    assert "loadCurrentSourceImages" in response.text
    assert "data-current-source-classification" in response.text
    assert "updateRegisteredSourceClassification" in response.text


def test_workflow_plan_and_execute_are_persistent_and_idempotent(tmp_path):
    old = settings.asset_storage_root
    settings.asset_storage_root = str(tmp_path)
    try:
        payload = {
            "product_id": "product-1",
            "sources": [{"id": "source-1", "primary": True}],
            "elements": [{
                "code": "MAIN", "name": "대표 MAIN", "mode": "primary",
                "selected": True, "ready": True, "preview_url": "/source.jpg",
            }],
            "quality": "standard", "resolution": "web",
            "budget_cap": 10000, "estimated_cost": 2800,
        }
        saved = client.put(
            "/api/v1/image-asset-workflows/product-1?tenant_id=tenant-1", json=payload
        )
        assert saved.status_code == 200
        assert saved.json()["status"] == "draft"

        first = client.post(
            "/api/v1/image-asset-workflows/product-1/execute?tenant_id=tenant-1", json=payload
        )
        second = client.post(
            "/api/v1/image-asset-workflows/product-1/execute?tenant_id=tenant-1", json=payload
        )
        assert first.status_code == second.status_code == 200
        assert first.json()["execution"]["plan_hash"] == second.json()["execution"]["plan_hash"]
        assert len(second.json()["execution"]["results"]) == 1

        loaded = client.get(
            "/api/v1/image-asset-workflows/product-1?tenant_id=tenant-1"
        )
        assert loaded.json()["status"] == "executing"
    finally:
        settings.asset_storage_root = old
