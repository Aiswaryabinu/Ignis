# Member 2 — Products, Plans, Taxes & Discounts

## Ownership

Own the catalogue and pricing rules used when quotations, subscriptions, and invoices are created.

### Modules

- `products`
- `plans`
- `taxes`
- `discounts`

### Responsibilities

1. Create and maintain products.
2. Manage product variants and variant-specific extra prices.
3. Define subscription plans and billing intervals: daily, weekly, monthly, yearly.
4. Support minimum quantities and plan availability dates.
5. Configure applicable tax rates.
6. Create fixed-amount and percentage discounts.
7. Enforce discount eligibility dates and usage limits.
8. Provide catalogue/pricing pages on the frontend.

## Database tables

- `products`
- `product_variants`
- `plans`
- `plan_items`
- `taxes`
- `discounts`
- `discount_applications` or an equivalent usage-tracking table

Suggested fields:

- Products: `id`, `name`, `description`, `is_active`
- Variants: `id`, `product_id`, `name`, `extra_price`, `is_active`
- Plans: `id`, `name`, `billing_interval`, `interval_count`, `minimum_quantity`, `available_from`, `available_until`, `is_active`
- Taxes: `id`, `name`, `rate`, `is_active`
- Discounts: `id`, `code`, `kind` (`FIXED`/`PERCENTAGE`), `value`, `starts_at`, `ends_at`, `usage_limit`, `usage_count`, `is_active`

Use `NUMERIC`/Python `Decimal` for money. Agree on currency and rounding rules with the team. Do not use floating-point values for monetary calculations.

## API contract

Prefix: `/api/v1`

Suggested endpoints:

- `GET /products`, `POST /products`, `GET /products/{id}`, `PATCH /products/{id}`
- `POST /products/{id}/variants`, `PATCH /variants/{id}`
- `GET /plans`, `POST /plans`, `GET /plans/{id}`, `PATCH /plans/{id}`
- `GET /taxes`, `POST /taxes`, `PATCH /taxes/{id}`
- `GET /discounts`, `POST /discounts`, `POST /discounts/validate`, `PATCH /discounts/{id}`

All create/update endpoints must check roles server-side. Define the shared request/response schemas with Members 3 and 4 before they integrate pricing.

## Pricing rules to agree on

- Whether plan prices are stored on `plans`, `plan_items`, or both; avoid duplicating the same source of truth.
- Whether variant extra prices are added per unit and how quantity affects the total.
- How taxes are applied (inclusive/exclusive) and how rounding works.
- Whether discount usage is reserved at quotation time or counted only when a quotation/subscription is confirmed.
- What happens when a product, plan, tax, or discount is later changed: existing invoices must preserve the prices/rates used at the time.

## Frontend ownership

Suggested pages:

- Product list/create/edit
- Product variant management
- Plan list/create/edit
- Tax configuration
- Discount list/create/edit
- Discount validation feedback

## Backend structure

```text
backend/app/modules/products/
backend/app/modules/plans/
backend/app/modules/taxes/
backend/app/modules/discounts/
backend/tests/modules/products/
backend/tests/modules/plans/
backend/tests/modules/discounts/
frontend/src/features/products/
frontend/src/features/plans/
frontend/src/features/taxes/
frontend/src/features/discounts/
```

## Dependencies and coordination

- Members 3 and 4 need stable plan, product, tax, and discount schemas.
- Expose a reusable pricing/calculation service instead of duplicating calculations in quotations and invoices.
- Return clear validation errors for unavailable plans, invalid quantities, expired discounts, and exhausted usage limits.
- Agree on whether discounts can be combined and the order of discount/tax calculations.

## Suggested commit sequence

1. `feat(catalogue): add product and variant models`
2. `feat(plans): add subscription plans and billing intervals`
3. `feat(pricing): add tax configuration and calculation rules`
4. `feat(discounts): implement fixed and percentage discounts`
5. `feat(frontend): add catalogue and pricing pages`
6. `test(pricing): cover quantity, tax, and discount edge cases`

## Definition of done

- Products, variants, plans, taxes, and discounts can be managed.
- Billing interval, quantity, and availability validation work.
- Discount date/usage restrictions are enforced server-side.
- Money calculations use Decimal/Numeric and have tests.
- Members 3 and 4 can call the pricing service without importing internal implementation details.
