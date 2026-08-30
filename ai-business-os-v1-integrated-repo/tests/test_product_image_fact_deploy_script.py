from pathlib import Path


def test_product_image_fact_deploy_script_has_safety_contract():
    text = Path("scripts/deploy_product_image_fact_v1.sh").read_text()

    assert "pg_dump" in text
    assert "pytest -q" in text
    assert "docker compose run --rm migrate" in text
    assert "0010_product_image_fact" in text
    assert "/api/v1/product-image-facts/products/{product_id}/batch-upload" in text
    assert "health/live" in text
    assert "health/ready" in text
