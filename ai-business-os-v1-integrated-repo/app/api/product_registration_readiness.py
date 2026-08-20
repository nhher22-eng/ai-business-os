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
    missing.extend(images.get("missing_labels") or [])
    if images.get("ready") and not primary_asset_linked:
        missing.append("대표 이미지 Product Master 연결")

    core_ready = facts_confirmed and bool(images.get("ready")) and primary_asset_linked
    registration_missing: list[str] = []
    if not core_ready:
        registration_missing.extend(missing)
    if not content_basis_saved:
        registration_missing.append("텍스트 확장정보 사용자 확정")
    if not image_plans_saved:
        registration_missing.append("AI 이미지 기획 사용자 확정")
    registration_flow_complete = core_ready and content_basis_saved and image_plans_saved

    return {
        # `ready` remains the stable Product Master core gate used by downstream release policy.
        "ready": core_ready,
        "registration_flow_complete": registration_flow_complete,
        "product_id": product.id,
        "product_status": product.status,
        "facts_confirmed": facts_confirmed,
        "images_ready": bool(images.get("ready")),
        "primary_asset_linked": primary_asset_linked,
        "required_image_slots": images.get("required_slots") or [],
        "missing_image_slots": images.get("missing_slots") or [],
        "missing_labels": missing,
        "registration_missing_labels": registration_missing,
        "content_basis_saved": content_basis_saved,
        "image_plans_saved": image_plans_saved,
        "image_generation_required": False,
        "note": (
            "상품등록 완료. 기본 Product Master와 확장 상품정보가 확정되었습니다. 실제 이미지 생성은 등록 완료 조건이 아닙니다."
            if registration_flow_complete
            else (
                "Product Master 핵심 등록은 완료되었습니다. 텍스트 확장정보와 이미지 기획을 확정하면 상품등록 흐름이 완료됩니다."
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
