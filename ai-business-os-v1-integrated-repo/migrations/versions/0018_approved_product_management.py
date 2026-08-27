"""approved product management UI data

Revision ID: 0018_approved_product_ui
Revises: 0017_product_management
"""
from alembic import op
import sqlalchemy as sa


revision = "0018_approved_product_ui"
down_revision = "0017_product_management"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("product_skus", sa.Column("shipping_fee", sa.Integer(), nullable=True))
    for name in ("hero_image_asset_id", "right45_image_asset_id", "front_image_asset_id"):
        op.add_column("product_registration_profiles", sa.Column(name, sa.String(36), nullable=True))


def downgrade():
    for name in ("front_image_asset_id", "right45_image_asset_id", "hero_image_asset_id"):
        op.drop_column("product_registration_profiles", name)
    op.drop_column("product_skus", "shipping_fee")
