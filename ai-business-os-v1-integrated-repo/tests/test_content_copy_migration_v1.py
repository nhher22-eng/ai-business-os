from pathlib import Path


def test_content_copy_migration_follows_current_head():
    text = Path("migrations/versions/0012_content_copy_assets.py").read_text()
    assert 'revision = "0012_content_copy"' in text
    assert 'down_revision = "0011_detail_templates"' in text
    assert '"content_copy_assets"' in text
    assert '"source_fact_keys"' in text
    assert '"approved_at"' in text
