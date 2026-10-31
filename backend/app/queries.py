"""Query helpers for list pages and reports: pagination, filters and SQL-side aggregation.

Everything here keeps work in the database (COUNT/SUM/GROUP BY) so list and report pages stay fast with
thousands of rows, instead of loading whole tables into Python."""
import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from fastapi import Query, HTTPException
from sqlalchemy import select, func, and_, or_, case, text
from sqlalchemy.orm import selectinload, joinedload
from . import models as m

D = Decimal
LIVE_INVOICE = ("DRAFT", "CANCELLED", "VOID")   # invoices in these states are not "billed"

class Page:
    """?page=1&page_size=200 (max 500). Lists stay plain arrays; the total is returned in the X-Total-Count header."""
    def __init__(self, page: int = Query(1, ge=1), page_size: int = Query(200, ge=1, le=500)):
        self.page, self.page_size = page, page_size

def paginate(db, qry, response, pg: Page):
    total = db.execute(select(func.count()).select_from(qry.order_by(None).subquery())).scalar()
    response.headers["X-Total-Count"] = str(total)
    return qry.limit(pg.page_size).offset((pg.page - 1) * pg.page_size)

def to_uuid(x, what="id"):
    if x in (None, ""): return None
    try: return uuid.UUID(str(x))
    except ValueError: raise HTTPException(422, f"Invalid {what}")

def search(term: str, *cols):
    t = term.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return or_(*[c.ilike(f"%{t}%", escape="\\") for c in cols])

def flag(value: str, yes: str, no: str) -> bool:
    v = value.strip().lower()
    if v == yes: return True
    if v == no: return False
    raise HTTPException(422, f"Status must be {yes} or {no}")

def norm(value: str) -> str: return value.strip().upper().replace(" ", "_").replace("-", "_")

def day_start(d: date) -> datetime: return datetime.combine(d, time.min, tzinfo=timezone.utc)
def between_dates(col, d_from, d_to):
    out = []
    if d_from: out.append(col >= d_from)
    if d_to: out.append(col <= d_to)
    return out
def between_timestamps(col, d_from, d_to):
    out = []
    if d_from: out.append(col >= day_start(d_from))
    if d_to: out.append(col < day_start(d_to + timedelta(days=1)))
    return out

# ---------- derived statuses, as SQL ----------
def overdue_clause(today: date):
    return and_(m.Invoice.status.in_(("CONFIRMED", "PARTIALLY_PAID")), m.Invoice.balance_due > 0, m.Invoice.due_date < today)

def invoice_status_filter(status: str, today: date):
    k = {"PART_PAID": "PARTIALLY_PAID"}.get(norm(status), norm(status))
    if k not in {"DRAFT", "CONFIRMED", "PARTIALLY_PAID", "PAID", "CANCELLED", "VOID", "OVERDUE"}: raise HTTPException(422, "Unknown invoice status")
    if k == "OVERDUE": return overdue_clause(today)
    if k in ("CONFIRMED", "PARTIALLY_PAID"): return and_(m.Invoice.status == k, ~overdue_clause(today))   # same rule as derive_status
    return m.Invoice.status == k

def quotation_status_filter(status: str, today: date):
    k = norm(status)
    if k not in {"DRAFT", "SENT", "ACCEPTED", "EXPIRED", "REJECTED"}: raise HTTPException(422, "Unknown quotation status")
    lapsed = and_(m.Quotation.status.in_(("DRAFT", "SENT")), m.Quotation.valid_until < today)
    if k == "EXPIRED": return or_(m.Quotation.status == "EXPIRED", lapsed)
    if k in ("DRAFT", "SENT"): return and_(m.Quotation.status == k, ~lapsed)
    return m.Quotation.status == k

# ---------- reports ----------
PER_MONTH = {"DAILY": D(30), "WEEKLY": D("4.33"), "MONTHLY": D(1), "YEARLY": D(1) / 12}

def month_starts(end: date, n: int = 5) -> list[date]:
    out = []
    for k in range(n - 1, -1, -1):
        mm, yy = end.month - k, end.year
        while mm <= 0: mm += 12; yy -= 1
        out.append(date(yy, mm, 1))
    return out

def summary(db, today: date, date_from=None, date_to=None, customer_id=None, plan_id=None) -> dict:
    """Finance summary.
    - subscription figures (active, MRR, pipeline, expiries) are a snapshot: only customer/plan filters apply;
    - invoice figures (billed, outstanding, overdue, by plan, health) use invoices issued in [date_from, date_to];
    - collected uses RECORDED payments dated in [date_from, date_to] (with a plan filter: the amount allocated to that plan's invoices)."""
    cust, plan = to_uuid(customer_id, "customer_id"), to_uuid(plan_id, "plan_id")
    f = lambda x: float(x) if x is not None else None
    sub_where = ([m.Subscription.customer_id == cust] if cust else []) + ([m.Subscription.plan_id == plan] if plan else [])
    inv_where = ([m.Invoice.customer_id == cust] if cust else []) + ([m.Subscription.plan_id == plan] if plan else []) + between_dates(m.Invoice.issue_date, date_from, date_to)
    inv_from = lambda *cols: select(*cols).select_from(m.Invoice).join(m.Subscription, m.Subscription.id == m.Invoice.subscription_id)

    pipeline = {st: 0 for st in ("DRAFT", "QUOTATION", "CONFIRMED", "ACTIVE", "PAUSED", "CLOSED")}
    for st, n in db.execute(select(m.Subscription.status, func.count()).where(*sub_where).group_by(m.Subscription.status)).all(): pipeline[st] = n

    line_totals = select(m.SubscriptionLine.subscription_id.label("sid"), func.sum(m.SubscriptionLine.line_total).label("amt")) \
        .group_by(m.SubscriptionLine.subscription_id).subquery()
    mrr = D(0)
    for interval, count, amt in db.execute(select(m.SubscriptionPlan.billing_interval, m.SubscriptionPlan.interval_count, func.sum(line_totals.c.amt))
            .select_from(m.Subscription).join(m.SubscriptionPlan, m.SubscriptionPlan.id == m.Subscription.plan_id)
            .join(line_totals, line_totals.c.sid == m.Subscription.id).where(m.Subscription.status == "ACTIVE", *sub_where)
            .group_by(m.SubscriptionPlan.billing_interval, m.SubscriptionPlan.interval_count)).all():
        mrr += D(amt or 0) * PER_MONTH[interval] / count

    billed, outstanding = db.execute(inv_from(func.coalesce(func.sum(m.Invoice.total_amount), 0), func.coalesce(func.sum(m.Invoice.balance_due), 0))
        .where(m.Invoice.status.not_in(LIVE_INVOICE), *inv_where)).one()
    overdue_n, overdue_total = db.execute(inv_from(func.count(), func.coalesce(func.sum(m.Invoice.balance_due), 0))
        .where(overdue_clause(today), *inv_where)).one()

    health = {k: {"count": 0, "total": 0.0} for k in ("PAID", "CONFIRMED", "PARTIALLY_PAID", "OVERDUE", "DRAFT")}
    derived = case((overdue_clause(today), "OVERDUE"), else_=m.Invoice.status)
    for st, n, tot in db.execute(inv_from(derived, func.count(), func.coalesce(func.sum(m.Invoice.total_amount), 0)).where(*inv_where).group_by(text("1"))).all():
        if st in health: health[st] = {"count": n, "total": f(tot)}

    by_plan = [{"plan": name, "billed": f(b), "collected": f(c), "outstanding": f(o)} for name, b, c, o in db.execute(
        inv_from(m.SubscriptionPlan.name, func.sum(m.Invoice.total_amount), func.sum(m.Invoice.amount_paid), func.sum(m.Invoice.balance_due))
        .join(m.SubscriptionPlan, m.SubscriptionPlan.id == m.Subscription.plan_id)
        .where(m.Invoice.status.not_in(LIVE_INVOICE), *inv_where).group_by(m.SubscriptionPlan.name).order_by(m.SubscriptionPlan.name)).all()]

    # payments: with a plan filter go through allocations -> invoices -> subscriptions
    def pay_q(*cols, extra=()):
        pw = [m.Payment.status == "RECORDED"] + ([m.Payment.customer_id == cust] if cust else []) + list(extra)
        if plan:   # the amount column that applies is returned alongside the query
            return select(*cols).select_from(m.PaymentAllocation).join(m.Payment, m.Payment.id == m.PaymentAllocation.payment_id) \
                .join(m.Invoice, m.Invoice.id == m.PaymentAllocation.invoice_id).join(m.Subscription, m.Subscription.id == m.Invoice.subscription_id) \
                .where(m.Subscription.plan_id == plan, *pw), m.PaymentAllocation.allocated_amount
        return select(*cols).select_from(m.Payment).where(*pw), m.Payment.amount
    q1, _ = pay_q(func.coalesce(func.sum(m.PaymentAllocation.allocated_amount if plan else m.Payment.amount), 0),
                    func.count(func.distinct(m.Payment.id)), extra=between_timestamps(m.Payment.payment_date, date_from, date_to))
    collected, pay_count = db.execute(q1).one()

    # trailing 5 months ending at date_to (or today); customer/plan filters apply, date filters do not
    starts = month_starts(date_to or today); end = (starts[-1] + timedelta(days=32)).replace(day=1)
    billed_m = {(int(y), int(mo)): t for y, mo, t in db.execute(inv_from(func.extract("year", m.Invoice.issue_date), func.extract("month", m.Invoice.issue_date),
        func.coalesce(func.sum(m.Invoice.total_amount), 0)).where(m.Invoice.status.not_in(LIVE_INVOICE), m.Invoice.issue_date >= starts[0], m.Invoice.issue_date < end,
        *([m.Invoice.customer_id == cust] if cust else []), *([m.Subscription.plan_id == plan] if plan else [])).group_by(text("1"), text("2"))).all()}
    qm, _ = pay_q(func.extract("year", m.Payment.payment_date), func.extract("month", m.Payment.payment_date),
                  func.coalesce(func.sum(m.PaymentAllocation.allocated_amount if plan else m.Payment.amount), 0),
                  extra=between_timestamps(m.Payment.payment_date, starts[0], end - timedelta(days=1)))
    coll_m = {(int(y), int(mo)): t for y, mo, t in db.execute(qm.group_by(text("1"), text("2"))).all()}
    months = [{"month": s0.strftime("%b"), "year": s0.year, "billed": f(billed_m.get((s0.year, s0.month), 0)), "collected": f(coll_m.get((s0.year, s0.month), 0))} for s0 in starts]

    upcoming = db.execute(select(m.Subscription).where(m.Subscription.status == "ACTIVE", m.Subscription.expiry_date.is_not(None), *sub_where)
        .order_by(m.Subscription.expiry_date, m.Subscription.id).limit(5)
        .options(joinedload(m.Subscription.customer), joinedload(m.Subscription.plan), selectinload(m.Subscription.lines))).scalars().all()
    fmt = lambda d: d.strftime("%d %b %Y") if d else "—"
    return {"active_subscriptions": pipeline["ACTIVE"], "confirmed_subscriptions": pipeline["CONFIRMED"], "mrr": f(mrr),
            "billed": f(billed), "collected": f(collected), "payments_count": pay_count, "outstanding": f(outstanding),
            "overdue_count": overdue_n, "overdue_total": f(overdue_total), "pipeline": pipeline, "by_plan": by_plan, "months": months,
            "invoice_health": health,
            "upcoming_expiries": [{"customer": x.customer.company_name, "plan": x.plan.name, "expiry": fmt(x.expiry_date),
                                   "amount": f(sum((l.line_total for l in x.lines), D(0)))} for x in upcoming],
            "filters": {"date_from": str(date_from) if date_from else None, "date_to": str(date_to) if date_to else None,
                        "customer_id": str(cust) if cust else None, "plan_id": str(plan) if plan else None}}
