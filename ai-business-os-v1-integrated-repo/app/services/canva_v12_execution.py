from __future__ import annotations

from collections.abc import Mapping

from app.services.canva_v12_text_export import (
    CANVA_BRAND_TEMPLATE_ID,
    CANVA_V12_IMAGE_FIELDS,
    canva_v12_autofill_data,
)


def build_canva_v12_execution_package(
    *,
    text_draft: Mapping[str, object],
    image_draft: Mapping[str, object],
) -> dict[str, object]:
    """Build a fail-closed 94-field Canva execution package.

    Internal AI Business OS image IDs are never passed to Canva as asset IDs.
    Every selected image must first carry a real ``canva_asset_id`` produced by
    the future OAuth upload adapter.
    """
    text_ready = bool(text_draft.get("ready"))
    images_assigned = bool(image_draft.get("ready"))
    image_fields = image_draft.get("image_fields") or {}
    eligible = {
        str(row.get("id")): row
        for row in (image_draft.get("eligible_assets") or [])
        if isinstance(row, Mapping)
    }
    canva_image_fields: dict[str, str] = {}
    upload_pending: list[str] = []
    for field in CANVA_V12_IMAGE_FIELDS:
        internal_id = str(image_fields.get(field) or "")
        asset = eligible.get(internal_id) or {}
        canva_asset_id = str(asset.get("canva_asset_id") or "").strip()
        if canva_asset_id:
            canva_image_fields[field] = canva_asset_id
        else:
            upload_pending.append(field)

    blockers: list[str] = []
    if not text_ready:
        blockers.append("text_not_ready")
    if not images_assigned:
        blockers.append("image_slots_not_ready")
    if upload_pending:
        blockers.append("canva_asset_upload_pending")

    execution_ready = not blockers
    data = None
    if execution_ready:
        data = canva_v12_autofill_data(
            text_fields=text_draft.get("text_fields") or {},
            image_fields=canva_image_fields,
        )
    return {
        "schema_version": "canva-v1.2-autofill-execution.v1",
        "brand_template_id": CANVA_BRAND_TEMPLATE_ID,
        "field_count": 94,
        "text": {
            "ready": text_ready,
            "matched": text_draft.get("matched", "0/72"),
            "missing_fields": text_draft.get("missing_fields", ()),
        },
        "images": {
            "assigned_ready": images_assigned,
            "matched": image_draft.get("matched", "0/22"),
            "missing_fields": image_draft.get("missing_fields", ()),
            "canva_uploaded_count": len(canva_image_fields),
            "canva_upload_pending_fields": tuple(upload_pending),
        },
        "execution_ready": execution_ready,
        "blockers": tuple(blockers),
        "autofill_data": data,
    }
