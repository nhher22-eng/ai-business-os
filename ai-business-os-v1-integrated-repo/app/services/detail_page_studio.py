from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import (
    BrandStyleSheet,
    BusinessWorkspace,
    DetailPageExport,
    DetailPageJob,
    DetailPageQAResult,
    DetailPageSection,
    DetailPageTemplate,
    DetailPageVersion,
    ImageGeneratedAsset,
    ImageGenerationJob,
    Product,
    ProductComponent,
    ProductDetail,
    ProductRelation,
    ProductSKU,
    ReviewSource,
)


TEMPLATE_DEFINITIONS = {
    "A_PRACTICAL_TRUST": {
        "name": "A — 실용·신뢰형",
        "description": "제품 이해, 실제 사용장면, 리뷰와 정확한 정보의 균형을 우선하는 기본 템플릿",
        "layout_rules": {"image_weight": "balanced", "card_style": "clean", "density": "medium"},
    },
    "B_LIFESTYLE": {
        "name": "B — 라이프스타일형",
        "description": "사용장면과 이미지 비중을 높여 감성적 사용 맥락을 먼저 보여주는 템플릿",
        "layout_rules": {"image_weight": "high", "card_style": "soft", "density": "low"},
    },
    "C_TECHNICAL": {
        "name": "C — 정보·기술형",
        "description": "스펙, 구성품, 설치법, 라인드로잉 등 정확한 정보 전달을 강화한 템플릿",
        "layout_rules": {"image_weight": "medium", "card_style": "technical", "density": "high"},
    },
}

DEFAULT_BRAND = {
    "name": "기본 브랜드 스타일",
    "primary_color": "#1F6B4F",
    "secondary_color": "#A7C4B5",
    "accent_color": "#E7B65A",
    "background_color": "#FFFFFF",
    "surface_color": "#F5F7F6",
    "text_color": "#17211C",
    "muted_text_color": "#66756D",
    "color_lock_enabled": True,
    "image_style_rules": {
        "product_color_lock": True,
        "prefer_real_product_assets": True,
        "brand_colors_apply_to_design_only": True,
    },
}

BASE_SECTION_ORDER = [
    "HERO",
    "REVIEW_SUMMARY",
    "PROBLEM",
    "LIFESTYLE",
    "FEATURE",
    "OPTION_COMPARE",
    "ADD_ON",
    "COMPONENTS",
    "INSTALLATION",
    "SPEC",
    "REVIEW_DETAIL",
    "RELATED_PRODUCTS",
    "FAQ",
]

STRATEGY_ORDERS = {
    "standard": BASE_SECTION_ORDER,
    "review_first": BASE_SECTION_ORDER,
    "specs_first": [
        "HERO", "REVIEW_SUMMARY", "FEATURE", "SPEC", "OPTION_COMPARE", "LIFESTYLE",
        "PROBLEM", "ADD_ON", "COMPONENTS", "INSTALLATION", "REVIEW_DETAIL",
        "RELATED_PRODUCTS", "FAQ",
    ],
    "lifestyle_first": [
        "HERO", "LIFESTYLE", "REVIEW_SUMMARY", "PROBLEM", "FEATURE", "OPTION_COMPARE",
        "ADD_ON", "COMPONENTS", "INSTALLATION", "SPEC", "REVIEW_DETAIL",
        "RELATED_PRODUCTS", "FAQ",
    ],
    "add_on_earlier": [
        "HERO", "REVIEW_SUMMARY", "PROBLEM", "LIFESTYLE", "FEATURE", "OPTION_COMPARE",
        "ADD_ON", "COMPONENTS", "INSTALLATION", "SPEC", "REVIEW_DETAIL",
        "RELATED_PRODUCTS", "FAQ",
    ],
}

REQUIRED_SECTIONS = {
    "HERO", "REVIEW_SUMMARY", "PROBLEM", "LIFESTYLE", "FEATURE", "OPTION_COMPARE",
    "COMPONENTS", "INSTALLATION", "SPEC", "REVIEW_DETAIL", "FAQ",
}

RELATION_TYPES = {"ADD_ON", "RELATED_PRODUCT", "ACCESSORY", "REPLACEMENT"}

# Conservative claim words. These are review triggers, not automatic legal conclusions.
SENSITIVE_CLAIM_PATTERNS = [
    r"\b100\s*%\b",
    r"무조건",
    r"완벽(?:한|하게|히)?",
    r"국내\s*(?:최고|1위)",
    r"세계\s*(?:최고|1위)",
    r"평생",
    r"영구",
    r"절대",
    r"최고의",
]


def ensure_defaults(db: Session, *, tenant_id: str, workspace_id: str) -> tuple[BrandStyleSheet, list[DetailPageTemplate]]:
    workspace = db.scalar(
        select(BusinessWorkspace).where(
            BusinessWorkspace.id == workspace_id,
            BusinessWorkspace.tenant_id == tenant_id,
        )
    )
    if workspace is None:
        raise ValueError("workspace not found")

    brand = db.scalar(
        select(BrandStyleSheet).where(
            BrandStyleSheet.tenant_id == tenant_id,
            BrandStyleSheet.workspace_id == workspace_id,
            BrandStyleSheet.name == DEFAULT_BRAND["name"],
        )
    )
    if brand is None:
        brand = BrandStyleSheet(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            **DEFAULT_BRAND,
        )
        db.add(brand)
        db.flush()

    templates: list[DetailPageTemplate] = []
    for code, definition in TEMPLATE_DEFINITIONS.items():
        row = db.scalar(
            select(DetailPageTemplate).where(
                DetailPageTemplate.tenant_id == tenant_id,
                DetailPageTemplate.code == code,
            )
        )
        if row is None:
            row = DetailPageTemplate(
                tenant_id=tenant_id,
                code=code,
                name=definition["name"],
                description=definition["description"],
                layout_rules=definition["layout_rules"],
            )
            db.add(row)
            db.flush()
        templates.append(row)
    return brand, templates


def product_snapshot(db: Session, *, tenant_id: str, product_id: str) -> dict:
    product = db.scalar(select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id))
    if product is None:
        raise ValueError("product not found")
    detail = db.scalar(
        select(ProductDetail).where(
            ProductDetail.product_id == product_id,
            ProductDetail.tenant_id == tenant_id,
        )
    )
    skus = db.scalars(
        select(ProductSKU)
        .where(ProductSKU.product_id == product_id, ProductSKU.tenant_id == tenant_id)
        .order_by(ProductSKU.created_at)
    ).all()
    sku_payload = []
    for sku in skus:
        components = db.scalars(
            select(ProductComponent)
            .where(
                ProductComponent.tenant_id == tenant_id,
                ProductComponent.product_id == product_id,
                ProductComponent.sku_id == sku.id,
                ProductComponent.status == "active",
            )
            .order_by(ProductComponent.created_at)
        ).all()
        sku_payload.append(
            {
                "id": sku.id,
                "sku_code": sku.sku_code,
                "name": sku.name,
                "option_value": sku.option_value,
                "status": sku.status,
                "components": [
                    {
                        "component_code": c.component_code,
                        "name": c.name,
                        "quantity": c.quantity,
                        "unit": c.unit,
                        "notes": c.notes,
                    }
                    for c in components
                ],
            }
        )
    snapshot = {
        "product": {
            "id": product.id,
            "workspace_id": product.workspace_id,
            "product_code": product.product_code,
            "name": product.name,
            "status": product.status,
            "sales_channel": product.sales_channel,
            "description": product.description,
        },
        "detail": {
            "specification": detail.specification if detail else None,
            "usage": detail.usage if detail else None,
            "installation_method": detail.installation_method if detail else None,
            "usage_conditions": detail.usage_conditions if detail else None,
            "cautions": detail.cautions if detail else None,
        },
        "skus": sku_payload,
    }
    return snapshot


def snapshot_hash(snapshot: dict) -> str:
    raw = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _active_relations(db: Session, tenant_id: str, product_id: str, relation_type: str) -> list[dict]:
    rows = db.scalars(
        select(ProductRelation)
        .where(
            ProductRelation.tenant_id == tenant_id,
            ProductRelation.source_product_id == product_id,
            ProductRelation.relation_type == relation_type,
            ProductRelation.is_active.is_(True),
        )
        .order_by(ProductRelation.sort_order, ProductRelation.created_at)
    ).all()
    payload = []
    for row in rows:
        target = None
        if row.target_product_id:
            target = db.scalar(
                select(Product).where(
                    Product.id == row.target_product_id,
                    Product.tenant_id == tenant_id,
                )
            )
        payload.append(
            {
                "relation_id": row.id,
                "target_product_id": row.target_product_id,
                "name": row.display_name or (target.name if target else None),
                "url": row.target_url,
                "image_asset_uri": row.image_asset_uri,
                "notes": row.notes,
            }
        )
    return payload


def _verified_reviews(db: Session, tenant_id: str, product_id: str) -> list[dict]:
    rows = db.scalars(
        select(ReviewSource)
        .where(
            ReviewSource.tenant_id == tenant_id,
            ReviewSource.product_id == product_id,
            ReviewSource.is_verified.is_(True),
        )
        .order_by(ReviewSource.reviewed_at.desc(), ReviewSource.created_at.desc())
    ).all()
    return [
        {
            "id": r.id,
            "channel": r.channel,
            "external_review_id": r.external_review_id,
            "rating": r.rating,
            "review_text": r.review_text,
            "photo_asset_uri": r.photo_asset_uri,
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
        }
        for r in rows
    ]


def _approved_image(db: Session, tenant_id: str, product_id: str, image_types: Iterable[str]) -> str | None:
    job_ids = db.scalars(
        select(ImageGenerationJob.id).where(
            ImageGenerationJob.tenant_id == tenant_id,
            ImageGenerationJob.product_id == product_id,
            ImageGenerationJob.image_type.in_(list(image_types)),
        )
    ).all()
    if not job_ids:
        return None
    asset = db.scalar(
        select(ImageGeneratedAsset)
        .where(
            ImageGeneratedAsset.tenant_id == tenant_id,
            ImageGeneratedAsset.job_id.in_(job_ids),
            ImageGeneratedAsset.asset_stage == "final",
            ImageGeneratedAsset.status == "approved",
        )
        .order_by(ImageGeneratedAsset.approved_at.desc(), ImageGeneratedAsset.created_at.desc())
    )
    return asset.id if asset else None


def build_sections(
    db: Session,
    *,
    tenant_id: str,
    product_id: str,
    strategy: str,
) -> list[dict]:
    facts = product_snapshot(db, tenant_id=tenant_id, product_id=product_id)
    product = facts["product"]
    detail = facts["detail"]
    skus = facts["skus"]
    reviews = _verified_reviews(db, tenant_id, product_id)
    add_ons = _active_relations(db, tenant_id, product_id, "ADD_ON")
    related = _active_relations(db, tenant_id, product_id, "RELATED_PRODUCT")

    lifestyle_asset_id = _approved_image(db, tenant_id, product_id, ["LIFESTYLE", "HERO"])
    spec_asset_id = _approved_image(db, tenant_id, product_id, ["SPEC_SIZE", "EXPLANATION"])

    options = [
        {
            "sku_id": sku["id"],
            "sku_code": sku["sku_code"],
            "name": sku["name"],
            "option_value": sku["option_value"],
            "components": sku["components"],
        }
        for sku in skus
        if sku["status"] == "active"
    ]

    component_map: dict[str, dict] = {}
    for sku in options:
        for comp in sku["components"]:
            key = comp["component_code"]
            component_map.setdefault(
                key,
                {"component_code": key, "name": comp["name"], "by_sku": []},
            )
            component_map[key]["by_sku"].append(
                {"sku_code": sku["sku_code"], "quantity": comp["quantity"], "unit": comp["unit"]}
            )

    review_summary = {
        "title": "실제 구매고객의 사용후기",
        "data_status": "ready" if reviews else "missing",
        "review_count": len(reviews),
        "average_rating": (
            round(sum(r["rating"] for r in reviews if r["rating"] is not None) /
                  len([r for r in reviews if r["rating"] is not None]), 2)
            if any(r["rating"] is not None for r in reviews) else None
        ),
        "review_ids": [r["id"] for r in reviews[:6]],
        "note": None if reviews else "실제 리뷰 데이터 연결 후 표시",
    }

    sections = {
        "HERO": {
            "title": product["name"],
            "headline": "여러 화분의 물주기, 하나의 관수라인으로",
            "subheadline": product["description"] or "상품 정보에 기반해 핵심 용도를 명확하게 보여줍니다.",
            "option_labels": [o["option_value"] or o["name"] for o in options],
            "fact_sources": ["Product", "ProductSKU"],
        },
        "REVIEW_SUMMARY": review_summary,
        "PROBLEM": {
            "title": "이런 경우에",
            "items": [
                "여러 화분을 한 번에 관리하고 싶은 경우",
                "베란다·텃밭·플랜터에 관수라인이 필요한 경우",
                "설치 규모에 맞는 길이 옵션을 선택하고 싶은 경우",
            ],
            "copy_status": "draft_copy",
        },
        "LIFESTYLE": {
            "title": "실제 사용 모습",
            "body": detail["usage"] or "승인된 사용장면 이미지와 확정된 사용정보를 연결합니다.",
            "fact_sources": ["ProductDetail.usage"],
            "image_asset_id": lifestyle_asset_id,
            "asset_status": "ready" if lifestyle_asset_id else "image_required",
        },
        "FEATURE": {
            "title": "제품 핵심 특징",
            "product_specification": detail["specification"],
            "usage": detail["usage"],
            "fact_sources": ["ProductDetail"],
        },
        "OPTION_COMPARE": {
            "title": "옵션을 비교해 보세요",
            "options": options,
            "fact_sources": ["ProductSKU", "ProductComponent"],
        },
        "ADD_ON": {
            "title": "함께 사용하면 좋은 추가상품",
            "items": add_ons,
            "disclosure": "※ 추가상품은 기본 구성품이 아닙니다.",
            "fact_sources": ["ProductRelation.ADD_ON"],
        },
        "COMPONENTS": {
            "title": "실제 구성품",
            "components": list(component_map.values()),
            "fact_sources": ["ProductComponent"],
        },
        "INSTALLATION": {
            "title": "설치방법",
            "body": detail["installation_method"],
            "data_status": "ready" if detail["installation_method"] else "missing",
            "fact_sources": ["ProductDetail.installation_method"],
        },
        "SPEC": {
            "title": "제품 상세정보",
            "specification": detail["specification"],
            "usage_conditions": detail["usage_conditions"],
            "options": options,
            "image_asset_id": spec_asset_id,
            "fact_sources": ["ProductDetail", "ProductSKU", "ProductComponent"],
        },
        "REVIEW_DETAIL": {
            "title": "고객 리뷰",
            "data_status": "ready" if reviews else "missing",
            "reviews": reviews[:12],
            "note": None if reviews else "실제 리뷰 데이터 연결 후 표시",
            "fact_sources": ["ReviewSource"],
        },
        "RELATED_PRODUCTS": {
            "title": "함께 둘러보면 좋은 상품",
            "items": related,
            "fact_sources": ["ProductRelation.RELATED_PRODUCT"],
        },
        "FAQ": {
            "title": "구매 전 확인",
            "cautions": detail["cautions"],
            "usage_conditions": detail["usage_conditions"],
            "items": [],
            "fact_sources": ["ProductDetail.cautions", "ProductDetail.usage_conditions"],
        },
    }

    order = STRATEGY_ORDERS.get(strategy, STRATEGY_ORDERS["review_first"])
    result = []
    for section_type in order:
        content = deepcopy(sections[section_type])
        enabled = True
        if section_type == "ADD_ON" and not add_ons:
            enabled = False
        if section_type == "RELATED_PRODUCTS" and not related:
            enabled = False
        image_asset_id = content.pop("image_asset_id", None)
        result.append(
            {
                "section_type": section_type,
                "is_required": section_type in REQUIRED_SECTIONS,
                "is_enabled": enabled,
                "layout_variant": _default_layout(section_type),
                "source_type": _source_type(section_type),
                "content_json": content,
                "image_asset_id": image_asset_id,
            }
        )
    return result


def _default_layout(section_type: str) -> str:
    return {
        "HERO": "full_bleed",
        "REVIEW_SUMMARY": "trust_strip",
        "LIFESTYLE": "image_story",
        "OPTION_COMPARE": "comparison_cards",
        "ADD_ON": "independent_section",
        "COMPONENTS": "fact_grid",
        "INSTALLATION": "step_stack",
        "SPEC": "spec_table",
        "REVIEW_DETAIL": "review_cards",
        "RELATED_PRODUCTS": "product_cards",
    }.get(section_type, "standard")


def _source_type(section_type: str) -> str:
    if section_type in {"OPTION_COMPARE", "COMPONENTS", "SPEC"}:
        return "fact"
    if section_type in {"REVIEW_SUMMARY", "REVIEW_DETAIL"}:
        return "review"
    if section_type in {"ADD_ON", "RELATED_PRODUCTS"}:
        return "relation"
    return "copy"


def create_prepared_version(
    db: Session,
    *,
    job: DetailPageJob,
    template: DetailPageTemplate,
    brand: BrandStyleSheet,
    visual_style: str,
    page_strategy: str,
    change_summary: str,
) -> DetailPageVersion:
    next_version = job.current_version_no + 1
    facts = product_snapshot(db, tenant_id=job.tenant_id, product_id=job.product_id)
    version = DetailPageVersion(
        tenant_id=job.tenant_id,
        job_id=job.id,
        version_no=next_version,
        template_id=template.id,
        brand_style_sheet_id=brand.id,
        visual_style=visual_style,
        page_strategy=page_strategy,
        status="p0_review",
        change_summary=change_summary,
        fact_snapshot_hash=snapshot_hash(facts),
    )
    db.add(version)
    db.flush()
    sections = build_sections(
        db,
        tenant_id=job.tenant_id,
        product_id=job.product_id,
        strategy=page_strategy,
    )
    for idx, spec in enumerate(sections, start=1):
        row = DetailPageSection(
            tenant_id=job.tenant_id,
            version_id=version.id,
            sort_order=idx,
            qa_status="review" if spec["is_enabled"] else "hidden",
            **spec,
        )
        db.add(row)
    job.current_version_no = next_version
    job.status = "p0_review"
    db.flush()
    return version


def clone_version(
    db: Session,
    *,
    job: DetailPageJob,
    source: DetailPageVersion,
    change_summary: str,
    template_id: str | None = None,
    brand_style_sheet_id: str | None = None,
    visual_style: str | None = None,
    page_strategy: str | None = None,
) -> DetailPageVersion:
    next_version = job.current_version_no + 1
    version = DetailPageVersion(
        tenant_id=job.tenant_id,
        job_id=job.id,
        version_no=next_version,
        template_id=template_id or source.template_id,
        brand_style_sheet_id=brand_style_sheet_id or source.brand_style_sheet_id,
        visual_style=visual_style or source.visual_style,
        page_strategy=page_strategy or source.page_strategy,
        status="p1_review",
        change_summary=change_summary,
        fact_snapshot_hash=source.fact_snapshot_hash,
    )
    db.add(version)
    db.flush()
    rows = db.scalars(
        select(DetailPageSection)
        .where(DetailPageSection.version_id == source.id)
        .order_by(DetailPageSection.sort_order)
    ).all()
    for row in rows:
        db.add(
            DetailPageSection(
                tenant_id=job.tenant_id,
                version_id=version.id,
                section_type=row.section_type,
                sort_order=row.sort_order,
                is_required=row.is_required,
                is_enabled=row.is_enabled,
                layout_variant=row.layout_variant,
                source_type=row.source_type,
                content_json=deepcopy(row.content_json),
                image_asset_id=row.image_asset_id,
                qa_status="review" if row.is_enabled else "hidden",
            )
        )
    job.current_version_no = next_version
    job.status = "p1_review"
    db.flush()
    return version


def current_version(db: Session, job: DetailPageJob) -> DetailPageVersion | None:
    if job.current_version_no <= 0:
        return None
    return db.scalar(
        select(DetailPageVersion).where(
            DetailPageVersion.job_id == job.id,
            DetailPageVersion.version_no == job.current_version_no,
        )
    )


def version_sections(db: Session, version_id: str) -> list[DetailPageSection]:
    return db.scalars(
        select(DetailPageSection)
        .where(DetailPageSection.version_id == version_id)
        .order_by(DetailPageSection.sort_order)
    ).all()


def reorder_sections(db: Session, *, version: DetailPageVersion, ordered_ids: list[str]) -> None:
    rows = version_sections(db, version.id)
    by_id = {row.id: row for row in rows}
    if set(ordered_ids) != set(by_id):
        raise ValueError("section_ids must include every section exactly once")
    # Avoid the unique(version_id, sort_order) collision by shifting first.
    for idx, row in enumerate(rows, start=1):
        row.sort_order = 1000 + idx
    db.flush()
    for idx, section_id in enumerate(ordered_ids, start=1):
        by_id[section_id].sort_order = idx
    db.flush()


def update_copy_section(section: DetailPageSection, *, headline: str | None = None, body: str | None = None) -> None:
    if section.source_type in {"fact", "review", "relation"}:
        raise ValueError("FACT/review/relation sections cannot be overwritten as free-form copy")
    content = deepcopy(section.content_json or {})
    if headline is not None:
        content["headline"] = headline
    if body is not None:
        content["body"] = body
    content["copy_status"] = "user_edited"
    section.content_json = content
    section.qa_status = "review"


def apply_natural_language_revision(db: Session, *, version: DetailPageVersion, instruction: str) -> dict:
    text = instruction.strip().lower()
    rows = version_sections(db, version.id)
    if not rows:
        return {"applied": False, "reason": "no sections"}

    def move(section_type: str, target_index: int) -> dict:
        ordered = [r for r in rows if r.section_type != section_type]
        target = next((r for r in rows if r.section_type == section_type), None)
        if target is None:
            return {"applied": False, "reason": f"{section_type} section not found"}
        target_index = max(0, min(target_index, len(ordered)))
        ordered.insert(target_index, target)
        reorder_sections(db, version=version, ordered_ids=[r.id for r in ordered])
        return {"applied": True, "action": "move", "section_type": section_type, "to": target_index + 1}

    if "리뷰" in text and any(k in text for k in ["위", "앞", "hero", "히어로"]):
        return move("REVIEW_SUMMARY", 1)
    if ("추가상품" in text or "워터타이머" in text) and "옵션" in text and any(k in text for k in ["다음", "뒤", "후"]):
        option_idx = next((i for i, r in enumerate(rows) if r.section_type == "OPTION_COMPARE"), 5)
        return move("ADD_ON", option_idx + 1)
    if "스펙" in text and any(k in text for k in ["위", "앞", "먼저"]):
        return move("SPEC", 2)
    if "라이프스타일" in text and any(k in text for k in ["위", "앞", "먼저"]):
        return move("LIFESTYLE", 1)
    return {
        "applied": False,
        "reason": "안전하게 자동 적용할 수 없는 요청입니다. 해당 블록을 선택해 직접 수정하거나 섹션 순서를 드래그해 주세요.",
        "requires_review": True,
    }


def _find_claims(value) -> list[str]:
    hits: list[str] = []
    if isinstance(value, str):
        for pattern in SENSITIVE_CLAIM_PATTERNS:
            if re.search(pattern, value, flags=re.IGNORECASE):
                hits.append(pattern)
    elif isinstance(value, dict):
        for item in value.values():
            hits.extend(_find_claims(item))
    elif isinstance(value, list):
        for item in value:
            hits.extend(_find_claims(item))
    return hits


def run_qa(db: Session, *, job: DetailPageJob, version: DetailPageVersion) -> list[DetailPageQAResult]:
    db.execute(
        delete(DetailPageQAResult).where(
            DetailPageQAResult.job_id == job.id,
            DetailPageQAResult.version_no == version.version_no,
        )
    )
    db.flush()
    sections = version_sections(db, version.id)
    enabled = [s for s in sections if s.is_enabled]
    by_type = {s.section_type: s for s in enabled}
    results: list[DetailPageQAResult] = []

    def add(code: str, status: str, message: str, *, severity: str = "info", section=None, fix=None):
        row = DetailPageQAResult(
            tenant_id=job.tenant_id,
            job_id=job.id,
            version_no=version.version_no,
            section_id=section.id if section else None,
            check_code=code,
            status=status,
            severity=severity,
            message=message,
            suggested_fix=fix,
            resolved=False,
        )
        db.add(row)
        results.append(row)

    current_hash = snapshot_hash(product_snapshot(db, tenant_id=job.tenant_id, product_id=job.product_id))
    if version.fact_snapshot_hash and current_hash != version.fact_snapshot_hash:
        add(
            "FACT_SNAPSHOT",
            "FAIL",
            "현재 상품 FACT가 이 상세페이지 버전을 만들 때의 상품정보와 달라졌습니다.",
            severity="error",
            fix="변경사항 반영본을 새 버전으로 생성하세요.",
        )
    else:
        add("FACT_SNAPSHOT", "PASS", "상품 FACT 스냅샷이 현재 데이터와 일치합니다.")

    missing_required = sorted(REQUIRED_SECTIONS - set(by_type))
    if missing_required:
        add(
            "REQUIRED_SECTIONS",
            "FAIL",
            f"필수 섹션 누락: {', '.join(missing_required)}",
            severity="error",
            fix="필수 섹션을 다시 활성화하세요.",
        )
    else:
        add("REQUIRED_SECTIONS", "PASS", "필수 상세페이지 섹션이 모두 존재합니다.")

    reviews = _verified_reviews(db, job.tenant_id, job.product_id)
    review_sections = [s for s in enabled if s.section_type in {"REVIEW_SUMMARY", "REVIEW_DETAIL"}]
    if not reviews:
        add(
            "REVIEW_SOURCE",
            "REVIEW",
            "실제 고객 리뷰 데이터가 아직 연결되지 않았습니다. 리뷰 블록은 자리만 유지되고 가짜 리뷰는 생성하지 않습니다.",
            severity="warning",
            section=review_sections[0] if review_sections else None,
            fix="실제 리뷰를 연결한 뒤 다시 QA 하세요.",
        )
    else:
        add("REVIEW_SOURCE", "PASS", f"검증된 실제 리뷰 {len(reviews)}건이 연결되어 있습니다.")

    add_on = by_type.get("ADD_ON")
    if add_on:
        content = add_on.content_json or {}
        disclosure = str(content.get("disclosure") or "")
        if "기본 구성품" not in disclosure:
            add(
                "ADD_ON_DISCLOSURE",
                "FAIL",
                "추가상품이 본품 기본 구성으로 오인될 수 있습니다.",
                severity="error",
                section=add_on,
                fix="'기본 구성품이 아닙니다' 표시를 추가하세요.",
            )
        else:
            add("ADD_ON_DISCLOSURE", "PASS", "추가상품 별도 판매 표시가 존재합니다.", section=add_on)

    related = by_type.get("RELATED_PRODUCTS")
    if related:
        items = (related.content_json or {}).get("items", [])
        broken = [item for item in items if not item.get("url")]
        if broken:
            add(
                "RELATED_LINKS",
                "REVIEW",
                f"관련상품 {len(broken)}개에 연결 URL이 없습니다.",
                severity="warning",
                section=related,
                fix="판매 URL을 연결하거나 해당 상품을 숨기세요.",
            )
        else:
            add("RELATED_LINKS", "PASS", "관련상품 링크가 준비되어 있습니다.", section=related)

    claim_sections = []
    for section in enabled:
        if _find_claims(section.content_json or {}):
            claim_sections.append(section)
    if claim_sections:
        add(
            "AD_CLAIM",
            "REVIEW",
            "근거 확인이 필요한 강한 광고 표현이 포함되어 있습니다.",
            severity="warning",
            section=claim_sections[0],
            fix="근거가 없다면 표현을 완화하세요.",
        )
    else:
        add("AD_CLAIM", "PASS", "사전 정의된 과장 표현 위험 패턴이 발견되지 않았습니다.")

    brand = db.scalar(select(BrandStyleSheet).where(BrandStyleSheet.id == version.brand_style_sheet_id))
    valid_hex = re.compile(r"^#[0-9A-Fa-f]{6}$")
    brand_values = [] if brand is None else [
        brand.primary_color, brand.secondary_color, brand.accent_color,
        brand.background_color, brand.surface_color, brand.text_color, brand.muted_text_color,
    ]
    if brand is None or any(not valid_hex.match(v or "") for v in brand_values):
        add("BRAND_STYLE", "FAIL", "브랜드 스타일 시트 컬러값이 올바르지 않습니다.", severity="error")
    else:
        add("BRAND_STYLE", "PASS", "브랜드 컬러 시트가 유효합니다.")

    # Lifestyle imagery is required for this v1 selling-page template.
    # SPEC can be rendered safely from FACT data alone; a line drawing/spec image is optional.
    lifestyle = by_type.get("LIFESTYLE")
    if lifestyle and not lifestyle.image_asset_id:
        add(
            "IMAGE_ASSETS",
            "REVIEW",
            "실제 사용 모습 섹션에 승인 이미지가 연결되지 않았습니다.",
            severity="warning",
            section=lifestyle,
            fix="M05에서 승인된 라이프스타일 이미지를 연결하세요.",
        )
    else:
        add("IMAGE_ASSETS", "PASS", "필수 라이프스타일 승인 이미지가 연결되어 있습니다.")

    spec = by_type.get("SPEC")
    if spec:
        spec_content = spec.content_json or {}
        has_spec_data = bool(
            spec_content.get("specification")
            or spec_content.get("usage_conditions")
            or spec_content.get("options")
        )
        if has_spec_data:
            add(
                "SPEC_DATA",
                "PASS",
                "제품 상세정보는 확정 FACT 데이터로 표시할 수 있습니다. 스펙 이미지는 선택사항입니다.",
                section=spec,
            )
        else:
            add(
                "SPEC_DATA",
                "REVIEW",
                "제품 상세정보에 표시할 확정 스펙 데이터가 부족합니다.",
                severity="warning",
                section=spec,
                fix="ProductDetail 또는 SKU 확정 스펙을 보완하세요.",
            )

    job.status = "qa_review"
    for section in sections:
        section.qa_status = "pass" if section.is_enabled else "hidden"
    for result in results:
        if result.section_id and result.status in {"FAIL", "REVIEW"}:
            target = next((s for s in sections if s.id == result.section_id), None)
            if target:
                target.qa_status = result.status.lower()
    db.flush()
    return results


def qa_summary(results: list[DetailPageQAResult]) -> str:
    if any(r.status == "FAIL" and not r.resolved for r in results):
        return "FAIL"
    if any(r.status == "REVIEW" and not r.resolved for r in results):
        return "REVIEW"
    return "PASS"


def approve_version(
    db: Session,
    *,
    job: DetailPageJob,
    version: DetailPageVersion,
    acknowledge_review: bool,
) -> str:
    rows = db.scalars(
        select(DetailPageQAResult).where(
            DetailPageQAResult.job_id == job.id,
            DetailPageQAResult.version_no == version.version_no,
        )
    ).all()
    if not rows:
        raise ValueError("QA must run before approval")
    summary = qa_summary(rows)
    if summary == "FAIL":
        raise ValueError("unresolved QA FAIL blocks approval")
    if summary == "REVIEW" and not acknowledge_review:
        raise ValueError("QA REVIEW requires acknowledge_review=true")
    version.status = "approved"
    job.status = "approved"
    job.approved_version_no = version.version_no
    db.flush()
    return summary


def export_package(db: Session, *, job: DetailPageJob, version: DetailPageVersion) -> DetailPageExport:
    if version.status != "approved" or job.approved_version_no != version.version_no:
        raise ValueError("only approved detail-page versions can be exported")
    template = db.scalar(select(DetailPageTemplate).where(DetailPageTemplate.id == version.template_id))
    brand = db.scalar(select(BrandStyleSheet).where(BrandStyleSheet.id == version.brand_style_sheet_id))
    facts = product_snapshot(db, tenant_id=job.tenant_id, product_id=job.product_id)
    sections = version_sections(db, version.id)
    payload = {
        "schema_version": "detail-page-export.v1",
        "job_id": job.id,
        "version_no": version.version_no,
        "channel": job.channel,
        "page_length": job.page_length,
        "template": {
            "id": template.id if template else None,
            "code": template.code if template else None,
            "name": template.name if template else None,
            "canva_brand_template_id": template.canva_brand_template_id if template else None,
        },
        "brand_style": None if brand is None else {
            "id": brand.id,
            "name": brand.name,
            "primary": brand.primary_color,
            "secondary": brand.secondary_color,
            "accent": brand.accent_color,
            "background": brand.background_color,
            "surface": brand.surface_color,
            "text": brand.text_color,
            "muted_text": brand.muted_text_color,
            "color_lock_enabled": brand.color_lock_enabled,
        },
        "visual_style": version.visual_style,
        "page_strategy": version.page_strategy,
        "product_facts": facts,
        "sections": [
            {
                "id": s.id,
                "type": s.section_type,
                "order": s.sort_order,
                "enabled": s.is_enabled,
                "layout": s.layout_variant,
                "source_type": s.source_type,
                "content": s.content_json,
                "image_asset_id": s.image_asset_id,
            }
            for s in sections
            if s.is_enabled
        ],
    }
    row = DetailPageExport(
        tenant_id=job.tenant_id,
        job_id=job.id,
        version_no=version.version_no,
        export_type="canva_package",
        status="ready",
        payload_json=payload,
    )
    db.add(row)
    job.status = "canva_export_ready"
    db.flush()
    return row
