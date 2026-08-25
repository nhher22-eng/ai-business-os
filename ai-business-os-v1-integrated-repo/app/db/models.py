import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
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


# --- M-21.1A BUSINESS WORKSPACE MODELS ---

class BusinessWorkspace(Base):
    __tablename__ = "business_workspaces"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug",
                         name="uq_business_workspace_tenant_slug"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    business_type: Mapped[str] = mapped_column(
        String(80), default="commerce", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default="active", nullable=False
    )
    mode: Mapped[str] = mapped_column(
        String(32), default="shadow", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow,
        onupdate=utcnow, nullable=False
    )

class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "product_code",
            name="uq_product_workspace_code",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("business_workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_code: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(240),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="draft",
        nullable=False,
    )
    sales_channel: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    category: Mapped[str | None] = mapped_column(String(160), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(160), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    country_of_origin: Mapped[str | None] = mapped_column(String(160), nullable=True)
    supplier_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    image_nonlocked_allowed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
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

class ProductSKU(Base):
    __tablename__ = "product_skus"
    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "sku_code",
            name="uq_product_sku_product_code",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    product_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    sku_code: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    option_value: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )
    barcode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sales_unit: Mapped[str] = mapped_column(String(32), default="each", nullable=False)
    purchase_cost: Mapped[int | None] = mapped_column(Integer, nullable=True)
    list_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sale_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    available_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    safety_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    incoming_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    storage_location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        default="active",
        nullable=False,
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


class CommerceCodeCounter(Base):
    __tablename__ = "commerce_code_counters"

    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("business_workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    next_product_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class SalesChannelListing(Base):
    __tablename__ = "sales_channel_listings"
    __table_args__ = (
        UniqueConstraint("sku_id", "channel", name="uq_channel_listing_sku_channel"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    sku_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("product_skus.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    external_product_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    external_sku_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="unlinked", nullable=False)
    channel_product_name: Mapped[str | None] = mapped_column(String(240), nullable=True)
    channel_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

class ProductDetail(Base):
    __tablename__ = "product_details"
    __table_args__ = (
        UniqueConstraint(
            "product_id",
            name="uq_product_detail_product",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    product_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    specification: Mapped[str | None] = mapped_column(
        String(240),
        nullable=True,
    )
    usage: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    installation_method: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    usage_conditions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    cautions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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

class ProductComponent(Base):
    __tablename__ = "product_components"
    __table_args__ = (
        UniqueConstraint(
            "sku_id",
            "component_code",
            name="uq_product_component_sku_code",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    product_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    sku_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("product_skus.id", ondelete="CASCADE"),
        nullable=False,
    )
    component_code: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    unit: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="active",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )


# --- M-05 IMAGE STUDIO MODELS ---

class ImageGenerationJob(Base):
    __tablename__ = "image_generation_jobs"

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
    sku_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("product_skus.id", ondelete="SET NULL"), nullable=True
    )
    image_type: Mapped[str] = mapped_column(String(40), nullable=False)
    style_preset: Mapped[str] = mapped_column(String(64), nullable=False)
    usage_context: Mapped[str] = mapped_column(String(64), nullable=False)
    aspect_ratio: Mapped[str] = mapped_column(String(16), nullable=False, default="4:3")
    custom_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    custom_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    protection_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default="hard_lock"
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    request_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    p0_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="openai")
    model_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    preview_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    final_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_micros: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actual_cost_micros: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class ImageReferenceAsset(Base):
    __tablename__ = "image_reference_assets"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("image_generation_jobs.id", ondelete="CASCADE"), nullable=True
    )
    asset_role: Mapped[str] = mapped_column(String(48), nullable=False)
    component_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    asset_uri: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    internal_reference_only: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    lock_level: Mapped[str] = mapped_column(
        String(24), nullable=False, default="hard_lock"
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class ImageGeneratedAsset(Base):
    __tablename__ = "image_generated_assets"
    __table_args__ = (
        UniqueConstraint(
            "job_id", "asset_stage", "version_no", name="uq_image_asset_job_stage_version"
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("image_generation_jobs.id", ondelete="CASCADE"), nullable=False
    )
    asset_stage: Mapped[str] = mapped_column(String(24), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="review")
    asset_uri: Mapped[str] = mapped_column(Text, nullable=False)
    asset_name: Mapped[str | None] = mapped_column(String(240), nullable=True)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    usage_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    asset_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(40), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    qa_status: Mapped[str] = mapped_column(String(24), nullable=False, default="review")
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    export_status: Mapped[str] = mapped_column(String(24), nullable=False, default="not_exported")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class ImageReviewEvent(Base):
    __tablename__ = "image_review_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("image_generation_jobs.id", ondelete="CASCADE"), nullable=False
    )
    generated_asset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("image_generated_assets.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class ImageQAResult(Base):
    __tablename__ = "image_qa_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("image_generation_jobs.id", ondelete="CASCADE"), nullable=False
    )
    generated_asset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("image_generated_assets.id", ondelete="CASCADE"), nullable=True
    )
    check_code: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


# --- M-06 DETAIL PAGE STUDIO MODELS ---

class BrandStyleSheet(Base):
    __tablename__ = "brand_style_sheets"
    __table_args__ = (
        UniqueConstraint("tenant_id", "workspace_id", "name", name="uq_brand_style_tenant_workspace_name"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("business_workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    logo_asset_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#1F6B4F")
    secondary_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#A7C4B5")
    accent_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#E7B65A")
    background_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#FFFFFF")
    surface_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#F5F7F6")
    text_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#17211C")
    muted_text_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#66756D")
    brand_font_primary: Mapped[str | None] = mapped_column(String(120), nullable=True)
    brand_font_secondary: Mapped[str | None] = mapped_column(String(120), nullable=True)
    image_style_rules: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    color_lock_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class DetailPageTemplate(Base):
    __tablename__ = "detail_page_templates"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_detail_template_tenant_code"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    layout_rules: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    canva_brand_template_id: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # User-managed template settings. Published templates are immutable;
    # edits create a new version linked through parent_template_id.
    workspace_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("business_workspaces.id", ondelete="CASCADE"), nullable=True
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parent_template_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("detail_page_templates.id", ondelete="SET NULL"), nullable=True
    )
    content_rules: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    field_bindings: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    category_scope: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    channel_scope: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    canva_design_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    canva_edit_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class ProductRelation(Base):
    __tablename__ = "product_relations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    target_product_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=True
    )
    relation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(240), nullable=True)
    target_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_asset_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class ReviewSource(Base):
    __tablename__ = "review_sources"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(80), nullable=False)
    external_review_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    review_text: Mapped[str] = mapped_column(Text, nullable=False)
    photo_asset_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class DetailPageJob(Base):
    __tablename__ = "detail_page_jobs"

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
    channel: Mapped[str] = mapped_column(String(80), nullable=False, default="naver-smartstore")
    page_length: Mapped[str] = mapped_column(String(16), nullable=False, default="long")
    generation_mode: Mapped[str] = mapped_column(
        String(16), nullable=False, default="manual"
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    current_version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    approved_version_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class DetailPageVersion(Base):
    __tablename__ = "detail_page_versions"
    __table_args__ = (
        UniqueConstraint("job_id", "version_no", name="uq_detail_page_job_version"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("detail_page_jobs.id", ondelete="CASCADE"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    template_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("detail_page_templates.id", ondelete="RESTRICT"), nullable=False
    )
    brand_style_sheet_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("brand_style_sheets.id", ondelete="RESTRICT"), nullable=False
    )
    visual_style: Mapped[str] = mapped_column(String(40), nullable=False, default="natural")
    page_strategy: Mapped[str] = mapped_column(String(40), nullable=False, default="review_first")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    fact_snapshot_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    template_snapshot_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    external_design_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    external_design_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class DetailPageSection(Base):
    __tablename__ = "detail_page_sections"
    __table_args__ = (
        UniqueConstraint("version_id", "sort_order", name="uq_detail_section_version_order"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("detail_page_versions.id", ondelete="CASCADE"), nullable=False
    )
    section_type: Mapped[str] = mapped_column(String(48), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    layout_variant: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_type: Mapped[str] = mapped_column(String(24), nullable=False, default="copy")
    content_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    image_asset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("image_generated_assets.id", ondelete="SET NULL"), nullable=True
    )
    qa_status: Mapped[str] = mapped_column(String(16), nullable=False, default="review")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class DetailPageQAResult(Base):
    __tablename__ = "detail_page_qa_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("detail_page_jobs.id", ondelete="CASCADE"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    section_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("detail_page_sections.id", ondelete="CASCADE"), nullable=True
    )
    check_code: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_fix: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class DetailPageExport(Base):
    __tablename__ = "detail_page_exports"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("detail_page_jobs.id", ondelete="CASCADE"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    export_type: Mapped[str] = mapped_column(String(32), nullable=False, default="canva_package")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="ready")
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    external_design_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    external_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
