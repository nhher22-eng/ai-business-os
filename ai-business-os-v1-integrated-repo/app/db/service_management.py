import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base


def utcnow():
    return datetime.now(timezone.utc)


class ServiceManagementSetting(Base):
    """Non-secret billing and operating metadata for an external service."""

    __tablename__ = "service_management_settings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "service_code", name="uq_service_setting_tenant_code"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    service_code: Mapped[str] = mapped_column(String(64), nullable=False)
    plan_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    billing_status: Mapped[str] = mapped_column(String(32), nullable=False, default="manual_check")
    current_month_cost_krw: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_budget_krw: Mapped[int | None] = mapped_column(Integer, nullable=True)
    renewal_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    usage_summary: Mapped[str | None] = mapped_column(String(240), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[str] = mapped_column(String(128), nullable=False, default="dashboard-user")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
