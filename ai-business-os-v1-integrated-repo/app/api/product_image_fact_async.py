from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dashboard_session import require_business_auth
from app.api.product_image_facts import _payload
from app.db.models import Product
from app.db.product_image_fact import ProductImageFact
from app.db.session import SessionLocal
from app.services.product_image_fact import apply_slot_policy, readiness, save_raw_capture


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


def _product(db: Session, *, tenant_id: str, product_id: str) -> Product:
    row = db.scalar(select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id))
    if row is None:
        raise HTTPException(404, detail="product not found")
    return row


@router.post("/products/{product_id}/batch-async", status_code=202)
async def batch_upload_async(
    product_id: str,
    files: list[UploadFile] = File(...),
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    """Store phone captures quickly; classification/cutout runs in image_worker."""
    _product(db, tenant_id=tenant_id, product_id=product_id)
    if not files:
        raise HTTPException(422, detail="업로드할 이미지가 없습니다.")
    if len(files) > 30:
        raise HTTPException(422, detail="한 번에 최대 30장까지 업로드할 수 있습니다.")

    created: list[ProductImageFact] = []
    for index, file in enumerate(files, start=1):
        content = await file.read()
        if not content:
            raise HTTPException(422, detail=f"빈 파일: {file.filename}")
        if len(content) > 50 * 1024 * 1024:
            raise HTTPException(413, detail=f"50MB 초과: {file.filename}")
        if file.content_type and not file.content_type.startswith("image/"):
            raise HTTPException(415, detail=f"이미지 파일만 가능: {file.filename}")

        raw_uri = save_raw_capture(
            product_id=product_id,
            filename=file.filename or "product-image",
            content=content,
        )
        row = ProductImageFact(
            tenant_id=tenant_id,
            product_id=product_id,
            slot_type="UNASSIGNED",
            slot_index=index,
            status="processing_queued",
            source_kind="temporary_capture",
            raw_asset_uri=raw_uri,
            original_filename=file.filename or "product-image",
            mime_type=file.content_type,
            classification_source="queued",
            classification_confidence=None,
        )
        apply_slot_policy(row, "UNASSIGNED")
        db.add(row)
        created.append(row)

    db.commit()
    for row in created:
        db.refresh(row)

    return {
        "accepted": len(created),
        "processing": True,
        "images": [_payload(row) for row in created],
        "readiness": readiness(db, tenant_id=tenant_id, product_id=product_id),
    }
