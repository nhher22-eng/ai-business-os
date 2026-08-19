from __future__ import annotations

import json
import os
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


def _fallback_suggestions(product_name: str, facts: dict[str, Any]) -> dict[str, Any]:
    """Conservative fallback when a text model is not configured.

    It never creates physical specs. It only turns confirmed FACT into editable
    operating/marketing suggestions.
    """
    material = facts.get("primary_material")
    origin = facts.get("country_of_origin")
    dimensions = facts.get("dimensions") or {}
    packaging = facts.get("packaging") or {}

    features = []
    if material:
        features.append(f"주재질: {material}")
    if origin:
        features.append(f"원산지: {origin}")
    if any(dimensions.values()):
        features.append("등록된 실제 치수 정보를 상세 스펙에 활용")
    if packaging:
        features.append("등록된 포장 정보를 배송·B2B 포장 판단에 활용")

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
            "features": features,
            "selling_points": [],
            "target_customer": [],
            "content_direction": f"{product_name}의 확정 FACT를 우선 사용하고 미확정 사양은 표현하지 않음",
        },
        "warnings": [
            "텍스트 AI가 연결되지 않아 확정 FACT를 재정리한 안전 제안만 만들었습니다.",
            "카테고리·용도·가격·마케팅 해석은 사용자 확인 후 적용하세요.",
        ],
    }


def _extract_response_text(payload: dict[str, Any]) -> str:
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                return content["text"]
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    raise ProductSuggestionError("text model returned no readable output")


def build_ai_suggestions(product_name: str, facts: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build editable suggestions without allowing the model to alter FACT.

    Suggestions are blocked until source FACT has been explicitly confirmed by
    the user. If no OpenAI key is configured, the deterministic fallback remains
    usable after confirmation.
    """
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
- The CONFIRMED FACT below is canonical truth.
- Never modify, invent, infer, or fill missing physical/product FACT.
- You may only propose mutable operating information and subjective marketing interpretation.
- If evidence is insufficient, return null or an empty list.
- Do not make exaggerated, unverifiable, medical, safety, certification, performance, or superiority claims.
- Return JSON only.

Product name: {product_name}
CONFIRMED FACT:
{json.dumps(facts, ensure_ascii=False)}

Return exactly this shape:
{{
  "category": string|null,
  "usage": [string],
  "operating": {{
    "category": string|null,
    "usage": [string],
    "sale_price": null,
    "cost": null
  }},
  "marketing": {{
    "features": [string],
    "selling_points": [string],
    "target_customer": [string],
    "content_direction": string|null
  }},
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
                json={
                    "model": model,
                    "input": prompt,
                },
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
        return suggestions, {
            "provider": "openai",
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
