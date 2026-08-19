from pathlib import Path

from app.db.models import ImageGenerationJob
from app.services.image_studio import output_size


def job(ratio: str, width=None, height=None):
    return ImageGenerationJob(
        tenant_id="t",
        workspace_id="w",
        product_id="p",
        image_type="LIFESTYLE",
        style_preset="LIFESTYLE_PHOTO",
        usage_context="DETAIL_PAGE",
        aspect_ratio=ratio,
        custom_width=width,
        custom_height=height,
    )


def test_camera_ratio_sizes_are_stable_between_preview_and_final():
    assert output_size(job("1:1"), "preview") == (1024, 1024)
    assert output_size(job("4:3"), "preview") == (1024, 768)
    assert output_size(job("3:4"), "preview") == (768, 1024)
    assert output_size(job("16:9"), "preview") == (1280, 720)
    assert output_size(job("9:16"), "preview") == (720, 1280)
    assert output_size(job("4:3"), "final") == (2048, 1536)


def test_custom_size_rounds_to_provider_multiple_of_16():
    width, height = output_size(job("CUSTOM", 1211, 905), "preview")
    assert width % 16 == 0
    assert height % 16 == 0


def test_original_png_ratio_is_preserved(tmp_path: Path):
    # Minimal 2:1 PNG header; image contents are not decoded for ratio extraction.
    png = tmp_path / "ref.png"
    png.write_bytes(
        b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + (1600).to_bytes(4, "big") + (800).to_bytes(4, "big")
    )
    width, height = output_size(job("ORIGINAL"), "preview", reference_path=png)
    assert abs((width / height) - 2.0) < 0.03
