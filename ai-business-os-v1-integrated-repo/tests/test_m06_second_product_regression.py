from app.services.canva_controlled_export import build_controlled_canva_contract


def _second_product_payload():
    return {
        "template": {
            "code": "A_PRACTICAL_TRUST",
            "canva_brand_template_id": "EAHSqrpWE7g",
        },
        "product_facts": {
            "product": {
                "id": "p-net",
                "product_code": "NET-ZIP",
                "name": "과수 보호 지퍼형 방충망",
                "description": "과수 보호용 완제품 방충망 세트",
                "sales_channel": "naver-smartstore",
            },
            "detail": {
                "specification": "지퍼형 · 60메쉬",
                "usage": "과수 및 열매 보호",
                "installation_method": "대상 수목 또는 프레임에 씌워 사용",
                "usage_conditions": None,
                "cautions": None,
            },
            "skus": [
                {
                    "id": "s-net-1",
                    "sku_code": "NET-S",
                    "name": "소형",
                    "option_value": "소형",
                    "status": "active",
                    "components": [],
                }
            ],
        },
        "sections": [
            {"type": "HERO", "enabled": True, "source_type": "fact", "content": {"title": "과수 보호 지퍼형 방충망"}, "image_asset_id": "approved-net-hero"},
            {"type": "PROBLEM", "enabled": True, "source_type": "copy", "content": {"items": ["열매 보호"]}, "image_asset_id": None},
            {"type": "LIFESTYLE", "enabled": True, "source_type": "fact", "content": {"body": "과수 및 열매 보호"}, "image_asset_id": "approved-net-life"},
            {"type": "FEATURE", "enabled": True, "source_type": "fact", "content": {"specification": "지퍼형 · 60메쉬"}, "image_asset_id": None},
            {"type": "OPTION_COMPARE", "enabled": True, "source_type": "fact", "content": {"options": ["소형"]}, "image_asset_id": None},
            {"type": "COMPONENTS", "enabled": True, "source_type": "fact", "content": {"components": ["완제품 방충망 세트"]}, "image_asset_id": None},
            {"type": "INSTALLATION", "enabled": True, "source_type": "fact", "content": {"body": "대상 수목 또는 프레임에 씌워 사용"}, "image_asset_id": None},
            {"type": "SPEC", "enabled": True, "source_type": "fact", "content": {"specification": "지퍼형 · 60메쉬"}, "image_asset_id": None},
            {"type": "FAQ", "enabled": True, "source_type": "copy", "content": {"items": []}, "image_asset_id": None},
        ],
    }


def test_second_product_generates_same_9p_release_structure_without_irrigation_assumptions():
    contract = build_controlled_canva_contract(export_payload=_second_product_payload())
    assert contract["target"]["release_candidate_pages"] == list(range(1, 10))
    assert contract["source_snapshot"]["product"]["product_code"] == "NET-ZIP"
    assert contract["source_snapshot"]["detail"]["specification"] == "지퍼형 · 60메쉬"
    assert contract["section_payloads"]["INSTALLATION"]["content"]["body"] == "대상 수목 또는 프레임에 씌워 사용"
    assert contract["conditional_sections"]["included"] == []


def test_second_product_export_keeps_image_truth_policy_and_no_invention_rules():
    contract = build_controlled_canva_contract(export_payload=_second_product_payload())
    policy = contract["source_policy"]
    assert policy["external_memory_fallback"] is False
    assert policy["invent_missing_fact"] is False
    assert policy["unapproved_image_fallback"] is False
    assert policy["customer_expectation_truth_first"] is True
    assert policy["reject_photo_vs_received_mismatch"] is True
    assert policy["product_geometry_color_material_components_locked"] is True
