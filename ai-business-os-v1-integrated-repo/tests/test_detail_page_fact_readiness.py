from app.services.detail_page_autogen import fact_readiness


def test_product_name_only_is_not_release_ready():
    snapshot = {
        "product": {"name": "분갈이 매트"},
        "detail": {
            "specification": None,
            "usage": None,
            "installation_method": None,
            "usage_conditions": None,
            "cautions": None,
        },
        "skus": [],
    }
    result = fact_readiness(snapshot)
    assert result["ready"] is False
    assert "product_detail_or_sku" in result["missing"]


def test_one_confirmed_detail_fact_is_enough_for_draft_release_path():
    snapshot = {
        "product": {"name": "분갈이 매트"},
        "detail": {
            "specification": "확정 규격",
            "usage": None,
            "installation_method": None,
            "usage_conditions": None,
            "cautions": None,
        },
        "skus": [],
    }
    result = fact_readiness(snapshot)
    assert result["ready"] is True
    assert result["has_detail_fact"] is True


def test_registered_sku_can_satisfy_minimum_fact_gate():
    snapshot = {
        "product": {"name": "분갈이 매트"},
        "detail": {},
        "skus": [{"sku_code": "MAT-S", "name": "소"}],
    }
    result = fact_readiness(snapshot)
    assert result["ready"] is True
    assert result["has_sku_fact"] is True
