"""initial AI Business OS runtime tables"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

run_status = postgresql.ENUM("queued", "running", "succeeded", "failed", name="runstatus", create_type=False)

def upgrade():
    run_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task", sa.Text(), nullable=False),
        sa.Column("status", run_status, nullable=False),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "worker_heartbeats",
        sa.Column("worker_id", sa.String(128), primary_key=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "scheduled_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.String(128), nullable=False, unique=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
    )
    op.create_table(
        "webhook_outbox",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

def downgrade():
    op.drop_table("webhook_outbox")
    op.drop_table("scheduled_jobs")
    op.drop_table("worker_heartbeats")
    op.drop_table("runs")
    run_status.drop(op.get_bind(), checkfirst=True)
