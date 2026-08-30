from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dashboard_session import require_business_auth
from app.db.models import (
    BrandStyleSheet,
    BusinessWorkspace,
    DetailPageExport,
    DetailPageJob,
    DetailPageQAResult,
    DetailPageSection,
    DetailPageTemplate,
    DetailPageVersion,
    Product,
    ProductRelation,
    ReviewSource,
)
from app.db.session import SessionLocal
from app.services.detail_page_studio import (
    RELATION_TYPES,
    TEMPLATE_DEFINITIONS,
    apply_natural_language_revision,
    approve_version,
    clone_version,
    create_prepared_version,
    current_version,
    ensure_defaults,
    export_package,
    qa_summary,
    reorder_sections,
    run_qa,
    update_copy_section,
    version_sections,
)


router = APIRouter(
    prefix="/api/v1/detail-pages",
    tags=["detail-pages"],
    dependencies=[Depends(require_business_auth)],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _job_or_404(db: Session, tenant_id: str, job_id: str) -> DetailPageJob:
    row = db.scalar(
        select(DetailPageJob).where(
            DetailPageJob.id == job_id,
            DetailPageJob.tenant_id == tenant_id,
        )
    )
    if row is None:
        raise HTTPException(404, detail="detail-page job not found")
    return row


def _current_or_409(db: Session, job: DetailPageJob) -> DetailPageVersion:
    row = current_version(db, job)
    if row is None:
        raise HTTPException(409, detail="prepare P0 first")
    return row


def _section_payload(row: DetailPageSection) -> dict:
    return {
        "id": row.id,
        "section_type": row.section_type,
        "sort_order": row.sort_order,
        "is_required": row.is_required,
        "is_enabled": row.is_enabled,
        "layout_variant": row.layout_variant,
        "source_type": row.source_type,
        "content": row.content_json,
        "image_asset_id": row.image_asset_id,
        "image_content_url": (
            f"/api/v1/images/assets/{row.image_asset_id}/content?tenant_id={row.tenant_id}"
            if row.image_asset_id
            else (
                f"/api/v1/product-image-facts/images/{(row.content_json or {}).get('product_image_fact_id')}/content?tenant_id={row.tenant_id}"
                if (row.content_json or {}).get("product_image_fact_id")
                else None
            )
        ),
        "qa_status": row.qa_status,
    }


def _version_payload(db: Session, version: DetailPageVersion | None) -> dict | None:
    if version is None:
        return None
    template = db.scalar(select(DetailPageTemplate).where(DetailPageTemplate.id == version.template_id))
    brand = db.scalar(select(BrandStyleSheet).where(BrandStyleSheet.id == version.brand_style_sheet_id))
    return {
        "id": version.id,
        "version_no": version.version_no,
        "status": version.status,
        "template": None if template is None else {
            "id": template.id,
            "code": template.code,
            "name": template.name,
            "description": template.description,
            "layout_rules": template.layout_rules,
            "canva_brand_template_id": template.canva_brand_template_id,
        },
        "brand_style": None if brand is None else {
            "id": brand.id,
            "name": brand.name,
            "primary_color": brand.primary_color,
            "secondary_color": brand.secondary_color,
            "accent_color": brand.accent_color,
            "background_color": brand.background_color,
            "surface_color": brand.surface_color,
            "text_color": brand.text_color,
            "muted_text_color": brand.muted_text_color,
            "color_lock_enabled": brand.color_lock_enabled,
            "version": brand.version,
        },
        "visual_style": version.visual_style,
        "page_strategy": version.page_strategy,
        "change_summary": version.change_summary,
        "fact_snapshot_hash": version.fact_snapshot_hash,
        "sections": [_section_payload(s) for s in version_sections(db, version.id)],
    }


def _job_payload(db: Session, job: DetailPageJob) -> dict:
    product = db.scalar(select(Product).where(Product.id == job.product_id))
    current = current_version(db, job)
    versions = db.scalars(
        select(DetailPageVersion)
        .where(DetailPageVersion.job_id == job.id)
        .order_by(DetailPageVersion.version_no.desc())
    ).all()
    qa_rows = []
    if current:
        qa_rows = db.scalars(
            select(DetailPageQAResult).where(
                DetailPageQAResult.job_id == job.id,
                DetailPageQAResult.version_no == current.version_no,
            )
        ).all()
    return {
        "id": job.id,
        "workspace_id": job.workspace_id,
        "product_id": job.product_id,
        "product_name": product.name if product else None,
        "channel": job.channel,
        "page_length": job.page_length,
        "status": job.status,
        "current_version_no": job.current_version_no,
        "approved_version_no": job.approved_version_no,
        "current_version": _version_payload(db, current),
        "versions": [
            {
                "id": v.id,
                "version_no": v.version_no,
                "status": v.status,
                "change_summary": v.change_summary,
                "created_at": v.created_at.isoformat(),
            }
            for v in versions
        ],
        "qa": {
            "summary": qa_summary(qa_rows) if qa_rows else "NOT_RUN",
            "items": [
                {
                    "id": q.id,
                    "section_id": q.section_id,
                    "check_code": q.check_code,
                    "status": q.status,
                    "severity": q.severity,
                    "message": q.message,
                    "suggested_fix": q.suggested_fix,
                    "resolved": q.resolved,
                }
                for q in qa_rows
            ],
        },
    }


class JobCreateBody(BaseModel):
    workspace_id: str
    product_id: str
    channel: str = "naver-smartstore"
    page_length: Literal["long", "short"] = "long"
    generation_mode: Literal["automatic", "manual"] = "manual"
    created_by: str | None = None


class PrepareBody(BaseModel):
    template_code: str = "A_PRACTICAL_TRUST"
    brand_style_sheet_id: str | None = None
    visual_style: str = "natural"
    page_strategy: str = "review_first"


class TemplateChangeBody(BaseModel):
    template_code: str


class BrandSelectionBody(BaseModel):
    brand_style_sheet_id: str


class VersionStyleBody(BaseModel):
    visual_style: str | None = None
    page_strategy: str | None = None


class ReorderBody(BaseModel):
    section_ids: list[str] = Field(min_length=1)


class SectionUpdateBody(BaseModel):
    headline: str | None = None
    body: str | None = None
    layout_variant: str | None = None
    is_enabled: bool | None = None


class RevisionBody(BaseModel):
    instruction: str = Field(min_length=1, max_length=5000)


class ApproveBody(BaseModel):
    acknowledge_review: bool = False


class BrandCreateBody(BaseModel):
    workspace_id: str
    name: str
    primary_color: str = "#1F6B4F"
    secondary_color: str = "#A7C4B5"
    accent_color: str = "#E7B65A"
    background_color: str = "#FFFFFF"
    surface_color: str = "#F5F7F6"
    text_color: str = "#17211C"
    muted_text_color: str = "#66756D"
    color_lock_enabled: bool = True


class BrandUpdateBody(BaseModel):
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    background_color: str | None = None
    surface_color: str | None = None
    text_color: str | None = None
    muted_text_color: str | None = None
    color_lock_enabled: bool | None = None


class RelationBody(BaseModel):
    source_product_id: str
    target_product_id: str | None = None
    relation_type: str
    display_name: str | None = None
    target_url: str | None = None
    image_asset_uri: str | None = None
    notes: str | None = None
    sort_order: int = 0


class ReviewBody(BaseModel):
    product_id: str
    channel: str
    external_review_id: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    review_text: str = Field(min_length=1, max_length=10000)
    photo_asset_uri: str | None = None
    reviewed_at: datetime | None = None
    is_verified: bool = True


@router.post("/jobs")
def create_job(
    body: JobCreateBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
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
    row = DetailPageJob(
        tenant_id=tenant_id,
        workspace_id=body.workspace_id,
        product_id=body.product_id,
        channel=body.channel,
        page_length=body.page_length,
        generation_mode=body.generation_mode,
        created_by=body.created_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _job_payload(db, row)


@router.get("/jobs")
def list_jobs(
    tenant_id: str = Query(..., min_length=1, max_length=128),
    product_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = select(DetailPageJob).where(DetailPageJob.tenant_id == tenant_id)
    if product_id:
        stmt = stmt.where(DetailPageJob.product_id == product_id)
    rows = db.scalars(stmt.order_by(DetailPageJob.created_at.desc())).all()
    return [_job_payload(db, row) for row in rows]


@router.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    return _job_payload(db, _job_or_404(db, tenant_id, job_id))


@router.post("/jobs/{job_id}/prepare")
def prepare_job(
    job_id: str,
    body: PrepareBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    job = _job_or_404(db, tenant_id, job_id)
    brand, templates = ensure_defaults(db, tenant_id=tenant_id, workspace_id=job.workspace_id)
    template = next((t for t in templates if t.code == body.template_code), None)
    if template is None:
        template = db.scalar(
            select(DetailPageTemplate).where(
                DetailPageTemplate.tenant_id == tenant_id,
                DetailPageTemplate.code == body.template_code,
            )
        )
    if template is None:
        raise HTTPException(404, detail="template not found")
    if job.generation_mode == "automatic" and template.status not in {
        "published",
        "active",
    }:
        raise HTTPException(
            409,
            detail="자동생성에는 템플릿 설정에서 확정·게시한 템플릿이 필요합니다.",
        )
    if body.brand_style_sheet_id:
        brand = db.scalar(
            select(BrandStyleSheet).where(
                BrandStyleSheet.id == body.brand_style_sheet_id,
                BrandStyleSheet.tenant_id == tenant_id,
                BrandStyleSheet.workspace_id == job.workspace_id,
            )
        )
        if brand is None:
            raise HTTPException(404, detail="brand style not found")
    create_prepared_version(
        db,
        job=job,
        template=template,
        brand=brand,
        visual_style=body.visual_style,
        page_strategy=body.page_strategy,
        change_summary="P0 상세페이지 기본 스토리보드 생성",
    )
    db.commit()
    db.refresh(job)
    return _job_payload(db, job)


@router.post("/jobs/{job_id}/template")
def change_template(
    job_id: str,
    body: TemplateChangeBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    job = _job_or_404(db, tenant_id, job_id)
    source = _current_or_409(db, job)
    template = db.scalar(
        select(DetailPageTemplate).where(
            DetailPageTemplate.tenant_id == tenant_id,
            DetailPageTemplate.code == body.template_code,
        )
    )
    if template is None:
        ensure_defaults(db, tenant_id=tenant_id, workspace_id=job.workspace_id)
        template = db.scalar(
            select(DetailPageTemplate).where(
                DetailPageTemplate.tenant_id == tenant_id,
                DetailPageTemplate.code == body.template_code,
            )
        )
    if template is None:
        raise HTTPException(404, detail="template not found")
    clone_version(
        db,
        job=job,
        source=source,
        template_id=template.id,
        change_summary=f"템플릿 변경: {template.name}",
    )
    db.commit()
    return _job_payload(db, job)


@router.post("/jobs/{job_id}/brand-style")
def change_brand_style(
    job_id: str,
    body: BrandSelectionBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    job = _job_or_404(db, tenant_id, job_id)
    source = _current_or_409(db, job)
    brand = db.scalar(
        select(BrandStyleSheet).where(
            BrandStyleSheet.id == body.brand_style_sheet_id,
            BrandStyleSheet.tenant_id == tenant_id,
            BrandStyleSheet.workspace_id == job.workspace_id,
        )
    )
    if brand is None:
        raise HTTPException(404, detail="brand style not found")
    clone_version(
        db,
        job=job,
        source=source,
        brand_style_sheet_id=brand.id,
        change_summary=f"브랜드 스타일 변경: {brand.name}",
    )
    db.commit()
    return _job_payload(db, job)


@router.post("/jobs/{job_id}/style")
def change_version_style(
    job_id: str,
    body: VersionStyleBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    job = _job_or_404(db, tenant_id, job_id)
    source = _current_or_409(db, job)
    clone_version(
        db,
        job=job,
        source=source,
        visual_style=body.visual_style,
        page_strategy=body.page_strategy,
        change_summary="Visual Style / 판매전략 변경",
    )
    db.commit()
    return _job_payload(db, job)


@router.post("/jobs/{job_id}/sections/reorder")
def reorder(
    job_id: str,
    body: ReorderBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    job = _job_or_404(db, tenant_id, job_id)
    source = _current_or_409(db, job)
    new_version = clone_version(
        db, job=job, source=source, change_summary="섹션 순서 변경"
    )
    new_rows = version_sections(db, new_version.id)
    source_rows = version_sections(db, source.id)
    if len(body.section_ids) != len(source_rows):
        raise HTTPException(422, detail="section_ids must include every section")
    source_order_types = []
    source_map = {r.id: r.section_type for r in source_rows}
    for source_id in body.section_ids:
        if source_id not in source_map:
            raise HTTPException(422, detail="section id does not belong to current version")
        source_order_types.append(source_map[source_id])
    by_type = {r.section_type: r for r in new_rows}
    try:
        reorder_sections(db, version=new_version, ordered_ids=[by_type[t].id for t in source_order_types])
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    db.commit()
    return _job_payload(db, job)


@router.put("/jobs/{job_id}/sections/{section_id}")
def update_section(
    job_id: str,
    section_id: str,
    body: SectionUpdateBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    job = _job_or_404(db, tenant_id, job_id)
    source = _current_or_409(db, job)
    source_section = db.scalar(
        select(DetailPageSection).where(
            DetailPageSection.id == section_id,
            DetailPageSection.version_id == source.id,
            DetailPageSection.tenant_id == tenant_id,
        )
    )
    if source_section is None:
        raise HTTPException(404, detail="section not found")
    new_version = clone_version(
        db,
        job=job,
        source=source,
        change_summary=f"{source_section.section_type} 섹션 수정",
    )
    target = db.scalar(
        select(DetailPageSection).where(
            DetailPageSection.version_id == new_version.id,
            DetailPageSection.section_type == source_section.section_type,
        )
    )
    try:
        if body.headline is not None or body.body is not None:
            update_copy_section(target, headline=body.headline, body=body.body)
    except ValueError as exc:
        raise HTTPException(409, detail=str(exc)) from exc
    if body.layout_variant is not None:
        target.layout_variant = body.layout_variant
    if body.is_enabled is not None:
        if target.is_required and body.is_enabled is False:
            raise HTTPException(409, detail="required section cannot be disabled")
        target.is_enabled = body.is_enabled
    db.commit()
    return _job_payload(db, job)


@router.post("/jobs/{job_id}/revision")
def natural_revision(
    job_id: str,
    body: RevisionBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    job = _job_or_404(db, tenant_id, job_id)
    source = _current_or_409(db, job)
    new_version = clone_version(
        db,
        job=job,
        source=source,
        change_summary=f"자연어 수정: {body.instruction[:180]}",
    )
    result = apply_natural_language_revision(db, version=new_version, instruction=body.instruction)
    if not result.get("applied"):
        # Do not leave a useless version behind when the request was not safely applied.
        db.query(DetailPageVersion).filter(DetailPageVersion.id == new_version.id).delete()
        job.current_version_no = source.version_no
        job.status = source.status
        db.commit()
        return {"applied": False, "revision": result, "job": _job_payload(db, job)}
    db.commit()
    return {"applied": True, "revision": result, "job": _job_payload(db, job)}


@router.post("/jobs/{job_id}/qa")
def qa(
    job_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    job = _job_or_404(db, tenant_id, job_id)
    version = _current_or_409(db, job)
    rows = run_qa(db, job=job, version=version)
    db.commit()
    return {
        "summary": qa_summary(rows),
        "job": _job_payload(db, job),
    }


@router.post("/jobs/{job_id}/approve")
def approve(
    job_id: str,
    body: ApproveBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    job = _job_or_404(db, tenant_id, job_id)
    version = _current_or_409(db, job)
    try:
        summary = approve_version(
            db,
            job=job,
            version=version,
            acknowledge_review=body.acknowledge_review,
        )
    except ValueError as exc:
        raise HTTPException(409, detail=str(exc)) from exc
    db.commit()
    return {"approved": True, "qa_summary": summary, "job": _job_payload(db, job)}


@router.post("/jobs/{job_id}/export/canva")
def canva_export(
    job_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    job = _job_or_404(db, tenant_id, job_id)
    version = _current_or_409(db, job)
    try:
        row = export_package(db, job=job, version=version)
    except ValueError as exc:
        raise HTTPException(409, detail=str(exc)) from exc
    db.commit()
    db.refresh(row)
    return {
        "export_id": row.id,
        "status": row.status,
        "export_type": row.export_type,
        "payload": row.payload_json,
    }


@router.get("/templates")
def list_templates(
    workspace_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    ensure_defaults(db, tenant_id=tenant_id, workspace_id=workspace_id)
    db.commit()
    rows = db.scalars(
        select(DetailPageTemplate).where(
            DetailPageTemplate.tenant_id == tenant_id,
            DetailPageTemplate.status == "active",
        )
    ).all()
    return [
        {
            "id": r.id,
            "code": r.code,
            "name": r.name,
            "description": r.description,
            "layout_rules": r.layout_rules,
            "canva_brand_template_id": r.canva_brand_template_id,
        }
        for r in rows
    ]


@router.get("/brand-styles")
def list_brand_styles(
    workspace_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    ensure_defaults(db, tenant_id=tenant_id, workspace_id=workspace_id)
    db.commit()
    rows = db.scalars(
        select(BrandStyleSheet).where(
            BrandStyleSheet.tenant_id == tenant_id,
            BrandStyleSheet.workspace_id == workspace_id,
        )
    ).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "primary_color": r.primary_color,
            "secondary_color": r.secondary_color,
            "accent_color": r.accent_color,
            "background_color": r.background_color,
            "surface_color": r.surface_color,
            "text_color": r.text_color,
            "muted_text_color": r.muted_text_color,
            "color_lock_enabled": r.color_lock_enabled,
            "version": r.version,
        }
        for r in rows
    ]


@router.post("/brand-styles")
def create_brand_style(
    body: BrandCreateBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    workspace = db.scalar(
        select(BusinessWorkspace).where(
            BusinessWorkspace.id == body.workspace_id,
            BusinessWorkspace.tenant_id == tenant_id,
        )
    )
    if workspace is None:
        raise HTTPException(404, detail="workspace not found")
    row = BrandStyleSheet(tenant_id=tenant_id, **body.model_dump())
    db.add(row)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(409, detail="brand style already exists or is invalid") from exc
    db.refresh(row)
    return {"id": row.id, "name": row.name, "version": row.version}


@router.patch("/brand-styles/{style_id}")
def update_brand_style(
    style_id: str,
    body: BrandUpdateBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    row = db.scalar(
        select(BrandStyleSheet).where(
            BrandStyleSheet.id == style_id,
            BrandStyleSheet.tenant_id == tenant_id,
        )
    )
    if row is None:
        raise HTTPException(404, detail="brand style not found")
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(row, key, value)
    row.version += 1
    db.commit()
    return {"id": row.id, "name": row.name, "version": row.version}


@router.post("/relations")
def create_relation(
    body: RelationBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    if body.relation_type not in RELATION_TYPES:
        raise HTTPException(422, detail="unsupported relation_type")
    source = db.scalar(
        select(Product).where(Product.id == body.source_product_id, Product.tenant_id == tenant_id)
    )
    if source is None:
        raise HTTPException(404, detail="source product not found")
    if body.target_product_id:
        target = db.scalar(
            select(Product).where(Product.id == body.target_product_id, Product.tenant_id == tenant_id)
        )
        if target is None:
            raise HTTPException(404, detail="target product not found")
    if not body.target_product_id and not body.display_name:
        raise HTTPException(422, detail="external relation requires display_name")
    row = ProductRelation(tenant_id=tenant_id, **body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "relation_type": row.relation_type, "display_name": row.display_name}


@router.get("/relations")
def list_relations(
    source_product_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(ProductRelation)
        .where(
            ProductRelation.tenant_id == tenant_id,
            ProductRelation.source_product_id == source_product_id,
            ProductRelation.is_active.is_(True),
        )
        .order_by(ProductRelation.relation_type, ProductRelation.sort_order)
    ).all()
    return [
        {
            "id": r.id,
            "relation_type": r.relation_type,
            "target_product_id": r.target_product_id,
            "display_name": r.display_name,
            "target_url": r.target_url,
            "image_asset_uri": r.image_asset_uri,
            "notes": r.notes,
            "sort_order": r.sort_order,
        }
        for r in rows
    ]


@router.post("/reviews")
def create_review(
    body: ReviewBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    product = db.scalar(
        select(Product).where(Product.id == body.product_id, Product.tenant_id == tenant_id)
    )
    if product is None:
        raise HTTPException(404, detail="product not found")
    row = ReviewSource(tenant_id=tenant_id, **body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "verified": row.is_verified}


@router.get("/reviews")
def list_reviews(
    product_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(ReviewSource)
        .where(ReviewSource.tenant_id == tenant_id, ReviewSource.product_id == product_id)
        .order_by(ReviewSource.created_at.desc())
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
            "is_verified": r.is_verified,
        }
        for r in rows
    ]
