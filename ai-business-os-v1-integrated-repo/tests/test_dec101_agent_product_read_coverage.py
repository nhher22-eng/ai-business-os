import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agent_work_ui import HTML
from app.db.content_copy import ContentCopyAsset
from app.db.models import (
    Base, BusinessWorkspace, DetailPageJob, ImageReferenceAsset, Product,
    ProductSKU, SalesChannelListing,
)
from app.db.product_registration import ProductRegistrationProfile, ProductSourceAsset
from app.services.agent_tools import TOOL_PROTOCOL, build_plan, execute_tool, infer_action


def _catalog_product(db: Session):
    workspace = BusinessWorkspace(tenant_id="t", name="Commerce", slug="commerce-dec101")
    db.add(workspace)
    db.flush()
    product = Product(
        tenant_id="t", workspace_id=workspace.id, product_code="FERTILIZER-SOL-001",
        name="멀티블루 블루베리 전용비료", status="active", category="비료",
        brand="멀티블루", description="블루베리 생육을 위한 전용 비료입니다.",
        manufacturer="가든팜", country_of_origin="대한민국", supplier_name="가든팜 공급센터",
    )
    db.add(product)
    db.flush()
    sku = ProductSKU(
        tenant_id="t", product_id=product.id, sku_code="FER-BLU-140", name="140g",
        option_value="140g", sale_price=5500, current_stock=50, available_stock=48,
        safety_stock=5, incoming_stock=20, shipping_fee=3000,
    )
    db.add(sku)
    db.flush()
    db.add(ProductRegistrationProfile(
        tenant_id="t", product_id=product.id, primary_material="복합비료", weight="140g",
        packaging={"components": ["비료 1봉", "계량스푼"]}, facts_confirmed=True,
        operating_info={"usage": ["블루베리 화분"], "usage_instructions": ["월 1회 사용"]},
        marketing_info={"features": ["블루베리 맞춤 배합"], "selling_points": ["간편 사용"],
                        "product_notes": ["어린이 손이 닿지 않는 곳에 보관"]},
    ))
    db.add(ProductSourceAsset(
        tenant_id="t", product_id=product.id, source_kind="document",
        original_filename="성분표.pdf", content_type="application/pdf", asset_uri="local://facts",
        content_hash="a" * 64, size_bytes=1024,
    ))
    db.add(ImageReferenceAsset(
        tenant_id="t", product_id=product.id, asset_role="FRONT", asset_uri="local://front",
        original_filename="front.jpg",
    ))
    db.add(DetailPageJob(
        tenant_id="t", workspace_id=workspace.id, product_id=product.id,
        status="approved", current_version_no=2, approved_version_no=2,
    ))
    db.add(ContentCopyAsset(
        tenant_id="t", workspace_id=workspace.id, product_id=product.id,
        target_type="detail_page", slot_key="headline", slot_label="헤드라인",
        content="블루베리를 위한 맞춤 영양", status="approved",
    ))
    db.add(SalesChannelListing(
        tenant_id="t", product_id=product.id, sku_id=sku.id, channel="naver",
        status="linked", external_product_id="N-100", channel_price=5500,
    ))
    db.commit()
    return product


def test_integrated_product_read_intents_cover_description_sections_and_all():
    assert infer_action("블루베리 비료 상품설명 알려줘") == "product_section"
    assert infer_action("특징과 사용방법 알려줘") == "product_section"
    assert infer_action("가격 재고 배송정보 알려줘") == "product_section"
    assert infer_action("등록 자료 모두 보여줘") == "product_section"
    assert infer_action("판매콘텐츠 진행상태 알려줘") == "product_section"
    assert infer_action("판매채널 연결상태 알려줘") == "product_section"
    assert infer_action("이 상품 전체 정보 알려줘") == "product_full_detail"


def test_description_query_returns_stored_product_narrative_without_write():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        product = _catalog_product(db)
        plan = build_plan(db, tenant_id="t", workflow="일반 요청",
                          request_text="블루베리 비료 상품설명 알려줘", staged=[])
        assert plan["args"] == {"section": "description"}
        assert plan["approval_required"] is False
        result = json.loads(execute_tool(db, {
            "protocol": TOOL_PROTOCOL, "action": plan["action"], "tenant_id": "t",
            "product_id": product.id, "args": plan["args"],
        }))
        assert result["actual_change"] is False
        assert result["sections"][0]["label"] == "상품설명"
        assert result["sections"][0]["fields"]["기본 설명"] == "블루베리 생육을 위한 전용 비료입니다."
        assert result["sections"][0]["fields"]["특징"] == ["블루베리 맞춤 배합"]
        assert result["sections"][0]["fields"]["사용방법"] == ["월 1회 사용"]


def test_full_query_returns_all_seven_integrated_management_tabs():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        product = _catalog_product(db)
        result = json.loads(execute_tool(db, {
            "protocol": TOOL_PROTOCOL, "action": "product_full_detail", "tenant_id": "t",
            "product_id": product.id, "args": {},
        }))
        assert [section["label"] for section in result["sections"]] == [
            "상품정보", "상품설명", "옵션·SKU", "가격·재고·배송",
            "등록자료", "판매콘텐츠", "판매채널",
        ]
        assert result["sections"][2]["items"][0]["SKU 코드"] == "FER-BLU-140"
        assert result["sections"][3]["items"][0]["판매가"] == 5500
        assert len(result["sections"][4]["items"]) == 2
        assert len(result["sections"][5]["items"]) == 2
        assert result["sections"][6]["items"][0]["내부 상태"] == "linked"
        assert result["live_marketplace_verified"] is False
        assert "실시간 외부 상태" in result["notice"]


def test_agent_result_ui_marks_empty_values_as_unregistered():
    assert "function displayValue" in HTML
    assert "미등록" in HTML
    assert "sectionMarkup" in HTML
