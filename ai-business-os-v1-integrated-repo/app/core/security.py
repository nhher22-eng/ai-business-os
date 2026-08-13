import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings


control_bearer = HTTPBearer(auto_error=False)


def require_agent_control_auth(
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
            detail={
                "code": "AGENT_CONTROL_UNAUTHORIZED",
                "message": "Valid Bearer credential required",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
