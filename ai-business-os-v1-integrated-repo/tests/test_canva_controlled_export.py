from app.services.canva_controlled_export import build_controlled_canva_contract


def _base_payload():
    return {
        "template": {
            "code": "A_PRACTICAL_TRUST",
            "canva_brand_template_id": "EAHSqrpWE7g",
        },
        "product_facts": {
            "product": {
                "id": "p1",
                "product_code": "TEST-1",
                "name": "테스트 상품",
                "description": "확정 설명",
                "sales_channel": "naver-smartstore",
            },
            "detail": {
                "specification": "확정 규격",
                "usage": "확정 사용정보",
                "installation_method": None,
                "usage_conditions": None,
                "cautions": None,
            },
            "skus": [
                {
                    "id": "s1",
                    "sku_code": "TEST-10",
                    "name": "10m",
                    "option_value": "10m",
                    "status": "active",
                    "components": [],
                }
            ],
        },
        "sections": [
            {"type": "HERO", "enabled": True, "source_type": "copy", "content": {"title": "테스트 상품"}, "image_asset_id": "img-hero"},
            {"type": "PROBLEM", "enabled": True, "source_type": "copy", "content": {"items": ["문제 1"]}, "image_asset_id": None},
            {"type": "LIFESTYLE", "enabled": True, "source_type": "copy", "content": {"body": "확정 사용정보"}, "image_asset_id": "img-life"},
            {"type": "FEATURE", "enabled": True, "source_type": "copy", "content": {"product_specification": "확정 규격"}, "image_asset_id": None},
            {"type": "OPTION_COMPARE", "enabled": True, "source_type": "fact", "content": {"options": []}, "image_asset_id": None},
            {"type": "COMPONENTS", "enabled": True, "source_type": "fact", "content": {"components": []}, "image_asset_id": None},
            {"type": "INSTALLATION", "enabled": True, "source_type": "copy", "content": {"body": None}, "image_asset_id": None},
            {"type": "SPEC", "enabled": True, "source_type": "fact", "content": {"specification": "확정 규격"}, "image_asset_id": None},
            {"type": "FAQ", "enabled": True, "source_type": "copy", "content": {"items": []}, "image_asset_id": None},
        ],
    }


def test_contract_selects_exact_9p_sales_pages():
    contract = build_controlled_canva_contract(export_payload=_base_payload())
    assert contract["target"]["release_candidate_pages"] == list(range(1, 10))
    assert contract["target"]["release_candidate_section_order"] == [
        "HERO", "PROBLEM", "LIFESTYLE", "FEATURE", "OPTION_COMPARE",
        "COMPONENTS", "INSTALLATION", "SPEC", "FAQ",
    ]


def test_contract_forbids_memory_and_invention_fallbacks():
    contract = build_controlled_canva_contract(export_payload=_base_payload())
    policy = contract["source_policy"]
    assert policy["external_memory_fallback"] is False
    assert policy["invent_missing_fact"] is False
    assert policy["invent_review"] is False
    assert policy["invent_relation"] is False
    assert policy["unapproved_image_fallback"] is False


def test_contract_preserves_missing_values_instead_of_guessing():
    contract = build_controlled_canva_contract(export_payload=_base_payload())
    assert contract["source_snapshot"]["detail"]["installation_method"] is None
    assert contract["section_payloads"]["INSTALLATION"]["content"]["body"] is None
    assert contract["source_policy"]["missing_value_action"] == "leave_empty_or_review"


def test_contract_excludes_conditional_pages_when_not_exported():
    contract = build_controlled_canva_contract(export_payload=_base_payload())
    assert contract["conditional_sections"]["included"] == []
    assert set(contract["conditional_sections"]["excluded"]) == {
        "REVIEW_SUMMARY", "ADD_ON", "REVIEW_DETAIL", "RELATED_PRODUCTS"
    }
