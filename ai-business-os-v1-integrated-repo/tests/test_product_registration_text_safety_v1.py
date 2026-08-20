from app.services.product_registration_safety_patch import (
    contains_unconfirmed_physical_claim,
    sanitize_ai_suggestions,
)


def test_product_name_material_hint_is_not_treated_as_fact():
    facts = {
        "facts_confirmed": True,
        "primary_material": None,
        "fact_notes": None,
        "dimensions": {},
        "certifications": [],
        "packaging": {},
    }
    assert contains_unconfirmed_physical_claim("우드 소재의 플랜터", facts) is True
    assert contains_unconfirmed_physical_claim("실내외 공간에서 사용", facts) is True
    assert contains_unconfirmed_physical_claim("튼튼한 구조", facts) is True


def test_confirmed_material_allows_matching_material_language():
    facts = {
        "facts_confirmed": True,
        "primary_material": "목재",
        "fact_notes": None,
        "dimensions": {},
        "certifications": [],
        "packaging": {},
    }
    assert contains_unconfirmed_physical_claim("목재 소재를 보여주는 상세 컷", facts) is False


def test_sanitizer_removes_unconfirmed_physical_copy_but_keeps_marketing_direction():
    facts = {
        "facts_confirmed": True,
        "primary_material": None,
        "fact_notes": None,
        "dimensions": {},
        "certifications": [],
        "packaging": {},
    }
    suggestions = {
        "category": None,
        "usage": ["실내외 공간에서 사용", "화분을 배치하는 용도"],
        "operating": {"category": None, "usage": ["실내외 공간에서 사용", "화분을 배치하는 용도"]},
        "marketing": {
            "features": ["우드 소재", "튼튼한 구조"],
            "selling_points": ["우드 감성 강조", "상품 형태를 깔끔하게 보여주는 구성"],
            "target_customer": ["야외 정원을 꾸미는 고객", "플랜터를 찾는 고객"],
            "content_direction": "우드 소재와 자연 친화성을 강조",
            "product_notes": ["추가 확인 필요: 실제 주재질", "실외 사용 가능"],
        },
        "editor": {
            "category": None,
            "usage": [
                {"value": "실내외 공간에서 사용", "source": "ai", "status": "review"},
                {"value": "화분을 배치하는 용도", "source": "ai", "status": "review"},
            ],
            "features": [
                {"value": "우드 소재", "source": "ai", "status": "review"},
                {"value": "모델명: WP-01", "source": "fact", "status": "confirmed"},
            ],
            "selling_points": [
                {"value": "우드 감성 강조", "source": "ai", "status": "review"},
                {"value": "상품 형태를 깔끔하게 보여주는 구성", "source": "ai", "status": "review"},
            ],
            "target_customer": [
                {"value": "야외 정원을 꾸미는 고객", "source": "ai", "status": "review"},
                {"value": "플랜터를 찾는 고객", "source": "ai", "status": "review"},
            ],
            "content_direction": {"value": "우드 소재와 자연 친화성을 강조", "source": "ai", "status": "review"},
            "product_notes": [
                {"value": "추가 확인 필요: 실제 주재질", "source": "ai", "status": "review"},
                {"value": "실외 사용 가능", "source": "ai", "status": "review"},
            ],
        },
        "warnings": [],
    }

    result = sanitize_ai_suggestions(suggestions, facts)

    assert result["usage"] == ["화분을 배치하는 용도"]
    assert result["marketing"]["selling_points"] == ["상품 형태를 깔끔하게 보여주는 구성"]
    assert result["marketing"]["target_customer"] == ["플랜터를 찾는 고객"]
    assert result["marketing"]["content_direction"] is None
    assert result["marketing"]["product_notes"] == ["추가 확인 필요: 실제 주재질"]
    assert [row["value"] for row in result["editor"]["features"]] == ["모델명: WP-01"]
