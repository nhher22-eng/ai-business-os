from __future__ import annotations

import app.api.product_registration as registration_api


FACT_FIELD_MAP = {
    "model_name": "model_name",
    "primary_material": "primary_material",
    "secondary_material": "secondary_material",
    "weight": "weight",
    "dimensions": "dimensions",
    "manufacturer": "manufacturer",
    "country_of_origin": "country_of_origin",
    "certifications": "certifications",
    "packaging": "packaging",
    "fact_notes": "fact_notes",
}

_INSTALLED = False


def apply_only_supplied_facts(row, body) -> None:
    """Update only fields explicitly supplied by the caller.

    A partial edit such as {"country_of_origin": "KR"} must never erase
    previously confirmed material, dimensions, packaging, or other FACT.
    """
    supplied = set(getattr(body, "model_fields_set", set()))
    for body_field, row_field in FACT_FIELD_MAP.items():
        if body_field in supplied:
            setattr(row, row_field, getattr(body, body_field))

    if body.confirm:
        row.facts_confirmed = True
        row.facts_confirmed_by = body.confirmed_by or "dashboard-user"
        row.facts_confirmed_at = registration_api.utcnow()


def install_product_registration_safety_patch() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    registration_api._apply_facts = apply_only_supplied_facts
    _INSTALLED = True
