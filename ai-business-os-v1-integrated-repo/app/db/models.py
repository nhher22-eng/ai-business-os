import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


LEGACY_TENANT_ID = "__legacy__"
LEGACY_AGENT_ID = "__legacy_default_agent__"


def utcnow():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class RunStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    task: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus),
        nullable=False,
        default=RunStatus.queued,
    )
    result: Mapped[str | None] = mapped_column(Text, nullable=True)

    tenant_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default=LEGACY_TENANT_ID,
    )
    agent_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default=LEGACY_AGENT_ID,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"

    worker_id: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
    )
    last_heartbeat_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )


class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    job_id: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
    )


class WebhookOutbox(Base):
    __tablename__ = "webhook_outbox"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )


class AgentControlState(Base):
    __tablename__ = "agent_control_states"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "agent_id",
            name="uq_agent_control_state",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    tenant_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    agent_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    desired_state: Mapped[str] = mapped_column(
        String(16),
        default="on",
        nullable=False,
    )
    changed_by: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )


class TenantAutomationState(Base):
    __tablename__ = "tenant_automation_states"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            name="uq_tenant_automation_state",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    tenant_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    paused: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    changed_by: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )


class SafetyGateResult(Base):
    __tablename__ = "safety_gate_results"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    tenant_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    agent_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    run_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )
    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    allowed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    reason_code: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
