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

    operating = dict(profile.operating_info or {}) if profile else {}
    marketing = dict(profile.marketing_info or {}) if profile else {}
    content_basis_saved = bool(operating or marketing)
    image_plan_policy = marketing.get("image_plan_policy") if isinstance(marketing, dict) else None
    image_plans_saved = bool(isinstance(image_plan_policy, dict) and image_plan_policy.get("plans_confirmed"))

    missing: list[str] = []
    if not facts_confirmed:
        missing.append("기본 FACT 사용자 확정")
    if not primary_asset_linked:
        missing.append("원본 이미지 최소 1개")

    # Product registration stores source material only. Angle completeness and
    # image-role planning are handled by the separate image asset generator.
    core_ready = facts_confirmed and primary_asset_linked
    registration_missing: list[str] = []
    if not core_ready:
        registration_missing.extend(missing)
    # Image role planning belongs to the separate image-asset generator.  It is
    # useful downstream state, but it must not block Product Master registration.
    registration_flow_complete = core_ready

    return {
        # `ready` remains the stable Product Master core gate used by downstream release policy.
        "ready": core_ready,
        "registration_flow_complete": registration_flow_complete,
        "product_id": product.id,
        "product_status": product.status,
        "facts_confirmed": facts_confirmed,
        "images_ready": primary_asset_linked,
        "primary_asset_linked": primary_asset_linked,
        "required_image_slots": images.get("required_slots") or [],
        "missing_image_slots": images.get("missing_slots") or [],
        "missing_labels": missing,
        "registration_missing_labels": registration_missing,
        "content_basis_saved": content_basis_saved,
        "image_plans_saved": image_plans_saved,
        "image_generation_required": False,
        "note": (
            "상품등록 완료. 객관적 FACT와 원본 자료가 저장되었습니다. 문안 작성과 이미지 활용 기획은 각각의 다음 도구에서 진행합니다."
            if registration_flow_complete
            else (
                "상품 FACT는 확인되었으며 원본 이미지를 최소 1개 등록하면 완료됩니다."
                if core_ready
                else "필수 FACT와 상품 이미지 FACT를 모두 확정해야 Product Master 핵심 등록이 완료됩니다."
            )
        ),
    }


@router.get("/products/{product_id}/readiness")
def get_registration_readiness(
    product_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    return registration_readiness(db, tenant_id=tenant_id, product_id=product_id)
