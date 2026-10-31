"""Single place that talks to an SMTP server (or logs / records mail for dev and tests)."""
import logging, smtplib, ssl
from email.message import EmailMessage
from . import config

log = logging.getLogger("brightloop.mail")
SENT: list[dict] = []        # filled by the "memory" backend (tests)

class MailError(Exception): pass

def send_email(to: str, subject: str, body: str) -> None:
    if not to or "@" not in to: raise MailError("no valid recipient")
    if any(c in to + subject for c in "\r\n"): raise MailError("line break in header")
    backend = config.EMAIL_BACKEND
    if backend == "memory": SENT.append({"to": to, "subject": subject, "body": body}); return
    if backend == "console": log.info("EMAIL to=%s subject=%s\n%s", to, subject, body); return
    if backend != "smtp": raise MailError(f"unknown EMAIL_BACKEND {backend!r}")
    msg = EmailMessage(); msg["From"] = config.SMTP_FROM; msg["To"] = to; msg["Subject"] = subject; msg.set_content(body)
    try:
        if config.SMTP_SSL: smtp = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, timeout=20, context=ssl.create_default_context())
        else:
            smtp = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20)
            if config.SMTP_STARTTLS: smtp.starttls(context=ssl.create_default_context())
        with smtp:
            if config.SMTP_USER: smtp.login(config.SMTP_USER, config.SMTP_PASSWORD)
            smtp.send_message(msg)
    except (smtplib.SMTPException, OSError) as e:
        raise MailError(f"SMTP error: {e}") from e
