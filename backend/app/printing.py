"""Printable invoice (self-contained HTML, no scripts). The browser's Print / Save-as-PDF does the rest."""
from html import escape as e
from decimal import Decimal

COMPANY = "Brightloop Software"

def money(x) -> str: return f"₹{Decimal(x or 0):,.2f}"

def invoice_html(inv, status_label: str) -> str:
    c = inv.customer
    addr = next((a for a in c.addresses if a.address_type == "BILLING" and a.is_default), None) or next((a for a in c.addresses if a.address_type == "BILLING"), None)
    addr_lines = "<br>".join(e(x) for x in ([addr.address_line1, addr.address_line2, ", ".join(filter(None, [addr.city, addr.state, addr.postal_code])), addr.country] if addr else []) if x)
    rows = "".join(
        f"<tr><td>{e(l.description)}</td><td class=n>{l.quantity}</td><td class=n>{money(l.unit_price)}</td><td class=n>{money(l.discount_amount)}</td>"
        f"<td class=n>{Decimal(l.tax_rate_snapshot):g}%</td><td class=n>{money(l.tax_amount)}</td><td class=n>{money(l.line_total)}</td></tr>" for l in inv.lines)
    period = f"{inv.billing_period_start:%d %b %Y} – {inv.billing_period_end:%d %b %Y}" if inv.billing_period_start and inv.billing_period_end else "—"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Invoice {e(inv.invoice_number)}</title>
<style>body{{font:14px/1.45 system-ui,Segoe UI,Arial,sans-serif;color:#1a1a1a;max-width:900px;margin:24px auto;padding:0 16px}}
h1{{margin:0;font-size:22px}}.top{{display:flex;justify-content:space-between;gap:24px;margin-bottom:24px}}.muted{{color:#666}}
table{{width:100%;border-collapse:collapse;margin-top:16px}}th,td{{border-bottom:1px solid #ddd;padding:8px;text-align:left;vertical-align:top}}
th{{background:#f5f5f5;font-size:12px;text-transform:uppercase}}.n{{text-align:right;white-space:nowrap}}
.tot{{margin-left:auto;width:320px;margin-top:16px}}.tot div{{display:flex;justify-content:space-between;padding:4px 0}}.tot .g{{font-weight:700;border-top:2px solid #1a1a1a}}
.badge{{display:inline-block;padding:2px 10px;border:1px solid #1a1a1a;border-radius:12px;font-size:12px}}@media print{{body{{margin:0}}}}</style></head><body>
<div class="top"><div><h1>{e(COMPANY)}</h1><div class="muted">Invoice</div></div>
<div style="text-align:right"><h1>{e(inv.invoice_number)}</h1><span class="badge">{e(status_label)}</span></div></div>
<div class="top"><div><strong>Bill to</strong><br>{e(c.company_name)}<br>{addr_lines}{('<br>Tax ID: ' + e(c.tax_identifier)) if c.tax_identifier else ''}</div>
<div style="text-align:right">Subscription: {e(inv.subscription.subscription_number)}<br>Issued: {inv.issue_date:%d %b %Y}<br>Due: {inv.due_date:%d %b %Y}<br>Period: {period}</div></div>
<table><thead><tr><th>Description</th><th class=n>Qty</th><th class=n>Unit price</th><th class=n>Discount</th><th class=n>Tax %</th><th class=n>Tax</th><th class=n>Amount</th></tr></thead><tbody>{rows}</tbody></table>
<div class="tot"><div><span>Subtotal</span><span>{money(inv.subtotal)}</span></div><div><span>Discount</span><span>−{money(inv.discount_total)}</span></div>
<div><span>Tax</span><span>{money(inv.tax_total)}</span></div><div class="g"><span>Total</span><span>{money(inv.total_amount)}</span></div>
<div><span>Paid</span><span>{money(inv.amount_paid)}</span></div><div class="g"><span>Balance due</span><span>{money(inv.balance_due)}</span></div></div>
</body></html>"""
