from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dashboard_session import require_business_auth
from app.db.models import Product
from app.db.product_image_fact import ProductImageFact
from app.db.session import SessionLocal
from app.services.image_studio import ImageStudioError, resolve_media_uri
from app.services.product_image_fact import (
    ProductImageFactError,
    SLOT_TYPES,
    confirm_image_fact,
    create_upload_row,
    delete_unconfirmed_row,
    process_row,
    readiness,
    set_slot_and_process,
    slot_definitions,
)


router = APIRouter(
    prefix="/api/v1/product-image-facts",
    tags=["product-image-facts"],
    dependencies=[Depends(require_business_auth)],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ImageFactEditBody(BaseModel):
    slot_type: str
    slot_index: int | None = Field(default=None, ge=1)


class ConfirmBody(BaseModel):
    confirmed_by: str | None = "dashboard-user"


def _product(db: Session, *, tenant_id: str, product_id: str) -> Product:
    row = db.scalar(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    if row is None:
        raise HTTPException(404, detail="product not found")
    return row


def _row(db: Session, *, tenant_id: str, image_fact_id: str) -> ProductImageFact:
    row = db.scalar(
        select(ProductImageFact).where(
            ProductImageFact.id == image_fact_id,
            ProductImageFact.tenant_id == tenant_id,
        )
    )
    if row is None:
        raise HTTPException(404, detail="product image FACT not found")
    return row


def _payload(row: ProductImageFact) -> dict:
    return {
        "id": row.id,
        "product_id": row.product_id,
        "slot_type": row.slot_type,
        "slot_index": row.slot_index,
        "is_required": row.is_required,
        "is_primary": row.is_primary,
        "status": row.status,
        "source_kind": row.source_kind,
        "classification_source": row.classification_source,
        "classification_confidence": row.classification_confidence,
        "background_removed": row.background_removed,
        "keep_background": row.keep_background,
        "raw_retention_policy": row.raw_retention_policy,
        "raw_available": bool(row.raw_asset_uri),
        "fact_available": bool(row.fact_asset_uri),
        "raw_deleted_at": row.raw_deleted_at.isoformat() if row.raw_deleted_at else None,
        "reference_asset_id": row.reference_asset_id,
        "filename": row.original_filename,
        "mime_type": row.mime_type,
        "confirmed_by": row.confirmed_by,
        "confirmed_at": row.confirmed_at.isoformat() if row.confirmed_at else None,
        "raw_content_url": (
            f"/api/v1/product-image-facts/images/{row.id}/content?tenant_id={row.tenant_id}&stage=raw"
            if row.raw_asset_uri else None
        ),
        "fact_content_url": (
            f"/api/v1/product-image-facts/images/{row.id}/content?tenant_id={row.tenant_id}&stage=fact"
            if row.fact_asset_uri else None
        ),
    }


@router.get("/slots")
def list_slots():
    return {"slots": slot_definitions()}


@router.get("/products/{product_id}")
def list_product_image_facts(
    product_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    _product(db, tenant_id=tenant_id, product_id=product_id)
    rows = db.scalars(
        select(ProductImageFact)
        .where(
            ProductImageFact.tenant_id == tenant_id,
            ProductImageFact.product_id == product_id,
        )
        .order_by(ProductImageFact.created_at, ProductImageFact.slot_index)
    ).all()
    return {
        "readiness": readiness(db, tenant_id=tenant_id, product_id=product_id),
        "images": [_payload(row) for row in rows],
    }


@router.post("/products/{product_id}/batch")
async def batch_upload(
    product_id: str,
    files: list[UploadFile] = File(...),
    auto_process: bool = Form(True),
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    _product(db, tenant_id=tenant_id, product_id=product_id)
    if not files:
        raise HTTPException(422, detail="업로드할 이미지가 없습니다.")
    if len(files) > 30:
        raise HTTPException(422, detail="한 번에 최대 30장까지 업로드할 수 있습니다.")

    created: list[ProductImageFact] = []
    try:
        for file in files:
            content = await file.read()
            if not content:
                raise HTTPException(422, detail=f"빈 파일: {file.filename}")
            if len(content) > 50 * 1024 * 1024:
                raise HTTPException(413, detail=f"50MB 초과: {file.filename}")
            if file.content_type and not file.content_type.startswith("image/"):
                raise HTTPException(415, detail=f"이미지 파일만 가능: {file.filename}")
            row = create_upload_row(
                db,
                tenant_id=tenant_id,
                product_id=product_id,
                filename=file.filename or "product-image",
                mime_type=file.content_type,
                content=content,
                auto_process=auto_process,
            )
            created.append(row)
        db.commit()
        for row in created:
            db.refresh(row)
    except ProductImageFactError as exc:
        db.rollback()
        raise HTTPException(409, detail=str(exc)) from exc

    return {
        "uploaded": len(created),
        "images": [_payload(row) for row in created],
        "readiness": readiness(db, tenant_id=tenant_id, product_id=product_id),
    }


@router.patch("/images/{image_fact_id}")
def edit_image_fact(
    image_fact_id: str,
    body: ImageFactEditBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    if body.slot_type not in SLOT_TYPES or body.slot_type == "UNASSIGNED":
        raise HTTPException(422, detail="유효한 이미지 항목을 선택해 주세요.")
    row = _row(db, tenant_id=tenant_id, image_fact_id=image_fact_id)
    try:
        set_slot_and_process(row, slot_type=body.slot_type, slot_index=body.slot_index)
        db.commit()
        db.refresh(row)
        return _payload(row)
    except ProductImageFactError as exc:
        db.rollback()
        raise HTTPException(409, detail=str(exc)) from exc


@router.post("/images/{image_fact_id}/process")
def process_image_fact(
    image_fact_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    row = _row(db, tenant_id=tenant_id, image_fact_id=image_fact_id)
    if row.status == "confirmed":
        raise HTTPException(409, detail="이미 확정된 이미지 FACT입니다.")
    try:
        process_row(row)
        db.commit()
        db.refresh(row)
        return _payload(row)
    except ProductImageFactError as exc:
        db.rollback()
        raise HTTPException(409, detail=str(exc)) from exc


@router.post("/images/{image_fact_id}/confirm")
def confirm(
    image_fact_id: str,
    body: ConfirmBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    row = _row(db, tenant_id=tenant_id, image_fact_id=image_fact_id)
    try:
        confirm_image_fact(db, row=row, confirmed_by=body.confirmed_by)
        db.commit()
        db.refresh(row)
        return {
            "image": _payload(row),
            "readiness": readiness(db, tenant_id=tenant_id, product_id=row.product_id),
        }
    except ProductImageFactError as exc:
        db.rollback()
        raise HTTPException(409, detail=str(exc)) from exc


@router.get("/images/{image_fact_id}/content")
def image_content(
    image_fact_id: str,
    stage: Literal["raw", "fact"] = Query("fact"),
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    row = _row(db, tenant_id=tenant_id, image_fact_id=image_fact_id)
    uri = row.raw_asset_uri if stage == "raw" else row.fact_asset_uri
    if not uri:
        raise HTTPException(404, detail=f"{stage} image is unavailable")
    try:
        path = resolve_media_uri(uri)
    except ImageStudioError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    media_type = row.mime_type if stage == "raw" or row.slot_type == "LIFESTYLE" else "image/png"
    return FileResponse(
        path,
        media_type=media_type or "application/octet-stream",
        filename=row.original_filename or path.name,
        content_disposition_type="inline",
    )


@router.delete("/images/{image_fact_id}")
def delete_image_fact(
    image_fact_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    row = _row(db, tenant_id=tenant_id, image_fact_id=image_fact_id)
    product_id = row.product_id
    try:
        delete_unconfirmed_row(row)
        db.delete(row)
        db.commit()
        return {
            "deleted": True,
            "readiness": readiness(db, tenant_id=tenant_id, product_id=product_id),
        }
    except ProductImageFactError as exc:
        db.rollback()
        raise HTTPException(409, detail=str(exc)) from exc
