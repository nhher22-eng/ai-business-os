"""product image FACT workflow

Revision ID: 0010_product_image_fact
Revises: 0009_product_operations
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_product_image_fact"
down_revision = "0009_product_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_image_facts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("slot_type", sa.String(40), nullable=False, server_default="UNASSIGNED"),
        sa.Column("slot_index", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(32), nullable=False, server_default="uploaded"),
        sa.Column("source_kind", sa.String(32), nullable=False, server_default="temporary_capture"),
        sa.Column("raw_asset_uri", sa.Text(), nullable=True),
        sa.Column("fact_asset_uri", sa.Text(), nullable=True),
        sa.Column("reference_asset_id", sa.String(36), nullable=True),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("classification_source", sa.String(32), nullable=True),
        sa.Column("classification_confidence", sa.Float(), nullable=True),
        sa.Column("background_removed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("keep_background", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("raw_retention_policy", sa.String(32), nullable=False, server_default="delete_on_confirm"),
        sa.Column("raw_deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by", sa.String(128), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reference_asset_id"], ["image_reference_assets.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_product_image_facts_product",
        "product_image_facts",
        ["tenant_id", "product_id", "slot_type", "status"],
        unique=False,
    )
    op.create_index(
        "ix_product_image_facts_reference_asset",
        "product_image_facts",
        ["reference_asset_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_product_image_facts_reference_asset", table_name="product_image_facts")
    op.drop_index("ix_product_image_facts_product", table_name="product_image_facts")
    op.drop_table("product_image_facts")
