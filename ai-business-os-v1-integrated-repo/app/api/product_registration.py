from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dashboard_session import require_business_auth
from app.db.models import BusinessWorkspace, ImageReferenceAsset, Product
from app.db.product_registration import ProductRegistrationProfile, ProductSourceAsset
from app.db.session import SessionLocal
from app.services.image_studio import ImageStudioError, media_root, resolve_media_uri, save_reference_upload
from app.services.product_registration import build_ai_suggestions
from app.services.commerce_codes import allocate_product_code, create_sku, normalize_product_code


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
    product_code: str | None = Field(default=None, max_length=128)
    name: str = Field(min_length=1, max_length=240)
    description: str | None = None
    options: list[str] = Field(default_factory=list, max_length=100)


class ApplySuggestionsBody(BaseModel):
    operating_info: dict[str, Any] | None = None
    marketing_info: dict[str, Any] | None = None


class ImageRoleBody(BaseModel):
    role: Literal["primary", "additional"]
    asset_id: str


class ImageClassificationBody(BaseModel):
    source_classification: str


SOURCE_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt", ".zip"}
SOURCE_KINDS = {"manufacturer", "manual", "specification", "certificate", "other"}
MAX_SOURCE_BYTES = 25 * 1024 * 1024
ALLOWED_IMAGE_CLASSIFICATIONS = {
    "front", "back", "right_45", "left_45", "side", "top", "bottom", "detail",
    "usage_original", "components", "group", "installation", "unknown",
}


def _safe_source_name(value: str) -> str:
    name = Path(value or "source").name
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or "source"
    return stem[:180]


_RESERVED_MARKETING_KEYS = {"confirmed_image_plans", "image_plan_policy"}


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

    try:
        product_code = (
            normalize_product_code(body.product_code)
            if (body.product_code or "").strip()
            else allocate_product_code(db, body.workspace_id)
        )
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    existing = db.scalar(
        select(Product).where(
            Product.workspace_id == body.workspace_id,
            func.lower(Product.product_code) == product_code.lower(),
        )
    )
    if existing is not None:
        raise HTTPException(409, detail="product already exists")

    product = Product(
        tenant_id=tenant_id,
        workspace_id=body.workspace_id,
        product_code=product_code,
        name=body.name,
        status="draft",
        description=body.description,
    )
    db.add(product)
    db.flush()

    options = list(dict.fromkeys(x.strip() for x in body.options if x.strip()))
    if options:
        skus = [create_sku(db, product=product, name=f"{body.name} {option}", option_value=option) for option in options]
    else:
        skus = [create_sku(db, product=product, name=f"{body.name} 기본")]

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
    payload = _profile_payload(row, product)
    payload["skus"] = [
        {"id": sku.id, "sku_code": sku.sku_code, "name": sku.name,
         "option_value": sku.option_value, "barcode": sku.barcode, "sales_unit": sku.sales_unit}
        for sku in skus
    ]
    return payload


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
        # Text confirmation may happen again after image planning. Preserve the
        # reserved image-plan state so re-editing text never silently deletes it.
        existing_marketing = dict(row.marketing_info or {})
        merged_marketing = dict(body.marketing_info)
        for key in _RESERVED_MARKETING_KEYS:
            if key in existing_marketing:
                merged_marketing[key] = existing_marketing[key]
        row.marketing_info = merged_marketing
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
    # Only expose the currently confirmed upload set.  Older uploads remain in
    # storage for recovery/audit, but must not leak into the next production
    # plan.  Legacy profiles accumulated every additional id, so the current
    # primary timestamp is also used as the batch boundary.
    primary = None
    if row.primary_image_asset_id:
        primary = db.scalar(
            select(ImageReferenceAsset).where(
                ImageReferenceAsset.id == row.primary_image_asset_id,
                ImageReferenceAsset.tenant_id == tenant_id,
            )
        )
    active_ids = [
        value
        for value in [row.primary_image_asset_id, *(row.additional_image_asset_ids or [])]
        if value
    ]
    assets = []
    if active_ids:
        statement = select(ImageReferenceAsset).where(
            ImageReferenceAsset.id.in_(active_ids),
            ImageReferenceAsset.tenant_id == tenant_id,
            ImageReferenceAsset.product_id == product_id,
            ImageReferenceAsset.job_id.is_(None),
        )
        if primary is not None:
            statement = statement.where(ImageReferenceAsset.created_at >= primary.created_at)
        assets = db.scalars(
            statement.order_by(ImageReferenceAsset.sort_order, ImageReferenceAsset.created_at)
        ).all()
    return {
        "primary_asset_id": row.primary_image_asset_id,
        "additional_asset_ids": row.additional_image_asset_ids or [],
        "assets": [
            {
                "id": asset.id,
                "filename": asset.original_filename,
                "source_classification": asset.asset_role.removeprefix("SOURCE_").lower(),
                "asset_uri": asset.asset_uri,
                "mime_type": asset.mime_type,
                "sort_order": asset.sort_order,
            }
            for asset in assets
        ],
    }


@router.get("/products/{product_id}/sources")
def list_product_sources(
    product_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    _get_product(db, tenant_id=tenant_id, product_id=product_id)
    rows = db.scalars(
        select(ProductSourceAsset).where(
            ProductSourceAsset.tenant_id == tenant_id,
            ProductSourceAsset.product_id == product_id,
        ).order_by(ProductSourceAsset.created_at.desc())
    ).all()
    return [
        {
            "id": row.id,
            "source_kind": row.source_kind,
            "original_filename": row.original_filename,
            "content_type": row.content_type,
            "content_hash": row.content_hash,
            "size_bytes": row.size_bytes,
            "note": row.note,
            "created_at": row.created_at.isoformat(),
            "content_url": f"/api/v1/product-registration/sources/{row.id}/content?tenant_id={tenant_id}",
        }
        for row in rows
    ]


@router.post("/products/{product_id}/sources/upload")
async def upload_product_source(
    product_id: str,
    source_kind: str = Form(...),
    note: str | None = Form(default=None),
    file: UploadFile = File(...),
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    _get_product(db, tenant_id=tenant_id, product_id=product_id)
    if source_kind not in SOURCE_KINDS:
        raise HTTPException(422, detail="invalid source kind")
    safe_name = _safe_source_name(file.filename or "source")
    if Path(safe_name).suffix.lower() not in SOURCE_EXTENSIONS:
        raise HTTPException(415, detail="지원 문서: PDF, Word, Excel, CSV, TXT, ZIP")
    content = await file.read(MAX_SOURCE_BYTES + 1)
    if not content or len(content) > MAX_SOURCE_BYTES:
        raise HTTPException(413, detail="문서 파일은 25MB 이하여야 합니다")
    digest = hashlib.sha256(content).hexdigest()
    folder = media_root() / "product_sources" / product_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{digest[:12]}_{safe_name}"
    path.write_bytes(content)
    row = ProductSourceAsset(
        tenant_id=tenant_id,
        product_id=product_id,
        source_kind=source_kind,
        original_filename=file.filename or safe_name,
        content_type=file.content_type,
        asset_uri=f"media://{path.relative_to(media_root()).as_posix()}",
        content_hash=digest,
        size_bytes=len(content),
        note=(note or "").strip() or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "filename": row.original_filename, "source_kind": row.source_kind}


@router.get("/sources/{source_id}/content")
def product_source_content(
    source_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    row = db.scalar(
        select(ProductSourceAsset).where(
            ProductSourceAsset.id == source_id,
            ProductSourceAsset.tenant_id == tenant_id,
        )
    )
    if row is None:
        raise HTTPException(404, detail="source asset not found")
    path = resolve_media_uri(row.asset_uri)
    return FileResponse(path, media_type=row.content_type, filename=row.original_filename)


@router.post("/products/{product_id}/images/upload")
async def upload_product_image(
    product_id: str,
    role: Literal["primary", "additional"] = Form(...),
    source_classification: str = Form(default="unknown"),
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

    # The first file of a confirmed browser queue starts a new current set.
    # Subsequent `additional` uploads in the same request sequence accumulate
    # under that new primary only.
    if role == "primary":
        row.additional_image_asset_ids = []
        current_additional = []
    else:
        current_additional = list(row.additional_image_asset_ids or [])
    sort_order = 0 if role == "primary" else len(current_additional) + 1
    if source_classification not in ALLOWED_IMAGE_CLASSIFICATIONS:
        raise HTTPException(422, detail="invalid source classification")
    asset = ImageReferenceAsset(
        tenant_id=tenant_id,
        product_id=product_id,
        job_id=None,
        asset_role=f"SOURCE_{source_classification.upper()}",
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


@router.patch("/products/{product_id}/images/{asset_id}/classification")
def update_product_image_classification(
    product_id: str,
    asset_id: str,
    body: ImageClassificationBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    _get_product(db, tenant_id=tenant_id, product_id=product_id)
    profile = _get_profile(db, tenant_id=tenant_id, product_id=product_id)
    if body.source_classification not in ALLOWED_IMAGE_CLASSIFICATIONS:
        raise HTTPException(422, detail="invalid source classification")
    current_ids = {
        value
        for value in [profile.primary_image_asset_id, *(profile.additional_image_asset_ids or [])]
        if value
    }
    if asset_id not in current_ids:
        raise HTTPException(409, detail="image is not in current confirmed source set")
    asset = db.scalar(
        select(ImageReferenceAsset).where(
            ImageReferenceAsset.id == asset_id,
            ImageReferenceAsset.tenant_id == tenant_id,
            ImageReferenceAsset.product_id == product_id,
            ImageReferenceAsset.job_id.is_(None),
        )
    )
    if asset is None:
        raise HTTPException(404, detail="product image asset not found")
    asset.asset_role = f"SOURCE_{body.source_classification.upper()}"
    db.commit()
    return {"id": asset.id, "source_classification": body.source_classification}


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
