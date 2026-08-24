from app.api.product_registration import FactBody
from app.db.product_registration import ProductRegistrationProfile
from app.services.product_master_integration_patch import (
    confirmed_master_facts,
    enhanced_fact_readiness,
)
from app.services.product_registration_safety_patch import apply_only_supplied_facts
from app import product_registration_ui
from app.product_registration_resume_ui_patch import inject_product_registration_resume


def test_only_confirmed_master_facts_are_exposed():
    profile = ProductRegistrationProfile(
        tenant_id="t",
        product_id="p",
        primary_material="steel",
        country_of_origin="KR",
        dimensions={"width": "100 mm"},
        facts_confirmed=False,
    )
    assert confirmed_master_facts(profile) == {}

    profile.facts_confirmed = True
    facts = confirmed_master_facts(profile)
    assert facts["primary_material"] == "steel"
    assert facts["country_of_origin"] == "KR"
    assert facts["dimensions"]["width"] == "100 mm"


def test_partial_fact_update_does_not_erase_existing_values():
    profile = ProductRegistrationProfile(
        tenant_id="t",
        product_id="p",
        primary_material="steel",
        manufacturer="maker-a",
        country_of_origin="CN",
        packaging={"box": "10 pcs"},
        facts_confirmed=True,
    )
    body = FactBody(country_of_origin="KR")
    apply_only_supplied_facts(profile, body)

    assert profile.country_of_origin == "KR"
    assert profile.primary_material == "steel"
    assert profile.manufacturer == "maker-a"
    assert profile.packaging == {"box": "10 pcs"}


def test_confirmed_master_fact_can_satisfy_detail_page_readiness():
    snapshot = {
        "product": {"name": "테스트 상품"},
        "detail": {},
        "skus": [],
        "registration": {
            "facts_confirmed": True,
            "facts": {"primary_material": "steel"},
        },
    }
    result = enhanced_fact_readiness(snapshot)
    assert result["ready"] is True
    assert result["has_master_fact"] is True
    assert "product_detail_or_sku" not in result["missing"]


def test_product_master_registration_ui_keeps_resume_patch_compatible():
    patched = inject_product_registration_resume(product_registration_ui.HTML)
    assert "resumeExistingProduct" in patched
    assert "if(!v('name'))" in patched
    assert "d.product.product_code" in patched
    assert "openNextSteps()" in patched
