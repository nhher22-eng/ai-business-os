from __future__ import annotations


POLICY_VERSION = "commerce-image-approval.v1"
SELLING_PRODUCT_DEFAULT_PROTECTION = "hard_lock"

# Selling images are approved on customer-expectation truth, not aesthetics alone.
# The product is immutable; only environment/lighting/framing may be changed in
# HARD LOCK mode unless an explicitly verified product fact says otherwise.
APPROVAL_CRITERIA = (
    "product_shape_and_geometry_match",
    "product_color_and_material_match",
    "component_and_connection_match",
    "included_component_scope_match",
    "no_unverified_part_or_accessory",
    "no_misleading_prop_as_included_item",
    "no_customer_expectation_gap",
)

FAIL_REASONS = (
    "actual_product_looks_different",
    "unverified_component_generated",
    "component_removed_or_substituted",
    "color_material_or_geometry_changed",
    "prop_or_addon_can_be_mistaken_as_included",
    "image_can_reasonably_trigger_photo_vs_received_mismatch",
)

ALLOWED_HARD_LOCK_CHANGES = (
    "environment",
    "lighting",
    "camera_framing",
    "non_product_background_elements",
)


def approval_gate(*, protection_mode: str, image_type: str) -> dict:
    """Return the non-negotiable approval contract for a generated image."""
    selling_locked = protection_mode == SELLING_PRODUCT_DEFAULT_PROTECTION
    return {
        "policy_version": POLICY_VERSION,
        "selling_product_locked": selling_locked,
        "image_type": image_type,
        "approval_basis": "customer_expectation_truth_before_visual_quality",
        "criteria": list(APPROVAL_CRITERIA) if selling_locked else [],
        "fail_reasons": list(FAIL_REASONS) if selling_locked else [],
        "allowed_changes": list(ALLOWED_HARD_LOCK_CHANGES) if selling_locked else [],
        "requires_human_product_match_confirmation": selling_locked,
        "approval_rule": (
            "reject_if_customer_could_receive_product_and_reasonably_feel_image_is_different"
            if selling_locked
            else "standard_visual_qa"
        ),
    }
