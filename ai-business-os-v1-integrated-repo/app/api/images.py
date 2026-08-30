from __future__ import annotations

from app.services.image_studio import ensure_product_image_fact_references

from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dashboard_session import require_business_auth
from app.db.models import (
    BusinessWorkspace,
    ImageGeneratedAsset,
    ImageGenerationJob,
    ImageQAResult,
    ImageReferenceAsset,
    ImageReviewEvent,
    Product,
    ProductSKU,
)
from app.db.session import SessionLocal
from app.core.config import settings
from app.services.image_studio import (
    ASPECT_RATIOS,
    IMAGE_TYPES,
    LOCK_LEVELS,
    REFERENCE_ROLES,
    STYLE_PRESETS,
    USAGE_CONTEXTS,
    ImageStudioError,
    ProviderNotConfigured,
    approve_asset,
    clean_original_brief,
    generate_stage,
    prepare_job,
    resolve_media_uri,
    run_image_qa,
    save_reference_upload,
)


router = APIRouter(
    prefix="/api/v1/images",
    tags=["image-studio"],
    dependencies=[Depends(require_business_auth)],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ImageJobBody(BaseModel):
    workspace_id: str
    product_id: str
    sku_id: str | None = None
    image_type: str = "LIFESTYLE"
    style_preset: str = "LIFESTYLE_PHOTO"
    usage_context: str = "DETAIL_PAGE"
    aspect_ratio: str = "4:3"
    custom_width: int | None = None
    custom_height: int | None = None
    protection_mode: Literal["hard_lock", "guided", "creative"] = "hard_lock"
    request_text: str | None = Field(default=None, max_length=5000)
    created_by: str | None = None


class RevisionBody(BaseModel):
    instruction: str = Field(min_length=1, max_length=5000)
    created_by: str | None = None


class ApprovalBody(BaseModel):
    approved_by: str | None = None
    acknowledge_review: bool = False


class ReferenceRegisterBody(BaseModel):
    product_id: str
    job_id: str | None = None
    asset_role: str
    asset_uri: str
    component_code: str | None = None
    internal_reference_only: bool = True
    lock_level: str = "hard_lock"
    sort_order: int = 0


def _job_payload(db: Session, job: ImageGenerationJob) -> dict:
    refs = db.scalars(
        select(ImageReferenceAsset).where(
            ImageReferenceAsset.tenant_id == job.tenant_id,
            ImageReferenceAsset.product_id == job.product_id,
            (ImageReferenceAsset.job_id == job.id) | (ImageReferenceAsset.job_id.is_(None)),
        )
    ).all()
    assets = db.scalars(
        select(ImageGeneratedAsset)
        .where(ImageGeneratedAsset.job_id == job.id)
        .order_by(ImageGeneratedAsset.created_at)
    ).all()
    revisions = db.scalars(
        select(ImageReviewEvent)
        .where(
            ImageReviewEvent.job_id == job.id,
            ImageReviewEvent.action == "request_revision",
        )
        .order_by(ImageReviewEvent.created_at)
    ).all()
    return {
        "id": job.id,
        "workspace_id": job.workspace_id,
        "product_id": job.product_id,
        "sku_id": job.sku_id,
        "image_type": job.image_type,
        "style_preset": job.style_preset,
        "usage_context": job.usage_context,
        "aspect_ratio": job.aspect_ratio,
        "custom_width": job.custom_width,
        "custom_height": job.custom_height,
        "protection_mode": job.protection_mode,
        "status": job.status,
        "request_text": job.request_text,
        "original_request_text": clean_original_brief(job.request_text),
        "p0_summary": job.p0_summary,
        "provider": job.provider,
        "model_name": job.model_name,
        "preview_count": job.preview_count,
        "final_count": job.final_count,
        "estimated_cost_micros": job.estimated_cost_micros,
        "actual_cost_micros": job.actual_cost_micros,
        "references": [
            {
                "id": r.id,
                "asset_role": r.asset_role,
                "component_code": r.component_code,
                "asset_uri": r.asset_uri,
                "original_filename": r.original_filename,
                "internal_reference_only": r.internal_reference_only,
                "lock_level": r.lock_level,
            }
            for r in refs
        ],
        "revisions": [
            {
                "id": r.id,
                "instruction": r.comment,
                "created_by": r.created_by,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in revisions
        ],
        "assets": [
            {
                "id": a.id,
                "stage": a.asset_stage,
                "version_no": a.version_no,
                "status": a.status,
                "asset_name": a.asset_name,
                "filename": a.filename,
                "role_code": a.role_code,
                "usage_code": a.usage_code,
                "content_hash": a.content_hash,
                "metadata": a.asset_metadata or {},
                "width": a.width,
                "height": a.height,
                "qa_status": a.qa_status,
                "content_url": f"/api/v1/images/assets/{a.id}/content?tenant_id={job.tenant_id}",
            }
            for a in assets
        ],
    }


@router.post("/jobs")
def create_job(
    body: ImageJobBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    if body.image_type not in IMAGE_TYPES:
        raise HTTPException(422, detail="unsupported image_type")
    if body.style_preset not in STYLE_PRESETS:
        raise HTTPException(422, detail="unsupported style_preset")
    if body.usage_context not in USAGE_CONTEXTS:
        raise HTTPException(422, detail="unsupported usage_context")
    if body.aspect_ratio not in ASPECT_RATIOS:
        raise HTTPException(422, detail="unsupported aspect_ratio")
    if body.protection_mode not in LOCK_LEVELS:
        raise HTTPException(422, detail="unsupported protection_mode")
    if body.aspect_ratio == "CUSTOM" and (not body.custom_width or not body.custom_height):
        raise HTTPException(422, detail="CUSTOM ratio requires custom_width/custom_height")

    workspace = db.scalar(
        select(BusinessWorkspace).where(
            BusinessWorkspace.id == body.workspace_id,
            BusinessWorkspace.tenant_id == tenant_id,
        )
    )
    product = db.scalar(
        select(Product).where(Product.id == body.product_id, Product.tenant_id == tenant_id)
    )
    if workspace is None or product is None or product.workspace_id != workspace.id:
        raise HTTPException(404, detail="workspace/product not found")
    if body.protection_mode != "hard_lock" and not product.image_nonlocked_allowed:
        raise HTTPException(
            409,
            detail="이 상품은 제품보존(HARD LOCK)이 기본입니다. 비잠금 모드는 상품 이미지 정책에서 예외 허용 후 사용할 수 있습니다.",
        )
    if body.sku_id:
        sku = db.scalar(
            select(ProductSKU).where(
                ProductSKU.id == body.sku_id,
                ProductSKU.product_id == body.product_id,
                ProductSKU.tenant_id == tenant_id,
            )
        )
        if sku is None:
            raise HTTPException(404, detail="sku not found")

    existing_draft = db.scalar(
        select(ImageGenerationJob)
        .where(
            ImageGenerationJob.tenant_id == tenant_id,
            ImageGenerationJob.product_id == body.product_id,
            ImageGenerationJob.sku_id == body.sku_id,
            ImageGenerationJob.image_type == body.image_type,
            ImageGenerationJob.style_preset == body.style_preset,
            ImageGenerationJob.usage_context == body.usage_context,
            ImageGenerationJob.aspect_ratio == body.aspect_ratio,
            ImageGenerationJob.protection_mode == body.protection_mode,
            ImageGenerationJob.request_text == body.request_text,
            ImageGenerationJob.status == "draft",
        )
        .order_by(ImageGenerationJob.created_at.desc())
    )
    if existing_draft is not None:
        ensure_product_image_fact_references(db, existing_draft)
        db.commit()
        db.refresh(existing_draft)
        return _job_payload(db, existing_draft)

    row = ImageGenerationJob(
        tenant_id=tenant_id,
        workspace_id=body.workspace_id,
        product_id=body.product_id,
        sku_id=body.sku_id,
        image_type=body.image_type,
        style_preset=body.style_preset,
        usage_context=body.usage_context,
        aspect_ratio=body.aspect_ratio,
        custom_width=body.custom_width,
        custom_height=body.custom_height,
        protection_mode=body.protection_mode,
        request_text=body.request_text,
        created_by=body.created_by,
    )
    db.add(row)
    db.flush()
    ensure_product_image_fact_references(db, row)
    db.commit()
    db.refresh(row)
    return _job_payload(db, row)


@router.get("/jobs")
def list_jobs(
    tenant_id: str = Query(..., min_length=1, max_length=128),
    product_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = select(ImageGenerationJob).where(ImageGenerationJob.tenant_id == tenant_id)
    if product_id:
        stmt = stmt.where(ImageGenerationJob.product_id == product_id)
    rows = db.scalars(stmt.order_by(ImageGenerationJob.created_at.desc())).all()
    return [_job_payload(db, row) for row in rows]


@router.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    row = db.scalar(
        select(ImageGenerationJob).where(
            ImageGenerationJob.id == job_id,
            ImageGenerationJob.tenant_id == tenant_id,
        )
    )
    if row is None:
        raise HTTPException(404, detail="image job not found")
    return _job_payload(db, row)


def _upload_reference(
    *,
    db: Session,
    tenant_id: str,
    product_id: str,
    job_id: str | None,
    file: UploadFile,
    content: bytes,
    asset_role: str,
    component_code: str | None,
    lock_level: str,
    internal_reference_only: bool,
    sort_order: int,
):
    if asset_role not in REFERENCE_ROLES:
        raise HTTPException(422, detail="unsupported asset_role")
    if lock_level not in LOCK_LEVELS:
        raise HTTPException(422, detail="unsupported lock_level")
    product = db.scalar(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    if product is None:
        raise HTTPException(404, detail="product not found")
    if job_id:
        job = db.scalar(
            select(ImageGenerationJob).where(
                ImageGenerationJob.id == job_id,
                ImageGenerationJob.product_id == product_id,
                ImageGenerationJob.tenant_id == tenant_id,
            )
        )
        if job is None:
            raise HTTPException(404, detail="image job not found")
    if not content:
        raise HTTPException(422, detail="empty file")
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(413, detail="reference image must be <= 50MB")
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(415, detail="only image uploads are accepted")

    try:
        uri = save_reference_upload(
            product_id=product_id,
            job_id=job_id,
            filename=file.filename or "reference-image",
            content=content,
        )
    except ImageStudioError as exc:
        raise HTTPException(500, detail=str(exc)) from exc
    row = ImageReferenceAsset(
        tenant_id=tenant_id,
        product_id=product_id,
        job_id=job_id,
        asset_role=asset_role,
        component_code=component_code,
        asset_uri=uri,
        original_filename=file.filename,
        mime_type=file.content_type,
        internal_reference_only=internal_reference_only,
        lock_level=lock_level,
        sort_order=sort_order,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "asset_role": row.asset_role,
        "component_code": row.component_code,
        "asset_uri": row.asset_uri,
        "lock_level": row.lock_level,
        "internal_reference_only": row.internal_reference_only,
    }


@router.post("/jobs/{job_id}/references/upload")
async def upload_job_reference(
    job_id: str,
    product_id: str = Form(...),
    asset_role: str = Form("PRODUCT_REFERENCE"),
    component_code: str | None = Form(default=None),
    lock_level: str = Form("hard_lock"),
    internal_reference_only: bool = Form(False),
    sort_order: int = Form(0),
    file: UploadFile = File(...),
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    content = await file.read()
    return _upload_reference(
        db=db,
        tenant_id=tenant_id,
        product_id=product_id,
        job_id=job_id,
        file=file,
        content=content,
        asset_role=asset_role,
        component_code=component_code,
        lock_level=lock_level,
        internal_reference_only=internal_reference_only,
        sort_order=sort_order,
    )


@router.post("/products/{product_id}/references/upload")
async def upload_master_reference(
    product_id: str,
    asset_role: str = Form("PRODUCT_REFERENCE"),
    component_code: str | None = Form(default=None),
    lock_level: str = Form("hard_lock"),
    internal_reference_only: bool = Form(False),
    sort_order: int = Form(0),
    file: UploadFile = File(...),
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    content = await file.read()
    return _upload_reference(
        db=db,
        tenant_id=tenant_id,
        product_id=product_id,
        job_id=None,
        file=file,
        content=content,
        asset_role=asset_role,
        component_code=component_code,
        lock_level=lock_level,
        internal_reference_only=internal_reference_only,
        sort_order=sort_order,
    )


@router.post("/references/register")
def register_reference(
    body: ReferenceRegisterBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    if body.asset_role not in REFERENCE_ROLES or body.lock_level not in LOCK_LEVELS:
        raise HTTPException(422, detail="unsupported reference metadata")
    product = db.scalar(
        select(Product).where(Product.id == body.product_id, Product.tenant_id == tenant_id)
    )
    if product is None:
        raise HTTPException(404, detail="product not found")
    row = ImageReferenceAsset(
        tenant_id=tenant_id,
        product_id=body.product_id,
        job_id=body.job_id,
        asset_role=body.asset_role,
        component_code=body.component_code,
        asset_uri=body.asset_uri,
        internal_reference_only=body.internal_reference_only,
        lock_level=body.lock_level,
        sort_order=body.sort_order,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "asset_uri": row.asset_uri, "asset_role": row.asset_role}


@router.post("/jobs/{job_id}/prepare")
def prepare_image_job(
    job_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    job = db.scalar(
        select(ImageGenerationJob).where(
            ImageGenerationJob.id == job_id,
            ImageGenerationJob.tenant_id == tenant_id,
        )
    )
    if job is None:
        raise HTTPException(404, detail="image job not found")
    try:
        prepare_job(db, job)
    except ImageStudioError as exc:
        raise HTTPException(409, detail=str(exc)) from exc
    return _job_payload(db, job)


@router.post("/jobs/{job_id}/preview")
def generate_preview(
    job_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    job = db.scalar(
        select(ImageGenerationJob).where(
            ImageGenerationJob.id == job_id,
            ImageGenerationJob.tenant_id == tenant_id,
        )
    )
    if job is None:
        raise HTTPException(404, detail="image job not found")
    try:
        asset = generate_stage(db, job, "preview")
    except ProviderNotConfigured as exc:
        raise HTTPException(503, detail=str(exc)) from exc
    except ImageStudioError as exc:
        raise HTTPException(409, detail=str(exc)) from exc
    return {"job": _job_payload(db, job), "asset_id": asset.id}


@router.post("/jobs/{job_id}/revision")
def request_revision(
    job_id: str,
    body: RevisionBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    job = db.scalar(
        select(ImageGenerationJob).where(
            ImageGenerationJob.id == job_id,
            ImageGenerationJob.tenant_id == tenant_id,
        )
    )
    if job is None:
        raise HTTPException(404, detail="image job not found")
    # Preserve the original brief. Revisions are append-only review events and are
    # merged into the provider prompt at generation time.
    job.status = "revision_requested"
    db.add(
        ImageReviewEvent(
            tenant_id=tenant_id,
            job_id=job.id,
            action="request_revision",
            comment=body.instruction,
            created_by=body.created_by,
        )
    )
    db.commit()
    return _job_payload(db, job)


@router.post("/jobs/{job_id}/finalize", status_code=status.HTTP_202_ACCEPTED)
def generate_final(
    job_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    # FINAL generation is intentionally asynchronous.  The API only queues the
    # work in Postgres and returns immediately; the dedicated image_worker claims
    # the row with SKIP LOCKED and performs the expensive provider call.
    job = db.scalar(
        select(ImageGenerationJob)
        .where(
            ImageGenerationJob.id == job_id,
            ImageGenerationJob.tenant_id == tenant_id,
        )
        .with_for_update()
    )
    if job is None:
        raise HTTPException(404, detail="image job not found")

    existing_final = db.scalar(
        select(ImageGeneratedAsset)
        .where(
            ImageGeneratedAsset.job_id == job.id,
            ImageGeneratedAsset.asset_stage == "final",
        )
        .order_by(ImageGeneratedAsset.version_no.desc())
    )
    if existing_final is not None:
        db.commit()
        return {
            "job": _job_payload(db, job),
            "asset_id": existing_final.id,
            "queued": False,
            "already_exists": True,
        }

    if job.status in {"final_queued", "final_generating"}:
        db.commit()
        return {"job": _job_payload(db, job), "asset_id": None, "queued": True}

    approved_preview = db.scalar(
        select(ImageGeneratedAsset)
        .where(
            ImageGeneratedAsset.job_id == job.id,
            ImageGeneratedAsset.asset_stage == "preview",
            ImageGeneratedAsset.status == "approved",
        )
        .order_by(ImageGeneratedAsset.version_no.desc())
    )
    if approved_preview is None:
        raise HTTPException(409, detail="FINAL 생성 전 승인된 P1 Preview가 필요합니다.")
    if job.final_count >= settings.image_max_final_generations:
        raise HTTPException(409, detail="이 작업의 FINAL 생성 한도에 도달했습니다. 추가 고비용 생성을 중단했습니다.")

    job.status = "final_queued"
    db.commit()
    db.refresh(job)
    return {"job": _job_payload(db, job), "asset_id": None, "queued": True}


@router.post("/assets/{asset_id}/qa")
def qa_asset(
    asset_id: str,
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
        raise HTTPException(404, detail="image asset not found")
    job = db.scalar(select(ImageGenerationJob).where(ImageGenerationJob.id == asset.job_id))
    rows = run_image_qa(db, job, asset)
    return [
        {"check_code": x.check_code, "status": x.status, "severity": x.severity, "message": x.message}
        for x in rows
    ]


@router.post("/assets/{asset_id}/approve")
def approve_image_asset(
    asset_id: str,
    body: ApprovalBody,
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
        raise HTTPException(404, detail="image asset not found")
    job = db.scalar(select(ImageGenerationJob).where(ImageGenerationJob.id == asset.job_id))
    try:
        approve_asset(
            db,
            job=job,
            asset=asset,
            approved_by=body.approved_by,
            acknowledge_review=body.acknowledge_review,
        )
    except ImageStudioError as exc:
        raise HTTPException(409, detail=str(exc)) from exc
    return _job_payload(db, job)


@router.get("/assets/{asset_id}/content")
def image_asset_content(
    asset_id: str,
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
        raise HTTPException(404, detail="image asset not found")
    try:
        path = resolve_media_uri(asset.asset_uri)
    except ImageStudioError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    return FileResponse(path, media_type="image/png", filename=asset.filename or path.name)
