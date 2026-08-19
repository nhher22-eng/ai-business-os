import importlib.util
from pathlib import Path


def load(name):
    path = Path('migrations/versions') / f'{name}.py'
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_product_registration_migration_chain():
    m6 = load('0006_detail_page_studio')
    m7 = load('0007_product_registration')
    assert m6.down_revision == '0005_image_studio'
    assert m7.down_revision == '0006_detail_page_studio'
