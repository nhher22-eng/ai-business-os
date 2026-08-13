from dataclasses import dataclass

from sqlalchemy import select

from app.db.models import (
    AgentControlState,
    SafetyGateResult,
    TenantAutomationState,
    utcnow,
)


VALID_AGENT_STATES = {"on", "paused", "off"}


@dataclass(frozen=True)
class ControlDecision:
    allowed: bool
    action: str
    reason_code: str


def evaluate_control_policy(
    *,
    tenant_paused: bool,
    desired_state: str,
) -> ControlDecision:
    if tenant_paused:
        return ControlDecision(
            allowed=False,
            action="block",
            reason_code="TENANT_AUTOMATION_PAUSED",
        )

    if desired_state == "off":
        return ControlDecision(
            allowed=False,
            action="block",
            reason_code="AGENT_USER_OFF",
        )

    if desired_state == "paused":
        return ControlDecision(
            allowed=False,
            action="block",
            reason_code="AGENT_USER_PAUSED",
        )

    return ControlDecision(
        allowed=True,
        action="allow",
        reason_code="OK",
    )


def get_agent_state(db, tenant_id: str, agent_id: str) -> str:
    row = db.scalar(
        select(AgentControlState).where(
            AgentControlState.tenant_id == tenant_id,
            AgentControlState.agent_id == agent_id,
        )
    )
    return row.desired_state if row else "on"


def is_tenant_paused(db, tenant_id: str) -> bool:
    row = db.scalar(
        select(TenantAutomationState).where(
            TenantAutomationState.tenant_id == tenant_id
        )
    )
    return bool(row and row.paused)


def authorize_identity(
    db,
    *,
    tenant_id: str,
    agent_id: str,
    source: str,
    run_id: str | None = None,
) -> ControlDecision:
    decision = evaluate_control_policy(
        tenant_paused=is_tenant_paused(db, tenant_id),
        desired_state=get_agent_state(db, tenant_id, agent_id),
    )

    db.add(
        SafetyGateResult(
            tenant_id=tenant_id,
            agent_id=agent_id,
            run_id=run_id,
            source=source,
            allowed=decision.allowed,
            action=decision.action,
            reason_code=decision.reason_code,
        )
    )

    return decision


def set_agent_state(
    db,
    *,
    tenant_id: str,
    agent_id: str,
    desired_state: str,
    changed_by: str = "operator-cli",
):
    if desired_state not in VALID_AGENT_STATES:
        raise ValueError(
            f"desired_state must be one of "
            f"{sorted(VALID_AGENT_STATES)}"
        )

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
            desired_state=desired_state,
            changed_by=changed_by,
        )
        db.add(row)
    else:
        row.desired_state = desired_state
        row.changed_by = changed_by
        row.changed_at = utcnow()
        row.version += 1

    return row


def set_tenant_paused(
    db,
    *,
    tenant_id: str,
    paused: bool,
    changed_by: str = "operator-cli",
):
    row = db.scalar(
        select(TenantAutomationState).where(
            TenantAutomationState.tenant_id == tenant_id
        )
    )

    if row is None:
        row = TenantAutomationState(
            tenant_id=tenant_id,
            paused=paused,
            changed_by=changed_by,
        )
        db.add(row)
    else:
        row.paused = paused
        row.changed_by = changed_by
        row.changed_at = utcnow()
        row.version += 1

    return row
