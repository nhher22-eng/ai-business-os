import importlib.util
from pathlib import Path

from app import product_registration_ui
from app.api.product_operations import SKUCreateBody, SKUUpdateBody, ProductStatusBody
from app.product_content_basis_ui_patch import inject_product_content_basis_editor
from app.product_management_ui_patch import inject_product_management_mode
from app.product_operations_ui_patch import inject_product_operations_ui
from app.product_registration_image_restore_ui_patch import inject_product_image_restore
from app.product_registration_resume_ui_patch import inject_product_registration_resume


def load_migration(name):
    path = Path("migrations/versions") / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_migration_chain_reaches_product_operations():
    m8 = load_migration("0008_detail_page_content_basis")
    m9 = load_migration("0009_product_operations")
    assert m8.revision == "0008_detail_page_content_basis"
    assert m9.down_revision == "0008_detail_page_content_basis"


def test_product_operations_ui_composes_after_existing_management_mode():
    html = product_registration_ui.HTML
    html = inject_product_registration_resume(html)
    html = inject_product_image_restore(html)
    html = inject_product_content_basis_editor(html)
    html = inject_product_management_mode(html)
    html = inject_product_operations_ui(html)

    assert "상태 · SKU · 변경 이력" in html
    assert "loadProductOperations" in html
    assert "saveOperationStatus" in html
    assert "addOperationSku" in html
    assert "SKU 수정 저장" in html
    assert "최근 변경 이력" in html
    assert "await loadProductOperations()" in html


def test_operations_ui_is_hidden_for_new_product_until_management_mode_loads():
    html = product_registration_ui.HTML
    html = inject_product_registration_resume(html)
    html = inject_product_image_restore(html)
    html = inject_product_content_basis_editor(html)
    html = inject_product_management_mode(html)
    html = inject_product_operations_ui(html)
    assert '<section class="card hidden" id="operationsCard">' in html
    assert "card.classList.remove('hidden')" in html


def test_status_and_sku_contracts_are_conservative():
    assert ProductStatusBody(status="draft").status == "draft"
    assert ProductStatusBody(status="active").status == "active"
    create = SKUCreateBody(sku_code="SKU-1", name="옵션 1")
    assert create.status == "active"
    update = SKUUpdateBody(name="옵션 수정", status="inactive")
    assert update.status == "inactive"
