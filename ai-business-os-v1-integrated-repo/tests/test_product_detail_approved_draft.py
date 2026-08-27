"""Unified product management regression gate."""

from unittest.mock import MagicMock

from app.api.commerce_catalog import (
    ProductDetailSaveBody,
    ProductMasterBody,
    ProductNarrativeBody,
    SKUDetailUpdate,
    _registration_review,
    save_product_detail,
)
from app.commerce_catalog_ui import DETAIL_HTML
from app.db.models import Product, ProductSKU
from app.db.product_registration import ProductRegistrationProfile


def test_approved_detail_ui_has_six_areas_and_shared_execution_controls():
    for marker in (
        "상품정보", "옵션·SKU", "가격·재고·배송", "등록 자료",
        "판매콘텐츠", "판매채널", "AI 제안", "적용 설정 보기",
        "Agent 실행 허용", "변경사항 저장", "변경·작업이력",
    ):
        assert marker in DETAIL_HTML
    assert "/products/${product.id}/detail" in DETAIL_HTML
    assert "외부 반영은 별도 승인 필요" in DETAIL_HTML
    assert "/readiness-review?tenant_id=${tenant}" in DETAIL_HTML
    assert "등록 준비 점검 · REVIEW" in DETAIL_HTML
    assert ".slot-body .secondary{display:inline-flex;margin-top:10px}" in DETAIL_HTML


def test_registration_review_reports_real_missing_work_without_external_action():
    skus = [ProductSKU(
        id="s1", tenant_id="t1", product_id="p1", sku_code="P1-01",
        name="10m", status="active", sales_unit="each", sale_price=None,
        current_stock=0, available_stock=0, safety_stock=0, incoming_stock=0,
    )]

    result = _registration_review(
        skus=skus,
        listings=[],
        image_readiness={"missing_slots": ["FRONT"]},
        detail_page_ready=False,
    )

    assert result["status"] == "REVIEW"
    assert result["missing_labels"] == [
        "정면 원본 이미지", "SKU 판매가", "배송조건", "판매콘텐츠", "판매채널",
    ]
    assert result["external_actions_executed"] is False
    assert result["approval_required_before_external_execution"] is True


def test_detail_batch_save_updates_product_narrative_and_skus_once():
    product = Product(
        id="p1", tenant_id="t1", workspace_id="w1",
        product_code="KEEP-001", name="이전 이름", status="draft",
    )
    sku = ProductSKU(
        id="s1", tenant_id="t1", product_id="p1", sku_code="KEEP-001-01",
        name="기본", status="active", sales_unit="each",
        current_stock=0, available_stock=0, safety_stock=0, incoming_stock=0,
    )
    profile = ProductRegistrationProfile(
        id="r1", tenant_id="t1", product_id="p1",
        operating_info={}, marketing_info={},
    )
    db = MagicMock()
    db.scalar.side_effect = [product, profile]
    db.scalars.return_value.all.return_value = [sku]
    body = ProductDetailSaveBody(
        product=ProductMasterBody(name="새 이름", status="active", category="원예"),
        narrative=ProductNarrativeBody(
            features=[" 특징 "], advantages=["장점"], limitations=["제약"],
            recommended_uses=["정원"], cautions=["주의"],
        ),
        skus=[SKUDetailUpdate(
            id="s1", name="10m", option_value="10 m", sales_unit="set",
            status="active", purchase_cost=4000, sale_price=8000,
            current_stock=5, available_stock=4, safety_stock=2, incoming_stock=3,
        )],
    )

    result = save_product_detail("p1", body, tenant_id="t1", db=db)

    assert product.product_code == "KEEP-001"
    assert product.name == "새 이름"
    assert sku.name == "10m"
    assert profile.marketing_info["features"] == ["특징"]
    assert profile.operating_info["usage"] == ["정원"]
    assert result["external_actions_executed"] is False
    db.commit.assert_called_once()


def test_product_detail_loads_confirmed_image_facts_and_click_zoom():
    assert "/api/v1/product-image-facts/products/${product.id}" in DETAIL_HTML
    assert "confirmed=data.images.filter(x=>x.status===\'confirmed\')" in DETAIL_HTML
    assert "confirmed.find(x=>x.is_primary)||right" in DETAIL_HTML
    assert "object-fit:cover" in DETAIL_HTML
    assert "openLightbox(url,label)" in DETAIL_HTML
    assert \'aria-label="이미지 확대보기"\' in DETAIL_HTML
    assert "우측 45도 · 필수" in DETAIL_HTML
    assert "정면 · 필수" in DETAIL_HTML
