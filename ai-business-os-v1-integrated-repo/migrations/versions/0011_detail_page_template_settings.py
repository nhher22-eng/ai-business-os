"""detail page template settings and generation modes

Revision ID: 0011_detail_templates
Revises: 0010_product_image_fact
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_detail_templates"
down_revision = "0010_product_image_fact"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "detail_page_templates",
        sa.Column("workspace_id", sa.String(36), nullable=True),
    )
    op.add_column(
        "detail_page_templates",
        sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "detail_page_templates",
        sa.Column("parent_template_id", sa.String(36), nullable=True),
    )
    op.add_column(
        "detail_page_templates",
        sa.Column("content_rules", sa.JSON(), nullable=True),
    )
    op.add_column(
        "detail_page_templates",
        sa.Column("field_bindings", sa.JSON(), nullable=True),
    )
    op.add_column(
        "detail_page_templates",
        sa.Column("category_scope", sa.JSON(), nullable=True),
    )
    op.add_column(
        "detail_page_templates",
        sa.Column("channel_scope", sa.JSON(), nullable=True),
    )
    op.add_column(
        "detail_page_templates",
        sa.Column("canva_design_id", sa.String(160), nullable=True),
    )
    op.add_column(
        "detail_page_templates",
        sa.Column("canva_edit_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "detail_page_templates",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "detail_page_templates",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_foreign_key(
        "fk_detail_templates_workspace",
        "detail_page_templates",
        "business_workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_detail_templates_parent",
        "detail_page_templates",
        "detail_page_templates",
        ["parent_template_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_detail_templates_workspace_status",
        "detail_page_templates",
        ["tenant_id", "workspace_id", "status"],
        unique=False,
    )

    op.add_column(
        "detail_page_jobs",
        sa.Column(
            "generation_mode",
            sa.String(16),
            nullable=False,
            server_default="manual",
        ),
    )

    op.add_column(
        "detail_page_versions",
        sa.Column("template_snapshot_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "detail_page_versions",
        sa.Column("external_design_id", sa.String(160), nullable=True),
    )
    op.add_column(
        "detail_page_versions",
        sa.Column("external_design_url", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("detail_page_versions", "external_design_url")
    op.drop_column("detail_page_versions", "external_design_id")
    op.drop_column("detail_page_versions", "template_snapshot_json")

    op.drop_column("detail_page_jobs", "generation_mode")

    op.drop_index(
        "ix_detail_templates_workspace_status",
        table_name="detail_page_templates",
    )
    op.drop_constraint(
        "fk_detail_templates_parent",
        "detail_page_templates",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_detail_templates_workspace",
        "detail_page_templates",
        type_="foreignkey",
    )
    op.drop_column("detail_page_templates", "updated_at")
    op.drop_column("detail_page_templates", "published_at")
    op.drop_column("detail_page_templates", "canva_edit_url")
    op.drop_column("detail_page_templates", "canva_design_id")
    op.drop_column("detail_page_templates", "channel_scope")
    op.drop_column("detail_page_templates", "category_scope")
    op.drop_column("detail_page_templates", "field_bindings")
    op.drop_column("detail_page_templates", "content_rules")
    op.drop_column("detail_page_templates", "parent_template_id")
    op.drop_column("detail_page_templates", "version_no")
    op.drop_column("detail_page_templates", "workspace_id")
