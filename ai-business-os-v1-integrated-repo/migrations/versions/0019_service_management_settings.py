"""service connection and billing management metadata

Revision ID: 0019_service_management
Revises: 0018_approved_product_ui
"""
from alembic import op
import sqlalchemy as sa


revision = "0019_service_management"
down_revision = "0018_approved_product_ui"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "service_management_settings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("service_code", sa.String(64), nullable=False),
        sa.Column("plan_name", sa.String(160), nullable=True),
        sa.Column("billing_status", sa.String(32), nullable=False, server_default="manual_check"),
        sa.Column("current_month_cost_krw", sa.Integer(), nullable=True),
        sa.Column("monthly_budget_krw", sa.Integer(), nullable=True),
        sa.Column("renewal_date", sa.Date(), nullable=True),
        sa.Column("usage_summary", sa.String(240), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("updated_by", sa.String(128), nullable=False, server_default="dashboard-user"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "service_code", name="uq_service_setting_tenant_code"),
    )


def downgrade():
    op.drop_table("service_management_settings")
