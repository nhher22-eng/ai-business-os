import hashlib
import hmac
import base64
import io
import secrets
import time
from urllib.parse import quote

import redis

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.responses import RedirectResponse
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from app.core.config import settings


router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["dashboard-session"],
)

bearer = HTTPBearer(auto_error=False)

COOKIE_NAME = "ai_business_os_session"
SESSION_SECONDS = 8 * 60 * 60
MOBILE_LINK_SECONDS = 2 * 60
MOBILE_LINK_PREFIX = "dashboard-mobile-link:"


def _secret() -> str:
    value = settings.agent_control_api_token.strip()

    if not value:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="dashboard authentication is not configured",
        )

    return value


def _make_session() -> str:
    expires = int(time.time()) + SESSION_SECONDS
    nonce = secrets.token_urlsafe(18)
    payload = f"{expires}.{nonce}"

    signature = hmac.new(
        _secret().encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()

    return f"{payload}.{signature}"


def _valid_session(value: str | None) -> bool:
    if not value:
        return False

    try:
        expires_text, nonce, signature = value.split(".", 2)
        expires = int(expires_text)
    except (ValueError, TypeError):
        return False

    if expires < int(time.time()):
        return False

    payload = f"{expires}.{nonce}"

    expected = hmac.new(
        _secret().encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, expected)


def _set_session_cookie(response: Response) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=_make_session(),
        max_age=SESSION_SECONDS,
        httponly=True,
        samesite="strict",
        secure=settings.app_env != "test",
        path="/",
    )


def _mobile_link_key(code: str) -> str:
    digest = hashlib.sha256(code.encode()).hexdigest()
    return f"{MOBILE_LINK_PREFIX}{digest}"


def _redis():
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def _public_origin(request: Request) -> str:
    host = request.headers.get("host", "").strip()
    if not host or any(char in host for char in "/\\\r\n"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="valid host required",
        )
    forwarded = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip()
    scheme = forwarded if forwarded in {"http", "https"} else request.url.scheme
    if settings.app_env != "test":
        scheme = "https"
    return f"{scheme}://{host}"


def _qr_data_url(value: str) -> str:
    import qrcode

    image = qrcode.make(value)
    output = io.BytesIO()
    image.save(output, format="PNG")
    encoded = base64.b64encode(output.getvalue()).decode()
    return f"data:image/png;base64,{encoded}"


def require_business_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> None:
    expected = _secret()

    if (
        credentials is not None
        and credentials.scheme.lower() == "bearer"
        and secrets.compare_digest(
            credentials.credentials,
            expected,
        )
    ):
        return

    if _valid_session(
        request.cookies.get(COOKIE_NAME)
    ):
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="dashboard authentication required",
    )


@router.post("/session")
def create_session(
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
):
    expected = _secret()

    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not secrets.compare_digest(
            credentials.credentials,
            expected,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="valid Bearer credential required",
        )

    _set_session_cookie(response)

    return {
        "authenticated": True,
        "expires_in_seconds": SESSION_SECONDS,
    }


@router.get("/session")
def session_status(request: Request):
    if not _valid_session(
        request.cookies.get(COOKIE_NAME)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="dashboard session required",
        )

    return {"authenticated": True}


@router.post("/mobile-link", dependencies=[Depends(require_business_auth)])
def create_mobile_link(request: Request):
    code = secrets.token_urlsafe(32)
    _redis().setex(
        _mobile_link_key(code),
        MOBILE_LINK_SECONDS,
        "unused",
    )
    path = f"/api/v1/dashboard/mobile-login?code={quote(code)}"
    login_url = f"{_public_origin(request)}{path}"
    return {
        "login_url": login_url,
        "qr_data_url": _qr_data_url(login_url),
        "expires_in_seconds": MOBILE_LINK_SECONDS,
        "single_use": True,
    }


@router.get("/mobile-login", name="consume_mobile_link")
def consume_mobile_link(code: str):
    if not code or len(code) > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="valid mobile login code required",
        )
    value = _redis().getdel(_mobile_link_key(code))
    if value != "unused":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="mobile login link is invalid, expired, or already used",
        )
    response = RedirectResponse(url="/business-home", status_code=303)
    _set_session_cookie(response)
    return response


@router.delete("/session")
def delete_session(response: Response):
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
    )

    return {"authenticated": False}
