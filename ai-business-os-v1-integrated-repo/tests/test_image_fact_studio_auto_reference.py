from pathlib import Path


SERVICE = Path("app/services/image_studio.py").read_text(encoding="utf-8")
API = Path("app/api/images.py").read_text(encoding="utf-8")


def test_confirmed_product_image_facts_become_hard_lock_references():
    assert "def ensure_product_image_fact_references(" in SERVICE
    assert 'ProductImageFact.status == "confirmed"' in SERVICE
    assert "ProductImageFact.fact_asset_uri.is_not(None)" in SERVICE
    assert 'asset_role="PRODUCT_REFERENCE"' in SERVICE
    assert 'lock_level="hard_lock"' in SERVICE


def test_product_fact_file_is_reused_without_copying():
    block = SERVICE.split(
        "def ensure_product_image_fact_references(", 1
    )[1].split("def references_for_job", 1)[0]
    assert "asset_uri=fact.fact_asset_uri" in block
    assert "write_bytes" not in block
    assert "save_reference_upload" not in block


def test_existing_draft_is_backfilled_before_p0():
    prepare = SERVICE.split(
        "def prepare_job(", 1
    )[1].split("def _managed_reference_paths", 1)[0]
    assert "ensure_product_image_fact_references(db, job)" in prepare
    assert prepare.index(
        "ensure_product_image_fact_references(db, job)"
    ) < prepare.index("references_for_job(db, job)")


def test_new_job_is_synced_before_commit():
    assert "db.flush()\n    ensure_product_image_fact_references(db, row)" in API


def test_identical_draft_is_reused_instead_of_duplicated():
    assert "existing_draft = db.scalar(" in API
    assert 'ImageGenerationJob.status == "draft"' in API
    assert "return _job_payload(db, existing_draft)" in API
