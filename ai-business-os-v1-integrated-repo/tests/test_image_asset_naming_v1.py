from app.services.image_studio import build_asset_filename


def test_image_element_asset_filename_is_stable_and_meaningful():
    name = build_asset_filename(
        product_code="IRRIGATION-8MM-KIT",
        role_code="SPEC_SIZE",
        usage_code="DETAIL_PAGE",
        stage="final",
        version=2,
    )
    assert name == "IRRIGATION-8MM-KIT_SPEC_SIZE_DETAIL_PAGE_FINAL_V02.png"
