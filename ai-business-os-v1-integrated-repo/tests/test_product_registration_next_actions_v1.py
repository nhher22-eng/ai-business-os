from app.product_image_fact_ui_patch import inject_product_image_fact_ui
from app.product_registration_async_restore_ui_patch import inject_async_restore_ui
from app.product_registration_readiness_ui_patch import inject_product_registration_readiness_ui
from app.product_registration_ui import HTML


def test_completed_product_master_offers_registration_next_work_actions_without_direct_image_generation():
    html = inject_product_image_fact_ui(HTML)
    html = inject_async_restore_ui(html)
    html = inject_product_registration_readiness_ui(html)

    assert 'id="nextDetailPage"' in html
    assert 'id="nextImageStudio"' not in html
    assert 'href="/products"' in html
    assert '>상세페이지 만들기<' in html
    assert '>AI 이미지 생성<' not in html
    assert '>전체 상품<' in html
    assert '`/detail-pages?product_id=${encodeURIComponent(productId)}`' in html
    assert '`/image-studio?product_id=${encodeURIComponent(productId)}`' not in html
    assert "setRegistrationNextActions();" in html


def test_next_actions_remain_hidden_until_full_registration_flow_is_complete():
    html = inject_product_image_fact_ui(HTML)
    html = inject_async_restore_ui(html)
    html = inject_product_registration_readiness_ui(html)

    assert "if(done)done.classList.add('hidden')" in html
    assert "if(done)done.classList.remove('hidden')" in html
    assert "registration_flow_complete" in html
    assert "/readiness?tenant_id=${tenant}" in html
