import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base


def utcnow():
    return datetime.now(timezone.utc)


class NaverChannelProfile(Base):
    """Naver SmartStore-only registration data layered on Product Master.

    Product facts remain canonical in Product/ProductRegistrationProfile. This
    table stores only channel-specific values and Naver-upload results.
    """

    __tablename__ = "naver_channel_profiles"
    __table_args__ = (
        UniqueConstraint("product_id", name="uq_naver_channel_profile_product"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )

    leaf_category_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sale_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stock_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    after_service_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    origin_area_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    delivery_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    product_info_provided_notice_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    product_info_provided_notice: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    representative_naver_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    optional_naver_image_urls: Mapped[list | None] = mapped_column(JSON, nullable=True)

    origin_product_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    smartstore_channel_product_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_publish_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_publish_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
