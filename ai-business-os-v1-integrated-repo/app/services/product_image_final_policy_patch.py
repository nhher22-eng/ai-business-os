from __future__ import annotations

from io import BytesIO

from PIL import Image

import app.api.product_image_facts as image_api
import app.services.product_image_fact as image_service


FULL_PRODUCT_SLOTS = {
    "RIGHT_45",
    "LEFT_45",
    "FRONT",
    "LEFT",
    "RIGHT",
    "TOP",
    "BOTTOM",
}
CANVAS_SIZE = 1000
OBJECT_MAX_SIZE = 900

_ORIGINAL_CONFIRM = image_service.confirm_image_fact


def _standard_fit_png(cutout: bytes) -> bytes:
    """Place the segmented product on a 1000x1000 white canvas.

    The object is scaled proportionally to fit inside a 900x900 safe area and
    centered. No generative redraw or product-pixel synthesis is performed.
    """
    try:
        source = Image.open(BytesIO(cutout)).convert("RGBA")
    except Exception as exc:
        raise image_service.ProductImageFactError("누끼 결과를 표준 Fit 이미지로 변환하지 못했습니다.") from exc

    alpha = source.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        raise image_service.ProductImageFactError("누끼 결과에서 상품 영역을 찾지 못했습니다.")

    product = source.crop(bbox)
    product.thumbnail((OBJECT_MAX_SIZE, OBJECT_MAX_SIZE), Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (255, 255, 255, 255))
    x = (CANVAS_SIZE - product.width) // 2
    y = (CANVAS_SIZE - product.height) // 2
    canvas.alpha_composite(product, (x, y))

    output = BytesIO()
    canvas.convert("RGB").save(output, format="PNG", optimize=True)
    return output.getvalue()


def _slot_policy(slot_type: str):
    if slot_type not in image_service.SLOT_TYPES:
        raise image_service.ProductImageFactError(f"unsupported slot_type: {slot_type}")

    full_product = slot_type in FULL_PRODUCT_SLOTS
    final_as_uploaded = slot_type in {"DETAIL", "LIFESTYLE"}
    return {
        "slot_type": slot_type,
        "label": image_service.SLOT_LABELS[slot_type],
        "required": slot_type in image_service.REQUIRED_SLOTS,
        "primary": slot_type == image_service.PRIMARY_SLOT,
        "remove_background": full_product,
        "keep_background": final_as_uploaded,
        "raw_retention_policy": "delete_on_confirm" if full_product else "final_only",
    }


def _process_row(row):
    if not row.raw_asset_uri:
        raise image_service.ProductImageFactError("임시 촬영 원본이 없습니다.")
    if row.slot_type == "UNASSIGNED":
        row.status = "needs_review"
        return row

    if row.slot_type in {"DETAIL", "LIFESTYLE"}:
        # The uploaded image is already the final usable image. We do not create
        # a duplicate intermediate file; raw_asset_uri is cleared on confirmation.
        row.fact_asset_uri = row.raw_asset_uri
        row.background_removed = False
        row.keep_background = True
        row.raw_retention_policy = "final_only"
        row.status = "processed"
        return row

    try:
        raw_path = image_service.resolve_media_uri(row.raw_asset_uri)
        content = raw_path.read_bytes()
    except (image_service.ImageStudioError, OSError) as exc:
        raise image_service.ProductImageFactError("임시 촬영 원본을 읽을 수 없습니다.") from exc

    cutout = image_service.remove_background(content)
    fitted = _standard_fit_png(cutout)
    row.fact_asset_uri = image_service.save_fact_image(
        product_id=row.product_id,
        filename=row.original_filename or "product.png",
        content=fitted,
    )
    row.background_removed = True
    row.keep_background = False
    row.raw_retention_policy = "delete_on_confirm"
    row.status = "processed"
    return row


def _confirm_image_fact(db, *, row, confirmed_by=None):
    raw_before = row.raw_asset_uri
    fact_before = row.fact_asset_uri
    result = _ORIGINAL_CONFIRM(db, row=row, confirmed_by=confirmed_by)

    # DETAIL/LIFESTYLE use the same managed file as both upload and final FACT.
    # After confirmation we clear the temporary/raw pointer without deleting the
    # final file, so the system exposes and retains one canonical asset only.
    if raw_before and fact_before and raw_before == fact_before:
        row.raw_asset_uri = None
        row.raw_deleted_at = image_service.utcnow()
        row.raw_retention_policy = "final_only"
        db.flush()
    return result


def install_product_image_final_policy_patch() -> None:
    image_service.slot_policy = _slot_policy
    image_service.process_row = _process_row
    image_service.confirm_image_fact = _confirm_image_fact

    # product_image_facts.py imports these symbols directly, so patch the API
    # module references too. Helpers such as create_upload_row/set_slot_and_process
    # resolve the service globals dynamically and therefore inherit this policy.
    image_api.process_row = _process_row
    image_api.confirm_image_fact = _confirm_image_fact
