from datetime import datetime, timezone

from app.services.canva_v12_image_export import assemble_canva_v12_image_draft
from app.services.canva_v12_text_export import CANVA_V12_IMAGE_FIELDS
from app.api.canva_controlled_export import CanvaV12ImageAssignments


def _asset(asset_id="a1", slot="hero_image", **overrides):
    row = {
        "id": asset_id,
        "asset_stage": "final",
        "status": "approved",
        "qa_status": "pass",
        "approved_at": datetime.now(timezone.utc),
        "asset_uri": f"drive://{asset_id}",
        "asset_metadata": {"canva_v12_field": slot},
    }
    row.update(overrides)
    return row


def test_image_draft_requires_all_22_explicit_approved_assignments():
    assets = [_asset(asset_id=f"a{i}", slot=slot) for i, slot in enumerate(CANVA_V12_IMAGE_FIELDS)]
    draft = assemble_canva_v12_image_draft(assets)
    assert draft["ready"] is True
    assert draft["matched"] == "22/22"
    assert tuple(draft["image_fields"]) == CANVA_V12_IMAGE_FIELDS


def test_unapproved_or_qa_review_image_never_fills_a_slot():
    draft = assemble_canva_v12_image_draft([_asset(status="review", qa_status="review")])
    assert draft["ready"] is False
    assert draft["image_fields"]["hero_image"] == ""
    assert draft["rejected_assets"][0]["reason"] == "not_approved"


def test_unknown_and_duplicate_slots_are_reported_deterministically():
    draft = assemble_canva_v12_image_draft([
        _asset("new", "hero_image"),
        _asset("old", "hero_image"),
        _asset("bad", "not_a_canva_slot"),
    ])
    assert draft["image_fields"]["hero_image"] == "new"
    assert {row["reason"] for row in draft["rejected_assets"]} == {
        "duplicate_slot",
        "unknown_slot",
    }


def test_assignment_request_supports_explicit_slot_clearing():
    request = CanvaV12ImageAssignments(
        assignments={"hero_image": "approved-asset-1"},
        clear_slots=["problem_image"],
    )
    assert request.assignments == {"hero_image": "approved-asset-1"}
    assert request.clear_slots == ["problem_image"]
