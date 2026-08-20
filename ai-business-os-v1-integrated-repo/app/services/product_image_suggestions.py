from __future__ import annotations

from typing import Any


def _items(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if str(item).strip()]
    return []


def build_image_suggestion_plan(
    product_name: str,
    suggestions: dict[str, Any] | None,
) -> list[dict[str, str]]:
    """Build a conservative image proposal plan from editable AI suggestions.

    The plan describes purpose/composition only. Product identity, physical
    details, components, colors and geometry are never supplied by this plan;
    Image Studio must obtain those from confirmed Product Master FACT and
    HARD LOCK reference images.
    """
    suggestions = suggestions or {}
    operating = suggestions.get("operating") or {}
    marketing = suggestions.get("marketing") or {}

    usages = _items(suggestions.get("usage") or operating.get("usage"))
    selling_points = _items(marketing.get("selling_points"))
    content_direction = str(marketing.get("content_direction") or "").strip()

    usage_hint = usages[0] if usages else "실제 사용 환경"
    lead = selling_points[0] if selling_points else product_name
    direction = content_direction or f"{product_name}의 실제 형태와 사용 맥락을 명확하게 보여주기"

    hard_rule = (
        "상품과 구성품의 형태·색상·재질·연결구조는 등록된 기준사진과 확정 FACT를 그대로 따르고, "
        "확인되지 않은 부품이나 기능은 추가하지 않는다. 이미지 안에 설명 문구나 수치 텍스트를 넣지 않는다."
    )

    return [
        {
            "key": "hero",
            "title": "대표 이미지 후보",
            "role": "primary",
            "image_type": "HERO",
            "style_preset": "PRODUCT_PHOTO",
            "usage_context": "SMARTSTORE",
            "aspect_ratio": "1:1",
            "request_text": (
                f"{lead}. 스마트스토어 대표 이미지 후보로 제품 자체가 한눈에 명확하게 보이도록 정돈된 구도. "
                f"{direction}. 배경은 제품 식별을 방해하지 않도록 단순하고 자연스럽게 구성한다. {hard_rule}"
            ),
        },
        {
            "key": "lifestyle",
            "title": "사용장면 이미지 후보",
            "role": "additional",
            "image_type": "LIFESTYLE",
            "style_preset": "LIFESTYLE_PHOTO",
            "usage_context": "DETAIL_PAGE",
            "aspect_ratio": "4:3",
            "request_text": (
                f"{product_name}의 {usage_hint} 사용장면을 보여주는 실제적인 라이프스타일 이미지. "
                f"{direction}. 제품이 실제로 사용되는 맥락은 보여주되 불필요한 액세서리나 임의 구성품은 배치하지 않는다. {hard_rule}"
            ),
        },
        {
            "key": "explanation",
            "title": "상품 이해 이미지 후보",
            "role": "additional",
            "image_type": "EXPLANATION",
            "style_preset": "PRODUCT_PHOTO",
            "usage_context": "DETAIL_PAGE",
            "aspect_ratio": "4:3",
            "request_text": (
                f"{product_name}의 형태와 실제 구성 관계를 고객이 쉽게 이해할 수 있도록 정돈된 설명용 제품 이미지. "
                "등록 이미지에서 확인되는 제품과 구성품만 사용하고, 없는 부품을 보완하거나 상상해서 넣지 않는다. "
                f"{hard_rule}"
            ),
        },
    ]
