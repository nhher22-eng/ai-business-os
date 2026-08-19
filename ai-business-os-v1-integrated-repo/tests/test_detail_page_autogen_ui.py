from app.detail_page_autogen_ui_patch import inject_autogen_ui
from app.detail_page_ui import HTML


def test_autogen_ui_injection_adds_primary_control_and_endpoint():
    patched = inject_autogen_ui(HTML)
    assert 'id="autogenBtn"' in patched
    assert '상세페이지 자동생성' in patched
    assert '/api/v1/detail-page-autogen/generate' in patched
    assert '수동 제작으로 시작' in patched


def test_autogen_ui_injection_is_idempotent():
    once = inject_autogen_ui(HTML)
    twice = inject_autogen_ui(once)
    assert twice == once


def test_autogen_ui_keeps_human_approval_controls():
    patched = inject_autogen_ui(HTML)
    assert '최종 승인' in patched
    assert 'Canva 전달 패키지' in patched


def test_repotting_mat_fact_editor_is_available_without_guessing_values():
    patched = inject_autogen_ui(HTML)
    assert '분갈이 매트 테스트 상품 준비' in patched
    assert "product_code:'REPOTTING-MAT'" in patched
    assert "name:'분갈이 매트'" in patched
    assert '확정 FACT 저장' in patched
    assert '/api/v1/business/product-detail' in patched
    assert '모르는 값은 비워두세요' in patched


def test_fact_editor_reuses_existing_product_and_rechecks_autogen():
    patched = inject_autogen_ui(HTML)
    assert "p.product_code==='REPOTTING-MAT'||p.name==='분갈이 매트'" in patched
    assert '저장 후 상세페이지 자동생성을 다시 실행' in patched
    assert 'FACT 보완 필요' in patched
