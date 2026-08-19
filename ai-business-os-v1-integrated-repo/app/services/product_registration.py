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
    editor = {
        "category": None,
        "usage": [],
        "features": [],
        "selling_points": [],
        "target_customer": [],
        "content_direction": None,
    }
    return {
        "category": None,
        "usage": [],
        "operating": {"category": None, "usage": [], "sale_price": None, "cost": None},
        "marketing": {
            "features": [],
            "selling_points": [],
            "target_customer": [],
            "content_direction": None,
        },
        "editor": editor,
        "warnings": [warning],
    }


def _fact_note_items(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    return [item.strip() for item in re.split(r"[,/\n]", text) if item.strip()]


def _literal_fact_features(facts: dict[str, Any]) -> list[str]:
    """Create literal labels from user-confirmed FACT without adding benefits."""
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


def _clean_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def _candidate(value: str, *, source: str, status: str, reason: str) -> dict[str, str]:
    return {
        "value": value,
        "source": source,
        "status": status,
        "reason": reason,
    }


def _review_reason(value: str) -> str:
    text = value.lower()
    sensitive = (
        "효과",
        "차단",
        "방지",
        "예방",
        "안전",
        "간편",
        "쉬운",
        "불필요",
        "최고",
        "완벽",
        "보장",
        "효율",
        "성능",
    )
    if any(word in text for word in sensitive):
        return "효과·성능·편의성 표현일 수 있어 실제 상품 근거 확인이 필요합니다."
    return "AI가 제안한 아이디어입니다. 실제 상품에 맞는지 확인 후 수정·채택하세요."


def _editor_suggestions(
    suggestions: dict[str, Any],
    *,
    product_name: str,
    facts: dict[str, Any],
) -> dict[str, Any]:
    """Preserve AI ideas while clearly separating confirmed FACT from hypotheses.

    Nothing in the editor payload mutates FACT. FACT-derived rows are marked
    confirmed; model-derived rows stay visible as review candidates so the user
    can edit, delete, or explicitly adopt them.
    """
    operating = suggestions.get("operating") if isinstance(suggestions.get("operating"), dict) else {}
    marketing = suggestions.get("marketing") if isinstance(suggestions.get("marketing"), dict) else {}

    category = suggestions.get("category") or operating.get("category")
    category = str(category).strip() if category is not None else ""
    category_row = (
        _candidate(
            category,
            source="ai",
            status="suggested",
            reason="상품명과 입력정보를 바탕으로 한 운영 카테고리 제안입니다. 필요하면 수정하거나 비워둘 수 있습니다.",
        )
        if category
        else None
    )

    fact_features = [
        _candidate(
            item,
            source="fact",
            status="confirmed",
            reason="사용자가 확정한 상품 FACT에서 가져왔습니다.",
        )
        for item in _literal_fact_features(facts)
    ]
    fact_values = {row["value"] for row in fact_features}

    raw_features = _clean_list(marketing.get("features"))
    ai_features = [
        _candidate(item, source="ai", status="review", reason=_review_reason(item))
        for item in raw_features
        if item not in fact_values
    ]

    usage = _clean_list(suggestions.get("usage")) or _clean_list(operating.get("usage"))
    selling_points = _clean_list(marketing.get("selling_points"))
    targets = _clean_list(marketing.get("target_customer"))
    direction = str(marketing.get("content_direction") or "").strip()

    editor = {
        "category": category_row,
        "usage": [
            _candidate(item, source="ai", status="review", reason=_review_reason(item))
            for item in usage
        ],
        "features": fact_features + ai_features,
        "selling_points": [
            _candidate(item, source="ai", status="review", reason=_review_reason(item))
            for item in selling_points
        ],
        "target_customer": [
            _candidate(item, source="ai", status="review", reason=_review_reason(item))
            for item in targets
        ],
        "content_direction": (
            _candidate(
                direction,
                source="ai",
                status="review",
                reason="상세페이지·이미지·광고에 재사용할 수 있는 콘텐츠 방향 아이디어입니다.",
            )
            if direction
            else None
        ),
    }

    # Legacy fields remain for API compatibility. Only explicitly applied editor
    # values are persisted by the UI; these fields are not auto-applied.
    return {
        "category": category or None,
        "usage": usage,
        "operating": {
            "category": category or None,
            "usage": usage,
            "sale_price": None,
            "cost": None,
        },
        "marketing": {
            "features": [row["value"] for row in fact_features] + raw_features,
            "selling_points": selling_points,
            "target_customer": targets,
            "content_direction": direction or None,
        },
        "editor": editor,
        "warnings": [
            "노란색 AI 제안은 아이디어입니다. 실제 상품에 맞게 수정·삭제·채택한 뒤 적용하세요.",
            "초록색 FACT 항목도 콘텐츠에서 사용하지 않을 경우 선택 해제할 수 있지만 원천 FACT 자체는 변경되지 않습니다.",
        ],
    }


# Compatibility alias used by earlier tests/imports.
def _ground_model_suggestions(
    suggestions: dict[str, Any], *, product_name: str, facts: dict[str, Any]
) -> dict[str, Any]:
    return _editor_suggestions(suggestions, product_name=product_name, facts=facts)


def _fallback_suggestions(product_name: str, facts: dict[str, Any]) -> dict[str, Any]:
    return _editor_suggestions(
        {
            "category": None,
            "usage": [],
            "marketing": {
                "features": [],
                "selling_points": [],
                "target_customer": [],
                "content_direction": None,
            },
        },
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
    """Generate a broad idea set, then label rather than hide uncertain ideas."""
    if not facts.get("facts_confirmed"):
        return _empty_suggestions(
            "상품 FACT를 먼저 사용자 확정해 주세요. 미확정 값으로 AI 제안을 만들지 않습니다."
        ), {
            "provider": "blocked-unconfirmed",
            "model": None,
            "fact_mutation_allowed": False,
        }

    if not settings.openai_api_key:
        result = _fallback_suggestions(product_name, facts)
        result["warnings"].append("텍스트 AI가 연결되지 않아 확정 FACT만 편집 후보로 표시했습니다.")
        return result, {
            "provider": "safe-fallback",
            "model": None,
            "fact_mutation_allowed": False,
        }

    model = os.getenv("OPENAI_TEXT_MODEL", "gpt-4.1-mini")
    prompt = f"""
You are brainstorming editable commerce content ideas for product registration.

IMPORTANT:
- CONFIRMED FACT is canonical truth and must never be changed or contradicted.
- Generate useful ideas for category, possible usage, features, selling points,
  target customers, and content direction.
- Ideas that go beyond CONFIRMED FACT are allowed as hypotheses because the UI
  will flag them for human review. Do not present them as verified facts.
- Avoid medical, legal, certification, safety guarantees, fabricated numeric
  performance claims, fake reviews, or superiority claims.
- Return JSON only.

Product name: {product_name}
CONFIRMED FACT:
{json.dumps(facts, ensure_ascii=False)}

Return exactly this shape:
{{
  "category": string|null,
  "usage": [string],
  "operating": {{"category": string|null, "usage": [string], "sale_price": null, "cost": null}},
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
        result = _editor_suggestions(
            suggestions,
            product_name=product_name,
            facts=facts,
        )
        model_warnings = suggestions.get("warnings") if isinstance(suggestions.get("warnings"), list) else []
        result["warnings"].extend(str(x) for x in model_warnings if str(x).strip())
        return result, {
            "provider": "openai-editable",
            "model": model,
            "fact_mutation_allowed": False,
        }
    except Exception as exc:
        suggestions = _fallback_suggestions(product_name, facts)
        suggestions.setdefault("warnings", []).append(
            f"AI 제안 호출 실패로 FACT 편집 후보만 표시: {type(exc).__name__}"
        )
        return suggestions, {
            "provider": "safe-fallback",
            "model": model,
            "fact_mutation_allowed": False,
            "fallback_reason": type(exc).__name__,
        }
