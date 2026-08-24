from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dashboard_session import require_business_auth
from app.db.models import Product, ProductSKU, SalesChannelListing
from app.db.session import SessionLocal

router = APIRouter(prefix="/api/v1/commerce-catalog", tags=["commerce-catalog"],
                   dependencies=[Depends(require_business_auth)])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ChannelListingBody(BaseModel):
    channel: str = Field(pattern="^(naver|coupang|own_store)$")
    external_product_id: str | None = Field(default=None, max_length=160)
    external_sku_id: str | None = Field(default=None, max_length=160)
    status: str = Field(default="linked", pattern="^(unlinked|linked|pending|active|error|stopped)$")
    channel_product_name: str | None = Field(default=None, max_length=240)
    channel_price: int | None = Field(default=None, ge=0)


class DeleteProductBody(BaseModel):
    confirm_product_code: str = Field(min_length=1, max_length=128)
    delete_linked_skus: bool = False


def _listing_payload(row: SalesChannelListing) -> dict:
    return {"id": row.id, "channel": row.channel, "external_product_id": row.external_product_id,
            "external_sku_id": row.external_sku_id, "status": row.status,
            "channel_product_name": row.channel_product_name, "channel_price": row.channel_price,
            "last_synced_at": row.last_synced_at.isoformat() if row.last_synced_at else None}


@router.get("/rows")
def catalog_rows(workspace_id: str = Query(...), tenant_id: str = Query(...), db: Session = Depends(get_db)):
    products = db.scalars(select(Product).where(
        Product.tenant_id == tenant_id, Product.workspace_id == workspace_id
    ).order_by(Product.created_at.desc())).all()
    product_ids = [p.id for p in products]
    skus = db.scalars(select(ProductSKU).where(
        ProductSKU.tenant_id == tenant_id, ProductSKU.product_id.in_(product_ids)
    ).order_by(ProductSKU.created_at)).all() if product_ids else []
    listings = db.scalars(select(SalesChannelListing).where(
        SalesChannelListing.tenant_id == tenant_id, SalesChannelListing.product_id.in_(product_ids)
    )).all() if product_ids else []
    by_product: dict[str, list[ProductSKU]] = {}
    by_sku: dict[str, list[SalesChannelListing]] = {}
    for sku in skus:
        by_product.setdefault(sku.product_id, []).append(sku)
    for listing in listings:
        by_sku.setdefault(listing.sku_id, []).append(listing)
    return [{
        "id": p.id, "product_code": p.product_code, "name": p.name, "status": p.status,
        "sales_channel": p.sales_channel, "created_at": p.created_at.isoformat(),
        "updated_at": p.updated_at.isoformat(),
        "skus": [{"id": s.id, "sku_code": s.sku_code, "name": s.name,
                  "option_value": s.option_value, "barcode": s.barcode,
                  "sales_unit": s.sales_unit, "status": s.status,
                  "channels": [_listing_payload(x) for x in by_sku.get(s.id, [])]}
                 for s in by_product.get(p.id, [])]
    } for p in products]


@router.delete("/products/{product_id}")
def delete_product(product_id: str, body: DeleteProductBody,
                   tenant_id: str = Query(...), db: Session = Depends(get_db)):
    product = db.scalar(select(Product).where(
        Product.id == product_id, Product.tenant_id == tenant_id
    ))
    if product is None:
        raise HTTPException(404, detail="product not found")
    if body.confirm_product_code != product.product_code:
        raise HTTPException(409, detail="상품코드 확인값이 일치하지 않습니다.")

    sku_ids = list(db.scalars(select(ProductSKU.id).where(
        ProductSKU.tenant_id == tenant_id, ProductSKU.product_id == product.id
    )).all())
    if sku_ids and not body.delete_linked_skus:
        raise HTTPException(
            409,
            detail=f"연결된 SKU {len(sku_ids)}개 삭제 확인이 필요합니다.",
        )
    listing_count = len(db.scalars(select(SalesChannelListing.id).where(
        SalesChannelListing.tenant_id == tenant_id,
        SalesChannelListing.product_id == product.id,
    )).all())
    deleted = {
        "id": product.id,
        "product_code": product.product_code,
        "name": product.name,
        "deleted_skus": len(sku_ids),
        "deleted_channel_listings": listing_count,
    }
    db.delete(product)
    db.commit()
    return deleted


@router.put("/skus/{sku_id}/channels/{channel}")
def upsert_channel(sku_id: str, channel: str, body: ChannelListingBody,
                   tenant_id: str = Query(...), db: Session = Depends(get_db)):
    if channel != body.channel:
        raise HTTPException(400, detail="channel mismatch")
    sku = db.scalar(select(ProductSKU).where(ProductSKU.id == sku_id, ProductSKU.tenant_id == tenant_id))
    if sku is None:
        raise HTTPException(404, detail="sku not found")
    row = db.scalar(select(SalesChannelListing).where(
        SalesChannelListing.sku_id == sku_id, SalesChannelListing.channel == channel
    ))
    if row is None:
        row = SalesChannelListing(tenant_id=tenant_id, product_id=sku.product_id,
                                  sku_id=sku.id, channel=channel)
        db.add(row)
    row.external_product_id = body.external_product_id or None
    row.external_sku_id = body.external_sku_id or None
    row.status = body.status
    row.channel_product_name = body.channel_product_name or None
    row.channel_price = body.channel_price
    row.last_synced_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(row)
    return _listing_payload(row)
