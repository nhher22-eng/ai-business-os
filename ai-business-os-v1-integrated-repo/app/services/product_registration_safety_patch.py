from __future__ import annotations

import re
from typing import Any

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

_PHYSICAL_TERM_GROUPS = (
    ("우드", "원목", "목재", "나무", "wood", "timber", "lumber"),
    ("스틸", "철제", "철", "강철", "steel"),
    ("알루미늄", "aluminum", "aluminium"),
    ("플라스틱", "plastic"),
    ("스테인리스", "스텐", "stainless"),
    ("실내외", "실외", "야외", "옥외", "outdoor"),
    ("실내", "indoor"),
    ("방수", "방습", "내수"),
    ("내구", "튼튼", "견고", "강한 구조"),
    ("친환경", "eco-friendly", "천연 소재", "자연 소재"),
    ("안전", "무독성", "food safe"),
    ("구성품", "세트 구성", "포함", "동봉"),
)

_ORIGINAL_BUILD_AI_SUGGESTIONS = registration_api.build_ai_suggestions
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


def _fact_corpus(facts: dict[str, Any]) -> str:
    values: list[str] = []
    for key in FACT_FIELD_MAP:
        value = facts.get(key)
        if isinstance(value, dict):
            values.extend(str(v) for v in value.values() if v is not None)
        elif isinstance(value, list):
            values.extend(str(v) for v in value if v is not None)
        elif value is not None:
            values.append(str(value))
    return " ".join(values).lower()


def contains_unconfirmed_physical_claim(text: str, facts: dict[str, Any]) -> bool:
    """Return True when model copy promotes context into an unconfirmed FACT.

    Product name is intentionally not part of the FACT corpus. A material,
    environment, durability, safety, composition or numeric spec may appear in
    a suggestion only when the corresponding term already exists in confirmed
    FACT supplied to the model.
    """
    lowered = str(text or "").lower()
    corpus = _fact_corpus(facts)
    for group in _PHYSICAL_TERM_GROUPS:
        if any(term.lower() in lowered for term in group):
            if not any(term.lower() in corpus for term in group):
                return True
    compact_corpus = corpus.replace(" ", "")
    for number in re.findall(r"\d+(?:\.\d+)?\s*(?:mm|cm|m|kg|g|개|pcs?)", lowered):
        if number.replace(" ", "") not in compact_corpus:
            return True
    return False


def _safe_text_list(values: Any, facts: dict[str, Any]) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and not contains_unconfirmed_physical_claim(text, facts) and text not in result:
            result.append(text)
    return result


def sanitize_ai_suggestions(suggestions: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    """Post-filter AI text so physical FACT cannot be inferred from product name."""
    result = dict(suggestions or {})
    editor = dict(result.get("editor") or {})
    marketing = dict(result.get("marketing") or {})
    operating = dict(result.get("operating") or {})

    # Physical feature rows are allowed only when explicitly sourced from FACT.
    editor["features"] = [
        row for row in (editor.get("features") or [])
        if isinstance(row, dict) and row.get("source") == "fact"
    ]

    for key in ("usage", "selling_points", "target_customer"):
        rows = []
        for row in editor.get(key) or []:
            if not isinstance(row, dict):
                continue
            value = str(row.get("value") or "").strip()
            if value and not contains_unconfirmed_physical_claim(value, facts):
                rows.append(row)
        editor[key] = rows

    direction = editor.get("content_direction")
    if isinstance(direction, dict):
        value = str(direction.get("value") or "").strip()
        if not value or contains_unconfirmed_physical_claim(value, facts):
            editor["content_direction"] = None

    # Notes may mention missing evidence only as an explicit additional-check task.
    editor["product_notes"] = [
        row for row in (editor.get("product_notes") or [])
        if isinstance(row, dict) and str(row.get("value") or "").startswith("추가 확인 필요:")
    ]

    operating["category"] = None
    operating["usage"] = _safe_text_list(operating.get("usage"), facts)
    marketing["features"] = [row.get("value") for row in editor["features"] if row.get("value")]
    marketing["selling_points"] = _safe_text_list(marketing.get("selling_points"), facts)
    marketing["target_customer"] = _safe_text_list(marketing.get("target_customer"), facts)
    direction_text = str(marketing.get("content_direction") or "").strip()
    marketing["content_direction"] = (
        direction_text if direction_text and not contains_unconfirmed_physical_claim(direction_text, facts) else None
    )
    marketing["product_notes"] = [
        text for text in (str(x or "").strip() for x in marketing.get("product_notes") or [])
        if text.startswith("추가 확인 필요:")
    ]

    result["category"] = None
    result["usage"] = _safe_text_list(result.get("usage"), facts)
    result["operating"] = operating
    result["marketing"] = marketing
    result["editor"] = editor
    warnings = list(result.get("warnings") or [])
    guard = "상품명은 참고 문맥일 뿐 물리적 FACT가 아닙니다. 확정 FACT에 없는 재질·내구성·사용환경·성능·치수·구성품 표현은 자동 제외됩니다."
    if guard not in warnings:
        warnings.append(guard)
    result["warnings"] = warnings
    return result


def guarded_build_ai_suggestions(product_name: str, facts: dict[str, Any]):
    suggestions, metadata = _ORIGINAL_BUILD_AI_SUGGESTIONS(product_name, facts)
    return sanitize_ai_suggestions(suggestions, facts), metadata


def install_product_registration_safety_patch() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    registration_api._apply_facts = apply_only_supplied_facts
    registration_api.build_ai_suggestions = guarded_build_ai_suggestions
    _INSTALLED = True
