from __future__ import annotations

import json
import os
from typing import Any

import httpx

from app.core.config import settings


IMAGE_PLAN_CATEGORIES = (
    "hero",
    "use_scene",
    "feature_focus",
    "detail",
    "simple_usage_flow",
    "line_drawing",
    "components",
    "extra",
)

CATEGORY_LABELS = {
    "hero": "메인 / 히어로",
    "use_scene": "사용 장면",
    "feature_focus": "특징 강조",
    "detail": "부분 상세",
    "simple_usage_flow": "간단 사용 / 활용 순서",
    "line_drawing": "라인드로잉 기본 2종",
    "components": "구성품 / 세트",
    "extra": "추가 이미지 아이디어",
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _clean_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = _clean_text(item)
        if text and text not in result:
            result.append(text)
    return result


def _plan(
    category: str,
    title: str,
    purpose: str,
    basis: list[str],
    execution: str,
    *,
    status: str = "review",
    note: str | None = None,
    required_reference: str | None = None,
) -> dict[str, Any]:
    return {
        "category": category,
        "category_label": CATEGORY_LABELS[category],
        "title": title,
        "purpose": purpose,
        "basis": [x for x in basis if _clean_text(x)],
        "execution": execution,
        "status": status,
        "note": note,
        "required_reference": required_reference,
    }


def _dimensions_present(facts: dict[str, Any]) -> bool:
    dims = facts.get("dimensions") or {}
    return isinstance(dims, dict) and any(_clean_text(dims.get(k)) for k in ("length", "width", "height"))


def _fallback_plans(
    *,
    facts: dict[str, Any],
    image_slots: list[str],
    operating_info: dict[str, Any],
    marketing_info: dict[str, Any],
) -> list[dict[str, Any]]:
    slots = set(image_slots)
    usage = _clean_list(operating_info.get("usage"))
    features = _clean_list(marketing_info.get("features"))
    selling = _clean_list(marketing_info.get("selling_points"))
    direction = _clean_text(marketing_info.get("content_direction"))
    plans: list[dict[str, Any]] = []

    if "RIGHT_45" in slots:
        plans.append(_plan(
            "hero",
            "대표 제품 중심 메인 이미지",
            "상품을 한눈에 인식할 수 있는 대표 이미지",
            ["RIGHT_45 이미지 FACT", direction or "확정 콘텐츠 방향"],
            "AI 생성 또는 안전한 합성",
        ))

    if usage:
        plans.append(_plan(
            "use_scene",
            f"{usage[0]} 사용 장면",
            "상품이 어디서 어떻게 쓰이는지 직관적으로 전달",
            [f"확정 용도: {usage[0]}", "상품 이미지 FACT"],
            "AI 생성",
        ))

    visual_feature = (features + selling)[:1]
    if visual_feature:
        plans.append(_plan(
            "feature_focus",
            f"{visual_feature[0]} 특징 강조",
            "구매자가 확인할 핵심 특징을 시각적으로 강조",
            [f"확정 특징/판매포인트: {visual_feature[0]}", "상품 이미지 FACT"],
            "기존 FACT 활용 또는 AI 생성",
        ))

    if "DETAIL" in slots:
        plans.append(_plan(
            "detail",
            "실제 DETAIL FACT 기반 부분 상세",
            "제품의 중요한 실제 부분을 가까이 확인",
            ["DETAIL 이미지 FACT"],
            "기존 FACT 이미지 활용/크롭",
            status="fact",
        ))

    # Simple usage-flow is intentionally conservative. It is a content idea, not a product manual.
    if usage:
        plans.append(_plan(
            "simple_usage_flow",
            "간단 사용 흐름",
            "누구나 이해할 수 있는 짧은 활용 순서를 보여주는 콘텐츠",
            [f"확정 용도: {usage[0]}", "일반적인 활용 맥락"],
            "2~5컷 콘텐츠 구성",
            note="복잡한 조립·설치·전문 사용법은 이 단계에서 다루지 않습니다.",
        ))

    if "FRONT" in slots:
        plans.append(_plan(
            "line_drawing",
            "정면 라인드로잉 · 상품 사이즈/규격용",
            "상품 사이즈와 외형을 명료하게 전달",
            ["FRONT 이미지 FACT", "확정 치수 FACT" if _dimensions_present(facts) else "FRONT 이미지 FACT"],
            "FACT 기반 라인드로잉",
            status="fact",
            note=None if _dimensions_present(facts) else "치수 FACT가 없으므로 숫자는 표시하지 않습니다.",
        ))
    if "RIGHT_45" in slots:
        plans.append(_plan(
            "line_drawing",
            "45도 라인드로잉 · 설명/주의사항 재사용용",
            "향후 설명·주의표시 콘텐츠에 재사용할 기본 도면 자산",
            ["RIGHT_45 이미지 FACT"],
            "FACT 기반 라인드로잉",
            status="fact",
        ))

    packaging = facts.get("packaging") or {}
    component_hint = _clean_text(facts.get("fact_notes"))
    if isinstance(packaging, dict) and any(_clean_text(v) for v in packaging.values()):
        component_hint = component_hint or "확정 포장/구성 정보"
    if component_hint:
        plans.append(_plan(
            "components",
            "본품과 확정 구성품을 한눈에 보여주는 이미지",
            "실제 포함 구성과 수량 확인",
            [component_hint],
            "기존 FACT 활용 또는 정리 배치",
            note="구성품·수량은 확정 FACT에 있는 내용만 사용합니다.",
        ))

    return plans[:10]


def _extract_response_text(payload: dict[str, Any]) -> str:
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                return content["text"]
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    raise RuntimeError("text model returned no readable output")


def build_image_plan_suggestions(
    *,
    product_name: str,
    facts: dict[str, Any],
    image_slots: list[str],
    operating_info: dict[str, Any],
    marketing_info: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Create editable image plans, never product-physical FACT.

    The planner uses confirmed product FACT, confirmed Product Image FACT slots and
    user-confirmed text basis. It plans what to show; it does not generate images.
    """
    if not facts.get("facts_confirmed"):
        return [], {"provider": "blocked", "reason": "facts_unconfirmed"}
    if not operating_info and not marketing_info:
        return [], {"provider": "blocked", "reason": "text_basis_unconfirmed"}

    fallback = _fallback_plans(
        facts=facts,
        image_slots=image_slots,
        operating_info=operating_info,
        marketing_info=marketing_info,
    )
    if not settings.openai_api_key:
        return fallback, {"provider": "safe-fallback", "model": None}

    model = os.getenv("OPENAI_TEXT_MODEL", "gpt-4.1-mini")
    prompt = f"""
You plan ecommerce product images. You do NOT generate images.

Canonical inputs:
- CONFIRMED PRODUCT FACT: {json.dumps(facts, ensure_ascii=False)}
- CONFIRMED PRODUCT IMAGE FACT SLOTS: {json.dumps(image_slots, ensure_ascii=False)}
- USER-CONFIRMED OPERATING INFO: {json.dumps(operating_info, ensure_ascii=False)}
- USER-CONFIRMED MARKETING INFO: {json.dumps(marketing_info, ensure_ascii=False)}

Hard rules:
1. Never invent or alter product shape, components, material, color, dimensions, quantity, installation method, performance or effect.
2. Every plan must reference Product Image FACT for product appearance.
3. If physical detail is not visible in available image FACT, do not propose generative reconstruction; say additional reference photo is needed.
4. Category counts: hero 1-3, use_scene 0-3, feature_focus 0-3, detail 0-3, simple_usage_flow 0-2, line_drawing exactly two when FRONT and RIGHT_45 are available (front size/spec + right-45 explanation/caution), components 0-2, extra 0-2.
5. simple_usage_flow is only a simple, ordinary 2-5 step usage-content idea. Never make a complex assembly/install manual.
6. line_drawing front is normally for size/spec. 45-degree is a reusable base drawing for later explanation/caution. Numeric dimensions only when confirmed FACT contains them.
7. detail may recommend existing FACT image use/crop instead of generation.
8. Avoid duplicate ideas across categories. Total should normally be 6-10; fewer is fine when the product does not need them.
9. Output Korean JSON only, array of objects with keys: category,title,purpose,basis,execution,status,note,required_reference.
10. category must be one of: {', '.join(IMAGE_PLAN_CATEGORIES)}. status is fact or review.

Product: {product_name}
""".strip()

    try:
        with httpx.Client(timeout=45.0) as client:
            response = client.post(
                f"{settings.openai_api_base.rstrip('/')}/responses",
                headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
                json={"model": model, "input": prompt},
            )
        response.raise_for_status()
        text = _extract_response_text(response.json()).strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].lstrip()
        raw = json.loads(text)
        if not isinstance(raw, list):
            raise RuntimeError("image plan output must be a JSON array")
        result: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict) or item.get("category") not in IMAGE_PLAN_CATEGORIES:
                continue
            title = _clean_text(item.get("title"))
            if not title:
                continue
            result.append(_plan(
                item["category"],
                title,
                _clean_text(item.get("purpose")) or "상품정보용 이미지 기획",
                _clean_list(item.get("basis")),
                _clean_text(item.get("execution")) or "AI 생성",
                status="fact" if item.get("status") == "fact" else "review",
                note=_clean_text(item.get("note")) or None,
                required_reference=_clean_text(item.get("required_reference")) or None,
            ))
        return (result or fallback)[:12], {"provider": "openai-image-planner", "model": model}
    except Exception as exc:
        return fallback, {
            "provider": "safe-fallback",
            "model": model,
            "fallback_reason": type(exc).__name__,
        }
