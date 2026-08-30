from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.api.commerce_catalog import DeleteProductBody, delete_product
from app.commerce_catalog_ui import HTML
from app.db.models import Product


def _product():
    return Product(
        id="product-1",
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        product_code="TEST-PRODUCT-001",
        name="삭제 테스트 상품",
    )


def _db(product, sku_ids=(), listing_ids=()):
    db = MagicMock()
    db.scalar.return_value = product
    db.scalars.side_effect = [
        MagicMock(all=MagicMock(return_value=list(sku_ids))),
        MagicMock(all=MagicMock(return_value=list(listing_ids))),
    ]
    return db


def test_delete_requires_exact_product_code():
    db = _db(_product())
    with pytest.raises(HTTPException) as error:
        delete_product(
            "product-1",
            DeleteProductBody(confirm_product_code="WRONG", delete_linked_skus=True),
            tenant_id="tenant-1",
            db=db,
        )
    assert error.value.status_code == 409
    db.delete.assert_not_called()


def test_delete_requires_linked_sku_acknowledgement():
    db = _db(_product(), sku_ids=("sku-1",))
    with pytest.raises(HTTPException) as error:
        delete_product(
            "product-1",
            DeleteProductBody(confirm_product_code="TEST-PRODUCT-001"),
            tenant_id="tenant-1",
            db=db,
        )
    assert error.value.status_code == 409
    assert "SKU 1개" in error.value.detail
    db.delete.assert_not_called()


def test_delete_returns_impact_and_commits():
    product = _product()
    db = _db(product, sku_ids=("sku-1",), listing_ids=("listing-1",))
    result = delete_product(
        "product-1",
        DeleteProductBody(
            confirm_product_code="TEST-PRODUCT-001",
            delete_linked_skus=True,
        ),
        tenant_id="tenant-1",
        db=db,
    )
    assert result["product_code"] == "TEST-PRODUCT-001"
    assert result["deleted_skus"] == 1
    assert result["deleted_channel_listings"] == 1
    db.delete.assert_called_once_with(product)
    db.commit.assert_called_once()


def test_catalog_ui_has_two_step_delete_confirmation():
    assert 'class="danger"' in HTML
    assert "deleteProduct" in HTML
    assert "최종 확인을 위해 상품코드" in HTML
    assert "confirm_product_code" in HTML
