"""google drive connections

Revision ID: 0015_google_drive
Revises: 0014_product_sources
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_google_drive"
down_revision = "0014_product_sources"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "google_drive_connections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("root_folder_id", sa.String(255), nullable=False),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("folder_map", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", name="uq_google_drive_connection_tenant"),
    )


def downgrade():
    op.drop_table("google_drive_connections")
