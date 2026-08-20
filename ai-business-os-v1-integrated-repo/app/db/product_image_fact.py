from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base


def utcnow():
    return datetime.now(timezone.utc)


class ProductImageFact(Base):
    """A product photograph moving from temporary capture to confirmed visual FACT.

    Raw phone captures are temporary by default. For non-lifestyle images the
    background-removed output becomes the canonical visual FACT after user
    confirmation and the temporary raw file is deleted. Lifestyle captures keep
    their original background and are retained as the FACT itself.
    """

    __tablename__ = "product_image_facts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )

    slot_type: Mapped[str] = mapped_column(String(40), nullable=False, default="UNASSIGNED")
    slot_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="uploaded")
    source_kind: Mapped[str] = mapped_column(
        String(32), nullable=False, default="temporary_capture"
    )

    raw_asset_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    fact_asset_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_asset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("image_reference_assets.id", ondelete="SET NULL"), nullable=True
    )
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    classification_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    background_removed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    keep_background: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    raw_retention_policy: Mapped[str] = mapped_column(
        String(32), nullable=False, default="delete_on_confirm"
    )
    raw_deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    confirmed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
