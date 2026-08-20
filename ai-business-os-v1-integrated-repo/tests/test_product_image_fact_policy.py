from app.services.product_image_fact import PRIMARY_SLOT, REQUIRED_SLOTS, slot_policy


def test_right_45_is_required_primary_and_raw_is_temporary():
    policy = slot_policy("RIGHT_45")
    assert PRIMARY_SLOT == "RIGHT_45"
    assert "RIGHT_45" in REQUIRED_SLOTS
    assert policy["required"] is True
    assert policy["primary"] is True
    assert policy["remove_background"] is True
    assert policy["raw_retention_policy"] == "delete_on_confirm"


def test_front_is_required_but_not_primary():
    policy = slot_policy("FRONT")
    assert policy["required"] is True
    assert policy["primary"] is False
    assert policy["remove_background"] is True
    assert policy["raw_retention_policy"] == "delete_on_confirm"


def test_lifestyle_keeps_real_background_but_only_final_asset_is_canonical():
    policy = slot_policy("LIFESTYLE")
    assert policy["required"] is False
    assert policy["primary"] is False
    assert policy["remove_background"] is False
    assert policy["keep_background"] is True
    assert policy["raw_retention_policy"] == "final_only"


def test_detail_is_preserved_as_final_use_image_without_forced_cutout():
    policy = slot_policy("DETAIL")
    assert policy["remove_background"] is False
    assert policy["keep_background"] is True
    assert policy["raw_retention_policy"] == "final_only"
