"""canva autofill runs

Revision ID: 0021_canva_autofill_runs
Revises: 0020_canva_connections
"""
from alembic import op
import sqlalchemy as sa

revision = "0021_canva_autofill_runs"
down_revision = "0020_canva_connections"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "canva_autofill_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("brand_template_id", sa.String(255), nullable=False),
        sa.Column("canva_job_id", sa.String(255), nullable=False, unique=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("design_id", sa.String(255), nullable=True),
        sa.Column("design_url", sa.Text(), nullable=True),
        sa.Column("error_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("canva_autofill_runs")
