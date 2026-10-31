from uuid import UUID, uuid4
from decimal import Decimal
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from . import models as m, services as s
from .db import get_db
from .security import current_user, hash_password, make_token, password_problems, verify_password, burn_password_check, staff_or_admin, admin_only, customer_of
from .queries import summary
from .ratelimit import client_ip, limiter
from . import config

router = APIRouter()


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class Registration(Credentials):
    full_name: str = Field(min_length=1, max_length=255)


class StaffInput(Registration):
    pass


class CustomerInput(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    billing_email: EmailStr | None = None
    contact_person: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    industry: str | None = Field(default=None, max_length=100)
    is_active: bool = True


class ProductInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    product_type: str = Field(min_length=1, max_length=100)
    sales_price: Decimal = Field(ge=Decimal("0"))
    cost_price: Decimal = Field(ge=Decimal("0"))
    notes: str | None = None
    is_active: bool = True


class PlanInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    product_id: UUID | None = None
    billing_interval: Literal["DAILY", "WEEKLY", "MONTHLY", "YEARLY"]
    interval_count: int = Field(default=1, ge=1)
    minimum_quantity: int = Field(default=1, ge=1)
    price: Decimal = Field(ge=Decimal("0"))
    start_date: date = Field(default_factory=date.today)
    end_date: date | None = None
    allow_renewal: bool = True
    is_active: bool = True


class QuotationInput(BaseModel):
    customer_id: UUID
    plan_id: UUID
    quantity: int = Field(ge=1)
    valid_days: int = Field(default=30, ge=1, le=365)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))


class TransitionInput(BaseModel):
    reason: str | None = None


class AllocationInput(BaseModel):
    invoice_id: UUID
    amount: Decimal = Field(gt=Decimal("0"))


class PaymentInput(BaseModel):
    customer_id: UUID
    payment_method: Literal["CASH", "BANK_TRANSFER", "CARD", "UPI", "OTHER"]
    amount: Decimal = Field(gt=Decimal("0"))
    payment_date: date | None = None
    reference_number: str | None = None
    notes: str | None = None
    allocations: list[AllocationInput] = Field(min_length=1)


class DiscountInput(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    discount_type: Literal["FIXED", "PERCENTAGE"]
    value: Decimal = Field(gt=Decimal("0"))
    min_purchase: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    min_quantity: int = Field(default=1, ge=1)
    start_date: date
    end_date: date | None = None
    usage_limit: int | None = Field(default=None, ge=1)
    scope: Literal["PRODUCT", "SUBSCRIPTION"] = "SUBSCRIPTION"
    product_id: UUID | None = None


def public_user(user: m.User):
    roles = {"ADMIN": "Admin", "STAFF": "Staff", "CUSTOMER": "Customer"}
    return {"id": str(user.id), "email": user.email, "name": user.full_name or user.email,
            "role": roles.get(user.role, "Customer")}


@router.post("/auth/login")
def login(body: Credentials, request: Request, db: Session = Depends(get_db)):
    email = body.email.lower()
    ip = client_ip(request)
    account_key = f"login:account:{email}:{ip}"
    ip_key = f"login:ip:{ip}"
    limiter.check(account_key, config.LOGIN_MAX_FAILURES, config.LOGIN_WINDOW_SECONDS)
    limiter.check(ip_key, config.LOGIN_MAX_FAILURES_PER_IP, config.LOGIN_WINDOW_SECONDS)
    user = db.query(m.User).filter(m.User.email == email).first()
    if not user:
        burn_password_check(body.password)
        limiter.hit(account_key, config.LOGIN_WINDOW_SECONDS)
        limiter.hit(ip_key, config.LOGIN_WINDOW_SECONDS)
        raise HTTPException(401, "Email or password is incorrect")
    if not user.is_active or not verify_password(body.password, user.password_hash):
        limiter.hit(account_key, config.LOGIN_WINDOW_SECONDS)
        limiter.hit(ip_key, config.LOGIN_WINDOW_SECONDS)
        raise HTTPException(401, "Email or password is incorrect")
    limiter.reset(account_key)
    return {"access_token": make_token(user), "token_type": "bearer", "user": public_user(user)}


@router.post("/auth/register", status_code=201)
def register(body: Registration, request: Request, db: Session = Depends(get_db)):
    ip_key = f"register:{client_ip(request)}"
    limiter.check(ip_key, config.REGISTER_MAX_PER_IP, 3600)
    limiter.hit(ip_key, 3600)
    email = body.email.lower()
    if db.query(m.User).filter(m.User.email == email).first():
        raise HTTPException(409, "An account with this email already exists")
    problems = password_problems(body.password)
    if problems:
        raise HTTPException(422, "Password must contain " + ", ".join(problems))
    name = body.full_name.strip()
    if not name:
        raise HTTPException(422, "Name is required")
    user = m.User(email=email, password_hash=hash_password(body.password), full_name=name, role="CUSTOMER")
    db.add(user)
    db.flush()
    customer = m.Customer(customer_code=f"CUS-{uuid4().hex[:10].upper()}", company_name=name,
                          contact_person=name, billing_email=email, user_id=user.id)
    db.add(customer)
    db.commit()
    db.refresh(user)
    return {"access_token": make_token(user), "token_type": "bearer", "user": public_user(user)}


@router.get("/auth/me")
def get_me(user: m.User = Depends(current_user)):
    return public_user(user)


@router.get("/users")
def list_users(db: Session = Depends(get_db), user: m.User = Depends(admin_only)):
    return [public_user(item) for item in db.query(m.User).order_by(m.User.created_at.desc()).all()]


@router.post("/users/staff", status_code=201)
def create_staff(body: StaffInput, db: Session = Depends(get_db), user: m.User = Depends(admin_only)):
    email = body.email.lower()
    if db.query(m.User).filter(m.User.email == email).first():
        raise HTTPException(409, "An account with this email already exists")
    problems = password_problems(body.password)
    if problems:
        raise HTTPException(422, "Password must contain " + ", ".join(problems))
    staff = m.User(email=email, full_name=body.full_name.strip(), password_hash=hash_password(body.password), role="STAFF")
    db.add(staff)
    db.flush()
    s.audit(db, user, "user.staff_created", "user", staff.id, None, {"email": staff.email, "role": staff.role})
    db.commit()
    db.refresh(staff)
    return public_user(staff)


def customer_data(customer: m.Customer, db: Session):
    sub_count = db.query(m.Subscription).filter(m.Subscription.customer_id == customer.id).count()
    address = next((a for a in customer.addresses if a.address_type == "BILLING" and a.is_default), None)
    if not address:
        address = next((a for a in customer.addresses if a.address_type == "BILLING"), None)
    location = ", ".join(x for x in [address.city, address.state] if x) if address else "—"
    return {"id": str(customer.id), "customer_code": customer.customer_code,
            "company_name": customer.company_name, "name": customer.company_name,
            "billing_email": customer.billing_email, "email": customer.billing_email or "",
            "contact_person": customer.contact_person, "contact": customer.contact_person or "—",
            "phone": customer.phone or "—", "industry": customer.industry or "—",
            "is_active": customer.is_active, "status": "Active" if customer.is_active else "Inactive",
            "subscriptions": sub_count, "location": location,
            "joined": customer.created_at.date().isoformat() if customer.created_at else "—",
            "revenue": "—"}


@router.get("/customers")
def list_customers(db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    if user.role in ("ADMIN", "STAFF"):
        rows = db.query(m.Customer).order_by(m.Customer.created_at.desc()).all()
    else:
        own = customer_of(db, user)
        rows = [own] if own else []
    return [customer_data(row, db) for row in rows]


@router.post("/customers", status_code=201)
def create_customer(body: CustomerInput, db: Session = Depends(get_db), user: m.User = Depends(staff_or_admin)):
    from uuid import uuid4
    customer = m.Customer(customer_code=f"CUS-{uuid4().hex[:10].upper()}", **body.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer_data(customer, db)


@router.patch("/customers/{customer_id}")
def update_customer(customer_id: UUID, body: CustomerInput, db: Session = Depends(get_db), user: m.User = Depends(staff_or_admin)):
    customer = db.get(m.Customer, customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(customer, key, value)
    db.commit()
    db.refresh(customer)
    return customer_data(customer, db)


def product_data(product: m.Product):
    variants = [f"{variant.attribute_name}: {variant.attribute_value} (+₹{variant.additional_price})"
                for variant in product.variants]
    return {"id": str(product.id), "name": product.name, "type": product.product_type,
            "product_type": product.product_type, "sales_price": product.sales_price,
            "cost_price": product.cost_price, "sales": f"₹{product.sales_price:,.2f}",
            "cost": f"₹{product.cost_price:,.2f}", "variants": ", ".join(variants) or "None",
            "is_active": product.is_active, "status": "Active" if product.is_active else "Inactive"}


@router.get("/products")
def list_products(db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    return [product_data(product) for product in db.query(m.Product).order_by(m.Product.name).all()]


@router.post("/products", status_code=201)
def create_product(body: ProductInput, db: Session = Depends(get_db), user: m.User = Depends(staff_or_admin)):
    product = m.Product(**body.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product_data(product)


def plan_data(plan: m.SubscriptionPlan):
    interval = plan.billing_interval.title()
    return {"id": str(plan.id), "name": plan.name, "plan": plan.name,
            "product_id": str(plan.product_id) if plan.product_id else None,
            "product": plan.product.name if plan.product else "—",
            "billing_interval": plan.billing_interval, "billing": interval,
            "interval_count": plan.interval_count, "price": plan.price,
            "basePrice": f"₹{plan.price:,.2f}", "minimum_quantity": plan.minimum_quantity,
            "minQty": str(plan.minimum_quantity), "allow_renewal": plan.allow_renewal,
            "renewal": "Automatic" if plan.allow_renewal else "Manual",
            "is_active": plan.is_active, "status": "Active" if plan.is_active else "Draft"}


@router.get("/plans")
def list_plans(db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    return [plan_data(plan) for plan in db.query(m.SubscriptionPlan).order_by(m.SubscriptionPlan.name).all()]


@router.post("/plans", status_code=201)
def create_plan(body: PlanInput, db: Session = Depends(get_db), user: m.User = Depends(staff_or_admin)):
    values = body.model_dump()
    values["billing_interval"] = values["billing_interval"].upper()
    if values["product_id"] and not db.get(m.Product, values["product_id"]):
        raise HTTPException(404, "Product not found")
    if values["end_date"] and values["end_date"] <= values["start_date"]:
        raise HTTPException(422, "End date must be after start date")
    plan = m.SubscriptionPlan(**values)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan_data(plan)


def quotation_data(quote: m.Quotation, db: Session):
    line = quote.lines[0] if quote.lines else None
    plan = db.get(m.SubscriptionPlan, line.plan_id) if line else None
    return {"id": str(quote.id), "quotation_number": quote.quotation_number,
            "number": quote.quotation_number, "customer_id": str(quote.customer_id),
            "customer": quote.customer.company_name if quote.customer else "—",
            "plan": plan.name if plan else "—",
            "product": line.product_name if line else "—",
            "quantity": line.quantity if line else 0,
            "lines": f"{line.product_name} × {line.quantity}" if line else "—",
            "issue_date": quote.issue_date, "valid_until": quote.valid_until,
            "validFor": f"{(quote.valid_until - quote.issue_date).days} days",
            "grand_total": quote.grand_total, "status": quote.status.title()}


@router.get("/quotations")
def list_quotations(db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    query = db.query(m.Quotation)
    if user.role == "CUSTOMER":
        own = customer_of(db, user)
        query = query.filter(m.Quotation.customer_id == own.id) if own else query.filter(False)
    return [quotation_data(q, db) for q in query.order_by(m.Quotation.created_at.desc()).all()]


@router.post("/quotations", status_code=201)
def create_quotation(body: QuotationInput, db: Session = Depends(get_db), user: m.User = Depends(staff_or_admin)):
    customer = db.get(m.Customer, body.customer_id)
    plan = db.get(m.SubscriptionPlan, body.plan_id)
    if not customer or not plan:
        raise HTTPException(404, "Customer or plan not found")
    product = db.get(m.Product, plan.product_id) if plan.product_id else None
    if not product:
        raise HTTPException(422, "The selected plan must be linked to a product before quoting")
    on = date.today()
    if not plan.is_active or on < plan.start_date or (plan.end_date and on > plan.end_date):
        raise HTTPException(409, "The selected plan is not currently available")
    quote = m.Quotation(quotation_number=s.next_number(db, "QUO"), customer_id=customer.id,
                        issue_date=on, valid_until=on + timedelta(days=body.valid_days),
                        subtotal=0, discount_total=0, tax_total=0, grand_total=0,
                        status="DRAFT", created_by=user.id)
    quote.lines.append(s.price_quotation_line(db, plan, product, None, body.quantity, plan.price,
                                               body.discount_amount, on, customer))
    s.recompute_quotation_totals(quote)
    db.add(quote)
    db.commit()
    db.refresh(quote)
    return quotation_data(quote, db)


@router.post("/quotations/{quotation_id}/send")
def send_quotation(quotation_id: UUID, db: Session = Depends(get_db), user: m.User = Depends(staff_or_admin)):
    quote = db.get(m.Quotation, quotation_id)
    if not quote:
        raise HTTPException(404, "Quotation not found")
    if quote.status != "DRAFT":
        raise HTTPException(409, "Only draft quotations can be sent")
    quote.status = "SENT"
    db.commit()
    db.refresh(quote)
    return quotation_data(quote, db)


@router.post("/quotations/{quotation_id}/accept")
def accept_quotation(quotation_id: UUID, db: Session = Depends(get_db), user: m.User = Depends(staff_or_admin)):
    subscription = s.convert_quotation(db, quotation_id, user)
    db.commit()
    return {"id": str(subscription.id), "subscription_number": subscription.subscription_number,
            "status": subscription.status.title()}


def subscription_data(sub: m.Subscription):
    total = sum((line.line_total for line in sub.lines), Decimal("0"))
    return {"id": str(sub.id), "subscription_number": sub.subscription_number,
            "number": sub.subscription_number, "customer_id": str(sub.customer_id),
            "customer": sub.customer.company_name if sub.customer else "—",
            "plan": sub.plan.name if sub.plan else "—", "start_date": sub.start_date,
            "start": sub.start_date.isoformat(), "expiry_date": sub.expiry_date,
            "expiry": sub.expiry_date.isoformat() if sub.expiry_date else "—",
            "payment_terms": sub.payment_terms or "—", "terms": sub.payment_terms or "—",
            "amount": f"₹{total:,.2f}", "status": sub.status.title()}


@router.get("/subscriptions")
def list_subscriptions(db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    query = db.query(m.Subscription)
    if user.role == "CUSTOMER":
        own = customer_of(db, user)
        query = query.filter(m.Subscription.customer_id == own.id) if own else query.filter(False)
    return [subscription_data(sub) for sub in query.order_by(m.Subscription.created_at.desc()).all()]


@router.post("/subscriptions/{subscription_id}/{action}")
def subscription_transition(subscription_id: UUID, action: str, body: TransitionInput | None = None,
                            db: Session = Depends(get_db), user: m.User = Depends(staff_or_admin)):
    actions = {"activate": "ACTIVE", "pause": "PAUSED", "resume": "ACTIVE", "close": "CLOSED"}
    if action not in actions:
        raise HTTPException(404, "Unknown subscription action")
    sub = db.get(m.Subscription, subscription_id)
    if not sub:
        raise HTTPException(404, "Subscription not found")
    s.set_status(db, sub, actions[action], user, body.reason if body else None)
    db.commit()
    db.refresh(sub)
    return subscription_data(sub)


def invoice_data(invoice: m.Invoice):
    return {"id": str(invoice.id), "invoice_number": invoice.invoice_number,
            "invoiceNumber": invoice.invoice_number,
            "customer_id": str(invoice.customer_id),
            "customer": invoice.customer.company_name if invoice.customer else "—",
            "subscription": invoice.subscription.subscription_number if invoice.subscription else "—",
            "issue_date": invoice.issue_date, "date": invoice.issue_date.isoformat(),
            "due_date": invoice.due_date, "due": invoice.due_date.isoformat(),
            "total_amount": invoice.total_amount, "total": invoice.total_amount,
            "amount_paid": invoice.amount_paid, "balance_due": invoice.balance_due,
            "status": s.derive_status(invoice).title()}


@router.get("/invoices")
def list_invoices(db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    query = db.query(m.Invoice)
    if user.role == "CUSTOMER":
        own = customer_of(db, user)
        query = query.filter(m.Invoice.customer_id == own.id) if own else query.filter(False)
    return [invoice_data(invoice) for invoice in query.order_by(m.Invoice.issue_date.desc()).all()]


@router.post("/billing/run")
def run_billing(db: Session = Depends(get_db), user: m.User = Depends(staff_or_admin)):
    result = s.run_billing(db, date.today(), actor=user)
    return result


@router.post("/invoices/{invoice_id}/confirm")
def confirm_invoice(invoice_id: UUID, db: Session = Depends(get_db), user: m.User = Depends(staff_or_admin)):
    invoice = db.get(m.Invoice, invoice_id)
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    s.confirm_invoice(db, invoice, user)
    db.commit()
    db.refresh(invoice)
    return invoice_data(invoice)


@router.post("/invoices/{invoice_id}/send")
def send_invoice(invoice_id: UUID, db: Session = Depends(get_db), user: m.User = Depends(staff_or_admin)):
    invoice = db.get(m.Invoice, invoice_id)
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    s.send_invoice(db, invoice, user)
    db.commit()
    return invoice_data(invoice)


@router.get("/payments")
def list_payments(db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    query = db.query(m.Payment)
    if user.role == "CUSTOMER":
        own = customer_of(db, user)
        query = query.filter(m.Payment.customer_id == own.id) if own else query.filter(False)
    result = []
    for payment in query.order_by(m.Payment.payment_date.desc()).all():
        allocation = payment.allocations[0] if payment.allocations else None
        result.append({"id": str(payment.id), "payment_number": payment.payment_number,
                       "reference": payment.payment_number, "customer_id": str(payment.customer_id),
                       "customer": payment.customer.company_name if payment.customer else "—",
                       "invoice_id": str(allocation.invoice_id) if allocation else None,
                       "invoice": allocation.invoice.invoice_number if allocation else "Unallocated",
                       "payment_method": payment.payment_method, "method": payment.payment_method.replace("_", " ").title(),
                       "amount": payment.amount, "date": payment.payment_date.date().isoformat(),
                       "notes": payment.notes or "", "note": payment.notes or "", "status": payment.status})
    return result


@router.post("/payments", status_code=201)
def record_payment(body: PaymentInput, db: Session = Depends(get_db), user: m.User = Depends(staff_or_admin)):
    payment_date = datetime.combine(body.payment_date, datetime.min.time(), tzinfo=timezone.utc) if body.payment_date else None
    payment = s.record_payment(db, user, body.customer_id, body.payment_method, body.amount,
                               payment_date, body.reference_number, body.notes,
                               [allocation.model_dump() for allocation in body.allocations])
    db.commit()
    db.refresh(payment)
    return {"id": str(payment.id), "payment_number": payment.payment_number,
            "amount": payment.amount, "status": payment.status}


@router.get("/reports/dashboard")
def dashboard_report(date_from: date | None = None, date_to: date | None = None,
                     customer_id: UUID | None = None, plan_id: UUID | None = None,
                     db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    if user.role == "CUSTOMER":
        own = customer_of(db, user)
        customer_id = own.id if own else UUID(int=0)
    return summary(db, date.today(), date_from, date_to, customer_id, plan_id)


def discount_data(discount: m.Discount):
    now = datetime.now(timezone.utc)
    if not discount.is_active or (discount.usage_limit is not None and discount.usage_count >= discount.usage_limit):
        status = "Inactive"
    elif discount.start_date > now:
        status = "Draft"
    elif discount.end_date and discount.end_date < now:
        status = "Expired"
    else:
        status = "Active"
    products = [row.product.name for row in discount.products if row.product]
    return {"id": str(discount.id), "code": discount.code or "", "name": discount.name,
            "discount_type": discount.discount_type, "type": discount.discount_type.title(),
            "value": discount.value, "formatted_value": f"{discount.value}%" if discount.discount_type == "PERCENTAGE" else f"₹{discount.value:,.2f}",
            "min_purchase": discount.min_purchase, "min_quantity": discount.min_quantity,
            "minimum": f"₹{discount.min_purchase:,.2f}" if discount.min_purchase else f"{discount.min_quantity} units",
            "start_date": discount.start_date.date(), "end_date": discount.end_date.date() if discount.end_date else None,
            "valid": f"{discount.start_date:%d %b %Y} - {discount.end_date:%d %b %Y}" if discount.end_date else f"From {discount.start_date:%d %b %Y}",
            "usage_count": discount.usage_count, "usage_limit": discount.usage_limit,
            "used": f"{discount.usage_count} / {discount.usage_limit}" if discount.usage_limit else str(discount.usage_count),
            "scope": discount.scope, "applies_to": ", ".join(products) or "All subscriptions",
            "status": status}


@router.get("/discounts")
def list_discounts(db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    return [discount_data(item) for item in db.query(m.Discount).order_by(m.Discount.created_at.desc()).all()]


@router.post("/discounts", status_code=201)
def create_discount(body: DiscountInput, db: Session = Depends(get_db), user: m.User = Depends(staff_or_admin)):
    if body.discount_type == "PERCENTAGE" and body.value > 100:
        raise HTTPException(422, "Percentage discounts cannot exceed 100")
    if body.end_date and body.end_date < body.start_date:
        raise HTTPException(422, "End date must be on or after start date")
    if body.scope == "PRODUCT" and not body.product_id:
        raise HTTPException(422, "Choose a product for product-specific discounts")
    product = db.get(m.Product, body.product_id) if body.product_id else None
    if body.product_id and not product:
        raise HTTPException(404, "Product not found")
    values = body.model_dump(exclude={"product_id"})
    values["start_date"] = datetime.combine(body.start_date, datetime.min.time(), tzinfo=timezone.utc)
    values["end_date"] = datetime.combine(body.end_date, datetime.max.time(), tzinfo=timezone.utc) if body.end_date else None
    values["created_by"] = user.id
    discount = m.Discount(**values)
    if product:
        discount.products.append(m.DiscountProduct(product_id=product.id))
    db.add(discount)
    db.commit()
    db.refresh(discount)
    return discount_data(discount)
