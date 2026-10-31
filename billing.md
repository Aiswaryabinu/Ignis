# Member 4 — Invoices, Payments & Reports

## Ownership
Own invoice generation, manual payment recording, payment allocation, balances, and financial reporting.

### Modules
- `invoices`
- `payments`
- `reports`
- Integration with the scheduled billing worker

### Responsibilities
1. Generate invoices for billable subscriptions.
2. Store invoice line-item snapshots, tax, discount, totals, due dates, and statuses.
3. Provide invoice detail/list views and permitted invoice actions.
4. Record manual payments.
5. Allocate payments to one or more invoices, including partial payments.
6. Calculate paid, partially paid, outstanding, and overdue balances.
7. Build dashboard reports for active subscriptions, collected revenue, outstanding invoices, and overdue invoices.
8. Implement and test the recurring billing job with Member 3's subscription contract.

## Database tables
- `invoices`
- `invoice_items`
- `payments`
- `payment_allocations`

Suggested fields:
- Invoice: `id`, `customer_id`, `subscription_id`, `invoice_number`, `issued_at`, `due_at`, `status`, `subtotal`, `tax_total`, `discount_total`, `total`, `currency`
- Invoice item: `id`, `invoice_id`, `description_snapshot`, `quantity`, `unit_price`, `tax_rate_snapshot`, `discount_amount`, `line_total`
- Payment: `id`, `customer_id`, `amount`, `currency`, `paid_at`, `method`, `reference`, `notes`
- Allocation: `id`, `payment_id`, `invoice_id`, `amount`

Use `NUMERIC` in PostgreSQL and Python `Decimal` in backend code for every monetary value.

## API contract
Prefix: `/api/v1`

Suggested endpoints:
- `GET /invoices`
- `GET /invoices/{id}`
- `POST /invoices/{id}/confirm` (if confirmation is part of the workflow)
- `POST /payments`
- `GET /payments`
- `POST /payments/{payment_id}/allocations`
- `GET /reports/dashboard`
- `GET /reports/revenue`
- `GET /reports/outstanding`
- `GET /reports/overdue`

Agree with the team on invoice numbering, due-date rules, allowed statuses, and whether invoice confirmation is required.

## Recurring billing safety
- Run the billing scheduler in a separate worker process using the same backend codebase and PostgreSQL database.
- For each eligible active subscription, determine the billing period and create the invoice.
- Add a database uniqueness constraint or idempotency key for the subscription + billing period so a retry cannot create a duplicate invoice.
- Use a transaction when creating the invoice and advancing the next billing date.
- Make retries safe; do not mark a subscription as billed unless invoice creation succeeds.
- Decide with Member 3 how pauses, closures, renewals, and first invoices affect the billing date.
- Start with manual payment recording; integrate a payment gateway only if explicitly required.

## Reporting definitions
- **Collected revenue:** payments actually recorded/received, not merely invoices issued.
- **Outstanding balance:** confirmed invoice totals minus allocated payments, never below zero for display.
- **Overdue invoices:** invoices with a positive outstanding balance and a due date before the current date.
- **Active subscriptions:** subscriptions whose current status and date range meet the agreed definition.
- Apply authorization and customer ownership rules to all report queries.

## Frontend ownership
Suggested pages:
- Invoice list and invoice detail
- Record payment form
- Payment/allocation history
- Financial dashboard
- Revenue, outstanding, and overdue report views

## Backend structure
```text
backend/app/modules/invoices/
backend/app/modules/payments/
backend/app/modules/reports/
backend/app/jobs/billing.py
backend/tests/modules/invoices/
backend/tests/modules/payments/
backend/tests/modules/reports/
frontend/src/features/invoices/
frontend/src/features/payments/
frontend/src/features/reports/
```

## Dependencies and coordination
- Member 1 provides customer IDs and permission helpers.
- Member 2 provides shared pricing/tax/discount calculations.
- Member 3 provides billable subscription data and billing-period rules.
- Agree on invoice and payment response schemas before frontend integration.
- Do not edit other modules' models directly without coordinating a shared migration.

## Suggested commit sequence
1. `feat(invoices): add invoice and invoice-item models`
2. `feat(invoices): generate invoices from subscriptions`
3. `feat(payments): add manual payment recording and allocations`
4. `feat(reports): add revenue and outstanding balance reports`
5. `feat(billing): add idempotent scheduled invoice generation`
6. `test(billing): cover retries, partial payments, and overdue logic`

## Definition of done
- An eligible subscription produces no more than one invoice per billing period.
- Invoice totals are stored as snapshots and remain historically accurate.
- Partial payments and allocations update outstanding balances correctly.
- Reports distinguish collected revenue from invoice totals.
- Scheduler retries do not create duplicate invoices.
- Tests cover billing idempotency, payment allocation, permissions, and report calculations.
