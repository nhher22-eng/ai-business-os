from app.services.image_approval_policy import POLICY_VERSION, approval_gate


def test_hard_lock_selling_image_uses_customer_expectation_truth_gate():
    gate = approval_gate(protection_mode="hard_lock", image_type="HERO")
    assert gate["policy_version"] == POLICY_VERSION
    assert gate["selling_product_locked"] is True
    assert gate["requires_human_product_match_confirmation"] is True
    assert gate["approval_basis"] == "customer_expectation_truth_before_visual_quality"
    assert "product_shape_and_geometry_match" in gate["criteria"]
    assert "product_color_and_material_match" in gate["criteria"]
    assert "component_and_connection_match" in gate["criteria"]
    assert "no_customer_expectation_gap" in gate["criteria"]
    assert "actual_product_looks_different" in gate["fail_reasons"]
    assert "prop_or_addon_can_be_mistaken_as_included" in gate["fail_reasons"]
    assert gate["approval_rule"] == (
        "reject_if_customer_could_receive_product_and_reasonably_feel_image_is_different"
    )


def test_hard_lock_only_allows_environmental_changes():
    gate = approval_gate(protection_mode="hard_lock", image_type="LIFESTYLE")
    assert set(gate["allowed_changes"]) == {
        "environment",
        "lighting",
        "camera_framing",
        "non_product_background_elements",
    }


def test_creative_mode_does_not_claim_selling_product_lock():
    gate = approval_gate(protection_mode="creative", image_type="BANNER")
    assert gate["selling_product_locked"] is False
    assert gate["requires_human_product_match_confirmation"] is False
    assert gate["criteria"] == []
    assert gate["fail_reasons"] == []
    assert gate["approval_rule"] == "standard_visual_qa"
