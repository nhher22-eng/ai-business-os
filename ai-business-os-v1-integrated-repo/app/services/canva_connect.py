import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import settings
from app.services.google_drive import decrypt, encrypt

AUTH_URL = "https://www.canva.com/api/oauth/authorize"
TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token"
SCOPES = "asset:read asset:write brandtemplate:meta:read design:content:write"


def pkce_pair():
    verifier = secrets.token_urlsafe(72)[:96]
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def authorization_url(*, state: str, challenge: str) -> str:
    return str(httpx.URL(AUTH_URL, params={
        "code_challenge": challenge, "code_challenge_method": "S256",
        "scope": SCOPES, "response_type": "code", "client_id": settings.canva_client_id,
        "state": state, "redirect_uri": settings.canva_redirect_uri,
    }))


def _token(data: dict) -> dict:
    response = httpx.post(TOKEN_URL, data=data, auth=(settings.canva_client_id, settings.canva_client_secret), timeout=20)
    response.raise_for_status()
    return response.json()


def exchange_code(code: str, verifier: str):
    return _token({"grant_type": "authorization_code", "code": code, "code_verifier": verifier, "redirect_uri": settings.canva_redirect_uri})


def refresh(refresh_token: str):
    return _token({"grant_type": "refresh_token", "refresh_token": refresh_token})


def expires_at(payload: dict):
    return datetime.now(timezone.utc) + timedelta(seconds=int(payload.get("expires_in", 14400)))


def create_asset_upload(access_token: str, *, content: bytes, name: str) -> dict:
    safe_name = (name.strip() or "AI Business OS image")[:50]
    metadata = {"name_base64": base64.b64encode(safe_name.encode()).decode()}
    response = httpx.post(
        "https://api.canva.com/rest/v1/asset-uploads",
        content=content,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/octet-stream",
            "Asset-Upload-Metadata": __import__("json").dumps(metadata),
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def get_asset_upload(access_token: str, job_id: str) -> dict:
    response = httpx.get(
        f"https://api.canva.com/rest/v1/asset-uploads/{job_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def get_brand_template_dataset(access_token: str, template_id: str) -> dict:
    response = httpx.get(
        f"https://api.canva.com/rest/v1/brand-templates/{template_id}/dataset",
        headers={"Authorization": f"Bearer {access_token}"}, timeout=20,
    )
    response.raise_for_status()
    return response.json()


def create_autofill(access_token: str, *, template_id: str, data: dict, title: str) -> dict:
    response = httpx.post(
        "https://api.canva.com/rest/v1/autofills",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={"type": "create_from_brand_template", "brand_template_id": template_id, "data": data, "title": title},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def get_autofill(access_token: str, job_id: str) -> dict:
    response = httpx.get(
        f"https://api.canva.com/rest/v1/autofills/{job_id}",
        headers={"Authorization": f"Bearer {access_token}"}, timeout=20,
    )
    response.raise_for_status()
    return response.json()
