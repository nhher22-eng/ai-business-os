from types import SimpleNamespace

from app.services import detail_page_autogen as autogen


def test_hidden_review_sections_convert_review_source_to_pass(monkeypatch):
    version = SimpleNamespace(id="v1")
    qa = SimpleNamespace(
        check_code="REVIEW_SOURCE",
        status="REVIEW",
        severity="warning",
        message="missing reviews",
        suggested_fix="connect reviews",
        section_id="review-section",
    )
    sections = [
        SimpleNamespace(section_type="HERO", is_enabled=True),
        SimpleNamespace(section_type="REVIEW_SUMMARY", is_enabled=False),
        SimpleNamespace(section_type="REVIEW_DETAIL", is_enabled=False),
    ]
    monkeypatch.setattr(autogen, "version_sections", lambda db, version_id: sections)
    db = SimpleNamespace(flush=lambda: None)

    autogen._reconcile_review_source(db, version=version, qa_rows=[qa])

    assert qa.status == "PASS"
    assert qa.severity == "info"
    assert qa.suggested_fix is None
    assert qa.section_id is None
    assert "자동 제외" in qa.message
    assert "가짜 리뷰" in qa.message


def test_enabled_review_section_keeps_review_status(monkeypatch):
    version = SimpleNamespace(id="v1")
    qa = SimpleNamespace(
        check_code="REVIEW_SOURCE",
        status="REVIEW",
        severity="warning",
        message="missing reviews",
        suggested_fix="connect reviews",
        section_id="review-section",
    )
    sections = [SimpleNamespace(section_type="REVIEW_SUMMARY", is_enabled=True)]
    monkeypatch.setattr(autogen, "version_sections", lambda db, version_id: sections)
    db = SimpleNamespace(flush=lambda: None)

    autogen._reconcile_review_source(db, version=version, qa_rows=[qa])

    assert qa.status == "REVIEW"
    assert qa.suggested_fix == "connect reviews"
