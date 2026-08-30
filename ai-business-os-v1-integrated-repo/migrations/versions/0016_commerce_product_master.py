"""integrated commerce product master

Revision ID: 0016_commerce_master
Revises: 0015_google_drive
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_commerce_master"
down_revision = "0015_google_drive"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("product_skus", sa.Column("barcode", sa.String(64), nullable=True))
    op.add_column("product_skus", sa.Column("sales_unit", sa.String(32), nullable=False, server_default="each"))
    op.create_index("ix_product_skus_barcode", "product_skus", ["tenant_id", "barcode"], unique=True,
                    postgresql_where=sa.text("barcode IS NOT NULL"))
    op.create_table(
        "commerce_code_counters",
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("business_workspaces.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("next_product_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "sales_channel_listings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku_id", sa.String(36), sa.ForeignKey("product_skus.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("external_product_id", sa.String(160), nullable=True),
        sa.Column("external_sku_id", sa.String(160), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="unlinked"),
        sa.Column("channel_product_name", sa.String(240), nullable=True),
        sa.Column("channel_price", sa.Integer(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("sku_id", "channel", name="uq_channel_listing_sku_channel"),
    )
    op.create_index("ix_channel_listings_tenant_product", "sales_channel_listings", ["tenant_id", "product_id"])


def downgrade():
    op.drop_index("ix_channel_listings_tenant_product", table_name="sales_channel_listings")
    op.drop_table("sales_channel_listings")
    op.drop_table("commerce_code_counters")
    op.drop_index("ix_product_skus_barcode", table_name="product_skus")
    op.drop_column("product_skus", "sales_unit")
    op.drop_column("product_skus", "barcode")
