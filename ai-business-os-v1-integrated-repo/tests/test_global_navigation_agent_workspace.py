from fastapi.testclient import TestClient

from app.agent_work_ui import HTML as AGENT_HTML
from app.global_navigation import NAV_CONTENT, navigation_markup
from app.main import app
from app.workflow_ui import HOME


def test_global_navigation_has_one_pc_and_mobile_menu_model():
    for label in ("오늘의 업무", "상품관리", "신규 상품 등록", "Agent에게 맡기기", "준비 중"):
        assert label in NAV_CONTENT
    markup = navigation_markup(False)
    for marker in ("aios-global-side", "aios-mobile-head", "aios-mobile-drawer", "전체메뉴"):
        assert marker in markup


def test_business_home_has_four_direct_and_agent_entries():
    for task in ("신상품 출시", "기존 상품 수정", "판매채널 등록", "콘텐츠 제작"):
        assert task in HOME
    assert HOME.count("Agent 호출") == 4
    assert "/product-registration" in HOME
    assert "/agent-workspace?task=new-product" in HOME
    assert "grid-template-columns:repeat(2" in HOME


def test_agent_workspace_contains_full_safe_conversation_flow():
    for label in ("1 요청", "2 확인", "3 계획", "4 승인", "5 결과"):
        assert label in AGENT_HTML
    for label in ("말하기", "사진·문서 첨부", "음성 대화", "계획 수정 요청", "Agent 실행 승인"):
        assert label in AGENT_HTML
    assert "외부 게시·가격 변경·판매 시작은 하지 않습니다" in AGENT_HTML
    assert "a.disabled=!c.checked" in AGENT_HTML
    assert "SpeechRecognition" in AGENT_HTML


def test_home_intro_is_four_seconds_and_skippable():
    markup = navigation_markup(True)
    assert "Welcome to AI Business OS" in markup
    assert "aiosIntroSkip" in markup
    assert "setTimeout(hide,4000)" in markup


def test_middleware_injects_navigation_into_html_only():
    client = TestClient(app)
    home = client.get("/business-home")
    assert home.status_code == 200
    assert "aios-global-style" in home.text
    assert "Welcome to AI Business OS" in home.text
    agent = client.get("/agent-workspace")
    assert agent.status_code == 200
    assert "aios-global-style" in agent.text
    assert "Welcome to AI Business OS" not in agent.text
    live = client.get("/health/live")
    assert live.headers["content-type"].startswith("application/json")
    assert live.json() == {"status": "ok"}
