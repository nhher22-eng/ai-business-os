from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agent_work_ui import HTML as AGENT_HTML
from app.db.models import Base, BusinessWorkspace, Product
from app.global_navigation import GLOBAL_STYLE, navigation_markup
from app.product_detail_v2_ui import DETAIL_HTML_V2
from app.services.agent_tools import build_plan


def test_global_agent_launcher_is_available_on_desktop_and_mobile():
    markup = navigation_markup(False)
    assert 'id="aiosAgentLaunch"' in markup
    assert "source_path:path" in markup
    assert "context_product_id" in markup
    assert ".aios-agent-launch" in GLOBAL_STYLE


def test_product_detail_has_context_agent_entry():
    assert 'id="productAgent"' in DETAIL_HTML_V2
    assert "이 상품을 Agent에게 요청" in DETAIL_HTML_V2
    assert "context_product_id=${encodeURIComponent(product.id)}" in DETAIL_HTML_V2


def test_agent_workspace_accepts_screen_and_product_context():
    assert "query.get('context_product_id')" in AGENT_HTML
    assert "form.append('context_product_id',contextProductId)" in AGENT_HTML
    assert "현재 업무 화면에서 호출됨" in AGENT_HTML


def test_context_product_is_the_first_plan_candidate():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        workspace = BusinessWorkspace(tenant_id="t", name="Commerce", slug="commerce")
        db.add(workspace)
        db.flush()
        product = Product(
            tenant_id="t", workspace_id=workspace.id,
            product_code="CTX-1", name="연결 상품", category="비료",
        )
        db.add(product)
        db.commit()
        plan = build_plan(
            db, tenant_id="t", workflow="기존 상품 수정",
            request_text="판매가 알려줘", staged=[],
            context_product_id=product.id,
        )
        assert plan["candidates"][0]["id"] == product.id
        assert plan["candidates"][0]["context_selected"] is True
