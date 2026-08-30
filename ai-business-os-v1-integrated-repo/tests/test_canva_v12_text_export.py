import csv
import io
import json

import pytest
from fastapi import HTTPException

from app.api.canva_controlled_export import (
    CanvaV12BulkRequest,
    CanvaV12TextRow,
    export_v12_bulk_csv,
    validate_v12_text,
)
from app.services.canva_v12_text_export import (
    CANVA_BRAND_TEMPLATE_ID,
    CANVA_SOURCE_DESIGN_ID,
    CANVA_V12_ALL_FIELDS,
    CANVA_V12_IMAGE_FIELDS,
    CANVA_V12_IMAGE_FIELDS_BY_PAGE,
    CANVA_V12_TEXT_FIELDS,
    CanvaTextValidationError,
    assemble_canva_v12_text_draft,
    build_canva_v12_text_payload,
    canva_v12_autofill_data,
    canva_v12_bulk_csv,
    canva_v12_text_json,
    parse_canva_v12_bulk_csv,
    validate_canva_v12_text_payload,
    validate_canva_v12_image_payload,
)


def _complete_payload():
    return {name: f"value:{name}" for name in CANVA_V12_TEXT_FIELDS}


def test_contract_has_exactly_72_unique_fields():
    assert len(CANVA_V12_TEXT_FIELDS) == 72
    assert len(set(CANVA_V12_TEXT_FIELDS)) == 72


def test_image_contract_matches_the_22_fields_connected_in_canva():
    assert CANVA_SOURCE_DESIGN_ID == "DAHTw4sMcVM"
    assert CANVA_BRAND_TEMPLATE_ID == "EAHTvwXU8Ig"
    assert len(CANVA_V12_IMAGE_FIELDS) == 22
    assert len(set(CANVA_V12_IMAGE_FIELDS)) == 22
    assert CANVA_V12_IMAGE_FIELDS_BY_PAGE[11] == ()
    assert CANVA_V12_IMAGE_FIELDS_BY_PAGE[12] == ()
    assert len(CANVA_V12_ALL_FIELDS) == 94
    assert len(set(CANVA_V12_ALL_FIELDS)) == 94


def test_combined_autofill_data_preserves_text_and_image_types():
    text_fields = _complete_payload()
    image_fields = {name: f"asset:{name}" for name in CANVA_V12_IMAGE_FIELDS}
    data = canva_v12_autofill_data(
        text_fields=text_fields,
        image_fields=image_fields,
    )
    assert len(data) == 94
    assert data["hero_headline"] == {
        "type": "text",
        "text": "value:hero_headline",
    }
    assert data["hero_image"] == {
        "type": "image",
        "asset_id": "asset:hero_image",
    }


def test_image_payload_rejects_missing_or_unknown_fields():
    fields = {name: f"asset:{name}" for name in CANVA_V12_IMAGE_FIELDS}
    fields.pop("components_image")
    fields["unknown_image"] = "asset:unknown"
    with pytest.raises(CanvaTextValidationError) as exc:
        validate_canva_v12_image_payload(fields)
    assert "components_image" in exc.value.missing
    assert "unknown_image" in exc.value.unknown


def test_validation_returns_canonical_field_order():
    source = dict(reversed(list(_complete_payload().items())))
    result = validate_canva_v12_text_payload(source)
    assert tuple(result) == CANVA_V12_TEXT_FIELDS


@pytest.mark.parametrize("mode", ["missing", "unknown", "blank"])
def test_validation_rejects_invalid_payload(mode):
    source = _complete_payload()
    if mode == "missing":
        source.pop("hero_headline")
    elif mode == "unknown":
        source["unexpected"] = "value"
    else:
        source["hero_headline"] = "   "

    with pytest.raises(CanvaTextValidationError) as exc:
        validate_canva_v12_text_payload(source)
    assert getattr(exc.value, mode)


def test_confirmed_facts_override_proposed_copy_without_invention():
    source = _complete_payload()
    result = build_canva_v12_text_payload(
        proposed_copy=source,
        confirmed_facts={
            "product_name": "8mm 자동 관수키트",
            "spec_product_name": "8mm 자동 관수키트",
            "spec_product_code": "IRRIGATION-8MM-KIT",
            "spec_manufacturer": None,
        },
    )
    assert result["product_name"] == "8mm 자동 관수키트"
    assert result["spec_product_code"] == "IRRIGATION-8MM-KIT"
    assert result["spec_manufacturer"] == "확정값 입력 필요"


def test_json_envelope_and_bulk_csv_are_deterministic():
    source = _complete_payload()
    document = json.loads(canva_v12_text_json(source))
    assert document["field_count"] == 72
    assert tuple(document["text_fields"]) == CANVA_V12_TEXT_FIELDS

    csv_text = canva_v12_bulk_csv([source])
    rows = list(csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff"))))
    assert tuple(rows[0]) == CANVA_V12_TEXT_FIELDS
    assert rows[0]["product_name"] == "value:product_name"


def test_api_validates_json_and_downloads_bulk_csv():
    row = CanvaV12TextRow(text_fields=_complete_payload())
    document = validate_v12_text(row)
    assert document["field_count"] == 72

    response = export_v12_bulk_csv(CanvaV12BulkRequest(rows=[row]))
    assert response.media_type == "text/csv; charset=utf-8"
    assert response.headers["content-disposition"].endswith(
        'filename="canva_v1.2_bulk_create.csv"'
    )
    parsed = list(
        csv.DictReader(io.StringIO(response.body.decode("utf-8-sig")))
    )
    assert len(parsed) == 1
    assert tuple(parsed[0]) == CANVA_V12_TEXT_FIELDS


def test_api_returns_422_for_incomplete_row():
    source = _complete_payload()
    source.pop("dimension_1_text")
    with pytest.raises(HTTPException) as exc:
        validate_v12_text(CanvaV12TextRow(text_fields=source))
    assert exc.value.status_code == 422
    assert "dimension_1_text" in exc.value.detail


def test_uploaded_csv_round_trip_requires_all_72_fields():
    source = _complete_payload()
    encoded = canva_v12_bulk_csv([source]).encode("utf-8")
    assert parse_canva_v12_bulk_csv(encoded) == [source]

    incomplete = encoded.decode("utf-8-sig").replace("dimension_1_text,", "", 1)
    with pytest.raises(CanvaTextValidationError):
        parse_canva_v12_bulk_csv(incomplete.encode("utf-8"))


def test_draft_uses_confirmed_facts_approved_copy_and_reports_missing_fields():
    draft = assemble_canva_v12_text_draft(
        product={
            "name": "8mm 자동 관수키트",
            "product_code": "IRRIGATION-8MM-KIT",
            "manufacturer": "확정 제조사",
            "country_of_origin": "대한민국",
        },
        profile={
            "dimensions": {"호스 외경": "8mm"},
            "primary_material": "확정 재질",
        },
        skus=[
            {"name": "10m", "option_value": "10m", "status": "active"},
            {"name": "20m", "option_value": "20m", "status": "active"},
            {"name": "30m", "option_value": "30m", "status": "active"},
        ],
        approved_copy={
            "headline": "필요한 곳에 정확하게 전달하는 물 관리",
            "hero_headline": "승인된 v1.2 메인 문안",
            "caution_1_text": "확정된 주의사항",
        },
    )
    fields = draft["text_fields"]
    assert fields["product_name"] == "8mm 자동 관수키트"
    assert fields["spec_product_code"] == "IRRIGATION-8MM-KIT"
    assert fields["spec_size"] == "호스 외경: 8mm"
    assert fields["hero_headline"] == "승인된 v1.2 메인 문안"
    assert [fields[f"option_{index}_name"] for index in range(1, 4)] == [
        "10m", "20m", "30m"
    ]
    assert draft["ready"] is False
    assert "hero_subcopy" in draft["missing_fields"]


def test_draft_is_ready_only_when_every_field_is_approved_or_fact_bound():
    approved = _complete_payload()
    draft = assemble_canva_v12_text_draft(
        product={"name": "상품", "product_code": "P-1"},
        profile={},
        skus=[],
        approved_copy=approved,
    )
    assert draft["ready"] is True
    assert draft["matched"] == "72/72"
    assert draft["missing_fields"] == ()
