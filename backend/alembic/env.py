import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from alembic import context
from sqlalchemy import create_engine
from app.config import DATABASE_URL
from app.db import Base
from app import models  # noqa: register tables
target_metadata = Base.metadata

def run_migrations_online():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction(): context.run_migrations()
run_migrations_online()
