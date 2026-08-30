"""business workspace product sku master

Revision ID: 0003_business_workspace
Revises: 0002_agent_control
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_business_workspace"
down_revision = "0002_agent_control"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "business_workspaces",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column(
            "business_type",
            sa.String(length=80),
            nullable=False,
            server_default="commerce",
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "mode",
            sa.String(length=32),
            nullable=False,
            server_default="shadow",
        ),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "slug",
            name="uq_business_workspace_tenant_slug",
        ),
        sa.CheckConstraint(
            "mode IN ('shadow', 'controlled_live', 'live')",
            name="ck_business_workspace_mode",
        ),
    )

    op.create_index(
        "ix_business_workspaces_tenant_id",
        "business_workspaces",
        ["tenant_id"],
        unique=False,
    )

    op.create_table(
        "products",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("product_code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("sales_channel", sa.String(length=80), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
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
            ["workspace_id"],
            ["business_workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "product_code",
            name="uq_product_workspace_code",
        ),
    )

    op.create_index(
        "ix_products_tenant_workspace",
        "products",
        ["tenant_id", "workspace_id"],
        unique=False,
    )

    op.create_table(
        "product_skus",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=False),
        sa.Column("sku_code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("option_value", sa.String(length=120), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="active",
        ),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "product_id",
            "sku_code",
            name="uq_product_sku_product_code",
        ),
    )

    op.create_index(
        "ix_product_skus_tenant_product",
        "product_skus",
        ["tenant_id", "product_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_product_skus_tenant_product",
        table_name="product_skus",
    )
    op.drop_table("product_skus")

    op.drop_index(
        "ix_products_tenant_workspace",
        table_name="products",
    )
    op.drop_table("products")

    op.drop_index(
        "ix_business_workspaces_tenant_id",
        table_name="business_workspaces",
    )
    op.drop_table("business_workspaces")
