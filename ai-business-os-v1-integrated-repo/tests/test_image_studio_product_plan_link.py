from pathlib import Path


SOURCE = Path("app/image_studio_ui.py").read_text(encoding="utf-8")


def test_image_jobs_are_filtered_by_selected_product():
    assert (
        "/api/v1/images/jobs?tenant_id=${tenant}"
        "&product_id=${encodeURIComponent(productId)}"
    ) in SOURCE


def test_image_studio_restores_requested_product_from_url():
    assert "new URLSearchParams(location.search).get('product_id')" in SOURCE
    assert "/image-studio?product_id=${encodeURIComponent(selected)}" in SOURCE


def test_image_studio_blocks_cross_product_job_open():
    assert "opened.product_id!==el('product').value" in SOURCE
    assert "현재 선택한 상품과 다른 이미지 작업은 열 수 없습니다." in SOURCE


def test_confirmed_product_image_plans_are_loaded():
    assert (
        "/api/v1/product-registration/products/${productId}"
        "/image-plans?tenant_id=${tenant}"
    ) in SOURCE
    assert "applyConfirmedImagePlan" in SOURCE
    assert "Product Image FACT를 변경하지 않습니다." in SOURCE
