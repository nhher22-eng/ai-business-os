import json
import secrets
from datetime import datetime, timedelta, timezone

import redis
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import require_agent_control_auth
from app.db.google_drive import GoogleDriveConnection
from app.db.session import SessionLocal
from app.services import google_drive as drive

router = APIRouter(prefix="/api/v1/integrations/google-drive", tags=["google-drive"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def configured():
    if not settings.google_drive_client_id or not settings.google_drive_client_secret:
        raise HTTPException(503, "Google Drive OAuth is not configured")


class FolderBody(BaseModel):
    folder_id: str


@router.post("/connect", dependencies=[Depends(require_agent_control_auth)])
def connect(tenant_id: str = Query(..., min_length=1, max_length=128)):
    configured()
    state = secrets.token_urlsafe(32)
    redis.Redis.from_url(settings.redis_url).setex(
        f"google-drive-oauth:{state}", 1800, json.dumps({"tenant_id": tenant_id})
    )
    return {"authorization_url": drive.authorization_url(state)}


@router.get("/callback")
def callback(code: str, state: str, db: Session = Depends(get_db)):
    configured()
    client = redis.Redis.from_url(settings.redis_url)
    state_key = f"google-drive-oauth:{state}"
    raw = client.get(state_key)
    if not raw:
        raise HTTPException(400, "OAuth state expired or invalid")
    tenant_id = json.loads(raw)["tenant_id"]
    tokens = drive.exchange_code(code)
    client.delete(state_key)
    row = db.scalar(select(GoogleDriveConnection).where(GoogleDriveConnection.tenant_id == tenant_id))
    if row is None:
        row = GoogleDriveConnection(tenant_id=tenant_id, root_folder_id="", folder_map={})
        db.add(row)
    row.access_token_encrypted = drive.encrypt(tokens["access_token"])
    if tokens.get("refresh_token"):
        row.refresh_token_encrypted = drive.encrypt(tokens["refresh_token"])
    row.token_expires_at = drive.expires_at(tokens)
    db.commit()
    ticket = secrets.token_urlsafe(32)
    client.setex(f"google-drive-picker:{ticket}", 600, tenant_id)
    return RedirectResponse(url=f"/google-drive-setup?ticket={ticket}", status_code=303)


def _picker_row(ticket: str, db: Session):
    tenant = redis.Redis.from_url(settings.redis_url).get(f"google-drive-picker:{ticket}")
    if not tenant:
        raise HTTPException(400, "Folder selection session expired")
    tenant_id = tenant.decode()
    row = db.scalar(select(GoogleDriveConnection).where(GoogleDriveConnection.tenant_id == tenant_id))
    if row is None:
        raise HTTPException(409, "Google Drive is not connected")
    return tenant_id, row


def _active_token(row: GoogleDriveConnection, db: Session) -> str:
    if row.token_expires_at and row.token_expires_at > datetime.now(timezone.utc) + timedelta(seconds=60):
        return drive.decrypt(row.access_token_encrypted)
    if not row.refresh_token_encrypted:
        raise HTTPException(409, "Google Drive authorization must be renewed")
    payload = drive.refresh(drive.decrypt(row.refresh_token_encrypted))
    row.access_token_encrypted = drive.encrypt(payload["access_token"])
    row.token_expires_at = drive.expires_at(payload)
    db.commit()
    return payload["access_token"]


@router.get("/picker-session")
def picker_session(ticket: str, db: Session = Depends(get_db)):
    _, row = _picker_row(ticket, db)
    if not settings.google_picker_api_key or not settings.google_picker_app_id:
        raise HTTPException(503, "Google Picker is not configured")
    return {
        "access_token": _active_token(row, db),
        "developer_key": settings.google_picker_api_key,
        "app_id": settings.google_picker_app_id,
        "expected_name": "AI Business OS",
    }


@router.post("/picker-folder")
def picker_folder(body: FolderBody, ticket: str, db: Session = Depends(get_db)):
    tenant_id, row = _picker_row(ticket, db)
    token = _active_token(row, db)
    info = drive.verify_folder(token, body.folder_id)
    if info.get("name") != "AI Business OS":
        raise HTTPException(400, "'AI Business OS' 폴더를 선택해 주세요")
    row.root_folder_id = body.folder_id
    row.folder_map = drive.provision_base_folders(token, body.folder_id)
    db.commit()
    redis.Redis.from_url(settings.redis_url).delete(f"google-drive-picker:{ticket}")
    return {"connected": True, "tenant_id": tenant_id, "root": info, "folders": row.folder_map}


@router.post("/folder", dependencies=[Depends(require_agent_control_auth)])
def select_folder(body: FolderBody, tenant_id: str, db: Session = Depends(get_db)):
    row = db.scalar(select(GoogleDriveConnection).where(GoogleDriveConnection.tenant_id == tenant_id))
    if row is None:
        raise HTTPException(409, "Connect Google Drive first")
    token = _active_token(row, db)
    info = drive.verify_folder(token, body.folder_id)
    row.root_folder_id = body.folder_id
    row.folder_map = drive.provision_base_folders(token, body.folder_id)
    db.commit()
    return {"connected": True, "root": info, "folders": row.folder_map}


@router.get("/status", dependencies=[Depends(require_agent_control_auth)])
def status(tenant_id: str, db: Session = Depends(get_db)):
    row = db.scalar(select(GoogleDriveConnection).where(GoogleDriveConnection.tenant_id == tenant_id))
    return {"connected": bool(row and row.root_folder_id), "root_folder_id": row.root_folder_id if row else None, "folders": row.folder_map if row else {}}
