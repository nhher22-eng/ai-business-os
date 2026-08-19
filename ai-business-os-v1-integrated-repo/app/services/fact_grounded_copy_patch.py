from __future__ import annotations

from copy import deepcopy

from app.services import detail_page_studio as studio


_ORIGINAL_BUILD_SECTIONS = studio.build_sections


def _clean(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def apply_fact_grounding(sections: list[dict], snapshot: dict) -> list[dict]:
    """Replace product-specific selling copy with copy grounded only in current Product DB facts."""
    product = snapshot.get("product") or {}
    detail = snapshot.get("detail") or {}

    product_name = _clean(product.get("name")) or "상품"
    description = _clean(product.get("description"))
    usage = _clean(detail.get("usage"))
    usage_conditions = _clean(detail.get("usage_conditions"))

    grounded = deepcopy(sections)
    for section in grounded:
        section_type = section.get("section_type")
        content = deepcopy(section.get("content_json") or {})

        if section_type == "HERO":
            headline = description or usage or product_name
            subheadline = usage if usage and usage != headline else (usage_conditions or "")
            content.update(
                {
                    "title": product_name,
                    "headline": headline,
                    "subheadline": subheadline,
                    "fact_sources": [
                        "Product.name",
                        "Product.description",
                        "ProductDetail.usage",
                        "ProductDetail.usage_conditions",
                    ],
                    "copy_status": "fact_grounded",
                }
            )
            section["content_json"] = content
            section["source_type"] = "fact"

        elif section_type == "PROBLEM":
            items = []
            for value in (usage, usage_conditions):
                if value and value not in items:
                    items.append(value)
            content.update(
                {
                    "title": "사용 용도·조건",
                    "items": items,
                    "fact_sources": ["ProductDetail.usage", "ProductDetail.usage_conditions"],
                    "copy_status": "fact_grounded" if items else "missing_fact",
                }
            )
            section["content_json"] = content
            section["source_type"] = "fact"

    return grounded


def _fact_grounded_build_sections(db, *, tenant_id: str, product_id: str, strategy: str):
    sections = _ORIGINAL_BUILD_SECTIONS(
        db,
        tenant_id=tenant_id,
        product_id=product_id,
        strategy=strategy,
    )
    snapshot = studio.product_snapshot(db, tenant_id=tenant_id, product_id=product_id)
    return apply_fact_grounding(sections, snapshot)


def install_fact_grounded_copy_patch() -> None:
    if studio.build_sections is not _fact_grounded_build_sections:
        studio.build_sections = _fact_grounded_build_sections
