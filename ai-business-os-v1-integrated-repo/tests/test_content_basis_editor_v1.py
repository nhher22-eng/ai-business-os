import importlib.util
from pathlib import Path

from app import detail_page_ui, product_registration_ui
from app.api.detail_page_content_basis import ContentBasisBody, _normalized_basis
from app.detail_page_autogen_ui_patch import inject_autogen_ui
from app.detail_page_content_basis_ui_patch import inject_detail_page_content_basis_editor
from app.product_content_basis_ui_patch import inject_product_content_basis_editor
from app.product_registration_image_restore_ui_patch import inject_product_image_restore
from app.product_registration_resume_ui_patch import inject_product_registration_resume


def load_migration(name):
    path = Path("migrations/versions") / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_migration_chain_reaches_content_basis():
    m7 = load_migration("0007_product_registration")
    m8 = load_migration("0008_detail_page_content_basis")
    assert m7.down_revision == "0006_detail_page_studio"
    assert m8.down_revision == "0007_product_registration"


def test_product_registration_editor_composes_with_resume_and_image_restore():
    html = product_registration_ui.HTML
    html = inject_product_registration_resume(html)
    html = inject_product_image_restore(html)
    html = inject_product_content_basis_editor(html)

    assert "editedBasisPayload" in html
    assert "basis-row" in html
    assert "⚠ 확인 필요" in html
    assert "기존 상품을 불러와 FACT를 이어서 저장했습니다." in html
    assert "현재 저장된 이미지" in html


def test_product_registration_separates_editor_guidance_from_product_notes():
    html = product_registration_ui.HTML
    html = inject_product_registration_resume(html)
    html = inject_product_image_restore(html)
    html = inject_product_content_basis_editor(html)

    assert "AI 제안 편집 안내" in html
    assert "상품 관련 참고·주의" in html
    assert "product_notes" in html
    assert "productNoteItems" in html
    assert "marketing_info:{features,selling_points:selling,target_customer:targets,content_direction:direction,product_notes:productNotes}" in html


def test_detail_page_manual_basis_editor_composes_after_autogen_patch():
    html = inject_autogen_ui(detail_page_ui.HTML)
    html = inject_detail_page_content_basis_editor(html)

    assert "페이지 콘텐츠 기준정보" in html
    assert "이 페이지에만 저장" in html
    assert "상품 Master에도 반영" in html
    assert "savePageBasis" in html


def test_detail_page_basis_is_optional_and_deduplicated():
    body = ContentBasisBody(
        category="  방충망  ",
        usage=["블루베리 보호", "블루베리 보호", ""],
        features=["60메쉬", "지퍼형"],
        selling_points=[],
        target_customer=[],
        content_direction="",
        sync_product_master=False,
    )
    result = _normalized_basis(body)
    assert result["category"] == "방충망"
    assert result["usage"] == ["블루베리 보호"]
    assert result["selling_points"] == []
    assert result["target_customer"] == []
    assert result["content_direction"] is None
