from __future__ import annotations

from collections.abc import Iterable, Mapping

from app.services.canva_v12_text_export import CANVA_V12_IMAGE_FIELDS


CANVA_V12_IMAGE_SLOT_METADATA_KEY = "canva_v12_field"


def is_approved_canva_image(asset: Mapping[str, object]) -> bool:
    """Return whether an image is eligible for a customer-facing Canva export."""
    return (
        asset.get("asset_stage") == "final"
        and asset.get("status") == "approved"
        and asset.get("qa_status") == "pass"
        and asset.get("approved_at") is not None
        and bool(str(asset.get("asset_uri") or "").strip())
    )


def image_slot(asset: Mapping[str, object]) -> str:
    metadata = asset.get("asset_metadata") or {}
    if not isinstance(metadata, Mapping):
        return ""
    return str(metadata.get(CANVA_V12_IMAGE_SLOT_METADATA_KEY) or "").strip()


def assemble_canva_v12_image_draft(
    assets: Iterable[Mapping[str, object]],
) -> dict[str, object]:
    """Assemble exact Canva image slots from explicitly assigned approved assets.

    Slot assignment is never inferred from filenames or generic role codes. If
    more than one approved asset targets a slot, the first input row wins; API
    callers order rows newest-first for deterministic replacement behavior.
    """
    fields = {name: "" for name in CANVA_V12_IMAGE_FIELDS}
    asset_uris = {name: "" for name in CANVA_V12_IMAGE_FIELDS}
    rejected: list[dict[str, str]] = []

    for asset in assets:
        slot = image_slot(asset)
        if not slot:
            continue
        asset_id = str(asset.get("id") or "").strip()
        if slot not in fields:
            rejected.append({"asset_id": asset_id, "reason": "unknown_slot", "slot": slot})
            continue
        if not is_approved_canva_image(asset):
            rejected.append({"asset_id": asset_id, "reason": "not_approved", "slot": slot})
            continue
        if fields[slot]:
            rejected.append({"asset_id": asset_id, "reason": "duplicate_slot", "slot": slot})
            continue
        fields[slot] = asset_id
        asset_uris[slot] = str(asset.get("asset_uri") or "").strip()

    completed_fields = tuple(name for name in CANVA_V12_IMAGE_FIELDS if fields[name])
    missing_fields = tuple(name for name in CANVA_V12_IMAGE_FIELDS if not fields[name])
    return {
        "field_count": len(CANVA_V12_IMAGE_FIELDS),
        "completed_count": len(completed_fields),
        "matched": f"{len(completed_fields)}/{len(CANVA_V12_IMAGE_FIELDS)}",
        "ready": not missing_fields,
        "completed_fields": completed_fields,
        "missing_fields": missing_fields,
        "image_fields": fields,
        "asset_uris": asset_uris,
        "rejected_assets": rejected,
    }
