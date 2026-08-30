from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_doctor_covers_stage1_dependencies_and_is_non_destructive():
    text = (ROOT / "scripts" / "aios-doctor").read_text()
    for marker in (
        "git push --dry-run",
        "AIOS_GIT_ROOT",
        "AIOS_ROOT",
        "docker compose ps",
        "/health/live",
        "/health/ready",
        "postgres",
        "redis",
        "sha256sum -c",
        "디스크 사용률",
        "작업 진행 가능 여부",
    ):
        assert marker in text
    for forbidden in ("reset --hard", "docker compose down", "DROP DATABASE", "rm -rf"):
        assert forbidden not in text


def test_preflight_delegates_to_doctor():
    text = (ROOT / "scripts" / "aios-preflight").read_text()
    assert 'aios-doctor" preflight' in text


def test_emergency_guide_has_fallbacks_and_secret_boundary():
    text = (ROOT / "docs" / "operations" / "EMERGENCY_ONE_PAGE_KO.md").read_text()
    assert "접근 문제" in text
    assert "사용자 PC → EC2 SSH → GitHub" in text
    assert "최신 백업을 격리 DB에 먼저 복원" in text
    assert "비밀번호, 토큰, `.env`, PEM 키 내용은 보내지 않습니다" in text
