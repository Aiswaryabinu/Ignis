# Member 3 — Quotations & Subscription Lifecycle

## Ownership
Own the workflow that converts a customer request into a quotation and then into a subscription.

### Modules
- `quotations`
- `subscriptions`
- Shared quotation-template functionality

### Responsibilities
1. Create and manage reusable quotation templates and template items.
2. Create quotations for customers using products, variants, plans, taxes, and eligible discounts.
3. Calculate and store quotation totals.
4. Support quotation status changes and confirmation/acceptance.
5. Convert an accepted quotation into a subscription.
6. Implement the subscription lifecycle and permitted actions: draft, quotation, confirmed, active, paused (if required), renewed, and closed.
7. Validate lifecycle transitions instead of allowing arbitrary status changes.
8. Provide quotation and subscription frontend pages.

## Database tables
- `quotation_templates`
- `quotation_template_items`
- `quotations`
- `quotation_items`
- `subscriptions`
- `subscription_items`

Suggested status values should be agreed by the team. A practical baseline is:
- Quotation: `DRAFT`, `SENT`, `ACCEPTED`, `REJECTED`, `EXPIRED`
- Subscription: `DRAFT`, `QUOTATION`, `CONFIRMED`, `ACTIVE`, `PAUSED`, `CLOSED`

If the source requirements specify a different status vocabulary, use that vocabulary consistently. Renewal can be an action/event rather than a permanent status.

## API contract
Prefix: `/api/v1`

Suggested endpoints:
- `GET /quotation-templates`
- `POST /quotation-templates`
- `POST /quotations`
- `GET /quotations`
- `GET /quotations/{id}`
- `POST /quotations/{id}/send`
- `POST /quotations/{id}/accept`
- `POST /quotations/{id}/reject`
- `POST /subscriptions`
- `GET /subscriptions`
- `GET /subscriptions/{id}`
- `POST /subscriptions/{id}/confirm`
- `POST /subscriptions/{id}/activate`
- `POST /subscriptions/{id}/pause`
- `POST /subscriptions/{id}/resume`
- `POST /subscriptions/{id}/renew`
- `POST /subscriptions/{id}/close`

Implement only the actions allowed by the project requirements and define allowed state transitions centrally.

## Important data-integrity rules
- Store a snapshot of item descriptions, quantities, unit prices, taxes, and discounts on quotation items.
- Later edits to a product or plan must not silently rewrite an already-issued quotation.
- Confirming a quotation and creating its subscription should be transactional.
- Prevent invalid lifecycle transitions (for example, activating a closed subscription).
- Keep a clear relationship between quotation, subscription, customer, and source template.
- Use shared pricing calculations from Member 2 rather than reimplementing pricing logic.

## Frontend ownership
Suggested pages:
- Quotation template list/editor
- Create quotation
- Quotation detail and status actions
- Subscription list and detail
- Subscription lifecycle controls and confirmation dialogs

## Backend structure
```text
backend/app/modules/quotations/
backend/app/modules/subscriptions/
backend/tests/modules/quotations/
backend/tests/modules/subscriptions/
frontend/src/features/quotations/
frontend/src/features/subscriptions/
```

## Dependencies and coordination
- Member 1 provides customer/auth models and permission helpers.
- Member 2 provides product/plan/tax/discount schemas and pricing service.
- Member 4 needs subscription status, next billing date, billing interval, and subscription item details to generate invoices.
- Agree with Member 4 on when the subscription becomes billable and how the next billing date is calculated.

## Suggested commit sequence
1. `feat(quotations): add quotation templates and models`
2. `feat(quotations): implement quotation creation and totals`
3. `feat(subscriptions): convert accepted quotations to subscriptions`
4. `feat(subscriptions): implement lifecycle actions and validation`
5. `feat(frontend): add quotation and subscription workflows`
6. `test(subscriptions): cover lifecycle transitions`

## Definition of done
- A quotation can be created for a customer with validated items and pricing.
- Acceptance/confirmation creates the expected subscription exactly once.
- Subscription transitions are validated and tested.
- Customers can only view their own quotations/subscriptions; staff/admin permissions are enforced.
- Member 4 can identify billable subscriptions and calculate billing periods from the agreed contract.