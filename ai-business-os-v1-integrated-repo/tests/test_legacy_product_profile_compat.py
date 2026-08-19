from pathlib import Path


def test_product_registration_auto_creates_missing_legacy_profile():
    src = Path('app/api/product_registration.py').read_text()
    assert 'Legacy products created before Product Registration' in src
    assert 'additional_image_asset_ids=[]' in src
    assert 'facts_confirmed' not in src[src.index('Legacy products created before Product Registration'):src.index('def _apply_facts')]
