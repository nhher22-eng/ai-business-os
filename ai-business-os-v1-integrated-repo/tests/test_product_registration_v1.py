from app.product_registration_ui import inject_product_registration_link
from app.services.product_registration import (
    _fallback_suggestions,
    _ground_model_suggestions,
    build_ai_suggestions,
)


def test_fallback_suggestions_do_not_invent_physical_facts():
    result = _fallback_suggestions(
        "테스트 상품",
        {
            "primary_material": "steel",
            "country_of_origin": "KR",
            "dimensions": {},
            "packaging": {},
        },
    )

    assert result["operating"]["sale_price"] is None
    assert result["operating"]["cost"] is None
    assert "주재질: steel" in result["marketing"]["features"]
    assert result["category"] is None
    assert result["usage"] == []
    assert result["marketing"]["selling_points"] == []


def test_ai_suggestions_are_blocked_until_facts_are_confirmed():
    result, meta = build_ai_suggestions(
        "테스트 상품",
        {
            "primary_material": "steel",
            "facts_confirmed": False,
        },
    )
    assert meta["provider"] == "blocked-unconfirmed"
    assert result["marketing"]["features"] == []
    assert result["operating"]["category"] is None


def test_grounding_removes_unsupported_use_benefit_and_target_claims():
    raw = {
        "category": "방충망",
        "usage": ["창문 방충", "벌레 차단"],
        "operating": {"category": "방충망", "usage": ["창문 방충"]},
        "marketing": {
            "features": ["촘촘해서 효과적으로 벌레 차단"],
            "selling_points": ["쉬운 설치", "별도 조립 불필요"],
            "target_customer": ["가정용 창문 구매자"],
            "content_direction": "편리성 강조",
        },
        "warnings": [],
    }
    facts = {
        "facts_confirmed": True,
        "fact_notes": "60메쉬, 지퍼형, 완제품 세트",
    }

    result = _ground_model_suggestions(
        raw,
        product_name="블루베리 방충망",
        facts=facts,
    )

    assert result["category"] == "방충망"
    assert result["usage"] == []
    assert result["operating"]["usage"] == []
    assert result["marketing"]["features"] == ["60메쉬", "지퍼형", "완제품 세트"]
    assert result["marketing"]["selling_points"] == []
    assert result["marketing"]["target_customer"] == []
    rendered = str(result)
    assert "창문 방충" not in rendered
    assert "쉬운 설치" not in rendered
    assert "별도 조립 불필요" not in rendered
    assert "효과적으로 벌레 차단" not in rendered


def test_dashboard_link_injection_is_idempotent():
    html = '<button data-panel="products">상품 업무</button>'
    once = inject_product_registration_link(html)
    twice = inject_product_registration_link(once)

    assert '/product-registration' in once
    assert once == twice
