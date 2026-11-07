"""Add durable outbox for Celery task dispatch."""
from alembic import op
import sqlalchemy as sa

revision = "0002_task_dispatch_outbox"
down_revision = "0001_order_outbox"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "task_dispatch_outbox",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_task_dispatch_outbox_order_id", "task_dispatch_outbox", ["order_id"])
    op.create_index("ix_task_dispatch_outbox_status", "task_dispatch_outbox", ["status"])


def downgrade():
    op.drop_index("ix_task_dispatch_outbox_status", table_name="task_dispatch_outbox")
    op.drop_index("ix_task_dispatch_outbox_order_id", table_name="task_dispatch_outbox")
    op.drop_table("task_dispatch_outbox")
