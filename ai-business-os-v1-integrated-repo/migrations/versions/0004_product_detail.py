"""product detail and components

Revision ID: 0004_product_detail
Revises: 0003_business_workspace
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_product_detail"
down_revision = "0003_business_workspace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_details",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("specification", sa.String(240), nullable=True),
        sa.Column("usage", sa.Text(), nullable=True),
        sa.Column("installation_method", sa.Text(), nullable=True),
        sa.Column("usage_conditions", sa.Text(), nullable=True),
        sa.Column("cautions", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "product_id",
            name="uq_product_detail_product",
        ),
    )

    op.create_table(
        "product_components",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("sku_id", sa.String(36), nullable=False),
        sa.Column("component_code", sa.String(128), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit", sa.String(40), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sku_id"],
            ["product_skus.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "sku_id",
            "component_code",
            name="uq_product_component_sku_code",
        ),
    )


def downgrade() -> None:
    op.drop_table("product_components")
    op.drop_table("product_details")
