# Backend setup

Start PostgreSQL and the API from the repository root with `docker compose up --build`. The API applies Alembic migrations before it starts and runs the background mail and billing scheduler when `SCHEDULER_ENABLED=true`.

Public registration creates customer accounts. Create the initial administrator explicitly after the first migration:

```sh
docker compose exec \
  -e ADMIN_EMAIL=admin@example.com \
  -e ADMIN_NAME="Ignis Admin" \
  -e ADMIN_PASSWORD='choose-a-long-password' \
  api python -m app.bootstrap_admin
```

The administrator can sign in from the frontend. Passwords must be longer than 8 characters and contain uppercase, lowercase, and special characters. For production, set a unique `JWT_SECRET`, an HTTPS `APP_BASE_URL`, the real frontend origin in `CORS_ORIGINS`, and SMTP settings.

The API listens on port 8000 and is mounted under `/api`; `/health` is the unauthenticated health endpoint.
