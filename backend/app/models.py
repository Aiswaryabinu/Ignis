"""SQLAlchemy 2.0 models for the Brightloop schema (see docs/DATABASE.md)."""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import (String, Text, Boolean, Integer, Numeric, Date, DateTime, ForeignKey,
                        UniqueConstraint, CheckConstraint, Index, func, text)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

def uid(): return uuid.uuid4()
def pk(): return mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
def fk(target, nullable=False, ondelete="RESTRICT", unique=False):
    return mapped_column(UUID(as_uuid=True), ForeignKey(target, ondelete=ondelete), nullable=nullable, unique=unique)
def ts(nullable=False):
    return mapped_column(DateTime(timezone=True), nullable=nullable, server_default=None if nullable else func.now())
def money(default=None, nullable=False):
    return mapped_column(Numeric(12, 2), nullable=nullable, default=default)

NUM = lambda: Numeric(12, 2)

# ---------------- Authentication ----------------
class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = pk()
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))  # extension: display name
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    created_at: Mapped[datetime] = ts()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (CheckConstraint("role in ('ADMIN','STAFF','CUSTOMER')", name="ck_users_role"),)

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id: Mapped[uuid.UUID] = pk()
    user_id = fk("users.id", ondelete="CASCADE")
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = ts(True)
    created_at: Mapped[datetime] = ts()

class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"
    id: Mapped[uuid.UUID] = pk()
    user_id = fk("users.id", ondelete="CASCADE")
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_at: Mapped[Optional[datetime]] = ts(True)
    created_at: Mapped[datetime] = ts()

# ---------------- Customers ----------------
class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[uuid.UUID] = pk()
    user_id = fk("users.id", nullable=True, ondelete="SET NULL", unique=True)
    customer_code: Mapped[str] = mapped_column(String(50), unique=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_person: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(30))
    billing_email: Mapped[Optional[str]] = mapped_column(String(255))
    tax_identifier: Mapped[Optional[str]] = mapped_column(String(100))
    industry: Mapped[Optional[str]] = mapped_column(String(100))  # extension used by UI
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = ts()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    addresses = relationship("CustomerAddress", cascade="all, delete-orphan")

class CustomerAddress(Base):
    __tablename__ = "customer_addresses"
    id: Mapped[uuid.UUID] = pk()
    customer_id = fk("customers.id", ondelete="CASCADE")
    address_type: Mapped[str] = mapped_column(String(20), nullable=False)
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[Optional[str]] = mapped_column(String(100))
    postal_code: Mapped[Optional[str]] = mapped_column(String(20))
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    created_at: Mapped[datetime] = ts()
    __table_args__ = (CheckConstraint("address_type in ('BILLING','SHIPPING')", name="ck_addr_type"),)

# ---------------- Products ----------------
class Product(Base):
    __tablename__ = "products"
    id: Mapped[uuid.UUID] = pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_type: Mapped[str] = mapped_column(String(100), nullable=False)
    sales_price: Mapped[Decimal] = money()
    cost_price: Mapped[Decimal] = money()
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = ts()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    variants = relationship("ProductVariant", cascade="all, delete-orphan", order_by="ProductVariant.created_at")
    __table_args__ = (CheckConstraint("sales_price >= 0 AND cost_price >= 0", name="ck_product_prices"),)

class ProductVariant(Base):
    __tablename__ = "product_variants"
    id: Mapped[uuid.UUID] = pk()
    product_id = fk("products.id", ondelete="CASCADE")
    attribute_name: Mapped[str] = mapped_column(String(100), nullable=False)
    attribute_value: Mapped[str] = mapped_column(String(100), nullable=False)
    additional_price: Mapped[Decimal] = mapped_column(NUM(), default=0, server_default=text("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = ts()
    __table_args__ = (UniqueConstraint("product_id", "attribute_name", "attribute_value"),)

# ---------------- Plans ----------------
class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    id: Mapped[uuid.UUID] = pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    product_id = fk("products.id", nullable=True, ondelete="SET NULL")  # extension: UI lists a product per plan
    billing_interval: Mapped[str] = mapped_column(String(20), nullable=False)
    interval_count: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    minimum_quantity: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    price: Mapped[Decimal] = money()
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    auto_close: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    allow_early_close: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    allow_pause: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    allow_renewal: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = ts()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    product = relationship("Product")
    __table_args__ = (
        CheckConstraint("billing_interval in ('DAILY','WEEKLY','MONTHLY','YEARLY')", name="ck_plan_interval"),
        CheckConstraint("minimum_quantity >= 1 AND interval_count >= 1 AND price >= 0", name="ck_plan_values"),
    )

# ---------------- Taxes ----------------
class Tax(Base):
    __tablename__ = "taxes"
    id: Mapped[uuid.UUID] = pk()
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    tax_type: Mapped[str] = mapped_column(String(20), nullable=False)
    is_inclusive: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_until: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = ts()
    __table_args__ = (CheckConstraint("tax_type in ('PERCENTAGE','FIXED')", name="ck_tax_type"),
                      CheckConstraint("rate >= 0", name="ck_tax_rate"))

class TaxRule(Base):
    __tablename__ = "tax_rules"
    id: Mapped[uuid.UUID] = pk()
    tax_id = fk("taxes.id", ondelete="CASCADE")
    product_id = fk("products.id", nullable=True, ondelete="CASCADE")
    country: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(100))
    priority: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    tax = relationship("Tax")

# ---------------- Quotations ----------------
class QuotationTemplate(Base):
    __tablename__ = "quotation_templates"
    id: Mapped[uuid.UUID] = pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    validity_days: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_by = fk("users.id")
    created_at: Mapped[datetime] = ts()
    lines = relationship("QuotationTemplateLine", cascade="all, delete-orphan")
    __table_args__ = (CheckConstraint("validity_days > 0", name="ck_qt_validity"),)

class QuotationTemplateLine(Base):
    __tablename__ = "quotation_template_lines"
    id: Mapped[uuid.UUID] = pk()
    template_id = fk("quotation_templates.id", ondelete="CASCADE")
    product_id = fk("products.id")
    variant_id = fk("product_variants.id", nullable=True)
    plan_id = fk("subscription_plans.id")
    default_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    default_unit_price: Mapped[Decimal] = money()
    product = relationship("Product"); plan = relationship("SubscriptionPlan")
    __table_args__ = (CheckConstraint("default_quantity > 0", name="ck_qtl_qty"),)

class Quotation(Base):
    __tablename__ = "quotations"
    id: Mapped[uuid.UUID] = pk()
    quotation_number: Mapped[str] = mapped_column(String(50), unique=True)
    customer_id = fk("customers.id")
    template_id = fk("quotation_templates.id", nullable=True, ondelete="SET NULL")
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)
    subtotal: Mapped[Decimal] = money()
    discount_total: Mapped[Decimal] = mapped_column(NUM(), default=0, server_default=text("0"))
    tax_total: Mapped[Decimal] = mapped_column(NUM(), default=0, server_default=text("0"))
    grand_total: Mapped[Decimal] = money()
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    created_by = fk("users.id")
    accepted_at: Mapped[Optional[datetime]] = ts(True)
    created_at: Mapped[datetime] = ts()
    customer = relationship("Customer")
    lines = relationship("QuotationLine", cascade="all, delete-orphan")
    __table_args__ = (CheckConstraint("status in ('DRAFT','SENT','ACCEPTED','EXPIRED','REJECTED')", name="ck_quote_status"),
                      Index("idx_quotations_customer", "customer_id"), Index("idx_quotations_status", "status"))

class QuotationLine(Base):
    __tablename__ = "quotation_lines"
    id: Mapped[uuid.UUID] = pk()
    quotation_id = fk("quotations.id", ondelete="CASCADE")
    product_id = fk("products.id")
    variant_id = fk("product_variants.id", nullable=True)
    plan_id = fk("subscription_plans.id")
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    variant_name: Mapped[Optional[str]] = mapped_column(String(255))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = money()
    discount_amount: Mapped[Decimal] = mapped_column(NUM(), default=0, server_default=text("0"))
    tax_rate_snapshot: Mapped[Decimal] = mapped_column(Numeric(7, 4), default=0, server_default=text("0"))
    tax_amount: Mapped[Decimal] = mapped_column(NUM(), default=0, server_default=text("0"))
    line_total: Mapped[Decimal] = money()
    __table_args__ = (CheckConstraint("quantity > 0 AND discount_amount >= 0 AND tax_amount >= 0", name="ck_ql_values"),)

# ---------------- Subscriptions ----------------
class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[uuid.UUID] = pk()
    subscription_number: Mapped[str] = mapped_column(String(50), unique=True)
    customer_id = fk("customers.id")
    plan_id = fk("subscription_plans.id")
    quotation_id = fk("quotations.id", nullable=True, unique=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date)
    next_billing_date: Mapped[Optional[date]] = mapped_column(Date)
    billing_anchor_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    payment_terms: Mapped[Optional[str]] = mapped_column(String(100))
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    paused_at: Mapped[Optional[datetime]] = ts(True)
    closed_at: Mapped[Optional[datetime]] = ts(True)
    created_by = fk("users.id")
    created_at: Mapped[datetime] = ts()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    customer = relationship("Customer"); plan = relationship("SubscriptionPlan")
    lines = relationship("SubscriptionLine", cascade="all, delete-orphan")
    __table_args__ = (
        CheckConstraint("status in ('DRAFT','QUOTATION','CONFIRMED','ACTIVE','PAUSED','CLOSED')", name="ck_sub_status"),
        CheckConstraint("expiry_date IS NULL OR expiry_date > start_date", name="ck_sub_dates"),
        Index("idx_subscriptions_customer", "customer_id"), Index("idx_subscriptions_status", "status"),
        Index("idx_subscriptions_next_billing", "next_billing_date"), Index("idx_subscriptions_plan", "plan_id"))

class SubscriptionLine(Base):
    __tablename__ = "subscription_lines"
    id: Mapped[uuid.UUID] = pk()
    subscription_id = fk("subscriptions.id", ondelete="CASCADE")
    product_id = fk("products.id")
    variant_id = fk("product_variants.id", nullable=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    variant_name: Mapped[Optional[str]] = mapped_column(String(255))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = money()
    tax_id = fk("taxes.id", nullable=True)
    tax_rate_snapshot: Mapped[Decimal] = mapped_column(Numeric(7, 4), default=0, server_default=text("0"))
    discount_amount: Mapped[Decimal] = mapped_column(NUM(), default=0, server_default=text("0"))
    line_total: Mapped[Decimal] = money()
    __table_args__ = (CheckConstraint("quantity > 0 AND discount_amount >= 0", name="ck_sl_values"),)

class SubscriptionStatusHistory(Base):
    __tablename__ = "subscription_status_history"
    id: Mapped[uuid.UUID] = pk()
    subscription_id = fk("subscriptions.id", ondelete="CASCADE")
    old_status: Mapped[Optional[str]] = mapped_column(String(20))
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_by = fk("users.id", nullable=True, ondelete="SET NULL")
    reason: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = ts()

class SubscriptionRenewal(Base):
    __tablename__ = "subscription_renewals"
    id: Mapped[uuid.UUID] = pk()
    subscription_id = fk("subscriptions.id", ondelete="CASCADE")
    previous_expiry_date: Mapped[Optional[date]] = mapped_column(Date)
    new_expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    renewal_date: Mapped[date] = mapped_column(Date, nullable=False)
    renewed_by = fk("users.id", nullable=True, ondelete="SET NULL")
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = ts()
    __table_args__ = (CheckConstraint("status in ('PENDING','COMPLETED','FAILED')", name="ck_renewal_status"),)

# ---------------- Discounts ----------------
class Discount(Base):
    __tablename__ = "discounts"
    id: Mapped[uuid.UUID] = pk()
    code: Mapped[Optional[str]] = mapped_column(String(50), unique=True)  # extension: UI shows a code
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[Decimal] = money()
    min_purchase: Mapped[Decimal] = mapped_column(NUM(), default=0, server_default=text("0"))
    min_quantity: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    usage_limit: Mapped[Optional[int]] = mapped_column(Integer)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_by = fk("users.id")
    created_at: Mapped[datetime] = ts()
    products = relationship("DiscountProduct", cascade="all, delete-orphan")
    __table_args__ = (
        CheckConstraint("discount_type in ('FIXED','PERCENTAGE')", name="ck_disc_type"),
        CheckConstraint("scope in ('PRODUCT','SUBSCRIPTION')", name="ck_disc_scope"),
        CheckConstraint("value >= 0 AND (discount_type <> 'PERCENTAGE' OR value <= 100)", name="ck_disc_value"),
        CheckConstraint("usage_limit IS NULL OR usage_count <= usage_limit", name="ck_disc_usage"))

class DiscountProduct(Base):
    __tablename__ = "discount_products"
    id: Mapped[uuid.UUID] = pk()
    discount_id = fk("discounts.id", ondelete="CASCADE")
    product_id = fk("products.id", ondelete="CASCADE")
    __table_args__ = (UniqueConstraint("discount_id", "product_id"),)

# ---------------- Invoices ----------------
class Invoice(Base):
    __tablename__ = "invoices"
    id: Mapped[uuid.UUID] = pk()
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True)
    customer_id = fk("customers.id")
    subscription_id = fk("subscriptions.id")
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    billing_period_start: Mapped[Optional[date]] = mapped_column(Date)
    billing_period_end: Mapped[Optional[date]] = mapped_column(Date)
    subtotal: Mapped[Decimal] = money()
    discount_total: Mapped[Decimal] = mapped_column(NUM(), default=0, server_default=text("0"))
    tax_total: Mapped[Decimal] = mapped_column(NUM(), default=0, server_default=text("0"))
    total_amount: Mapped[Decimal] = money()
    amount_paid: Mapped[Decimal] = mapped_column(NUM(), default=0, server_default=text("0"))
    balance_due: Mapped[Decimal] = money()
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    pdf_url: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = ts()
    customer = relationship("Customer"); subscription = relationship("Subscription")
    lines = relationship("InvoiceLine", cascade="all, delete-orphan")
    __table_args__ = (
        CheckConstraint("status in ('DRAFT','CONFIRMED','PARTIALLY_PAID','PAID','CANCELLED','VOID')", name="ck_inv_status"),
        CheckConstraint("total_amount >= 0 AND amount_paid >= 0 AND balance_due >= 0", name="ck_inv_amounts"),
        UniqueConstraint("subscription_id", "billing_period_start", "billing_period_end", name="uq_invoice_period"),
        Index("idx_invoices_customer", "customer_id"), Index("idx_invoices_status", "status"),
        Index("idx_invoices_due_date", "due_date"), Index("idx_invoices_subscription", "subscription_id"))

class InvoiceLine(Base):
    __tablename__ = "invoice_lines"
    id: Mapped[uuid.UUID] = pk()
    invoice_id = fk("invoices.id", ondelete="CASCADE")
    product_id = fk("products.id", nullable=True)
    variant_id = fk("product_variants.id", nullable=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = money()
    discount_amount: Mapped[Decimal] = mapped_column(NUM(), default=0, server_default=text("0"))
    taxable_amount: Mapped[Decimal] = money()
    tax_rate_snapshot: Mapped[Decimal] = mapped_column(Numeric(7, 4), default=0, server_default=text("0"))
    tax_amount: Mapped[Decimal] = mapped_column(NUM(), default=0, server_default=text("0"))
    line_total: Mapped[Decimal] = money()
    __table_args__ = (CheckConstraint("quantity > 0 AND discount_amount >= 0 AND tax_amount >= 0", name="ck_il_values"),)

class DiscountUsage(Base):
    __tablename__ = "discount_usages"
    id: Mapped[uuid.UUID] = pk()
    discount_id = fk("discounts.id")
    customer_id = fk("customers.id")
    subscription_id = fk("subscriptions.id", nullable=True)
    invoice_id = fk("invoices.id")
    discount_amount: Mapped[Decimal] = money()
    used_at: Mapped[datetime] = ts()

# ---------------- Billing ----------------
class BillingJob(Base):
    __tablename__ = "billing_jobs"
    id: Mapped[uuid.UUID] = pk()
    subscription_id = fk("subscriptions.id")
    billing_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    billing_period_end: Mapped[date] = mapped_column(Date, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = ts()
    completed_at: Mapped[Optional[datetime]] = ts(True)
    __table_args__ = (
        CheckConstraint("status in ('PENDING','PROCESSING','COMPLETED','FAILED')", name="ck_job_status"),
        UniqueConstraint("subscription_id", "billing_period_start", "billing_period_end", name="uq_job_period"),
        Index("idx_billing_jobs_status", "status"))

class BillingPeriod(Base):
    __tablename__ = "billing_periods"
    id: Mapped[uuid.UUID] = pk()
    subscription_id = fk("subscriptions.id")
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    billing_date: Mapped[date] = mapped_column(Date, nullable=False)
    invoice_id = fk("invoices.id", nullable=True, ondelete="SET NULL")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = ts()
    __table_args__ = (
        CheckConstraint("status in ('PENDING','BILLED','SKIPPED')", name="ck_bp_status"),
        UniqueConstraint("subscription_id", "period_start", "period_end", name="uq_billing_period"))

# ---------------- Payments ----------------
class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[uuid.UUID] = pk()
    payment_number: Mapped[str] = mapped_column(String(50), unique=True)
    customer_id = fk("customers.id")
    payment_method: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[Decimal] = money()
    payment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reference_number: Mapped[Optional[str]] = mapped_column(String(255))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="RECORDED")
    recorded_by = fk("users.id")
    created_at: Mapped[datetime] = ts()
    customer = relationship("Customer")
    allocations = relationship("PaymentAllocation", cascade="all, delete-orphan")
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_pay_amount"),
        CheckConstraint("payment_method in ('CASH','BANK_TRANSFER','CARD','UPI','OTHER')", name="ck_pay_method"),
        CheckConstraint("status in ('RECORDED','REVERSED')", name="ck_pay_status"),
        Index("idx_payments_customer", "customer_id"))

class PaymentAllocation(Base):
    __tablename__ = "payment_allocations"
    id: Mapped[uuid.UUID] = pk()
    payment_id = fk("payments.id", ondelete="CASCADE")
    invoice_id = fk("invoices.id")
    allocated_amount: Mapped[Decimal] = money()
    created_at: Mapped[datetime] = ts()
    invoice = relationship("Invoice")
    __table_args__ = (CheckConstraint("allocated_amount > 0", name="ck_alloc_amount"),
                      Index("idx_payment_allocations_invoice", "invoice_id"))

# ---------------- Notifications / outbox ----------------
class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[uuid.UUID] = pk()
    user_id = fk("users.id", ondelete="CASCADE")
    notification_type: Mapped[str] = mapped_column(String(100), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    related_entity_type: Mapped[Optional[str]] = mapped_column(String(50))
    related_entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    sent_at: Mapped[Optional[datetime]] = ts(True)
    created_at: Mapped[datetime] = ts()
    __table_args__ = (CheckConstraint("status in ('PENDING','SENT','FAILED')", name="ck_notif_status"),)

class NotificationTemplate(Base):
    __tablename__ = "notification_templates"
    id: Mapped[uuid.UUID] = pk()
    event_type: Mapped[str] = mapped_column(String(100), unique=True)
    subject_template: Mapped[str] = mapped_column(String(255), nullable=False)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = ts()

class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    id: Mapped[uuid.UUID] = pk()
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = ts()
    published_at: Mapped[Optional[datetime]] = ts(True)
    __table_args__ = (CheckConstraint("status in ('PENDING','PUBLISHED','FAILED')", name="ck_outbox_status"),)

# ---------------- Audit ----------------
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[uuid.UUID] = pk()
    actor_user_id = fk("users.id", nullable=True, ondelete="SET NULL")
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    old_values: Mapped[Optional[dict]] = mapped_column(JSONB)
    new_values: Mapped[Optional[dict]] = mapped_column(JSONB)
    ip_address: Mapped[Optional[str]] = mapped_column(INET)
    created_at: Mapped[datetime] = ts()

# ---------------- Query-performance indexes (Alembic 0002) ----------------
Index("idx_invoices_issue_date", Invoice.__table__.c.issue_date)
Index("idx_invoices_status_due", Invoice.__table__.c.status, Invoice.__table__.c.due_date)
Index("idx_invoices_customer_status", Invoice.__table__.c.customer_id, Invoice.__table__.c.status)
Index("idx_invoices_created", Invoice.__table__.c.created_at)
Index("idx_invoice_lines_invoice", InvoiceLine.__table__.c.invoice_id)
Index("idx_subscription_lines_sub", SubscriptionLine.__table__.c.subscription_id)
Index("idx_quotation_lines_quotation", QuotationLine.__table__.c.quotation_id)
Index("idx_subscriptions_status_next", Subscription.__table__.c.status, Subscription.__table__.c.next_billing_date)
Index("idx_subscriptions_created", Subscription.__table__.c.created_at)
Index("idx_subscriptions_expiry", Subscription.__table__.c.expiry_date)
Index("idx_payments_date", Payment.__table__.c.payment_date)
Index("idx_payments_status_date", Payment.__table__.c.status, Payment.__table__.c.payment_date)
Index("idx_payments_created", Payment.__table__.c.created_at)
Index("idx_quotations_created", Quotation.__table__.c.created_at)
Index("idx_customers_created", Customer.__table__.c.created_at)
Index("idx_audit_logs_created", AuditLog.__table__.c.created_at)
Index("idx_notifications_user_created", Notification.__table__.c.user_id, Notification.__table__.c.created_at)
Index("idx_outbox_status_created", OutboxEvent.__table__.c.status, OutboxEvent.__table__.c.created_at)
Index("idx_outbox_type_aggregate", OutboxEvent.__table__.c.event_type, OutboxEvent.__table__.c.aggregate_id)
Index("idx_billing_jobs_created", BillingJob.__table__.c.created_at)

# step 4: one default address per customer and type (enforced in the database), plus lookups used by the admin screens
Index("uq_customer_default_address", CustomerAddress.__table__.c.customer_id, CustomerAddress.__table__.c.address_type, unique=True, postgresql_where=text("is_default"))
Index("idx_customer_addresses_customer", CustomerAddress.__table__.c.customer_id)
Index("idx_users_role_active", User.__table__.c.role, User.__table__.c.is_active)
Index("idx_tax_rules_tax", TaxRule.__table__.c.tax_id)
