# Commit 02 — PostgreSQL database foundation

Incremental overlay for the backend from Commit 01. It adds the SQLAlchemy
connection, User / RefreshSession / PasswordReset models, and initial Alembic
migration.

Prerequisites: existing `app/core/config.py` exposing `settings.DATABASE_URL`,
and installed SQLAlchemy, psycopg and Alembic dependencies.

1. Extract into the root of the existing backend repository.
2. Ensure the PostgreSQL database in `DATABASE_URL` exists.
3. Run `alembic upgrade head`.
4. Verify the `users`, `refresh_sessions`, `password_resets`, and
   `alembic_version` tables exist.

Commit:
```bash
git add app/core/database.py app/models migrations
git commit -m "feat(db): add PostgreSQL models and Alembic migration"
```
