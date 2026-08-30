from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dashboard_session import require_business_auth
from app.db.models import Product, ProductSKU
from app.db.product_operations import ProductChangeEvent
from app.db.session import SessionLocal
from app.services.commerce_codes import create_sku as create_automatic_sku


router = APIRouter(
    prefix="/api/v1/product-operations",
    tags=["product-operations"],
    dependencies=[Depends(require_business_auth)],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ProductStatusBody(BaseModel):
    status: str = Field(pattern="^(draft|active|inactive)$")
    changed_by: str | None = None


class SKUCreateBody(BaseModel):
    sku_code: str | None = Field(default=None, max_length=128)
    name: str = Field(min_length=1, max_length=200)
    option_value: str | None = Field(default=None, max_length=120)
    barcode: str | None = Field(default=None, max_length=64)
    sales_unit: str = Field(default="each", pattern="^(each|box|set)$")
    status: str = Field(default="active", pattern="^(active|inactive)$")
    changed_by: str | None = None


class SKUUpdateBody(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    option_value: str | None = Field(default=None, max_length=120)
    status: str | None = Field(default=None, pattern="^(active|inactive)$")
    barcode: str | None = Field(default=None, max_length=64)
    sales_unit: str | None = Field(default=None, pattern="^(each|box|set)$")
    changed_by: str | None = None


def _product(db: Session, tenant_id: str, product_id: str) -> Product:
    row = db.scalar(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    if row is None:
        raise HTTPException(404, detail="product not found")
    return row


def _sku_payload(row: ProductSKU) -> dict:
    return {
        "id": row.id,
        "sku_code": row.sku_code,
        "name": row.name,
        "option_value": row.option_value,
        "barcode": row.barcode,
        "sales_unit": row.sales_unit,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _event(db: Session, *, tenant_id: str, product_id: str, event_type: str, summary: str, payload: dict | None = None, changed_by: str | None = None):
    db.add(ProductChangeEvent(
        tenant_id=tenant_id,
        product_id=product_id,
        event_type=event_type,
        summary=summary,
        payload=payload,
        changed_by=changed_by or "dashboard-user",
    ))


@router.get("/products/{product_id}")
def get_operations(
    product_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    product = _product(db, tenant_id, product_id)
    skus = db.scalars(
        select(ProductSKU)
        .where(ProductSKU.product_id == product_id, ProductSKU.tenant_id == tenant_id)
        .order_by(ProductSKU.created_at)
    ).all()
    history = db.scalars(
        select(ProductChangeEvent)
        .where(ProductChangeEvent.product_id == product_id, ProductChangeEvent.tenant_id == tenant_id)
        .order_by(ProductChangeEvent.created_at.desc())
        .limit(50)
    ).all()
    return {
        "product": {"id": product.id, "status": product.status},
        "skus": [_sku_payload(x) for x in skus],
        "history": [
            {
                "id": x.id,
                "event_type": x.event_type,
                "summary": x.summary,
                "payload": x.payload or {},
                "changed_by": x.changed_by,
                "created_at": x.created_at.isoformat() if x.created_at else None,
            }
            for x in history
        ],
    }


@router.patch("/products/{product_id}/status")
def update_product_status(
    product_id: str,
    body: ProductStatusBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    product = _product(db, tenant_id, product_id)
    old = product.status
    if old != body.status:
        product.status = body.status
        _event(
            db,
            tenant_id=tenant_id,
            product_id=product_id,
            event_type="product_status_changed",
            summary=f"상품 상태 변경: {old} → {body.status}",
            payload={"before": old, "after": body.status},
            changed_by=body.changed_by,
        )
        db.commit()
    return {"id": product.id, "status": product.status}


@router.post("/products/{product_id}/skus")
def create_sku(
    product_id: str,
    body: SKUCreateBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    _product(db, tenant_id, product_id)
    existing = db.scalar(
        select(ProductSKU).where(
            ProductSKU.product_id == product_id,
            ProductSKU.sku_code == body.sku_code,
        )
    ) if body.sku_code else None
    if existing is not None:
        raise HTTPException(409, detail="sku already exists")
    product = _product(db, tenant_id, product_id)
    if body.sku_code:
        row = ProductSKU(tenant_id=tenant_id, product_id=product_id, sku_code=body.sku_code,
                         name=body.name, option_value=body.option_value, barcode=body.barcode,
                         sales_unit=body.sales_unit, status=body.status)
        db.add(row)
        db.flush()
    else:
        row = create_automatic_sku(db, product=product, name=body.name,
                                   option_value=body.option_value, barcode=body.barcode,
                                   sales_unit=body.sales_unit)
        row.status = body.status
    _event(
        db,
        tenant_id=tenant_id,
        product_id=product_id,
        event_type="sku_created",
        summary=f"SKU 추가: {row.sku_code}",
        payload=_sku_payload(row),
        changed_by=body.changed_by,
    )
    db.commit()
    db.refresh(row)
    return _sku_payload(row)


@router.patch("/products/{product_id}/skus/{sku_id}")
def update_sku(
    product_id: str,
    sku_id: str,
    body: SKUUpdateBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    _product(db, tenant_id, product_id)
    row = db.scalar(
        select(ProductSKU).where(
            ProductSKU.id == sku_id,
            ProductSKU.product_id == product_id,
            ProductSKU.tenant_id == tenant_id,
        )
    )
    if row is None:
        raise HTTPException(404, detail="sku not found")
    before = _sku_payload(row)
    if body.name is not None:
        row.name = body.name
    if body.option_value is not None:
        row.option_value = body.option_value or None
    if body.status is not None:
        row.status = body.status
    if body.barcode is not None:
        row.barcode = body.barcode or None
    if body.sales_unit is not None:
        row.sales_unit = body.sales_unit
    after = _sku_payload(row)
    if before != after:
        _event(
            db,
            tenant_id=tenant_id,
            product_id=product_id,
            event_type="sku_updated",
            summary=f"SKU 수정: {row.sku_code}",
            payload={"before": before, "after": after},
            changed_by=body.changed_by,
        )
        db.commit()
        db.refresh(row)
    return _sku_payload(row)
