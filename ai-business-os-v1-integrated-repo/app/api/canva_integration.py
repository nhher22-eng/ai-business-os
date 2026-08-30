import json
import secrets
from datetime import datetime, timedelta, timezone

import redis
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import require_agent_control_auth
from app.db.canva import CanvaConnection
from app.db.session import SessionLocal
from app.services import canva_connect
from app.services.google_drive import decrypt, encrypt

router = APIRouter(prefix="/api/v1/integrations/canva", tags=["canva-integration"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def configured():
    if not settings.canva_client_id or not settings.canva_client_secret:
        raise HTTPException(503, "Canva OAuth is not configured")


def active_token(row: CanvaConnection, db: Session) -> str:
    if row.status != "connected":
        raise HTTPException(409, "Canva authorization must be renewed")
    if row.token_expires_at and row.token_expires_at > datetime.now(timezone.utc) + timedelta(seconds=60):
        return decrypt(row.access_token_encrypted)
    if not row.refresh_token_encrypted:
        row.status = "reauthorization_required"
        db.commit()
        raise HTTPException(409, "Canva authorization must be renewed")
    try:
        payload = canva_connect.refresh(decrypt(row.refresh_token_encrypted))
    except Exception as exc:
        row.status = "reauthorization_required"
        db.commit()
        raise HTTPException(409, "Canva token refresh failed; reconnect Canva") from exc
    row.access_token_encrypted = encrypt(payload["access_token"])
    if payload.get("refresh_token"):
        row.refresh_token_encrypted = encrypt(payload["refresh_token"])
    row.token_expires_at = canva_connect.expires_at(payload)
    row.scopes = payload.get("scope", row.scopes)
    db.commit()
    return payload["access_token"]


@router.post("/connect", dependencies=[Depends(require_agent_control_auth)])
def connect(tenant_id: str = Query(..., min_length=1, max_length=128)):
    configured()
    state = secrets.token_urlsafe(32)
    verifier, challenge = canva_connect.pkce_pair()
    redis.Redis.from_url(settings.redis_url).setex(
        f"canva-oauth:{state}", 1800,
        json.dumps({"tenant_id": tenant_id, "code_verifier": verifier}),
    )
    return {"authorization_url": canva_connect.authorization_url(state=state, challenge=challenge)}


@router.get("/callback")
def callback(code: str, state: str, db: Session = Depends(get_db)):
    configured()
    client = redis.Redis.from_url(settings.redis_url)
    key = f"canva-oauth:{state}"
    raw = client.get(key)
    if not raw:
        raise HTTPException(400, "OAuth state expired or invalid")
    context = json.loads(raw)
    tokens = canva_connect.exchange_code(code, context["code_verifier"])
    client.delete(key)
    row = db.scalar(select(CanvaConnection).where(CanvaConnection.tenant_id == context["tenant_id"]))
    if row is None:
        row = CanvaConnection(tenant_id=context["tenant_id"], access_token_encrypted="")
        db.add(row)
    row.access_token_encrypted = encrypt(tokens["access_token"])
    if tokens.get("refresh_token"):
        row.refresh_token_encrypted = encrypt(tokens["refresh_token"])
    row.token_expires_at = canva_connect.expires_at(tokens)
    row.scopes = tokens.get("scope", canva_connect.SCOPES)
    row.status = "connected"
    db.commit()
    return RedirectResponse(url="/service-management?canva=connected", status_code=303)


@router.get("/status", dependencies=[Depends(require_agent_control_auth)])
def status(tenant_id: str, db: Session = Depends(get_db)):
    row = db.scalar(select(CanvaConnection).where(CanvaConnection.tenant_id == tenant_id))
    return {"configured": bool(settings.canva_client_id and settings.canva_client_secret), "connected": bool(row and row.status == "connected"), "scopes": row.scopes.split() if row else []}
