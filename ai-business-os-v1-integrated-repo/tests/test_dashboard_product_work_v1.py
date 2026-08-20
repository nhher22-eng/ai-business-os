from app.dashboard_product_work_ui_patch import inject_dashboard_product_work
from app.dashboard_ui import HTML
from app.product_overview_ui import inject_product_overview_link
from app.product_registration_ui import inject_product_registration_link


def test_dashboard_removes_demo_product_hardcode_and_prioritizes_incomplete_master():
    html = inject_product_registration_link(HTML)
    html = inject_product_overview_link(html)
    html = inject_dashboard_product_work(html)

    assert "IRRIGATION-8MM-KIT" not in html
    assert "/api/v1/product-overview/products" in html
    assert "products.find((x) => !x.master_ready)" in html
    assert 'id="needsAttentionCount"' in html
    assert "products.filter((x) => !x.master_ready).length" in html
    assert "등록 보완 계속하기 →" in html
    assert "/product-registration?product_id=${encodeURIComponent(product.id)}" in html
    assert "product.master_missing_labels" in html


def test_dashboard_keeps_operational_status_separate_from_master_readiness():
    html = inject_dashboard_product_work(HTML)

    assert '${product.status}' in html
    assert '${product.master_ready ? "Master 완료" : "보완 필요"}' in html
    assert 'if (!product.master_ready)' in html
    assert 'if (!product.master_ready) return;' in html
