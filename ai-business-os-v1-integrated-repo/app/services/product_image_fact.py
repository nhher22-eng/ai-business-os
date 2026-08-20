from __future__ import annotations

import base64
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import ImageReferenceAsset, Product
from app.db.product_image_fact import ProductImageFact
from app.db.product_registration import ProductRegistrationProfile
from app.services.image_studio import ImageStudioError, media_root, resolve_media_uri


SLOT_TYPES = (
    "RIGHT_45",
    "LEFT_45",
    "FRONT",
    "LEFT",
    "RIGHT",
    "TOP",
    "BOTTOM",
    "DETAIL",
    "LIFESTYLE",
    "UNASSIGNED",
)

SLOT_LABELS = {
    "RIGHT_45": "45도 우측",
    "LEFT_45": "45도 좌측",
    "FRONT": "정면",
    "LEFT": "좌측",
    "RIGHT": "우측",
    "TOP": "상부",
    "BOTTOM": "하부",
    "DETAIL": "부분상세",
    "LIFESTYLE": "라이프스타일",
    "UNASSIGNED": "미분류",
}

REQUIRED_SLOTS = {"RIGHT_45", "FRONT"}
PRIMARY_SLOT = "RIGHT_45"


class ProductImageFactError(RuntimeError):
    pass


def utcnow():
    return datetime.now(timezone.utc)


def slot_policy(slot_type: str) -> dict[str, Any]:
    if slot_type not in SLOT_TYPES:
        raise ProductImageFactError(f"unsupported slot_type: {slot_type}")
    lifestyle = slot_type == "LIFESTYLE"
    return {
        "slot_type": slot_type,
        "label": SLOT_LABELS[slot_type],
        "required": slot_type in REQUIRED_SLOTS,
        "primary": slot_type == PRIMARY_SLOT,
        "remove_background": not lifestyle and slot_type != "UNASSIGNED",
        "keep_background": lifestyle,
        "raw_retention_policy": "keep" if lifestyle else "delete_on_confirm",
    }


def slot_definitions() -> list[dict[str, Any]]:
    return [slot_policy(slot) for slot in SLOT_TYPES]


def _safe_name(name: str) -> str:
    name = Path(name).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-")
    return cleaned or f"image-{uuid.uuid4().hex[:8]}.bin"


def _store_bytes(*, product_id: str, folder: str, filename: str, content: bytes) -> str:
    root = media_root()
    target_dir = root / "product-image-facts" / product_id / folder
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{uuid.uuid4().hex[:10]}-{_safe_name(filename)}"
        path.write_bytes(content)
    except OSError as exc:
        raise ProductImageFactError("상품 이미지 FACT 저장소에 쓸 수 없습니다.") from exc
    return f"media://{path.relative_to(root).as_posix()}"


def save_raw_capture(*, product_id: str, filename: str, content: bytes) -> str:
    return _store_bytes(
        product_id=product_id,
        folder="raw",
        filename=filename,
        content=content,
    )


def save_fact_image(*, product_id: str, filename: str, content: bytes) -> str:
    stem = Path(filename).stem or "product"
    return _store_bytes(
        product_id=product_id,
        folder="facts",
        filename=f"{stem}.png",
        content=content,
    )


def delete_managed_media(uri: str | None) -> bool:
    if not uri:
        return False
    try:
        path = resolve_media_uri(uri)
        path.unlink(missing_ok=True)
        return True
    except (ImageStudioError, OSError):
        return False


def _extract_response_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                return content["text"]
    raise ProductImageFactError("vision model returned no readable output")


def classify_slot(
    *,
    filename: str,
    mime_type: str | None,
    content: bytes,
) -> tuple[str, str, float | None]:
    """Classify viewpoint/use only. Never infer product specifications."""
    if not settings.openai_api_key:
        return "UNASSIGNED", "manual_required", None

    media_type = mime_type or "image/jpeg"
    encoded = base64.b64encode(content).decode("ascii")
    allowed = [slot for slot in SLOT_TYPES if slot != "UNASSIGNED"]
    model = os.getenv("OPENAI_VISION_MODEL", os.getenv("OPENAI_TEXT_MODEL", "gpt-4.1-mini"))
    prompt = (
        "Classify only the photographic viewpoint/use of this commerce product photo. "
        "Do not infer any product facts, dimensions, materials, parts, or performance. "
        f"Choose exactly one slot_type from {allowed}. "
        "RIGHT_45 means the product is viewed from the front-right diagonal; LEFT_45 front-left diagonal; "
        "FRONT straight front; LEFT/RIGHT straight side; TOP/BOTTOM straight above/below; "
        "DETAIL is a close-up of a part/detail; LIFESTYLE shows the real product in a use/environment scene. "
        "Return JSON only: {\"slot_type\":\"...\",\"confidence\":0.0}."
    )
    try:
        with httpx.Client(timeout=45.0) as client:
            response = client.post(
                f"{settings.openai_api_base.rstrip('/')}/responses",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "input": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": prompt},
                                {
                                    "type": "input_image",
                                    "image_url": f"data:{media_type};base64,{encoded}",
                                },
                            ],
                        }
                    ],
                },
            )
        response.raise_for_status()
        text = _extract_response_text(response.json()).strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].lstrip()
        payload = json.loads(text)
        slot = str(payload.get("slot_type") or "UNASSIGNED").upper()
        if slot not in SLOT_TYPES or slot == "UNASSIGNED":
            return "UNASSIGNED", "manual_required", None
        confidence_raw = payload.get("confidence")
        confidence = None
        if confidence_raw is not None:
            confidence = max(0.0, min(1.0, float(confidence_raw)))
        return slot, "vision_ai", confidence
    except Exception:
        return "UNASSIGNED", "manual_required", None


def remove_background(content: bytes) -> bytes:
    """Segment background without generatively redrawing product pixels."""
    try:
        from rembg import remove
    except ImportError as exc:
        raise ProductImageFactError(
            "배경제거 엔진(rembg)이 설치되어 있지 않습니다."
        ) from exc
    try:
        result = remove(content)
    except Exception as exc:
        raise ProductImageFactError("배경제거 처리에 실패했습니다.") from exc
    if not result:
        raise ProductImageFactError("배경제거 결과가 비어 있습니다.")
    return bytes(result)


def apply_slot_policy(row: ProductImageFact, slot_type: str) -> None:
    policy = slot_policy(slot_type)
    row.slot_type = slot_type
    row.is_required = bool(policy["required"])
    row.is_primary = bool(policy["primary"])
    row.keep_background = bool(policy["keep_background"])
    row.raw_retention_policy = str(policy["raw_retention_policy"])


def process_row(row: ProductImageFact) -> ProductImageFact:
    if not row.raw_asset_uri:
        raise ProductImageFactError("임시 촬영 원본이 없습니다.")
    if row.slot_type == "UNASSIGNED":
        row.status = "needs_review"
        return row

    if row.slot_type == "LIFESTYLE":
        row.fact_asset_uri = row.raw_asset_uri
        row.background_removed = False
        row.keep_background = True
        row.raw_retention_policy = "keep"
        row.status = "processed"
        return row

    try:
        raw_path = resolve_media_uri(row.raw_asset_uri)
        content = raw_path.read_bytes()
    except (ImageStudioError, OSError) as exc:
        raise ProductImageFactError("임시 촬영 원본을 읽을 수 없습니다.") from exc

    cutout = remove_background(content)
    row.fact_asset_uri = save_fact_image(
        product_id=row.product_id,
        filename=row.original_filename or "product.png",
        content=cutout,
    )
    row.background_removed = True
    row.keep_background = False
    row.raw_retention_policy = "delete_on_confirm"
    row.status = "processed"
    return row


def _next_slot_index(db: Session, *, tenant_id: str, product_id: str, slot_type: str) -> int:
    rows = db.scalars(
        select(ProductImageFact).where(
            ProductImageFact.tenant_id == tenant_id,
            ProductImageFact.product_id == product_id,
            ProductImageFact.slot_type == slot_type,
        )
    ).all()
    return max((row.slot_index for row in rows), default=0) + 1


def create_upload_row(
    db: Session,
    *,
    tenant_id: str,
    product_id: str,
    filename: str,
    mime_type: str | None,
    content: bytes,
    slot_hint: str | None = None,
    auto_process: bool = True,
) -> ProductImageFact:
    if slot_hint and slot_hint not in SLOT_TYPES:
        raise ProductImageFactError("지원하지 않는 이미지 항목입니다.")
    raw_uri = save_raw_capture(
        product_id=product_id,
        filename=filename,
        content=content,
    )
    if slot_hint:
        slot, source, confidence = slot_hint, "user_hint", 1.0
    else:
        slot, source, confidence = classify_slot(
            filename=filename,
            mime_type=mime_type,
            content=content,
        )

    row = ProductImageFact(
        tenant_id=tenant_id,
        product_id=product_id,
        slot_type=slot,
        slot_index=_next_slot_index(
            db, tenant_id=tenant_id, product_id=product_id, slot_type=slot
        ),
        status="uploaded",
        source_kind="temporary_capture",
        raw_asset_uri=raw_uri,
        original_filename=filename,
        mime_type=mime_type,
        classification_source=source,
        classification_confidence=confidence,
    )
    apply_slot_policy(row, slot)
    db.add(row)
    db.flush()
    if auto_process and slot != "UNASSIGNED":
        process_row(row)
    elif slot == "UNASSIGNED":
        row.status = "needs_review"
    db.flush()
    return row


def set_slot_and_process(
    row: ProductImageFact,
    *,
    slot_type: str,
    slot_index: int | None = None,
) -> ProductImageFact:
    if row.status == "confirmed":
        raise ProductImageFactError("확정된 이미지 FACT는 등록 화면에서 재분류할 수 없습니다.")
    old_fact = row.fact_asset_uri
    old_raw = row.raw_asset_uri
    apply_slot_policy(row, slot_type)
    if slot_index is not None:
        row.slot_index = max(1, int(slot_index))
    row.classification_source = "user"
    row.classification_confidence = 1.0

    if old_fact and old_fact != old_raw:
        delete_managed_media(old_fact)
        row.fact_asset_uri = None
    return process_row(row)


def _get_profile(db: Session, *, tenant_id: str, product_id: str) -> ProductRegistrationProfile:
    profile = db.scalar(
        select(ProductRegistrationProfile).where(
            ProductRegistrationProfile.tenant_id == tenant_id,
            ProductRegistrationProfile.product_id == product_id,
        )
    )
    if profile is None:
        profile = ProductRegistrationProfile(
            tenant_id=tenant_id,
            product_id=product_id,
            additional_image_asset_ids=[],
        )
        db.add(profile)
        db.flush()
    return profile


def confirm_image_fact(
    db: Session,
    *,
    row: ProductImageFact,
    confirmed_by: str | None = None,
) -> ProductImageFact:
    if row.slot_type == "UNASSIGNED":
        raise ProductImageFactError("이미지 항목을 먼저 지정해 주세요.")
    if not row.fact_asset_uri:
        raise ProductImageFactError("확정할 처리 이미지가 없습니다.")

    profile = _get_profile(db, tenant_id=row.tenant_id, product_id=row.product_id)
    reference = None
    if row.reference_asset_id:
        reference = db.scalar(
            select(ImageReferenceAsset).where(ImageReferenceAsset.id == row.reference_asset_id)
        )
    if reference is None:
        reference = ImageReferenceAsset(
            tenant_id=row.tenant_id,
            product_id=row.product_id,
            job_id=None,
            asset_role="PRODUCT_REFERENCE",
            asset_uri=row.fact_asset_uri,
            original_filename=row.original_filename,
            mime_type=(row.mime_type if row.slot_type == "LIFESTYLE" else "image/png"),
            internal_reference_only=False,
            lock_level="hard_lock",
            sort_order=0 if row.slot_type == PRIMARY_SLOT else row.slot_index,
        )
        db.add(reference)
        db.flush()
        row.reference_asset_id = reference.id

    additional = list(profile.additional_image_asset_ids or [])
    if row.slot_type == PRIMARY_SLOT:
        profile.primary_image_asset_id = reference.id
        if reference.id in additional:
            additional.remove(reference.id)
    elif reference.id not in additional:
        additional.append(reference.id)
    profile.additional_image_asset_ids = additional

    row.status = "confirmed"
    row.confirmed_by = confirmed_by or "dashboard-user"
    row.confirmed_at = utcnow()

    if (
        row.raw_retention_policy == "delete_on_confirm"
        and row.raw_asset_uri
        and row.raw_asset_uri != row.fact_asset_uri
    ):
        if delete_managed_media(row.raw_asset_uri):
            row.raw_asset_uri = None
            row.raw_deleted_at = utcnow()
    db.flush()
    return row


def readiness(db: Session, *, tenant_id: str, product_id: str) -> dict[str, Any]:
    rows = db.scalars(
        select(ProductImageFact).where(
            ProductImageFact.tenant_id == tenant_id,
            ProductImageFact.product_id == product_id,
            ProductImageFact.status == "confirmed",
        )
    ).all()
    confirmed = {row.slot_type for row in rows}
    missing = [slot for slot in ("RIGHT_45", "FRONT") if slot not in confirmed]
    return {
        "ready": not missing,
        "required_slots": ["RIGHT_45", "FRONT"],
        "missing_slots": missing,
        "missing_labels": [SLOT_LABELS[slot] for slot in missing],
        "confirmed_count": len(rows),
    }


def delete_unconfirmed_row(row: ProductImageFact) -> None:
    if row.status == "confirmed":
        raise ProductImageFactError("확정된 이미지 FACT는 이 화면에서 삭제할 수 없습니다.")
    raw_uri = row.raw_asset_uri
    fact_uri = row.fact_asset_uri
    delete_managed_media(raw_uri)
    if fact_uri and fact_uri != raw_uri:
        delete_managed_media(fact_uri)
