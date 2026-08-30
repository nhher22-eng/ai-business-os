"""M09 product operations history

Revision ID: 0009_product_operations
Revises: 0008_detail_page_content_basis
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_product_operations"
down_revision = "0008_detail_page_content_basis"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "product_change_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("changed_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_product_change_events_product_created",
        "product_change_events",
        ["product_id", "created_at"],
    )


def downgrade():
    op.drop_index("ix_product_change_events_product_created", table_name="product_change_events")
    op.drop_table("product_change_events")
