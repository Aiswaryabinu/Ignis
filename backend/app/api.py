from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from . import models as m
from .db import get_db
from .security import current_user, hash_password, make_token, password_problems, verify_password, burn_password_check

router = APIRouter()


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class Registration(Credentials):
    full_name: str = Field(min_length=1, max_length=255)


def public_user(user: m.User):
    roles = {"ADMIN": "Admin", "STAFF": "Staff", "CUSTOMER": "Customer"}
    return {"id": str(user.id), "email": user.email, "name": user.full_name or user.email,
            "role": roles.get(user.role, "Customer")}


@router.post("/auth/login")
def login(body: Credentials, db: Session = Depends(get_db)):
    user = db.query(m.User).filter(m.User.email == body.email.lower()).first()
    if not user:
        burn_password_check(body.password)
        raise HTTPException(401, "Email or password is incorrect")
    if not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Email or password is incorrect")
    return {"access_token": make_token(user), "token_type": "bearer", "user": public_user(user)}


@router.post("/auth/register", status_code=201)
def register(body: Registration, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.query(m.User).filter(m.User.email == email).first():
        raise HTTPException(409, "An account with this email already exists")
    problems = password_problems(body.password)
    if problems:
        raise HTTPException(422, "Password must contain " + ", ".join(problems))
    name = body.full_name.strip()
    if not name:
        raise HTTPException(422, "Name is required")
    user = m.User(email=email, password_hash=hash_password(body.password), full_name=name, role="CUSTOMER")
    db.add(user)
    db.flush()
    customer = m.Customer(customer_code=f"CUS-{uuid4().hex[:10].upper()}", company_name=name,
                          contact_person=name, billing_email=email, user_id=user.id)
    db.add(customer)
    db.commit()
    db.refresh(user)
    return {"access_token": make_token(user), "token_type": "bearer", "user": public_user(user)}


@router.get("/auth/me")
def get_me(user: m.User = Depends(current_user)):
    return public_user(user)
