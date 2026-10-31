# Member 1 — Authentication, Users & Customers

## Ownership
Own the identity and customer-management foundation of SubscriptIQ.

### Modules
- `auth`
- `users`
- `customers`

### Responsibilities
1. Registration and login.
2. Password hashing and password-reset flow.
3. Role-based access: `ADMIN`, `STAFF`, `CUSTOMER`.
4. Admin-only staff account creation.
5. Customer profile creation, viewing, editing, and listing.
6. Authorization helpers/dependencies used by other backend modules.
7. Customer-facing profile and account pages on the frontend.

## Database tables
- `users`
  - `id`, `email`, `password_hash`, `role`, `is_active`, timestamps
- `customers`
  - `id`, `user_id` (nullable if staff creates a customer without login), name, contact details, billing address, timestamps
- `audit_logs` may be implemented jointly or left for integration; coordinate before changing its structure.

Use UUID or integer IDs consistently across the project. Decide the ID convention with the team before migrations are committed.

## API contract
Prefix: `/api/v1`

Suggested endpoints:
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/forgot-password`
- `POST /auth/reset-password`
- `GET /auth/me`
- `GET /users`
- `POST /users/staff` — admin only
- `GET /customers`
- `POST /customers`
- `GET /customers/{customer_id}`
- `PATCH /customers/{customer_id}`

Agree with the team on the authentication mechanism (for example, bearer access tokens) before frontend integration. Never trust a role sent by the client.

## Frontend ownership
Suggested pages/components:
- Login
- Register
- Forgot/reset password
- User profile
- Customer list and customer form
- Staff creation page (admin only)

Use the shared frontend conventions: React + TypeScript + Vite, React Router, TanStack Query, React Hook Form, Zod, and the agreed UI styling system.

## Backend structure
```text
backend/app/modules/auth/
backend/app/modules/users/
backend/app/modules/customers/
backend/app/core/security.py
backend/app/core/permissions.py
backend/tests/modules/auth/
backend/tests/modules/customers/
frontend/src/features/auth/
frontend/src/features/customers/
frontend/src/features/users/
```

## Security requirements
- Hash passwords with a suitable password-hashing library; never store plaintext passwords.
- Enforce password policy on the server.
- Check permissions on every protected endpoint.
- Customers may access only their own customer record and related data.
- Admin-only staff creation must be enforced by the backend.
- Avoid exposing password hashes or reset tokens in API responses or logs.

## Dependencies and coordination
- Define the shared `User`, `Customer`, role enum, error response, and auth dependency early.
- Share the customer ID field and response shape with Members 3 and 4.
- Coordinate endpoint names and token handling with the frontend team members.
- Do not edit other members' module internals without discussing it first.

## Suggested commit sequence
1. `feat(auth): add user and role models`
2. `feat(auth): implement registration and login`
3. `feat(auth): add role-based permissions and staff creation`
4. `feat(customers): add customer CRUD APIs`
5. `feat(frontend): add authentication and customer pages`
6. `test(auth): cover authentication and customer permissions`

## Definition of done
- Registration/login work.
- Password policy and hashing are tested.
- Staff creation is restricted to admins.
- Customer data is protected by ownership checks.
- API tests cover success, invalid input, unauthenticated access, and forbidden access.
- Changes are committed to the agreed feature branch and merged through a PR.
