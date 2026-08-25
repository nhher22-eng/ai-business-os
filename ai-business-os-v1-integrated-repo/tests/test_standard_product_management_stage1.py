from unittest.mock import MagicMock
import importlib

import pytest

from app.api.commerce_catalog import (
    ProductMasterBody,
    SKUManagementBody,
    update_product_master,
    update_sku_management,
)
from app.commerce_catalog_ui import DETAIL_HTML, HTML
from app.db.models import Product, ProductSKU
from app.services.commerce_codes import normalize_product_code


def test_product_code_is_normalized_and_restricted():
    assert normalize_product_code(" blueberry-net-60 ") == "BLUEBERRY-NET-60"
    assert normalize_product_code("prd_001.2") == "PRD_001.2"
    with pytest.raises(ValueError):
        normalize_product_code("상품 코드")


def test_product_master_update_preserves_code_and_saves_standard_fields():
    product = Product(
        id="p1", tenant_id="t1", workspace_id="w1",
        product_code="KEEP-001", name="이전 이름", status="draft",
    )
    db = MagicMock()
    db.scalar.return_value = product
    result = update_product_master(
        "p1",
        ProductMasterBody(
            name="표준 상품", status="active", category="원예",
            brand="GrowFrame", model_name="GF-01", manufacturer="제조사",
            country_of_origin="대한민국", supplier_name="공급처",
        ),
        tenant_id="t1", db=db,
    )
    assert result["product_code"] == "KEEP-001"
    assert product.category == "원예"
    assert product.supplier_name == "공급처"
    db.commit.assert_called_once()


def test_sku_update_calculates_margin_and_stock_warning():
    sku = ProductSKU(
        id="s1", tenant_id="t1", product_id="p1", sku_code="SKU-001-01",
        name="기본", status="active", sales_unit="each",
    )
    db = MagicMock()
    db.scalar.return_value = sku
    result = update_sku_management(
        "s1",
        SKUManagementBody(
            name="10m", option_value="10m", purchase_cost=4000,
            list_price=10000, sale_price=8000, current_stock=5,
            available_stock=2, safety_stock=3, incoming_stock=10,
            storage_location="A-01",
        ),
        tenant_id="t1", db=db,
    )
    assert result["margin"] == 4000
    assert result["margin_rate"] == 50.0
    assert result["stock_warning"] is True
    assert result["incoming_stock"] == 10


def test_management_center_separates_new_registration_and_existing_edit():
    assert "상품관리 센터" in HTML
    assert "＋ 신규 상품 등록" in HTML
    assert "/commerce-catalog/product/${p.id}" in HTML
    assert "상품 상세·수정" in DETAIL_HTML
    assert "변경사항 저장" in DETAIL_HTML


def test_stage_one_sections_and_scope_are_visible():
    for marker in (
        "기본정보", "옵션·SKU·가격·재고", "상품 콘텐츠", "판매채널",
        "매입원가", "정상 판매가", "가용재고", "안전재고", "입고 예정",
        "FACT·원본 자료", "네이버", "쿠팡", "자사몰",
    ):
        assert marker in DETAIL_HTML
    assert "주문 자동 차감은 이후 단계" in DETAIL_HTML
    assert "전체 등록항목과 엑셀 연동은 2단계" in DETAIL_HTML


def test_stage_one_migration_follows_commerce_master():
    migration = importlib.import_module(
        "migrations.versions.0017_standard_product_management"
    )
    assert migration.down_revision == "0016_commerce_master"
