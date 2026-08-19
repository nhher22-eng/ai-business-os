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
