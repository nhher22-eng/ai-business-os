from app.product_image_fact_ui_patch import inject_product_image_fact_ui
from app.product_registration_ui import HTML


def test_product_image_fact_ui_is_injected_once():
    rendered = inject_product_image_fact_ui(HTML)
    assert 'id="imageFactCard"' in rendered
    assert 'id="imageFactFiles"' in rendered
    assert '일괄 업로드 · 자동 정리' in rendered
    assert '45도 우측' in rendered
    assert '라이프스타일' in rendered
    assert rendered.count('id="imageFactCard"') == 1


def test_legacy_image_card_is_hidden_by_runtime_patch():
    rendered = inject_product_image_fact_ui(HTML)
    assert "legacyImageCard.style.display='none'" in rendered
