import base64
import hashlib
from datetime import datetime, timedelta, timezone

import httpx
from cryptography.fernet import Fernet

from app.core.config import settings

DRIVE_API = "https://www.googleapis.com/drive/v3"


def _cipher() -> Fernet:
    if not settings.secret_key or settings.secret_key == "CHANGE_ME":
        raise RuntimeError("SECRET_KEY must be configured before Google Drive can be connected")
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
    return Fernet(key)


def encrypt(value: str) -> str:
    return _cipher().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return _cipher().decrypt(value.encode()).decode()


def authorization_url(state: str) -> str:
    params = {
        "client_id": settings.google_drive_client_id,
        "redirect_uri": settings.google_drive_redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/drive.file",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return str(httpx.URL("https://accounts.google.com/o/oauth2/v2/auth", params=params))


def exchange_code(code: str) -> dict:
    response = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": settings.google_drive_client_id,
            "client_secret": settings.google_drive_client_secret,
            "redirect_uri": settings.google_drive_redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def refresh(refresh_token: str) -> dict:
    response = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "refresh_token": refresh_token,
            "client_id": settings.google_drive_client_id,
            "client_secret": settings.google_drive_client_secret,
            "grant_type": "refresh_token",
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def expires_at(payload: dict):
    return datetime.now(timezone.utc) + timedelta(seconds=int(payload.get("expires_in", 3600)))


def headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


def verify_folder(access_token: str, folder_id: str) -> dict:
    response = httpx.get(
        f"{DRIVE_API}/files/{folder_id}",
        params={"fields": "id,name,mimeType,trashed"},
        headers=headers(access_token),
        timeout=20,
    )
    response.raise_for_status()
    item = response.json()
    if item.get("mimeType") != "application/vnd.google-apps.folder" or item.get("trashed"):
        raise ValueError("선택한 항목은 사용 가능한 Google Drive 폴더가 아닙니다.")
    return item


def ensure_child_folder(access_token: str, parent_id: str, name: str) -> str:
    escaped = name.replace("'", "\\'")
    query = (
        f"'{parent_id}' in parents and name = '{escaped}' and "
        "mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    )
    found = httpx.get(
        f"{DRIVE_API}/files",
        params={"q": query, "fields": "files(id,name)", "pageSize": 2},
        headers=headers(access_token),
        timeout=20,
    )
    found.raise_for_status()
    files = found.json().get("files", [])
    if files:
        return files[0]["id"]
    created = httpx.post(
        f"{DRIVE_API}/files",
        params={"fields": "id"},
        json={"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]},
        headers=headers(access_token),
        timeout=20,
    )
    created.raise_for_status()
    return created.json()["id"]


def provision_base_folders(access_token: str, root_id: str) -> dict:
    return {
        name: ensure_child_folder(access_token, root_id, name)
        for name in ("상품자산", "판매콘텐츠", "공통자산", "내보내기", "보관")
    }
