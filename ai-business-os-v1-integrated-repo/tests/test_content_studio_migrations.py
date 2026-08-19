import importlib.util
from pathlib import Path


def load(name):
    path = Path('migrations/versions') / f'{name}.py'
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_content_studio_migration_chain():
    m5 = load('0005_image_studio')
    m6 = load('0006_detail_page_studio')
    assert m5.down_revision == '0004_product_detail'
    assert m6.down_revision == '0005_image_studio'
