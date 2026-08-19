from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

from app.core.config import settings


class ProductSuggestionError(RuntimeError):
    pass


def _empty_suggestions(warning: str) -> dict[str, Any]:
    return {
        "category": None,
        "usage": [],
        "operating": {
            "category": None,
            "usage": [],
            "sale_price": None,
            "cost": None,
        },
        "marketing": {
            "features": [],
            "selling_points": [],
            "target_customer": [],
            "content_direction": None,
        },
        "warnings": [warning],
    }


def _fact_note_items(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    return [item.strip() for item in re.split(r"[,/\n]", text) if item.strip()]


def _literal_fact_features(facts: dict[str, Any]) -> list[str]:
    """Create feature labels only from literal confirmed FACT values.

    No benefit, performance, convenience, target, or usage language is inferred.
    """
    result: list[str] = []
    mapping = (
        ("model_name", "모델명"),
        ("primary_material", "주재질"),
        ("secondary_material", "보조재질"),
        ("weight", "중량"),
        ("manufacturer", "제조사"),
        ("country_of_origin", "원산지"),
    )
    for key, label in mapping:
        value = facts.get(key)
        if value is not None and str(value).strip():
            result.append(f"{label}: {str(value).strip()}")

    dimensions = facts.get("dimensions") or {}
    if isinstance(dimensions, dict):
        for key, label in (("length", "길이"), ("width", "폭"), ("height", "높이")):
            value = dimensions.get(key)
            if value is not None and str(value).strip():
                result.append(f"{label}: {str(value).strip()}")

    certifications = facts.get("certifications") or []
    if isinstance(certifications, list):
        result.extend(f"인증: {str(item).strip()}" for item in certifications if str(item).strip())

    result.extend(_fact_note_items(facts.get("fact_notes")))

    deduped: list[str] = []
    for item in result:
        if item not in deduped:
            deduped.append(item)
    return deduped


def _ground_model_suggestions(
    suggestions: dict[str, Any],
    *,
    product_name: str,
    facts: dict[str, Any],
) -> dict[str, Any]:
    """Server-side grounding boundary for model output.

    Category may be suggested from the product name as mutable operating metadata.
    Usage, benefits, target customers, convenience claims and selling points are
    suppressed until an explicit evidence field for them exists. Marketing
    features are rebuilt from literal confirmed FACT instead of trusting model copy.
    """
    category = suggestions.get("category")
    operating = suggestions.get("operating") if isinstance(suggestions.get("operating"), dict) else {}
    if not isinstance(category, str) or not category.strip():
        category = operating.get("category")
    if not isinstance(category, str) or not category.strip():
        category = None
    else:
        category = category.strip()

    warnings = suggestions.get("warnings") if isinstance(suggestions.get("warnings"), list) else []
    warnings = [str(item) for item in warnings if str(item).strip()]
    warnings.append(
        "FACT 근거가 없는 용도·효과·편의성·타깃·판매포인트 제안은 자동 제외했습니다."
    )

    return {
        "category": category,
        "usage": [],
        "operating": {
            "category": category,
            "usage": [],
            "sale_price": None,
            "cost": None,
        },
        "marketing": {
            "features": _literal_fact_features(facts),
            "selling_points": [],
            "target_customer": [],
            "content_direction": f"{product_name}의 확정 FACT만 사용해 사실 중심으로 안내",
        },
        "warnings": warnings,
    }


def _fallback_suggestions(product_name: str, facts: dict[str, Any]) -> dict[str, Any]:
    return _ground_model_suggestions(
        {"category": None, "warnings": ["텍스트 AI가 연결되지 않아 안전 제안으로 전환했습니다."]},
        product_name=product_name,
        facts=facts,
    )


def _extract_response_text(payload: dict[str, Any]) -> str:
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                return content["text"]
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    raise ProductSuggestionError("text model returned no readable output")


def build_ai_suggestions(product_name: str, facts: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build editable suggestions without allowing the model to alter FACT."""
    if not facts.get("facts_confirmed"):
        return _empty_suggestions(
            "상품 FACT를 먼저 사용자 확정해 주세요. 미확정 값으로 AI 제안을 만들지 않습니다."
        ), {
            "provider": "blocked-unconfirmed",
            "model": None,
            "fact_mutation_allowed": False,
        }

    if not settings.openai_api_key:
        return _fallback_suggestions(product_name, facts), {
            "provider": "safe-fallback",
            "model": None,
            "fact_mutation_allowed": False,
        }

    model = os.getenv("OPENAI_TEXT_MODEL", "gpt-4.1-mini")
    prompt = f"""
You assist with commerce product registration.

CRITICAL RULES:
- CONFIRMED FACT is canonical truth.
- Never invent or infer physical facts, use cases, performance, benefits, ease-of-use, assembly requirements, target customers, or effectiveness.
- A product name may support a conservative CATEGORY suggestion only.
- Do not infer "window", "garden", "easy installation", "no assembly", "effective blocking", or similar claims unless explicitly present in CONFIRMED FACT.
- If evidence is insufficient, return null or an empty list.
- Return JSON only.

Product name: {product_name}
CONFIRMED FACT:
{json.dumps(facts, ensure_ascii=False)}

Return exactly this shape:
{{
  "category": string|null,
  "usage": [],
  "operating": {{"category": string|null, "usage": [], "sale_price": null, "cost": null}},
  "marketing": {{"features": [], "selling_points": [], "target_customer": [], "content_direction": string|null}},
  "warnings": [string]
}}
""".strip()

    try:
        with httpx.Client(timeout=45.0) as client:
            response = client.post(
                f"{settings.openai_api_base.rstrip('/')}/responses",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": model, "input": prompt},
            )
        response.raise_for_status()
        text = _extract_response_text(response.json()).strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].lstrip()
        suggestions = json.loads(text)
        if not isinstance(suggestions, dict):
            raise ProductSuggestionError("suggestion output must be a JSON object")
        grounded = _ground_model_suggestions(
            suggestions,
            product_name=product_name,
            facts=facts,
        )
        return grounded, {
            "provider": "openai-grounded",
            "model": model,
            "fact_mutation_allowed": False,
        }
    except Exception as exc:
        suggestions = _fallback_suggestions(product_name, facts)
        suggestions.setdefault("warnings", []).append(
            f"AI 제안 호출 실패로 안전 제안으로 전환: {type(exc).__name__}"
        )
        return suggestions, {
            "provider": "safe-fallback",
            "model": model,
            "fact_mutation_allowed": False,
            "fallback_reason": type(exc).__name__,
        }
