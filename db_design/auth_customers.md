Member 1 — Authentication, Customers & Products
Project: Brightloop Software — Subscription Management System  
Branch: `feature/auth-customers-products`  
Assigned tables: 7  
Tables: `users`, `password_reset_tokens`, `email_verification_tokens`, `customers`, `customer_addresses`, `products`, `product_variants`

---

Brightloop Subscription Management System — Database Implementation
Shared implementation contract (applies to every member)
Stack: PostgreSQL, SQLAlchemy 2.0, Alembic, FastAPI, Pydantic, UUID primary keys, `TIMESTAMPTZ` timestamps, and `NUMERIC` for monetary values.
Repository conventions
Use the repository's existing package layout and naming conventions. Do not create a second competing `Base`, database session, enum module, or migration environment.
Use SQLAlchemy 2.0 typed mappings (`Mapped[...]` and `mapped_column`) if that is the project's established style.
Use UUID primary keys consistently. Prefer a database/server-side UUID default if the project already uses one; otherwise follow the agreed project convention.
Store timestamps with timezone (`TIMESTAMPTZ`). Use UTC-aware values in application code.
Store money as `NUMERIC`, never binary floating point. Use `Decimal` in Python.
Add explicit `ForeignKey`, `UniqueConstraint`, `CheckConstraint`, and indexes where specified or required by the business rules.
Use named constraints and indexes so Alembic migrations are readable and stable.
Use SQLAlchemy relationships only where useful; avoid circular imports by using string relationship targets and `TYPE_CHECKING` imports where appropriate.
Do not put passwords, raw reset tokens, raw verification tokens, card details, or secrets in logs.
Do not silently delete financial history. Prefer `RESTRICT` for referenced business/financial records; use `CASCADE` for true dependent rows only where agreed.
Do not create or edit another member's models or migration files without coordinating first.
Add/update Pydantic schemas only for the endpoints or use cases included in your assigned scope. Keep ORM models and API schemas separate.
Write tests for constraints and important business rules. Do not rely only on Pydantic validation for database integrity.
Important design clarifications to resolve with the team before migrations
Enums: Agree whether statuses/roles are PostgreSQL native enums or constrained strings. Use one shared definition per enum; do not independently define duplicate enums.
Delete policies: Agree each FK's `ON DELETE` action. Recommended starting point: `RESTRICT` for customers, products, plans, quotations, subscriptions, invoices and payments once referenced; `CASCADE` for child lines/history that have no independent life only when the parent itself may legally be deleted; `SET NULL` for optional actor/user references.
Financial snapshots: Quotation, subscription and invoice lines must retain names, quantities, prices, discounts and tax values as snapshots. Never recalculate historical documents from the current product/plan/tax catalog.
Money precision: Use a consistent currency precision and rounding policy. The current document examples use `NUMERIC(12,2)` for amounts and `NUMERIC(7,4)` for rates. Confirm whether multi-currency is out of scope.
Invoice/payment consistency: `amount_paid` and `balance_due` are derived from payment allocations. If stored for performance, update them only inside the same transaction as allocation changes.
Billing idempotency: Enforce uniqueness for a subscription + billing period. A retry must return/reuse the existing billing result, not create another invoice.
Tenant scope: This initial design is single-business / single-tenant. Do not add tenant_id unless the project owner changes scope.
Required deliverables for every member
SQLAlchemy model(s) for every assigned table.
Alembic migration(s), coordinated with the migration owner.
Relevant Pydantic schemas only if needed by the assigned API work.
Unit/integration tests for model constraints and business rules.
A short module README or code comments for non-obvious decisions.
A feature branch and focused commits; do not commit generated secrets, local database files, or `.env`.
Migration coordination
Create feature branches and develop models in parallel, but do not independently create conflicting Alembic heads. The designated migration coordinator should generate/merge migrations after the shared base models and dependency order are agreed. If parallel migrations are unavoidable, use Alembic merge revisions deliberately and test `alembic upgrade head` on a clean database.
Definition of done
Models import successfully from the shared model registry.
A clean PostgreSQL database upgrades to the latest Alembic head.
Downgrade works for the member's migration where practical.
Constraints and indexes exist in PostgreSQL, not just in application code.
Tests pass against PostgreSQL (SQLite is not a substitute for PostgreSQL-specific enum, JSONB, INET, or locking behavior).
No duplicate table definitions, enum definitions, or Alembic heads remain.

---

1. Ownership and goal
   Own the foundation layer for identity, customer records, and the product catalog. Other modules depend on your tables, so prioritize stable identifiers, clear relationships, and agreed shared enum definitions.
2. Assigned tables and implementation requirements
   `users`
   Fields: `id UUID PK`, `email VARCHAR(255) UNIQUE NOT NULL`, `password_hash VARCHAR(255) NOT NULL`, `role VARCHAR(20) NOT NULL`, `is_active BOOLEAN NOT NULL DEFAULT TRUE`, `email_verified BOOLEAN NOT NULL DEFAULT FALSE`, `created_at TIMESTAMPTZ NOT NULL`, `updated_at TIMESTAMPTZ NOT NULL`.
   Rules:
   Normalize email consistently before storage and enforce uniqueness (consider a unique index on `lower(email)` if case-insensitive identity is required).
   Store only a strong password hash; never store plaintext passwords.
   Role values initially: `ADMIN`, `STAFF`, `CUSTOMER`.
   Enforce role validity with the team's shared enum/check strategy.
   Only an ADMIN may create STAFF accounts; enforce this in service authorization, not with a row check constraint.
   `password_reset_tokens`
   Fields: `id UUID PK`, `user_id UUID FK users.id NOT NULL`, `token_hash VARCHAR(255) NOT NULL`, `expires_at TIMESTAMPTZ NOT NULL`, `used_at TIMESTAMPTZ NULL`, `created_at TIMESTAMPTZ NOT NULL`.
   Rules:
   Persist a hash of a cryptographically random token, not the raw token.
   A token is valid only if not used and not expired.
   Add indexes for `user_id` and `expires_at`.
   Consider preventing multiple simultaneously active reset tokens per user in service logic or with a suitable partial index if the team wants that policy.
   `email_verification_tokens`
   Fields: `id UUID PK`, `user_id UUID FK users.id NOT NULL`, `token_hash VARCHAR(255) NOT NULL`, `expires_at TIMESTAMPTZ NOT NULL`, `verified_at TIMESTAMPTZ NULL`, `created_at TIMESTAMPTZ NOT NULL`.
   Rules:
   Store token hashes only.
   A token is valid only if not verified and not expired.
   Add indexes for `user_id` and `expires_at`.
   `customers`
   Fields: `id UUID PK`, `user_id UUID FK users.id UNIQUE NULL`, `customer_code VARCHAR(50) UNIQUE NULL`, `company_name VARCHAR(255) NOT NULL`, `contact_person VARCHAR(255) NULL`, `phone VARCHAR(30) NULL`, `billing_email VARCHAR(255) NULL`, `tax_identifier VARCHAR(100) NULL`, `is_active BOOLEAN NOT NULL DEFAULT TRUE`, `created_at TIMESTAMPTZ NOT NULL`, `updated_at TIMESTAMPTZ NOT NULL`.
   Rules:
   A customer is a business/customer entity; a user is a login identity. They are not interchangeable.
   `user_id` is nullable so staff can create customers without portal access.
   One portal user maps to at most one customer.
   Customer code is unique when supplied. Decide with the team whether it is required/generated at customer creation.
   Do not cascade-delete customers that already have quotations, subscriptions, invoices, or payments.
   `customer_addresses`
   Fields: `id UUID PK`, `customer_id UUID FK customers.id NOT NULL`, `address_type VARCHAR(20) NOT NULL`, `address_line1 VARCHAR(255) NOT NULL`, `address_line2 VARCHAR(255) NULL`, `city VARCHAR(100) NOT NULL`, `state VARCHAR(100) NULL`, `postal_code VARCHAR(20) NULL`, `country VARCHAR(100) NOT NULL`, `is_default BOOLEAN NOT NULL DEFAULT FALSE`, `created_at TIMESTAMPTZ NOT NULL`.
   Rules:
   `address_type` initially `BILLING` or `SHIPPING`.
   Add index on `customer_id`.
   If the business requires only one default address per type, enforce with a partial unique index on `(customer_id, address_type)` where `is_default = TRUE`.
   Address history may matter for invoices; invoice billing-address snapshots are a later integration requirement, not currently in the supplied invoice schema.
   `products`
   Fields: `id UUID PK`, `name VARCHAR(255) NOT NULL`, `product_type VARCHAR(100) NOT NULL`, `sales_price NUMERIC(12,2) NOT NULL`, `cost_price NUMERIC(12,2) NOT NULL`, `notes TEXT NULL`, `is_active BOOLEAN NOT NULL DEFAULT TRUE`, `created_at TIMESTAMPTZ NOT NULL`, `updated_at TIMESTAMPTZ NOT NULL`.
   Rules:
   `sales_price >= 0`; `cost_price >= 0`.
   Use `Decimal`; never float for prices.
   Inactive products cannot be selected for new quotations/subscriptions, but historical lines must remain readable.
   Product price changes must not update existing quotation/subscription/invoice snapshots.
   `product_variants`
   Fields: `id UUID PK`, `product_id UUID FK products.id NOT NULL`, `attribute_name VARCHAR(100) NOT NULL`, `attribute_value VARCHAR(100) NOT NULL`, `additional_price NUMERIC(12,2) NOT NULL DEFAULT 0`, `is_active BOOLEAN NOT NULL DEFAULT TRUE`, `created_at TIMESTAMPTZ NOT NULL`.
   Rules:
   `additional_price >= 0` unless the product owner explicitly permits negative adjustments.
   Add index on `product_id`.
   Consider unique `(product_id, attribute_name, attribute_value)` to prevent duplicate variants.
   Validate that a selected variant belongs to the selected product in service logic.
3. Relationships and dependencies
   `users` → `password_reset_tokens` (1:N)
   `users` → `email_verification_tokens` (1:N)
   `users` → `customers` (0:1)
   `users` → quotation/subscription/payment actor references owned by other members
   `customers` → `customer_addresses` (1:N)
   `customers` → quotations, subscriptions, invoices, payments owned by other members
   `products` → `product_variants` (1:N)
   `products` and variants are referenced by quotation, subscription, and invoice lines.
   Dependency contract: publish the exact Python import paths and shared enum names to the team early. Person 2 and Person 3 need your `Customer`, `Product`, and `ProductVariant` model/table names and FK types.
4. Suggested indexes and constraints
   Unique email (case-insensitive policy to be agreed).
   Unique `customers.user_id` (nullable).
   Unique `customers.customer_code` (nullable if code generation is deferred).
   Index token tables on `(user_id, expires_at)`.
   Index `customer_addresses.customer_id`.
   Check non-negative product sales/cost prices and variant additional price.
   Unique product variant attribute combination if duplicates are not meaningful.
5. Tests
   Duplicate email rejected.
   Invalid role/address type rejected.
   Reset/verification token FK and expiry fields behave as expected.
   A user cannot be linked to two customers.
   Customer without a portal user is allowed.
   Duplicate customer code rejected.
   Negative product/variant prices rejected by PostgreSQL.
   Duplicate variant combination rejected if that constraint is adopted.
   Deleting a referenced customer/product is restricted according to agreed policy.
6. Suggested commits
   `feat(db): add users and authentication token models`
   `feat(db): add customer and address models`
   `feat(db): add product and variant models`
   `test(db): cover auth customer and product constraints`
7. Handoff checklist
   [ ] Publish model import paths and table names.
   [ ] Confirm role and address-type enum strategy with team.
   [ ] Confirm customer-code generation policy.
   [ ] Confirm FK deletion policies.
   [ ] Ensure all assigned models are registered for Alembic metadata discovery.
   [ ] Share migration revision/dependency information with the coordinator.
   [ ] Run tests and a clean migration upgrade.
