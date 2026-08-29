from fastapi import HTTPException
from starlette.requests import Request

from app import dashboard_ui
from app.api import dashboard_session


class FakeRedis:
    def __init__(self):
        self.values = {}

    def setex(self, key, seconds, value):
        self.values[key] = (seconds, value)

    def getdel(self, key):
        stored = self.values.pop(key, None)
        return stored[1] if stored else None


def request(host="os.gardenfarm.kr"):
    return Request({
        "type": "http",
        "method": "POST",
        "scheme": "https",
        "path": "/api/v1/dashboard/mobile-link",
        "headers": [(b"host", host.encode())],
        "server": (host, 443),
        "client": ("127.0.0.1", 1),
    })


def test_mobile_link_is_hashed_short_lived_and_single_use(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(dashboard_session, "_redis", lambda: fake)
    monkeypatch.setattr(dashboard_session, "_qr_data_url", lambda value: "data:image/png;base64,QR")
    monkeypatch.setattr(dashboard_session, "_secret", lambda: "test-session-secret")

    issued = dashboard_session.create_mobile_link(request())
    assert issued["expires_in_seconds"] == 120
    assert issued["single_use"] is True
    assert issued["login_url"].startswith(
        "https://os.gardenfarm.kr/api/v1/dashboard/mobile-login?code="
    )
    assert issued["qr_data_url"].startswith("data:image/png;base64,")
    assert len(fake.values) == 1
    stored_key = next(iter(fake.values))
    assert "code=" not in stored_key
    assert fake.values[stored_key] == (120, "unused")

    code = issued["login_url"].split("code=", 1)[1]
    response = dashboard_session.consume_mobile_link(code)
    assert response.status_code == 303
    assert response.headers["location"] == "/business-home"
    assert dashboard_session.COOKIE_NAME in response.headers["set-cookie"]

    try:
        dashboard_session.consume_mobile_link(code)
    except HTTPException as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("single-use mobile link was accepted twice")


def test_dashboard_exposes_mobile_qr_only_after_session_connection():
    for marker in (
        "모바일 연결 QR", "mobileConnectPanel", "createMobileConnectQr",
        "/api/v1/dashboard/mobile-link", "2분 동안 한 번만",
    ):
        assert marker in dashboard_ui.HTML
    assert 'id="mobileConnect"' in dashboard_ui.HTML
    assert 'style="display:none' in dashboard_ui.HTML
