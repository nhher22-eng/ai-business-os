from app.agent_work_ui import HTML as AGENT_HTML
from app.global_navigation import navigation_markup
from app.product_detail_v2_ui import DETAIL_HTML_V2


def test_general_agent_window_is_distinct_from_four_task_workspace():
    assert "location.pathname==='/agent-request'" in AGENT_HTML
    assert "무엇을 도와드릴까요?" in AGENT_HTML
    assert "generic-agent" in AGENT_HTML
    assert '@router.get("/agent-request"' in open(
        "app/agent_work_ui.py", encoding="utf-8"
    ).read()


def test_global_agent_button_opens_general_agent_window():
    markup = navigation_markup(False)
    assert "launch.href='/agent-request?'" in markup
    assert 'href="/agent-request"' in markup


def test_product_agent_button_opens_general_window_with_context():
    assert 'id="productAgent" href="/agent-request"' in DETAIL_HTML_V2
    assert "`/agent-request?context_product_id=${encodeURIComponent(product.id)}" in DETAIL_HTML_V2


def test_existing_four_task_workspace_remains_available():
    assert 'data-task="new-product"' in AGENT_HTML
    assert 'data-task="edit-product"' in AGENT_HTML
    assert 'data-task="sales-channel"' in AGENT_HTML
    assert 'data-task="content"' in AGENT_HTML
