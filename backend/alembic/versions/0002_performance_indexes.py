"""query-performance indexes (list pages, reports, overdue lookups)

Revision ID: 0002
Revises: 0001
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

INDEXES = [
    ("idx_invoices_issue_date", "invoices", ['issue_date']),
    ("idx_invoices_status_due", "invoices", ['status', 'due_date']),
    ("idx_invoices_customer_status", "invoices", ['customer_id', 'status']),
    ("idx_invoices_created", "invoices", ['created_at']),
    ("idx_invoice_lines_invoice", "invoice_lines", ['invoice_id']),
    ("idx_subscription_lines_sub", "subscription_lines", ['subscription_id']),
    ("idx_quotation_lines_quotation", "quotation_lines", ['quotation_id']),
    ("idx_subscriptions_status_next", "subscriptions", ['status', 'next_billing_date']),
    ("idx_subscriptions_created", "subscriptions", ['created_at']),
    ("idx_subscriptions_expiry", "subscriptions", ['expiry_date']),
    ("idx_payments_date", "payments", ['payment_date']),
    ("idx_payments_status_date", "payments", ['status', 'payment_date']),
    ("idx_payments_created", "payments", ['created_at']),
    ("idx_quotations_created", "quotations", ['created_at']),
    ("idx_customers_created", "customers", ['created_at']),
    ("idx_audit_logs_created", "audit_logs", ['created_at']),
    ("idx_notifications_user_created", "notifications", ['user_id', 'created_at']),
]

def upgrade():
    for name, table, cols in INDEXES: op.create_index(name, table, cols)

def downgrade():
    for name, table, _ in reversed(INDEXES): op.drop_index(name, table_name=table)
