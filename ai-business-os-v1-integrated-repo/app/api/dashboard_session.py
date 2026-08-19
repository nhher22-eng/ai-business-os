import hashlib
import hmac
import secrets
import time

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
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

    response.set_cookie(
        key=COOKIE_NAME,
        value=_make_session(),
        max_age=SESSION_SECONDS,
        httponly=True,
        samesite="strict",
        secure=False,
        path="/",
    )

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


@router.delete("/session")
def delete_session(response: Response):
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
    )

    return {"authenticated": False}
