"""standard product management stage one

Revision ID: 0017_product_management
Revises: 0016_commerce_master
"""
from alembic import op
import sqlalchemy as sa


revision = "0017_product_management"
down_revision = "0016_commerce_master"
branch_labels = None
depends_on = None


def upgrade():
    for name, length in (
        ("category", 160),
        ("brand", 160),
        ("model_name", 160),
        ("manufacturer", 200),
        ("country_of_origin", 160),
        ("supplier_name", 200),
    ):
        op.add_column("products", sa.Column(name, sa.String(length), nullable=True))

    op.add_column("product_skus", sa.Column("purchase_cost", sa.Integer(), nullable=True))
    op.add_column("product_skus", sa.Column("list_price", sa.Integer(), nullable=True))
    op.add_column("product_skus", sa.Column("sale_price", sa.Integer(), nullable=True))
    for name in ("current_stock", "available_stock", "safety_stock", "incoming_stock"):
        op.add_column(
            "product_skus",
            sa.Column(name, sa.Integer(), nullable=False, server_default="0"),
        )
    op.add_column("product_skus", sa.Column("storage_location", sa.String(160), nullable=True))

    # Existing verified FACT values seed the standard master without changing
    # or deleting the original registration profile.
    op.execute(sa.text("""
        UPDATE products AS p
           SET model_name = COALESCE(p.model_name, r.model_name),
               manufacturer = COALESCE(p.manufacturer, r.manufacturer),
               country_of_origin = COALESCE(p.country_of_origin, r.country_of_origin)
          FROM product_registration_profiles AS r
         WHERE r.product_id = p.id
    """))


def downgrade():
    for name in (
        "storage_location", "incoming_stock", "safety_stock", "available_stock",
        "current_stock", "sale_price", "list_price", "purchase_cost",
    ):
        op.drop_column("product_skus", name)
    for name in (
        "supplier_name", "country_of_origin", "manufacturer", "model_name",
        "brand", "category",
    ):
        op.drop_column("products", name)
