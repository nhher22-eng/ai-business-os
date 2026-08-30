from pathlib import Path


SOURCE = Path("app/services/detail_page_studio.py").read_text(encoding="utf-8")


def test_required_sections_keep_core_and_review_placeholders():
    block = SOURCE.split("REQUIRED_SECTIONS = {", 1)[1].split("}", 1)[0]

    for required in (
        "HERO",
        "FEATURE",
        "SPEC",
    ):
        assert f'"{required}"' in block

    for optional in (
        "PROBLEM",
        "LIFESTYLE",
        "OPTION_COMPARE",
        "COMPONENTS",
        "INSTALLATION",
        "FAQ",
    ):
        assert f'"{optional}"' not in block


def test_lifestyle_does_not_reuse_hero_image():
    assert '_approved_image(db, tenant_id, product_id, ["LIFESTYLE"])' in SOURCE
    assert '_approved_image(db, tenant_id, product_id, ["LIFESTYLE", "HERO"])' not in SOURCE

    lifestyle = SOURCE.split('"LIFESTYLE": {', 1)[1].split('"FEATURE": {', 1)[0]
    assert '"product_image_fact_id": None' in lifestyle
    assert '"asset_status": "ready" if lifestyle_asset_id else "image_required"' in lifestyle
    assert "hero_fact_id if not lifestyle_asset_id" not in lifestyle
