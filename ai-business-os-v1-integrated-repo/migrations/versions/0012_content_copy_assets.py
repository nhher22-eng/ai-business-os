"""approved content copy assets

Revision ID: 0012_content_copy
Revises: 0011_detail_templates
"""

from alembic import op
import sqlalchemy as sa


revision = "0012_content_copy"
down_revision = "0011_detail_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_copy_assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("workspace_id", sa.String(36), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("target_type", sa.String(40), nullable=False),
        sa.Column("slot_key", sa.String(80), nullable=False),
        sa.Column("slot_label", sa.String(160), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="candidate"),
        sa.Column("source_fact_keys", sa.JSON(), nullable=True),
        sa.Column("generation_method", sa.String(32), nullable=False, server_default="fact_substitution"),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("approved_by", sa.String(128), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["workspace_id"], ["business_workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("product_id", "target_type", "slot_key", "version_no", name="uq_content_copy_asset_version"),
    )
    op.create_index(
        "ix_content_copy_product_status",
        "content_copy_assets",
        ["tenant_id", "product_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_content_copy_product_status", table_name="content_copy_assets")
    op.drop_table("content_copy_assets")
