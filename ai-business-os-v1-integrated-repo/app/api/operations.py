from datetime import datetime, timezone
from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    Header,
    Query,
)
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import require_agent_control_auth
from app.db.models import (
    AgentControlState,
    TenantAutomationState,
)
from app.db.session import SessionLocal


router = APIRouter(
    prefix="/api/v1/operations/control",
    tags=["operations-control"],
    dependencies=[Depends(require_agent_control_auth)],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def now_utc():
    return datetime.now(timezone.utc)


def normalize_operator(value: str | None) -> str:
    value = (value or "operations-dashboard").strip()
    return value[:128] or "operations-dashboard"


class AgentStateBody(BaseModel):
    desired_state: Literal["on", "paused", "off"]


class TenantPauseBody(BaseModel):
    paused: bool


def snapshot(
    db: Session,
    tenant_id: str,
    agent_id: str,
):
    agent = db.scalar(
        select(AgentControlState).where(
            AgentControlState.tenant_id == tenant_id,
            AgentControlState.agent_id == agent_id,
        )
    )

    tenant = db.scalar(
        select(TenantAutomationState).where(
            TenantAutomationState.tenant_id == tenant_id,
        )
    )

    desired_state = (
        agent.desired_state
        if agent is not None
        else "on"
    )

    tenant_paused = bool(
        tenant is not None and tenant.paused
    )

    if tenant_paused:
        effective_state = "paused_by_tenant"
    else:
        effective_state = desired_state

    return {
        "tenant_id": tenant_id,
        "agent_id": agent_id,
        "tenant_paused": tenant_paused,
        "desired_state": desired_state,
        "effective_state": effective_state,
        "agent": {
            "changed_by": (
                agent.changed_by
                if agent is not None
                else None
            ),
            "changed_at": (
                agent.changed_at.isoformat()
                if agent is not None
                and agent.changed_at is not None
                else None
            ),
            "version": (
                agent.version
                if agent is not None
                else 0
            ),
        },
        "tenant": {
            "changed_by": (
                tenant.changed_by
                if tenant is not None
                else None
            ),
            "changed_at": (
                tenant.changed_at.isoformat()
                if tenant is not None
                and tenant.changed_at is not None
                else None
            ),
            "version": (
                tenant.version
                if tenant is not None
                else 0
            ),
        },
    }


@router.get("/status")
def get_control_status(
    tenant_id: str = Query(..., min_length=1, max_length=128),
    agent_id: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
):
    return snapshot(
        db,
        tenant_id,
        agent_id,
    )


@router.put("/agent")
def update_agent_state(
    body: AgentStateBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    agent_id: str = Query(..., min_length=1, max_length=128),
    x_operator_id: str | None = Header(
        default=None,
        alias="X-Operator-ID",
    ),
    db: Session = Depends(get_db),
):
    operator = normalize_operator(x_operator_id)
    changed_at = now_utc()

    row = db.scalar(
        select(AgentControlState).where(
            AgentControlState.tenant_id == tenant_id,
            AgentControlState.agent_id == agent_id,
        )
    )

    if row is None:
        row = AgentControlState(
            tenant_id=tenant_id,
            agent_id=agent_id,
            desired_state=body.desired_state,
            changed_by=operator,
            changed_at=changed_at,
            version=1,
        )
        db.add(row)
    else:
        row.desired_state = body.desired_state
        row.changed_by = operator
        row.changed_at = changed_at
        row.version = int(row.version or 0) + 1

    db.commit()

    return snapshot(
        db,
        tenant_id,
        agent_id,
    )


@router.put("/tenant")
def update_tenant_state(
    body: TenantPauseBody,
    tenant_id: str = Query(..., min_length=1, max_length=128),
    agent_id: str = Query(
        "__legacy_default_agent__",
        min_length=1,
        max_length=128,
    ),
    x_operator_id: str | None = Header(
        default=None,
        alias="X-Operator-ID",
    ),
    db: Session = Depends(get_db),
):
    operator = normalize_operator(x_operator_id)
    changed_at = now_utc()

    row = db.scalar(
        select(TenantAutomationState).where(
            TenantAutomationState.tenant_id == tenant_id,
        )
    )

    if row is None:
        row = TenantAutomationState(
            tenant_id=tenant_id,
            paused=body.paused,
            changed_by=operator,
            changed_at=changed_at,
            version=1,
        )
        db.add(row)
    else:
        row.paused = body.paused
        row.changed_by = operator
        row.changed_at = changed_at
        row.version = int(row.version or 0) + 1

    db.commit()

    return snapshot(
        db,
        tenant_id,
        agent_id,
    )
