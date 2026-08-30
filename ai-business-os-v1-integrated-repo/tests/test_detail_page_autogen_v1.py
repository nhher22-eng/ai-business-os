from types import SimpleNamespace

from app.services import detail_page_autogen as autogen


class FakeDB:
    def flush(self):
        return None


def _section(section_type: str, *, enabled: bool = True, required: bool = True):
    return SimpleNamespace(
        section_type=section_type,
        is_enabled=enabled,
        is_required=required,
        qa_status="review",
    )


def test_release_candidate_hides_missing_optional_data(monkeypatch):
    sections = [
        _section("HERO"),
        _section("REVIEW_SUMMARY"),
        _section("PROBLEM"),
        _section("LIFESTYLE"),
        _section("FEATURE"),
        _section("OPTION_COMPARE"),
        _section("ADD_ON", required=False),
        _section("COMPONENTS"),
        _section("INSTALLATION"),
        _section("SPEC"),
        _section("REVIEW_DETAIL"),
        _section("RELATED_PRODUCTS", required=False),
        _section("FAQ"),
    ]
    monkeypatch.setattr(autogen, "version_sections", lambda db, version_id: sections)
    monkeypatch.setattr(
        autogen,
        "_conditional_availability",
        lambda db, tenant_id, product_id: {
            "reviews": False,
            "add_on": False,
            "related_products": False,
        },
    )

    job = SimpleNamespace(tenant_id="tenant", product_id="product", status="p0_review")
    version = SimpleNamespace(id="version", status="p0_review")

    enabled, hidden = autogen.apply_release_candidate_rules(
        FakeDB(), job=job, version=version
    )

    assert "REVIEW_SUMMARY" in hidden
    assert "REVIEW_DETAIL" in hidden
    assert "ADD_ON" in hidden
    assert "RELATED_PRODUCTS" in hidden
    assert "HERO" in enabled
    assert "SPEC" in enabled
    assert "FAQ" in enabled

    hidden_rows = [row for row in sections if row.section_type in hidden]
    assert all(row.is_enabled is False for row in hidden_rows)
    assert all(row.is_required is False for row in hidden_rows)
    assert all(row.qa_status == "hidden" for row in hidden_rows)
    assert job.status == "release_candidate_review"
    assert version.status == "release_candidate_review"


def test_release_candidate_keeps_available_conditional_sections(monkeypatch):
    sections = [
        _section("HERO"),
        _section("REVIEW_SUMMARY"),
        _section("ADD_ON", required=False),
        _section("RELATED_PRODUCTS", required=False),
    ]
    monkeypatch.setattr(autogen, "version_sections", lambda db, version_id: sections)
    monkeypatch.setattr(
        autogen,
        "_conditional_availability",
        lambda db, tenant_id, product_id: {
            "reviews": True,
            "add_on": True,
            "related_products": True,
        },
    )

    job = SimpleNamespace(tenant_id="tenant", product_id="product", status="p0_review")
    version = SimpleNamespace(id="version", status="p0_review")

    enabled, hidden = autogen.apply_release_candidate_rules(
        FakeDB(), job=job, version=version
    )

    assert hidden == []
    assert enabled == [
        "HERO",
        "REVIEW_SUMMARY",
        "ADD_ON",
        "RELATED_PRODUCTS",
    ]


def test_release_ready_requires_qa_pass_and_fact_readiness():
    base = dict(
        job=SimpleNamespace(),
        version=SimpleNamespace(),
        qa_rows=[],
        enabled_sections=[],
        hidden_sections=[],
    )
    assert autogen.AutoGenerateResult(
        **base, qa_summary="PASS", fact_readiness={"ready": True}
    ).release_ready is True
    assert autogen.AutoGenerateResult(
        **base, qa_summary="PASS", fact_readiness={"ready": False}
    ).release_ready is False
    assert autogen.AutoGenerateResult(
        **base, qa_summary="REVIEW", fact_readiness={"ready": True}
    ).release_ready is False
    assert autogen.AutoGenerateResult(
        **base, qa_summary="FAIL", fact_readiness={"ready": True}
    ).release_ready is False
