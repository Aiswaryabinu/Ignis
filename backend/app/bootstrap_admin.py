"""Create the first administrator using ADMIN_EMAIL, ADMIN_NAME and ADMIN_PASSWORD."""
import os

from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import User
from .security import hash_password, password_problems


def main():
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    name = os.environ.get("ADMIN_NAME", "").strip()
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not email or not name or not password:
        raise SystemExit("Set ADMIN_EMAIL, ADMIN_NAME and ADMIN_PASSWORD before running this command")
    problems = password_problems(password)
    if problems:
        raise SystemExit("ADMIN_PASSWORD must contain " + ", ".join(problems))
    db: Session = SessionLocal()
    try:
        if db.query(User).filter(User.role == "ADMIN").first():
            raise SystemExit("An administrator already exists")
        if db.query(User).filter(User.email == email).first():
            raise SystemExit("That email is already registered")
        db.add(User(email=email, full_name=name, password_hash=hash_password(password), role="ADMIN"))
        db.commit()
        print(f"Administrator account created for {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
