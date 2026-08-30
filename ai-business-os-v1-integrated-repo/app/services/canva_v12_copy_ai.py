from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any

import httpx

from app.core.config import settings
from app.services.canva_v12_text_export import CANVA_V12_COPY_FIELDS


AI_BLOCKED_FIELDS = {
    "review_1_author", "review_1_text",
    "review_2_author", "review_2_text",
    "review_3_author", "review_3_text",
    "shipping_copy", "exchange_return_copy", "return_restriction_copy",
}
AI_ELIGIBLE_FIELDS = tuple(
    name for name in CANVA_V12_COPY_FIELDS if name not in AI_BLOCKED_FIELDS
)


def _extract_response_text(payload: Mapping[str, Any]) -> str:
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                return str(content["text"])
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    raise RuntimeError("text model returned no readable output")


def _json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].lstrip()
    value = json.loads(cleaned)
    if not isinstance(value, dict):
        raise RuntimeError("AI copy output must be a JSON object")
    return value


def _safe_proposals(raw: Mapping[str, Any]) -> dict[str, str]:
    allowed = set(AI_ELIGIBLE_FIELDS)
    result: dict[str, str] = {}
    for name, value in raw.items():
        if name not in allowed or not isinstance(value, str):
            continue
        text = value.strip()
        if text:
            result[name] = text[:1000]
    return result


def generate_canva_v12_copy_candidates(
    *,
    product_name: str,
    confirmed_facts: Mapping[str, Any],
    approved_copy: Mapping[str, str],
) -> tuple[dict[str, str], dict[str, Any]]:
    """Generate editable candidates only; never save or approve them."""
    if not confirmed_facts.get("facts_confirmed"):
        return {}, {"provider": "blocked", "reason": "facts_unconfirmed"}
    missing = [name for name in AI_ELIGIBLE_FIELDS if not approved_copy.get(name)]
    if not missing:
        return {}, {"provider": "not_needed", "reason": "no_missing_eligible_fields"}
    if not settings.openai_api_key:
        return {}, {"provider": "safe-fallback", "model": None, "reason": "openai_not_configured"}

    model = os.getenv("OPENAI_TEXT_MODEL", "gpt-4.1-mini")
    prompt = f"""
당신은 한국 온라인 판매용 상세페이지 문안 제안 도우미입니다. JSON 객체만 반환하세요.

CONFIRMED FACT가 유일한 사실 근거입니다. 물리적 구조, 재질, 치수, 구성품, 성능,
효과, 인증, 안전성, 제조사, 원산지, 배송·교환·반품 조건을 추측하지 마세요.
가짜 리뷰와 리뷰 작성자를 만들지 마세요. 근거가 부족한 필드는 빈 문자열로 두세요.
과장, 최상급, 비교우위, 보장 표현을 사용하지 마세요.
기존 승인 문안은 변경하거나 다시 제안하지 마세요.

상품명: {product_name}
CONFIRMED FACT: {json.dumps(dict(confirmed_facts), ensure_ascii=False)}
기존 승인 문안: {json.dumps(dict(approved_copy), ensure_ascii=False)}
제안할 수 있는 미작성 필드: {json.dumps(missing, ensure_ascii=False)}

반환 형식: 위 미작성 필드명만 키로 갖는 JSON 객체.
각 값은 한국어 문자열이며 근거가 없으면 빈 문자열입니다.
""".strip()
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{settings.openai_api_base.rstrip('/')}/responses",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": model, "input": prompt},
            )
        response.raise_for_status()
        proposals = _safe_proposals(_json_object(_extract_response_text(response.json())))
        return proposals, {
            "provider": "openai-canva-copy-v1.2",
            "model": model,
            "auto_saved": False,
            "auto_approved": False,
        }
    except Exception as exc:
        return {}, {
            "provider": "safe-fallback",
            "model": model,
            "reason": type(exc).__name__,
            "auto_saved": False,
            "auto_approved": False,
        }
