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
    fact_rows = result["editor"]["features"]
    assert any(row["value"] == "주재질: steel" and row["status"] == "confirmed" for row in fact_rows)


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


def test_model_physical_feature_hypotheses_are_not_exposed_as_product_features():
    raw = {
        "category": "방충망",
        "usage": ["블루베리 보호"],
        "operating": {"category": "방충망", "usage": ["블루베리 보호"]},
        "marketing": {
            "features": ["매우 튼튼한 구조", "친환경 소재"],
            "selling_points": ["확정된 60메쉬 사양을 중심으로 설명"],
            "target_customer": ["블루베리 재배자"],
            "content_direction": "실제 사양과 사용 장면 중심",
            "product_notes": ["추가 확인 필요: 실외 장기 사용 조건"],
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

    assert result["category"] is None
    editor = result["editor"]
    assert editor["category"] is None
    assert any(row["value"] == "블루베리 보호" and row["status"] == "review" for row in editor["usage"])
    assert any(row["value"] == "60메쉬" and row["source"] == "fact" for row in editor["features"])
    assert all(row["value"] not in {"매우 튼튼한 구조", "친환경 소재"} for row in editor["features"])
    assert any(row["value"] == "블루베리 재배자" and row["status"] == "review" for row in editor["target_customer"])
    assert any(row["value"].startswith("추가 확인 필요:") for row in editor["product_notes"])


def test_dashboard_link_injection_is_idempotent():
    html = '<button data-panel="products">상품 업무</button>'
    once = inject_product_registration_link(html)
    twice = inject_product_registration_link(once)

    assert '/product-registration' in once
    assert once == twice
