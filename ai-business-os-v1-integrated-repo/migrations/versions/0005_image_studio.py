"""image studio core

Revision ID: 0005_image_studio
Revises: 0004_product_detail
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_image_studio"
down_revision = "0004_product_detail"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("image_nonlocked_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "image_generation_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("workspace_id", sa.String(36), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("sku_id", sa.String(36), nullable=True),
        sa.Column("image_type", sa.String(40), nullable=False),
        sa.Column("style_preset", sa.String(64), nullable=False),
        sa.Column("usage_context", sa.String(64), nullable=False),
        sa.Column("aspect_ratio", sa.String(16), nullable=False, server_default="4:3"),
        sa.Column("custom_width", sa.Integer(), nullable=True),
        sa.Column("custom_height", sa.Integer(), nullable=True),
        sa.Column("protection_mode", sa.String(32), nullable=False, server_default="hard_lock"),
        sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
        sa.Column("request_text", sa.Text(), nullable=True),
        sa.Column("p0_summary", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(40), nullable=False, server_default="openai"),
        sa.Column("model_name", sa.String(80), nullable=True),
        sa.Column("preview_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("final_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost_micros", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actual_cost_micros", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["workspace_id"], ["business_workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sku_id"], ["product_skus.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_image_jobs_tenant_product_status",
        "image_generation_jobs",
        ["tenant_id", "product_id", "status"],
        unique=False,
    )

    op.create_table(
        "image_reference_assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("job_id", sa.String(36), nullable=True),
        sa.Column("asset_role", sa.String(48), nullable=False),
        sa.Column("component_code", sa.String(128), nullable=True),
        sa.Column("asset_uri", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("internal_reference_only", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("lock_level", sa.String(24), nullable=False, server_default="hard_lock"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["image_generation_jobs.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_image_refs_product_job",
        "image_reference_assets",
        ["tenant_id", "product_id", "job_id"],
        unique=False,
    )

    op.create_table(
        "image_generated_assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("asset_stage", sa.String(24), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(32), nullable=False, server_default="review"),
        sa.Column("asset_uri", sa.Text(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("provider_name", sa.String(40), nullable=True),
        sa.Column("model_name", sa.String(80), nullable=True),
        sa.Column("qa_status", sa.String(24), nullable=False, server_default="review"),
        sa.Column("approved_by", sa.String(128), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("export_status", sa.String(24), nullable=False, server_default="not_exported"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["job_id"], ["image_generation_jobs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("job_id", "asset_stage", "version_no", name="uq_image_asset_job_stage_version"),
    )
    op.create_index(
        "ix_image_assets_job_stage",
        "image_generated_assets",
        ["job_id", "asset_stage"],
        unique=False,
    )

    op.create_table(
        "image_review_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("generated_asset_id", sa.String(36), nullable=True),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["job_id"], ["image_generation_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["generated_asset_id"], ["image_generated_assets.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "image_qa_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("generated_asset_id", sa.String(36), nullable=True),
        sa.Column("check_code", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="info"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["job_id"], ["image_generation_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["generated_asset_id"], ["image_generated_assets.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_column("products", "image_nonlocked_allowed")
    op.drop_table("image_qa_results")
    op.drop_table("image_review_events")
    op.drop_index("ix_image_assets_job_stage", table_name="image_generated_assets")
    op.drop_table("image_generated_assets")
    op.drop_index("ix_image_refs_product_job", table_name="image_reference_assets")
    op.drop_table("image_reference_assets")
    op.drop_index("ix_image_jobs_tenant_product_status", table_name="image_generation_jobs")
    op.drop_table("image_generation_jobs")
