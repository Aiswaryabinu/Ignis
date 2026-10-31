# Member 4 — Payments, Notifications & Audit

**Project:** Brightloop Software — Subscription Management System  
**Branch:** `feature/payments-notifications`  
**Assigned tables:** 6  
**Tables:** `payments`, `payment_allocations`, `notifications`, `notification_templates`, `outbox_events`, `audit_logs`

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

Own money-received records and allocation/reconciliation, notification persistence and delivery support, transactional outbox infrastructure, and audit logging.

You depend on Member 1 for `users` and `customers`, and Member 3 for `invoices`. Your payment allocation work must integrate with Member 3's invoice balance/status rules.

## 2. Assigned tables and implementation requirements

### `payments`
Fields: `id UUID PK`, `payment_number VARCHAR(50) UNIQUE NOT NULL`, `customer_id UUID FK customers.id NOT NULL`, `payment_method VARCHAR(30) NOT NULL`, `amount NUMERIC(12,2) NOT NULL`, `payment_date TIMESTAMPTZ NOT NULL`, `reference_number VARCHAR(255) NULL`, `notes TEXT NULL`, `status VARCHAR(20) NOT NULL`, `recorded_by UUID FK users.id NOT NULL`, `created_at TIMESTAMPTZ NOT NULL`.

Rules:
- Payment methods initially: `CASH`, `BANK_TRANSFER`, `CARD`, `UPI`, `OTHER`.
- Status values: `RECORDED`, `REVERSED`.
- `amount > 0`.
- Do not store card PAN, CVV, banking credentials, or other sensitive payment credentials. Store only gateway/reference identifiers if applicable.
- Reversals must preserve the original payment record and be auditable; do not hard-delete a payment.

### `payment_allocations`
Fields: `id UUID PK`, `payment_id UUID FK payments.id NOT NULL`, `invoice_id UUID FK invoices.id NOT NULL`, `allocated_amount NUMERIC(12,2) NOT NULL`, `created_at TIMESTAMPTZ NOT NULL`.

Rules:
- `allocated_amount > 0`.
- A payment can be allocated to multiple invoices; an invoice can receive multiple payments.
- Validate payment customer equals invoice customer.
- Total allocations for a payment must not exceed payment amount.
- Total active allocations for an invoice must not exceed its outstanding amount.
- These are cross-row rules: enforce transactionally with appropriate row locks (lock payment and invoice rows in a consistent order) or an explicitly designed database trigger. A simple `CHECK` constraint cannot enforce aggregate totals.
- Decide whether multiple allocation rows for the same payment/invoice are allowed. If not, add unique `(payment_id, invoice_id)`.
- Reversing a payment must reverse/deactivate its allocations and recalculate affected invoice balances/statuses in the same transaction. The current schema has no allocation status column; coordinate whether to add `reversed_at` or use a separate reversal ledger before implementation.

### `notifications`
Fields: `id UUID PK`, `user_id UUID FK users.id NOT NULL`, `notification_type VARCHAR(100) NOT NULL`, `subject VARCHAR(255) NOT NULL`, `message TEXT NOT NULL`, `related_entity_type VARCHAR(50) NULL`, `related_entity_id UUID NULL`, `status VARCHAR(20) NOT NULL`, `sent_at TIMESTAMPTZ NULL`, `created_at TIMESTAMPTZ NOT NULL`.

Rules:
- Status values: `PENDING`, `SENT`, `FAILED`.
- Add indexes on `(user_id, created_at)` and `(status, created_at)`.
- Related entity fields are polymorphic and therefore cannot have a normal FK; validate allowed entity types in application code.
- Do not assume every customer has a portal user. Define fallback recipient behavior for customers without a user account (e.g., billing_email handled by delivery service).

### `notification_templates`
Fields: `id UUID PK`, `event_type VARCHAR(100) UNIQUE NOT NULL`, `subject_template VARCHAR(255) NOT NULL`, `body_template TEXT NOT NULL`, `is_active BOOLEAN NOT NULL DEFAULT TRUE`, `created_at TIMESTAMPTZ NOT NULL`.

Rules:
- Event type examples: invoice-created, payment-recorded, subscription-renewed, subscription-paused.
- Template rendering must escape untrusted customer/product values and must not execute arbitrary template code.
- Keep versioning strategy simple initially; if templates are editable, consider recording rendered subject/body in `notifications` so later template edits do not alter already queued notifications.

### `outbox_events`
Fields: `id UUID PK`, `event_type VARCHAR(100) NOT NULL`, `aggregate_type VARCHAR(100) NOT NULL`, `aggregate_id UUID NOT NULL`, `payload JSONB NOT NULL`, `status VARCHAR(20) NOT NULL`, `created_at TIMESTAMPTZ NOT NULL`, `published_at TIMESTAMPTZ NULL`.

Rules:
- Status values: `PENDING`, `PUBLISHED`, `FAILED`.
- Add indexes on `(status, created_at)` and `(aggregate_type, aggregate_id)`.
- Outbox row must be inserted in the same DB transaction as the business change it announces.
- Publisher should claim rows safely (e.g., `FOR UPDATE SKIP LOCKED`), publish, then mark as published. Delivery is at-least-once; consumers must be idempotent.
- Payload must contain only necessary event data, not passwords, raw tokens, or payment secrets.
- Consider adding `attempts`, `last_error`, and `next_attempt_at` if retries/backoff are in scope; get team approval before changing the logical schema.

### `audit_logs`
Fields: `id UUID PK`, `actor_user_id UUID FK users.id NULL`, `action VARCHAR(100) NOT NULL`, `entity_type VARCHAR(100) NOT NULL`, `entity_id UUID NOT NULL`, `old_values JSONB NULL`, `new_values JSONB NULL`, `ip_address INET NULL`, `created_at TIMESTAMPTZ NOT NULL`.

Rules:
- Append-only for normal application roles. Do not expose update/delete APIs.
- Redact secrets and sensitive payment/authentication fields from JSON snapshots.
- `actor_user_id` is nullable for system/scheduler actions.
- Add indexes on `(entity_type, entity_id, created_at)` and `(actor_user_id, created_at)`.
- Consider partitioning only if audit volume later justifies it; do not prematurely complicate the first release.

## 3. Relationships and dependencies

- `payments` → `payment_allocations` (1:N).
- `invoices` → `payment_allocations` (1:N), owned by Member 3.
- `customers` → `payments` (1:N), owned by Member 1.
- `users` → payments (`recorded_by`), notifications, audit actor.
- `outbox_events` is intentionally generic and has no direct FK to every aggregate.
- `notifications.related_entity_id` is polymorphic and has no conventional FK.

## 4. Payment recording transaction

1. Begin transaction.
2. Lock payment and target invoice rows in a consistent order.
3. Verify payment is `RECORDED`, invoice is payable, and both belong to the same customer.
4. Verify requested allocation is positive.
5. Sum active allocations and ensure the new allocation does not exceed payment remainder or invoice balance.
6. Insert allocation.
7. Recalculate invoice `amount_paid`, `balance_due`, and status (`PAID`, `PARTIALLY_PAID`, or the agreed unpaid status).
8. Insert audit log and outbox event.
9. Commit.

If any validation fails, roll back all changes. Coordinate with Member 3 so invoice totals/status are not independently updated by two implementations.

## 5. Payment reversal transaction

The supplied schema has no explicit allocation reversal fields. Before implementation, agree one of these approaches:
- Add `reversed_at` (and optionally `reversal_reason`) to allocations; or
- Introduce a separate immutable payment-reversal/allocation-reversal table.

Do not simply delete allocation rows, because that destroys the reconciliation trail. On reversal, recalculate every affected invoice balance and status in the same transaction.

## 6. Tests

- Payment amount must be positive; invalid method/status rejected.
- Duplicate payment number rejected.
- Payment and invoice belonging to different customers cannot be allocated.
- Allocation cannot exceed payment remainder or invoice outstanding balance.
- Concurrent allocations cannot over-allocate either side.
- Partial allocation updates invoice to partially paid; full allocation updates to paid.
- Reversal restores invoice balance correctly and preserves audit history.
- Notification status transitions are valid.
- Inactive/missing notification template is handled safely.
- Outbox publisher can retry without losing events; consumers can handle duplicate delivery.
- Audit records redact secrets and normal application role cannot mutate history.

## 7. Suggested commits

1. `feat(db): add payment and allocation models`
2. `feat(db): add notification and template models`
3. `feat(db): add transactional outbox and audit models`
4. `feat(payment): implement allocation and reversal transactions`
5. `test(payment): cover allocation reconciliation and reversal`
6. `test(events): cover outbox retry and audit behavior`

## 8. Handoff checklist

- [ ] Coordinate invoice model path and migration dependency with Member 3.
- [ ] Agree how payment allocations are reversed before coding.
- [ ] Agree who owns invoice balance/status recalculation (recommended: one shared service owned by Member 3 with payment integration from you).
- [ ] Agree outbox event names/payload schema with Members 2 and 3.
- [ ] Confirm notification recipient behavior for customers without portal users.
- [ ] Register models with Alembic metadata.
- [ ] Run PostgreSQL concurrency tests for allocation limits.
