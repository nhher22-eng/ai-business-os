from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dashboard_session import require_business_auth
from app.db.models import Product
from app.db.product_image_fact import ProductImageFact
from app.db.product_registration import ProductRegistrationProfile
from app.db.session import SessionLocal
from app.services.product_image_planning import IMAGE_PLAN_CATEGORIES, build_image_plan_suggestions


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


class ImagePlanItem(BaseModel):
    category: str
    category_label: str | None = None
    title: str = Field(min_length=1, max_length=500)
    purpose: str | None = None
    basis: list[str] = Field(default_factory=list)
    execution: str | None = None
    status: str = "review"
    note: str | None = None
    required_reference: str | None = None


class ConfirmImagePlansBody(BaseModel):
    plans: list[ImagePlanItem] = Field(default_factory=list, max_length=30)


def _load(db: Session, *, tenant_id: str, product_id: str) -> tuple[Product, ProductRegistrationProfile]:
    product = db.scalar(select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id))
    if product is None:
        raise HTTPException(404, detail="product not found")
    profile = db.scalar(
        select(ProductRegistrationProfile).where(
            ProductRegistrationProfile.product_id == product_id,
            ProductRegistrationProfile.tenant_id == tenant_id,
        )
    )
    if profile is None:
        raise HTTPException(409, detail="product registration profile not found")
    return product, profile


def _facts(profile: ProductRegistrationProfile) -> dict[str, Any]:
    return {
        "model_name": profile.model_name,
        "primary_material": profile.primary_material,
        "secondary_material": profile.secondary_material,
        "weight": profile.weight,
        "dimensions": profile.dimensions or {},
        "manufacturer": profile.manufacturer,
        "country_of_origin": profile.country_of_origin,
        "certifications": profile.certifications or [],
        "packaging": profile.packaging or {},
        "fact_notes": profile.fact_notes,
        "facts_confirmed": profile.facts_confirmed,
    }


def _confirmed_image_slots(db: Session, *, tenant_id: str, product_id: str) -> list[str]:
    rows = db.scalars(
        select(ProductImageFact).where(
            ProductImageFact.tenant_id == tenant_id,
            ProductImageFact.product_id == product_id,
            ProductImageFact.status == "confirmed",
        )
    ).all()
    result: list[str] = []
    for row in rows:
        if row.slot_type and row.slot_type not in result:
            result.append(row.slot_type)
    return result


@router.post("/products/{product_id}/image-plan-suggestions")
def suggest_image_plans(
    product_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    product, profile = _load(db, tenant_id=tenant_id, product_id=product_id)
    if not profile.facts_confirmed:
        raise HTTPException(409, detail="confirmed FACT is required before image planning")
    operating = dict(profile.operating_info or {})
    marketing = dict(profile.marketing_info or {})
    # Image planning is downstream of the user's text-basis confirmation.
    if not operating and not marketing:
        raise HTTPException(409, detail="confirm text AI suggestions before image planning")

    slots = _confirmed_image_slots(db, tenant_id=tenant_id, product_id=product_id)
    plans, metadata = build_image_plan_suggestions(
        product_name=product.name,
        facts=_facts(profile),
        image_slots=slots,
        operating_info=operating,
        marketing_info=marketing,
    )
    return {
        "plans": plans,
        "metadata": metadata,
        "confirmed_image_fact_slots": slots,
        "physical_fact_creation_allowed": False,
        "generation_started": False,
    }


@router.post("/products/{product_id}/image-plans/confirm")
def confirm_image_plans(
    product_id: str,
    body: ConfirmImagePlansBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    _, profile = _load(db, tenant_id=tenant_id, product_id=product_id)
    cleaned: list[dict[str, Any]] = []
    for item in body.plans:
        if item.category not in IMAGE_PLAN_CATEGORIES:
            raise HTTPException(422, detail=f"unsupported image plan category: {item.category}")
        payload = item.model_dump()
        payload["status"] = "confirmed"
        cleaned.append(payload)

    marketing = dict(profile.marketing_info or {})
    marketing["confirmed_image_plans"] = cleaned
    marketing["image_plan_policy"] = {
        "product_image_fact_is_canonical": True,
        "image_generation_required_for_registration": False,
        "complex_manual_content_excluded": True,
    }
    profile.marketing_info = marketing
    db.commit()
    db.refresh(profile)
    return {
        "ok": True,
        "product_id": product_id,
        "confirmed_count": len(cleaned),
        "plans": cleaned,
        "registration_blocked_by_generation": False,
    }


@router.get("/products/{product_id}/image-plans")
def get_confirmed_image_plans(
    product_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    _, profile = _load(db, tenant_id=tenant_id, product_id=product_id)
    marketing = dict(profile.marketing_info or {})
    return {
        "product_id": product_id,
        "plans": marketing.get("confirmed_image_plans") or [],
        "policy": marketing.get("image_plan_policy") or {},
    }
