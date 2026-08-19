"""detail page content basis

Revision ID: 0008_detail_page_content_basis
Revises: 0007_product_registration
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_detail_page_content_basis"
down_revision = "0007_product_registration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "detail_page_content_basis",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("basis", sa.JSON(), nullable=True),
        sa.Column("source", sa.String(32), nullable=False, server_default="product_master"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["job_id"], ["detail_page_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["detail_page_versions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("version_id", name="uq_detail_page_content_basis_version"),
    )
    op.create_index(
        "ix_detail_page_content_basis_job_version",
        "detail_page_content_basis",
        ["tenant_id", "job_id", "version_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_detail_page_content_basis_job_version",
        table_name="detail_page_content_basis",
    )
    op.drop_table("detail_page_content_basis")
