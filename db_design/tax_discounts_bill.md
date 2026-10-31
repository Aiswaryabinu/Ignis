# Member 3 — Taxes, Discounts, Billing & Invoices

**Project:** Brightloop Software — Subscription Management System  
**Branch:** `feature/billing-invoices`  
**Assigned tables:** 9  
**Tables:** `taxes`, `tax_rules`, `discounts`, `discount_products`, `discount_usages`, `billing_jobs`, `billing_periods`, `invoices`, `invoice_lines`

---

# Brightloop Subscription Management System — Database Implementation

## Shared implementation contract (applies to every member)

**Stack:** PostgreSQL, SQLAlchemy 2.0, Alembic, FastAPI, Pydantic, UUID primary keys, `TIMESTAMPTZ` timestamps, and `NUMERIC` for monetary values.

### Repository conventions
- Use the repository's existing package layout and naming conventions. Do not create a second competing `Base`, database session, enum module, or migration environment.
- Use SQLAlchemy 2.0 typed mappings (`Mapped[...]` and `mapped_column`) if that is the project's established style.
- Use UUID primary keys consistently. Prefer a database/server-side UUID default if the project already uses one; otherwise follow the agreed project convention.
- Store timestamps with timezone (`TIMESTAMPTZ`). Use UTC-aware values in application code.
- Store money as `NUMERIC`, never binary floating point. Use `Decimal` in Python.
- Add explicit `ForeignKey`, `UniqueConstraint`, `CheckConstraint`, and indexes where specified or required by the business rules.
- Use named constraints and indexes so Alembic migrations are readable and stable.
- Use SQLAlchemy relationships only where useful; avoid circular imports by using string relationship targets and `TYPE_CHECKING` imports where appropriate.
- Do not put passwords, raw reset tokens, raw verification tokens, card details, or secrets in logs.
- Do not silently delete financial history. Prefer `RESTRICT` for referenced business/financial records; use `CASCADE` for true dependent rows only where agreed.
- Do not create or edit another member's models or migration files without coordinating first.
- Add/update Pydantic schemas only for the endpoints or use cases included in your assigned scope. Keep ORM models and API schemas separate.
- Write tests for constraints and important business rules. Do not rely only on Pydantic validation for database integrity.

### Important design clarifications to resolve with the team before migrations
1. **Enums:** Agree whether statuses/roles are PostgreSQL native enums or constrained strings. Use one shared definition per enum; do not independently define duplicate enums.
2. **Delete policies:** Agree each FK's `ON DELETE` action. Recommended starting point: `RESTRICT` for customers, products, plans, quotations, subscriptions, invoices and payments once referenced; `CASCADE` for child lines/history that have no independent life only when the parent itself may legally be deleted; `SET NULL` for optional actor/user references.
3. **Financial snapshots:** Quotation, subscription and invoice lines must retain names, quantities, prices, discounts and tax values as snapshots. Never recalculate historical documents from the current product/plan/tax catalog.
4. **Money precision:** Use a consistent currency precision and rounding policy. The current document examples use `NUMERIC(12,2)` for amounts and `NUMERIC(7,4)` for rates. Confirm whether multi-currency is out of scope.
5. **Invoice/payment consistency:** `amount_paid` and `balance_due` are derived from payment allocations. If stored for performance, update them only inside the same transaction as allocation changes.
6. **Billing idempotency:** Enforce uniqueness for a subscription + billing period. A retry must return/reuse the existing billing result, not create another invoice.
7. **Tenant scope:** This initial design is single-business / single-tenant. Do not add tenant_id unless the project owner changes scope.

### Required deliverables for every member
- SQLAlchemy model(s) for every assigned table.
- Alembic migration(s), coordinated with the migration owner.
- Relevant Pydantic schemas only if needed by the assigned API work.
- Unit/integration tests for model constraints and business rules.
- A short module README or code comments for non-obvious decisions.
- A feature branch and focused commits; do not commit generated secrets, local database files, or `.env`.

### Migration coordination
Create feature branches and develop models in parallel, but **do not independently create conflicting Alembic heads**. The designated migration coordinator should generate/merge migrations after the shared base models and dependency order are agreed. If parallel migrations are unavoidable, use Alembic merge revisions deliberately and test `alembic upgrade head` on a clean database.

### Definition of done
- Models import successfully from the shared model registry.
- A clean PostgreSQL database upgrades to the latest Alembic head.
- Downgrade works for the member's migration where practical.
- Constraints and indexes exist in PostgreSQL, not just in application code.
- Tests pass against PostgreSQL (SQLite is not a substitute for PostgreSQL-specific enum, JSONB, INET, or locking behavior).
- No duplicate table definitions, enum definitions, or Alembic heads remain.

---

## 1. Ownership and goal

Own the financial calculation and recurring billing pipeline: tax configuration, discount eligibility and usage, billing job execution, billing-period tracking, invoice creation, and immutable invoice-line snapshots.

You depend on Member 1 for products/customers, Member 2 for subscriptions/subscription lines, and Member 4's payment module only for later invoice settlement integration. Your `invoices` table is a dependency for Member 4's payment allocations.

## 2. Assigned tables and implementation requirements

### `taxes`
Fields: `id UUID PK`, `name VARCHAR(100) NOT NULL`, `rate NUMERIC(7,4) NOT NULL`, `tax_type VARCHAR(20) NOT NULL`, `is_inclusive BOOLEAN NOT NULL DEFAULT FALSE`, `is_active BOOLEAN NOT NULL DEFAULT TRUE`, `effective_from DATE NOT NULL`, `effective_until DATE NULL`, `created_at TIMESTAMPTZ NOT NULL`.

Rules:
- `tax_type`: `PERCENTAGE` or `FIXED`.
- Rate must be non-negative; percentage rate must be within the agreed maximum (normally 0–100 if represented as percentage points).
- `effective_until` must be on/after `effective_from`.
- Do not edit historical invoice tax snapshots when a tax record changes.

### `tax_rules`
Fields: `id UUID PK`, `tax_id UUID FK taxes.id NOT NULL`, `product_id UUID FK products.id NULL`, `country VARCHAR(100) NULL`, `state VARCHAR(100) NULL`, `priority INTEGER NOT NULL DEFAULT 0`, `is_active BOOLEAN NOT NULL DEFAULT TRUE`.

Rules:
- Add indexes on `tax_id`, `product_id`, and location matching fields as query patterns require.
- Define rule precedence deterministically (e.g., product+state beats country-only, then priority).
- Prevent ambiguous duplicate active rules where practical.
- Tax engine must select the applicable rule for the invoice date and customer location; store the resulting rate/amount snapshots on invoice lines.

### `discounts`
Fields: `id UUID PK`, `name VARCHAR(255) NOT NULL`, `discount_type VARCHAR(20) NOT NULL`, `value NUMERIC(12,2) NOT NULL`, `min_purchase NUMERIC(12,2) NOT NULL DEFAULT 0`, `min_quantity INTEGER NOT NULL DEFAULT 1`, `start_date TIMESTAMPTZ NOT NULL`, `end_date TIMESTAMPTZ NULL`, `usage_limit INTEGER NULL`, `usage_count INTEGER NOT NULL DEFAULT 0`, `scope VARCHAR(20) NOT NULL`, `is_active BOOLEAN NOT NULL DEFAULT TRUE`, `created_by UUID FK users.id NOT NULL`, `created_at TIMESTAMPTZ NOT NULL`.

Rules:
- `discount_type`: `FIXED` or `PERCENTAGE`; `scope`: `PRODUCT` or `SUBSCRIPTION`.
- Values/minimums/counts must be non-negative; `min_quantity >= 1`; usage count cannot be negative and must not exceed usage limit.
- Percentage discount must be within the agreed range (normally 0–100).
- End date, if supplied, must not precede start date.
- Prevent concurrent workers from exceeding usage limits: lock the discount row or use an atomic conditional update inside the invoice transaction.

### `discount_products`
Fields: `id UUID PK`, `discount_id UUID FK discounts.id NOT NULL`, `product_id UUID FK products.id NOT NULL`.

Rules:
- Unique `(discount_id, product_id)`.
- Add indexes on both FKs.
- Validate discount scope and eligible product before application.

### `discount_usages`
Fields: `id UUID PK`, `discount_id UUID FK discounts.id NOT NULL`, `customer_id UUID FK customers.id NOT NULL`, `subscription_id UUID FK subscriptions.id NULL`, `invoice_id UUID FK invoices.id NOT NULL`, `discount_amount NUMERIC(12,2) NOT NULL`, `used_at TIMESTAMPTZ NOT NULL`.

Rules:
- `discount_amount >= 0`.
- Record usage in the same transaction as invoice creation.
- Prevent duplicate usage for the same discount and invoice where business rules allow only one application.
- Coordinate creation order because this table references `invoices`, `subscriptions`, and `customers`.

### `billing_jobs`
Fields: `id UUID PK`, `subscription_id UUID FK subscriptions.id NOT NULL`, `billing_period_start DATE NOT NULL`, `billing_period_end DATE NOT NULL`, `idempotency_key VARCHAR(255) UNIQUE NOT NULL`, `status VARCHAR(20) NOT NULL`, `attempts INTEGER NOT NULL DEFAULT 0`, `error_message TEXT NULL`, `created_at TIMESTAMPTZ NOT NULL`, `completed_at TIMESTAMPTZ NULL`.

Rules:
- Status values: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`.
- Unique `(subscription_id, billing_period_start, billing_period_end)` as well as unique idempotency key.
- Period end must be on/after period start.
- Worker claims jobs safely (e.g., row locking / `FOR UPDATE SKIP LOCKED`).
- Retry failed jobs without creating duplicate invoices.

### `billing_periods`
Fields: `id UUID PK`, `subscription_id UUID FK subscriptions.id NOT NULL`, `period_start DATE NOT NULL`, `period_end DATE NOT NULL`, `billing_date DATE NOT NULL`, `invoice_id UUID FK invoices.id NULL`, `status VARCHAR(20) NOT NULL`, `created_at TIMESTAMPTZ NOT NULL`.

Rules:
- Status values: `PENDING`, `BILLED`, `SKIPPED`.
- Unique `(subscription_id, period_start, period_end)`.
- Period end must be on/after period start.
- Invoice link should be unique if one invoice corresponds to exactly one billing period; confirm this rule with the team.

### `invoices`
Fields: `id UUID PK`, `invoice_number VARCHAR(50) UNIQUE NOT NULL`, `customer_id UUID FK customers.id NOT NULL`, `subscription_id UUID FK subscriptions.id NOT NULL`, `issue_date DATE NOT NULL`, `due_date DATE NOT NULL`, `billing_period_start DATE NULL`, `billing_period_end DATE NULL`, `subtotal NUMERIC(12,2) NOT NULL`, `discount_total NUMERIC(12,2) NOT NULL DEFAULT 0`, `tax_total NUMERIC(12,2) NOT NULL DEFAULT 0`, `total_amount NUMERIC(12,2) NOT NULL`, `amount_paid NUMERIC(12,2) NOT NULL DEFAULT 0`, `balance_due NUMERIC(12,2) NOT NULL`, `status VARCHAR(20) NOT NULL`, `pdf_url TEXT NULL`, `created_at TIMESTAMPTZ NOT NULL`.

Rules:
- Status values: `DRAFT`, `CONFIRMED`, `PARTIALLY_PAID`, `PAID`, `CANCELLED`, `VOID`. `OVERDUE` is derived from due date and outstanding balance.
- Enforce recurring uniqueness on `(subscription_id, billing_period_start, billing_period_end)` when both period values are non-null, using a partial unique index if needed.
- `due_date >= issue_date` unless an explicit business exception is approved.
- All totals/balances must be non-negative; `amount_paid <= total_amount`; `balance_due = total_amount - amount_paid`.
- Keep issued invoices immutable; corrections should use void/cancel or future credit-note functionality, not overwrite line history.
- Customer must match subscription customer (validate in service or enforce with a suitable composite FK if the team chooses).

### `invoice_lines`
Fields: `id UUID PK`, `invoice_id UUID FK invoices.id NOT NULL`, `product_id UUID FK products.id NULL`, `variant_id UUID FK product_variants.id NULL`, `description VARCHAR(500) NOT NULL`, `quantity INTEGER NOT NULL`, `unit_price NUMERIC(12,2) NOT NULL`, `discount_amount NUMERIC(12,2) NOT NULL DEFAULT 0`, `taxable_amount NUMERIC(12,2) NOT NULL`, `tax_rate_snapshot NUMERIC(7,4) NOT NULL DEFAULT 0`, `tax_amount NUMERIC(12,2) NOT NULL DEFAULT 0`, `line_total NUMERIC(12,2) NOT NULL`.

Rules:
- `quantity > 0`; monetary values and tax rate must be non-negative.
- Preserve description, quantity, unit price, discount, taxable amount, tax rate, tax amount and final line total as invoice snapshots.
- Agree with Member 2 whether line totals include tax and how rounding is applied.

## 3. Relationships and dependencies

- `taxes` → `tax_rules`; `taxes` is also referenced by Member 2's `subscription_lines.tax_id`.
- `discounts` → `discount_products` and `discount_usages`.
- `subscriptions` → `billing_jobs`, `billing_periods`, `invoices`, `discount_usages`.
- `invoices` → `invoice_lines`, `billing_periods`, `discount_usages`, and Member 4's `payment_allocations`.
- `products` → `tax_rules`, `discount_products`, and invoice lines.
- `customers` → invoices and discount usages.

## 4. Billing transaction / idempotency contract

For each subscription billing period:
1. Create or claim one `billing_jobs` row using the unique idempotency key and unique subscription-period constraint.
2. Lock the subscription row and verify it is active, within dates, and not paused/closed.
3. Verify no invoice already exists for this subscription period.
4. Load subscription line snapshots; do not fetch current product prices as the charge price.
5. Evaluate discount eligibility and reserve/increment usage atomically.
6. Resolve tax rules for the customer and billing date.
7. Insert invoice and invoice lines with all calculated snapshots.
8. Insert `billing_periods` row or update its existing pending row to `BILLED`.
9. Update `subscriptions.next_billing_date` using the agreed interval/anchor rules.
10. Insert an outbox event for invoice-created notification (coordinate event payload with Member 4).
11. Mark the billing job `COMPLETED` and commit.

All steps must be one transaction where feasible. A failed transaction must not leave a partially created invoice, discount usage, or advanced next-billing date. Use unique constraints as the final duplicate-billing defense.

## 5. Tests

- Invalid tax types/rates/effective dates rejected.
- Tax rule precedence is deterministic.
- Fixed and percentage discounts calculate correctly and are capped at eligible amount.
- Discount validity, minimum purchase, minimum quantity, product scope and usage limits enforced.
- Concurrent discount applications cannot exceed usage limit.
- Duplicate billing job for same subscription period rejected/reused.
- Paused/closed/not-yet-started subscriptions are not billed.
- Retry after worker failure does not create a second invoice.
- Invoice line snapshots remain unchanged after product, plan, tax or discount catalog edits.
- Invoice totals reconcile to line totals using agreed rounding.
- Duplicate recurring invoice for a period is rejected.
- Billing period and next billing date update atomically.

## 6. Suggested commits

1. `feat(db): add tax and tax rule models`
2. `feat(db): add discount and discount usage models`
3. `feat(db): add billing job and billing period models`
4. `feat(db): add invoice and invoice line models`
5. `feat(billing): implement idempotent recurring invoice generation`
6. `test(billing): cover tax discount invoice and retry cases`

## 7. Handoff checklist

- [ ] Agree line-total formula, tax inclusion and rounding with Member 2.
- [ ] Agree billing interval and billing anchor semantics with Member 2.
- [ ] Agree invoice-created outbox event payload with Member 4.
- [ ] Publish invoice model path and migration ID to Member 4.
- [ ] Confirm invoice period partial unique index behavior.
- [ ] Register all models with Alembic metadata.
- [ ] Test concurrent billing and retries on PostgreSQL.
