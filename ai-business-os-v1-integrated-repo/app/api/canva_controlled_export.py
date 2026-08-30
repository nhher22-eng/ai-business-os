from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dashboard_session import require_business_auth
from app.api.canva_integration import active_token
from app.core.config import settings
from app.db.canva import CanvaAutofillRun, CanvaConnection
from app.db.content_copy import ContentCopyAsset
from app.db.models import (
    DetailPageExport,
    DetailPageJob,
    ImageGeneratedAsset,
    ImageGenerationJob,
    Product,
    ProductSKU,
)
from app.db.product_registration import ProductRegistrationProfile
from app.db.session import SessionLocal
from app.services.canva_controlled_export import build_controlled_canva_contract
from app.services.canva_v12_text_export import (
    CANVA_V12_IMAGE_FIELDS,
    CanvaTextValidationError,
    assemble_canva_v12_text_draft,
    build_canva_v12_text_payload,
    canva_v12_bulk_csv,
    canva_v12_text_json,
    parse_canva_v12_bulk_csv,
)
from app.services.canva_v12_image_export import (
    CANVA_V12_IMAGE_SLOT_METADATA_KEY,
    assemble_canva_v12_image_draft,
    is_approved_canva_image,
)
from app.services.canva_v12_execution import build_canva_v12_execution_package
from app.services.detail_page_studio import current_version, export_package
from app.services.image_studio import ImageStudioError, resolve_media_uri
from app.services import canva_connect


router = APIRouter(
    prefix="/api/v1/detail-page-canva",
    tags=["detail-page-canva"],
    dependencies=[Depends(require_business_auth)],
)


class CanvaV12TextRow(BaseModel):
    text_fields: dict[str, object]
    confirmed_facts: dict[str, object] = Field(default_factory=dict)


class CanvaV12BulkRequest(BaseModel):
    rows: list[CanvaV12TextRow] = Field(min_length=1)


class CanvaV12ImageAssignments(BaseModel):
    assignments: dict[str, str] = Field(default_factory=dict)
    clear_slots: list[str] = Field(default_factory=list)


class CanvaV12CanvaUploadRequest(BaseModel):
    execution_approved: bool = False


class CanvaV12AutofillRequest(BaseModel):
    execution_approved: bool = False


def _validated_v12_row(row: CanvaV12TextRow) -> dict[str, str]:
    try:
        return build_canva_v12_text_payload(
            proposed_copy=row.text_fields,
            confirmed_facts=row.confirmed_facts,
        )
    except CanvaTextValidationError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/v1.2/text/validate")
def validate_v12_text(request: CanvaV12TextRow):
    """Validate one exact 72-field row and return the canonical JSON contract."""
    payload = _validated_v12_row(request)
    return json.loads(canva_v12_text_json(payload))


@router.post("/v1.2/text/bulk.csv")
def export_v12_bulk_csv(request: CanvaV12BulkRequest):
    """Download Canva Bulk Create CSV with one canonical row per product."""
    payloads = [_validated_v12_row(row) for row in request.rows]
    return Response(
        content=canva_v12_bulk_csv(payloads),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                'attachment; filename="canva_v1.2_bulk_create.csv"'
            )
        },
    )


@router.post("/v1.2/text/import.csv")
async def import_v12_bulk_csv(file: UploadFile = File(...)):
    """Validate an uploaded Canva CSV and return canonical rows for review."""
    try:
        rows = parse_canva_v12_bulk_csv(await file.read())
    except CanvaTextValidationError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    return {
        "template_name": "AI Business OS 상세페이지 표준 v1.2_12P",
        "field_count": 72,
        "row_count": len(rows),
        "matched": "72/72",
        "rows": rows,
    }


@router.get("/v1.2/products/{product_id}/draft")
def product_v12_text_draft(
    product_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    """Assemble a non-invented v1.2 draft from confirmed FACT and approved copy."""
    product = db.scalar(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    if product is None:
        raise HTTPException(404, detail="product not found")
    profile = db.scalar(
        select(ProductRegistrationProfile).where(
            ProductRegistrationProfile.product_id == product_id,
            ProductRegistrationProfile.tenant_id == tenant_id,
        )
    )
    skus = list(
        db.scalars(
            select(ProductSKU).where(
                ProductSKU.product_id == product_id,
                ProductSKU.tenant_id == tenant_id,
            ).order_by(ProductSKU.created_at)
        ).all()
    )
    copies = list(
        db.scalars(
            select(ContentCopyAsset).where(
                ContentCopyAsset.product_id == product_id,
                ContentCopyAsset.tenant_id == tenant_id,
                ContentCopyAsset.status == "approved",
            ).order_by(ContentCopyAsset.updated_at.desc())
        ).all()
    )
    latest_copy: dict[str, str] = {}
    for row in copies:
        latest_copy.setdefault(row.slot_key, row.content)
    product_data = {
        "name": product.name,
        "product_code": product.product_code,
        "manufacturer": product.manufacturer,
        "country_of_origin": product.country_of_origin,
    }
    profile_data = None if profile is None else {
        "dimensions": profile.dimensions,
        "primary_material": profile.primary_material,
        "manufacturer": profile.manufacturer,
        "country_of_origin": profile.country_of_origin,
    }
    sku_data = [
        {
            "name": row.name,
            "option_value": row.option_value,
            "status": row.status,
        }
        for row in skus
    ]
    return assemble_canva_v12_text_draft(
        product=product_data,
        profile=profile_data,
        skus=sku_data,
        approved_copy=latest_copy,
    )


def _product_or_404(db: Session, *, tenant_id: str, product_id: str) -> Product:
    product = db.scalar(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    if product is None:
        raise HTTPException(404, detail="product not found")
    return product


def _product_image_assets(db: Session, *, tenant_id: str, product_id: str):
    return list(
        db.execute(
            select(ImageGeneratedAsset)
            .join(ImageGenerationJob, ImageGenerationJob.id == ImageGeneratedAsset.job_id)
            .where(
                ImageGeneratedAsset.tenant_id == tenant_id,
                ImageGenerationJob.tenant_id == tenant_id,
                ImageGenerationJob.product_id == product_id,
            )
            .order_by(
                ImageGeneratedAsset.approved_at.desc(),
                ImageGeneratedAsset.created_at.desc(),
            )
        ).scalars().all()
    )


def _image_asset_data(row: ImageGeneratedAsset) -> dict[str, object]:
    return {
        "id": row.id,
        "asset_stage": row.asset_stage,
        "status": row.status,
        "qa_status": row.qa_status,
        "approved_at": row.approved_at,
        "asset_uri": row.asset_uri,
        "asset_name": row.asset_name or row.filename or row.id,
        "role_code": row.role_code,
        "usage_code": row.usage_code,
        "asset_metadata": row.asset_metadata or {},
        "canva_asset_id": (row.asset_metadata or {}).get("canva_asset_id"),
    }


@router.get("/v1.2/products/{product_id}/images/draft")
def product_v12_image_draft(
    product_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    """Report exact 22-slot readiness using only approved, explicitly assigned images."""
    _product_or_404(db, tenant_id=tenant_id, product_id=product_id)
    assets = _product_image_assets(db, tenant_id=tenant_id, product_id=product_id)
    result = assemble_canva_v12_image_draft(_image_asset_data(row) for row in assets)
    result["eligible_assets"] = [
        _image_asset_data(row)
        for row in assets
        if is_approved_canva_image(_image_asset_data(row))
    ]
    return result


@router.post("/v1.2/products/{product_id}/images/assign")
def assign_product_v12_images(
    product_id: str,
    request: CanvaV12ImageAssignments,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    """Assign approved product images to exact Canva slots without inference."""
    _product_or_404(db, tenant_id=tenant_id, product_id=product_id)
    unknown = sorted(set(request.assignments) - set(CANVA_V12_IMAGE_FIELDS))
    unknown_clear = sorted(set(request.clear_slots) - set(CANVA_V12_IMAGE_FIELDS))
    if unknown:
        raise HTTPException(422, detail=f"unknown Canva image fields: {','.join(unknown)}")
    if unknown_clear:
        raise HTTPException(422, detail=f"unknown Canva image fields to clear: {','.join(unknown_clear)}")
    if set(request.assignments) & set(request.clear_slots):
        raise HTTPException(422, detail="a Canva image field cannot be assigned and cleared together")
    if len(set(request.assignments.values())) != len(request.assignments):
        raise HTTPException(422, detail="one image asset cannot fill multiple Canva image fields")

    assets = _product_image_assets(db, tenant_id=tenant_id, product_id=product_id)
    by_id = {row.id: row for row in assets}
    missing_ids = sorted(set(request.assignments.values()) - set(by_id))
    if missing_ids:
        raise HTTPException(422, detail=f"image asset not found for product: {','.join(missing_ids)}")
    for slot, asset_id in request.assignments.items():
        row = by_id[asset_id]
        if not is_approved_canva_image(_image_asset_data(row)):
            raise HTTPException(409, detail=f"image asset is not final approved QA-pass: {asset_id}")

    assigned_ids = set(request.assignments.values())
    requested_slots = set(request.assignments) | set(request.clear_slots)
    for row in assets:
        metadata = dict(row.asset_metadata or {})
        current_slot = str(metadata.get(CANVA_V12_IMAGE_SLOT_METADATA_KEY) or "")
        if row.id in assigned_ids:
            slot = next(name for name, asset_id in request.assignments.items() if asset_id == row.id)
            metadata[CANVA_V12_IMAGE_SLOT_METADATA_KEY] = slot
            row.asset_metadata = metadata
        elif current_slot in requested_slots:
            metadata.pop(CANVA_V12_IMAGE_SLOT_METADATA_KEY, None)
            row.asset_metadata = metadata

    db.commit()
    refreshed = _product_image_assets(db, tenant_id=tenant_id, product_id=product_id)
    result = assemble_canva_v12_image_draft(_image_asset_data(row) for row in refreshed)
    result["eligible_assets"] = [
        _image_asset_data(row)
        for row in refreshed
        if is_approved_canva_image(_image_asset_data(row))
    ]
    return result


@router.get("/v1.2/products/{product_id}/autofill/readiness")
def product_v12_autofill_readiness(
    product_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    """Prepare the 94-field package without performing an external Canva write."""
    text_draft = product_v12_text_draft(product_id, tenant_id=tenant_id, db=db)
    image_draft = product_v12_image_draft(product_id, tenant_id=tenant_id, db=db)
    package = build_canva_v12_execution_package(
        text_draft=text_draft,
        image_draft=image_draft,
    )
    connection = db.scalar(
        select(CanvaConnection).where(CanvaConnection.tenant_id == tenant_id)
    )
    connected = bool(connection and connection.status == "connected")
    package["canva_connection"] = {
        "configured": bool(settings.canva_client_id and settings.canva_client_secret),
        "connected": connected,
        "reason": None if connected else "server_side_canva_oauth_not_connected",
        "external_execution_allowed": connected and package["execution_ready"],
    }
    return package


@router.post("/v1.2/products/{product_id}/images/upload-to-canva")
def upload_product_v12_images_to_canva(
    product_id: str,
    request: CanvaV12CanvaUploadRequest,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    """Start approved Canva uploads only after an explicit execution approval."""
    if not request.execution_approved:
        raise HTTPException(409, detail="explicit Canva upload approval is required")
    image_draft = product_v12_image_draft(product_id, tenant_id=tenant_id, db=db)
    if not image_draft["ready"]:
        raise HTTPException(409, detail=f"Canva image slots are incomplete: {image_draft['matched']}")
    connection = db.scalar(select(CanvaConnection).where(CanvaConnection.tenant_id == tenant_id))
    if connection is None:
        raise HTTPException(409, detail="Canva is not connected")
    token = active_token(connection, db)
    assets = {row.id: row for row in _product_image_assets(db, tenant_id=tenant_id, product_id=product_id)}
    started = []
    skipped = []
    for slot, asset_id in image_draft["image_fields"].items():
        row = assets[asset_id]
        metadata = dict(row.asset_metadata or {})
        if metadata.get("canva_asset_id"):
            skipped.append(slot)
            continue
        if metadata.get("canva_upload_job_id") and metadata.get("canva_upload_status") == "in_progress":
            skipped.append(slot)
            continue
        try:
            path = resolve_media_uri(row.asset_uri)
            payload = canva_connect.create_asset_upload(
                token, content=path.read_bytes(), name=row.filename or row.asset_name or row.id
            )
        except (ImageStudioError, OSError) as exc:
            raise HTTPException(409, detail=f"image content unavailable for {slot}") from exc
        job = payload.get("job") or {}
        if not job.get("id"):
            raise HTTPException(502, detail=f"Canva upload did not return a job ID for {slot}")
        metadata["canva_upload_job_id"] = job["id"]
        metadata["canva_upload_status"] = job.get("status", "in_progress")
        row.asset_metadata = metadata
        started.append(slot)
    db.commit()
    return {"started_count": len(started), "started_fields": started, "skipped_fields": skipped, "status": "in_progress" if started else "unchanged"}


@router.post("/v1.2/products/{product_id}/images/sync-canva-uploads")
def sync_product_v12_canva_uploads(
    product_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    """Poll existing upload jobs and store returned Canva asset IDs."""
    _product_or_404(db, tenant_id=tenant_id, product_id=product_id)
    connection = db.scalar(select(CanvaConnection).where(CanvaConnection.tenant_id == tenant_id))
    if connection is None:
        raise HTTPException(409, detail="Canva is not connected")
    token = active_token(connection, db)
    completed, failed, pending = [], [], []
    for row in _product_image_assets(db, tenant_id=tenant_id, product_id=product_id):
        metadata = dict(row.asset_metadata or {})
        job_id = metadata.get("canva_upload_job_id")
        if not job_id or metadata.get("canva_asset_id"):
            continue
        payload = canva_connect.get_asset_upload(token, job_id)
        job = payload.get("job") or {}
        status = job.get("status", "in_progress")
        metadata["canva_upload_status"] = status
        if status == "success" and (job.get("asset") or {}).get("id"):
            metadata["canva_asset_id"] = job["asset"]["id"]
            completed.append(row.id)
        elif status == "failed":
            metadata["canva_upload_error"] = (job.get("error") or {}).get("message", "upload failed")
            failed.append(row.id)
        else:
            pending.append(row.id)
        row.asset_metadata = metadata
    db.commit()
    return {"completed_count": len(completed), "failed_count": len(failed), "pending_count": len(pending), "completed_asset_ids": completed}


def _dataset_definition(payload: dict) -> dict:
    value = payload.get("dataset") or payload.get("data") or {}
    return value if isinstance(value, dict) else {}


@router.post("/v1.2/products/{product_id}/autofill/start")
def start_product_v12_autofill(
    product_id: str,
    request: CanvaV12AutofillRequest,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    if not request.execution_approved:
        raise HTTPException(409, detail="explicit Canva Autofill approval is required")
    text_draft = product_v12_text_draft(product_id, tenant_id=tenant_id, db=db)
    image_draft = product_v12_image_draft(product_id, tenant_id=tenant_id, db=db)
    package = build_canva_v12_execution_package(text_draft=text_draft, image_draft=image_draft)
    if not package["execution_ready"]:
        raise HTTPException(409, detail=f"Canva Autofill is not ready: {','.join(package['blockers'])}")
    connection = db.scalar(select(CanvaConnection).where(CanvaConnection.tenant_id == tenant_id))
    if connection is None:
        raise HTTPException(409, detail="Canva is not connected")
    token = active_token(connection, db)
    dataset = _dataset_definition(canva_connect.get_brand_template_dataset(token, package["brand_template_id"]))
    expected = {name: value["type"] for name, value in package["autofill_data"].items()}
    actual = {name: str(value.get("type")) for name, value in dataset.items() if isinstance(value, dict)}
    if expected != actual:
        missing = sorted(set(expected) - set(actual))
        unknown = sorted(set(actual) - set(expected))
        wrong_type = sorted(name for name in set(expected) & set(actual) if expected[name] != actual[name])
        raise HTTPException(409, detail={"message": "Canva template dataset changed", "missing": missing, "unknown": unknown, "wrong_type": wrong_type})
    product = _product_or_404(db, tenant_id=tenant_id, product_id=product_id)
    result = canva_connect.create_autofill(token, template_id=package["brand_template_id"], data=package["autofill_data"], title=f"{product.name} 상세페이지 v1.2")
    job = result.get("job") or {}
    if not job.get("id"):
        raise HTTPException(502, detail="Canva Autofill did not return a job ID")
    row = CanvaAutofillRun(tenant_id=tenant_id, product_id=product_id, brand_template_id=package["brand_template_id"], canva_job_id=job["id"], status=job.get("status", "in_progress"))
    db.add(row); db.commit(); db.refresh(row)
    return {"run_id": row.id, "canva_job_id": row.canva_job_id, "status": row.status}


@router.post("/v1.2/autofill-runs/{run_id}/sync")
def sync_v12_autofill_run(
    run_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    row = db.scalar(select(CanvaAutofillRun).where(CanvaAutofillRun.id == run_id, CanvaAutofillRun.tenant_id == tenant_id))
    if row is None:
        raise HTTPException(404, detail="Canva Autofill run not found")
    connection = db.scalar(select(CanvaConnection).where(CanvaConnection.tenant_id == tenant_id))
    if connection is None:
        raise HTTPException(409, detail="Canva is not connected")
    payload = canva_connect.get_autofill(active_token(connection, db), row.canva_job_id)
    job = payload.get("job") or {}
    row.status = job.get("status", row.status)
    if row.status == "success":
        design = job.get("design") or {}
        row.design_id = design.get("id")
        row.design_url = design.get("url") or design.get("edit_url") or design.get("view_url")
    elif row.status == "failed":
        row.error_json = job.get("error") or {"message": "Canva Autofill failed"}
    db.commit()
    return {"run_id": row.id, "status": row.status, "design_id": row.design_id, "design_url": row.design_url, "error": row.error_json}


def _job_or_404(db: Session, *, tenant_id: str, job_id: str) -> DetailPageJob:
    row = db.scalar(
        select(DetailPageJob).where(
            DetailPageJob.id == job_id,
            DetailPageJob.tenant_id == tenant_id,
        )
    )
    if row is None:
        raise HTTPException(404, detail="detail-page job not found")
    return row


@router.post("/jobs/{job_id}/export")
def controlled_canva_export(
    job_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    """Create an approved export and attach the deterministic Canva execution contract."""
    job = _job_or_404(db, tenant_id=tenant_id, job_id=job_id)
    version = current_version(db, job)
    if version is None:
        raise HTTPException(409, detail="detail-page version not prepared")
    try:
        row = export_package(db, job=job, version=version)
    except ValueError as exc:
        raise HTTPException(409, detail=str(exc)) from exc

    payload = dict(row.payload_json or {})
    payload["canva_controlled_contract"] = build_controlled_canva_contract(
        export_payload=payload
    )
    payload["schema_version"] = "detail-page-export.v2"
    row.payload_json = payload
    row.export_type = "canva_controlled_package"
    db.commit()
    db.refresh(row)
    return {
        "export_id": row.id,
        "status": row.status,
        "export_type": row.export_type,
        "payload": row.payload_json,
    }


@router.get("/exports/{export_id}")
def get_controlled_canva_export(
    export_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    row = db.scalar(
        select(DetailPageExport).where(
            DetailPageExport.id == export_id,
            DetailPageExport.tenant_id == tenant_id,
        )
    )
    if row is None:
        raise HTTPException(404, detail="detail-page export not found")
    payload = dict(row.payload_json or {})
    if "canva_controlled_contract" not in payload:
        payload["canva_controlled_contract"] = build_controlled_canva_contract(
            export_payload=payload
        )
    return {
        "export_id": row.id,
        "status": row.status,
        "export_type": row.export_type,
        "payload": payload,
    }
