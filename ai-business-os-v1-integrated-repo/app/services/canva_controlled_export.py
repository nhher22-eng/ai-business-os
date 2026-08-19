from __future__ import annotations

from copy import deepcopy


TEMPLATE_A_SECTION_PAGE_MAP = {
    "HERO": 1,
    "PROBLEM": 2,
    "LIFESTYLE": 3,
    "FEATURE": 4,
    "OPTION_COMPARE": 5,
    "COMPONENTS": 6,
    "INSTALLATION": 7,
    "SPEC": 8,
    "FAQ": 9,
}

# Conditional sections are intentionally excluded from the 9P sales RC. They are
# only eligible when the approved detail-page version has real source data.
TEMPLATE_A_OPTIONAL_13P_PAGE_MAP = {
    "REVIEW_SUMMARY": 2,
    "ADD_ON": 7,
    "REVIEW_DETAIL": 11,
    "RELATED_PRODUCTS": 12,
}


def _section_by_type(sections: list[dict]) -> dict[str, dict]:
    return {str(section.get("type")): section for section in sections if section.get("enabled", True)}


def _safe(value):
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return deepcopy(value)


def build_controlled_canva_contract(*, export_payload: dict) -> dict:
    """Build a deterministic Canva execution contract from the export payload only.

    The contract is deliberately conservative:
    - no model-memory or outside-data fallback is allowed;
    - only enabled sections and product_facts from this export may be used;
    - missing values stay null/empty and must not be invented;
    - images must come from approved image_asset_id values carried by sections.
    """
    sections = list(export_payload.get("sections") or [])
    by_type = _section_by_type(sections)
    facts = deepcopy(export_payload.get("product_facts") or {})
    product = deepcopy(facts.get("product") or {})
    detail = deepcopy(facts.get("detail") or {})
    skus = deepcopy(facts.get("skus") or [])

    active_9p_sections = [
        section_type
        for section_type in TEMPLATE_A_SECTION_PAGE_MAP
        if section_type in by_type
    ]
    selected_pages = [TEMPLATE_A_SECTION_PAGE_MAP[name] for name in active_9p_sections]

    field_sources: dict[str, dict] = {}
    for section_type in active_9p_sections:
        section = by_type[section_type]
        field_sources[section_type] = {
            "page": TEMPLATE_A_SECTION_PAGE_MAP[section_type],
            "source_type": section.get("source_type"),
            "content": deepcopy(section.get("content") or {}),
            "image_asset_id": section.get("image_asset_id"),
        }

    return {
        "schema_version": "canva-controlled-export.v1",
        "mode": "controlled_template",
        "template_code": (export_payload.get("template") or {}).get("code"),
        "canva_brand_template_id": (export_payload.get("template") or {}).get("canva_brand_template_id"),
        "target": {
            "template_family": "A_PRACTICAL_TRUST",
            "release_candidate_pages": selected_pages,
            "release_candidate_section_order": active_9p_sections,
        },
        "source_policy": {
            "allowed_sources": ["export.product_facts", "export.sections", "approved_section_images"],
            "external_memory_fallback": False,
            "invent_missing_fact": False,
            "invent_review": False,
            "invent_relation": False,
            "unapproved_image_fallback": False,
            "missing_value_action": "leave_empty_or_review",
        },
        "source_snapshot": {
            "product": {
                "id": _safe(product.get("id")),
                "product_code": _safe(product.get("product_code")),
                "name": _safe(product.get("name")),
                "description": _safe(product.get("description")),
                "sales_channel": _safe(product.get("sales_channel")),
            },
            "detail": {
                "specification": _safe(detail.get("specification")),
                "usage": _safe(detail.get("usage")),
                "installation_method": _safe(detail.get("installation_method")),
                "usage_conditions": _safe(detail.get("usage_conditions")),
                "cautions": _safe(detail.get("cautions")),
            },
            "skus": skus,
        },
        "section_payloads": field_sources,
        "conditional_sections": {
            "included": [
                name
                for name in TEMPLATE_A_OPTIONAL_13P_PAGE_MAP
                if name in by_type
            ],
            "excluded": [
                name
                for name in TEMPLATE_A_OPTIONAL_13P_PAGE_MAP
                if name not in by_type
            ],
        },
    }
