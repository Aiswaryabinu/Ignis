from datetime import date, timedelta
import pytest
from sqlalchemy import text

def test_auth_rules(client):
    r = client.post("/auth/register", json={"email": "x@y.com", "password": "short", "company_name": "X"}); assert r.status_code == 422
    r = client.post("/auth/register", json={"email": "new@acme.in", "password": "Strong#Pass1", "company_name": "Acme"}); assert r.status_code == 201
    assert client.post("/auth/register", json={"email": "NEW@acme.in", "password": "Strong#Pass1", "company_name": "Acme"}).status_code == 409
    assert client.post("/auth/login", json={"email": "new@acme.in", "password": "bad"}).status_code == 401
    tok = r.json()["dev_verification_token"]; assert client.post("/auth/verify-email", json={"token": tok}).status_code == 200
    assert client.post("/auth/verify-email", json={"token": tok}).status_code == 400   # single use

def test_password_reset_single_use(client):
    t = client.post("/auth/forgot-password", json={"email": "new@acme.in"}).json()["dev_reset_token"]
    assert client.post("/auth/reset-password", json={"token": t, "password": "Another#Pass2"}).status_code == 200
    assert client.post("/auth/reset-password", json={"token": t, "password": "Another#Pass3"}).status_code == 400
    assert client.post("/auth/login", json={"email": "new@acme.in", "password": "Another#Pass2"}).status_code == 200

def test_roles(client, admin, staff, cust):
    assert client.get("/customers").status_code == 401
    assert client.get("/users", headers=staff).status_code == 403          # only admin
    assert client.post("/users", headers=staff, json={"email": "a@b.in", "password": "Strong#Pass1", "full_name": "A"}).status_code == 403
    assert client.post("/users", headers=admin, json={"email": "newstaff@b.in", "password": "Strong#Pass1", "full_name": "A"}).status_code == 201
    assert client.get("/discounts", headers=cust).status_code == 403
    assert client.post("/products", headers=cust, json={"name": "x", "product_type": "x", "sales_price": 1, "cost_price": 1}).status_code == 403
    assert client.post("/plans", headers=staff, json={"name": "p", "billing_interval": "MONTHLY", "price": 1}).status_code == 403   # plans are admin-only
    mine = client.get("/customers", headers=cust).json(); assert [c["name"] for c in mine] == ["Northwind Traders"]
    assert {s["customer"] for s in client.get("/subscriptions", headers=cust).json()} == {"Northwind Traders"}
    assert {i["customer"] for i in client.get("/invoices", headers=cust).json()} == {"Northwind Traders"}

def test_product_validation(client, staff):
    assert client.post("/products", headers=staff, json={"name": "x", "product_type": "x", "sales_price": -1, "cost_price": 1}).status_code == 422

def get(client, h, path, **kw): return client.get(path, headers=h, **kw).json()

def test_quote_to_subscription_to_invoice_to_payment(client, admin, staff, cust):
    customers = get(client, staff, "/customers"); nw = next(c for c in customers if c["name"] == "Northwind Traders")
    plans = get(client, staff, "/plans"); sm = next(p for p in plans if p["name"] == "Starter Monthly")
    products = get(client, staff, "/products"); cd = next(p for p in products if p["name"] == "CloudDesk Pro"); var = cd["variant_list"][0]
    # variant price: 7500 + 560 = 8060; qty 2 -> 16120; GST 18% -> 2901.60
    r = client.post("/quotations", headers=staff, json={"customer_id": nw["id"], "lines": [{"product_id": cd["id"], "variant_id": var["id"], "plan_id": sm["id"], "quantity": 2}]}); assert r.status_code == 201, r.text
    q = r.json(); assert q["subtotal"] == 16120 and q["tax"] == 2901.6 and q["total"] == 19021.6
    assert client.post(f"/quotations/{q['id']}/accept", headers=cust).status_code == 409   # draft cannot be accepted
    assert client.post(f"/quotations/{q['id']}/send", headers=staff).status_code == 200
    # another customer cannot accept it; own customer can
    other = client.post("/auth/login", json={"email": "new@acme.in", "password": "Another#Pass2"}).json()["token"]
    assert client.post(f"/quotations/{q['id']}/accept", headers={"Authorization": "Bearer " + other}).status_code == 404
    r = client.post(f"/quotations/{q['id']}/accept", headers=cust, json={"start_date": str(date.today()), "payment_terms": "Net 15"}); assert r.status_code == 200, r.text
    sub_id = r.json()["subscription_id"]
    assert client.post(f"/quotations/{q['id']}/accept", headers=cust).status_code == 409   # only once
    sub = next(s for s in get(client, staff, "/subscriptions") if s["id"] == sub_id)
    assert sub["status"] == "Confirmed" and sub["amount"] == 19021.6
    # price changes must not affect the agreed subscription
    client.put(f"/products/{cd['id']}", headers=staff, json={"name": cd["name"], "product_type": "Software", "sales_price": 9999, "cost_price": 3100})
    # activate + bill
    assert client.post(f"/subscriptions/{sub_id}/activate", headers=staff).status_code == 200
    r = client.post("/billing/run", headers=staff, json={"subscription_id": sub_id}).json(); assert len(r["created"]) == 1 and not r["failed"]
    r2 = client.post("/billing/run", headers=staff, json={"subscription_id": sub_id}).json(); assert r2["created"] == []   # never twice
    inv = next(i for i in get(client, staff, "/invoices") if i["subscription"] == sub["number"])
    assert inv["status"] == "Draft" and inv["total"] == 19021.6 and inv["line_data"][0]["unit_price"] == 8060
    assert inv["line_data"][0]["tax_rate"] == 18
    # customer can't see drafts; payment needs a confirmed invoice
    assert all(i["number"] != inv["number"] for i in get(client, cust, "/invoices"))
    assert client.post("/payments", headers=staff, json={"invoice_id": inv["id"], "payment_method": "UPI", "amount": 100}).status_code == 409
    assert client.post(f"/invoices/{inv['id']}/confirm", headers=staff).status_code == 200
    # part pay, then too-large allocation, then rest
    p1 = client.post("/payments", headers=staff, json={"invoice_id": inv["id"], "payment_method": "UPI", "amount": 10000}); assert p1.status_code == 201, p1.text
    i = next(i for i in get(client, staff, "/invoices") if i["id"] == inv["id"]); assert i["status"] == "Part paid" and i["balance"] == 9021.6
    over = client.post("/payments", headers=staff, json={"customer_id": nw["id"], "payment_method": "CASH", "amount": 99999, "allocations": [{"invoice_id": inv["id"], "amount": 99999}]}); assert over.status_code == 422
    assert client.post("/payments", headers=staff, json={"customer_id": nw["id"], "payment_method": "CASH", "amount": 100, "allocations": [{"invoice_id": inv["id"], "amount": 200}]}).status_code == 422
    p2 = client.post("/payments", headers=staff, json={"invoice_id": inv["id"], "payment_method": "CARD", "amount": 9021.6}).json()
    i = next(i for i in get(client, staff, "/invoices") if i["id"] == inv["id"]); assert i["status"] == "Paid" and i["balance"] == 0
    # reversal restores the balance
    assert client.post(f"/payments/{p2['id']}/reverse", headers=staff).status_code == 403
    assert client.post(f"/payments/{p2['id']}/reverse", headers=admin).status_code == 200
    i = next(i for i in get(client, staff, "/invoices") if i["id"] == inv["id"]); assert i["status"] == "Part paid" and i["balance"] == 9021.6
    assert client.post(f"/invoices/{inv['id']}/cancel", headers=staff).status_code == 409   # has payments

def test_split_payment_across_invoices(client, staff):
    invs = [i for i in get(client, staff, "/invoices") if i["customer"] == "Northwind Traders" and i["status"] in ("Confirmed", "Overdue", "Part paid") and i["balance"] > 1000][:2]
    assert len(invs) == 2
    total = invs[0]["balance"] + 1000
    r = client.post("/payments", headers=staff, json={"customer_id": invs[0]["customer_id"], "payment_method": "BANK_TRANSFER", "amount": total,
        "allocations": [{"invoice_id": invs[0]["id"], "amount": invs[0]["balance"]}, {"invoice_id": invs[1]["id"], "amount": 1000}]}); assert r.status_code == 201, r.text
    now = {i["id"]: i for i in get(client, staff, "/invoices")}
    assert now[invs[0]["id"]]["status"] == "Paid" and now[invs[1]["id"]]["status"] in ("Part paid", "Overdue") and now[invs[1]["id"]]["paid"] == 1000 + invs[1]["paid"]

def test_payment_other_customer_rejected(client, staff):
    invs = get(client, staff, "/invoices"); a = next(i for i in invs if i["customer"] == "Kerala Foods Co." and i["status"] != "Draft" and i["balance"] > 0)
    nw = next(c for c in get(client, staff, "/customers") if c["name"] == "Northwind Traders")
    r = client.post("/payments", headers=staff, json={"customer_id": nw["id"], "payment_method": "CASH", "amount": 10, "allocations": [{"invoice_id": a["id"], "amount": 10}]}); assert r.status_code == 422

def test_db_constraints(client):
    from app.db import engine
    with engine.begin() as c:
        with pytest.raises(Exception): c.execute(text("update audit_logs set action='x'"))   # append-only trigger
    with engine.begin() as c:
        with pytest.raises(Exception): c.execute(text("insert into products(id,name,product_type,sales_price,cost_price,is_active) values (gen_random_uuid(),'n','t',-5,1,true)"))

def test_pause_blocks_billing_and_plan_rules(client, admin, staff):
    subs = get(client, staff, "/subscriptions"); active = next(s for s in subs if s["number"] == "SUB-0001")
    assert client.post(f"/subscriptions/{active['id']}/pause", headers=staff).status_code == 200
    future = str(date.today() + timedelta(days=90))
    r = client.post("/billing/run", headers=staff, json={"as_of": future, "subscription_id": active["id"]}).json(); assert r["created"] == []
    assert client.post(f"/subscriptions/{active['id']}/resume", headers=staff).status_code == 200
    # a draft cannot jump straight to paused
    assert client.post(f"/subscriptions/{active['id']}/close", headers=staff).status_code == 200
    assert client.post(f"/subscriptions/{active['id']}/resume", headers=staff).status_code == 409

def test_discount_applied_and_usage_recorded(client, staff):
    # Kerala Foods has 10 seats: SEATS10 (10%) should have been applied to its yearly invoice at seed time
    inv = next(i for i in get(client, staff, "/invoices") if i["customer"] == "Kerala Foods Co.")
    assert inv["discount"] == round(inv["subtotal"] * 0.10, 2)
    d = next(d for d in get(client, staff, "/discounts") if d["code"] == "SEATS10"); assert not d["used"].startswith("0 /")

def test_reports(client, staff):
    s = get(client, staff, "/reports/summary"); assert s["mrr"] > 0 and s["collected"] > 0 and s["by_plan"] and len(s["months"]) == 5

def test_audit_trail(client, admin):
    logs = get(client, admin, "/audit-logs"); acts = {l["action"] for l in logs}
    assert {"payment.recorded", "payment.reversed", "quotation.converted", "invoice.generated"} <= acts


def test_auto_close_at_plan_end_after_final_invoice(client, admin, staff):
    """Regression: once the last period is billed next_billing_date is NULL; the sub must still auto-close at expiry."""
    today = date.today()
    r = client.post("/plans", headers=admin, json={"name": "Fixed Term", "billing_interval": "monthly", "price": 100,
        "start_date": str(today - timedelta(days=40)), "end_date": str(today + timedelta(days=10)), "auto_close": True}); assert r.status_code == 201, r.text
    plan = r.json()
    cust = next(c for c in get(client, staff, "/customers") if c["name"] == "Northwind Traders")
    prod = next(p for p in get(client, staff, "/products") if p["name"] == "CloudDesk Pro")
    r = client.post("/subscriptions", headers=staff, json={"customer_id": cust["id"], "plan_id": plan["id"], "start_date": str(today - timedelta(days=35)),
        "lines": [{"product_id": prod["id"], "quantity": 1}]}); assert r.status_code == 201, r.text
    sub = r.json(); assert sub["expiry"] == (today + timedelta(days=10)).strftime("%d %b %Y")   # defaulted from plan end date
    assert client.post(f"/subscriptions/{sub['id']}/activate", headers=staff).status_code == 200
    r1 = client.post("/billing/run", headers=staff, json={"as_of": str(today), "subscription_id": sub["id"]}).json()
    assert r1["created"] and r1["closed"] == []
    now_sub = next(s for s in get(client, staff, "/subscriptions") if s["id"] == sub["id"])
    assert now_sub["status"] == "Active" and now_sub["next_billing"] == "—"      # final period billed, not yet expired
    r2 = client.post("/billing/run", headers=staff, json={"as_of": str(today + timedelta(days=10)), "subscription_id": sub["id"]}).json()
    assert r2["closed"] == [sub["number"]] and r2["created"] == []
    assert next(s for s in get(client, staff, "/subscriptions") if s["id"] == sub["id"])["status"] == "Closed"


# ---------------- step 1: customer self-service, invoice send/print, renewals ----------------
def _fmt(d): return d.strftime("%d %b %Y")

def _new_sub(client, staff, plan_name="Starter Monthly", start=None, expiry=None, auto_renew=False, plan=None):
    nw = next(c for c in get(client, staff, "/customers") if c["name"] == "Northwind Traders")
    plan = plan or next(p for p in get(client, staff, "/plans") if p["name"] == plan_name)
    prod = next(p for p in get(client, staff, "/products") if p["name"] == "CloudDesk Pro")
    body = {"customer_id": nw["id"], "plan_id": plan["id"], "start_date": str(start or date.today()), "auto_renew": auto_renew,
            "lines": [{"product_id": prod["id"], "quantity": 1}]}
    if expiry: body["expiry_date"] = str(expiry)
    r = client.post("/subscriptions", headers=staff, json=body); assert r.status_code == 201, r.text
    sub = r.json(); assert client.post(f"/subscriptions/{sub['id']}/activate", headers=staff).status_code == 200
    return sub

def test_invoice_send_and_print(client, staff, cust):
    sub = _new_sub(client, staff)
    assert client.post("/billing/run", headers=staff, json={"subscription_id": sub["id"]}).json()["created"]
    inv = next(i for i in get(client, staff, "/invoices") if i["subscription"] == sub["number"])
    assert client.post(f"/invoices/{inv['id']}/send", headers=staff).status_code == 409          # draft: confirm first
    assert client.get(f"/invoices/{inv['id']}/print", headers=cust).status_code == 404            # customers never see drafts
    assert client.post(f"/invoices/{inv['id']}/confirm", headers=staff).status_code == 200
    assert client.post(f"/invoices/{inv['id']}/send", headers=cust).status_code == 403            # customers cannot send
    assert client.post(f"/invoices/{inv['id']}/send", headers=staff).status_code == 200
    page = client.get(f"/invoices/{inv['id']}/print", headers=cust); assert page.status_code == 200 and "text/html" in page.headers["content-type"]
    assert inv["number"] in page.text and "Northwind Traders" in page.text
    assert client.get(f"/invoices/{inv['id']}", headers=cust).json()["number"] == inv["number"]
    other = client.post("/auth/login", json={"email": "new@acme.in", "password": "Another#Pass2"}).json()["token"]
    assert client.get(f"/invoices/{inv['id']}/print", headers={"Authorization": "Bearer " + other}).status_code == 404
    assert client.post(f"/invoices/{inv['id']}/cancel", headers=staff).status_code == 200
    assert client.post(f"/invoices/{inv['id']}/send", headers=staff).status_code == 409          # cancelled invoices are not sent

def test_customer_manages_own_subscription(client, staff, cust):
    today = date.today()
    sub = _new_sub(client, staff, expiry=today + timedelta(days=60))
    assert client.post(f"/subscriptions/{sub['id']}/pause", headers=cust).status_code == 200
    assert client.post(f"/subscriptions/{sub['id']}/resume", headers=cust).status_code == 200
    assert client.post(f"/subscriptions/{sub['id']}/activate", headers=cust).status_code == 403     # staff-only transitions
    other = {"Authorization": "Bearer " + client.post("/auth/login", json={"email": "new@acme.in", "password": "Another#Pass2"}).json()["token"]}
    assert client.post(f"/subscriptions/{sub['id']}/pause", headers=other).status_code == 404       # not theirs
    # each renewal adds the ORIGINAL 60-day term (no doubling)
    assert client.post(f"/subscriptions/{sub['id']}/renew", headers=cust).json()["expiry"] == _fmt(today + timedelta(days=120))
    assert client.post(f"/subscriptions/{sub['id']}/renew", headers=cust).json()["expiry"] == _fmt(today + timedelta(days=180))
    assert client.post(f"/subscriptions/{sub['id']}/close", headers=cust).status_code == 200
    assert next(s for s in get(client, cust, "/subscriptions") if s["id"] == sub["id"])["status"] == "Closed"

def test_plan_flags_bind_customers_too(client, admin, staff, cust):
    p = client.post("/plans", headers=admin, json={"name": "Locked Plan", "billing_interval": "monthly", "price": 10,
        "allow_pause": False, "allow_early_close": False, "allow_renewal": False}).json()
    sub = _new_sub(client, staff, plan=p, expiry=date.today() + timedelta(days=90))
    for action in ("pause", "close", "renew"): assert client.post(f"/subscriptions/{sub['id']}/{action}", headers=cust).status_code == 409

def test_auto_renew_in_billing_run(client, admin, staff):
    today = date.today()
    p = client.post("/plans", headers=admin, json={"name": "Rolling Monthly", "billing_interval": "monthly", "price": 10,
        "start_date": str(today - timedelta(days=60))}).json()
    sub = _new_sub(client, staff, plan=p, start=today - timedelta(days=45), expiry=today - timedelta(days=5), auto_renew=True)   # 40-day term, lapsed 5 days ago
    r = client.post("/billing/run", headers=staff, json={"as_of": str(today), "subscription_id": sub["id"]}).json()
    assert r["renewed"] == [sub["number"]] and not r["failed"] and r["closed"] == []
    now_sub = next(s for s in get(client, staff, "/subscriptions") if s["id"] == sub["id"])
    assert now_sub["status"] == "Active" and now_sub["expiry"] == _fmt(today + timedelta(days=35))
    assert client.post("/billing/run", headers=staff, json={"as_of": str(today), "subscription_id": sub["id"]}).json()["renewed"] == []   # idempotent

def test_auto_close_beats_auto_renew(client, admin, staff):
    today = date.today()
    p = client.post("/plans", headers=admin, json={"name": "Closing Term", "billing_interval": "monthly", "price": 10, "auto_close": True,
        "start_date": str(today - timedelta(days=60))}).json()
    sub = _new_sub(client, staff, plan=p, start=today - timedelta(days=45), expiry=today - timedelta(days=5), auto_renew=True)
    r = client.post("/billing/run", headers=staff, json={"as_of": str(today), "subscription_id": sub["id"]}).json()
    assert r["renewed"] == [] and r["closed"] == [sub["number"]]


# ---------------- step 2: pagination, filters, SQL reports, query counts ----------------
def test_pagination_header_and_pages(client, staff):
    r = client.get("/invoices", headers=staff, params={"page_size": 2}); assert r.status_code == 200
    total = int(r.headers["x-total-count"]); first = r.json(); assert len(first) == min(2, total) and total >= 3
    second = client.get("/invoices", headers=staff, params={"page_size": 2, "page": 2}).json()
    assert second and {i["id"] for i in first}.isdisjoint({i["id"] for i in second})          # stable, non-overlapping pages
    assert client.get("/invoices", headers=staff, params={"page_size": 0}).status_code == 422
    assert client.get("/invoices", headers=staff, params={"page_size": 501}).status_code == 422
    assert len(client.get("/invoices", headers=staff).json()) == total                          # default page is large enough for the demo data

def test_invoice_filters(client, staff, cust):
    allinv = get(client, staff, "/invoices")
    od = client.get("/invoices", headers=staff, params={"status": "overdue"}); assert od.status_code == 200
    assert od.json() and {i["status"] for i in od.json()} == {"Overdue"}
    assert {i["number"] for i in od.json()} == {i["number"] for i in allinv if i["status"] == "Overdue"}
    for label in ("Part paid", "part_paid", "PARTIALLY_PAID"):
        assert {i["status"] for i in client.get("/invoices", headers=staff, params={"status": label}).json()} <= {"Part paid"}
    assert client.get("/invoices", headers=staff, params={"status": "bogus"}).status_code == 422
    one = allinv[0]
    assert [i["number"] for i in client.get("/invoices", headers=staff, params={"q": one["number"].lower()}).json()] == [one["number"]]
    assert {i["customer_id"] for i in client.get("/invoices", headers=staff, params={"customer_id": one["customer_id"]}).json()} == {one["customer_id"]}
    assert client.get("/invoices", headers=staff, params={"customer_id": "not-a-uuid"}).status_code == 422
    assert client.get("/invoices", headers=staff, params={"issue_from": "2999-01-01"}).json() == []
    # a customer cannot widen their own scope by passing someone else's id
    other = next(c for c in get(client, staff, "/customers") if c["name"] == "Kerala Foods Co.")
    assert client.get("/invoices", headers=cust, params={"customer_id": other["id"]}).json() == []

def test_other_list_filters(client, staff):
    assert {s["status"] for s in client.get("/subscriptions", headers=staff, params={"status": "active"}).json()} == {"Active"}
    assert client.get("/subscriptions", headers=staff, params={"status": "nope"}).status_code == 422
    pays = client.get("/payments", headers=staff, params={"method": "bank transfer"}).json(); assert pays and {p["method"] for p in pays} == {"Bank Transfer"}
    assert client.get("/payments", headers=staff, params={"date_from": "2999-01-01"}).json() == []
    assert {c["status"] for c in client.get("/customers", headers=staff, params={"status": "inactive"}).json()} == {"Inactive"}
    assert [c["name"] for c in client.get("/customers", headers=staff, params={"q": "tidewater"}).json()] == ["Tidewater Logistics"]
    assert client.get("/customers", headers=staff, params={"q": "%"}).json() == []                # wildcard characters are literal
    assert all(q["status"] == "Accepted" for q in client.get("/quotations", headers=staff, params={"status": "accepted"}).json())

def test_summary_filters_are_consistent(client, staff):
    whole = get(client, staff, "/reports/summary")
    custs = get(client, staff, "/customers")
    parts = [get(client, staff, "/reports/summary", params={"customer_id": c["id"]}) for c in custs]
    for k in ("billed", "outstanding", "collected", "overdue_total", "mrr"): assert abs(sum(p[k] for p in parts) - whole[k]) < 0.05, k
    assert sum(p["active_subscriptions"] for p in parts) == whole["active_subscriptions"]
    assert sum(p["overdue_count"] for p in parts) == whole["overdue_count"]
    by_plan = [get(client, staff, "/reports/summary", params={"plan_id": p["id"]}) for p in get(client, staff, "/plans")]
    assert abs(sum(p["billed"] for p in by_plan) - whole["billed"]) < 0.05 and abs(sum(p["collected"] for p in by_plan) - whole["collected"]) < 0.05
    future = get(client, staff, "/reports/summary", params={"date_from": "2999-01-01"}); assert future["billed"] == 0 and future["collected"] == 0 and future["overdue_count"] == 0
    assert future["active_subscriptions"] == whole["active_subscriptions"]                       # snapshot figures ignore dates
    assert client.get("/reports/summary", headers=staff, params={"date_from": "2026-02-01", "date_to": "2026-01-01"}).status_code == 422
    live = [i for i in get(client, staff, "/invoices") if i["status"] not in ("Cancelled", "Void")]   # health covers the five working states
    assert len(whole["months"]) == 5 and sum(h["count"] for h in whole["invoice_health"].values()) == len(live)

def test_overdue_report(client, staff, cust):
    r = client.get("/reports/overdue", headers=staff); assert r.status_code == 200
    rows = r.json(); assert rows and all(x["days_overdue"] > 0 and x["status"] == "Overdue" and x["balance"] > 0 for x in rows)
    assert [x["due_iso"] for x in rows] == sorted(x["due_iso"] for x in rows)                    # oldest first
    assert int(r.headers["x-total-count"]) == get(client, staff, "/reports/summary")["overdue_count"]
    assert client.get("/reports/overdue", headers=cust).status_code == 403

def test_list_endpoints_use_constant_queries(client, staff, cust):
    """No N+1: statements per request must not grow with the number of rows returned."""
    from sqlalchemy import event
    from app.db import engine
    n = []
    def count(conn, cursor, statement, *a): n.append(statement)
    event.listen(engine, "before_cursor_execute", count)
    try:
        for path in ("/customers", "/products", "/plans", "/taxes", "/discounts", "/quotations", "/subscriptions", "/invoices", "/payments", "/reports/overdue", "/reports/summary"):
            n.clear(); r = client.get(path, headers=staff); assert r.status_code == 200, path
            assert len(n) <= 16, f"{path} ran {len(n)} statements"
        n.clear(); client.get("/invoices", headers=cust); assert len(n) <= 8
    finally: event.remove(engine, "before_cursor_execute", count)


# ---------------- step 3: e-mail delivery, outbox worker, reminders, daily jobs ----------------
def _worker():
    from app import worker, mailer
    return worker, mailer

def _outbox_run(limit=200):
    worker, _ = _worker(); return worker.run_outbox(limit)

def test_reset_link_is_emailed_and_works(client):
    worker, mailer = _worker(); _outbox_run(); before = len(mailer.SENT)
    assert client.post("/auth/forgot-password", json={"email": "nobody@nowhere.in"}).status_code == 200      # unknown address: same reply, no mail
    r = client.post("/auth/forgot-password", json={"email": "new@acme.in"}); token = r.json()["dev_reset_token"]
    _outbox_run()
    mails = [x for x in mailer.SENT[before:] if x["to"] == "new@acme.in"]; assert len(mails) == 1 and not [x for x in mailer.SENT[before:] if x["to"] == "nobody@nowhere.in"]
    assert f"/#reset={token}" in mails[0]["body"] and "reset" in mails[0]["subject"].lower()
    assert client.post("/auth/reset-password", json={"token": token, "password": "Final#Pass3"}).status_code == 200
    assert client.post("/auth/login", json={"email": "new@acme.in", "password": "Final#Pass3"}).status_code == 200
    from app.db import SessionLocal; from app import models as m
    with SessionLocal() as db:   # the link is removed from the stored event once it has been sent
        ev = db.query(m.OutboxEvent).filter(m.OutboxEvent.event_type == "auth.password_reset").all()
        assert ev and all("link" not in e.payload and e.status == "PUBLISHED" for e in ev)
    client.post("/auth/login", json={"email": "new@acme.in", "password": "Final#Pass3"})
    # later tests log in with the earlier password: put it back
    t2 = client.post("/auth/forgot-password", json={"email": "new@acme.in"}).json()["dev_reset_token"]
    assert client.post("/auth/reset-password", json={"token": t2, "password": "Another#Pass2"}).status_code == 200

def test_signup_sends_verification_mail(client):
    _, mailer = _worker(); before = len(mailer.SENT)
    r = client.post("/auth/register", json={"email": "verify-me@acme.in", "password": "Strong#Pass1", "company_name": "VerifyCo"}); assert r.status_code == 201
    _outbox_run(); m1 = [x for x in mailer.SENT[before:] if x["to"] == "verify-me@acme.in"]
    assert len(m1) == 1 and f"/#verify={r.json()['dev_verification_token']}" in m1[0]["body"]

def test_invoice_send_quotation_and_payment_mails(client, staff):
    _, mailer = _worker(); _outbox_run(); before = len(mailer.SENT)
    sub = _new_sub(client, staff)
    client.post("/billing/run", headers=staff, json={"subscription_id": sub["id"]})
    inv = next(i for i in get(client, staff, "/invoices") if i["subscription"] == sub["number"])
    client.post(f"/invoices/{inv['id']}/confirm", headers=staff)
    assert client.post(f"/invoices/{inv['id']}/send", headers=staff).status_code == 200
    assert client.post("/payments", headers=staff, json={"invoice_id": inv["id"], "payment_method": "UPI", "amount": 50}).status_code == 201
    _outbox_run(); new = mailer.SENT[before:]
    sent = [x for x in new if inv["number"] in x["subject"] and x["to"] == "ops@northwind.in"]; assert len(sent) == 1 and "Balance due" in sent[0]["body"]
    assert [x for x in new if x["subject"].startswith("Payment PAY-")]
    # quotations are mailed when they are sent
    nw = next(c for c in get(client, staff, "/customers") if c["name"] == "Northwind Traders")
    sm = next(p for p in get(client, staff, "/plans") if p["name"] == "Starter Monthly"); cd = next(p for p in get(client, staff, "/products") if p["name"] == "CloudDesk Pro")
    q = client.post("/quotations", headers=staff, json={"customer_id": nw["id"], "lines": [{"product_id": cd["id"], "plan_id": sm["id"], "quantity": 1}]}).json()
    before = len(mailer.SENT); assert client.post(f"/quotations/{q['id']}/send", headers=staff).status_code == 200; _outbox_run()
    assert [x for x in mailer.SENT[before:] if q["number"] in x["subject"] and x["to"] == "ops@northwind.in"]

def test_failed_delivery_backs_off_then_fails_and_can_be_retried(client, admin, staff, monkeypatch):
    from app import config; worker, mailer = _worker(); _outbox_run()
    client.post("/auth/forgot-password", json={"email": "ops@northwind.in"})
    monkeypatch.setattr(config, "EMAIL_BACKEND", "smtp"); monkeypatch.setattr(config, "SMTP_HOST", "127.0.0.1"); monkeypatch.setattr(config, "SMTP_PORT", 9)   # nothing listens there
    monkeypatch.setattr(config, "OUTBOX_MAX_ATTEMPTS", 2)
    r1 = _outbox_run(); assert r1["retry"] == 1 and r1["sent"] == 0
    ev = client.get("/admin/outbox", headers=admin, params={"status": "pending"}).json()[0]
    assert ev["attempts"] == 1 and ev["error"] and ev["next_try"] and "link" not in str(ev)
    assert _outbox_run()["retry"] == 0                                        # backing off: not tried again immediately
    from app.db import SessionLocal; from app import models as m
    with SessionLocal() as db:                                                # pretend the back-off has passed
        e = db.get(m.OutboxEvent, ev["id"]); e.payload = {**e.payload, "_not_before": "2000-01-01T00:00:00+00:00"}; db.commit()
    assert _outbox_run()["failed"] == 1
    assert client.get("/admin/outbox", headers=admin, params={"status": "failed"}).json()[0]["id"] == ev["id"]
    assert client.post(f"/admin/outbox/{ev['id']}/retry", headers=staff).status_code == 403
    monkeypatch.setattr(config, "EMAIL_BACKEND", "memory"); before = len(mailer.SENT)
    assert client.post(f"/admin/outbox/{ev['id']}/retry", headers=admin).json()["status"] == "PENDING"
    assert _outbox_run()["sent"] >= 1 and [x for x in mailer.SENT[before:] if x["to"] == "ops@northwind.in"]
    assert client.post(f"/admin/outbox/{ev['id']}/retry", headers=admin).status_code == 409   # already delivered

def test_overdue_reminders_are_spaced_out(client, staff):
    from datetime import datetime, timezone
    from sqlalchemy import func
    from app import models as m, config
    from app.db import SessionLocal
    worker, mailer = _worker(); _outbox_run(); before = len(mailer.SENT)
    overdue = [i for i in get(client, staff, "/invoices") if i["status"] == "Overdue"]; assert overdue
    with SessionLocal() as db: assert worker.send_overdue_reminders(db) == len(overdue)     # one reminder per overdue invoice
    with SessionLocal() as db: assert worker.send_overdue_reminders(db) == 0                # same day: nothing new
    _outbox_run(); mails = [x for x in mailer.SENT[before:] if "overdue" in x["subject"].lower()]
    assert len(mails) == len(overdue) and all("overdue" in x["body"] and "Balance due" in x["body"] for x in mails)
    long_ago = datetime(2000, 1, 1, tzinfo=timezone.utc)
    with SessionLocal() as db:   # age the reminders so the next one is due; stops after REMINDER_MAX
        for n in range(1, config.REMINDER_MAX + 1):
            db.query(m.OutboxEvent).filter(m.OutboxEvent.event_type == "invoice.overdue_reminder").update({"created_at": long_ago}); db.commit()
            assert (worker.send_overdue_reminders(db) >= 1) == (n < config.REMINDER_MAX)
        counts = dict(db.query(m.OutboxEvent.aggregate_id, func.count()).filter(m.OutboxEvent.event_type == "invoice.overdue_reminder").group_by(m.OutboxEvent.aggregate_id).all())
        assert counts and max(counts.values()) == config.REMINDER_MAX

def test_daily_jobs_idempotent_and_single_instance(client, admin, staff):
    worker, _ = _worker()
    r1 = worker.run_daily(); assert "billing" in r1 and "reminders_queued" in r1
    r2 = worker.run_daily(); assert r2["billing"]["created"] == [] and not r2["billing"]["failed"]
    with worker.single_instance(worker.LOCK_DAILY) as got:
        assert got and "skipped" in worker.run_daily()                              # a second instance backs off
    assert client.post("/admin/jobs/daily", headers=staff).status_code == 403
    assert "billing" in client.post("/admin/jobs/daily", headers=admin).json()
    assert client.post("/admin/jobs/nope", headers=admin).status_code == 404
    assert "sent" in client.post("/admin/jobs/outbox", headers=admin).json()

def test_billing_jobs_listing(client, staff, cust):
    rows = client.get("/billing/jobs", headers=staff).json(); assert rows and {"subscription", "period_start", "status", "attempts"} <= set(rows[0])
    assert {j["status"] for j in client.get("/billing/jobs", headers=staff, params={"status": "completed"}).json()} == {"Completed"}
    assert client.get("/billing/jobs", headers=cust).status_code == 403


# ---------------- step 4: admin completeness + hardening ----------------
def _auth(client, email, pw):
    r = client.post("/auth/login", json={"email": email, "password": pw}); assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}

def _step4_product(client, staff, name="Step4 Widget", price=1000):
    r = client.post("/products", headers=staff, json={"name": name, "product_type": "Service", "sales_price": price, "cost_price": 100}); assert r.status_code == 201, r.text
    return r.json()

def _quote_total_tax(client, staff, customer_id, plan_id, product_id):
    r = client.post("/quotations", headers=staff, json={"customer_id": customer_id, "lines": [{"product_id": product_id, "plan_id": plan_id, "quantity": 1}]}); assert r.status_code == 201, r.text
    return r.json()["tax"]

def test_tax_edit_deactivate_and_rules(client, admin, staff):
    prod = _step4_product(client, staff, "Step4 Taxed")
    nw = next(c for c in get(client, staff, "/customers") if c["name"] == "Northwind Traders"); sm = next(p for p in get(client, staff, "/plans") if p["name"] == "Starter Monthly")
    assert client.post("/taxes", headers=staff, json={"name": "x", "rate": 5}).status_code == 403                     # admin only
    r = client.post("/taxes", headers=admin, json={"name": "Step4 VAT", "rate": 10, "product_id": prod["id"], "priority": 50}); assert r.status_code == 201, r.text
    tax = r.json(); assert tax["rules"][0]["product"] == "Step4 Taxed" and tax["is_active"]
    assert client.post("/taxes", headers=admin, json={"name": "bad", "rate": 150}).status_code == 422                     # percentage > 100
    assert _quote_total_tax(client, staff, nw["id"], sm["id"], prod["id"]) == 100.0                                       # 10% of 1000
    # edit: the new rate applies to new quotes only
    r = client.put(f"/taxes/{tax['id']}", headers=admin, json={"rate": 12}); assert r.status_code == 200 and r.json()["rate"] == 12
    assert client.put(f"/taxes/{tax['id']}", headers=admin, json={"effective_until": "2000-01-01"}).status_code == 422     # ends before it starts
    assert client.put(f"/taxes/{tax['id']}", headers=staff, json={"rate": 1}).status_code == 403
    assert _quote_total_tax(client, staff, nw["id"], sm["id"], prod["id"]) == 120.0
    # rules
    rid = tax["rules"][0]["id"]
    assert client.delete(f"/taxes/{tax['id']}/rules/{rid}", headers=admin).status_code == 409                             # last rule cannot go
    assert client.post(f"/taxes/{tax['id']}/rules", headers=admin, json={"product_id": prod["id"]}).status_code == 409     # duplicate
    r = client.post(f"/taxes/{tax['id']}/rules", headers=admin, json={"country": "India", "state": "Kerala", "priority": 5}); assert r.status_code == 201, r.text
    r2 = r.json(); assert r2["country"] == "India" and r2["product"] == "All products"
    assert len(get(client, staff, f"/taxes/{tax['id']}/rules")) == 2
    assert client.put(f"/taxes/{tax['id']}/rules/{r2['id']}", headers=admin, json={"country": "India", "state": "Goa", "priority": 5}).json()["state"] == "Goa"
    assert client.delete(f"/taxes/{tax['id']}/rules/{r2['id']}", headers=admin).status_code == 200
    # deactivate: no longer applied; reactivate: applied again
    r = client.post(f"/taxes/{tax['id']}/deactivate", headers=admin); assert r.status_code == 200 and r.json()["status"] == "Inactive"
    assert _quote_total_tax(client, staff, nw["id"], sm["id"], prod["id"]) == 0
    assert tax["id"] in [t["id"] for t in get(client, staff, "/taxes?status=inactive")] and tax["id"] not in [t["id"] for t in get(client, staff, "/taxes?status=active")]
    client.post(f"/taxes/{tax['id']}/activate", headers=admin); assert _quote_total_tax(client, staff, nw["id"], sm["id"], prod["id"]) == 120.0
    client.post(f"/taxes/{tax['id']}/deactivate", headers=admin)                                                           # leave nothing active that later tests could pick up
    assert client.get("/taxes/not-a-uuid", headers=staff).status_code == 404 and client.post(f"/taxes/{tax['id']}/explode", headers=admin).status_code == 404

def test_discount_edit_and_deactivate(client, admin, staff):
    prod = _step4_product(client, staff, "Step4 Discounted")
    body = {"code": "step4a", "discount_type": "PERCENTAGE", "value": 10, "start_date": "2020-01-01T00:00:00Z", "scope": "PRODUCT", "product_ids": [prod["id"]]}
    assert client.post("/discounts", headers=staff, json=body).status_code == 403
    r = client.post("/discounts", headers=admin, json=body); assert r.status_code == 201, r.text
    d = r.json(); assert d["code"] == "STEP4A" and d["product_ids"] == [prod["id"]] and d["is_active"]
    assert client.post("/discounts", headers=admin, json=body).status_code == 409                                          # duplicate code
    assert client.post("/discounts", headers=admin, json={**body, "code": "STEP4B", "end_date": "2019-01-01T00:00:00Z"}).status_code == 422
    assert client.post("/discounts", headers=admin, json={**body, "code": "STEP4C", "value": 101}).status_code == 422
    r = client.put(f"/discounts/{d['id']}", headers=admin, json={"value": 15, "usage_limit": 3, "name": "Step 4 promo"}); assert r.status_code == 200, r.text
    assert r.json()["raw_value"] == 15 and r.json()["usage_limit"] == 3 and r.json()["name"] == "Step 4 promo"
    assert client.put(f"/discounts/{d['id']}", headers=admin, json={"scope": "SUBSCRIPTION", "discount_type": "FIXED", "value": 500}).json()["value"] == "₹500"
    assert client.put(f"/discounts/{d['id']}", headers=admin, json={"scope": "PRODUCT", "product_ids": []}).status_code == 422   # product scope needs a product
    assert client.put(f"/discounts/{d['id']}", headers=admin, json={"code": "seats10"}).status_code == 409                # code taken by the seeded discount
    assert client.put(f"/discounts/{d['id']}", headers=admin, json={"usage_limit": None}).json()["usage_limit"] is None    # null removes the limit
    assert client.put(f"/discounts/{d['id']}", headers=staff, json={"value": 1}).status_code == 403
    # an existing, already-used discount cannot get a limit below its usage
    used = next(x for x in get(client, staff, "/discounts") if x["code"] == "SEATS10"); n = used["usage_count"]; assert n > 0
    r = client.put(f"/discounts/{used['id']}", headers=admin, json={"usage_limit": n - 1}); assert r.status_code == 422, r.text
    # deactivate / reactivate
    assert client.post(f"/discounts/{d['id']}/deactivate", headers=admin).json()["status"] == "Draft"
    assert client.post(f"/discounts/{d['id']}/activate", headers=admin).json()["is_active"] is True
    client.post(f"/discounts/{d['id']}/deactivate", headers=admin)
    assert client.get("/discounts", headers=staff).status_code == 200 and client.post(f"/discounts/{d['id']}/nope", headers=admin).status_code == 404

def test_template_edit_and_deactivate(client, admin, staff):
    prod = _step4_product(client, staff, "Step4 Tpl"); other = _step4_product(client, staff, "Step4 Tpl B", 2000)
    cust = next(c for c in get(client, staff, "/customers") if c["name"] == "Northwind Traders"); sm = next(p for p in get(client, staff, "/plans") if p["name"] == "Starter Monthly")
    inactive_plan = next(p for p in get(client, staff, "/plans") if p["status"] != "Active")
    line = {"product_id": prod["id"], "plan_id": sm["id"], "default_quantity": 2}
    assert client.post("/quotation-templates", headers=staff, json={"name": "t", "validity_days": 10, "lines": [line]}).status_code == 403
    assert client.post("/quotation-templates", headers=admin, json={"name": "t", "validity_days": 10, "lines": [{**line, "plan_id": inactive_plan["id"]}]}).status_code == 409
    r = client.post("/quotation-templates", headers=admin, json={"name": "Step4 template", "validity_days": 10, "lines": [line]}); assert r.status_code == 201, r.text
    t = r.json()
    r = client.put(f"/quotation-templates/{t['id']}", headers=admin, json={"name": "Renamed", "validity_days": 45, "lines": [{**line, "product_id": other["id"], "default_quantity": 3}]})
    assert r.status_code == 200, r.text
    t2 = r.json(); assert t2["template"] == "Renamed" and t2["validity_days"] == 45 and len(t2["line_data"]) == 1 and t2["line_data"][0]["quantity"] == 3 and t2["line_data"][0]["unit_price"] == 2000
    assert client.put(f"/quotation-templates/{t['id']}", headers=admin, json={"validity_days": 0}).status_code == 422
    assert client.put(f"/quotation-templates/{t['id']}", headers=admin, json={"lines": []}).status_code == 422
    q = client.post("/quotations", headers=staff, json={"customer_id": cust["id"], "template_id": t["id"]}); assert q.status_code == 201 and q.json()["subtotal"] == 6000, q.text
    assert t["id"] not in [x["id"] for x in get(client, staff, "/quotation-templates?status=draft")]
    assert client.post(f"/quotation-templates/{t['id']}/deactivate", headers=admin).json()["status"] == "Draft"
    assert client.post("/quotations", headers=staff, json={"customer_id": cust["id"], "template_id": t["id"]}).status_code == 409   # switched off
    assert t["id"] in [x["id"] for x in get(client, staff, "/quotation-templates?status=draft")]
    assert client.post(f"/quotation-templates/{t['id']}/activate", headers=admin).json()["status"] == "Active"
    assert client.post("/quotations", headers=staff, json={"customer_id": cust["id"], "template_id": t["id"]}).status_code == 201

def test_team_user_management(client, admin, staff):
    r = client.post("/users", headers=admin, json={"email": "step4.staff@b.in", "password": "Strong#Pass1", "full_name": "Step Four"}); assert r.status_code == 201
    uid = r.json()["id"]; mine = _auth(client, "step4.staff@b.in", "Strong#Pass1")
    assert client.put(f"/users/{uid}", headers=staff, json={"full_name": "x"}).status_code == 403
    assert client.get("/customers", headers=mine).status_code == 200
    me = client.get("/auth/me", headers=admin).json()
    # filters + pagination header
    rows = client.get("/users?q=step4&role=staff&status=active", headers=admin); assert [u["email"] for u in rows.json()] == ["step4.staff@b.in"] and rows.headers["x-total-count"] == "1"
    assert client.get("/users?role=customer", headers=admin).status_code == 422
    # edit name + role
    r = client.put(f"/users/{uid}", headers=admin, json={"full_name": "Step Four B", "role": "ADMIN"}); assert r.status_code == 200 and r.json()["role"] == "Admin" and r.json()["name"] == "Step Four B"
    assert client.get("/users", headers=mine).status_code == 200                                                                 # role change is effective at once
    client.put(f"/users/{uid}", headers=admin, json={"role": "STAFF"})
    assert client.get("/users", headers=mine).status_code == 403
    # guards: never yourself, never the last admin, never a customer account
    assert client.put(f"/users/{me['id']}", headers=admin, json={"role": "STAFF"}).status_code == 409
    assert client.post(f"/users/{me['id']}/deactivate", headers=admin).status_code == 409
    cust_user = client.get("/auth/me", headers=_auth(client, "ops@northwind.in", "Brightloop@2026")).json()
    assert client.post(f"/users/{cust_user['id']}/deactivate", headers=admin).status_code == 404
    # deactivate: the person's existing token dies immediately, login is refused; reactivate restores it
    assert client.post(f"/users/{uid}/deactivate", headers=admin).json()["status"] == "Inactive"
    assert client.get("/customers", headers=mine).status_code == 401
    assert client.post("/auth/login", json={"email": "step4.staff@b.in", "password": "Strong#Pass1"}).status_code == 403
    assert client.post(f"/users/{uid}/activate", headers=admin).json()["status"] == "Active"
    mine = _auth(client, "step4.staff@b.in", "Strong#Pass1"); assert client.get("/customers", headers=mine).status_code == 200
    # admin-triggered reset mail; old password dies once the link is used
    r = client.post(f"/users/{uid}/reset-password", headers=admin); assert r.status_code == 200 and r.json()["dev_reset_token"]
    assert client.post("/auth/reset-password", json={"token": r.json()["dev_reset_token"], "password": "Reset#Pass9"}).status_code == 200
    assert client.get("/customers", headers=mine).status_code == 401                                                              # old token revoked by the password change
    _auth(client, "step4.staff@b.in", "Reset#Pass9")

def test_profile_and_password_change_revokes_sessions(client, admin):
    client.post("/users", headers=admin, json={"email": "step4.pw@b.in", "password": "Strong#Pass1", "full_name": "Pw User"})
    old = _auth(client, "step4.pw@b.in", "Strong#Pass1"); other_device = _auth(client, "step4.pw@b.in", "Strong#Pass1")
    assert client.put("/auth/me", headers=old, json={"full_name": "Pw Renamed"}).json()["full_name"] == "Pw Renamed"
    assert client.put("/auth/me", headers=old, json={"full_name": ""}).status_code == 422
    assert client.post("/auth/change-password", headers=old, json={"current_password": "wrong", "new_password": "Newer#Pass7"}).status_code == 400
    assert client.post("/auth/change-password", headers=old, json={"current_password": "Strong#Pass1", "new_password": "weak"}).status_code == 422
    assert client.post("/auth/change-password", headers=old, json={"current_password": "Strong#Pass1", "new_password": "Strong#Pass1"}).status_code == 422
    r = client.post("/auth/change-password", headers=old, json={"current_password": "Strong#Pass1", "new_password": "Newer#Pass7"}); assert r.status_code == 200
    fresh = {"Authorization": "Bearer " + r.json()["token"]}
    assert client.get("/auth/me", headers=fresh).status_code == 200                                                                # the caller stays signed in
    assert client.get("/auth/me", headers=old).status_code == 401 and client.get("/auth/me", headers=other_device).status_code == 401
    assert client.post("/auth/login", json={"email": "step4.pw@b.in", "password": "Strong#Pass1"}).status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    import jwt as _jwt; from app.config import JWT_SECRET
    assert client.get("/auth/me", headers={"Authorization": "Bearer " + _jwt.encode({"sub": "not-a-uuid", "exp": 4102444800}, JWT_SECRET, algorithm="HS256")}).status_code == 401
    aid = client.get("/auth/me", headers=admin).json()["id"]; tok = lambda claims: {"Authorization": "Bearer " + _jwt.encode(claims, JWT_SECRET, algorithm="HS256")}
    assert client.get("/auth/me", headers=tok({"sub": aid})).status_code == 401                          # no exp
    assert client.get("/auth/me", headers=tok({"sub": aid, "exp": 4102444800})).status_code == 401       # no password stamp (token from before this version)

def test_customer_address_crud(client, staff, cust):
    customers = get(client, staff, "/customers"); nw = next(c for c in customers if c["name"] == "Northwind Traders"); other = next(c for c in customers if c["name"] != "Northwind Traders")
    base = f"/customers/{nw['id']}/addresses"; start = get(client, staff, base); assert start and sum(a["is_default"] and a["type"] == "BILLING" for a in start) == 1
    new = {"address_type": "billing", "address_line1": "9 Lake Road", "city": "Pune", "state": "Maharashtra", "country": "India", "postal_code": "411001"}
    r = client.post(base, headers=cust, json=new); assert r.status_code == 201, r.text
    a1 = r.json(); assert a1["type"] == "BILLING" and a1["is_default"] is False                                                   # another billing address: the first one stays default
    assert client.post(base, headers=cust, json={**new, "address_type": "HOME"}).status_code == 422
    assert client.post(base, headers=cust, json={**new, "city": ""}).status_code == 422
    r = client.put(f"{base}/{a1['id']}", headers=cust, json={**new, "address_line1": "10 Lake Road", "is_default": True}); assert r.status_code == 200 and r.json()["is_default"] and r.json()["line1"] == "10 Lake Road"
    rows = get(client, staff, base); assert sum(a["is_default"] and a["type"] == "BILLING" for a in rows) == 1 and next(a for a in rows if a["id"] == a1["id"])["is_default"]
    # un-ticking the only default keeps one default; deleting the default promotes another
    client.put(f"{base}/{a1['id']}", headers=cust, json={**new, "is_default": False}); assert sum(a["is_default"] and a["type"] == "BILLING" for a in get(client, staff, base)) == 1
    client.put(f"{base}/{a1['id']}", headers=cust, json={**new, "is_default": True})
    assert client.delete(f"{base}/{a1['id']}", headers=cust).status_code == 200
    rows = get(client, staff, base); assert len(rows) == len(start) and sum(a["is_default"] and a["type"] == "BILLING" for a in rows) == 1
    # first address of a new type becomes its default; customer_out carries the ids
    r = client.post(base, headers=staff, json={**new, "address_type": "SHIPPING"}); assert r.json()["is_default"] is True
    assert any(a["id"] == r.json()["id"] for a in next(c for c in get(client, staff, "/customers") if c["id"] == nw["id"])["addresses"])
    client.delete(f"{base}/{r.json()['id']}", headers=staff)
    # scope: a customer only reaches their own record; an address id from another customer is "not found"
    assert client.get(f"/customers/{other['id']}/addresses", headers=cust).status_code == 404
    assert client.post(f"/customers/{other['id']}/addresses", headers=cust, json=new).status_code == 404
    foreign = get(client, staff, f"/customers/{other['id']}/addresses")
    if foreign: assert client.delete(f"{base}/{foreign[0]['id']}", headers=staff).status_code == 404
    assert client.get(base).status_code == 401

def test_customer_deactivate_blocked_by_open_subscriptions(client, staff):
    nw = next(c for c in get(client, staff, "/customers") if c["name"] == "Northwind Traders"); assert nw["subscriptions"] > 0
    assert client.post(f"/customers/{nw['id']}/deactivate", headers=staff).status_code == 409
    r = client.get(f"/customers", headers=staff); body = next(c for c in r.json() if c["id"] == nw["id"])
    assert client.put(f"/customers/{nw['id']}", headers=staff, json={"company_name": body["name"], "is_active": False}).status_code == 409
    r = client.post("/customers", headers=staff, json={"company_name": "Step4 Idle Co"}); assert r.status_code == 201
    cid = r.json()["id"]
    assert client.post(f"/customers/{cid}/deactivate", headers=staff).json()["status"] == "Inactive"
    assert client.post("/quotations", headers=staff, json={"customer_id": cid, "lines": [{"product_id": get(client, staff, "/products")[0]["id"], "plan_id": get(client, staff, "/plans")[0]["id"], "quantity": 1}]}).status_code == 409
    assert client.post(f"/customers/{cid}/activate", headers=staff).json()["status"] == "Active"

def test_login_rate_limit(client, admin, monkeypatch):
    from app import config
    from app.ratelimit import limiter
    client.post("/users", headers=admin, json={"email": "step4.rl@b.in", "password": "Strong#Pass1", "full_name": "Rate Limited"})
    monkeypatch.setattr(config, "LOGIN_MAX_FAILURES", 3); monkeypatch.setattr(config, "LOGIN_MAX_FAILURES_PER_IP", 1000); limiter.clear()
    bad = {"email": "step4.rl@b.in", "password": "nope"}; good = {"email": "step4.rl@b.in", "password": "Strong#Pass1"}
    for _ in range(2): assert client.post("/auth/login", json=bad).status_code == 401
    assert client.post("/auth/login", json=good).status_code == 200                      # a success clears the count ...
    for _ in range(2): assert client.post("/auth/login", json=bad).status_code == 401   # ... so these two are not the 3rd and 4th
    assert client.post("/auth/login", json=bad).status_code == 401
    r = client.post("/auth/login", json=good); assert r.status_code == 429 and int(r.headers["retry-after"]) > 0   # locked, even with the right password
    assert client.post("/auth/login", json={"email": "someone.else@b.in", "password": "nope"}).status_code == 401  # other accounts are unaffected
    limiter.clear(); assert client.post("/auth/login", json=good).status_code == 200
    # per-IP ceiling across different e-mail addresses
    monkeypatch.setattr(config, "LOGIN_MAX_FAILURES", 100); monkeypatch.setattr(config, "LOGIN_MAX_FAILURES_PER_IP", 4); limiter.clear()
    for i in range(4): assert client.post("/auth/login", json={"email": f"guess{i}@b.in", "password": "nope"}).status_code == 401
    assert client.post("/auth/login", json={"email": "guess9@b.in", "password": "nope"}).status_code == 429
    limiter.clear()

def test_forgot_password_and_register_are_throttled(client, monkeypatch):
    from app import config
    from app.ratelimit import limiter
    monkeypatch.setattr(config, "RESET_MAX_REQUESTS", 2); limiter.clear()
    for _ in range(2): assert client.post("/auth/forgot-password", json={"email": "unknown.step4@b.in"}).status_code == 200
    assert client.post("/auth/forgot-password", json={"email": "unknown.step4@b.in"}).status_code == 429          # same answer shape for unknown and known addresses
    assert client.post("/auth/forgot-password", json={"email": "unknown2.step4@b.in"}).status_code == 200
    monkeypatch.setattr(config, "REGISTER_MAX_PER_IP", 1); limiter.clear()
    assert client.post("/auth/register", json={"email": "step4.reg1@b.in", "password": "Strong#Pass1", "company_name": "R1"}).status_code == 201
    assert client.post("/auth/register", json={"email": "step4.reg2@b.in", "password": "Strong#Pass1", "company_name": "R2"}).status_code == 429
    limiter.clear()

def test_production_config_guard(monkeypatch):
    from app import config
    for k, v in (("ENVIRONMENT", "production"), ("JWT_SECRET", "x" * 40), ("CORS_ORIGINS", ["https://app.brightloop.in"]), ("DEV_RETURN_TOKENS", False),
                 ("EMAIL_BACKEND", "smtp"), ("APP_BASE_URL", "https://app.brightloop.in")): monkeypatch.setattr(config, k, v)
    assert config.production_problems() == []; config.assert_production_ready()
    monkeypatch.setattr(config, "JWT_SECRET", "dev-secret-change-me-please-32-bytes-min"); monkeypatch.setattr(config, "CORS_ORIGINS", ["*"]); monkeypatch.setattr(config, "DEV_RETURN_TOKENS", True)
    monkeypatch.setattr(config, "EMAIL_BACKEND", "console"); monkeypatch.setattr(config, "APP_BASE_URL", "http://localhost:8000")
    assert len(config.production_problems()) == 5
    with pytest.raises(RuntimeError) as e: config.assert_production_ready()
    assert "JWT_SECRET" in str(e.value) and "CORS_ORIGINS" in str(e.value)
    monkeypatch.setattr(config, "ENVIRONMENT", "development"); config.assert_production_ready()                      # development is never blocked

def test_security_headers(client):
    r = client.get("/health"); assert r.status_code == 200
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "SAMEORIGIN" and r.headers["referrer-policy"] == "same-origin"
