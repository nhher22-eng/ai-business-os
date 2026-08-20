from app import product_registration_ui
from app.api.product_image_planning import router as image_planning_router
from app.product_content_basis_ui_patch import inject_product_content_basis_editor
from app.product_image_fact_ui_patch import inject_product_image_fact_ui
from app.product_image_planning_ui_patch import inject_product_image_planning_ui
from app.product_registration_readiness_ui_patch import inject_product_registration_readiness_ui
from app.services.product_image_planning import _fallback_plans, build_image_plan_suggestions


def test_image_planning_blocks_before_confirmed_fact():
    plans, meta = build_image_plan_suggestions(
        product_name="테스트 상품",
        facts={"facts_confirmed": False},
        image_slots=["FRONT", "RIGHT_45"],
        operating_info={"usage": ["일반 사용"]},
        marketing_info={"features": ["단순 구조"]},
    )
    assert plans == []
    assert meta["provider"] == "blocked"
    assert meta["reason"] == "facts_unconfirmed"


def test_fallback_has_two_fact_grounded_line_drawings_and_no_fake_dimensions():
    plans = _fallback_plans(
        facts={
            "facts_confirmed": True,
            "dimensions": {},
            "packaging": {},
            "fact_notes": None,
        },
        image_slots=["FRONT", "RIGHT_45", "DETAIL"],
        operating_info={"usage": ["일반적인 일상 사용"]},
        marketing_info={
            "features": ["실제 외형 확인"],
            "selling_points": [],
            "content_direction": "실제 사용성 중심",
        },
    )
    line = [p for p in plans if p["category"] == "line_drawing"]
    assert len(line) == 2
    assert any("정면 라인드로잉" in p["title"] for p in line)
    assert any("45도 라인드로잉" in p["title"] for p in line)
    front = next(p for p in line if "정면" in p["title"])
    assert front["status"] == "fact"
    assert "숫자는 표시하지 않습니다" in (front["note"] or "")
    assert "확정 치수 FACT" not in front["basis"]


def test_simple_usage_flow_is_not_complex_manual_content():
    plans = _fallback_plans(
        facts={"facts_confirmed": True, "dimensions": {}, "packaging": {}},
        image_slots=["FRONT", "RIGHT_45"],
        operating_info={"usage": ["분갈이"]},
        marketing_info={},
    )
    flow = next(p for p in plans if p["category"] == "simple_usage_flow")
    assert "복잡한 조립·설치·전문 사용법" in (flow["note"] or "")
    assert flow["execution"] == "2~5컷 콘텐츠 구성"


def test_image_planning_routes_are_registered():
    paths = {route.path for route in image_planning_router.routes}
    assert "/api/v1/product-registration/products/{product_id}/image-plan-suggestions" in paths
    assert "/api/v1/product-registration/products/{product_id}/image-plans/confirm" in paths
    assert "/api/v1/product-registration/products/{product_id}/image-plans" in paths


def test_registration_ui_contains_eight_planning_categories_without_direct_generation_link():
    html = product_registration_ui.HTML
    html = inject_product_content_basis_editor(html)
    html = inject_product_image_fact_ui(html)
    html = inject_product_image_planning_ui(html)
    html = inject_product_registration_readiness_ui(html)

    for text in (
        "① 메인 / 히어로",
        "② 사용 장면",
        "③ 특징 강조",
        "④ 부분 상세",
        "⑤ 간단 사용 / 활용 순서",
        "⑥ 라인드로잉 기본 2종",
        "⑦ 구성품 / 세트",
        "⑧ 추가 이미지 아이디어",
    ):
        assert text in html

    assert "선택한 이미지 기획 확정" in html
    assert "실제 이미지 생성은 등록 완료 조건이 아닙니다" in html
    assert "AI 이미지 생성 열기" not in html
    assert "nextImageStudio" not in html
    assert "registration_flow_complete" in html
