from app.services.canva_v12_execution import build_canva_v12_execution_package
from app.services.canva_v12_text_export import CANVA_V12_IMAGE_FIELDS, CANVA_V12_TEXT_FIELDS


def _text(ready=True):
    return {
        "ready": ready,
        "matched": "72/72" if ready else "71/72",
        "missing_fields": () if ready else ("hero_subcopy",),
        "text_fields": {name: f"text:{name}" for name in CANVA_V12_TEXT_FIELDS},
    }


def _images(*, assigned=True, uploaded=True):
    fields = {name: f"internal:{name}" for name in CANVA_V12_IMAGE_FIELDS}
    if not assigned:
        fields["hero_image"] = ""
    assets = [
        {
            "id": internal_id,
            "canva_asset_id": f"canva:{field}" if uploaded else None,
        }
        for field, internal_id in fields.items()
        if internal_id
    ]
    return {
        "ready": assigned,
        "matched": "22/22" if assigned else "21/22",
        "missing_fields": () if assigned else ("hero_image",),
        "image_fields": fields,
        "eligible_assets": assets,
    }


def test_execution_package_contains_exact_94_typed_fields_when_ready():
    package = build_canva_v12_execution_package(
        text_draft=_text(), image_draft=_images()
    )
    assert package["execution_ready"] is True
    assert package["blockers"] == ()
    assert len(package["autofill_data"]) == 94
    assert package["autofill_data"]["hero_image"] == {
        "type": "image",
        "asset_id": "canva:hero_image",
    }


def test_internal_image_ids_are_never_treated_as_canva_asset_ids():
    package = build_canva_v12_execution_package(
        text_draft=_text(), image_draft=_images(uploaded=False)
    )
    assert package["execution_ready"] is False
    assert package["autofill_data"] is None
    assert package["images"]["canva_uploaded_count"] == 0
    assert "canva_asset_upload_pending" in package["blockers"]


def test_missing_text_and_image_assignment_are_reported_separately():
    package = build_canva_v12_execution_package(
        text_draft=_text(False), image_draft=_images(assigned=False)
    )
    assert package["execution_ready"] is False
    assert "text_not_ready" in package["blockers"]
    assert "image_slots_not_ready" in package["blockers"]
