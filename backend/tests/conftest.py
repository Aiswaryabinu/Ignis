import os
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", "postgresql+psycopg://brightloop:brightloop@localhost:5432/brightloop_test")
os.environ["EMAIL_BACKEND"] = "memory"      # mails are recorded in app.mailer.SENT
os.environ["SCHEDULER_ENABLED"] = "0"
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

@pytest.fixture(scope="session")
def client():
    from app.main import app, init_db
    from app.db import Base, engine
    from app import seed
    Base.metadata.drop_all(engine)
    with engine.begin() as c:
        from app.ddl import SEQUENCES
        for sq in SEQUENCES.values(): c.execute(text(f"DROP SEQUENCE IF EXISTS {sq}"))
        for fn in ("audit_logs_immutable", "alloc_same_customer"): c.execute(text(f"DROP FUNCTION IF EXISTS {fn}() CASCADE"))
    seed.seed()
    return TestClient(app)

def login(client, email, pw="Brightloop@2026"):
    r = client.post("/auth/login", json={"email": email, "password": pw}); assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}

@pytest.fixture(scope="session")
def admin(client): return login(client, "aisha@brightloop.in")
@pytest.fixture(scope="session")
def staff(client): return login(client, "rohan@brightloop.in")
@pytest.fixture(scope="session")
def cust(client): return login(client, "ops@northwind.in")
