from __future__ import annotations

import csv
import io
import json
from collections.abc import Mapping
from dataclasses import dataclass


SCHEMA_VERSION = "canva-detail-page-text.v1.2"
TEMPLATE_NAME = "AI Business OS 상세페이지 표준 v1.2_12P"
CANVA_SOURCE_DESIGN_ID = "DAHTw4sMcVM"
CANVA_BRAND_TEMPLATE_ID = "EAHTvwXU8Ig"
UNCONFIRMED_VALUE = "확정값 입력 필요"

CANVA_V12_TEXT_FIELDS = (
    "product_name",
    "hero_headline",
    "hero_subcopy",
    "problem_title",
    "problem_copy",
    "features_section_title",
    "features_section_subcopy",
    "feature_1_title",
    "feature_1_copy",
    "feature_2_title",
    "feature_2_copy",
    "feature_3_title",
    "feature_3_copy",
    "detail_section_title",
    "detail_section_subcopy",
    "detail_1_title",
    "detail_1_copy",
    "detail_2_title",
    "detail_2_copy",
    "usage_scene_section_title",
    "usage_scene_section_subcopy",
    "usage_scene_1_title",
    "usage_scene_1_copy",
    "usage_scene_2_title",
    "usage_scene_2_copy",
    "review_section_title",
    "review_section_subcopy",
    "review_1_author",
    "review_1_text",
    "review_2_author",
    "review_2_text",
    "review_3_author",
    "review_3_text",
    "spec_section_title",
    "spec_section_subcopy",
    "option_1_name",
    "option_1_copy",
    "option_2_name",
    "option_2_copy",
    "option_3_name",
    "option_3_copy",
    "usage_section_title",
    "usage_section_subcopy",
    "usage_step_1_title",
    "usage_step_1_copy",
    "usage_step_2_title",
    "usage_step_2_copy",
    "usage_step_3_title",
    "usage_step_3_copy",
    "components_section_title",
    "dimension_1_text",
    "dimension_2_text",
    "dimension_3_text",
    "spec_product_name",
    "spec_size",
    "spec_material",
    "spec_manufacturer",
    "spec_origin",
    "spec_product_code",
    "caution_section_title",
    "caution_section_subcopy",
    "caution_1_text",
    "caution_2_text",
    "caution_3_text",
    "caution_4_text",
    "policy_section_title",
    "shipping_title",
    "shipping_copy",
    "exchange_return_title",
    "exchange_return_copy",
    "return_restriction_title",
    "return_restriction_copy",
)

CANVA_V12_IMAGE_FIELDS_BY_PAGE = {
    1: ("hero_image",),
    2: ("problem_image",),
    3: ("feature_1_image", "feature_2_image", "feature_3_image"),
    4: ("detail_1_image", "detail_2_image"),
    5: ("usage_scene_main_image", "usage_scene_1_image", "usage_scene_2_image"),
    6: ("review_1_image", "review_2_image", "review_3_image"),
    7: ("option_main_image", "option_1_image", "option_2_image", "option_3_image"),
    8: ("usage_step_1_image", "usage_step_2_image", "usage_step_3_image"),
    9: ("components_image",),
    10: ("spec_line_drawing_image",),
    11: (),
    12: (),
}
CANVA_V12_IMAGE_FIELDS = tuple(
    name
    for page_number in range(1, 13)
    for name in CANVA_V12_IMAGE_FIELDS_BY_PAGE[page_number]
)
CANVA_V12_ALL_FIELDS = CANVA_V12_TEXT_FIELDS + CANVA_V12_IMAGE_FIELDS

FACT_BOUND_FIELDS = {
    "product_name",
    "spec_product_name",
    "spec_size",
    "spec_material",
    "spec_manufacturer",
    "spec_origin",
    "spec_product_code",
    "dimension_1_text",
    "dimension_2_text",
    "dimension_3_text",
}

SKU_BOUND_FIELDS = {"option_1_name", "option_2_name", "option_3_name"}
CANVA_V12_COPY_FIELDS = tuple(
    name
    for name in CANVA_V12_TEXT_FIELDS
    if name not in FACT_BOUND_FIELDS and name not in SKU_BOUND_FIELDS
)

LEGACY_APPROVED_COPY_ALIASES = {
    "headline": "hero_headline",
    "subheadline": "hero_subcopy",
    "feature_summary": "features_section_subcopy",
    "usage": "usage_scene_section_subcopy",
    "specification": "spec_section_subcopy",
    "caution": "caution_section_subcopy",
}


@dataclass(frozen=True)
class CanvaTextValidationError(ValueError):
    missing: tuple[str, ...] = ()
    unknown: tuple[str, ...] = ()
    blank: tuple[str, ...] = ()

    def __str__(self) -> str:
        parts = []
        if self.missing:
            parts.append(f"missing={','.join(self.missing)}")
        if self.unknown:
            parts.append(f"unknown={','.join(self.unknown)}")
        if self.blank:
            parts.append(f"blank={','.join(self.blank)}")
        return "invalid Canva v1.2 text payload: " + "; ".join(parts)


def _clean_text(value: object) -> str:
    return str(value if value is not None else "").strip()


def _fact_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " / ".join(
            f"{_clean_text(key)}: {_clean_text(item)}"
            for key, item in value.items()
            if _clean_text(item)
        )
    if isinstance(value, (list, tuple)):
        return " / ".join(_clean_text(item) for item in value if _clean_text(item))
    return _clean_text(value)


def assemble_canva_v12_text_draft(
    *,
    product: Mapping[str, object],
    profile: Mapping[str, object] | None,
    skus: list[Mapping[str, object]],
    approved_copy: Mapping[str, object],
) -> dict[str, object]:
    """Assemble only confirmed FACT and approved copy into the 72-field draft."""
    profile = profile or {}
    fields = {name: "" for name in CANVA_V12_TEXT_FIELDS}

    # Existing six-slot copy assets remain usable while exact v1.2 slot assets
    # are introduced. Exact Canva field names take precedence over aliases.
    for source, target in LEGACY_APPROVED_COPY_ALIASES.items():
        if source in approved_copy:
            fields[target] = _clean_text(approved_copy[source])
    for name in CANVA_V12_TEXT_FIELDS:
        if name in approved_copy:
            fields[name] = _clean_text(approved_copy[name])

    product_name = _clean_text(product.get("name"))
    fact_values = {
        "product_name": product_name,
        "spec_product_name": product_name,
        "spec_product_code": _clean_text(product.get("product_code")),
        "spec_size": _fact_text(profile.get("dimensions")),
        "spec_material": _clean_text(profile.get("primary_material")),
        "spec_manufacturer": _clean_text(
            product.get("manufacturer") or profile.get("manufacturer")
        ),
        "spec_origin": _clean_text(
            product.get("country_of_origin") or profile.get("country_of_origin")
        ),
    }
    for name, value in fact_values.items():
        if value:
            fields[name] = value

    active_skus = [row for row in skus if row.get("status", "active") == "active"]
    for index, sku in enumerate(active_skus[:3], start=1):
        fields[f"option_{index}_name"] = _clean_text(
            sku.get("option_value") or sku.get("name")
        )

    completed_fields = tuple(name for name in CANVA_V12_TEXT_FIELDS if fields[name])
    missing_fields = tuple(name for name in CANVA_V12_TEXT_FIELDS if not fields[name])
    return {
        "template_name": TEMPLATE_NAME,
        "field_count": len(CANVA_V12_TEXT_FIELDS),
        "completed_count": len(completed_fields),
        "matched": f"{len(completed_fields)}/{len(CANVA_V12_TEXT_FIELDS)}",
        "ready": not missing_fields,
        "completed_fields": completed_fields,
        "missing_fields": missing_fields,
        "text_fields": fields,
    }


def validate_canva_v12_text_payload(payload: Mapping[str, object]) -> dict[str, str]:
    """Validate and order the exact 72-field Canva v1.2 text payload."""
    expected = set(CANVA_V12_TEXT_FIELDS)
    received = set(payload)
    missing = tuple(name for name in CANVA_V12_TEXT_FIELDS if name not in received)
    unknown = tuple(sorted(received - expected))
    blank = tuple(
        name for name in CANVA_V12_TEXT_FIELDS
        if name in payload and not _clean_text(payload[name])
    )
    if missing or unknown or blank:
        raise CanvaTextValidationError(missing=missing, unknown=unknown, blank=blank)
    return {name: _clean_text(payload[name]) for name in CANVA_V12_TEXT_FIELDS}


def validate_canva_v12_image_payload(payload: Mapping[str, object]) -> dict[str, str]:
    """Validate Canva asset IDs for the exact 22 image Autofill fields."""
    expected = set(CANVA_V12_IMAGE_FIELDS)
    received = set(payload)
    missing = tuple(name for name in CANVA_V12_IMAGE_FIELDS if name not in received)
    unknown = tuple(sorted(received - expected))
    blank = tuple(
        name for name in CANVA_V12_IMAGE_FIELDS
        if name in payload and not _clean_text(payload[name])
    )
    if missing or unknown or blank:
        raise CanvaTextValidationError(missing=missing, unknown=unknown, blank=blank)
    return {name: _clean_text(payload[name]) for name in CANVA_V12_IMAGE_FIELDS}


def canva_v12_autofill_data(
    *,
    text_fields: Mapping[str, object],
    image_fields: Mapping[str, object],
) -> dict[str, dict[str, str]]:
    """Build Canva Autofill data for all 94 approved text and image fields."""
    text_payload = validate_canva_v12_text_payload(text_fields)
    image_payload = validate_canva_v12_image_payload(image_fields)
    return {
        **{name: {"type": "text", "text": value} for name, value in text_payload.items()},
        **{
            name: {"type": "image", "asset_id": asset_id}
            for name, asset_id in image_payload.items()
        },
    }


def build_canva_v12_text_payload(
    *,
    proposed_copy: Mapping[str, object],
    confirmed_facts: Mapping[str, object],
) -> dict[str, str]:
    """Combine proposed copy with confirmed facts, letting FACT values win.

    The caller must supply a complete proposed payload. Confirmed FACT fields
    overwrite the corresponding proposed values. Missing confirmed facts remain
    explicitly unconfirmed; they are never inferred from marketing copy.
    """
    merged = dict(proposed_copy)
    for name in FACT_BOUND_FIELDS:
        if name in confirmed_facts:
            merged[name] = _clean_text(confirmed_facts[name]) or UNCONFIRMED_VALUE
    return validate_canva_v12_text_payload(merged)


def canva_v12_text_json(payload: Mapping[str, object]) -> str:
    ordered = validate_canva_v12_text_payload(payload)
    document = {
        "schema_version": SCHEMA_VERSION,
        "template_name": TEMPLATE_NAME,
        "field_count": len(CANVA_V12_TEXT_FIELDS),
        "text_fields": ordered,
    }
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def canva_v12_bulk_csv(payloads: list[Mapping[str, object]]) -> str:
    """Render one Canva Bulk Create row per payload in canonical column order."""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(CANVA_V12_TEXT_FIELDS), lineterminator="\n")
    writer.writeheader()
    for payload in payloads:
        writer.writerow(validate_canva_v12_text_payload(payload))
    return "\ufeff" + output.getvalue()


def parse_canva_v12_bulk_csv(content: bytes) -> list[dict[str, str]]:
    """Decode and validate every row of an uploaded Canva Bulk Create CSV."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CanvaTextValidationError(unknown=("CSV 인코딩은 UTF-8이어야 합니다",)) from exc
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise CanvaTextValidationError(missing=CANVA_V12_TEXT_FIELDS)
    rows = [validate_canva_v12_text_payload(row) for row in reader]
    if not rows:
        raise CanvaTextValidationError(missing=("상품 데이터 행",))
    return rows
