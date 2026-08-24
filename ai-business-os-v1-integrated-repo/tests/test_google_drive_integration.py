from app.core.config import settings
from app.services import google_drive


def test_authorization_url_uses_narrow_drive_file_scope(monkeypatch):
    monkeypatch.setattr(settings, "google_drive_client_id", "client-id")
    monkeypatch.setattr(settings, "google_drive_redirect_uri", "https://os.gardenfarm.kr/callback")
    url = google_drive.authorization_url("state-value")
    assert "drive.file" in url
    assert "access_type=offline" in url
    assert "state=state-value" in url
    assert "auth%2Fdrive&" not in url


def test_token_encryption_round_trip(monkeypatch):
    monkeypatch.setattr(settings, "secret_key", "test-only-long-random-secret")
    encrypted = google_drive.encrypt("refresh-token")
    assert encrypted != "refresh-token"
    assert google_drive.decrypt(encrypted) == "refresh-token"
