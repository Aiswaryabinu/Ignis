"""Demo data. Run: python -m app.seed   (add --reset to wipe the database first)"""
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal as D
from sqlalchemy import text
from .db import SessionLocal, Base, engine
from .main import init_db
from . import models as m, services as s, worker
from .security import hash_password

PASSWORD = "Brightloop@2026"

def reset():
    with engine.begin() as c:
        c.execute(text("DROP TRIGGER IF EXISTS trg_audit_logs_immutable ON audit_logs")) if engine.dialect.has_table(c, "audit_logs") else None
    Base.metadata.drop_all(engine)
    from .ddl import SEQUENCES
    with engine.begin() as c:
        for sq in SEQUENCES.values(): c.execute(text(f"DROP SEQUENCE IF EXISTS {sq}"))
        for fn in ("audit_logs_immutable", "alloc_same_customer"): c.execute(text(f"DROP FUNCTION IF EXISTS {fn}() CASCADE"))

def seed():
    init_db(); db = SessionLocal()
    if db.query(m.User).count(): print("Database already has data; use --reset to wipe."); return
    mk = lambda email, name, role: db.add(m.User(email=email, full_name=name, role=role, password_hash=hash_password(PASSWORD), email_verified=True)) or db.flush()
    admin = m.User(email="aisha@brightloop.in", full_name="Aisha Khan", role="ADMIN", password_hash=hash_password(PASSWORD), email_verified=True)
    staff = m.User(email="rohan@brightloop.in", full_name="Rohan Mehta", role="STAFF", password_hash=hash_password(PASSWORD), email_verified=True)
    nw = m.User(email="ops@northwind.in", full_name="Northwind Ops", role="CUSTOMER", password_hash=hash_password(PASSWORD), email_verified=True)
    db.add_all([admin, staff, nw]); db.flush()
    cs = {}
    for key, name, email, ind, uid in [("nw", "Northwind Traders", "ops@northwind.in", "Retail", nw.id), ("kf", "Kerala Foods Co.", "it@keralafoods.in", "Food & Beverage", None),
                                      ("tw", "Tidewater Logistics", "admin@tidewater.in", "Logistics", None), ("lc", "Lumen Clinics", "billing@lumen.in", "Healthcare", None)]:
        c = m.Customer(user_id=uid, customer_code=s.next_number(db, "CUS"), company_name=name, billing_email=email, industry=ind, is_active=key != "lc")
        c.addresses.append(m.CustomerAddress(address_type="BILLING", address_line1="1 Main Road", city="Kochi", state="Kerala", country="India", is_default=True)); db.add(c); cs[key] = c
    cd = m.Product(name="CloudDesk Pro", product_type="Software", sales_price=D(7500), cost_price=D(3100))
    cd.variants += [m.ProductVariant(attribute_name="Brand", attribute_value="Odoo", additional_price=D(560))]
    an = m.Product(name="Analytics Suite", product_type="Software", sales_price=D(21600), cost_price=D(9800))
    an.variants += [m.ProductVariant(attribute_name="Edition", attribute_value="Plus", additional_price=D(1200))]
    sv = m.Product(name="SecureVault", product_type="Add-on", sales_price=D(1400), cost_price=D(520))
    db.add_all([cd, an, sv]); db.flush()
    today = date.today(); st = date(today.year, 1, 1)
    mk_plan = lambda **k: m.SubscriptionPlan(start_date=st, **k)
    p_bm = mk_plan(name="Business Monthly", product_id=cd.id, billing_interval="MONTHLY", price=D(18500), minimum_quantity=5)
    p_sa = mk_plan(name="Scale Annual", product_id=an.id, billing_interval="YEARLY", price=D(216000), minimum_quantity=10)
    p_sw = mk_plan(name="Secure Weekly", product_id=sv.id, billing_interval="WEEKLY", price=D(2800), minimum_quantity=2, allow_renewal=False, is_active=False)
    p_sm = mk_plan(name="Starter Monthly", product_id=cd.id, billing_interval="MONTHLY", price=D(7500), minimum_quantity=1)
    db.add_all([p_bm, p_sa, p_sw, p_sm]); db.flush()
    gst = m.Tax(name="GST 18%", rate=D(18), tax_type="PERCENTAGE", effective_from=st); db.add(gst); db.flush()
    db.add(m.TaxRule(tax_id=gst.id, country="India"))
    db.add(m.Discount(code="SEATS10", name="10% for 10+ seats", discount_type="PERCENTAGE", value=D(10), min_quantity=10, start_date=datetime(today.year, 1, 1, tzinfo=timezone.utc),
                      end_date=datetime(today.year, 12, 31, tzinfo=timezone.utc), usage_limit=20, scope="SUBSCRIPTION", created_by=admin.id))
    for name, plan, prod, qty, days in [("Retail Starter Pack", p_sm, cd, 5, 30), ("Enterprise Analytics", p_sa, an, 10, 15)]:
        t = m.QuotationTemplate(name=name, validity_days=days, created_by=admin.id)
        t.lines.append(m.QuotationTemplateLine(product_id=prod.id, plan_id=plan.id, default_quantity=qty, default_unit_price=prod.sales_price)); db.add(t)
    for et, (subj, body) in worker.DEFAULT_TEMPLATES.items(): db.add(m.NotificationTemplate(event_type=et, subject_template=subj, body_template=body))   # editable e-mail wording
    db.flush()
    s.__dict__  # services imported
    def mksub(c, plan, prod, qty, start, terms, status):
        sub = m.Subscription(subscription_number=s.next_number(db, "SUB"), customer_id=c.id, plan_id=plan.id, start_date=start, expiry_date=start.replace(year=start.year + 1), payment_terms=terms, status="DRAFT", created_by=admin.id)
        db.add(sub); db.flush(); sub.lines.append(s.build_sub_line(db, prod, None, qty, None, D(0), start, c))
        db.add(m.SubscriptionStatusHistory(subscription_id=sub.id, new_status="DRAFT", changed_by=admin.id)); db.flush(); db.refresh(sub)
        for step in {"ACTIVE": ["CONFIRMED", "ACTIVE"], "CONFIRMED": ["CONFIRMED"], "QUOTATION": ["QUOTATION"]}[status]:
            if step == "ACTIVE" and start > today: continue
            s.set_status(db, sub, step, admin)
        return sub
    mksub(cs["nw"], p_bm, cd, 5, date(today.year, 6, 1), "Net 15", "ACTIVE")
    mksub(cs["kf"], p_sa, an, 10, date(today.year, 3, 15), "Net 30", "ACTIVE")
    mksub(cs["tw"], p_sm, cd, 1, today + timedelta(days=20), "Immediate", "CONFIRMED")
    db.commit()
    r = s.run_billing(db, today, actor=admin)
    for inv in db.query(m.Invoice).filter(m.Invoice.status == "DRAFT").all(): s.confirm_invoice(db, inv, admin)
    db.commit()
    # demo payments: Northwind paid its older invoices; Kerala Foods part-paid its annual invoice
    invs = db.query(m.Invoice).order_by(m.Invoice.issue_date).all()
    nwi = [i for i in invs if i.customer_id == cs["nw"].id]
    for i in nwi[:-1]:
        s.record_payment(db, admin, cs["nw"].id, "BANK_TRANSFER", i.total_amount, datetime.combine(i.issue_date + timedelta(days=5), datetime.min.time(), tzinfo=timezone.utc), None, "Full payment", [{"invoice_id": i.id, "amount": i.total_amount}])
    kfi = next(i for i in invs if i.customer_id == cs["kf"].id)
    s.record_payment(db, admin, cs["kf"].id, "CARD", D(100000), datetime.combine(kfi.issue_date + timedelta(days=10), datetime.min.time(), tzinfo=timezone.utc), None, "Part payment", [{"invoice_id": kfi.id, "amount": D(100000)}])
    db.commit(); print("Seeded. Billing created:", len(r["created"]), "invoices")
    print(f"Logins (password {PASSWORD}): aisha@brightloop.in (Admin), rohan@brightloop.in (Staff), ops@northwind.in (Customer)")

if __name__ == "__main__":
    if "--reset" in sys.argv: reset()
    seed()
