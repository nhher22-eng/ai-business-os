from __future__ import annotations

from copy import deepcopy
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dashboard_session import require_business_auth
from app.db.detail_page_content_basis import DetailPageContentBasis
from app.db.models import DetailPageJob, DetailPageSection, Product
from app.db.product_registration import ProductRegistrationProfile
from app.db.session import SessionLocal
from app.services.detail_page_studio import clone_version, current_version, version_sections


router = APIRouter(
    prefix="/api/v1/detail-page-content-basis",
    tags=["detail-page-content-basis"],
    dependencies=[Depends(require_business_auth)],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ContentBasisBody(BaseModel):
    category: str | None = None
    usage: list[str] = []
    features: list[str] = []
    selling_points: list[str] = []
    target_customer: list[str] = []
    content_direction: str | None = None
    sync_product_master: bool = False


def _clean_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _clean_list(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values or []:
        text = _clean_text(value)
        if text and text not in result:
            result.append(text)
    return result


def _normalized_basis(body: ContentBasisBody) -> dict:
    return {
        "category": _clean_text(body.category),
        "usage": _clean_list(body.usage),
        "features": _clean_list(body.features),
        "selling_points": _clean_list(body.selling_points),
        "target_customer": _clean_list(body.target_customer),
        "content_direction": _clean_text(body.content_direction),
    }


def _master_basis(db: Session, *, tenant_id: str, product_id: str) -> dict:
    profile = db.scalar(
        select(ProductRegistrationProfile).where(
            ProductRegistrationProfile.tenant_id == tenant_id,
            ProductRegistrationProfile.product_id == product_id,
        )
    )
    operating = (profile.operating_info or {}) if profile else {}
    marketing = (profile.marketing_info or {}) if profile else {}
    return {
        "category": operating.get("category"),
        "usage": operating.get("usage") or [],
        "features": marketing.get("features") or [],
        "selling_points": marketing.get("selling_points") or [],
        "target_customer": marketing.get("target_customer") or [],
        "content_direction": marketing.get("content_direction"),
    }


def _apply_basis_to_sections(db: Session, *, version_id: str, basis: dict) -> None:
    """Keep the page-local basis visible to the current page without changing FACT."""
    rows = version_sections(db, version_id)
    by_type = {row.section_type: row for row in rows}

    hero = by_type.get("HERO")
    if hero:
        content = deepcopy(hero.content_json or {})
        content["content_basis"] = {
            "category": basis.get("category"),
            "selling_points": basis.get("selling_points") or [],
            "target_customer": basis.get("target_customer") or [],
            "content_direction": basis.get("content_direction"),
        }
        hero.content_json = content

    problem = by_type.get("PROBLEM")
    if problem:
        content = deepcopy(problem.content_json or {})
        content["items"] = basis.get("usage") or []
        content["copy_status"] = "page_override" if content["items"] else "missing"
        problem.content_json = content

    feature = by_type.get("FEATURE")
    if feature:
        content = deepcopy(feature.content_json or {})
        content["usage"] = basis.get("usage") or []
        content["features"] = basis.get("features") or []
        content["selling_points"] = basis.get("selling_points") or []
        feature.content_json = content


def _job_or_404(db: Session, *, tenant_id: str, job_id: str) -> DetailPageJob:
    job = db.scalar(
        select(DetailPageJob).where(
            DetailPageJob.id == job_id,
            DetailPageJob.tenant_id == tenant_id,
        )
    )
    if job is None:
        raise HTTPException(404, detail="detail-page job not found")
    return job


def _payload(db: Session, *, job: DetailPageJob) -> dict:
    version = current_version(db, job)
    if version is None:
        return {
            "job_id": job.id,
            "version_id": None,
            "source": "product_master",
            "basis": _master_basis(db, tenant_id=job.tenant_id, product_id=job.product_id),
            "product_master_basis": _master_basis(
                db, tenant_id=job.tenant_id, product_id=job.product_id
            ),
        }
    row = db.scalar(
        select(DetailPageContentBasis).where(
            DetailPageContentBasis.tenant_id == job.tenant_id,
            DetailPageContentBasis.version_id == version.id,
        )
    )
    master = _master_basis(db, tenant_id=job.tenant_id, product_id=job.product_id)
    return {
        "job_id": job.id,
        "version_id": version.id,
        "version_no": version.version_no,
        "source": row.source if row else "product_master",
        "basis": (row.basis or {}) if row else master,
        "product_master_basis": master,
    }


@router.get("/jobs/{job_id}")
def get_content_basis(
    job_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    job = _job_or_404(db, tenant_id=tenant_id, job_id=job_id)
    return _payload(db, job=job)


@router.post("/jobs/{job_id}")
def save_content_basis(
    job_id: str,
    body: ContentBasisBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    job = _job_or_404(db, tenant_id=tenant_id, job_id=job_id)
    source = current_version(db, job)
    if source is None:
        raise HTTPException(409, detail="prepare detail page first")

    basis = _normalized_basis(body)
    new_version = clone_version(
        db,
        job=job,
        source=source,
        change_summary="페이지 콘텐츠 기준정보 수정",
    )
    row = DetailPageContentBasis(
        tenant_id=tenant_id,
        job_id=job.id,
        version_id=new_version.id,
        basis=basis,
        source="page_override",
    )
    db.add(row)
    _apply_basis_to_sections(db, version_id=new_version.id, basis=basis)

    if body.sync_product_master:
        profile = db.scalar(
            select(ProductRegistrationProfile).where(
                ProductRegistrationProfile.tenant_id == tenant_id,
                ProductRegistrationProfile.product_id == job.product_id,
            )
        )
        if profile is None:
            raise HTTPException(409, detail="product registration profile not found")
        profile.operating_info = {
            "category": basis.get("category"),
            "usage": basis.get("usage") or [],
        }
        profile.marketing_info = {
            "features": basis.get("features") or [],
            "selling_points": basis.get("selling_points") or [],
            "target_customer": basis.get("target_customer") or [],
            "content_direction": basis.get("content_direction"),
        }
        row.source = "page_override_and_master_sync"

    db.commit()
    db.refresh(job)
    return {
        "saved": True,
        "synced_product_master": bool(body.sync_product_master),
        "basis": basis,
        "version_id": new_version.id,
        "version_no": new_version.version_no,
    }
