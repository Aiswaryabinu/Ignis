"""Business logic: numbering, tax, discounts, quotation conversion, billing, payments."""
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from dateutil.relativedelta import relativedelta
from fastapi import HTTPException
from sqlalchemy import select, func, or_, and_, text
from sqlalchemy.orm import Session
from . import models as m
from .ddl import SEQUENCES

D = Decimal
def q2(x) -> Decimal: return D(x).quantize(D("0.01"), rounding=ROUND_HALF_UP)
def today() -> date: return date.today()
def inr(x) -> str: return f"₹{D(str(x or 0)):,.2f}"
def now() -> datetime: return datetime.now(timezone.utc)

def next_number(db: Session, prefix: str, width=4) -> str:
    n = db.execute(text(f"SELECT nextval('{SEQUENCES[prefix]}')")).scalar()
    return f"{prefix}-{n:0{width}d}"

# ---------- audit / outbox ----------
def audit(db, actor, action, entity_type, entity_id, old=None, new=None, ip=None):
    db.add(m.AuditLog(actor_user_id=getattr(actor, "id", actor), action=action, entity_type=entity_type,
                      entity_id=entity_id, old_values=old, new_values=new, ip_address=ip))

def outbox(db, event_type, agg_type, agg_id, payload):
    db.add(m.OutboxEvent(event_type=event_type, aggregate_type=agg_type, aggregate_id=agg_id, payload=payload))

def notify(db, customer: m.Customer, ntype, subject, message, entity_type=None, entity_id=None):
    """Queue an in-app/email notification for the customer's portal user (if any)."""
    if customer and customer.user_id:
        db.add(m.Notification(user_id=customer.user_id, notification_type=ntype, subject=subject, message=message,
                              related_entity_type=entity_type, related_entity_id=entity_id))

# ---------- tax ----------
def find_tax(db: Session, product_id, on: date, customer: m.Customer | None = None):
    """Highest-priority active tax whose rule matches the product (or is generic) and country/state."""
    country = state = None
    if customer:
        a = next((x for x in customer.addresses if x.address_type == "BILLING" and x.is_default), None) or \
            next((x for x in customer.addresses if x.address_type == "BILLING"), None)
        if a: country, state = a.country, a.state
    rules = db.execute(select(m.TaxRule).join(m.Tax).where(
        m.TaxRule.is_active, m.Tax.is_active, m.Tax.effective_from <= on,
        or_(m.Tax.effective_until.is_(None), m.Tax.effective_until >= on),
        or_(m.TaxRule.product_id.is_(None), m.TaxRule.product_id == product_id),
        or_(m.TaxRule.country.is_(None), m.TaxRule.country == country),
        or_(m.TaxRule.state.is_(None), m.TaxRule.state == state))).scalars().all()
    if not rules: return None
    # specificity first (product, state, country), then explicit priority
    key = lambda r: (r.priority, r.product_id is not None, r.state is not None, r.country is not None)
    return max(rules, key=key).tax

def tax_amount(base: Decimal, tax: m.Tax | None):
    """Return (rate_snapshot, tax_amount, net_base). Percentage rate is e.g. 18.0 for 18%."""
    if not tax: return D(0), D(0), base
    if tax.tax_type == "FIXED": return tax.rate, q2(tax.rate), base
    r = tax.rate / 100
    if tax.is_inclusive:
        net = q2(base / (1 + r)); return tax.rate, q2(base - net), net
    return tax.rate, q2(base * r), base

def unit_price_for(product: m.Product, variant: m.ProductVariant | None) -> Decimal:
    return q2(product.sales_price + (variant.additional_price if variant else 0))

# ---------- subscription state machine ----------
TRANSITIONS = {"DRAFT": {"QUOTATION", "CONFIRMED", "CLOSED"}, "QUOTATION": {"CONFIRMED", "DRAFT", "CLOSED"},
               "CONFIRMED": {"ACTIVE", "CLOSED"}, "ACTIVE": {"PAUSED", "CLOSED"}, "PAUSED": {"ACTIVE", "CLOSED"}, "CLOSED": set()}

def add_interval(anchor: date, plan: m.SubscriptionPlan, n: int) -> date:
    k = plan.interval_count * n
    return anchor + {"DAILY": relativedelta(days=k), "WEEKLY": relativedelta(weeks=k),
                     "MONTHLY": relativedelta(months=k), "YEARLY": relativedelta(years=k)}[plan.billing_interval]

def first_period_on_or_after(anchor: date, plan, d: date) -> int:
    n = 0
    while add_interval(anchor, plan, n) < d: n += 1
    return n

def set_status(db, sub: m.Subscription, new: str, actor=None, reason=None, on: date | None = None):
    on = on or today()
    if new not in TRANSITIONS[sub.status]:
        raise HTTPException(409, f"Cannot move a {sub.status.title()} subscription to {new.title()}")
    plan = sub.plan
    if new == "PAUSED" and not plan.allow_pause: raise HTTPException(409, "This plan does not allow pausing")
    if new == "CLOSED" and sub.status in ("ACTIVE", "PAUSED") and not plan.allow_early_close \
            and not (sub.expiry_date and sub.expiry_date <= on):
        raise HTTPException(409, "This plan does not allow early close")
    if new == "ACTIVE" and sub.status == "CONFIRMED" and sub.start_date > on:
        raise HTTPException(409, f"Cannot activate before the start date ({sub.start_date})")
    old = sub.status
    sub.status = new
    if new == "ACTIVE" and old == "CONFIRMED":
        sub.billing_anchor_date = sub.start_date
        sub.next_billing_date = sub.start_date
    if new == "PAUSED": sub.paused_at = now()
    if new == "ACTIVE" and old == "PAUSED":
        sub.paused_at = None  # periods missed while paused are not billed
        if sub.next_billing_date and sub.next_billing_date < today():
            n = first_period_on_or_after(sub.billing_anchor_date, plan, today())
            sub.next_billing_date = add_interval(sub.billing_anchor_date, plan, n)
    if new == "CLOSED": sub.closed_at = now(); sub.next_billing_date = None
    db.add(m.SubscriptionStatusHistory(subscription_id=sub.id, old_status=old, new_status=new,
                                       changed_by=getattr(actor, "id", None), reason=reason))
    audit(db, actor, f"subscription.{new.lower()}", "subscription", sub.id, {"status": old}, {"status": new})

def build_sub_line(db, product, variant, qty, unit_price=None, discount=D(0), on=None, customer=None):
    price = q2(unit_price) if unit_price is not None else unit_price_for(product, variant)
    tax = find_tax(db, product.id, on or today(), customer)
    base = q2(price * qty - discount)
    rate, tamt, net = tax_amount(base, tax)
    total = base if (tax and tax.is_inclusive) else q2(base + tamt)
    return m.SubscriptionLine(product_id=product.id, variant_id=variant.id if variant else None,
        product_name=product.name, variant_name=f"{variant.attribute_name}: {variant.attribute_value}" if variant else None,
        quantity=qty, unit_price=price, tax_id=tax.id if tax else None, tax_rate_snapshot=rate,
        discount_amount=q2(discount), line_total=total)

def default_expiry(plan: m.SubscriptionPlan, start: date, explicit: date | None = None) -> date | None:
    """Subscription expiry: the explicit value, else the plan's end date (if after the start)."""
    if explicit: return explicit
    return plan.end_date if plan.end_date and plan.end_date > start else None

# ---------- quotation ----------
def price_quotation_line(db, plan, product, variant, qty, unit_price, discount, on, customer):
    if qty < plan.minimum_quantity:
        raise HTTPException(422, f"{plan.name} needs at least {plan.minimum_quantity} units")
    price = q2(unit_price) if unit_price is not None else unit_price_for(product, variant)
    tax = find_tax(db, product.id, on, customer)
    base = q2(price * qty - discount)
    if base < 0: raise HTTPException(422, "Discount exceeds line amount")
    rate, tamt, net = tax_amount(base, tax)
    total = base if (tax and tax.is_inclusive) else q2(base + tamt)
    return m.QuotationLine(product_id=product.id, variant_id=variant.id if variant else None, plan_id=plan.id,
        product_name=product.name, variant_name=f"{variant.attribute_name}: {variant.attribute_value}" if variant else None,
        quantity=qty, unit_price=price, discount_amount=q2(discount), tax_rate_snapshot=rate,
        tax_amount=tamt, line_total=total)

def recompute_quotation_totals(qt: m.Quotation):
    qt.subtotal = q2(sum(l.unit_price * l.quantity for l in qt.lines))
    qt.discount_total = q2(sum(l.discount_amount for l in qt.lines))
    qt.tax_total = q2(sum(l.tax_amount for l in qt.lines))
    qt.grand_total = q2(sum(l.line_total for l in qt.lines))

def convert_quotation(db: Session, quotation_id, actor, start_date: date | None = None, payment_terms=None, auto_renew=False):
    qt = db.execute(select(m.Quotation).where(m.Quotation.id == quotation_id).with_for_update()).scalar_one_or_none()
    if not qt: raise HTTPException(404, "Quotation not found")
    if qt.status not in ("SENT", "ACCEPTED"): raise HTTPException(409, f"Only a sent quotation can be accepted (this one is {qt.status.title()})")
    if qt.valid_until < today():
        qt.status = "EXPIRED"; db.commit()
        raise HTTPException(409, "This quotation has expired")
    if db.execute(select(m.Subscription.id).where(m.Subscription.quotation_id == qt.id)).first():
        raise HTTPException(409, "This quotation has already been converted")
    plan_ids = {l.plan_id for l in qt.lines}
    if len(plan_ids) != 1: raise HTTPException(422, "All lines of a quotation must use the same plan to become one subscription")
    plan = db.get(m.SubscriptionPlan, plan_ids.pop())
    start = start_date or today()
    if not plan.is_active or start < plan.start_date or (plan.end_date and start > plan.end_date):
        raise HTTPException(409, "The plan is not available for that start date")
    sub = m.Subscription(subscription_number=next_number(db, "SUB"), customer_id=qt.customer_id, plan_id=plan.id,
        quotation_id=qt.id, start_date=start, expiry_date=default_expiry(plan, start), payment_terms=payment_terms, auto_renew=auto_renew,
        status="QUOTATION", created_by=actor.id)
    db.add(sub); db.flush()
    for l in qt.lines:   # snapshot what was agreed
        sub.lines.append(m.SubscriptionLine(product_id=l.product_id, variant_id=l.variant_id, product_name=l.product_name,
            variant_name=l.variant_name, quantity=l.quantity, unit_price=l.unit_price, tax_rate_snapshot=l.tax_rate_snapshot,
            tax_id=(lambda t: t.id if t else None)(find_tax(db, l.product_id, start, qt.customer)),
            discount_amount=l.discount_amount, line_total=l.line_total))
    db.add(m.SubscriptionStatusHistory(subscription_id=sub.id, old_status=None, new_status="QUOTATION", changed_by=actor.id, reason=f"Created from {qt.quotation_number}"))
    qt.status = "ACCEPTED"; qt.accepted_at = now()
    db.flush(); db.refresh(sub)
    set_status(db, sub, "CONFIRMED", actor, "Quotation accepted")
    audit(db, actor, "quotation.converted", "quotation", qt.id, {"status": "SENT"}, {"status": "ACCEPTED", "subscription": sub.subscription_number})
    return sub

# ---------- renewal ----------
def renewal_term(db: Session, sub: m.Subscription) -> timedelta:
    """Length of the ORIGINAL term (expiry at creation - start). Every renewal extends by this much,
    so repeated renewals add the same duration instead of doubling."""
    first = db.execute(select(m.SubscriptionRenewal).where(m.SubscriptionRenewal.subscription_id == sub.id,
        m.SubscriptionRenewal.status == "COMPLETED").order_by(m.SubscriptionRenewal.new_expiry_date).limit(1)).scalar_one_or_none()
    original_expiry = first.previous_expiry_date if first and first.previous_expiry_date else sub.expiry_date
    return original_expiry - sub.start_date

def renew_subscription(db: Session, sub: m.Subscription, actor=None, on: date | None = None) -> date:
    """Extend an active/paused subscription by its original term. Used by the manual endpoint and the billing run."""
    on = on or today(); plan = sub.plan
    if not plan.allow_renewal: raise HTTPException(409, "This plan does not allow renewal")
    if sub.status not in ("ACTIVE", "PAUSED") or not sub.expiry_date:
        raise HTTPException(409, "Only an active subscription with an expiry date can be renewed")
    prev = sub.expiry_date; new = prev + renewal_term(db, sub)
    db.add(m.SubscriptionRenewal(subscription_id=sub.id, previous_expiry_date=prev, new_expiry_date=new, renewal_date=on,
                                 renewed_by=getattr(actor, "id", None), status="COMPLETED"))
    sub.expiry_date = new
    if not sub.next_billing_date and sub.status == "ACTIVE":   # billing had stopped at the old expiry: pick it up again
        n = first_period_on_or_after(sub.billing_anchor_date, plan, prev)
        sub.next_billing_date = add_interval(sub.billing_anchor_date, plan, n)
    audit(db, actor, "subscription.renewed", "subscription", sub.id, {"expiry": str(prev)}, {"expiry": str(new)})
    return new

# ---------- billing ----------
def sub_amount(sub: m.Subscription) -> Decimal:
    return q2(sum(l.line_total for l in sub.lines))

def eligible_discounts(db, now_ts):
    return db.execute(select(m.Discount).where(m.Discount.is_active, m.Discount.start_date <= now_ts,
        or_(m.Discount.end_date.is_(None), m.Discount.end_date >= now_ts),
        or_(m.Discount.usage_limit.is_(None), m.Discount.usage_count < m.Discount.usage_limit))
        .with_for_update()).scalars().all()

def apply_discounts(db, sub, line_rows):
    """line_rows: list of dicts {line, gross, discount}. Returns list of (discount, amount)."""
    used = []
    for d in eligible_discounts(db, now()):
        if d.usage_limit is not None and d.usage_count >= d.usage_limit: continue
        if d.scope == "SUBSCRIPTION":
            gross = sum(r["gross"] for r in line_rows); qty = sum(r["line"].quantity for r in line_rows)
            if gross < d.min_purchase or qty < d.min_quantity: continue
            amt = q2(gross * d.value / 100) if d.discount_type == "PERCENTAGE" else q2(d.value)
            amt = min(amt, sum(r["gross"] - r["discount"] for r in line_rows))
            tot = sum(r["gross"] for r in line_rows) or D(1)
            for r in line_rows: r["discount"] += q2(amt * r["gross"] / tot)
        else:
            pids = {p.product_id for p in d.products}
            rows = [r for r in line_rows if r["line"].product_id in pids]
            if not rows: continue
            gross = sum(r["gross"] for r in rows); qty = sum(r["line"].quantity for r in rows)
            if gross < d.min_purchase or qty < d.min_quantity: continue
            amt = q2(gross * d.value / 100) if d.discount_type == "PERCENTAGE" else q2(d.value)
            amt = min(amt, sum(r["gross"] - r["discount"] for r in rows))
            for r in rows: r["discount"] += q2(amt * r["gross"] / gross)
        if amt > 0: used.append((d, amt))
    return used

def due_date_for(sub, issue: date) -> date:
    t = (sub.payment_terms or "").lower()
    if t.startswith("net"):
        try: return issue + timedelta(days=int(t.split()[1]))
        except (IndexError, ValueError): pass
    return issue

def bill_period(db: Session, sub: m.Subscription, start: date, end: date, on: date) -> m.Invoice | None:
    """Create the invoice for one billing period. Idempotent on (subscription, period)."""
    key = f"{sub.id}:{start}:{end}"
    job = db.execute(select(m.BillingJob).where(m.BillingJob.idempotency_key == key).with_for_update()).scalar_one_or_none()
    if job and job.status == "COMPLETED": return None
    if not job:
        job = m.BillingJob(subscription_id=sub.id, billing_period_start=start, billing_period_end=end, idempotency_key=key, status="PROCESSING")
        db.add(job)
    job.status = "PROCESSING"; job.attempts = (job.attempts or 0) + 1
    if db.execute(select(m.Invoice.id).where(m.Invoice.subscription_id == sub.id,
            m.Invoice.billing_period_start == start, m.Invoice.billing_period_end == end)).first():
        job.status = "COMPLETED"; job.completed_at = now(); return None
    cust = sub.customer
    rows = []
    for l in sub.lines:
        gross = q2(l.unit_price * l.quantity)
        rows.append({"line": l, "gross": gross, "discount": q2(l.discount_amount)})
    used = apply_discounts(db, sub, rows)
    issue = min(on, start)   # catch-up invoices for past periods are dated at the period start
    inv = m.Invoice(invoice_number=next_number(db, "INV"), customer_id=sub.customer_id, subscription_id=sub.id,
        issue_date=issue, due_date=due_date_for(sub, issue), billing_period_start=start, billing_period_end=end,
        subtotal=0, total_amount=0, balance_due=0, status="DRAFT")
    db.add(inv); db.flush()
    sub_t = disc_t = tax_t = tot_t = D(0)
    for r in rows:
        l = r["line"]; base = q2(max(r["gross"] - r["discount"], 0))
        tax = db.get(m.Tax, l.tax_id) if l.tax_id else None
        if tax: rate, tamt, net = tax_amount(base, tax)   # rate is snapshotted from the agreed line
        else: rate, tamt, net = l.tax_rate_snapshot, q2(base * l.tax_rate_snapshot / 100), base
        total = base if (tax and tax.is_inclusive) else q2(base + tamt)
        desc = f"{l.product_name}{' – ' + l.variant_name if l.variant_name else ''} ({start:%d %b %Y} to {end:%d %b %Y})"
        inv.lines.append(m.InvoiceLine(product_id=l.product_id, variant_id=l.variant_id, description=desc[:500],
            quantity=l.quantity, unit_price=l.unit_price, discount_amount=r["discount"], taxable_amount=net if tax else base,
            tax_rate_snapshot=rate, tax_amount=tamt, line_total=total))
        sub_t += r["gross"]; disc_t += r["discount"]; tax_t += tamt; tot_t += total
    inv.subtotal, inv.discount_total, inv.tax_total = q2(sub_t), q2(disc_t), q2(tax_t)
    inv.total_amount = inv.balance_due = q2(tot_t)
    for d, amt in used:
        d.usage_count += 1
        db.add(m.DiscountUsage(discount_id=d.id, customer_id=sub.customer_id, subscription_id=sub.id, invoice_id=inv.id, discount_amount=amt))
    db.flush()
    bp = db.execute(select(m.BillingPeriod).where(m.BillingPeriod.subscription_id == sub.id,
            m.BillingPeriod.period_start == start, m.BillingPeriod.period_end == end)).scalar_one_or_none()
    if not bp:
        bp = m.BillingPeriod(subscription_id=sub.id, period_start=start, period_end=end, billing_date=on); db.add(bp)
    bp.invoice_id, bp.status = inv.id, "BILLED"
    job.status, job.completed_at, job.error_message = "COMPLETED", now(), None
    outbox(db, "invoice.created", "invoice", inv.id, {"invoice_number": inv.invoice_number, "customer_id": str(inv.customer_id)})
    audit(db, None, "invoice.generated", "invoice", inv.id, None, {"number": inv.invoice_number, "total": str(inv.total_amount)})
    return inv

def record_failure(db, sid, err):
    """Persist a FAILED billing job (separate transaction) so it can be retried and inspected."""
    try:
        sub = db.get(m.Subscription, sid)
        if not sub or not sub.next_billing_date: return
        n = first_period_on_or_after(sub.billing_anchor_date, sub.plan, sub.next_billing_date)
        start = add_interval(sub.billing_anchor_date, sub.plan, n); end = add_interval(sub.billing_anchor_date, sub.plan, n + 1) - timedelta(days=1)
        key = f"{sub.id}:{start}:{end}"
        job = db.execute(select(m.BillingJob).where(m.BillingJob.idempotency_key == key)).scalar_one_or_none()
        if not job:
            job = m.BillingJob(subscription_id=sub.id, billing_period_start=start, billing_period_end=end, idempotency_key=key, attempts=0); db.add(job)
        if job.status == "COMPLETED": return     # another worker finished this period meanwhile
        job.status, job.error_message, job.attempts = "FAILED", str(err)[:1000], (job.attempts or 0) + 1
        db.commit()
    except Exception:
        db.rollback()

def run_billing(db: Session, on: date | None = None, subscription_id=None, actor=None):
    """Activate due subscriptions, close expired ones, then invoice every due period (catches up, never twice)."""
    on = on or today(); created, skipped, failed, renewed = [], 0, [], []
    if subscription_id:   # the API passes a string; comparing it with a UUID column value in Python never matched
        try: subscription_id = uuid.UUID(str(subscription_id))
        except ValueError: raise HTTPException(422, "Invalid subscription_id")
    # confirmed -> active when start date reached (one bad subscription must not stop the run)
    aq = select(m.Subscription).where(m.Subscription.status == "CONFIRMED", m.Subscription.start_date <= on)
    if subscription_id: aq = aq.where(m.Subscription.id == subscription_id)
    for sub in db.execute(aq).scalars().all():
        try: set_status(db, sub, "ACTIVE", actor, "Start date reached", on=on); db.commit()
        except Exception as e: db.rollback(); failed.append({"subscription_id": str(sub.id), "error": str(getattr(e, "detail", e))})
    # auto-renew: subscriptions flagged auto_renew on a renewable, non auto-close plan are extended instead of left to lapse
    rq = select(m.Subscription).join(m.SubscriptionPlan).where(m.Subscription.status == "ACTIVE", m.Subscription.auto_renew,
        m.Subscription.expiry_date.is_not(None), m.Subscription.expiry_date <= on, m.SubscriptionPlan.allow_renewal,
        m.SubscriptionPlan.auto_close.is_(False), m.SubscriptionPlan.is_active)
    if subscription_id: rq = rq.where(m.Subscription.id == subscription_id)
    for sub in db.execute(rq).scalars().all():
        try:
            guard = 0
            while sub.expiry_date <= on and guard < 24 and not (sub.plan.end_date and sub.plan.end_date <= sub.expiry_date):
                renew_subscription(db, sub, actor, on); guard += 1
            db.commit()
            if guard: renewed.append(sub.subscription_number)
        except Exception as e:
            db.rollback(); failed.append({"subscription_id": str(sub.id), "error": str(getattr(e, "detail", e))})
    q = select(m.Subscription.id).where(m.Subscription.status == "ACTIVE", m.Subscription.next_billing_date <= on)
    if subscription_id: q = q.where(m.Subscription.id == subscription_id)
    for sid in db.execute(q).scalars().all():
        try:
            sub = db.execute(select(m.Subscription).where(m.Subscription.id == sid).with_for_update().execution_options(populate_existing=True)).scalar_one()   # re-read: another worker may have billed it meanwhile
            guard = 0
            while sub.status == "ACTIVE" and sub.next_billing_date and sub.next_billing_date <= on and guard < 60:
                guard += 1
                n = first_period_on_or_after(sub.billing_anchor_date, sub.plan, sub.next_billing_date)
                start = add_interval(sub.billing_anchor_date, sub.plan, n)
                nxt = add_interval(sub.billing_anchor_date, sub.plan, n + 1)
                if sub.expiry_date and start >= sub.expiry_date:
                    sub.next_billing_date = None
                    break
                end = nxt - timedelta(days=1)
                inv = bill_period(db, sub, start, end, on)
                if inv: created.append(inv.invoice_number)
                else: skipped += 1
                sub.next_billing_date = nxt
                if sub.expiry_date and nxt >= sub.expiry_date: sub.next_billing_date = None
            db.commit()
        except Exception as e:  # one bad subscription must not stop the run
            db.rollback(); failed.append({"subscription_id": str(sid), "error": str(e)})
            record_failure(db, sid, e)
    # auto-close: plans flagged auto_close end their subscriptions at expiry. This must not depend on
    # next_billing_date, which is NULL once the final period has been billed.
    closed = []
    cq = select(m.Subscription).join(m.SubscriptionPlan).where(m.Subscription.status.in_(("ACTIVE", "PAUSED")),
        m.SubscriptionPlan.auto_close, m.Subscription.expiry_date.is_not(None), m.Subscription.expiry_date <= on)
    if subscription_id: cq = cq.where(m.Subscription.id == subscription_id)
    for sub in db.execute(cq).scalars().all():
        try:
            set_status(db, sub, "CLOSED", actor, "Reached expiry (auto close)", on=on); db.commit(); closed.append(sub.subscription_number)
        except Exception as e:
            db.rollback(); failed.append({"subscription_id": str(sub.id), "error": str(getattr(e, "detail", e))})
    return {"created": created, "already_billed": skipped, "failed": failed, "closed": closed, "renewed": renewed}

# ---------- invoices ----------
def derive_status(inv: m.Invoice) -> str:
    if inv.status in ("CONFIRMED", "PARTIALLY_PAID") and inv.balance_due > 0 and inv.due_date < today(): return "OVERDUE"
    return inv.status

def confirm_invoice(db, inv, actor):
    if inv.status != "DRAFT": raise HTTPException(409, "Only a draft invoice can be confirmed")
    inv.status = "CONFIRMED"
    notify(db, inv.customer, "invoice.confirmed", f"Invoice {inv.invoice_number}", f"Amount due ₹{inv.balance_due}, due {inv.due_date}.", "invoice", inv.id)
    outbox(db, "invoice.confirmed", "invoice", inv.id, {"invoice_number": inv.invoice_number})
    audit(db, actor, "invoice.confirmed", "invoice", inv.id, {"status": "DRAFT"}, {"status": "CONFIRMED"})

def send_invoice(db, inv, actor):
    """Queue the invoice for delivery to the customer (portal notification + outbox event for the e-mail worker)."""
    if inv.status in ("DRAFT", "CANCELLED", "VOID"): raise HTTPException(409, "Confirm the invoice before sending it")
    notify(db, inv.customer, "invoice.sent", f"Invoice {inv.invoice_number}", f"Amount due ₹{inv.balance_due}, due {inv.due_date}.", "invoice", inv.id)
    period = f"{inv.billing_period_start:%d %b %Y} – {inv.billing_period_end:%d %b %Y}" if inv.billing_period_start and inv.billing_period_end else "your subscription"
    outbox(db, "invoice.sent", "invoice", inv.id, {"to": inv.customer.billing_email, "customer": inv.customer.company_name, "invoice_number": inv.invoice_number,
           "period": period, "total": inr(inv.total_amount), "balance": inr(inv.balance_due), "due_date": f"{inv.due_date:%d %b %Y}"})
    audit(db, actor, "invoice.sent", "invoice", inv.id, None, {"to": inv.customer.billing_email})

def recompute_invoice_paid(db, inv: m.Invoice):
    paid = db.execute(select(func.coalesce(func.sum(m.PaymentAllocation.allocated_amount), 0))
        .join(m.Payment).where(m.PaymentAllocation.invoice_id == inv.id, m.Payment.status == "RECORDED")).scalar()
    inv.amount_paid = q2(paid); inv.balance_due = q2(inv.total_amount - paid)
    if inv.status in ("CONFIRMED", "PARTIALLY_PAID", "PAID"):
        inv.status = "PAID" if inv.balance_due <= 0 else ("PARTIALLY_PAID" if paid > 0 else "CONFIRMED")

def cancel_invoice(db, inv, actor, void=False):
    if inv.amount_paid > 0: raise HTTPException(409, "Reverse its payments before cancelling this invoice")
    if inv.status in ("CANCELLED", "VOID"): raise HTTPException(409, "Already cancelled")
    old = inv.status; inv.status = "VOID" if void else "CANCELLED"
    audit(db, actor, "invoice.cancelled", "invoice", inv.id, {"status": old}, {"status": inv.status})

# ---------- payments ----------
def record_payment(db: Session, actor, customer_id, method, amount, payment_date, reference, notes, allocations):
    amount = q2(amount)
    if amount <= 0: raise HTTPException(422, "Payment amount must be positive")
    if not allocations: raise HTTPException(422, "Allocate the payment to at least one invoice")
    total = q2(sum(q2(a["amount"]) for a in allocations))
    if total > amount: raise HTTPException(422, "Allocations exceed the payment amount")
    pay = m.Payment(payment_number=next_number(db, "PAY"), customer_id=customer_id, payment_method=method, amount=amount,
        payment_date=payment_date or now(), reference_number=reference, notes=notes, status="RECORDED", recorded_by=actor.id)
    db.add(pay); db.flush()
    seen = set()
    for a in allocations:
        amt = q2(a["amount"])
        if amt <= 0: raise HTTPException(422, "Allocated amount must be positive")
        if a["invoice_id"] in seen: raise HTTPException(422, "Invoice listed twice in allocations")
        seen.add(a["invoice_id"])
        inv = db.execute(select(m.Invoice).where(m.Invoice.id == a["invoice_id"]).with_for_update()).scalar_one_or_none()
        if not inv: raise HTTPException(404, "Invoice not found")
        if inv.customer_id != customer_id: raise HTTPException(422, f"{inv.invoice_number} belongs to a different customer")
        if inv.status not in ("CONFIRMED", "PARTIALLY_PAID"): raise HTTPException(409, f"{inv.invoice_number} is {inv.status.title()} and cannot take payment")
        if amt > inv.balance_due: raise HTTPException(422, f"Allocation exceeds the balance of {inv.invoice_number} (₹{inv.balance_due})")
        db.add(m.PaymentAllocation(payment_id=pay.id, invoice_id=inv.id, allocated_amount=amt))
        db.flush(); recompute_invoice_paid(db, inv)
    cust = db.get(m.Customer, customer_id)
    notify(db, cust, "payment.recorded", f"Payment {pay.payment_number} received", f"We received ₹{amount}. Thank you.", "payment", pay.id)
    outbox(db, "payment.recorded", "payment", pay.id, {"to": cust.billing_email, "customer": cust.company_name, "payment_number": pay.payment_number, "amount": inr(amount)})
    audit(db, actor, "payment.recorded", "payment", pay.id, None, {"number": pay.payment_number, "amount": str(amount)})
    return pay

def reverse_payment(db: Session, actor, pay: m.Payment):
    pay = db.execute(select(m.Payment).where(m.Payment.id == pay.id).with_for_update()).scalar_one()
    if pay.status == "REVERSED": raise HTTPException(409, "Payment already reversed")
    pay.status = "REVERSED"; db.flush()
    for al in pay.allocations:
        inv = db.execute(select(m.Invoice).where(m.Invoice.id == al.invoice_id).with_for_update()).scalar_one()
        recompute_invoice_paid(db, inv)
    audit(db, actor, "payment.reversed", "payment", pay.id, {"status": "RECORDED"}, {"status": "REVERSED"})
