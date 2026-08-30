from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dashboard_session import require_business_auth
from app.db.models import ImageReferenceAsset
from app.db.session import SessionLocal
from app.services.image_studio import ImageStudioError, resolve_media_uri


router = APIRouter(
    prefix="/api/v1/product-registration-assets",
    tags=["product-registration-assets"],
    dependencies=[Depends(require_business_auth)],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/references/{asset_id}/content")
def reference_asset_content(
    asset_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    asset = db.scalar(
        select(ImageReferenceAsset).where(
            ImageReferenceAsset.id == asset_id,
            ImageReferenceAsset.tenant_id == tenant_id,
            ImageReferenceAsset.job_id.is_(None),
        )
    )
    if asset is None:
        raise HTTPException(404, detail="product image asset not found")
    try:
        path = resolve_media_uri(asset.asset_uri)
    except ImageStudioError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    return FileResponse(
        path,
        media_type=asset.mime_type or "application/octet-stream",
        filename=asset.original_filename or path.name,
        content_disposition_type="inline",
    )
