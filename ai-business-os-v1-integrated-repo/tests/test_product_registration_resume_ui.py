from app.product_registration_resume_ui_patch import inject_product_registration_resume
from app.product_registration_ui import HTML


def test_refresh_duplicate_save_resumes_existing_product():
    patched = inject_product_registration_resume(HTML)
    assert "resumeExistingProduct" in patched
    assert "기존 상품을 불러와 FACT를 이어서 저장했습니다." in patched
    assert "product already exists" in patched
    assert "method:'PUT'" in patched
    assert "/facts?tenant_id=${tenant}" in patched


def test_resume_ui_patch_is_idempotent():
    once = inject_product_registration_resume(HTML)
    twice = inject_product_registration_resume(once)
    assert once == twice
