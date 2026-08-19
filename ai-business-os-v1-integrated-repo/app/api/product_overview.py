from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dashboard_session import require_business_auth
from app.db.detail_page_content_basis import DetailPageContentBasis
from app.db.models import DetailPageJob, Product, ProductSKU
from app.db.product_registration import ProductRegistrationProfile
from app.db.session import SessionLocal


router = APIRouter(
    prefix="/api/v1/product-overview",
    tags=["product-overview"],
    dependencies=[Depends(require_business_auth)],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _has_content(profile: ProductRegistrationProfile | None) -> bool:
    if profile is None:
        return False
    op = profile.operating_info or {}
    mk = profile.marketing_info or {}
    values = [
        op.get("category"),
        op.get("usage"),
        mk.get("features"),
        mk.get("selling_points"),
        mk.get("target_customer"),
        mk.get("content_direction"),
        mk.get("product_notes"),
    ]
    return any(bool(v) for v in values)


@router.get("/products")
def product_overview(
    workspace_id: str = Query(...),
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    products = db.scalars(
        select(Product)
        .where(
            Product.tenant_id == tenant_id,
            Product.workspace_id == workspace_id,
        )
        .order_by(Product.updated_at.desc(), Product.created_at.desc())
    ).all()

    result = []
    for product in products:
        profile = db.scalar(
            select(ProductRegistrationProfile).where(
                ProductRegistrationProfile.tenant_id == tenant_id,
                ProductRegistrationProfile.product_id == product.id,
            )
        )
        sku_count = db.scalar(
            select(func.count(ProductSKU.id)).where(
                ProductSKU.tenant_id == tenant_id,
                ProductSKU.product_id == product.id,
            )
        ) or 0
        detail_count = db.scalar(
            select(func.count(DetailPageJob.id)).where(
                DetailPageJob.tenant_id == tenant_id,
                DetailPageJob.product_id == product.id,
            )
        ) or 0
        page_basis_count = db.scalar(
            select(func.count(DetailPageContentBasis.id)).join(
                DetailPageJob, DetailPageJob.id == DetailPageContentBasis.job_id
            ).where(
                DetailPageContentBasis.tenant_id == tenant_id,
                DetailPageJob.product_id == product.id,
            )
        ) or 0
        primary = bool(profile and profile.primary_image_asset_id)
        additional = len(profile.additional_image_asset_ids or []) if profile else 0
        result.append(
            {
                "id": product.id,
                "name": product.name,
                "product_code": product.product_code,
                "status": product.status,
                "sales_channel": product.sales_channel,
                "facts_confirmed": bool(profile and profile.facts_confirmed),
                "has_primary_image": primary,
                "additional_image_count": additional,
                "image_count": (1 if primary else 0) + additional,
                "content_basis_status": "complete" if _has_content(profile) else "empty",
                "sku_count": int(sku_count),
                "detail_page_count": int(detail_count),
                "page_override_count": int(page_basis_count),
                "updated_at": product.updated_at.isoformat() if product.updated_at else None,
            }
        )
    return result
