"""outbox / billing-job indexes for the worker and reminder lookups

Revision ID: 0003
Revises: 0002
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

INDEXES = [
    ("idx_outbox_status_created", "outbox_events", ["status", "created_at"]),
    ("idx_outbox_type_aggregate", "outbox_events", ["event_type", "aggregate_id"]),
    ("idx_billing_jobs_created", "billing_jobs", ["created_at"]),
]

def upgrade():
    for name, table, cols in INDEXES: op.create_index(name, table, cols)

def downgrade():
    for name, table, _ in reversed(INDEXES): op.drop_index(name, table_name=table)
