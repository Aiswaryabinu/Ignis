from uuid import UUID, uuid4
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from . import models as m
from .db import get_db
from .security import current_user, hash_password, make_token, password_problems, verify_password, burn_password_check, staff_or_admin, customer_of

router = APIRouter()


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class Registration(Credentials):
    full_name: str = Field(min_length=1, max_length=255)


class CustomerInput(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    billing_email: EmailStr | None = None
    contact_person: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    industry: str | None = Field(default=None, max_length=100)
    is_active: bool = True


class ProductInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    product_type: str = Field(min_length=1, max_length=100)
    sales_price: Decimal = Field(ge=Decimal("0"))
    cost_price: Decimal = Field(ge=Decimal("0"))
    notes: str | None = None
    is_active: bool = True


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


def customer_data(customer: m.Customer, db: Session):
    sub_count = db.query(m.Subscription).filter(m.Subscription.customer_id == customer.id).count()
    address = next((a for a in customer.addresses if a.address_type == "BILLING" and a.is_default), None)
    if not address:
        address = next((a for a in customer.addresses if a.address_type == "BILLING"), None)
    location = ", ".join(x for x in [address.city, address.state] if x) if address else "—"
    return {"id": str(customer.id), "customer_code": customer.customer_code,
            "company_name": customer.company_name, "name": customer.company_name,
            "billing_email": customer.billing_email, "email": customer.billing_email or "",
            "contact_person": customer.contact_person, "contact": customer.contact_person or "—",
            "phone": customer.phone or "—", "industry": customer.industry or "—",
            "is_active": customer.is_active, "status": "Active" if customer.is_active else "Inactive",
            "subscriptions": sub_count, "location": location,
            "joined": customer.created_at.date().isoformat() if customer.created_at else "—",
            "revenue": "—"}


@router.get("/customers")
def list_customers(db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    if user.role in ("ADMIN", "STAFF"):
        rows = db.query(m.Customer).order_by(m.Customer.created_at.desc()).all()
    else:
        own = customer_of(db, user)
        rows = [own] if own else []
    return [customer_data(row, db) for row in rows]


@router.post("/customers", status_code=201)
def create_customer(body: CustomerInput, db: Session = Depends(get_db), user: m.User = Depends(staff_or_admin)):
    from uuid import uuid4
    customer = m.Customer(customer_code=f"CUS-{uuid4().hex[:10].upper()}", **body.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer_data(customer, db)


@router.patch("/customers/{customer_id}")
def update_customer(customer_id: UUID, body: CustomerInput, db: Session = Depends(get_db), user: m.User = Depends(staff_or_admin)):
    customer = db.get(m.Customer, customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(customer, key, value)
    db.commit()
    db.refresh(customer)
    return customer_data(customer, db)


def product_data(product: m.Product):
    variants = [f"{variant.attribute_name}: {variant.attribute_value} (+₹{variant.additional_price})"
                for variant in product.variants]
    return {"id": str(product.id), "name": product.name, "type": product.product_type,
            "product_type": product.product_type, "sales_price": product.sales_price,
            "cost_price": product.cost_price, "sales": f"₹{product.sales_price:,.2f}",
            "cost": f"₹{product.cost_price:,.2f}", "variants": ", ".join(variants) or "None",
            "is_active": product.is_active, "status": "Active" if product.is_active else "Inactive"}


@router.get("/products")
def list_products(db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    return [product_data(product) for product in db.query(m.Product).order_by(m.Product.name).all()]


@router.post("/products", status_code=201)
def create_product(body: ProductInput, db: Session = Depends(get_db), user: m.User = Depends(staff_or_admin)):
    product = m.Product(**body.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product_data(product)
