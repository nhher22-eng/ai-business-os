"""canva oauth connections

Revision ID: 0020_canva_connections
Revises: 0019_service_management
"""
from alembic import op
import sqlalchemy as sa

revision = "0020_canva_connections"
down_revision = "0019_service_management"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "canva_connections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", name="uq_canva_connection_tenant"),
    )


def downgrade():
    op.drop_table("canva_connections")
