"""product source assets

Revision ID: 0014_product_sources
Revises: 0013_image_asset_meta
"""

from alembic import op
import sqlalchemy as sa

revision = "0014_product_sources"
down_revision = "0013_image_asset_meta"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_source_assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_kind", sa.String(48), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(160), nullable=True),
        sa.Column("asset_uri", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_product_source_assets_tenant_id", "product_source_assets", ["tenant_id"])
    op.create_index("ix_product_source_assets_product_id", "product_source_assets", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_product_source_assets_product_id", table_name="product_source_assets")
    op.drop_index("ix_product_source_assets_tenant_id", table_name="product_source_assets")
    op.drop_table("product_source_assets")
