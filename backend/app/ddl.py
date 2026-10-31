"""Extra PostgreSQL DDL not expressed by the ORM models (shared by init_db and Alembic)."""
SEQUENCES = {"CUS": "seq_customer_code", "QUO": "seq_quotation_number", "SUB": "seq_subscription_number",
             "INV": "seq_invoice_number", "PAY": "seq_payment_number"}
SEQ_START = {"seq_customer_code": 1001, "seq_quotation_number": 1, "seq_subscription_number": 1,
             "seq_invoice_number": 1001, "seq_payment_number": 501}

UP = [f"CREATE SEQUENCE IF NOT EXISTS {n} START {SEQ_START[n]}" for n in SEQUENCES.values()] + [
    """CREATE OR REPLACE FUNCTION audit_logs_immutable() RETURNS trigger AS $$
       BEGIN RAISE EXCEPTION 'audit_logs is append-only'; END; $$ LANGUAGE plpgsql""",
    "DROP TRIGGER IF EXISTS trg_audit_logs_immutable ON audit_logs",
    """CREATE TRIGGER trg_audit_logs_immutable BEFORE UPDATE OR DELETE ON audit_logs
       FOR EACH ROW EXECUTE FUNCTION audit_logs_immutable()""",
    # a customer's payment may only be allocated to that customer's invoices
    """CREATE OR REPLACE FUNCTION alloc_same_customer() RETURNS trigger AS $$
       BEGIN
         IF (SELECT customer_id FROM payments WHERE id = NEW.payment_id)
            <> (SELECT customer_id FROM invoices WHERE id = NEW.invoice_id) THEN
           RAISE EXCEPTION 'payment and invoice must belong to the same customer';
         END IF; RETURN NEW; END; $$ LANGUAGE plpgsql""",
    "DROP TRIGGER IF EXISTS trg_alloc_same_customer ON payment_allocations",
    """CREATE TRIGGER trg_alloc_same_customer BEFORE INSERT OR UPDATE ON payment_allocations
       FOR EACH ROW EXECUTE FUNCTION alloc_same_customer()""",
]
DOWN = ["DROP TRIGGER IF EXISTS trg_alloc_same_customer ON payment_allocations",
        "DROP FUNCTION IF EXISTS alloc_same_customer()",
        "DROP TRIGGER IF EXISTS trg_audit_logs_immutable ON audit_logs",
        "DROP FUNCTION IF EXISTS audit_logs_immutable()"] + [f"DROP SEQUENCE IF EXISTS {n}" for n in SEQUENCES.values()]
