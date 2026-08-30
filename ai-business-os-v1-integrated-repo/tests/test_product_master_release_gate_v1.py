from app.services.product_master_release_gate_patch import apply_product_master_release_gate


def test_selling_release_is_blocked_when_required_product_image_is_missing():
    base = {
        "ready": True,
        "missing": [],
        "missing_labels": [],
        "has_product_name": True,
        "has_master_fact": True,
    }
    registration = {
        "facts_confirmed": True,
        "primary_asset_linked": True,
        "image_readiness": {
            "ready": False,
            "missing_slots": ["FRONT"],
            "missing_labels": ["정면"],
        },
    }

    result = apply_product_master_release_gate(base, registration)

    assert result["ready"] is False
    assert result["product_master_ready"] is False
    assert "product_master_core" in result["missing"]
    assert "정면" in result["missing_labels"]
    assert result["product_master_missing_labels"] == ["정면"]


def test_selling_release_is_blocked_when_master_fact_is_not_user_confirmed():
    base = {"ready": True, "missing": [], "missing_labels": []}
    registration = {
        "facts_confirmed": False,
        "primary_asset_linked": True,
        "image_readiness": {"ready": True, "missing_labels": []},
    }

    result = apply_product_master_release_gate(base, registration)

    assert result["ready"] is False
    assert "Product Master FACT 사용자 확정" in result["missing_labels"]


def test_selling_release_passes_only_when_existing_checks_and_product_master_pass():
    registration = {
        "facts_confirmed": True,
        "primary_asset_linked": True,
        "image_readiness": {"ready": True, "missing_labels": []},
    }

    passed = apply_product_master_release_gate(
        {"ready": True, "missing": [], "missing_labels": []},
        registration,
    )
    assert passed["ready"] is True
    assert passed["product_master_ready"] is True
    assert passed["product_master_missing_labels"] == []

    existing_failure = apply_product_master_release_gate(
        {
            "ready": False,
            "missing": ["other_release_check"],
            "missing_labels": ["기존 필수 검증"],
        },
        registration,
    )
    assert existing_failure["ready"] is False
    assert existing_failure["product_master_ready"] is True
    assert existing_failure["missing"] == ["other_release_check"]
