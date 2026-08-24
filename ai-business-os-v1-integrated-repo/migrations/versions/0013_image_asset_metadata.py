"""image element asset naming and metadata

Revision ID: 0013_image_asset_meta
Revises: 0012_content_copy
"""

from alembic import op
import sqlalchemy as sa


revision = "0013_image_asset_meta"
down_revision = "0012_content_copy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column in (
        sa.Column("asset_name", sa.String(240), nullable=True),
        sa.Column("filename", sa.String(255), nullable=True),
        sa.Column("role_code", sa.String(64), nullable=True),
        sa.Column("usage_code", sa.String(64), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("asset_metadata", sa.JSON(), nullable=True),
    ):
        op.add_column("image_generated_assets", column)
    op.create_index(
        "ix_image_generated_content_hash",
        "image_generated_assets",
        ["tenant_id", "content_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_image_generated_content_hash", table_name="image_generated_assets")
    for name in ("asset_metadata", "content_hash", "usage_code", "role_code", "filename", "asset_name"):
        op.drop_column("image_generated_assets", name)
