"""Opt-in timing test for the "every page under two seconds with thousands of rows" requirement.

    RUN_PERF=1 pytest -q tests/test_perf.py -s           # 5,000 subscriptions + invoices + 2,500 payments
    RUN_PERF=1 PERF_ROWS=10000 pytest -q tests/test_perf.py -s

It bulk-inserts rows with the ORM into the test database (a minute or so), then times each list/report endpoint through the API.
The data stays in the test database until the next full run (conftest wipes it)."""
import os, time, uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal as D
import pytest

pytestmark = pytest.mark.skipif(os.getenv("RUN_PERF") != "1", reason="set RUN_PERF=1 to run the 2-second timing test")
LIMIT = float(os.getenv("PERF_LIMIT_SECONDS", "2.0"))

def _seed(n):
    from app.db import SessionLocal
    from app import models as m
    db = SessionLocal()
    try:
        admin = db.query(m.User).filter(m.User.role == "ADMIN").first()
        plan = db.query(m.SubscriptionPlan).filter(m.SubscriptionPlan.name == "Starter Monthly").first()
        prod = db.query(m.Product).filter(m.Product.name == "CloudDesk Pro").first()
        today = date.today(); cust = []
        for i in range(max(50, n // 25)):
            c = m.Customer(customer_code=f"PERF-C{i:05d}", company_name=f"Perf Customer {i:05d}", billing_email=f"perf{i}@example.com", is_active=True); db.add(c); cust.append(c)
        db.flush()
        subs, invs, pays = [], [], []
        for i in range(n):
            c = cust[i % len(cust)]; start = today - timedelta(days=30 + i % 300)
            sub = m.Subscription(subscription_number=f"PERF-S{i:06d}", customer_id=c.id, plan_id=plan.id, start_date=start, status="ACTIVE", billing_anchor_date=start,
                                 next_billing_date=today + timedelta(days=i % 30), payment_terms="Net 15", created_by=admin.id)
            sub.lines.append(m.SubscriptionLine(product_id=prod.id, product_name=prod.name, quantity=1 + i % 5, unit_price=D(7500), tax_rate_snapshot=D(18), line_total=D(8850) * (1 + i % 5)))
            db.add(sub); subs.append(sub)
        db.flush()
        for i, sub in enumerate(subs):
            total = D(8850) * (1 + i % 5); issue = today - timedelta(days=i % 120); paid = i % 2 == 0
            inv = m.Invoice(invoice_number=f"PERF-I{i:06d}", customer_id=sub.customer_id, subscription_id=sub.id, issue_date=issue, due_date=issue + timedelta(days=15),
                            billing_period_start=issue, billing_period_end=issue + timedelta(days=29), subtotal=total, tax_total=D(0), total_amount=total,
                            amount_paid=total if paid else D(0), balance_due=D(0) if paid else total, status="PAID" if paid else "CONFIRMED")
            inv.lines.append(m.InvoiceLine(product_id=prod.id, description="Perf line", quantity=1, unit_price=total, taxable_amount=total, line_total=total))
            db.add(inv); invs.append((inv, paid, total))
            if i % 500 == 499: db.flush()
        db.flush()
        for i, (inv, paid, total) in enumerate(invs):
            if not paid: continue
            p = m.Payment(payment_number=f"PERF-P{i:06d}", customer_id=inv.customer_id, payment_method="BANK_TRANSFER", amount=total, recorded_by=admin.id,
                          payment_date=datetime.combine(inv.issue_date + timedelta(days=3), datetime.min.time(), tzinfo=timezone.utc), status="RECORDED")
            p.allocations.append(m.PaymentAllocation(invoice_id=inv.id, allocated_amount=total)); db.add(p)
        db.commit()
    finally: db.close()

def test_every_page_responds_in_under_two_seconds(client, staff, cust):
    n = int(os.getenv("PERF_ROWS", "5000")); t0 = time.perf_counter(); _seed(n); print(f"\nseeded {n} subscriptions/invoices in {time.perf_counter() - t0:.1f}s")
    one_customer = client.get("/customers", headers=staff, params={"page_size": 1}).json()[0]["id"]
    paths = [("/customers", {}), ("/products", {}), ("/plans", {}), ("/quotations", {}), ("/subscriptions", {}), ("/subscriptions", {"status": "active", "page_size": 500}),
             ("/subscriptions", {"q": "perf customer 0001"}), ("/invoices", {}), ("/invoices", {"page": 5, "page_size": 500}), ("/invoices", {"status": "overdue"}),
             ("/invoices", {"q": "perf-i00"}), ("/invoices", {"customer_id": one_customer}), ("/payments", {}), ("/payments", {"method": "bank transfer", "date_from": "2020-01-01"}),
             ("/reports/summary", {}), ("/reports/summary", {"customer_id": one_customer}), ("/reports/overdue", {}), ("/audit-logs", {}),
             ("/reports/export/invoices", {"status": "overdue"})]
    slow = []
    for path, params in paths:
        t = time.perf_counter(); r = client.get(path, headers=staff, params=params); dt = time.perf_counter() - t
        print(f"{dt * 1000:8.0f} ms  {r.status_code}  {path} {params}")
        assert r.status_code == 200, (path, r.text[:200])
        if dt > LIMIT: slow.append((path, params, round(dt, 2)))
    assert not slow, f"slower than {LIMIT}s: {slow}"
