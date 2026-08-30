from datetime import datetime, timezone

from app.services.canva_v12_execution import build_canva_v12_execution_package
from app.services.canva_v12_image_export import assemble_canva_v12_image_draft
from app.services.canva_v12_text_export import (
    CANVA_BRAND_TEMPLATE_ID,
    CANVA_V12_IMAGE_FIELDS,
    CANVA_V12_TEXT_FIELDS,
    assemble_canva_v12_text_draft,
)


def test_8mm_irrigation_kit_reaches_exact_94_field_canva_contract():
    approved_copy = {name: f"승인 문안 · {name}" for name in CANVA_V12_TEXT_FIELDS}
    text = assemble_canva_v12_text_draft(
        product={
            "name": "8mm 자동 관수키트",
            "product_code": "IRRIGATION-8MM-KIT",
            "manufacturer": "확정 제조사",
            "country_of_origin": "대한민국",
        },
        profile={"dimensions": {"호스 외경": "8mm"}, "primary_material": "확정 재질"},
        skus=[
            {"name": "10m", "option_value": "10m", "status": "active"},
            {"name": "20m", "option_value": "20m", "status": "active"},
            {"name": "30m", "option_value": "30m", "status": "active"},
        ],
        approved_copy=approved_copy,
    )
    assets = []
    for index, slot in enumerate(CANVA_V12_IMAGE_FIELDS, start=1):
        assets.append({
            "id": f"approved-image-{index}",
            "asset_stage": "final",
            "status": "approved",
            "qa_status": "pass",
            "approved_at": datetime.now(timezone.utc),
            "asset_uri": f"media://irrigation/{index}.png",
            "asset_metadata": {"canva_v12_field": slot},
        })
    images = assemble_canva_v12_image_draft(assets)
    images["eligible_assets"] = [
        {"id": asset["id"], "canva_asset_id": f"canva-asset-{index}"}
        for index, asset in enumerate(assets, start=1)
    ]
    package = build_canva_v12_execution_package(text_draft=text, image_draft=images)

    assert text["matched"] == "72/72"
    assert images["matched"] == "22/22"
    assert package["brand_template_id"] == CANVA_BRAND_TEMPLATE_ID == "EAHTvwXU8Ig"
    assert package["execution_ready"] is True
    assert len(package["autofill_data"]) == 94
    assert package["autofill_data"]["product_name"]["text"] == "8mm 자동 관수키트"
    assert package["autofill_data"]["option_1_name"]["text"] == "10m"
    assert package["autofill_data"]["hero_image"]["asset_id"] == "canva-asset-1"


def test_irrigation_contract_fails_closed_before_canva_upload_finishes():
    text = {
        "ready": True,
        "matched": "72/72",
        "missing_fields": (),
        "text_fields": {name: f"approved:{name}" for name in CANVA_V12_TEXT_FIELDS},
    }
    images = {
        "ready": True,
        "matched": "22/22",
        "missing_fields": (),
        "image_fields": {name: f"internal:{name}" for name in CANVA_V12_IMAGE_FIELDS},
        "eligible_assets": [],
    }
    package = build_canva_v12_execution_package(text_draft=text, image_draft=images)
    assert package["execution_ready"] is False
    assert package["autofill_data"] is None
    assert package["blockers"] == ("canva_asset_upload_pending",)
