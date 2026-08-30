import secrets

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings


control_bearer = HTTPBearer(auto_error=False)


def require_agent_control_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        control_bearer
    ),
) -> None:
    expected = settings.agent_control_api_token.strip()

    # A privileged control endpoint must never become unauthenticated
    # simply because deployment configuration is missing.
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "AGENT_CONTROL_AUTH_NOT_CONFIGURED",
                "message": "Agent Control authentication is not configured",
            },
        )

    bearer_valid = (
        credentials is not None
        and credentials.scheme.lower() == "bearer"
        and secrets.compare_digest(credentials.credentials, expected)
    )
    # The common 8-hour dashboard session is also a valid operator session.
    # Import lazily to keep the authentication modules acyclic.
    from app.api.dashboard_session import COOKIE_NAME, _valid_session
    session_valid = _valid_session(request.cookies.get(COOKIE_NAME))
    if not bearer_valid and not session_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AGENT_CONTROL_UNAUTHORIZED",
                "message": "Valid Bearer credential required",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
