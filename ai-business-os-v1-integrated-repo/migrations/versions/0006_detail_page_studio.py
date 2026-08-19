"""detail page studio core

Revision ID: 0006_detail_page_studio
Revises: 0005_image_studio
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_detail_page_studio"
down_revision = "0005_image_studio"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "brand_style_sheets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("workspace_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("logo_asset_uri", sa.Text(), nullable=True),
        sa.Column("primary_color", sa.String(7), nullable=False, server_default="#1F6B4F"),
        sa.Column("secondary_color", sa.String(7), nullable=False, server_default="#A7C4B5"),
        sa.Column("accent_color", sa.String(7), nullable=False, server_default="#E7B65A"),
        sa.Column("background_color", sa.String(7), nullable=False, server_default="#FFFFFF"),
        sa.Column("surface_color", sa.String(7), nullable=False, server_default="#F5F7F6"),
        sa.Column("text_color", sa.String(7), nullable=False, server_default="#17211C"),
        sa.Column("muted_text_color", sa.String(7), nullable=False, server_default="#66756D"),
        sa.Column("brand_font_primary", sa.String(120), nullable=True),
        sa.Column("brand_font_secondary", sa.String(120), nullable=True),
        sa.Column("image_style_rules", sa.JSON(), nullable=True),
        sa.Column("color_lock_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["workspace_id"], ["business_workspaces.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "workspace_id", "name", name="uq_brand_style_tenant_workspace_name"),
    )

    op.create_table(
        "detail_page_templates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("layout_rules", sa.JSON(), nullable=True),
        sa.Column("canva_brand_template_id", sa.String(120), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "code", name="uq_detail_template_tenant_code"),
    )

    op.create_table(
        "product_relations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("source_product_id", sa.String(36), nullable=False),
        sa.Column("target_product_id", sa.String(36), nullable=True),
        sa.Column("relation_type", sa.String(32), nullable=False),
        sa.Column("display_name", sa.String(240), nullable=True),
        sa.Column("target_url", sa.Text(), nullable=True),
        sa.Column("image_asset_uri", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["source_product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_product_id"], ["products.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_product_relations_source_type",
        "product_relations",
        ["tenant_id", "source_product_id", "relation_type"],
        unique=False,
    )

    op.create_table(
        "review_sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("channel", sa.String(80), nullable=False),
        sa.Column("external_review_id", sa.String(160), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("review_text", sa.Text(), nullable=False),
        sa.Column("photo_asset_uri", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_review_sources_product",
        "review_sources",
        ["tenant_id", "product_id"],
        unique=False,
    )

    op.create_table(
        "detail_page_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("workspace_id", sa.String(36), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("channel", sa.String(80), nullable=False, server_default="naver-smartstore"),
        sa.Column("page_length", sa.String(16), nullable=False, server_default="long"),
        sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
        sa.Column("current_version_no", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("approved_version_no", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["workspace_id"], ["business_workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_detail_jobs_tenant_product",
        "detail_page_jobs",
        ["tenant_id", "product_id"],
        unique=False,
    )

    op.create_table(
        "detail_page_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.String(36), nullable=False),
        sa.Column("brand_style_sheet_id", sa.String(36), nullable=False),
        sa.Column("visual_style", sa.String(40), nullable=False, server_default="natural"),
        sa.Column("page_strategy", sa.String(40), nullable=False, server_default="review_first"),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("fact_snapshot_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["job_id"], ["detail_page_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["detail_page_templates.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["brand_style_sheet_id"], ["brand_style_sheets.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("job_id", "version_no", name="uq_detail_page_job_version"),
    )

    op.create_table(
        "detail_page_sections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("section_type", sa.String(48), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("layout_variant", sa.String(64), nullable=True),
        sa.Column("source_type", sa.String(24), nullable=False, server_default="copy"),
        sa.Column("content_json", sa.JSON(), nullable=True),
        sa.Column("image_asset_id", sa.String(36), nullable=True),
        sa.Column("qa_status", sa.String(16), nullable=False, server_default="review"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["version_id"], ["detail_page_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["image_asset_id"], ["image_generated_assets.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("version_id", "sort_order", name="uq_detail_section_version_order"),
    )
    op.create_index(
        "ix_detail_sections_version",
        "detail_page_sections",
        ["version_id", "sort_order"],
        unique=False,
    )

    op.create_table(
        "detail_page_qa_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("section_id", sa.String(36), nullable=True),
        sa.Column("check_code", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="info"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("suggested_fix", sa.Text(), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["job_id"], ["detail_page_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["section_id"], ["detail_page_sections.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "detail_page_exports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("export_type", sa.String(32), nullable=False, server_default="canva_package"),
        sa.Column("status", sa.String(24), nullable=False, server_default="ready"),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("external_design_id", sa.String(160), nullable=True),
        sa.Column("external_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["job_id"], ["detail_page_jobs.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("detail_page_exports")
    op.drop_table("detail_page_qa_results")
    op.drop_index("ix_detail_sections_version", table_name="detail_page_sections")
    op.drop_table("detail_page_sections")
    op.drop_table("detail_page_versions")
    op.drop_index("ix_detail_jobs_tenant_product", table_name="detail_page_jobs")
    op.drop_table("detail_page_jobs")
    op.drop_index("ix_review_sources_product", table_name="review_sources")
    op.drop_table("review_sources")
    op.drop_index("ix_product_relations_source_type", table_name="product_relations")
    op.drop_table("product_relations")
    op.drop_table("detail_page_templates")
    op.drop_table("brand_style_sheets")
