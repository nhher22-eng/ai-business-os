from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dashboard_session import require_business_auth
from app.api.product_registration import _profile_payload
from app.db.models import Product
from app.db.product_registration import ProductRegistrationProfile
from app.db.session import SessionLocal


router = APIRouter(
    prefix="/api/v1/product-registration",
    tags=["product-registration"],
    dependencies=[Depends(require_business_auth)],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/recent")
def recent_registration(
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    profile = db.scalar(
        select(ProductRegistrationProfile)
        .where(ProductRegistrationProfile.tenant_id == tenant_id)
        .order_by(ProductRegistrationProfile.updated_at.desc(), ProductRegistrationProfile.created_at.desc())
        .limit(1)
    )
    if profile is None:
        return {"registration": None}
    product = db.scalar(select(Product).where(Product.id == profile.product_id, Product.tenant_id == tenant_id))
    if product is None:
        return {"registration": None}
    return {"registration": _profile_payload(profile, product)}
