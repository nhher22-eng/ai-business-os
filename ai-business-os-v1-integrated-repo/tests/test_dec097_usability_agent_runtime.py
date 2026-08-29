from app.agent_work_ui import HTML as AGENT_HTML
from app.product_detail_v2_ui import DETAIL_HTML_V2
from app.product_registration_simple_ui import HTML as REGISTRATION_HTML


def test_registration_files_accumulate_across_multiple_selections():
    assert "selectedImages" in REGISTRATION_HTML
    assert "selectedDocuments" in REGISTRATION_HTML
    assert "addUnique(selectedImages" in REGISTRATION_HTML
    assert "$('images').value=''" in REGISTRATION_HTML


def test_product_detail_has_additive_images_and_inactive_sku_filter():
    assert "＋ 이미지 추가" in DETAIL_HTML_V2
    assert "pendingAssetFiles" in DETAIL_HTML_V2
    assert "multiple hidden" in DETAIL_HTML_V2
    assert "activeSkuEntries" in DETAIL_HTML_V2
    assert "deleteSku(" in DETAIL_HTML_V2


def test_agent_workspace_uses_real_run_api_and_ordered_steps():
    assert "직접 입력하기" not in AGENT_HTML
    assert "계획 수정 요청" in AGENT_HTML
    assert "'/api/v1/runs'" in AGENT_HTML
    assert "if(n>maxStep)return" in AGENT_HTML
    assert "배포 전 UI 구현본" not in AGENT_HTML

