from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dashboard_session import require_business_auth
from app.db.models import DetailPageJob, Product, ProductSKU, SalesChannelListing
from app.db.product_registration import ProductRegistrationProfile
from app.db.session import SessionLocal
from app.services.commerce_codes import create_sku as create_commerce_sku
from app.services.product_image_fact import readiness as image_fact_readiness

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
    shipping_fee: int | None = Field(default=None, ge=0)


class ProductNarrativeBody(BaseModel):
    features: list[str] = Field(default_factory=list, max_length=30)
    advantages: list[str] = Field(default_factory=list, max_length=30)
    limitations: list[str] = Field(default_factory=list, max_length=30)
    recommended_uses: list[str] = Field(default_factory=list, max_length=30)
    usage_instructions: list[str] = Field(default_factory=list, max_length=30)
    cautions: list[str] = Field(default_factory=list, max_length=30)


class ProductFactsBody(BaseModel):
    primary_material: str | None = None
    secondary_material: str | None = None
    weight: str | None = None
    dimensions: dict = Field(default_factory=dict)
    certifications: list = Field(default_factory=list)
    components: list[str] = Field(default_factory=list, max_length=100)
    fact_notes: str | None = None


class SKUDetailUpdate(SKUManagementBody):
    id: str = Field(min_length=1, max_length=36)


class ChannelDetailUpdate(ChannelListingBody):
    sku_id: str = Field(min_length=1, max_length=36)


class ProductDetailSaveBody(BaseModel):
    product: ProductMasterBody
    narrative: ProductNarrativeBody = Field(default_factory=ProductNarrativeBody)
    facts: ProductFactsBody = Field(default_factory=ProductFactsBody)
    skus: list[SKUDetailUpdate] = Field(default_factory=list, max_length=200)
    channels: list[ChannelDetailUpdate] = Field(default_factory=list, max_length=600)
    changed_by: str = Field(default="dashboard-user", min_length=1, max_length=128)


def _listing_payload(row: SalesChannelListing) -> dict:
    return {"id": row.id, "channel": row.channel, "external_product_id": row.external_product_id,
            "external_sku_id": row.external_sku_id, "status": row.status,
            "channel_product_name": row.channel_product_name, "channel_price": row.channel_price,
            "last_synced_at": row.last_synced_at.isoformat() if row.last_synced_at else None}


def _clean(value: str | None) -> str | None:
    return value.strip() or None if value is not None else None


def _clean_list(values: list[str]) -> list[str]:
    return [cleaned for value in values if (cleaned := value.strip())]


def _narrative_payload(profile: ProductRegistrationProfile | None) -> dict:
    operating = profile.operating_info or {} if profile else {}
    marketing = profile.marketing_info or {} if profile else {}
    return {
        "features": marketing.get("features") or [],
        "advantages": marketing.get("selling_points") or [],
        "limitations": marketing.get("limitations") or [],
        "recommended_uses": operating.get("usage") or [],
        "usage_instructions": operating.get("usage_instructions") or [],
        "cautions": marketing.get("product_notes") or [],
        "facts_confirmed": bool(profile and profile.facts_confirmed),
        "ai_suggestions": profile.ai_suggestions or {} if profile else {},
    }


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
        "shipping_fee": row.shipping_fee,
        "stock_warning": row.available_stock <= row.safety_stock,
        "channels": [_listing_payload(x) for x in channels],
    }


def _registration_review(*, skus: list[ProductSKU],
                         listings: list[SalesChannelListing],
                         image_readiness: dict,
                         detail_page_ready: bool) -> dict:
    checks = [
        {"code": "front_image", "label": "정면 원본 이미지",
         "ready": "FRONT" not in (image_readiness.get("missing_slots") or []),
         "next_action": "등록 자료에서 정면 원본 이미지를 등록·확정하세요."},
        {"code": "sku_price", "label": "SKU 판매가",
         "ready": bool(skus) and all(sku.sale_price is not None for sku in skus),
         "next_action": "가격·재고·배송에서 모든 SKU의 현재 판매가를 입력하세요."},
        {"code": "shipping", "label": "배송비",
         "ready": bool(skus) and all(sku.shipping_fee is not None for sku in skus),
         "next_action": "가격·재고·배송에서 모든 SKU의 배송비를 입력하세요."},
        {"code": "selling_content", "label": "판매콘텐츠",
         "ready": detail_page_ready,
         "next_action": "판매콘텐츠에서 승인된 상세페이지를 준비하세요."},
        {"code": "sales_channel", "label": "판매채널",
         "ready": any(row.status in {"linked", "pending", "active"}
                      and bool(row.external_product_id) for row in listings),
         "next_action": "판매채널에서 최소 한 채널의 상품번호를 연결하세요."},
    ]
    missing = [check for check in checks if not check["ready"]]
    return {
        "status": "PASS" if not missing else "REVIEW",
        "ready": not missing,
        "checks": checks,
        "missing_count": len(missing),
        "missing_labels": [check["label"] for check in missing],
        "next_actions": [check["next_action"] for check in missing],
        "external_actions_executed": False,
        "approval_required_before_external_execution": True,
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
    profile = db.scalar(select(ProductRegistrationProfile).where(
        ProductRegistrationProfile.tenant_id == tenant_id,
        ProductRegistrationProfile.product_id == product.id,
    ))
    return {
        "id": product.id, "product_code": product.product_code, "name": product.name,
        "status": product.status, "description": product.description,
        "category": product.category, "brand": product.brand,
        "model_name": product.model_name, "manufacturer": product.manufacturer,
        "country_of_origin": product.country_of_origin,
        "supplier_name": product.supplier_name,
        "created_at": product.created_at.isoformat(),
        "updated_at": product.updated_at.isoformat(),
        "narrative": _narrative_payload(profile),
        "facts": {
            "primary_material": profile.primary_material if profile else None,
            "secondary_material": profile.secondary_material if profile else None,
            "weight": profile.weight if profile else None,
            "dimensions": profile.dimensions or {} if profile else {},
            "certifications": profile.certifications or [] if profile else [],
            "components": (profile.packaging or {}).get("components", []) if profile else [],
            "fact_notes": profile.fact_notes if profile else None,
        },
        "skus": [_sku_payload(s, by_sku.get(s.id, [])) for s in skus],
    }


@router.get("/products/{product_id}/readiness-review")
def product_registration_review(product_id: str, tenant_id: str = Query(...),
                                db: Session = Depends(get_db)):
    product = db.scalar(select(Product).where(
        Product.id == product_id, Product.tenant_id == tenant_id
    ))
    if product is None:
        raise HTTPException(404, detail="product not found")
    skus = list(db.scalars(select(ProductSKU).where(
        ProductSKU.tenant_id == tenant_id,
        ProductSKU.product_id == product.id,
    )).all())
    listings = list(db.scalars(select(SalesChannelListing).where(
        SalesChannelListing.tenant_id == tenant_id,
        SalesChannelListing.product_id == product.id,
    )).all())
    detail_page_ready = db.scalar(select(DetailPageJob.id).where(
        DetailPageJob.tenant_id == tenant_id,
        DetailPageJob.product_id == product.id,
        DetailPageJob.approved_version_no.is_not(None),
    )) is not None
    return _registration_review(
        skus=skus,
        listings=listings,
        image_readiness=image_fact_readiness(
            db, tenant_id=tenant_id, product_id=product.id
        ),
        detail_page_ready=detail_page_ready,
    )


@router.put("/products/{product_id}/detail")
def save_product_detail(product_id: str, body: ProductDetailSaveBody,
                        tenant_id: str = Query(...), db: Session = Depends(get_db)):
    """Validate first, then save the internal product detail as one transaction.

    External channel publication is intentionally excluded. Channel rows here
    are internal preparation records and remain subject to the existing approval
    boundary before any marketplace write.
    """
    product = db.scalar(select(Product).where(
        Product.id == product_id, Product.tenant_id == tenant_id
    ))
    if product is None:
        raise HTTPException(404, detail="product not found")

    sku_rows = db.scalars(select(ProductSKU).where(
        ProductSKU.tenant_id == tenant_id,
        ProductSKU.product_id == product.id,
    )).all()
    by_id = {row.id: row for row in sku_rows}
    unknown = [item.id for item in body.skus if item.id not in by_id]
    channel_unknown = [item.sku_id for item in body.channels if item.sku_id not in by_id]
    if unknown or channel_unknown:
        raise HTTPException(409, detail={
            "message": "상품에 속하지 않는 SKU 변경이 포함되어 있습니다.",
            "sku_ids": sorted(set(unknown + channel_unknown)),
        })

    # 상품명·상품코드·상품분류는 신규등록에서 넘어온 기준값이다.
    # 통합관리 상세 저장에서는 의도치 않게 변경하지 않는다.
    product.status = body.product.status
    product.description = _clean(body.product.description)
    for field in (
        "brand", "model_name", "manufacturer",
        "country_of_origin", "supplier_name",
    ):
        setattr(product, field, _clean(getattr(body.product, field)))

    for item in body.skus:
        sku = by_id[item.id]
        for field in (
            "name", "option_value", "barcode", "sales_unit", "status",
            "purchase_cost", "list_price", "sale_price", "current_stock",
            "available_stock", "safety_stock", "incoming_stock", "storage_location",
            "shipping_fee",
        ):
            value = getattr(item, field)
            if field == "name":
                value = value.strip()
            elif field in {"option_value", "barcode", "storage_location"}:
                value = _clean(value)
            setattr(sku, field, value)

    profile = db.scalar(select(ProductRegistrationProfile).where(
        ProductRegistrationProfile.tenant_id == tenant_id,
        ProductRegistrationProfile.product_id == product.id,
    ))
    if profile is None:
        profile = ProductRegistrationProfile(tenant_id=tenant_id, product_id=product.id)
        db.add(profile)
    operating = dict(profile.operating_info or {})
    marketing = dict(profile.marketing_info or {})
    operating["usage"] = _clean_list(body.narrative.recommended_uses)
    operating["usage_instructions"] = _clean_list(body.narrative.usage_instructions)
    marketing.update({
        "features": _clean_list(body.narrative.features),
        "selling_points": _clean_list(body.narrative.advantages),
        "limitations": _clean_list(body.narrative.limitations),
        "product_notes": _clean_list(body.narrative.cautions),
    })
    profile.operating_info = operating
    profile.marketing_info = marketing
    profile.primary_material = _clean(body.facts.primary_material)
    profile.secondary_material = _clean(body.facts.secondary_material)
    profile.weight = _clean(body.facts.weight)
    profile.dimensions = body.facts.dimensions or {}
    profile.certifications = body.facts.certifications or []
    packaging = dict(profile.packaging or {})
    packaging["components"] = _clean_list(body.facts.components)
    profile.packaging = packaging
    profile.fact_notes = _clean(body.facts.fact_notes)

    for item in body.channels:
        row = db.scalar(select(SalesChannelListing).where(
            SalesChannelListing.tenant_id == tenant_id,
            SalesChannelListing.sku_id == item.sku_id,
            SalesChannelListing.channel == item.channel,
        ))
        if row is None:
            row = SalesChannelListing(
                tenant_id=tenant_id, product_id=product.id,
                sku_id=item.sku_id, channel=item.channel,
            )
            db.add(row)
        row.external_product_id = _clean(item.external_product_id)
        row.external_sku_id = _clean(item.external_sku_id)
        row.status = item.status
        row.channel_product_name = _clean(item.channel_product_name)
        row.channel_price = item.channel_price
        row.last_synced_at = datetime.now(timezone.utc)

    db.commit()
    return {
        "id": product.id,
        "product_code": product.product_code,
        "saved": {
            "product": 1, "narrative": 1,
            "skus": len(body.skus), "channels": len(body.channels),
        },
        "external_actions_executed": False,
        "approval_required": any(item.status in {"pending", "active"} for item in body.channels),
        "changed_by": body.changed_by,
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
            "available_stock", "safety_stock", "incoming_stock", "shipping_fee"):
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
                  "available_stock", "safety_stock", "incoming_stock", "shipping_fee"):
        setattr(sku, field, getattr(body, field))
    sku.storage_location = _clean(body.storage_location)
    db.commit()
    db.refresh(sku)
    return _sku_payload(sku, [])


@router.delete("/skus/{sku_id}")
def delete_managed_sku(sku_id: str, tenant_id: str = Query(...),
                       db: Session = Depends(get_db)):
    """Delete an unused SKU; referenced SKUs must be deactivated instead."""
    sku = db.scalar(select(ProductSKU).where(
        ProductSKU.id == sku_id, ProductSKU.tenant_id == tenant_id
    ))
    if sku is None:
        raise HTTPException(404, detail="sku not found")
    listing = db.scalar(select(SalesChannelListing.id).where(
        SalesChannelListing.tenant_id == tenant_id,
        SalesChannelListing.sku_id == sku.id,
    ))
    if listing is not None:
        raise HTTPException(
            409,
            detail="판매채널 연결 이력이 있는 SKU는 삭제할 수 없습니다. 비활성화하세요.",
        )
    deleted = {"id": sku.id, "sku_code": sku.sku_code, "product_id": sku.product_id}
    db.delete(sku)
    db.commit()
    return deleted


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
