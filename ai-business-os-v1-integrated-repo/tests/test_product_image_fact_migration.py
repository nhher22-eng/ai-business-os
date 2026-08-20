import importlib.util
from pathlib import Path


def test_product_image_fact_migration_chain():
    path = Path(__file__).parents[1] / "migrations" / "versions" / "0010_product_image_fact.py"
    spec = importlib.util.spec_from_file_location("migration_0010", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    assert module.revision == "0010_product_image_fact"
    assert module.down_revision == "0009_product_operations"
