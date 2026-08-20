from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dashboard_session import require_business_auth
from app.db.models import (
    ImageGeneratedAsset,
    ImageGenerationJob,
    ImageReferenceAsset,
    Product,
)
from app.db.product_registration import ProductRegistrationProfile
from app.db.session import SessionLocal
from app.services.image_studio import ImageStudioError, approve_asset
from app.services.product_image_suggestions import build_image_suggestion_plan


router = APIRouter(
    prefix="/api/v1/product-image-suggestions",
    tags=["product-image-suggestions"],
    dependencies=[Depends(require_business_auth)],
)

SUGGESTION_CREATED_BY_PREFIX = "product-registration-ai-suggestion:"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class SuggestionStartBody(BaseModel):
    force: bool = False


class SuggestionDecisionBody(BaseModel):
    decision: Literal["hold", "dismiss"]


class SuggestionAdoptBody(BaseModel):
    role: Literal["primary", "additional"] | None = None
    approved_by: str | None = "dashboard-user"


def _get_product(db: Session, *, tenant_id: str, product_id: str) -> Product:
    product = db.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.tenant_id == tenant_id,
        )
    )
    if product is None:
        raise HTTPException(404, detail="product not found")
    return product


def _get_profile(
    db: Session,
    *,
    tenant_id: str,
    product_id: str,
) -> ProductRegistrationProfile:
    row = db.scalar(
        select(ProductRegistrationProfile).where(
            ProductRegistrationProfile.tenant_id == tenant_id,
            ProductRegistrationProfile.product_id == product_id,
        )
    )
    if row is None:
        raise HTTPException(404, detail="product registration profile not found")
    return row


def _latest_preview(db: Session, job_id: str) -> ImageGeneratedAsset | None:
    return db.scalar(
        select(ImageGeneratedAsset)
        .where(
            ImageGeneratedAsset.job_id == job_id,
            ImageGeneratedAsset.asset_stage == "preview",
        )
        .order_by(ImageGeneratedAsset.version_no.desc())
    )


def _role_for_job(job: ImageGenerationJob) -> str:
    return "primary" if job.image_type == "HERO" else "additional"


def _title_for_job(job: ImageGenerationJob) -> str:
    return {
        "HERO": "대표 이미지 후보",
        "LIFESTYLE": "사용장면 이미지 후보",
        "EXPLANATION": "상품 이해 이미지 후보",
        "BANNER": "배너 이미지 후보",
        "SPEC_SIZE": "스펙 이미지 후보",
    }.get(job.image_type, "AI 이미지 후보")


def _job_payload(db: Session, job: ImageGenerationJob) -> dict:
    asset = _latest_preview(db, job.id)
    return {
        "id": job.id,
        "product_id": job.product_id,
        "sku_id": job.sku_id,
        "title": _title_for_job(job),
        "role": _role_for_job(job),
        "image_type": job.image_type,
        "style_preset": job.style_preset,
        "usage_context": job.usage_context,
        "aspect_ratio": job.aspect_ratio,
        "protection_mode": job.protection_mode,
        "request_text": job.request_text,
        "status": job.status,
        "asset": None
        if asset is None
        else {
            "id": asset.id,
            "status": asset.status,
            "qa_status": asset.qa_status,
            "version_no": asset.version_no,
            "content_url": (
                f"/api/v1/images/assets/{asset.id}/content?tenant_id={job.tenant_id}"
            ),
        },
    }


def _suggestion_jobs(
    db: Session,
    *,
    tenant_id: str,
    product_id: str,
    include_dismissed: bool = False,
) -> list[ImageGenerationJob]:
    stmt = (
        select(ImageGenerationJob)
        .where(
            ImageGenerationJob.tenant_id == tenant_id,
            ImageGenerationJob.product_id == product_id,
            ImageGenerationJob.created_by.like(SUGGESTION_CREATED_BY_PREFIX + "%"),
        )
        .order_by(ImageGenerationJob.created_at.desc())
    )
    rows = list(db.scalars(stmt).all())
    if include_dismissed:
        return rows
    return [row for row in rows if row.status != "suggestion_dismissed"]


def _has_canonical_reference(
    db: Session,
    *,
    tenant_id: str,
    product_id: str,
) -> bool:
    return db.scalar(
        select(ImageReferenceAsset.id)
        .where(
            ImageReferenceAsset.tenant_id == tenant_id,
            ImageReferenceAsset.product_id == product_id,
            ImageReferenceAsset.job_id.is_(None),
            ImageReferenceAsset.internal_reference_only.is_(False),
            ImageReferenceAsset.lock_level == "hard_lock",
            ImageReferenceAsset.asset_role.in_(["PRODUCT_REFERENCE", "COMPONENT_REFERENCE"]),
        )
        .limit(1)
    ) is not None


@router.post("/products/{product_id}/start")
def start_product_image_suggestions(
    product_id: str,
    body: SuggestionStartBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    product = _get_product(db, tenant_id=tenant_id, product_id=product_id)
    profile = _get_profile(db, tenant_id=tenant_id, product_id=product_id)

    if not profile.facts_confirmed:
        raise HTTPException(
            409,
            detail="상품 FACT를 사용자 확정한 뒤 이미지 AI 제안을 만들 수 있습니다.",
        )
    if not _has_canonical_reference(db, tenant_id=tenant_id, product_id=product_id):
        raise HTTPException(
            409,
            detail="이미지 AI 제안 전 실제 상품 기준 이미지를 1장 이상 저장해 주세요.",
        )

    existing = [
        job
        for job in _suggestion_jobs(
            db,
            tenant_id=tenant_id,
            product_id=product_id,
            include_dismissed=False,
        )
        if job.status not in {"suggestion_adopted", "failed"}
    ]
    if existing and not body.force:
        return {
            "created": False,
            "jobs": [_job_payload(db, job) for job in existing[:6]],
        }

    plan = build_image_suggestion_plan(product.name, profile.ai_suggestions or {})
    created: list[ImageGenerationJob] = []
    for item in plan:
        job = ImageGenerationJob(
            tenant_id=tenant_id,
            workspace_id=product.workspace_id,
            product_id=product.id,
            sku_id=None,
            image_type=item["image_type"],
            style_preset=item["style_preset"],
            usage_context=item["usage_context"],
            aspect_ratio=item["aspect_ratio"],
            protection_mode="hard_lock",
            status="suggestion_queued",
            request_text=item["request_text"],
            created_by=SUGGESTION_CREATED_BY_PREFIX + item["key"],
        )
        db.add(job)
        created.append(job)
    db.commit()
    for job in created:
        db.refresh(job)

    return {
        "created": True,
        "jobs": [_job_payload(db, job) for job in created],
    }


@router.get("/products/{product_id}")
def list_product_image_suggestions(
    product_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    _get_product(db, tenant_id=tenant_id, product_id=product_id)
    rows = _suggestion_jobs(
        db,
        tenant_id=tenant_id,
        product_id=product_id,
        include_dismissed=False,
    )
    return {"jobs": [_job_payload(db, row) for row in rows[:9]]}


@router.post("/jobs/{job_id}/decision")
def decide_product_image_suggestion(
    job_id: str,
    body: SuggestionDecisionBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    job = db.scalar(
        select(ImageGenerationJob).where(
            ImageGenerationJob.id == job_id,
            ImageGenerationJob.tenant_id == tenant_id,
            ImageGenerationJob.created_by.like(SUGGESTION_CREATED_BY_PREFIX + "%"),
        )
    )
    if job is None:
        raise HTTPException(404, detail="image suggestion job not found")
    job.status = "suggestion_on_hold" if body.decision == "hold" else "suggestion_dismissed"
    db.commit()
    return {"ok": True, "job_id": job.id, "status": job.status}


@router.post("/assets/{asset_id}/adopt")
def adopt_product_image_suggestion(
    asset_id: str,
    body: SuggestionAdoptBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    asset = db.scalar(
        select(ImageGeneratedAsset).where(
            ImageGeneratedAsset.id == asset_id,
            ImageGeneratedAsset.tenant_id == tenant_id,
        )
    )
    if asset is None:
        raise HTTPException(404, detail="generated image not found")
    job = db.scalar(
        select(ImageGenerationJob).where(
            ImageGenerationJob.id == asset.job_id,
            ImageGenerationJob.tenant_id == tenant_id,
            ImageGenerationJob.created_by.like(SUGGESTION_CREATED_BY_PREFIX + "%"),
        )
    )
    if job is None:
        raise HTTPException(404, detail="image suggestion job not found")
    profile = _get_profile(db, tenant_id=tenant_id, product_id=job.product_id)

    try:
        if asset.status != "approved":
            approve_asset(
                db,
                job=job,
                asset=asset,
                approved_by=body.approved_by,
                acknowledge_review=True,
            )
    except ImageStudioError as exc:
        raise HTTPException(409, detail=str(exc)) from exc

    reference = db.scalar(
        select(ImageReferenceAsset).where(
            ImageReferenceAsset.tenant_id == tenant_id,
            ImageReferenceAsset.product_id == job.product_id,
            ImageReferenceAsset.job_id.is_(None),
            ImageReferenceAsset.asset_uri == asset.asset_uri,
        )
    )
    if reference is None:
        reference = ImageReferenceAsset(
            tenant_id=tenant_id,
            product_id=job.product_id,
            job_id=None,
            asset_role="PRODUCT_REFERENCE",
            asset_uri=asset.asset_uri,
            original_filename=f"ai-suggestion-{job.image_type.lower()}-v{asset.version_no}.png",
            mime_type="image/png",
            internal_reference_only=False,
            lock_level="hard_lock",
            sort_order=0 if (body.role or _role_for_job(job)) == "primary" else 100,
        )
        db.add(reference)
        db.flush()

    role = body.role or _role_for_job(job)
    additional = list(profile.additional_image_asset_ids or [])
    if role == "primary":
        profile.primary_image_asset_id = reference.id
        if reference.id in additional:
            additional.remove(reference.id)
            profile.additional_image_asset_ids = additional
    else:
        if reference.id not in additional:
            additional.append(reference.id)
        profile.additional_image_asset_ids = additional

    job.status = "suggestion_adopted"
    db.commit()
    return {
        "ok": True,
        "job_id": job.id,
        "generated_asset_id": asset.id,
        "reference_asset_id": reference.id,
        "role": role,
        "status": job.status,
        "images": {
            "primary_asset_id": profile.primary_image_asset_id,
            "additional_asset_ids": profile.additional_image_asset_ids or [],
        },
    }
