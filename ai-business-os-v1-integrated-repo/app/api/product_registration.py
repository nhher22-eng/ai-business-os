from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dashboard_session import require_business_auth
from app.db.models import BusinessWorkspace, ImageReferenceAsset, Product
from app.db.product_registration import ProductRegistrationProfile
from app.db.session import SessionLocal
from app.services.image_studio import ImageStudioError, save_reference_upload
from app.services.product_registration import build_ai_suggestions


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


def utcnow():
    return datetime.now(timezone.utc)


class FactBody(BaseModel):
    model_name: str | None = None
    primary_material: str | None = None
    secondary_material: str | None = None
    weight: str | None = None
    dimensions: dict[str, Any] | None = None
    manufacturer: str | None = None
    country_of_origin: str | None = None
    certifications: list[Any] | dict[str, Any] | None = None
    packaging: dict[str, Any] | None = None
    fact_notes: str | None = None
    confirm: bool = False
    confirmed_by: str | None = None


class NewProductBody(FactBody):
    workspace_id: str
    product_code: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=240)
    description: str | None = None


class ApplySuggestionsBody(BaseModel):
    operating_info: dict[str, Any] | None = None
    marketing_info: dict[str, Any] | None = None


class ImageRoleBody(BaseModel):
    role: Literal["primary", "additional"]
    asset_id: str


def _profile_payload(row: ProductRegistrationProfile, product: Product) -> dict:
    return {
        "product": {
            "id": product.id,
            "workspace_id": product.workspace_id,
            "product_code": product.product_code,
            "name": product.name,
            "description": product.description,
            "status": product.status,
        },
        "facts": {
            "model_name": row.model_name,
            "primary_material": row.primary_material,
            "secondary_material": row.secondary_material,
            "weight": row.weight,
            "dimensions": row.dimensions or {},
            "manufacturer": row.manufacturer,
            "country_of_origin": row.country_of_origin,
            "certifications": row.certifications or [],
            "packaging": row.packaging or {},
            "fact_notes": row.fact_notes,
            "confirmed": row.facts_confirmed,
            "confirmed_by": row.facts_confirmed_by,
            "confirmed_at": row.facts_confirmed_at.isoformat() if row.facts_confirmed_at else None,
        },
        "operating_info": row.operating_info or {},
        "marketing_info": row.marketing_info or {},
        "ai_suggestions": row.ai_suggestions or {},
        "ai_suggestion_meta": row.ai_suggestion_meta or {},
        "images": {
            "primary_asset_id": row.primary_image_asset_id,
            "additional_asset_ids": row.additional_image_asset_ids or [],
        },
    }


def _get_product(db: Session, *, tenant_id: str, product_id: str) -> Product:
    product = db.scalar(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    if product is None:
        raise HTTPException(404, detail="product not found")
    return product


def _get_profile(db: Session, *, tenant_id: str, product_id: str) -> ProductRegistrationProfile:
    row = db.scalar(
        select(ProductRegistrationProfile).where(
            ProductRegistrationProfile.product_id == product_id,
            ProductRegistrationProfile.tenant_id == tenant_id,
        )
    )
    if row is None:
        # Legacy products created before Product Registration may not have a
        # profile yet. Create an empty compatibility profile on first access.
        # No FACT values are invented or confirmed here.
        row = ProductRegistrationProfile(
            tenant_id=tenant_id,
            product_id=product_id,
            additional_image_asset_ids=[],
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _apply_facts(row: ProductRegistrationProfile, body: FactBody) -> None:
    row.model_name = body.model_name
    row.primary_material = body.primary_material
    row.secondary_material = body.secondary_material
    row.weight = body.weight
    row.dimensions = body.dimensions
    row.manufacturer = body.manufacturer
    row.country_of_origin = body.country_of_origin
    row.certifications = body.certifications
    row.packaging = body.packaging
    row.fact_notes = body.fact_notes
    if body.confirm:
        row.facts_confirmed = True
        row.facts_confirmed_by = body.confirmed_by or "dashboard-user"
        row.facts_confirmed_at = utcnow()


def _facts_for_ai(row: ProductRegistrationProfile) -> dict[str, Any]:
    return {
        "model_name": row.model_name,
        "primary_material": row.primary_material,
        "secondary_material": row.secondary_material,
        "weight": row.weight,
        "dimensions": row.dimensions or {},
        "manufacturer": row.manufacturer,
        "country_of_origin": row.country_of_origin,
        "certifications": row.certifications or [],
        "packaging": row.packaging or {},
        "fact_notes": row.fact_notes,
        "facts_confirmed": row.facts_confirmed,
    }


@router.post("/products")
def register_product(
    body: NewProductBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    workspace = db.scalar(
        select(BusinessWorkspace).where(
            BusinessWorkspace.id == body.workspace_id,
            BusinessWorkspace.tenant_id == tenant_id,
        )
    )
    if workspace is None:
        raise HTTPException(404, detail="workspace not found")

    existing = db.scalar(
        select(Product).where(
            Product.workspace_id == body.workspace_id,
            Product.product_code == body.product_code,
        )
    )
    if existing is not None:
        raise HTTPException(409, detail="product already exists")

    product = Product(
        tenant_id=tenant_id,
        workspace_id=body.workspace_id,
        product_code=body.product_code,
        name=body.name,
        status="draft",
        description=body.description,
    )
    db.add(product)
    db.flush()

    row = ProductRegistrationProfile(
        tenant_id=tenant_id,
        product_id=product.id,
        additional_image_asset_ids=[],
    )
    _apply_facts(row, body)
    db.add(row)
    db.commit()
    db.refresh(product)
    db.refresh(row)
    return _profile_payload(row, product)


@router.get("/products/{product_id}")
def get_registration(
    product_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    product = _get_product(db, tenant_id=tenant_id, product_id=product_id)
    row = _get_profile(db, tenant_id=tenant_id, product_id=product_id)
    return _profile_payload(row, product)


@router.put("/products/{product_id}/facts")
def update_facts(
    product_id: str,
    body: FactBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    product = _get_product(db, tenant_id=tenant_id, product_id=product_id)
    row = _get_profile(db, tenant_id=tenant_id, product_id=product_id)
    _apply_facts(row, body)
    db.commit()
    db.refresh(row)
    return _profile_payload(row, product)


@router.post("/products/{product_id}/suggest")
def suggest_product_info(
    product_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    product = _get_product(db, tenant_id=tenant_id, product_id=product_id)
    row = _get_profile(db, tenant_id=tenant_id, product_id=product_id)
    suggestions, metadata = build_ai_suggestions(product.name, _facts_for_ai(row))
    row.ai_suggestions = suggestions
    row.ai_suggestion_meta = metadata
    db.commit()
    return {
        "suggestions": suggestions,
        "metadata": metadata,
        "fact_mutation_allowed": False,
    }


@router.post("/products/{product_id}/apply-suggestions")
def apply_suggestions(
    product_id: str,
    body: ApplySuggestionsBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    product = _get_product(db, tenant_id=tenant_id, product_id=product_id)
    row = _get_profile(db, tenant_id=tenant_id, product_id=product_id)
    if body.operating_info is not None:
        row.operating_info = body.operating_info
    if body.marketing_info is not None:
        row.marketing_info = body.marketing_info
    db.commit()
    db.refresh(row)
    return _profile_payload(row, product)


@router.get("/products/{product_id}/images")
def list_product_images(
    product_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    _get_product(db, tenant_id=tenant_id, product_id=product_id)
    row = _get_profile(db, tenant_id=tenant_id, product_id=product_id)
    assets = db.scalars(
        select(ImageReferenceAsset).where(
            ImageReferenceAsset.tenant_id == tenant_id,
            ImageReferenceAsset.product_id == product_id,
            ImageReferenceAsset.job_id.is_(None),
        ).order_by(ImageReferenceAsset.sort_order, ImageReferenceAsset.created_at)
    ).all()
    return {
        "primary_asset_id": row.primary_image_asset_id,
        "additional_asset_ids": row.additional_image_asset_ids or [],
        "assets": [
            {
                "id": asset.id,
                "filename": asset.original_filename,
                "asset_uri": asset.asset_uri,
                "mime_type": asset.mime_type,
                "sort_order": asset.sort_order,
            }
            for asset in assets
        ],
    }


@router.post("/products/{product_id}/images/upload")
async def upload_product_image(
    product_id: str,
    role: Literal["primary", "additional"] = Form(...),
    file: UploadFile = File(...),
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    _get_product(db, tenant_id=tenant_id, product_id=product_id)
    row = _get_profile(db, tenant_id=tenant_id, product_id=product_id)
    content = await file.read()
    if not content:
        raise HTTPException(422, detail="empty file")
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(413, detail="image must be <= 50MB")
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(415, detail="only image uploads are accepted")
    try:
        uri = save_reference_upload(
            product_id=product_id,
            job_id=None,
            filename=file.filename or "product-image",
            content=content,
        )
    except ImageStudioError as exc:
        raise HTTPException(500, detail=str(exc)) from exc

    current_additional = list(row.additional_image_asset_ids or [])
    sort_order = 0 if role == "primary" else len(current_additional) + 1
    asset = ImageReferenceAsset(
        tenant_id=tenant_id,
        product_id=product_id,
        job_id=None,
        asset_role="PRODUCT_REFERENCE",
        asset_uri=uri,
        original_filename=file.filename,
        mime_type=file.content_type,
        internal_reference_only=False,
        lock_level="hard_lock",
        sort_order=sort_order,
    )
    db.add(asset)
    db.flush()

    if role == "primary":
        row.primary_image_asset_id = asset.id
    else:
        if asset.id not in current_additional:
            current_additional.append(asset.id)
        row.additional_image_asset_ids = current_additional
    db.commit()
    db.refresh(asset)
    return {
        "id": asset.id,
        "role": role,
        "filename": asset.original_filename,
        "asset_uri": asset.asset_uri,
    }


@router.post("/products/{product_id}/images/assign")
def assign_product_image(
    product_id: str,
    body: ImageRoleBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    _get_product(db, tenant_id=tenant_id, product_id=product_id)
    row = _get_profile(db, tenant_id=tenant_id, product_id=product_id)
    asset = db.scalar(
        select(ImageReferenceAsset).where(
            ImageReferenceAsset.id == body.asset_id,
            ImageReferenceAsset.product_id == product_id,
            ImageReferenceAsset.tenant_id == tenant_id,
        )
    )
    if asset is None:
        raise HTTPException(404, detail="image asset not found")

    additional = list(row.additional_image_asset_ids or [])
    if body.role == "primary":
        row.primary_image_asset_id = asset.id
        if asset.id in additional:
            additional.remove(asset.id)
            row.additional_image_asset_ids = additional
    else:
        if asset.id not in additional:
            additional.append(asset.id)
        row.additional_image_asset_ids = additional
    db.commit()
    return {"ok": True, "role": body.role, "asset_id": asset.id}
