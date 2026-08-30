from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base


def utcnow():
    return datetime.now(timezone.utc)


class ContentCopyAsset(Base):
    """Reusable, approved copy derived from product FACT.

    Source facts and generated wording remain separate. A candidate only becomes
    a reusable expression asset after an explicit approval action.
    """

    __tablename__ = "content_copy_assets"
    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "target_type",
            "slot_key",
            "version_no",
            name="uq_content_copy_asset_version",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("business_workspaces.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    target_type: Mapped[str] = mapped_column(String(40), nullable=False)
    slot_key: Mapped[str] = mapped_column(String(80), nullable=False)
    slot_label: Mapped[str] = mapped_column(String(160), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="candidate")
    source_fact_keys: Mapped[list | None] = mapped_column(JSON, nullable=True)
    generation_method: Mapped[str] = mapped_column(
        String(32), nullable=False, default="fact_substitution"
    )
    version_no: Mapped[int] = mapped_column(nullable=False, default=1)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
