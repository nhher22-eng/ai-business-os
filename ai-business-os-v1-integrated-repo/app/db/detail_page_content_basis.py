from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base


def utcnow():
    return datetime.now(timezone.utc)


class DetailPageContentBasis(Base):
    """Editable page-local content basis, separate from Product Master.

    Each detail-page version can carry its own category/usage/marketing basis.
    This lets a page evolve without silently mutating the shared Product Master.
    """

    __tablename__ = "detail_page_content_basis"
    __table_args__ = (
        UniqueConstraint("version_id", name="uq_detail_page_content_basis_version"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("detail_page_jobs.id", ondelete="CASCADE"), nullable=False
    )
    version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("detail_page_versions.id", ondelete="CASCADE"), nullable=False
    )
    basis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="product_master")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
