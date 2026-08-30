import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agent_work_ui import HTML
from app.db.models import Base, BusinessWorkspace, Product, ProductSKU
from app.services.agent_tools import (
    TOOL_PROTOCOL,
    TOOL_REGISTRY,
    build_plan,
    execute_tool,
    infer_action,
    normalize,
    parse_sku_args,
)
from app.worker import execute


class DummyRun:
    task = "등록되지 않은 자유형 요청"


def test_common_query_intents_are_recognized():
    assert infer_action("블루베리 비료 상품 판매가 알려줘") == "product_price"
    assert infer_action("블루베리 비료 배송비 알려줘") == "shipping_fee"
    assert infer_action("블루베리 비료 SKU 구성 알려줘") == "sku_list"
    assert infer_action("대표이미지 보여줘") == "primary_image"
    assert infer_action("등록이미지 모두 보여줘") == "image_list"
    assert infer_action("상세페이지 보여줘") == "detail_page"
    assert infer_action("방충망 카테고리에 등록된 모든 상품 보여줘") == "category_products"
    assert infer_action("네이버에 상품등록이 되어 있는지 확인해줘") == "channel_status"


def test_write_intents_and_risk_registry():
    assert infer_action("사진 추가해줘", attachment_count=1) == "product_image_add"
    assert infer_action("5kg SKU 추가해줘") == "sku_add"
    assert TOOL_REGISTRY["product_price"] == {
        "risk": "read", "approval": False, "label": "판매가 조회"
    }
    assert TOOL_REGISTRY["sku_add"]["approval"] is True
    assert TOOL_REGISTRY["product_image_add"]["risk"] == "internal_write"


def test_sku_request_is_structured():
    args = parse_sku_args(
        "SKU 추가 해줘 5kg 입제 지퍼백 그리고 판매금액은 25,000원으로 해주고 재고 7개"
    )
    assert args["name"] == "5kg 입제 지퍼백"
    assert args["option_value"] == "5kg / 입제 / 지퍼백"
    assert args["sale_price"] == 25000
    assert args["current_stock"] == 7
    assert normalize("블루베리 전용 비료") == "블루베리전용비료"


def test_unregistered_worker_request_never_claims_actual_change():
    result = json.loads(execute(None, DummyRun(), 0))
    assert result["verified"] is False
    assert result["actual_change"] is False
    assert result["message"] == "요청 기록 완료 · 실제 상품 변경 없음"


def test_fuzzy_product_plan_and_sku_write_are_verified():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        workspace = BusinessWorkspace(tenant_id="t", name="Commerce", slug="commerce")
        db.add(workspace)
        db.flush()
        product = Product(
            tenant_id="t", workspace_id=workspace.id, product_code="FER-BLU",
            name="멀티블루 블루베리 전용비료", category="비료",
        )
        db.add(product)
        db.commit()

        plan = build_plan(
            db, tenant_id="t", workflow="기존 상품 수정",
            request_text="블루베리 비료 SKU 추가 해줘 5kg 입제 지퍼백 판매가는 25,000원",
            staged=[],
        )
        assert plan["action"] == "sku_add"
        assert plan["candidates"][0]["id"] == product.id

        result = json.loads(execute_tool(db, {
            "protocol": TOOL_PROTOCOL, "action": "sku_add", "tenant_id": "t",
            "product_id": product.id, "approval_confirmed": True,
            "args": plan["args"],
        }))
        assert result["verified"] is True
        assert result["actual_change"] is True
        saved = db.get(ProductSKU, result["sku"]["id"])
        assert saved is not None
        assert saved.sale_price == 25000
        assert saved.option_value == "5kg / 입제 / 지퍼백"


def test_agent_ui_uses_real_tool_api_and_verified_result_language():
    assert "/api/v1/agent-tools/plan" in HTML
    assert "/api/v1/agent-tools/execute" in HTML
    assert "실제 변경 완료" in HTML
    assert "요청 기록 완료 · 실제 상품 변경 없음" in HTML
    assert "대상 상품을 먼저 선택해 주세요" in HTML
