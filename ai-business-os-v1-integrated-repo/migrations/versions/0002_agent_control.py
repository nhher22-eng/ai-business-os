"""agent manual control and runtime gate

Revision ID: 0002_agent_control
Revises: 0001_initial
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_agent_control"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    # Compatibility identity for pre-vNext workloads.
    # Server defaults intentionally remain during the compatibility window
    # so the previous GA application can still insert rows after app rollback.
    op.add_column(
        "runs",
        sa.Column(
            "tenant_id",
            sa.String(128),
            nullable=False,
            server_default="__legacy__",
        ),
    )
    op.add_column(
        "runs",
        sa.Column(
            "agent_id",
            sa.String(128),
            nullable=False,
            server_default="__legacy_default_agent__",
        ),
    )

    op.create_index(
        "ix_runs_tenant_agent",
        "runs",
        ["tenant_id", "agent_id"],
    )

    op.create_table(
        "agent_control_states",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("agent_id", sa.String(128), nullable=False),
        sa.Column(
            "desired_state",
            sa.String(16),
            nullable=False,
            server_default="on",
        ),
        sa.Column("changed_by", sa.String(128), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "agent_id",
            name="uq_agent_control_state",
        ),
        sa.CheckConstraint(
            "desired_state IN ('on','paused','off')",
            name="ck_agent_control_desired_state",
        ),
    )

    op.create_table(
        "tenant_automation_states",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column(
            "paused",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("changed_by", sa.String(128), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            name="uq_tenant_automation_state",
        ),
    )

    op.create_table(
        "safety_gate_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("agent_id", sa.String(128), nullable=False),
        sa.Column("run_id", sa.String(36), nullable=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("allowed", sa.Boolean(), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("reason_code", sa.String(128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index(
        "ix_safety_gate_results_created",
        "safety_gate_results",
        ["created_at"],
    )


def downgrade():
    op.drop_index(
        "ix_safety_gate_results_created",
        table_name="safety_gate_results",
    )
    op.drop_table("safety_gate_results")
    op.drop_table("tenant_automation_states")
    op.drop_table("agent_control_states")

    op.drop_index("ix_runs_tenant_agent", table_name="runs")
    op.drop_column("runs", "agent_id")
    op.drop_column("runs", "tenant_id")
