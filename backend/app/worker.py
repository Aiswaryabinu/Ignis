"""Background work: outbox -> e-mail, overdue reminders, and the daily billing run.

Run inside the API (SCHEDULER_ENABLED=1, default) or as its own process:
    python -m app.worker           # loop forever (set SCHEDULER_ENABLED=0 on the API instances)
    python -m app.worker --once    # one outbox pass + the daily jobs, then exit (cron friendly)
Several instances are safe: outbox rows are claimed with FOR UPDATE SKIP LOCKED and the daily jobs take a Postgres advisory lock."""
import logging, sys, threading
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from string import Template
from sqlalchemy import select, func, or_, text
from sqlalchemy.orm import joinedload
from . import config, models as m, services as s, queries as Q
from .db import SessionLocal, engine
from .mailer import send_email

log = logging.getLogger("brightloop.worker")
LOCK_DAILY = 727001
SECRET_KEYS = ("link",)      # removed from an outbox payload once the e-mail has gone out (reset/verify links)

# ---------- templates ($name placeholders; admins can override per event in the notification_templates table) ----------
DEFAULT_TEMPLATES = {
    "auth.verify_email": ("Confirm your Brightloop email", "Hi $name,\n\nPlease confirm your email address:\n$link\n\nThe link works for 2 days. If you did not create an account, ignore this message.\n\nBrightloop Software"),
    "auth.password_reset": ("Reset your Brightloop password", "Hi $name,\n\nUse this link to choose a new password:\n$link\n\nIt works once and expires in 1 hour. If you did not ask for it, you can ignore this message.\n\nBrightloop Software"),
    "invoice.sent": ("Invoice $invoice_number from Brightloop", "Hello $customer,\n\nInvoice $invoice_number for $period is attached to your account.\nTotal: $total\nBalance due: $balance\nDue date: $due_date\n\nYou can view it any time in the customer portal: $portal\n\nBrightloop Software"),
    "invoice.overdue_reminder": ("Reminder: invoice $invoice_number is overdue", "Hello $customer,\n\nInvoice $invoice_number was due on $due_date and is $days_overdue day(s) overdue. Balance due: $balance.\nIf you have already paid, please ignore this reminder.\n\nPortal: $portal\n\nBrightloop Software"),
    "quotation.sent": ("Quotation $quotation_number from Brightloop", "Hello $customer,\n\nYour quotation $quotation_number totals $total and is valid until $valid_until.\nYou can accept it in the customer portal: $portal\n\nBrightloop Software"),
    "payment.recorded": ("Payment $payment_number received", "Hello $customer,\n\nWe received your payment of $amount (ref. $payment_number). Thank you.\n\nBrightloop Software"),
}
MAILABLE = set(DEFAULT_TEMPLATES)

inr = s.inr

def render_event(db, event_type: str, p: dict):
    """-> (to, subject, body), or None when this event type is not e-mailed."""
    if event_type not in MAILABLE: return None
    to = p.get("to")
    if not to: return None                                        # nobody to mail (customer has no billing e-mail)
    t = db.execute(select(m.NotificationTemplate).where(m.NotificationTemplate.event_type == event_type, m.NotificationTemplate.is_active)).scalar_one_or_none()
    subject, body = (t.subject_template, t.body_template) if t else DEFAULT_TEMPLATES[event_type]
    ctx = {k: ("" if v is None else v) for k, v in p.items() if not k.startswith("_")}
    ctx.setdefault("portal", config.APP_BASE_URL)
    return to, Template(subject).safe_substitute(ctx), Template(body).safe_substitute(ctx)

# ---------- outbox ----------
def process_outbox(db, limit: int = 50) -> dict:
    """Deliver PENDING events one transaction each (a row lock is held while its mail is sent). At-least-once:
    failures back off (2, 4, 8 ... min, max 60) and become FAILED after OUTBOX_MAX_ATTEMPTS."""
    res = {"sent": 0, "skipped": 0, "retry": 0, "failed": 0}
    for _ in range(limit):
        now = datetime.now(timezone.utc)
        not_before = m.OutboxEvent.payload["_not_before"].astext
        ev = db.execute(select(m.OutboxEvent).where(m.OutboxEvent.status == "PENDING", or_(not_before.is_(None), not_before <= now.isoformat()))
                        .order_by(m.OutboxEvent.created_at, m.OutboxEvent.id).limit(1).with_for_update(skip_locked=True)).scalar_one_or_none()
        if not ev: break
        p = dict(ev.payload)
        try:
            msg = render_event(db, ev.event_type, p)
            if msg: send_email(*msg)
        except Exception as e:
            n = int(p.get("_attempts", 0)) + 1
            p["_attempts"], p["_error"] = n, str(e)[:300]
            if n >= config.OUTBOX_MAX_ATTEMPTS: ev.status = "FAILED"; res["failed"] += 1
            else: p["_not_before"] = (now + timedelta(minutes=min(60, 2 ** n))).isoformat(); res["retry"] += 1
            ev.payload = p; db.commit(); log.warning("outbox %s %s failed (attempt %s): %s", ev.id, ev.event_type, n, e); continue
        for k in SECRET_KEYS: p.pop(k, None)
        for k in ("_not_before", "_error"): p.pop(k, None)
        if not msg: p["_skipped"] = "not e-mailed" if ev.event_type not in MAILABLE else "no recipient"
        ev.payload, ev.status, ev.published_at = p, "PUBLISHED", now
        res["sent" if msg else "skipped"] += 1; db.commit()
    return res

# ---------- overdue reminders ----------
def send_overdue_reminders(db, today: date | None = None) -> int:
    """Queue a reminder for every overdue invoice: first the day after it falls due, then every REMINDER_INTERVAL_DAYS, at most REMINDER_MAX."""
    today = today or date.today(); now = datetime.now(timezone.utc)
    invs = db.execute(select(m.Invoice).options(joinedload(m.Invoice.customer)).where(Q.overdue_clause(today)).order_by(m.Invoice.due_date)).scalars().all()
    if not invs: return 0
    prior = {a: (n, last) for a, n, last in db.execute(select(m.OutboxEvent.aggregate_id, func.count(), func.max(m.OutboxEvent.created_at))
             .where(m.OutboxEvent.event_type == "invoice.overdue_reminder", m.OutboxEvent.aggregate_id.in_([i.id for i in invs])).group_by(m.OutboxEvent.aggregate_id)).all()}
    queued = 0
    for i in invs:
        n, last = prior.get(i.id, (0, None))
        if n >= config.REMINDER_MAX or (last and now - last < timedelta(days=config.REMINDER_INTERVAL_DAYS) - timedelta(hours=1)): continue
        days = (today - i.due_date).days
        s.outbox(db, "invoice.overdue_reminder", "invoice", i.id, {"to": i.customer.billing_email, "customer": i.customer.company_name, "invoice_number": i.invoice_number,
                 "balance": inr(i.balance_due), "due_date": f"{i.due_date:%d %b %Y}", "days_overdue": days})
        s.notify(db, i.customer, "invoice.overdue", f"Invoice {i.invoice_number} is overdue", f"Balance ₹{i.balance_due} was due on {i.due_date}.", "invoice", i.id)
        s.audit(db, None, "invoice.reminder_queued", "invoice", i.id, None, {"days_overdue": days, "reminder_no": n + 1})
        queued += 1
    db.commit(); return queued

# ---------- daily jobs, one instance at a time ----------
@contextmanager
def single_instance(key: int):
    """Session-level Postgres advisory lock on a dedicated connection (released on exit or if the process dies)."""
    with engine.connect() as conn:
        got = bool(conn.execute(text("select pg_try_advisory_lock(:k)"), {"k": key}).scalar()); conn.commit()
        try: yield got
        finally:
            if got: conn.execute(text("select pg_advisory_unlock(:k)"), {"k": key}); conn.commit()

def run_billing_job(db=None):
    own = db is None; db = db or SessionLocal()
    try: return s.run_billing(db, date.today())
    finally:
        if own: db.close()

def run_daily() -> dict:
    """Billing run (activate, renew, invoice, auto-close) then overdue reminders. Idempotent, so running it twice is harmless."""
    with single_instance(LOCK_DAILY) as ok:
        if not ok: return {"skipped": "another instance is already running the daily jobs"}
        db = SessionLocal()
        try:
            billing = s.run_billing(db, date.today())
            return {"billing": billing, "reminders_queued": send_overdue_reminders(db)}
        finally: db.close()

def run_outbox(limit: int = 50) -> dict:
    db = SessionLocal()
    try: return process_outbox(db, limit)
    finally: db.close()

# ---------- scheduler ----------
class Scheduler(threading.Thread):
    def __init__(self):
        super().__init__(name="brightloop-scheduler", daemon=True)
        self.halt = threading.Event(); self.last_daily: date | None = None; self.retry_at: datetime | None = None
    def tick(self):
        run_outbox()
        now = datetime.now()
        if now.hour >= config.DAILY_JOBS_HOUR and self.last_daily != now.date() and (not self.retry_at or now >= self.retry_at):
            try:
                r = run_daily(); self.last_daily = now.date(); self.retry_at = None; log.info("daily jobs: %s", r)
            except Exception:
                self.retry_at = now + timedelta(minutes=10); raise
    def run(self):
        while not self.halt.is_set():
            try: self.tick()
            except Exception: log.exception("scheduler tick failed")
            self.halt.wait(config.OUTBOX_POLL_SECONDS)

_sched: Scheduler | None = None
def start_scheduler():
    global _sched
    if _sched and _sched.is_alive(): return _sched
    _sched = Scheduler(); _sched.start(); return _sched
def stop_scheduler():
    if _sched: _sched.halt.set()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if "--once" in sys.argv:
        print({"outbox": run_outbox(), "daily": run_daily(), "outbox_after": run_outbox()})
    else:
        Scheduler().run()
