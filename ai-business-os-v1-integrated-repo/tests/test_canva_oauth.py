from app.services import canva_connect


def test_canva_oauth_uses_pkce_s256_and_minimum_scopes(monkeypatch):
    monkeypatch.setattr(canva_connect.settings, "canva_client_id", "client")
    monkeypatch.setattr(canva_connect.settings, "canva_redirect_uri", "https://example.test/callback")
    verifier, challenge = canva_connect.pkce_pair()
    assert 43 <= len(verifier) <= 128
    url = canva_connect.authorization_url(state="state", challenge=challenge)
    assert "code_challenge_method=S256" in url
    assert "state=state" in url
    for scope in ("asset%3Aread", "asset%3Awrite", "brandtemplate%3Ameta%3Aread", "design%3Acontent%3Awrite"):
        assert scope in url


def test_canva_connection_migration_follows_service_management():
    text = open("migrations/versions/0020_canva_connections.py", encoding="utf-8").read()
    assert 'down_revision = "0019_service_management"' in text
    assert '"canva_connections"' in text
