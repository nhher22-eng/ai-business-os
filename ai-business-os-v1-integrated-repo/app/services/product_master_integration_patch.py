from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.api.images as images_api
from app.db.models import ProductDetail
from app.db.product_registration import ProductRegistrationProfile
from app.services import detail_page_autogen as detail_autogen
from app.services import detail_page_studio as detail_studio
from app.services import image_studio


_ORIGINAL_PRODUCT_SNAPSHOT = detail_studio.product_snapshot
_ORIGINAL_BUILD_SECTIONS = detail_studio.build_sections
_ORIGINAL_FACT_READINESS = detail_autogen.fact_readiness
_ORIGINAL_IMAGE_P0 = image_studio.build_p0_summary
_ORIGINAL_IMAGE_PROMPT = image_studio.build_generation_prompt
_INSTALLED = False


def _profile(db: Session, *, tenant_id: str, product_id: str) -> ProductRegistrationProfile | None:
    return db.scalar(
        select(ProductRegistrationProfile).where(
            ProductRegistrationProfile.tenant_id == tenant_id,
            ProductRegistrationProfile.product_id == product_id,
        )
    )


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(_has_value(v) for v in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_has_value(v) for v in value)
    return True


def confirmed_master_facts(profile: ProductRegistrationProfile | None) -> dict[str, Any]:
    """Return only user-confirmed source-of-truth product facts."""
    if profile is None or not profile.facts_confirmed:
        return {}
    values = {
        "model_name": profile.model_name,
        "primary_material": profile.primary_material,
        "secondary_material": profile.secondary_material,
        "weight": profile.weight,
        "dimensions": profile.dimensions or {},
        "manufacturer": profile.manufacturer,
        "country_of_origin": profile.country_of_origin,
        "certifications": profile.certifications or [],
        "packaging": profile.packaging or {},
        "fact_notes": profile.fact_notes,
    }
    return {key: value for key, value in values.items() if _has_value(value)}


def _fact_summary(facts: dict[str, Any]) -> str | None:
    if not facts:
        return None
    labels = {
        "model_name": "모델명",
        "primary_material": "주재질",
        "secondary_material": "보조재질",
        "weight": "중량",
        "dimensions": "사이즈",
        "manufacturer": "제조사",
        "country_of_origin": "원산지",
        "certifications": "인증",
        "packaging": "포장",
        "fact_notes": "추가 FACT",
    }
    parts: list[str] = []
    for key, value in facts.items():
        if isinstance(value, (dict, list)):
            rendered = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        else:
            rendered = str(value)
        parts.append(f"{labels.get(key, key)}: {rendered}")
    return " | ".join(parts)


def enriched_product_snapshot(db: Session, *, tenant_id: str, product_id: str) -> dict:
    snapshot = _ORIGINAL_PRODUCT_SNAPSHOT(db, tenant_id=tenant_id, product_id=product_id)
    profile = _profile(db, tenant_id=tenant_id, product_id=product_id)
    snapshot["registration"] = {
        "facts_confirmed": bool(profile and profile.facts_confirmed),
        "facts": confirmed_master_facts(profile),
        "operating_info": (profile.operating_info or {}) if profile else {},
        "marketing_info": (profile.marketing_info or {}) if profile else {},
        "primary_image_asset_id": profile.primary_image_asset_id if profile else None,
        "additional_image_asset_ids": (profile.additional_image_asset_ids or []) if profile else [],
    }
    return snapshot


def enhanced_fact_readiness(snapshot: dict) -> dict:
    readiness = dict(_ORIGINAL_FACT_READINESS(snapshot))
    registration = snapshot.get("registration") or {}
    has_master_fact = bool(
        registration.get("facts_confirmed")
        and _has_value(registration.get("facts") or {})
    )
    readiness["has_master_fact"] = has_master_fact
    if has_master_fact and "product_detail_or_sku" in readiness.get("missing", []):
        readiness["missing"] = [
            item for item in readiness["missing"] if item != "product_detail_or_sku"
        ]
        readiness["missing_labels"] = [
            label
            for label in readiness.get("missing_labels", [])
            if label != "확정 사양/사용정보 또는 SKU"
        ]
        readiness["ready"] = not readiness["missing"]
    return readiness


def _as_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if _has_value(item)]
    return []


def grounded_build_sections(
    db: Session,
    *,
    tenant_id: str,
    product_id: str,
    strategy: str,
) -> list[dict]:
    """Remove sample-product copy and bind sections to actual registered data."""
    rows = _ORIGINAL_BUILD_SECTIONS(
        db,
        tenant_id=tenant_id,
        product_id=product_id,
        strategy=strategy,
    )
    snapshot = enriched_product_snapshot(db, tenant_id=tenant_id, product_id=product_id)
    product = snapshot["product"]
    detail = snapshot["detail"]
    registration = snapshot["registration"]
    master_facts = registration.get("facts") or {}
    operating = registration.get("operating_info") or {}
    marketing = registration.get("marketing_info") or {}
    usage = _as_list(operating.get("usage"))
    if not usage and detail.get("usage"):
        usage = [detail["usage"]]
    features = _as_list(marketing.get("features"))
    selling_points = _as_list(marketing.get("selling_points"))
    summary = detail.get("specification") or _fact_summary(master_facts)

    for row in rows:
        section_type = row.get("section_type")
        content = row.get("content_json") or {}
        if section_type == "HERO":
            content["headline"] = selling_points[0] if selling_points else product["name"]
            content["subheadline"] = product.get("description") or marketing.get("content_direction")
            content["fact_sources"] = ["Product", "ProductRegistrationProfile", "ProductSKU"]
        elif section_type == "PROBLEM":
            content["title"] = "주요 사용 용도" if usage else "상품 사용 정보"
            content["items"] = usage
            content["copy_status"] = "fact_grounded" if usage else "missing"
        elif section_type == "LIFESTYLE":
            content["body"] = detail.get("usage") or (" / ".join(usage) if usage else None)
            content["fact_sources"] = ["ProductDetail.usage", "ProductRegistrationProfile.operating_info"]
        elif section_type == "FEATURE":
            content["product_specification"] = summary
            content["usage"] = detail.get("usage") or usage
            content["features"] = features
            content["master_facts"] = master_facts
            content["fact_sources"] = ["ProductDetail", "ProductRegistrationProfile"]
        elif section_type == "SPEC":
            content["specification"] = summary
            content["master_facts"] = master_facts
            content["fact_sources"] = [
                "ProductRegistrationProfile",
                "ProductDetail",
                "ProductSKU",
                "ProductComponent",
            ]
        row["content_json"] = content
    return rows


def grounded_image_p0(db: Session, job, references) -> str:
    base = _ORIGINAL_IMAGE_P0(db, job, references)
    profile = _profile(db, tenant_id=job.tenant_id, product_id=job.product_id)
    summary = _fact_summary(confirmed_master_facts(profile))
    if not summary:
        return base
    return base + "\n상품 Master 확정 FACT: " + summary


def grounded_image_prompt(db: Session, job, references, *, stage: str) -> str:
    base = _ORIGINAL_IMAGE_PROMPT(db, job, references, stage=stage)
    profile = _profile(db, tenant_id=job.tenant_id, product_id=job.product_id)
    facts = confirmed_master_facts(profile)
    if not facts:
        return base
    return (
        base
        + "\nCONFIRMED PRODUCT MASTER FACT (canonical; never alter or contradict): "
        + json.dumps(facts, ensure_ascii=False, separators=(",", ":"))
    )


def prepare_image_job_with_master(db: Session, job):
    refs = image_studio.references_for_job(db, job)
    if job.protection_mode == "hard_lock":
        has_canonical = any(
            ref.lock_level == "hard_lock"
            and ref.asset_role in {"PRODUCT_REFERENCE", "COMPONENT_REFERENCE"}
            for ref in refs
        )
        if not has_canonical:
            raise image_studio.ImageStudioError(
                "HARD LOCK 작업에는 PRODUCT_REFERENCE 또는 COMPONENT_REFERENCE 기준 이미지가 필요합니다."
            )
    if job.image_type == "SPEC_SIZE":
        detail = db.scalar(
            select(ProductDetail).where(
                ProductDetail.product_id == job.product_id,
                ProductDetail.tenant_id == job.tenant_id,
            )
        )
        profile = _profile(db, tenant_id=job.tenant_id, product_id=job.product_id)
        master = confirmed_master_facts(profile)
        has_dimensions = _has_value(master.get("dimensions"))
        if not ((detail and (detail.specification or "").strip()) or has_dimensions):
            raise image_studio.ImageStudioError(
                "SPEC_SIZE 작업에는 확정 상품 스펙 또는 상품 Master 사이즈 FACT가 필요합니다."
            )
    job.p0_summary = grounded_image_p0(db, job, refs)
    job.status = "p0_ready"
    db.commit()
    db.refresh(job)
    return job


def install_product_master_integration_patch() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    # Detail-page path. Imported aliases in detail_page_autogen must be patched too.
    detail_studio.product_snapshot = enriched_product_snapshot
    detail_studio.build_sections = grounded_build_sections
    detail_autogen.product_snapshot = enriched_product_snapshot
    detail_autogen.fact_readiness = enhanced_fact_readiness

    # Image path. images.py imported prepare_job by name, so patch both references.
    image_studio.build_p0_summary = grounded_image_p0
    image_studio.build_generation_prompt = grounded_image_prompt
    image_studio.prepare_job = prepare_image_job_with_master
    images_api.prepare_job = prepare_image_job_with_master

    _INSTALLED = True
