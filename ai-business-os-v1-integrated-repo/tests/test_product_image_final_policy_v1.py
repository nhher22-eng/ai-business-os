from io import BytesIO

from PIL import Image

from app.services.product_image_final_policy_patch import (
    CANVAS_SIZE,
    OBJECT_MAX_SIZE,
    _slot_policy,
    _standard_fit_png,
)


def _transparent_product_png(width=420, height=180):
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    for x in range(20, width - 20):
        for y in range(10, height - 10):
            image.putpixel((x, y), (20, 80, 120, 255))
    out = BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def test_full_product_policy_requires_cutout_and_raw_deletion():
    policy = _slot_policy("RIGHT_45")
    assert policy["remove_background"] is True
    assert policy["keep_background"] is False
    assert policy["raw_retention_policy"] == "delete_on_confirm"


def test_detail_and_lifestyle_are_final_only_without_forced_cutout():
    for slot in ("DETAIL", "LIFESTYLE"):
        policy = _slot_policy(slot)
        assert policy["remove_background"] is False
        assert policy["keep_background"] is True
        assert policy["raw_retention_policy"] == "final_only"


def test_standard_fit_is_square_white_and_object_stays_inside_safe_area():
    result = _standard_fit_png(_transparent_product_png())
    image = Image.open(BytesIO(result)).convert("RGB")

    assert image.size == (CANVAS_SIZE, CANVAS_SIZE)
    assert image.getpixel((0, 0)) == (255, 255, 255)

    background = Image.new("RGB", image.size, (255, 255, 255))
    diff = Image.new("L", image.size, 0)
    for x in range(image.width):
        for y in range(image.height):
            if image.getpixel((x, y)) != background.getpixel((x, y)):
                diff.putpixel((x, y), 255)
    bbox = diff.getbbox()
    assert bbox is not None
    assert bbox[2] - bbox[0] <= OBJECT_MAX_SIZE
    assert bbox[3] - bbox[1] <= OBJECT_MAX_SIZE

    cx = (bbox[0] + bbox[2]) / 2
    cy = (bbox[1] + bbox[3]) / 2
    assert abs(cx - CANVAS_SIZE / 2) <= 1
    assert abs(cy - CANVAS_SIZE / 2) <= 1
