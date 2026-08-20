from pathlib import Path


def test_product_dashboard_deploy_script_covers_current_runtime_contract():
    script = Path("scripts/deploy_product_registration_v1.sh").read_text(encoding="utf-8")

    assert "docker compose build api worker image_worker scheduler migrate" in script
    assert "docker compose up -d api worker image_worker scheduler" in script
    assert "products HTTP" in script
    assert "/api/v1/product-registration/products/{product_id}/readiness" in script
    assert "/api/v1/product-registration/products/{product_id}/image-plan-suggestions" in script
    assert "/api/v1/product-registration/products/{product_id}/image-plans/confirm" in script
    assert "/api/v1/product-registration/products/{product_id}/image-plans" in script
    assert "/api/v1/product-overview/products" in script
    assert "/api/v1/product-image-facts/products/{product_id}/batch-async" in script
    assert "⑥ 라인드로잉 기본 2종" in script
    assert "실제 이미지 생성은 등록 완료 조건이 아닙니다" in script
    assert "AI 이미지 생성 열기" in script  # negative runtime assertion is encoded in deploy script
    assert "direct Image Studio generation link must not exist" in script
    assert "docker compose exec -T api python" in script
    assert "Expanded Product Registration + Product Master deployment completed." in script
