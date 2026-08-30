"""product registration master profile

Revision ID: 0007_product_registration
Revises: 0006_detail_page_studio
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_product_registration"
down_revision = "0006_detail_page_studio"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_registration_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("model_name", sa.String(160), nullable=True),
        sa.Column("primary_material", sa.String(240), nullable=True),
        sa.Column("secondary_material", sa.String(240), nullable=True),
        sa.Column("weight", sa.String(120), nullable=True),
        sa.Column("dimensions", sa.JSON(), nullable=True),
        sa.Column("manufacturer", sa.String(240), nullable=True),
        sa.Column("country_of_origin", sa.String(160), nullable=True),
        sa.Column("certifications", sa.JSON(), nullable=True),
        sa.Column("packaging", sa.JSON(), nullable=True),
        sa.Column("fact_notes", sa.Text(), nullable=True),
        sa.Column("facts_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("facts_confirmed_by", sa.String(128), nullable=True),
        sa.Column("facts_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("operating_info", sa.JSON(), nullable=True),
        sa.Column("marketing_info", sa.JSON(), nullable=True),
        sa.Column("ai_suggestions", sa.JSON(), nullable=True),
        sa.Column("ai_suggestion_meta", sa.JSON(), nullable=True),
        sa.Column("primary_image_asset_id", sa.String(36), nullable=True),
        sa.Column("additional_image_asset_ids", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("product_id", name="uq_product_registration_profile_product"),
    )
    op.create_index(
        "ix_product_registration_tenant_product",
        "product_registration_profiles",
        ["tenant_id", "product_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_product_registration_tenant_product",
        table_name="product_registration_profiles",
    )
    op.drop_table("product_registration_profiles")
