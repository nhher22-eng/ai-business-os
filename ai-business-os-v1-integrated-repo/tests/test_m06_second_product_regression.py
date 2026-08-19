from app.services.canva_controlled_export import build_controlled_canva_contract


def _second_product_payload():
    """Second M06 product: repotting mat.

    Only the product identity is currently confirmed in the project record.
    Exact size, material, color, options, components, installation/use details,
    and approved images intentionally remain empty until real Product DB facts
    are connected. The regression test must prove that the pipeline does not
    invent those missing values.
    """
    return {
        "template": {
            "code": "A_PRACTICAL_TRUST",
            "canva_brand_template_id": "EAHSqrpWE7g",
        },
        "product_facts": {
            "product": {
                "id": "p-repotting-mat",
                "product_code": "REPOTTING-MAT",
                "name": "분갈이 매트",
                "description": None,
                "sales_channel": "naver-smartstore",
            },
            "detail": {
                "specification": None,
                "usage": None,
                "installation_method": None,
                "usage_conditions": None,
                "cautions": None,
            },
            "skus": [],
        },
        "sections": [
            {"type": "HERO", "enabled": True, "source_type": "fact", "content": {"title": "분갈이 매트"}, "image_asset_id": None},
            {"type": "PROBLEM", "enabled": True, "source_type": "copy", "content": {}, "image_asset_id": None},
            {"type": "LIFESTYLE", "enabled": True, "source_type": "fact", "content": {}, "image_asset_id": None},
            {"type": "FEATURE", "enabled": True, "source_type": "fact", "content": {}, "image_asset_id": None},
            {"type": "OPTION_COMPARE", "enabled": True, "source_type": "fact", "content": {"options": []}, "image_asset_id": None},
            {"type": "COMPONENTS", "enabled": True, "source_type": "fact", "content": {"components": []}, "image_asset_id": None},
            {"type": "INSTALLATION", "enabled": True, "source_type": "fact", "content": {"body": None}, "image_asset_id": None},
            {"type": "SPEC", "enabled": True, "source_type": "fact", "content": {"specification": None}, "image_asset_id": None},
            {"type": "FAQ", "enabled": True, "source_type": "copy", "content": {"items": []}, "image_asset_id": None},
        ],
    }


def test_second_product_is_repotting_mat_and_keeps_same_9p_release_structure():
    contract = build_controlled_canva_contract(export_payload=_second_product_payload())
    assert contract["target"]["release_candidate_pages"] == list(range(1, 10))
    assert contract["source_snapshot"]["product"]["product_code"] == "REPOTTING-MAT"
    assert contract["source_snapshot"]["product"]["name"] == "분갈이 매트"
    assert contract["conditional_sections"]["included"] == []


def test_repotting_mat_missing_facts_are_preserved_not_invented():
    contract = build_controlled_canva_contract(export_payload=_second_product_payload())
    snapshot = contract["source_snapshot"]
    assert snapshot["detail"]["specification"] is None
    assert snapshot["detail"]["usage"] is None
    assert snapshot["detail"]["installation_method"] is None
    assert snapshot["skus"] == []
    assert contract["section_payloads"]["INSTALLATION"]["content"]["body"] is None
    assert contract["section_payloads"]["SPEC"]["content"]["specification"] is None


def test_repotting_mat_export_keeps_image_truth_policy_and_no_invention_rules():
    contract = build_controlled_canva_contract(export_payload=_second_product_payload())
    policy = contract["source_policy"]
    assert policy["external_memory_fallback"] is False
    assert policy["invent_missing_fact"] is False
    assert policy["unapproved_image_fallback"] is False
    assert policy["customer_expectation_truth_first"] is True
    assert policy["reject_photo_vs_received_mismatch"] is True
    assert policy["product_geometry_color_material_components_locked"] is True
