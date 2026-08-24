import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base


def utcnow():
    return datetime.now(timezone.utc)


class ProductRegistrationProfile(Base):
    """Product master fields that sit on top of the existing Product/SKU model.

    FACT fields are user-confirmed source-of-truth values. Operating and
    marketing data may be AI-assisted, but are stored separately so they never
    overwrite factual product data.
    """

    __tablename__ = "product_registration_profiles"
    __table_args__ = (
        UniqueConstraint("product_id", name="uq_product_registration_profile_product"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )

    # 1) User-confirmed source FACT
    model_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    primary_material: Mapped[str | None] = mapped_column(String(240), nullable=True)
    secondary_material: Mapped[str | None] = mapped_column(String(240), nullable=True)
    weight: Mapped[str | None] = mapped_column(String(120), nullable=True)
    dimensions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(240), nullable=True)
    country_of_origin: Mapped[str | None] = mapped_column(String(160), nullable=True)
    certifications: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    packaging: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fact_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    facts_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    facts_confirmed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    facts_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 2) Operating information: mutable and AI-assistable
    operating_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # 3) Marketing interpretation: subjective and AI-assistable
    marketing_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # AI proposal stays separate until the user applies it.
    ai_suggestions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_suggestion_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Reuse ImageReferenceAsset rows; only IDs and display role live here.
    primary_image_asset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    additional_image_asset_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class ProductSourceAsset(Base):
    """User-supplied source material kept as first-party product evidence."""

    __tablename__ = "product_source_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_kind: Mapped[str] = mapped_column(String(48), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(160), nullable=True)
    asset_uri: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
