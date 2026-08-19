from app.product_registration_ui import inject_product_registration_link
from app.services.product_registration import _fallback_suggestions


def test_fallback_suggestions_do_not_invent_physical_facts():
    result = _fallback_suggestions(
        "테스트 상품",
        {
            "primary_material": "steel",
            "country_of_origin": "KR",
            "dimensions": {},
            "packaging": {},
        },
    )

    assert result["operating"]["sale_price"] is None
    assert result["operating"]["cost"] is None
    assert "steel" in " ".join(result["marketing"]["features"])
    assert result["category"] is None


def test_dashboard_link_injection_is_idempotent():
    html = '<button data-panel="products">상품 업무</button>'
    once = inject_product_registration_link(html)
    twice = inject_product_registration_link(once)

    assert '/product-registration' in once
    assert once == twice
