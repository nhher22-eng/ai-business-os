from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dashboard_session import require_business_auth
from app.db.models import Product, ProductSKU, SalesChannelListing
from app.db.session import SessionLocal
from app.services.commerce_codes import create_sku as create_commerce_sku

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


class ProductMasterBody(BaseModel):
    name: str = Field(min_length=1, max_length=240)
    status: str = Field(pattern="^(draft|active|inactive)$")
    description: str | None = None
    category: str | None = Field(default=None, max_length=160)
    brand: str | None = Field(default=None, max_length=160)
    model_name: str | None = Field(default=None, max_length=160)
    manufacturer: str | None = Field(default=None, max_length=200)
    country_of_origin: str | None = Field(default=None, max_length=160)
    supplier_name: str | None = Field(default=None, max_length=200)


class SKUManagementBody(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    option_value: str | None = Field(default=None, max_length=120)
    barcode: str | None = Field(default=None, max_length=64)
    sales_unit: str = Field(default="each", pattern="^(each|box|set)$")
    status: str = Field(default="active", pattern="^(draft|active|inactive)$")
    purchase_cost: int | None = Field(default=None, ge=0)
    list_price: int | None = Field(default=None, ge=0)
    sale_price: int | None = Field(default=None, ge=0)
    current_stock: int = Field(default=0, ge=0)
    available_stock: int = Field(default=0, ge=0)
    safety_stock: int = Field(default=0, ge=0)
    incoming_stock: int = Field(default=0, ge=0)
    storage_location: str | None = Field(default=None, max_length=160)


def _listing_payload(row: SalesChannelListing) -> dict:
    return {"id": row.id, "channel": row.channel, "external_product_id": row.external_product_id,
            "external_sku_id": row.external_sku_id, "status": row.status,
            "channel_product_name": row.channel_product_name, "channel_price": row.channel_price,
            "last_synced_at": row.last_synced_at.isoformat() if row.last_synced_at else None}


def _clean(value: str | None) -> str | None:
    return value.strip() or None if value is not None else None


def _sku_payload(row: ProductSKU, channels: list[SalesChannelListing]) -> dict:
    sale = row.sale_price
    cost = row.purchase_cost
    margin = sale - cost if sale is not None and cost is not None else None
    margin_rate = round(margin / sale * 100, 1) if margin is not None and sale else None
    return {
        "id": row.id, "sku_code": row.sku_code, "name": row.name,
        "option_value": row.option_value, "barcode": row.barcode,
        "sales_unit": row.sales_unit, "status": row.status,
        "purchase_cost": row.purchase_cost, "list_price": row.list_price,
        "sale_price": row.sale_price, "margin": margin, "margin_rate": margin_rate,
        "current_stock": row.current_stock, "available_stock": row.available_stock,
        "safety_stock": row.safety_stock, "incoming_stock": row.incoming_stock,
        "storage_location": row.storage_location,
        "stock_warning": row.available_stock <= row.safety_stock,
        "channels": [_listing_payload(x) for x in channels],
    }


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
        "sales_channel": p.sales_channel, "category": p.category, "brand": p.brand,
        "manufacturer": p.manufacturer, "supplier_name": p.supplier_name,
        "created_at": p.created_at.isoformat(),
        "updated_at": p.updated_at.isoformat(),
        "skus": [_sku_payload(s, by_sku.get(s.id, [])) for s in by_product.get(p.id, [])]
    } for p in products]


@router.get("/products/{product_id}")
def product_management_detail(product_id: str, tenant_id: str = Query(...),
                              db: Session = Depends(get_db)):
    product = db.scalar(select(Product).where(
        Product.id == product_id, Product.tenant_id == tenant_id
    ))
    if product is None:
        raise HTTPException(404, detail="product not found")
    skus = db.scalars(select(ProductSKU).where(
        ProductSKU.tenant_id == tenant_id, ProductSKU.product_id == product.id
    ).order_by(ProductSKU.created_at)).all()
    listings = db.scalars(select(SalesChannelListing).where(
        SalesChannelListing.tenant_id == tenant_id,
        SalesChannelListing.product_id == product.id,
    )).all()
    by_sku: dict[str, list[SalesChannelListing]] = {}
    for listing in listings:
        by_sku.setdefault(listing.sku_id, []).append(listing)
    return {
        "id": product.id, "product_code": product.product_code, "name": product.name,
        "status": product.status, "description": product.description,
        "category": product.category, "brand": product.brand,
        "model_name": product.model_name, "manufacturer": product.manufacturer,
        "country_of_origin": product.country_of_origin,
        "supplier_name": product.supplier_name,
        "created_at": product.created_at.isoformat(),
        "updated_at": product.updated_at.isoformat(),
        "skus": [_sku_payload(s, by_sku.get(s.id, [])) for s in skus],
    }


@router.put("/products/{product_id}")
def update_product_master(product_id: str, body: ProductMasterBody,
                          tenant_id: str = Query(...), db: Session = Depends(get_db)):
    product = db.scalar(select(Product).where(
        Product.id == product_id, Product.tenant_id == tenant_id
    ))
    if product is None:
        raise HTTPException(404, detail="product not found")
    product.name = body.name.strip()
    product.status = body.status
    product.description = _clean(body.description)
    for field in (
        "category", "brand", "model_name", "manufacturer",
        "country_of_origin", "supplier_name",
    ):
        setattr(product, field, _clean(getattr(body, field)))
    db.commit()
    db.refresh(product)
    return {"id": product.id, "product_code": product.product_code,
            "name": product.name, "status": product.status}


@router.put("/skus/{sku_id}")
def update_sku_management(sku_id: str, body: SKUManagementBody,
                          tenant_id: str = Query(...), db: Session = Depends(get_db)):
    sku = db.scalar(select(ProductSKU).where(
        ProductSKU.id == sku_id, ProductSKU.tenant_id == tenant_id
    ))
    if sku is None:
        raise HTTPException(404, detail="sku not found")
    sku.name = body.name.strip()
    sku.option_value = _clean(body.option_value)
    sku.barcode = _clean(body.barcode)
    sku.sales_unit = body.sales_unit
    sku.status = body.status
    for field in ("purchase_cost", "list_price", "sale_price", "current_stock",
                  "available_stock", "safety_stock", "incoming_stock"):
        setattr(sku, field, getattr(body, field))
    sku.storage_location = _clean(body.storage_location)
    db.commit()
    db.refresh(sku)
    return _sku_payload(sku, [])


@router.post("/products/{product_id}/skus")
def add_managed_sku(product_id: str, body: SKUManagementBody,
                    tenant_id: str = Query(...), db: Session = Depends(get_db)):
    product = db.scalar(select(Product).where(
        Product.id == product_id, Product.tenant_id == tenant_id
    ))
    if product is None:
        raise HTTPException(404, detail="product not found")
    sku = create_commerce_sku(
        db,
        product=product,
        name=body.name.strip(),
        option_value=_clean(body.option_value),
    )
    sku.barcode = _clean(body.barcode)
    sku.sales_unit = body.sales_unit
    sku.status = body.status
    for field in ("purchase_cost", "list_price", "sale_price", "current_stock",
                  "available_stock", "safety_stock", "incoming_stock"):
        setattr(sku, field, getattr(body, field))
    sku.storage_location = _clean(body.storage_location)
    db.commit()
    db.refresh(sku)
    return _sku_payload(sku, [])


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
