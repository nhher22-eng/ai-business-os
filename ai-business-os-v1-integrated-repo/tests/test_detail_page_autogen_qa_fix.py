from types import SimpleNamespace

import app.services.detail_page_autogen as autogen


class DummyDB:
    def __init__(self):
        self.flush_count = 0

    def flush(self):
        self.flush_count += 1


def test_conditional_hidden_review_sections_do_not_fail_required_qa(monkeypatch):
    sections = [
        SimpleNamespace(section_type="HERO", is_enabled=True, is_required=True),
        SimpleNamespace(section_type="PROBLEM", is_enabled=True, is_required=True),
        SimpleNamespace(section_type="REVIEW_SUMMARY", is_enabled=False, is_required=False),
        SimpleNamespace(section_type="REVIEW_DETAIL", is_enabled=False, is_required=False),
    ]
    qa = SimpleNamespace(
        check_code="REQUIRED_SECTIONS",
        status="FAIL",
        severity="error",
        message="필수 섹션 누락: REVIEW_SUMMARY, REVIEW_DETAIL",
        suggested_fix="필수 섹션을 다시 활성화하세요.",
    )
    monkeypatch.setattr(autogen, "version_sections", lambda db, version_id: sections)

    db = DummyDB()
    autogen._reconcile_conditional_required_sections(
        db,
        version=SimpleNamespace(id="version-1"),
        qa_rows=[qa],
    )

    assert qa.status == "PASS"
    assert qa.severity == "info"
    assert qa.suggested_fix is None
    assert "조건부 페이지 규칙" in qa.message
    assert db.flush_count == 1


def test_true_required_section_still_fails(monkeypatch):
    sections = [
        SimpleNamespace(section_type="HERO", is_enabled=True, is_required=True),
        SimpleNamespace(section_type="SPEC", is_enabled=False, is_required=True),
        SimpleNamespace(section_type="REVIEW_DETAIL", is_enabled=False, is_required=False),
    ]
    qa = SimpleNamespace(
        check_code="REQUIRED_SECTIONS",
        status="PASS",
        severity="info",
        message="",
        suggested_fix=None,
    )
    monkeypatch.setattr(autogen, "version_sections", lambda db, version_id: sections)

    autogen._reconcile_conditional_required_sections(
        DummyDB(),
        version=SimpleNamespace(id="version-2"),
        qa_rows=[qa],
    )

    assert qa.status == "FAIL"
    assert qa.severity == "error"
    assert "SPEC" in qa.message
    assert qa.suggested_fix
