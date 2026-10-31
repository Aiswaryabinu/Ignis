-- Brightloop Subscription Management System
-- PostgreSQL 18 schema
-- Run this entire script in pgAdmin Query Tool while connected to subscription_db.
-- It creates 31 tables in dependency order. It does not insert sample data.
-- UUID generation uses gen_random_uuid(), available in PostgreSQL 13+.

BEGIN;

-- 1. AUTHENTICATION
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('ADMIN','STAFF','CUSTOMER')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_password_reset_user ON password_reset_tokens(user_id);

CREATE TABLE email_verification_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_email_verification_user ON email_verification_tokens(user_id);

-- 2. CUSTOMER MANAGEMENT
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE REFERENCES users(id) ON DELETE SET NULL,
    customer_code VARCHAR(50) UNIQUE,
    company_name VARCHAR(255) NOT NULL,
    contact_person VARCHAR(255),
    phone VARCHAR(30),
    billing_email VARCHAR(255),
    tax_identifier VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE customer_addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    address_type VARCHAR(20) NOT NULL CHECK (address_type IN ('BILLING','SHIPPING')),
    address_line1 VARCHAR(255) NOT NULL,
    address_line2 VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100) NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_customer_addresses_customer ON customer_addresses(customer_id);

-- 3. PRODUCT CATALOG
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    product_type VARCHAR(100) NOT NULL,
    sales_price NUMERIC(12,2) NOT NULL CHECK (sales_price >= 0),
    cost_price NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (cost_price >= 0),
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE product_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    attribute_name VARCHAR(100) NOT NULL,
    attribute_value VARCHAR(100) NOT NULL,
    additional_price NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (additional_price >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(product_id, attribute_name, attribute_value)
);
CREATE INDEX idx_product_variants_product ON product_variants(product_id);

-- 4. SUBSCRIPTION PLANS
CREATE TABLE subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    billing_interval VARCHAR(20) NOT NULL
        CHECK (billing_interval IN ('DAILY','WEEKLY','MONTHLY','YEARLY')),
    interval_count INTEGER NOT NULL DEFAULT 1 CHECK (interval_count > 0),
    minimum_quantity INTEGER NOT NULL DEFAULT 1 CHECK (minimum_quantity > 0),
    price NUMERIC(12,2) NOT NULL CHECK (price >= 0),
    start_date DATE NOT NULL,
    end_date DATE,
    auto_close BOOLEAN NOT NULL DEFAULT FALSE,
    allow_early_close BOOLEAN NOT NULL DEFAULT TRUE,
    allow_pause BOOLEAN NOT NULL DEFAULT TRUE,
    allow_renewal BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (end_date IS NULL OR end_date >= start_date)
);

-- 5. TAX CONFIGURATION (created before subscription_lines)
CREATE TABLE taxes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    rate NUMERIC(7,4) NOT NULL CHECK (rate >= 0),
    tax_type VARCHAR(20) NOT NULL CHECK (tax_type IN ('PERCENTAGE','FIXED')),
    is_inclusive BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    effective_from DATE NOT NULL,
    effective_until DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (effective_until IS NULL OR effective_until >= effective_from)
);

CREATE TABLE tax_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tax_id UUID NOT NULL REFERENCES taxes(id) ON DELETE RESTRICT,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    country VARCHAR(100),
    state VARCHAR(100),
    priority INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX idx_tax_rules_tax ON tax_rules(tax_id);
CREATE INDEX idx_tax_rules_product ON tax_rules(product_id);

-- 6. QUOTATION TEMPLATES
CREATE TABLE quotation_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    validity_days INTEGER NOT NULL CHECK (validity_days > 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE quotation_template_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL REFERENCES quotation_templates(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    variant_id UUID REFERENCES product_variants(id) ON DELETE RESTRICT,
    plan_id UUID NOT NULL REFERENCES subscription_plans(id) ON DELETE RESTRICT,
    default_quantity INTEGER NOT NULL CHECK (default_quantity > 0),
    default_unit_price NUMERIC(12,2) NOT NULL CHECK (default_unit_price >= 0)
);
CREATE INDEX idx_template_lines_template ON quotation_template_lines(template_id);

-- 7. CUSTOMER QUOTATIONS
CREATE TABLE quotations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quotation_number VARCHAR(50) NOT NULL UNIQUE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    template_id UUID REFERENCES quotation_templates(id) ON DELETE SET NULL,
    issue_date DATE NOT NULL,
    valid_until DATE NOT NULL,
    subtotal NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (subtotal >= 0),
    discount_total NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (discount_total >= 0),
    tax_total NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (tax_total >= 0),
    grand_total NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (grand_total >= 0),
    status VARCHAR(20) NOT NULL
        CHECK (status IN ('DRAFT','SENT','ACCEPTED','EXPIRED','REJECTED')),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (valid_until >= issue_date)
);

CREATE TABLE quotation_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quotation_id UUID NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    variant_id UUID REFERENCES product_variants(id) ON DELETE RESTRICT,
    plan_id UUID NOT NULL REFERENCES subscription_plans(id) ON DELETE RESTRICT,
    product_name VARCHAR(255) NOT NULL,
    variant_name VARCHAR(255),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12,2) NOT NULL CHECK (unit_price >= 0),
    discount_amount NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
    tax_rate_snapshot NUMERIC(7,4) NOT NULL DEFAULT 0 CHECK (tax_rate_snapshot >= 0),
    tax_amount NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (tax_amount >= 0),
    line_total NUMERIC(12,2) NOT NULL CHECK (line_total >= 0)
);
CREATE INDEX idx_quotations_customer ON quotations(customer_id);
CREATE INDEX idx_quotations_status ON quotations(status);
CREATE INDEX idx_quotation_lines_quotation ON quotation_lines(quotation_id);

-- 8. SUBSCRIPTIONS
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_number VARCHAR(50) NOT NULL UNIQUE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    plan_id UUID NOT NULL REFERENCES subscription_plans(id) ON DELETE RESTRICT,
    quotation_id UUID UNIQUE REFERENCES quotations(id) ON DELETE RESTRICT,
    start_date DATE NOT NULL,
    expiry_date DATE,
    next_billing_date DATE,
    billing_anchor_date DATE,
    status VARCHAR(20) NOT NULL
        CHECK (status IN ('DRAFT','QUOTATION','CONFIRMED','ACTIVE','PAUSED','CLOSED')),
    payment_terms VARCHAR(100),
    auto_renew BOOLEAN NOT NULL DEFAULT FALSE,
    paused_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (expiry_date IS NULL OR expiry_date >= start_date)
);
CREATE INDEX idx_subscriptions_customer ON subscriptions(customer_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_next_billing ON subscriptions(next_billing_date);
CREATE INDEX idx_subscriptions_plan ON subscriptions(plan_id);

CREATE TABLE subscription_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    variant_id UUID REFERENCES product_variants(id) ON DELETE RESTRICT,
    product_name VARCHAR(255) NOT NULL,
    variant_name VARCHAR(255),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12,2) NOT NULL CHECK (unit_price >= 0),
    tax_id UUID REFERENCES taxes(id) ON DELETE SET NULL,
    tax_rate_snapshot NUMERIC(7,4) NOT NULL DEFAULT 0 CHECK (tax_rate_snapshot >= 0),
    discount_amount NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
    line_total NUMERIC(12,2) NOT NULL CHECK (line_total >= 0)
);
CREATE INDEX idx_subscription_lines_subscription ON subscription_lines(subscription_id);

CREATE TABLE subscription_status_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    old_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL
        CHECK (new_status IN ('DRAFT','QUOTATION','CONFIRMED','ACTIVE','PAUSED','CLOSED')),
    changed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_subscription_history_subscription ON subscription_status_history(subscription_id);

CREATE TABLE subscription_renewals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    previous_expiry_date DATE,
    new_expiry_date DATE NOT NULL,
    renewal_date DATE NOT NULL,
    renewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('PENDING','COMPLETED','FAILED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_subscription_renewals_subscription ON subscription_renewals(subscription_id);

-- 9. DISCOUNTS
CREATE TABLE discounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    discount_type VARCHAR(20) NOT NULL CHECK (discount_type IN ('FIXED','PERCENTAGE')),
    value NUMERIC(12,2) NOT NULL CHECK (value >= 0),
    min_purchase NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (min_purchase >= 0),
    min_quantity INTEGER NOT NULL DEFAULT 1 CHECK (min_quantity > 0),
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ,
    usage_limit INTEGER CHECK (usage_limit IS NULL OR usage_limit >= 0),
    usage_count INTEGER NOT NULL DEFAULT 0 CHECK (usage_count >= 0),
    scope VARCHAR(20) NOT NULL CHECK (scope IN ('PRODUCT','SUBSCRIPTION')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (end_date IS NULL OR end_date >= start_date),
    CHECK (discount_type <> 'PERCENTAGE' OR value <= 100),
    CHECK (usage_limit IS NULL OR usage_count <= usage_limit)
);

CREATE TABLE discount_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    discount_id UUID NOT NULL REFERENCES discounts(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    UNIQUE(discount_id, product_id)
);

-- 10. INVOICES
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_number VARCHAR(50) NOT NULL UNIQUE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE RESTRICT,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    billing_period_start DATE,
    billing_period_end DATE,
    subtotal NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (subtotal >= 0),
    discount_total NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (discount_total >= 0),
    tax_total NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (tax_total >= 0),
    total_amount NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (total_amount >= 0),
    amount_paid NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (amount_paid >= 0),
    balance_due NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (balance_due >= 0),
    status VARCHAR(20) NOT NULL
        CHECK (status IN ('DRAFT','CONFIRMED','PARTIALLY_PAID','PAID','CANCELLED','VOID')),
    pdf_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (due_date >= issue_date),
    CHECK (billing_period_end IS NULL OR billing_period_start IS NULL OR billing_period_end >= billing_period_start)
);
CREATE INDEX idx_invoices_customer ON invoices(customer_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_due_date ON invoices(due_date);
CREATE INDEX idx_invoices_subscription ON invoices(subscription_id);
CREATE UNIQUE INDEX uq_invoice_subscription_period
    ON invoices(subscription_id, billing_period_start, billing_period_end)
    WHERE billing_period_start IS NOT NULL AND billing_period_end IS NOT NULL;

CREATE TABLE invoice_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    variant_id UUID REFERENCES product_variants(id) ON DELETE SET NULL,
    description VARCHAR(500) NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12,2) NOT NULL CHECK (unit_price >= 0),
    discount_amount NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
    taxable_amount NUMERIC(12,2) NOT NULL CHECK (taxable_amount >= 0),
    tax_rate_snapshot NUMERIC(7,4) NOT NULL DEFAULT 0 CHECK (tax_rate_snapshot >= 0),
    tax_amount NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (tax_amount >= 0),
    line_total NUMERIC(12,2) NOT NULL CHECK (line_total >= 0)
);
CREATE INDEX idx_invoice_lines_invoice ON invoice_lines(invoice_id);

-- 11. DISCOUNT USAGE (after invoices exist)
CREATE TABLE discount_usages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    discount_id UUID NOT NULL REFERENCES discounts(id) ON DELETE RESTRICT,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE RESTRICT,
    discount_amount NUMERIC(12,2) NOT NULL CHECK (discount_amount >= 0),
    used_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_discount_usages_discount ON discount_usages(discount_id);
CREATE INDEX idx_discount_usages_invoice ON discount_usages(invoice_id);

-- 12. BILLING
CREATE TABLE billing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE RESTRICT,
    billing_period_start DATE NOT NULL,
    billing_period_end DATE NOT NULL,
    idempotency_key VARCHAR(255) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL
        CHECK (status IN ('PENDING','PROCESSING','COMPLETED','FAILED')),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    CHECK (billing_period_end >= billing_period_start),
    UNIQUE(subscription_id, billing_period_start, billing_period_end)
);
CREATE INDEX idx_billing_jobs_status ON billing_jobs(status);

CREATE TABLE billing_periods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE RESTRICT,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    billing_date DATE NOT NULL,
    invoice_id UUID UNIQUE REFERENCES invoices(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('PENDING','BILLED','SKIPPED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (period_end >= period_start),
    UNIQUE(subscription_id, period_start, period_end)
);

-- 13. PAYMENTS
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_number VARCHAR(50) NOT NULL UNIQUE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    payment_method VARCHAR(30) NOT NULL
        CHECK (payment_method IN ('CASH','BANK_TRANSFER','CARD','UPI','OTHER')),
    amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    payment_date TIMESTAMPTZ NOT NULL,
    reference_number VARCHAR(255),
    notes TEXT,
    status VARCHAR(20) NOT NULL CHECK (status IN ('RECORDED','REVERSED')),
    recorded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_payments_customer ON payments(customer_id);

CREATE TABLE payment_allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id UUID NOT NULL REFERENCES payments(id) ON DELETE RESTRICT,
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE RESTRICT,
    allocated_amount NUMERIC(12,2) NOT NULL CHECK (allocated_amount > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(payment_id, invoice_id)
);
CREATE INDEX idx_payment_allocations_invoice ON payment_allocations(invoice_id);

-- 14. NOTIFICATIONS AND OUTBOX
CREATE TABLE notification_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL UNIQUE,
    subject_template VARCHAR(255) NOT NULL,
    body_template TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_type VARCHAR(100) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    related_entity_type VARCHAR(50),
    related_entity_id UUID,
    status VARCHAR(20) NOT NULL CHECK (status IN ('PENDING','SENT','FAILED')),
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_status ON notifications(status);

CREATE TABLE outbox_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    aggregate_type VARCHAR(100) NOT NULL,
    aggregate_id UUID NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('PENDING','PUBLISHED','FAILED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ
);
CREATE INDEX idx_outbox_status_created ON outbox_events(status, created_at);

-- 15. AUDIT
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID NOT NULL,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_audit_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_actor ON audit_logs(actor_user_id);
CREATE INDEX idx_audit_created_at ON audit_logs(created_at);

COMMIT;

-- Verify the number and names of tables:
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;
