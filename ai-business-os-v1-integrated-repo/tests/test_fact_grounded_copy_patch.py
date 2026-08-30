from app.services.fact_grounded_copy_patch import apply_fact_grounding


def test_repotting_mat_hero_and_problem_use_only_current_product_facts():
    sections = [
        {
            "section_type": "HERO",
            "source_type": "copy",
            "content_json": {
                "title": "분갈이 매트",
                "headline": "여러 화분의 물주기, 하나의 관수라인으로",
                "subheadline": "상품 정보에 기반해 핵심 용도를 명확하게 보여줍니다.",
            },
        },
        {
            "section_type": "PROBLEM",
            "source_type": "copy",
            "content_json": {
                "title": "이런 경우에",
                "items": [
                    "여러 화분을 한 번에 관리하고 싶은 경우",
                    "베란다·텃밭·플랜터에 관수라인이 필요한 경우",
                    "설치 규모에 맞는 길이 옵션을 선택하고 싶은 경우",
                ],
            },
        },
    ]
    snapshot = {
        "product": {"name": "분갈이 매트", "description": None},
        "detail": {
            "usage": "실내 식물 분갈이, 베란다 가드닝 작업 시 주변 오염을 줄이기 위한 작업용 매트",
            "usage_conditions": "실내 또는 베란다 등에서 분갈이·원예 작업 시 사용",
        },
    }

    grounded = apply_fact_grounding(sections, snapshot)
    hero = grounded[0]["content_json"]
    problem = grounded[1]["content_json"]

    assert hero["headline"] == snapshot["detail"]["usage"]
    assert hero["subheadline"] == snapshot["detail"]["usage_conditions"]
    assert hero["copy_status"] == "fact_grounded"
    assert problem["title"] == "사용 용도·조건"
    assert problem["items"] == [
        snapshot["detail"]["usage"],
        snapshot["detail"]["usage_conditions"],
    ]
    assert problem["copy_status"] == "fact_grounded"
    assert "관수라인" not in str(grounded)


def test_missing_usage_does_not_invent_product_specific_problem_copy():
    sections = [
        {"section_type": "HERO", "source_type": "copy", "content_json": {}},
        {"section_type": "PROBLEM", "source_type": "copy", "content_json": {}},
    ]
    snapshot = {
        "product": {"name": "새 상품", "description": None},
        "detail": {"usage": None, "usage_conditions": None},
    }

    grounded = apply_fact_grounding(sections, snapshot)
    assert grounded[0]["content_json"]["headline"] == "새 상품"
    assert grounded[1]["content_json"]["items"] == []
    assert grounded[1]["content_json"]["copy_status"] == "missing_fact"
