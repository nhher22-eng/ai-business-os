from pathlib import Path


def test_product_dashboard_deploy_script_covers_current_runtime_contract():
    script = Path("scripts/deploy_product_registration_v1.sh").read_text(encoding="utf-8")

    assert "docker compose build api worker image_worker scheduler migrate" in script
    assert "docker compose up -d api worker image_worker scheduler" in script
    assert "products HTTP" in script
    assert "/api/v1/product-registration/products/{product_id}/readiness" in script
    assert "/api/v1/product-overview/products" in script
    assert "/api/v1/product-image-facts/products/{product_id}/batch-async" in script
    assert "docker compose exec -T api python" in script
    assert "Product Registration + Product Master + Dashboard deployment completed." in script
