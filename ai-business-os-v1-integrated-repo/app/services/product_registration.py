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
        "category": None,  # legacy compatibility only; final UI does not expose it
        "usage": [],
        "features": [],
        "selling_points": [],
        "target_customer": [],
        "content_direction": None,
        "product_notes": [],
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
            "product_notes": [],
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
    """Create literal Korean labels from user-confirmed FACT without adding benefits."""
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
    return "확정 FACT를 바탕으로 한 마케팅 해석 제안입니다. 실제 판매 방향에 맞는지 확인 후 수정·채택하세요."


def _editor_suggestions(
    suggestions: dict[str, Any],
    *,
    product_name: str,
    facts: dict[str, Any],
) -> dict[str, Any]:
    """Build the final text-extension editor without inventing product FACT.

    Physical/product-feature rows come only from confirmed FACT. The model may
    propose marketing interpretation (selling points, target customers, content
    direction) and explicitly grounded usage restatements, but those remain
    review candidates until the user confirms them.
    """
    operating = suggestions.get("operating") if isinstance(suggestions.get("operating"), dict) else {}
    marketing = suggestions.get("marketing") if isinstance(suggestions.get("marketing"), dict) else {}

    fact_features = [
        _candidate(
            item,
            source="fact",
            status="confirmed",
            reason="사용자가 확정한 상품 FACT에서 직접 가져왔습니다.",
        )
        for item in _literal_fact_features(facts)
    ]

    # Product physical features must never be generated from hypotheses.
    # Ignore model-generated feature claims entirely; only literal confirmed FACT is shown here.
    usage = _clean_list(suggestions.get("usage")) or _clean_list(operating.get("usage"))
    selling_points = _clean_list(marketing.get("selling_points"))
    targets = _clean_list(marketing.get("target_customer"))
    direction = str(marketing.get("content_direction") or "").strip()
    product_notes = _clean_list(marketing.get("product_notes"))

    editor = {
        "category": None,
        "usage": [
            _candidate(
                item,
                source="ai",
                status="review",
                reason="확정 FACT/상품명에 근거해 다시 표현한 용도 후보입니다. 실제 용도와 일치하는지 확인하세요.",
            )
            for item in usage
        ],
        "features": fact_features,
        "selling_points": [
            _candidate(item, source="ai", status="review", reason=_review_reason(item))
            for item in selling_points
        ],
        "target_customer": [
            _candidate(
                item,
                source="ai",
                status="review",
                reason="상품 FACT를 바꾸지 않는 고객군/판매 방향 제안입니다. 실제 타깃에 맞게 수정·채택하세요.",
            )
            for item in targets
        ],
        "content_direction": (
            _candidate(
                direction,
                source="ai",
                status="review",
                reason="확정 FACT를 어떻게 설명할지에 대한 콘텐츠 방향 제안입니다.",
            )
            if direction
            else None
        ),
        "product_notes": [
            _candidate(
                item,
                source="ai",
                status="review",
                reason="새 사실을 단정하는 항목이 아니라, 판매 전 추가 확인이 필요한 정보 제안입니다.",
            )
            for item in product_notes
        ],
    }

    return {
        "category": None,
        "usage": usage,
        "operating": {
            "category": None,
            "usage": usage,
            "sale_price": None,
            "cost": None,
        },
        "marketing": {
            "features": [row["value"] for row in fact_features],
            "selling_points": selling_points,
            "target_customer": targets,
            "content_direction": direction or None,
            "product_notes": product_notes,
        },
        "editor": editor,
        "warnings": [
            "AI 제안은 확정 FACT를 바꾸지 않는 설명·마케팅 해석입니다. 실제 상품에 맞는 내용만 사용자가 수정·삭제·채택합니다.",
            "상품의 재질·구조·성능·내구성·효과·치수·구성품 등 물리적 사실은 AI가 새로 만들지 않습니다.",
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
            "usage": [],
            "marketing": {
                "selling_points": [],
                "target_customer": [],
                "content_direction": None,
                "product_notes": [],
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
    """Generate Korean, FACT-first text-extension suggestions for human confirmation."""
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
당신은 상품등록용 텍스트 확장정보 제안 도우미입니다.
반드시 한국어로만 답하고 JSON만 반환하세요.

핵심 원칙:
- CONFIRMED FACT는 유일한 상품 사실입니다. 절대 변경·추가·추측하지 마세요.
- 재질, 구조, 내구성, 성능, 효과, 치수, 구성품, 안전성, 인증, 사용 제한 같은 물리적 사실을 새로 만들지 마세요.
- features(특징)는 생성하지 마세요. 특징은 시스템이 CONFIRMED FACT에서 직접 구성합니다.
- usage(용도)는 상품명 또는 CONFIRMED FACT에 용도가 명시적으로 드러나는 경우에만 짧게 다시 표현하세요. 근거가 없으면 빈 배열로 두세요.
- selling_points(판매 포인트)는 CONFIRMED FACT를 과장하지 않고 설명하는 마케팅 해석만 제안하세요.
- target_customer(타깃)는 상품 FACT를 바꾸지 않는 고객군 가설이며 사용자가 검토할 제안입니다.
- content_direction(콘텐츠 방향)은 확정 FACT를 어떻게 보여주고 설명할지에 대한 방향만 제안하세요.
- product_notes(상품 관련 참고·주의)는 새로운 사실을 단정하지 말고, 판매 전에 사용자가 추가 확인하면 좋은 정보가 있을 때만 '추가 확인 필요: ...' 형태로 작성하세요. 없으면 빈 배열입니다.
- 과장광고, 비교우위, 보장, 가짜 리뷰, 의료/법률/인증/안전 보장은 금지합니다.

상품명: {product_name}
CONFIRMED FACT:
{json.dumps(facts, ensure_ascii=False)}

정확히 다음 형태로 반환하세요:
{{
  "usage": ["한국어"],
  "operating": {{"category": null, "usage": ["한국어"], "sale_price": null, "cost": null}},
  "marketing": {{
    "features": [],
    "selling_points": ["한국어"],
    "target_customer": ["한국어"],
    "content_direction": "한국어 또는 null",
    "product_notes": ["추가 확인 필요: ..."]
  }},
  "warnings": []
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
        return result, {
            "provider": "openai-fact-first-ko",
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
