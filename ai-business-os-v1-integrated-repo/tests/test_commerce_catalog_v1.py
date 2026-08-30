from unittest.mock import MagicMock

from app.api.product_registration import NewProductBody
from app.db.models import Product
from app.services.commerce_codes import next_sku_code


def test_registration_contract_allows_automatic_code_and_default_sku():
    body = NewProductBody(workspace_id="ws", name="옵션 없는 상품")
    assert body.product_code is None
    assert body.options == []


def test_registration_contract_accepts_options():
    body = NewProductBody(workspace_id="ws", name="관수키트", options=["10m", "20m", "30m"])
    assert body.options == ["10m", "20m", "30m"]


def test_next_sku_code_uses_product_number_and_increments():
    db = MagicMock()
    db.scalars.return_value.all.return_value = ["SKU-000123-01", "SKU-000123-02"]
    product = Product(id="p", tenant_id="t", workspace_id="w", product_code="PRD-000123", name="상품")
    assert next_sku_code(db, product) == "SKU-000123-03"


def test_legacy_product_code_is_preserved_in_sku_prefix():
    db = MagicMock()
    db.scalars.return_value.all.return_value = []
    product = Product(id="p", tenant_id="t", workspace_id="w", product_code="LEGACY-CODE", name="상품")
    assert next_sku_code(db, product) == "SKU-LEGACY-CODE-01"
