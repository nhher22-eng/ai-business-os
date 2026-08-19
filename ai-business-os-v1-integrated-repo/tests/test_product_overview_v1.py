from app import dashboard_ui, product_registration_ui
from app.product_content_basis_ui_patch import inject_product_content_basis_editor
from app.product_management_ui_patch import inject_product_management_mode
from app.product_overview_ui import HTML as OVERVIEW_HTML, inject_product_overview_link
from app.product_registration_image_restore_ui_patch import inject_product_image_restore
from app.product_registration_resume_ui_patch import inject_product_registration_resume


def test_product_overview_has_management_links_and_status_columns():
    assert '전체 상품' in OVERVIEW_HTML
    assert 'FACT' in OVERVIEW_HTML
    assert '콘텐츠 기준정보' in OVERVIEW_HTML
    assert 'SKU' in OVERVIEW_HTML
    assert '상세페이지' in OVERVIEW_HTML
    assert '/product-registration?product_id=' in OVERVIEW_HTML
    assert '＋ 새 상품 등록' in OVERVIEW_HTML


def test_dashboard_product_overview_link_is_idempotent():
    once = inject_product_overview_link(dashboard_ui.HTML)
    twice = inject_product_overview_link(once)
    assert 'href="/products"' in once
    assert once == twice


def test_existing_product_management_mode_composes_with_m07_patches():
    html = product_registration_ui.HTML
    html = inject_product_registration_resume(html)
    html = inject_product_image_restore(html)
    html = inject_product_content_basis_editor(html)
    html = inject_product_management_mode(html)

    assert 'loadExistingProductFromUrl' in html
    assert '상품 정보 관리' in html
    assert 'product_id' in html
    assert '기존 상품을 불러왔습니다' in html
    assert '현재 저장된 이미지' in html
    assert 'editedBasisPayload' in html
    assert 'showSavedContentBasis' in html


def test_management_mode_does_not_change_new_product_path():
    html = inject_product_management_mode(
        inject_product_content_basis_editor(
            inject_product_image_restore(
                inject_product_registration_resume(product_registration_ui.HTML)
            )
        )
    )
    assert "if(!id)return false" in html
    assert "if(productId&&new URLSearchParams(location.search).get('product_id'))" in html
