from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dashboard_session import require_business_auth
from app.db.models import DetailPageExport, DetailPageJob
from app.db.session import SessionLocal
from app.services.canva_controlled_export import build_controlled_canva_contract
from app.services.detail_page_studio import current_version, export_package


router = APIRouter(
    prefix="/api/v1/detail-page-canva",
    tags=["detail-page-canva"],
    dependencies=[Depends(require_business_auth)],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _job_or_404(db: Session, *, tenant_id: str, job_id: str) -> DetailPageJob:
    row = db.scalar(
        select(DetailPageJob).where(
            DetailPageJob.id == job_id,
            DetailPageJob.tenant_id == tenant_id,
        )
    )
    if row is None:
        raise HTTPException(404, detail="detail-page job not found")
    return row


@router.post("/jobs/{job_id}/export")
def controlled_canva_export(
    job_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    """Create an approved export and attach the deterministic Canva execution contract."""
    job = _job_or_404(db, tenant_id=tenant_id, job_id=job_id)
    version = current_version(db, job)
    if version is None:
        raise HTTPException(409, detail="detail-page version not prepared")
    try:
        row = export_package(db, job=job, version=version)
    except ValueError as exc:
        raise HTTPException(409, detail=str(exc)) from exc

    payload = dict(row.payload_json or {})
    payload["canva_controlled_contract"] = build_controlled_canva_contract(
        export_payload=payload
    )
    payload["schema_version"] = "detail-page-export.v2"
    row.payload_json = payload
    row.export_type = "canva_controlled_package"
    db.commit()
    db.refresh(row)
    return {
        "export_id": row.id,
        "status": row.status,
        "export_type": row.export_type,
        "payload": row.payload_json,
    }


@router.get("/exports/{export_id}")
def get_controlled_canva_export(
    export_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    row = db.scalar(
        select(DetailPageExport).where(
            DetailPageExport.id == export_id,
            DetailPageExport.tenant_id == tenant_id,
        )
    )
    if row is None:
        raise HTTPException(404, detail="detail-page export not found")
    payload = dict(row.payload_json or {})
    if "canva_controlled_contract" not in payload:
        payload["canva_controlled_contract"] = build_controlled_canva_contract(
            export_payload=payload
        )
    return {
        "export_id": row.id,
        "status": row.status,
        "export_type": row.export_type,
        "payload": payload,
    }
