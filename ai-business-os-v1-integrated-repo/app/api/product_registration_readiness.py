from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dashboard_session import require_business_auth
from app.db.models import Product
from app.db.product_registration import ProductRegistrationProfile
from app.db.session import SessionLocal
from app.services.product_image_fact import readiness as image_readiness


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


def registration_readiness(
    db: Session,
    *,
    tenant_id: str,
    product_id: str,
) -> dict:
    product = db.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.tenant_id == tenant_id,
        )
    )
    if product is None:
        raise HTTPException(404, detail="product not found")

    profile = db.scalar(
        select(ProductRegistrationProfile).where(
            ProductRegistrationProfile.product_id == product_id,
            ProductRegistrationProfile.tenant_id == tenant_id,
        )
    )
    facts_confirmed = bool(profile and profile.facts_confirmed)
    images = image_readiness(db, tenant_id=tenant_id, product_id=product_id)
    primary_asset_linked = bool(profile and profile.primary_image_asset_id)

    missing: list[str] = []
    if not facts_confirmed:
        missing.append("기본 FACT 사용자 확정")
    missing.extend(images.get("missing_labels") or [])
    if images.get("ready") and not primary_asset_linked:
        missing.append("대표 이미지 Product Master 연결")

    return {
        "ready": facts_confirmed and bool(images.get("ready")) and primary_asset_linked,
        "product_id": product.id,
        "product_status": product.status,
        "facts_confirmed": facts_confirmed,
        "images_ready": bool(images.get("ready")),
        "primary_asset_linked": primary_asset_linked,
        "required_image_slots": images.get("required_slots") or [],
        "missing_image_slots": images.get("missing_slots") or [],
        "missing_labels": missing,
        "content_basis_saved": bool(
            profile
            and (
                (profile.operating_info and bool(profile.operating_info))
                or (profile.marketing_info and bool(profile.marketing_info))
            )
        ),
        "note": (
            "Product Master 핵심 등록 완료. AI 제안/마케팅 정보는 선택적으로 보완할 수 있습니다."
            if facts_confirmed and bool(images.get("ready")) and primary_asset_linked
            else "필수 FACT와 상품 이미지 FACT를 모두 확정해야 Product Master 등록이 완료됩니다."
        ),
    }


@router.get("/products/{product_id}/readiness")
def get_registration_readiness(
    product_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    return registration_readiness(db, tenant_id=tenant_id, product_id=product_id)
