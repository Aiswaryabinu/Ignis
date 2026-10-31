import secrets, hashlib, os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Literal
from fastapi import FastAPI, Depends, HTTPException, Request, Query, Response
from collections import defaultdict
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select, func, or_, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload, joinedload, contains_eager
from . import models as m, services as s
from .printing import invoice_html
from . import queries as Q
from .queries import Page
from . import config
from .config import CORS_ORIGINS, SCHEDULER_ENABLED, APP_BASE_URL
from .ratelimit import limiter, client_ip
from . import worker
from .db import get_db, engine, Base
from .ddl import UP as DDL_UP
from .security import (hash_password, verify_password, password_problems, make_token, current_user,
                       staff_or_admin, admin_only, customer_of, burn_password_check)

app = FastAPI(title="Brightloop Subscription Management API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Total-Count"])
DEV_TOKENS = config.DEV_RETURN_TOKENS   # return reset/verify tokens in responses (development only; forced off by default in production)

@app.middleware("http")
async def security_headers(request: Request, call_next):
    r = await call_next(request)
    r.headers.setdefault("X-Content-Type-Options", "nosniff"); r.headers.setdefault("X-Frame-Options", "SAMEORIGIN"); r.headers.setdefault("Referrer-Policy", "same-origin")
    if config.ENVIRONMENT == "production": r.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return r

@app.exception_handler(IntegrityError)
async def integrity_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=409, content={"detail": "That conflicts with existing data (duplicate or still in use)."})

def init_db():
    Base.metadata.create_all(engine)
    with engine.begin() as c:
        for stmt in DDL_UP: c.execute(text(stmt))

def ip(req: Request):
    import ipaddress
    try: return str(ipaddress.ip_address(req.client.host)) if req.client else None
    except ValueError: return None
def get_or_404(db, model, id_):
    try: o = db.get(model, id_)
    except Exception: o = None
    if not o: raise HTTPException(404, f"{model.__name__} not found")
    return o
def f(x): return float(x) if x is not None else None

# =================== AUTH ===================
class RegisterIn(BaseModel):
    email: EmailStr; password: str; company_name: str = Field(min_length=1); full_name: Optional[str] = None
class LoginIn(BaseModel):
    email: EmailStr; password: str

def user_out(u: m.User, db=None):
    c = customer_of(db, u) if db and u.role == "CUSTOMER" else None
    return {"id": str(u.id), "email": u.email, "role": u.role, "full_name": u.full_name or u.email.split("@")[0],
            "email_verified": u.email_verified, "customer_id": str(c.id) if c else None, "company_name": c.company_name if c else None}

def issue_reset(db, u: m.User) -> str:
    """Create a single-use reset token (1 h) and queue the e-mail. The caller commits."""
    raw = secrets.token_urlsafe(32)
    db.add(m.PasswordResetToken(user_id=u.id, token_hash=hashlib.sha256(raw.encode()).hexdigest(), expires_at=datetime.now(timezone.utc) + timedelta(hours=1)))
    s.outbox(db, "auth.password_reset", "user", u.id, {"to": u.email, "name": u.full_name or u.email.split("@")[0], "link": f"{APP_BASE_URL}/#reset={raw}"})
    return raw

@app.post("/auth/register", status_code=201)
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    rk = f"register:{client_ip(request)}"; limiter.check(rk, config.REGISTER_MAX_PER_IP, 3600); limiter.hit(rk, 3600)
    probs = password_problems(body.password)
    if probs: raise HTTPException(422, "Password needs " + ", ".join(probs))
    if db.execute(select(m.User).where(func.lower(m.User.email) == body.email.lower())).first():
        raise HTTPException(409, "An account with this email already exists")
    u = m.User(email=body.email.lower(), password_hash=hash_password(body.password), role="CUSTOMER", full_name=body.full_name)
    db.add(u); db.flush()
    db.add(m.Customer(user_id=u.id, customer_code=s.next_number(db, "CUS"), company_name=body.company_name, billing_email=u.email, contact_person=body.full_name))
    raw = secrets.token_urlsafe(32)
    db.add(m.EmailVerificationToken(user_id=u.id, token_hash=hashlib.sha256(raw.encode()).hexdigest(), expires_at=datetime.now(timezone.utc) + timedelta(days=2)))
    s.outbox(db, "auth.verify_email", "user", u.id, {"to": u.email, "name": body.full_name or body.company_name, "link": f"{APP_BASE_URL}/#verify={raw}"})
    db.commit()
    out = {"token": make_token(u), "user": user_out(u, db)}
    if DEV_TOKENS: out["dev_verification_token"] = raw
    return out

@app.post("/auth/login")
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    addr, w = client_ip(request), config.LOGIN_WINDOW_SECONDS
    ek, ik = f"login:{body.email.lower()}:{addr}", f"login-ip:{addr}"
    limiter.check(ek, config.LOGIN_MAX_FAILURES, w); limiter.check(ik, config.LOGIN_MAX_FAILURES_PER_IP, w)   # 429 + Retry-After after too many wrong passwords
    u = db.execute(select(m.User).where(m.User.email == body.email.lower())).scalar_one_or_none()
    if not u: burn_password_check(body.password)
    if not u or not verify_password(body.password, u.password_hash):
        limiter.hit(ek, w); limiter.hit(ik, w); raise HTTPException(401, "Wrong email or password")
    if not u.is_active: raise HTTPException(403, "This account is disabled")
    limiter.reset(ek)
    return {"token": make_token(u), "user": user_out(u, db)}

@app.get("/auth/me")
def me(u: m.User = Depends(current_user), db: Session = Depends(get_db)): return user_out(u, db)

class ProfileIn(BaseModel): full_name: str = Field(min_length=1, max_length=255)
@app.put("/auth/me")
def update_me(body: ProfileIn, request: Request, u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    old = u.full_name; u.full_name = body.full_name.strip()
    s.audit(db, u, "user.profile_updated", "user", u.id, {"full_name": old}, {"full_name": u.full_name}, ip(request)); db.commit()
    return user_out(u, db)

class ChangePwIn(BaseModel): current_password: str; new_password: str
@app.post("/auth/change-password")
def change_password(body: ChangePwIn, request: Request, u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    """Changing the password ends every other session (their tokens carry the old password stamp); the reply carries a fresh token."""
    key, w = f"chpw:{u.id}", config.LOGIN_WINDOW_SECONDS
    limiter.check(key, config.LOGIN_MAX_FAILURES, w)
    if not verify_password(body.current_password, u.password_hash): limiter.hit(key, w); raise HTTPException(400, "The current password is wrong")
    probs = password_problems(body.new_password)
    if probs: raise HTTPException(422, "Password needs " + ", ".join(probs))
    if body.new_password == body.current_password: raise HTTPException(422, "Choose a password different from the current one")
    u.password_hash = hash_password(body.new_password); s.audit(db, u, "user.password_changed", "user", u.id, ip=ip(request)); db.commit()
    limiter.reset(key); return {"ok": True, "token": make_token(u)}

class TokenIn(BaseModel): token: str
@app.post("/auth/verify-email")
def verify_email(body: TokenIn, db: Session = Depends(get_db)):
    h = hashlib.sha256(body.token.encode()).hexdigest()
    t = db.execute(select(m.EmailVerificationToken).where(m.EmailVerificationToken.token_hash == h)).scalar_one_or_none()
    if not t or t.verified_at or t.expires_at < datetime.now(timezone.utc): raise HTTPException(400, "Invalid or expired token")
    t.verified_at = datetime.now(timezone.utc); db.get(m.User, t.user_id).email_verified = True; db.commit()
    return {"ok": True}

class ForgotIn(BaseModel): email: EmailStr
@app.post("/auth/forgot-password")
def forgot(body: ForgotIn, request: Request, db: Session = Depends(get_db)):
    rk = f"forgot:{body.email.lower()}:{client_ip(request)}"      # counted whether or not the address exists, so the reply never leaks it
    limiter.check(rk, config.RESET_MAX_REQUESTS, config.LOGIN_WINDOW_SECONDS); limiter.hit(rk, config.LOGIN_WINDOW_SECONDS)
    u = db.execute(select(m.User).where(m.User.email == body.email.lower())).scalar_one_or_none()
    out = {"message": "If that email is registered, a reset link has been sent."}
    if u:
        raw = issue_reset(db, u); db.commit()
        if DEV_TOKENS: out["dev_reset_token"] = raw
    return out

class ResetIn(BaseModel): token: str; password: str
@app.post("/auth/reset-password")
def reset(body: ResetIn, db: Session = Depends(get_db)):
    probs = password_problems(body.password)
    if probs: raise HTTPException(422, "Password needs " + ", ".join(probs))
    h = hashlib.sha256(body.token.encode()).hexdigest()
    t = db.execute(select(m.PasswordResetToken).where(m.PasswordResetToken.token_hash == h).with_for_update()).scalar_one_or_none()
    if not t or t.used_at or t.expires_at < datetime.now(timezone.utc): raise HTTPException(400, "Invalid, used or expired token")
    t.used_at = datetime.now(timezone.utc); db.get(m.User, t.user_id).password_hash = hash_password(body.password); db.commit()
    return {"ok": True}

# =================== USERS (team) ===================
class StaffIn(BaseModel): email: EmailStr; password: str; full_name: str; role: str = "STAFF"
def team_out(u: m.User):
    return {"id": str(u.id), "name": u.full_name or u.email, "full_name": u.full_name, "email": u.email, "role": u.role.title(),
            "status": "Active" if u.is_active else "Inactive", "email_verified": u.email_verified, "created_at": u.created_at.isoformat() if u.created_at else None}
@app.get("/users")
def users(response: Response, pg: Page = Depends(), q: Optional[str] = None, role: Optional[str] = None, status: Optional[str] = None,
          _: m.User = Depends(admin_only), db: Session = Depends(get_db)):
    qry = select(m.User).where(m.User.role.in_(["ADMIN", "STAFF"]))
    if q: qry = qry.where(Q.search(q, m.User.email, m.User.full_name))
    if role:
        if Q.norm(role) not in ("ADMIN", "STAFF"): raise HTTPException(422, "Role must be Admin or Staff")
        qry = qry.where(m.User.role == Q.norm(role))
    if status: qry = qry.where(m.User.is_active == Q.flag(status, "active", "inactive"))
    return [team_out(u) for u in db.execute(Q.paginate(db, qry, response, pg).order_by(m.User.created_at, m.User.id)).scalars()]
@app.post("/users", status_code=201)
def create_staff(body: StaffIn, request: Request, a: m.User = Depends(admin_only), db: Session = Depends(get_db)):
    if body.role not in ("STAFF", "ADMIN"): raise HTTPException(422, "Role must be STAFF or ADMIN")
    probs = password_problems(body.password)
    if probs: raise HTTPException(422, "Password needs " + ", ".join(probs))
    if db.execute(select(m.User.id).where(m.User.email == body.email.lower())).first(): raise HTTPException(409, "Email already in use")
    u = m.User(email=body.email.lower(), password_hash=hash_password(body.password), role=body.role, full_name=body.full_name, email_verified=True)
    db.add(u); db.flush(); s.audit(db, a, "user.created", "user", u.id, None, {"email": u.email, "role": u.role}, ip(request)); db.commit()
    return {"id": str(u.id)}

class UserPatch(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255); role: Optional[Literal["STAFF", "ADMIN"]] = None
def team_user(db, uid) -> m.User:
    u = get_or_404(db, m.User, uid)
    if u.role not in ("ADMIN", "STAFF"): raise HTTPException(404, "User not found")      # customers are managed from their customer record
    return u
def keep_one_admin(db, target: m.User):
    """About to demote/disable `target`: refuse if that would leave no active admin."""
    if target.role == "ADMIN" and target.is_active:
        others = db.execute(select(m.User.id).where(m.User.role == "ADMIN", m.User.is_active, m.User.id != target.id).with_for_update()).all()
        if not others: raise HTTPException(409, "This is the only active admin. Make someone else an admin first.")
@app.put("/users/{uid}")
def update_user(uid: str, body: UserPatch, request: Request, a: m.User = Depends(admin_only), db: Session = Depends(get_db)):
    u = team_user(db, uid); old = {"full_name": u.full_name, "role": u.role}
    if body.role and body.role != u.role:
        if u.id == a.id: raise HTTPException(409, "You cannot change your own role")
        keep_one_admin(db, u); u.role = body.role
    if body.full_name is not None: u.full_name = body.full_name.strip()
    s.audit(db, a, "user.updated", "user", u.id, old, {"full_name": u.full_name, "role": u.role}, ip(request)); db.commit(); return team_out(u)
@app.post("/users/{uid}/{action}")
def user_action(uid: str, action: str, request: Request, a: m.User = Depends(admin_only), db: Session = Depends(get_db)):
    """activate | deactivate | reset-password (e-mails the person a reset link)."""
    if action not in ("activate", "deactivate", "reset-password"): raise HTTPException(404, "Unknown action")
    u = team_user(db, uid); out = None
    if action == "deactivate":
        if u.id == a.id: raise HTTPException(409, "You cannot deactivate your own account")
        keep_one_admin(db, u); u.is_active = False       # their tokens stop working at once (checked on every request)
    elif action == "activate": u.is_active = True
    else:
        raw = issue_reset(db, u); out = raw
    s.audit(db, a, {"activate": "user.activated", "deactivate": "user.deactivated", "reset-password": "user.password_reset_requested"}[action], "user", u.id, None, None, ip(request)); db.commit()
    res = team_out(u)
    if out and DEV_TOKENS: res["dev_reset_token"] = out
    return res

# =================== CUSTOMERS ===================
class AddressIn(BaseModel):
    address_type: Literal["BILLING", "SHIPPING"] = "BILLING"; address_line1: str = Field(min_length=1, max_length=255); address_line2: Optional[str] = None; city: str = Field(min_length=1, max_length=100)
    state: Optional[str] = None; postal_code: Optional[str] = None; country: str = Field("India", min_length=1, max_length=100); is_default: bool = False
    @field_validator("address_type", mode="before")
    @classmethod
    def _upper(cls, v): return v.strip().upper() if isinstance(v, str) else v
class CustomerIn(BaseModel):
    company_name: str = Field(min_length=1); contact_person: Optional[str] = None; phone: Optional[str] = None
    billing_email: Optional[str] = None; tax_identifier: Optional[str] = None; industry: Optional[str] = None
    is_active: bool = True; address: Optional[AddressIn] = None

def addr_out(a: m.CustomerAddress):
    return {"id": str(a.id), "type": a.address_type, "line1": a.address_line1, "line2": a.address_line2, "city": a.city, "state": a.state,
            "postal_code": a.postal_code, "country": a.country, "is_default": a.is_default}

def customer_counts(db, ids):
    """Open subscriptions per customer for a whole page in one query."""
    return dict(db.execute(select(m.Subscription.customer_id, func.count()).where(m.Subscription.customer_id.in_(ids), m.Subscription.status != "CLOSED")
                           .group_by(m.Subscription.customer_id)).all()) if ids else {}
def customer_out(c: m.Customer, db, counts=None):
    n = counts.get(c.id, 0) if counts is not None else db.execute(select(func.count()).select_from(m.Subscription).where(m.Subscription.customer_id == c.id, m.Subscription.status != "CLOSED")).scalar()
    return {"id": str(c.id), "code": c.customer_code, "name": c.company_name, "contact_person": c.contact_person, "phone": c.phone,
            "email": c.billing_email, "tax_identifier": c.tax_identifier, "industry": c.industry, "subscriptions": n,
            "status": "Active" if c.is_active else "Inactive",
            "addresses": [addr_out(a) for a in c.addresses]}

@app.get("/customers")
def customers(response: Response, pg: Page = Depends(), q: Optional[str] = None, status: Optional[str] = None, u: m.User = Depends(current_user), db: Session = Depends(get_db)):
    qry = select(m.Customer)
    if u.role == "CUSTOMER": qry = qry.where(m.Customer.user_id == u.id)
    if q: qry = qry.where(Q.search(q, m.Customer.company_name, m.Customer.customer_code, m.Customer.billing_email, m.Customer.contact_person))
    if status: qry = qry.where(m.Customer.is_active == Q.flag(status, "active", "inactive"))
    qry = Q.paginate(db, qry, response, pg).order_by(m.Customer.created_at.desc(), m.Customer.id).options(selectinload(m.Customer.addresses))
    rows = db.execute(qry).scalars().all(); counts = customer_counts(db, [c.id for c in rows])
    return [customer_out(c, db, counts) for c in rows]

def open_subscription_count(db, cid) -> int:
    return db.execute(select(func.count()).select_from(m.Subscription).where(m.Subscription.customer_id == cid, m.Subscription.status != "CLOSED")).scalar()
def ensure_deactivatable(db, c: m.Customer):
    n = open_subscription_count(db, c.id)
    if n: raise HTTPException(409, f"{c.company_name} still has {n} open subscription{'s' if n != 1 else ''}. Close them before deactivating the customer.")

def apply_customer(c, body: CustomerIn, db):
    if c.is_active and not body.is_active: ensure_deactivatable(db, c)
    for k in ("company_name", "contact_person", "phone", "billing_email", "tax_identifier", "industry", "is_active"): setattr(c, k, getattr(body, k))
    if body.address:
        c.addresses.clear(); db.flush()
        c.addresses.append(m.CustomerAddress(**body.address.model_dump()))

@app.post("/customers", status_code=201)
def create_customer(body: CustomerIn, request: Request, a=Depends(staff_or_admin), db: Session = Depends(get_db)):
    c = m.Customer(customer_code=s.next_number(db, "CUS"), company_name=body.company_name); db.add(c); apply_customer(c, body, db); db.flush()
    s.audit(db, a, "customer.created", "customer", c.id, None, {"name": c.company_name}, ip(request)); db.commit(); db.refresh(c)
    return customer_out(c, db)
@app.put("/customers/{cid}")
def update_customer(cid: str, body: CustomerIn, a=Depends(staff_or_admin), db: Session = Depends(get_db)):
    c = get_or_404(db, m.Customer, cid); apply_customer(c, body, db); s.audit(db, a, "customer.updated", "customer", c.id); db.commit()
    return customer_out(c, db)

# ---- customer addresses (staff/admin for any customer; a customer for their own). Tax lookup reads the default BILLING address. ----
def customer_for(db, u, cid) -> m.Customer:
    c = get_or_404(db, m.Customer, cid); check_own_customer(db, u, c.id); return c
def fix_defaults(db, cid, address_type):
    """Exactly one default per customer and address type, as long as there is at least one address of that type."""
    db.flush()
    rows = db.execute(select(m.CustomerAddress).where(m.CustomerAddress.customer_id == cid, m.CustomerAddress.address_type == address_type)
                      .order_by(m.CustomerAddress.created_at, m.CustomerAddress.id)).scalars().all()
    if rows and not any(r.is_default for r in rows): rows[0].is_default = True
def make_default(db, a: m.CustomerAddress):
    for o in db.execute(select(m.CustomerAddress).where(m.CustomerAddress.customer_id == a.customer_id, m.CustomerAddress.address_type == a.address_type,
                                                        m.CustomerAddress.id != a.id, m.CustomerAddress.is_default)).scalars(): o.is_default = False
    db.flush(); a.is_default = True      # unset first: the database allows one default per customer and type
def own_address(db, c, aid) -> m.CustomerAddress:
    a = get_or_404(db, m.CustomerAddress, aid)
    if a.customer_id != c.id: raise HTTPException(404, "CustomerAddress not found")
    return a
@app.get("/customers/{cid}/addresses")
def list_addresses(cid: str, u=Depends(current_user), db: Session = Depends(get_db)):
    c = customer_for(db, u, cid)
    return [addr_out(a) for a in db.execute(select(m.CustomerAddress).where(m.CustomerAddress.customer_id == c.id).order_by(m.CustomerAddress.created_at, m.CustomerAddress.id)).scalars()]
@app.post("/customers/{cid}/addresses", status_code=201)
def add_address(cid: str, body: AddressIn, request: Request, u=Depends(current_user), db: Session = Depends(get_db)):
    c = customer_for(db, u, cid)
    first_of_type = not db.execute(select(m.CustomerAddress.id).where(m.CustomerAddress.customer_id == c.id, m.CustomerAddress.address_type == body.address_type).limit(1)).first()
    a = m.CustomerAddress(customer_id=c.id, is_default=False, **body.model_dump(exclude={"is_default"})); db.add(a); db.flush()
    if body.is_default or first_of_type: make_default(db, a)
    s.audit(db, u, "customer.address_added", "customer", c.id, None, {"type": a.address_type, "city": a.city}, ip(request)); db.commit(); return addr_out(a)
@app.put("/customers/{cid}/addresses/{aid}")
def update_address(cid: str, aid: str, body: AddressIn, request: Request, u=Depends(current_user), db: Session = Depends(get_db)):
    c = customer_for(db, u, cid); a = own_address(db, c, aid); old_type = a.address_type
    old = {"type": a.address_type, "line1": a.address_line1, "city": a.city, "state": a.state, "country": a.country}
    for k, v in body.model_dump(exclude={"is_default"}).items(): setattr(a, k, v)
    if a.address_type != old_type: a.is_default = False
    if body.is_default: make_default(db, a)
    elif a.is_default: a.is_default = False
    for t in {old_type, a.address_type}: fix_defaults(db, c.id, t)       # un-ticking the only default keeps it default
    s.audit(db, u, "customer.address_updated", "customer", c.id, old, {"type": a.address_type, "line1": a.address_line1, "city": a.city, "state": a.state, "country": a.country}, ip(request))
    db.commit(); db.refresh(a); return addr_out(a)
@app.delete("/customers/{cid}/addresses/{aid}")
def delete_address(cid: str, aid: str, request: Request, u=Depends(current_user), db: Session = Depends(get_db)):
    c = customer_for(db, u, cid); a = own_address(db, c, aid); t = a.address_type
    s.audit(db, u, "customer.address_deleted", "customer", c.id, {"type": t, "city": a.city}, None, ip(request)); db.delete(a); fix_defaults(db, c.id, t); db.commit()
    return {"ok": True}
@app.post("/customers/{cid}/{action}")
def customer_action(cid: str, action: str, request: Request, a=Depends(staff_or_admin), db: Session = Depends(get_db)):
    """activate | deactivate (a customer with open subscriptions cannot be deactivated)."""
    if action not in ("activate", "deactivate"): raise HTTPException(404, "Unknown action")
    c = get_or_404(db, m.Customer, cid)
    if action == "deactivate" and c.is_active: ensure_deactivatable(db, c)
    c.is_active = action == "activate"; s.audit(db, a, f"customer.{action}d", "customer", c.id, None, None, ip(request)); db.commit()
    return customer_out(c, db)

# =================== PRODUCTS ===================
class VariantIn(BaseModel): attribute_name: str; attribute_value: str; additional_price: Decimal = Decimal(0); is_active: bool = True
class ProductIn(BaseModel):
    name: str = Field(min_length=1); product_type: str; sales_price: Decimal = Field(ge=0); cost_price: Decimal = Field(ge=0)
    notes: Optional[str] = None; is_active: bool = True; variants: list[VariantIn] = []

def product_out(p: m.Product):
    vs = [v for v in p.variants if v.is_active]
    return {"id": str(p.id), "name": p.name, "type": p.product_type, "sales": f(p.sales_price), "cost": f(p.cost_price), "notes": p.notes,
            "variants": ", ".join(f"{v.attribute_name}: {v.attribute_value} (+₹{v.additional_price:,.0f})" for v in vs) or "None",
            "variant_list": [{"id": str(v.id), "label": f"{v.attribute_name}: {v.attribute_value}", "additional_price": f(v.additional_price)} for v in vs],
            "status": "Active" if p.is_active else "Inactive"}

@app.get("/products")
def products(response: Response, pg: Page = Depends(), q: Optional[str] = None, status: Optional[str] = None, product_type: Optional[str] = None,
             u=Depends(current_user), db: Session = Depends(get_db)):
    qry = select(m.Product)
    if q: qry = qry.where(Q.search(q, m.Product.name, m.Product.product_type))
    if product_type: qry = qry.where(m.Product.product_type.ilike(product_type))
    if status: qry = qry.where(m.Product.is_active == Q.flag(status, "active", "inactive"))
    qry = Q.paginate(db, qry, response, pg).order_by(m.Product.created_at.desc(), m.Product.id).options(selectinload(m.Product.variants))
    return [product_out(p) for p in db.execute(qry).scalars().all()]
@app.post("/products", status_code=201)
def create_product(body: ProductIn, request: Request, a=Depends(staff_or_admin), db: Session = Depends(get_db)):
    p = m.Product(**body.model_dump(exclude={"variants"})); db.add(p)
    for v in body.variants: p.variants.append(m.ProductVariant(**v.model_dump()))
    db.flush(); s.audit(db, a, "product.created", "product", p.id, None, {"name": p.name, "sales_price": str(p.sales_price)}, ip(request)); db.commit(); db.refresh(p)
    return product_out(p)
@app.put("/products/{pid}")
def update_product(pid: str, body: ProductIn, request: Request, a=Depends(staff_or_admin), db: Session = Depends(get_db)):
    p = get_or_404(db, m.Product, pid); old = {"sales_price": str(p.sales_price), "cost_price": str(p.cost_price)}
    for k, v in body.model_dump(exclude={"variants"}).items(): setattr(p, k, v)
    if body.variants:   # replace variants; existing subscription lines keep their own snapshot
        for v in list(p.variants): v.is_active = False
        for v in body.variants: p.variants.append(m.ProductVariant(**v.model_dump()))
    s.audit(db, a, "product.updated", "product", p.id, old, {"sales_price": str(p.sales_price), "cost_price": str(p.cost_price)}, ip(request)); db.commit(); db.refresh(p)
    return product_out(p)

# =================== PLANS ===================
class PlanIn(BaseModel):
    name: str = Field(min_length=1); description: Optional[str] = None; product_id: Optional[str] = None
    billing_interval: str; interval_count: int = Field(1, ge=1); minimum_quantity: int = Field(1, ge=1); price: Decimal = Field(ge=0)
    start_date: date = Field(default_factory=date.today); end_date: Optional[date] = None
    auto_close: bool = False; allow_early_close: bool = True; allow_pause: bool = True; allow_renewal: bool = True; is_active: bool = True

def plan_out(p: m.SubscriptionPlan):
    return {"id": str(p.id), "name": p.name, "product": p.product.name if p.product else "—", "product_id": str(p.product_id) if p.product_id else None,
            "billing": p.billing_interval.title(), "interval_count": p.interval_count, "price": f(p.price), "minqty": p.minimum_quantity,
            "renewal": "Automatic" if p.allow_renewal else "Manual", "allow_pause": p.allow_pause, "allow_early_close": p.allow_early_close,
            "allow_renewal": p.allow_renewal, "auto_close": p.auto_close, "start_date": str(p.start_date), "end_date": str(p.end_date) if p.end_date else None,
            "status": "Active" if p.is_active else "Draft"}
@app.get("/plans")
def plans(response: Response, pg: Page = Depends(), q: Optional[str] = None, status: Optional[str] = None, billing_interval: Optional[str] = None,
          u=Depends(current_user), db: Session = Depends(get_db)):
    qry = select(m.SubscriptionPlan)
    if q: qry = qry.where(Q.search(q, m.SubscriptionPlan.name))
    if billing_interval: qry = qry.where(m.SubscriptionPlan.billing_interval == Q.norm(billing_interval))
    if status: qry = qry.where(m.SubscriptionPlan.is_active == Q.flag(status, "active", "draft"))
    qry = Q.paginate(db, qry, response, pg).order_by(m.SubscriptionPlan.created_at.desc(), m.SubscriptionPlan.id).options(joinedload(m.SubscriptionPlan.product))
    return [plan_out(p) for p in db.execute(qry).scalars().all()]
def plan_data(body: PlanIn):
    if body.billing_interval.upper() not in ("DAILY", "WEEKLY", "MONTHLY", "YEARLY"): raise HTTPException(422, "Billing interval must be Daily, Weekly, Monthly or Yearly")
    if body.end_date and body.end_date < body.start_date: raise HTTPException(422, "End date is before start date")
    d = body.model_dump(); d["billing_interval"] = body.billing_interval.upper(); return d
@app.post("/plans", status_code=201)
def create_plan(body: PlanIn, a=Depends(admin_only), db: Session = Depends(get_db)):
    p = m.SubscriptionPlan(**plan_data(body)); db.add(p); db.flush(); s.audit(db, a, "plan.created", "plan", p.id, None, {"name": p.name}); db.commit(); db.refresh(p)
    return plan_out(p)
@app.put("/plans/{pid}")
def update_plan(pid: str, body: PlanIn, a=Depends(admin_only), db: Session = Depends(get_db)):
    p = get_or_404(db, m.SubscriptionPlan, pid)
    for k, v in plan_data(body).items(): setattr(p, k, v)
    s.audit(db, a, "plan.updated", "plan", p.id); db.commit(); db.refresh(p); return plan_out(p)   # existing subscriptions keep their own lines/prices

# =================== TAXES ===================
class TaxIn(BaseModel):
    name: str = Field(min_length=1, max_length=100); rate: Decimal = Field(ge=0); tax_type: str = "PERCENTAGE"; is_inclusive: bool = False; effective_from: date = Field(default_factory=date.today)
    effective_until: Optional[date] = None; product_id: Optional[str] = None; country: Optional[str] = None; state: Optional[str] = None; priority: int = 0
class TaxUpdate(BaseModel):
    """Partial update of the tax itself (where it applies is edited through the rules). Existing quotations, subscriptions and invoices keep their snapshot."""
    name: Optional[str] = Field(None, min_length=1, max_length=100); rate: Optional[Decimal] = Field(None, ge=0); tax_type: Optional[str] = None; is_inclusive: Optional[bool] = None
    effective_from: Optional[date] = None; effective_until: Optional[date] = None; is_active: Optional[bool] = None
class RuleIn(BaseModel):
    product_id: Optional[str] = None; country: Optional[str] = None; state: Optional[str] = None; priority: int = Field(0, ge=0, le=1000); is_active: bool = True
    @field_validator("product_id", "country", "state", mode="before")
    @classmethod
    def _blank_is_none(cls, v): return (v.strip() or None) if isinstance(v, str) else v

def check_tax(rate, tax_type, eff_from, eff_until):
    if tax_type not in ("PERCENTAGE", "FIXED"): raise HTTPException(422, "Type must be Percentage or Fixed")
    if tax_type == "PERCENTAGE" and rate > 100: raise HTTPException(422, "A percentage tax cannot exceed 100")
    if eff_until and eff_until < eff_from: raise HTTPException(422, "The end date is before the start date")
def rule_out(r: m.TaxRule, names):
    return {"id": str(r.id), "product_id": str(r.product_id) if r.product_id else None, "product": names.get(r.product_id) if r.product_id else "All products",
            "country": r.country, "state": r.state, "priority": r.priority, "is_active": r.is_active}
def taxes_out(db, rows):
    rules = defaultdict(list)
    if rows:
        for r in db.execute(select(m.TaxRule).where(m.TaxRule.tax_id.in_([t.id for t in rows])).order_by(m.TaxRule.priority.desc(), m.TaxRule.id)).scalars(): rules[r.tax_id].append(r)
    pids = {r.product_id for rs in rules.values() for r in rs if r.product_id}
    names = dict(db.execute(select(m.Product.id, m.Product.name).where(m.Product.id.in_(pids))).all()) if pids else {}
    return [{"id": str(t.id), "name": t.name, "rate": f(t.rate), "type": t.tax_type.title(), "inclusive": t.is_inclusive,
             "from": str(t.effective_from), "until": str(t.effective_until) if t.effective_until else "—",
             "from_iso": str(t.effective_from), "until_iso": str(t.effective_until) if t.effective_until else None, "is_active": t.is_active,
             "applies": "; ".join(", ".join(filter(None, [names.get(r.product_id) if r.product_id else "All products", r.country, r.state])) for r in rules[t.id]) or "All",
             "rules": [rule_out(r, names) for r in rules[t.id]],
             "status": "Active" if t.is_active else "Inactive"} for t in rows]
@app.get("/taxes")
def taxes(response: Response, pg: Page = Depends(), q: Optional[str] = None, status: Optional[str] = None, u=Depends(staff_or_admin), db: Session = Depends(get_db)):
    qry = select(m.Tax)
    if q: qry = qry.where(Q.search(q, m.Tax.name))
    if status: qry = qry.where(m.Tax.is_active == Q.flag(status, "active", "inactive"))
    return taxes_out(db, db.execute(Q.paginate(db, qry, response, pg).order_by(m.Tax.created_at.desc(), m.Tax.id)).scalars().all())
@app.get("/taxes/{tid}")
def tax_detail(tid: str, u=Depends(staff_or_admin), db: Session = Depends(get_db)): return taxes_out(db, [get_or_404(db, m.Tax, tid)])[0]
@app.post("/taxes", status_code=201)
def create_tax(body: TaxIn, a=Depends(admin_only), db: Session = Depends(get_db)):
    ttype = body.tax_type.upper(); check_tax(body.rate, ttype, body.effective_from, body.effective_until)
    pid = Q.to_uuid(body.product_id, "product_id")
    if pid: get_or_404(db, m.Product, pid)
    t = m.Tax(name=body.name, rate=body.rate, tax_type=ttype, is_inclusive=body.is_inclusive, effective_from=body.effective_from, effective_until=body.effective_until)
    db.add(t); db.flush()
    db.add(m.TaxRule(tax_id=t.id, product_id=pid, country=(body.country or None), state=(body.state or None), priority=body.priority))
    s.audit(db, a, "tax.created", "tax", t.id, None, {"name": t.name, "rate": str(t.rate)}); db.commit(); return taxes_out(db, [t])[0]
@app.put("/taxes/{tid}")
def update_tax(tid: str, body: TaxUpdate, a=Depends(admin_only), db: Session = Depends(get_db)):
    t = get_or_404(db, m.Tax, tid); old = {"name": t.name, "rate": str(t.rate), "type": t.tax_type, "inclusive": t.is_inclusive, "from": str(t.effective_from),
                                          "until": str(t.effective_until) if t.effective_until else None, "active": t.is_active}
    data = body.model_dump(exclude_unset=True)
    if data.get("tax_type"): data["tax_type"] = data["tax_type"].upper()
    for k in ("name", "rate", "tax_type", "is_inclusive", "effective_from", "is_active"):
        if k in data and data[k] is not None: setattr(t, k, data[k])
    if "effective_until" in data: t.effective_until = data["effective_until"]          # null clears it
    check_tax(t.rate, t.tax_type, t.effective_from, t.effective_until)
    s.audit(db, a, "tax.updated", "tax", t.id, old, {"name": t.name, "rate": str(t.rate), "type": t.tax_type, "inclusive": t.is_inclusive, "from": str(t.effective_from),
                                                      "until": str(t.effective_until) if t.effective_until else None, "active": t.is_active}); db.commit()
    return taxes_out(db, [t])[0]
@app.get("/taxes/{tid}/rules")
def tax_rules(tid: str, u=Depends(staff_or_admin), db: Session = Depends(get_db)): return taxes_out(db, [get_or_404(db, m.Tax, tid)])[0]["rules"]

def rule_values(db, tid, body: RuleIn, exclude=None):
    pid = Q.to_uuid(body.product_id, "product_id")
    if pid: get_or_404(db, m.Product, pid)
    eq = lambda col, v: col.is_(None) if v is None else col == v
    dup = select(m.TaxRule.id).where(m.TaxRule.tax_id == tid, eq(m.TaxRule.product_id, pid), eq(m.TaxRule.country, body.country), eq(m.TaxRule.state, body.state))
    if exclude: dup = dup.where(m.TaxRule.id != exclude)
    if db.execute(dup.limit(1)).first(): raise HTTPException(409, "This tax already has a rule for that product, country and state")
    return {"product_id": pid, "country": body.country, "state": body.state, "priority": body.priority, "is_active": body.is_active}
def one_rule(db, t, rid) -> m.TaxRule:
    r = get_or_404(db, m.TaxRule, rid)
    if r.tax_id != t.id: raise HTTPException(404, "TaxRule not found")
    return r
@app.post("/taxes/{tid}/rules", status_code=201)
def add_tax_rule(tid: str, body: RuleIn, a=Depends(admin_only), db: Session = Depends(get_db)):
    t = get_or_404(db, m.Tax, tid); r = m.TaxRule(tax_id=t.id, **rule_values(db, t.id, body)); db.add(r); db.flush()
    s.audit(db, a, "tax.rule_added", "tax", t.id, None, {"country": r.country, "state": r.state, "product_id": str(r.product_id) if r.product_id else None}); db.commit()
    return next(x for x in taxes_out(db, [t])[0]["rules"] if x["id"] == str(r.id))
@app.put("/taxes/{tid}/rules/{rid}")
def update_tax_rule(tid: str, rid: str, body: RuleIn, a=Depends(admin_only), db: Session = Depends(get_db)):
    t = get_or_404(db, m.Tax, tid); r = one_rule(db, t, rid)
    for k, v in rule_values(db, t.id, body, exclude=r.id).items(): setattr(r, k, v)
    s.audit(db, a, "tax.rule_updated", "tax", t.id, None, {"rule": str(r.id)}); db.commit()
    return next(x for x in taxes_out(db, [t])[0]["rules"] if x["id"] == str(r.id))
@app.delete("/taxes/{tid}/rules/{rid}")
def delete_tax_rule(tid: str, rid: str, a=Depends(admin_only), db: Session = Depends(get_db)):
    t = get_or_404(db, m.Tax, tid); r = one_rule(db, t, rid)
    if db.execute(select(func.count()).select_from(m.TaxRule).where(m.TaxRule.tax_id == t.id)).scalar() <= 1:
        raise HTTPException(409, "A tax needs at least one rule. Deactivate the tax instead.")
    s.audit(db, a, "tax.rule_deleted", "tax", t.id, {"rule": str(r.id)}, None); db.delete(r); db.commit(); return {"ok": True}
@app.post("/taxes/{tid}/{action}")
def tax_action(tid: str, action: str, a=Depends(admin_only), db: Session = Depends(get_db)):
    """activate | deactivate. A deactivated tax is no longer applied to new quotations, subscriptions or invoices."""
    if action not in ("activate", "deactivate"): raise HTTPException(404, "Unknown action")
    t = get_or_404(db, m.Tax, tid); t.is_active = action == "activate"; s.audit(db, a, f"tax.{action}d", "tax", t.id); db.commit()
    return taxes_out(db, [t])[0]

# =================== DISCOUNTS ===================
class DiscountIn(BaseModel):
    code: str = Field(min_length=1, max_length=50); name: Optional[str] = None; discount_type: str; value: Decimal = Field(ge=0); min_purchase: Decimal = Field(Decimal(0), ge=0); min_quantity: int = Field(1, ge=1)
    start_date: datetime; end_date: Optional[datetime] = None; usage_limit: Optional[int] = Field(None, ge=1); scope: str = "SUBSCRIPTION"
    product_ids: list[str] = []; is_active: bool = True
class DiscountUpdate(BaseModel):
    """Partial update. end_date / usage_limit set to null remove the limit. Past usage is kept, and only future billing is affected."""
    code: Optional[str] = Field(None, min_length=1, max_length=50); name: Optional[str] = Field(None, min_length=1); discount_type: Optional[str] = None; value: Optional[Decimal] = Field(None, ge=0)
    min_purchase: Optional[Decimal] = Field(None, ge=0); min_quantity: Optional[int] = Field(None, ge=1); start_date: Optional[datetime] = None; end_date: Optional[datetime] = None
    usage_limit: Optional[int] = Field(None, ge=1); scope: Optional[str] = None; product_ids: Optional[list[str]] = None; is_active: Optional[bool] = None
def aware(dt):
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=timezone.utc)
def check_discount(d: m.Discount, n_products: int):
    if d.discount_type not in ("FIXED", "PERCENTAGE"): raise HTTPException(422, "Type must be Fixed or Percentage")
    if d.discount_type == "PERCENTAGE" and d.value > 100: raise HTTPException(422, "A percentage discount cannot exceed 100")
    if d.scope not in ("PRODUCT", "SUBSCRIPTION"): raise HTTPException(422, "Scope must be Product or Subscription")
    if d.scope == "PRODUCT" and not n_products: raise HTTPException(422, "Choose at least one product")
    if d.end_date and d.end_date < d.start_date: raise HTTPException(422, "The end date is before the start date")
    if d.usage_limit is not None and d.usage_limit < (d.usage_count or 0): raise HTTPException(422, f"This discount has already been used {d.usage_count} times, so the limit cannot be lower than that")
def discount_out(d: m.Discount):
    now = datetime.now(timezone.utc)
    st = "Draft" if not d.is_active else "Expired" if (d.end_date and d.end_date < now) or (d.usage_limit and d.usage_count >= d.usage_limit) else "Draft" if d.start_date > now else "Active"
    pv = lambda x: f"{x:g}%" if d.discount_type == "PERCENTAGE" else f"₹{x:,.0f}"
    return {"id": str(d.id), "code": d.code, "name": d.name, "type": d.discount_type.title(), "value": pv(d.value), "raw_value": f(d.value),
            "min": (f"₹{d.min_purchase:,.0f}" if d.min_purchase else "") + (f" / {d.min_quantity} seats" if d.min_quantity > 1 else "") or "—",
            "valid": f"{d.start_date:%d %b %Y} – {d.end_date:%d %b %Y}" if d.end_date else f"From {d.start_date:%d %b %Y}",
            "used": f"{d.usage_count} / {d.usage_limit}" if d.usage_limit else f"{d.usage_count} / ∞",
            "applies": ("Selected products" if d.scope == "PRODUCT" else "All subscriptions"), "scope": d.scope, "status": st,
            "is_active": d.is_active, "discount_type": d.discount_type, "start_iso": d.start_date.isoformat(), "end_iso": d.end_date.isoformat() if d.end_date else None,
            "usage_limit": d.usage_limit, "usage_count": d.usage_count, "min_purchase": f(d.min_purchase), "min_quantity": d.min_quantity,
            "product_ids": [str(x.product_id) for x in d.products]}
@app.get("/discounts")
def discounts(response: Response, pg: Page = Depends(), q: Optional[str] = None, u=Depends(staff_or_admin), db: Session = Depends(get_db)):
    qry = select(m.Discount)
    if q: qry = qry.where(Q.search(q, m.Discount.code, m.Discount.name))
    return [discount_out(d) for d in db.execute(Q.paginate(db, qry, response, pg).order_by(m.Discount.created_at.desc(), m.Discount.id).options(selectinload(m.Discount.products))).scalars().all()]
@app.get("/discounts/{did}")
def discount_detail(did: str, u=Depends(staff_or_admin), db: Session = Depends(get_db)): return discount_out(get_or_404(db, m.Discount, did))
def unique_code(db, code, exclude=None):
    q = select(m.Discount.id).where(func.upper(m.Discount.code) == code)
    if exclude: q = q.where(m.Discount.id != exclude)
    if db.execute(q.limit(1)).first(): raise HTTPException(409, f"The code {code} is already in use")
def set_discount_products(db, d, ids):
    d.products.clear(); db.flush()
    for pid in {Q.to_uuid(x, "product_id") for x in ids}:
        get_or_404(db, m.Product, pid); d.products.append(m.DiscountProduct(product_id=pid))
@app.post("/discounts", status_code=201)
def create_discount(body: DiscountIn, a=Depends(admin_only), db: Session = Depends(get_db)):
    code = body.code.strip().upper(); unique_code(db, code)
    d = m.Discount(code=code, name=body.name or code, discount_type=body.discount_type.upper(), value=body.value, min_purchase=body.min_purchase, min_quantity=body.min_quantity,
                   start_date=aware(body.start_date), end_date=aware(body.end_date), usage_limit=body.usage_limit, usage_count=0, scope=body.scope.upper(), is_active=body.is_active, created_by=a.id)
    check_discount(d, len(set(body.product_ids)))
    db.add(d); db.flush(); set_discount_products(db, d, body.product_ids)
    s.audit(db, a, "discount.created", "discount", d.id, None, {"code": d.code}); db.commit(); db.refresh(d); return discount_out(d)
def discount_snapshot(d): return {"code": d.code, "type": d.discount_type, "value": str(d.value), "scope": d.scope, "active": d.is_active, "usage_limit": d.usage_limit,
                                  "start": d.start_date.isoformat(), "end": d.end_date.isoformat() if d.end_date else None}
def locked_discount(db, did) -> m.Discount:
    try: d = db.execute(select(m.Discount).where(m.Discount.id == did).with_for_update()).scalar_one_or_none()     # same lock the billing run takes, so usage_count cannot change under us
    except Exception: d = None
    if not d: raise HTTPException(404, "Discount not found")
    return d
@app.put("/discounts/{did}")
def update_discount(did: str, body: DiscountUpdate, a=Depends(admin_only), db: Session = Depends(get_db)):
    d = locked_discount(db, did); old = discount_snapshot(d); data = body.model_dump(exclude_unset=True); pids = data.pop("product_ids", None)
    if data.get("code"):
        data["code"] = data["code"].strip().upper(); unique_code(db, data["code"], d.id)
    for k in ("discount_type", "scope"):
        if data.get(k): data[k] = data[k].upper()
    for k in ("code", "name", "discount_type", "value", "min_purchase", "min_quantity", "scope", "is_active"):
        if data.get(k) is not None: setattr(d, k, data[k])
    if data.get("start_date"): d.start_date = aware(data["start_date"])
    if "end_date" in data: d.end_date = aware(data["end_date"])
    if "usage_limit" in data: d.usage_limit = data["usage_limit"]
    n = len(set(pids)) if pids is not None else len(d.products)
    check_discount(d, n)
    if pids is not None: set_discount_products(db, d, pids)
    s.audit(db, a, "discount.updated", "discount", d.id, old, discount_snapshot(d)); db.commit(); db.refresh(d); return discount_out(d)
@app.post("/discounts/{did}/{action}")
def discount_action(did: str, action: str, a=Depends(admin_only), db: Session = Depends(get_db)):
    """activate | deactivate. A deactivated discount stops being applied to future invoices at once."""
    if action not in ("activate", "deactivate"): raise HTTPException(404, "Unknown action")
    d = locked_discount(db, did); d.is_active = action == "activate"; s.audit(db, a, f"discount.{action}d", "discount", d.id); db.commit(); db.refresh(d)
    return discount_out(d)

# =================== QUOTATIONS ===================
class TplLineIn(BaseModel): product_id: str; variant_id: Optional[str] = None; plan_id: str; default_quantity: int = Field(ge=1)
class TplIn(BaseModel): name: str; description: Optional[str] = None; validity_days: int = Field(gt=0); lines: list[TplLineIn] = Field(min_length=1)
def tpl_out(t: m.QuotationTemplate):
    return {"id": str(t.id), "template": t.name, "plan": ", ".join(sorted({l.plan.name for l in t.lines})), "lines": ", ".join(f"{l.product.name} × {l.default_quantity}" for l in t.lines),
            "validity": f"{t.validity_days} days", "validity_days": t.validity_days, "status": "Active" if t.is_active else "Draft",
            "line_data": [{"product_id": str(l.product_id), "variant_id": str(l.variant_id) if l.variant_id else None, "plan_id": str(l.plan_id), "quantity": l.default_quantity, "unit_price": f(l.default_unit_price)} for l in t.lines]}
TPL_LOAD = (selectinload(m.QuotationTemplate.lines).options(joinedload(m.QuotationTemplateLine.product), joinedload(m.QuotationTemplateLine.plan)),)
@app.get("/quotation-templates")
def templates(response: Response, pg: Page = Depends(), q: Optional[str] = None, status: Optional[str] = None, u=Depends(staff_or_admin), db: Session = Depends(get_db)):
    qry = select(m.QuotationTemplate)
    if q: qry = qry.where(Q.search(q, m.QuotationTemplate.name, m.QuotationTemplate.description))
    if status: qry = qry.where(m.QuotationTemplate.is_active == Q.flag(status, "active", "draft"))
    return [tpl_out(t) for t in db.execute(Q.paginate(db, qry, response, pg).order_by(m.QuotationTemplate.created_at.desc(), m.QuotationTemplate.id).options(*TPL_LOAD)).scalars().all()]
@app.get("/quotation-templates/{tid}")
def template_detail(tid: str, u=Depends(staff_or_admin), db: Session = Depends(get_db)): return tpl_out(get_or_404(db, m.QuotationTemplate, tid))
def fill_tpl_lines(db, t, lines):
    for l in lines:
        p = get_or_404(db, m.Product, l.product_id); v = get_or_404(db, m.ProductVariant, l.variant_id) if l.variant_id else None; pl = get_or_404(db, m.SubscriptionPlan, l.plan_id)
        if not p.is_active: raise HTTPException(409, f"{p.name} is inactive")
        if not pl.is_active: raise HTTPException(409, f"{pl.name} is not an active plan")
        if v and v.product_id != p.id: raise HTTPException(422, f"That variant does not belong to {p.name}")
        t.lines.append(m.QuotationTemplateLine(product_id=p.id, variant_id=v.id if v else None, plan_id=pl.id, default_quantity=l.default_quantity, default_unit_price=s.unit_price_for(p, v)))
@app.post("/quotation-templates", status_code=201)
def create_template(body: TplIn, a=Depends(admin_only), db: Session = Depends(get_db)):
    t = m.QuotationTemplate(name=body.name, description=body.description, validity_days=body.validity_days, created_by=a.id); db.add(t)
    fill_tpl_lines(db, t, body.lines)
    db.flush(); s.audit(db, a, "quotation_template.created", "quotation_template", t.id); db.commit(); db.refresh(t); return tpl_out(t)
class TplUpdate(BaseModel):
    """Partial update; `lines`, when sent, replaces all lines (prices are re-read from the products now). Quotations already made from the template are not touched."""
    name: Optional[str] = Field(None, min_length=1); description: Optional[str] = None; validity_days: Optional[int] = Field(None, gt=0); is_active: Optional[bool] = None
    lines: Optional[list[TplLineIn]] = Field(None, min_length=1)
@app.put("/quotation-templates/{tid}")
def update_template(tid: str, body: TplUpdate, a=Depends(admin_only), db: Session = Depends(get_db)):
    t = get_or_404(db, m.QuotationTemplate, tid); old = {"name": t.name, "validity_days": t.validity_days, "active": t.is_active}; data = body.model_dump(exclude_unset=True)
    for k in ("name", "validity_days", "is_active"):
        if data.get(k) is not None: setattr(t, k, data[k])
    if "description" in data: t.description = data["description"]
    if body.lines is not None:
        t.lines.clear(); db.flush(); fill_tpl_lines(db, t, body.lines)
    db.flush(); s.audit(db, a, "quotation_template.updated", "quotation_template", t.id, old, {"name": t.name, "validity_days": t.validity_days, "active": t.is_active, "lines": len(t.lines)})
    db.commit(); db.refresh(t); return tpl_out(t)
@app.post("/quotation-templates/{tid}/{action}")
def template_action(tid: str, action: str, a=Depends(admin_only), db: Session = Depends(get_db)):
    """activate | deactivate. A deactivated template cannot be used for new quotations."""
    if action not in ("activate", "deactivate"): raise HTTPException(404, "Unknown action")
    t = get_or_404(db, m.QuotationTemplate, tid); t.is_active = action == "activate"; s.audit(db, a, f"quotation_template.{action}d", "quotation_template", t.id); db.commit(); db.refresh(t)
    return tpl_out(t)

class QLineIn(BaseModel): product_id: str; variant_id: Optional[str] = None; plan_id: str; quantity: int = Field(ge=1); unit_price: Optional[Decimal] = None; discount_amount: Decimal = Decimal(0)
class QuoteIn(BaseModel): customer_id: str; template_id: Optional[str] = None; lines: list[QLineIn] = []; valid_days: Optional[int] = None
def quote_out(qt: m.Quotation, db, subs=None):
    sub_no = subs.get(qt.id) if subs is not None else db.execute(select(m.Subscription.subscription_number).where(m.Subscription.quotation_id == qt.id)).scalar_one_or_none()
    st = "EXPIRED" if qt.status in ("DRAFT", "SENT") and qt.valid_until < date.today() else qt.status
    return {"id": str(qt.id), "number": qt.quotation_number, "customer": qt.customer.company_name, "customer_id": str(qt.customer_id), "issue": str(qt.issue_date), "valid_until": str(qt.valid_until),
            "lines": ", ".join(f"{l.product_name} × {l.quantity}" for l in qt.lines), "subtotal": f(qt.subtotal), "discount": f(qt.discount_total), "tax": f(qt.tax_total),
            "total": f(qt.grand_total), "status": st.title(), "subscription": sub_no,
            "line_data": [{"product": l.product_name, "variant": l.variant_name, "quantity": l.quantity, "unit_price": f(l.unit_price), "tax": f(l.tax_amount), "total": f(l.line_total)} for l in qt.lines]}
def scope_customer(db, u, q, col):
    if u.role == "CUSTOMER":
        c = customer_of(db, u); return q.where(col == (c.id if c else None))
    return q
@app.get("/quotations")
def quotations(response: Response, pg: Page = Depends(), q: Optional[str] = None, status: Optional[str] = None, customer_id: Optional[str] = None,
               issue_from: Optional[date] = None, issue_to: Optional[date] = None, u=Depends(current_user), db: Session = Depends(get_db)):
    qry = scope_customer(db, u, select(m.Quotation).join(m.Customer, m.Customer.id == m.Quotation.customer_id), m.Quotation.customer_id)
    if u.role == "CUSTOMER": qry = qry.where(m.Quotation.status != "DRAFT")
    if q: qry = qry.where(Q.search(q, m.Quotation.quotation_number, m.Customer.company_name))
    if status: qry = qry.where(Q.quotation_status_filter(status, date.today()))
    if customer_id: qry = qry.where(m.Quotation.customer_id == Q.to_uuid(customer_id, "customer_id"))
    qry = qry.where(*Q.between_dates(m.Quotation.issue_date, issue_from, issue_to))
    qry = Q.paginate(db, qry, response, pg).order_by(m.Quotation.created_at.desc(), m.Quotation.id).options(contains_eager(m.Quotation.customer), selectinload(m.Quotation.lines))
    rows = db.execute(qry).scalars().all()
    subs = dict(db.execute(select(m.Subscription.quotation_id, m.Subscription.subscription_number).where(m.Subscription.quotation_id.in_([x.id for x in rows]))).all()) if rows else {}
    return [quote_out(x, db, subs) for x in rows]
@app.post("/quotations", status_code=201)
def create_quotation(body: QuoteIn, a=Depends(staff_or_admin), db: Session = Depends(get_db)):
    cust = get_or_404(db, m.Customer, body.customer_id); tpl = get_or_404(db, m.QuotationTemplate, body.template_id) if body.template_id else None
    if not cust.is_active: raise HTTPException(409, f"{cust.company_name} is inactive")
    if tpl and not tpl.is_active: raise HTTPException(409, "That template is switched off")
    lines = body.lines
    if not lines and tpl:
        lines = [QLineIn(product_id=str(l.product_id), variant_id=str(l.variant_id) if l.variant_id else None, plan_id=str(l.plan_id), quantity=l.default_quantity, unit_price=l.default_unit_price) for l in tpl.lines]
    if not lines: raise HTTPException(422, "Add at least one line or choose a template")
    days = body.valid_days or (tpl.validity_days if tpl else 30); today = date.today()
    qt = m.Quotation(quotation_number=s.next_number(db, "QUO"), customer_id=cust.id, template_id=tpl.id if tpl else None, issue_date=today, valid_until=today + timedelta(days=days),
                     subtotal=0, grand_total=0, status="DRAFT", created_by=a.id); db.add(qt)
    for l in lines:
        p = get_or_404(db, m.Product, l.product_id)
        if not p.is_active: raise HTTPException(409, f"{p.name} is inactive")
        v = get_or_404(db, m.ProductVariant, l.variant_id) if l.variant_id else None; pl = get_or_404(db, m.SubscriptionPlan, l.plan_id)
        qt.lines.append(s.price_quotation_line(db, pl, p, v, l.quantity, l.unit_price, l.discount_amount, today, cust))
    if len({l.plan_id for l in qt.lines}) != 1: raise HTTPException(422, "Use a single plan per quotation")
    s.recompute_quotation_totals(qt); db.flush(); s.audit(db, a, "quotation.created", "quotation", qt.id); db.commit(); db.refresh(qt)
    return quote_out(qt, db)
@app.post("/quotations/{qid}/send")
def send_quotation(qid: str, a=Depends(staff_or_admin), db: Session = Depends(get_db)):
    qt = get_or_404(db, m.Quotation, qid)
    if qt.status != "DRAFT": raise HTTPException(409, "Only a draft quotation can be sent")
    qt.status = "SENT"; s.notify(db, qt.customer, "quotation.sent", f"Quotation {qt.quotation_number}", f"Total ₹{qt.grand_total}, valid until {qt.valid_until}.", "quotation", qt.id)
    s.outbox(db, "quotation.sent", "quotation", qt.id, {"to": qt.customer.billing_email, "customer": qt.customer.company_name, "quotation_number": qt.quotation_number,
             "total": s.inr(qt.grand_total), "valid_until": f"{qt.valid_until:%d %b %Y}"})
    s.audit(db, a, "quotation.sent", "quotation", qt.id); db.commit(); return quote_out(qt, db)
@app.post("/quotations/{qid}/reject")
def reject_quotation(qid: str, u=Depends(current_user), db: Session = Depends(get_db)):
    qt = get_or_404(db, m.Quotation, qid); check_own_customer(db, u, qt.customer_id)
    if qt.status != "SENT": raise HTTPException(409, "Only a sent quotation can be rejected")
    qt.status = "REJECTED"; s.audit(db, u, "quotation.rejected", "quotation", qt.id); db.commit(); return quote_out(qt, db)
class AcceptIn(BaseModel): start_date: Optional[date] = None; payment_terms: Optional[str] = "Net 15"; auto_renew: bool = False
def check_own_customer(db, u, customer_id):
    if u.role == "CUSTOMER":
        c = customer_of(db, u)
        if not c or c.id != customer_id: raise HTTPException(404, "Not found")
@app.post("/quotations/{qid}/accept")
def accept_quotation(qid: str, body: AcceptIn = AcceptIn(), u=Depends(current_user), db: Session = Depends(get_db)):
    qt = get_or_404(db, m.Quotation, qid); check_own_customer(db, u, qt.customer_id)
    sub = s.convert_quotation(db, qt.id, u, body.start_date, body.payment_terms, body.auto_renew); db.commit()
    return {"subscription_id": str(sub.id), "subscription_number": sub.subscription_number, "status": sub.status}

# =================== SUBSCRIPTIONS ===================
class SubLineIn(BaseModel): product_id: str; variant_id: Optional[str] = None; quantity: int = Field(ge=1); unit_price: Optional[Decimal] = None; discount_amount: Decimal = Decimal(0)
class SubIn(BaseModel):
    customer_id: str; plan_id: str; start_date: date; expiry_date: Optional[date] = None; payment_terms: str = "Net 15"; auto_renew: bool = False; lines: list[SubLineIn] = Field(min_length=1)
fmt = lambda d: d.strftime("%d %b %Y") if d else "—"
def sub_out(x: m.Subscription):
    return {"id": str(x.id), "number": x.subscription_number, "customer": x.customer.company_name, "customer_id": str(x.customer_id), "plan": x.plan.name, "plan_id": str(x.plan_id),
            "start": fmt(x.start_date), "expiry": fmt(x.expiry_date), "next_billing": fmt(x.next_billing_date), "start_iso": str(x.start_date), "terms": x.payment_terms or "—", "amount": f(s.sub_amount(x)),
            "cycle": x.plan.billing_interval.title(), "status": x.status.title(), "auto_renew": x.auto_renew, "quotation_id": str(x.quotation_id) if x.quotation_id else None,
            "can_pause": x.plan.allow_pause, "can_close": x.plan.allow_early_close, "can_renew": x.plan.allow_renewal,
            "line_data": [{"product": l.product_name, "variant": l.variant_name, "quantity": l.quantity, "unit_price": f(l.unit_price), "tax_rate": f(l.tax_rate_snapshot), "total": f(l.line_total)} for l in x.lines]}
@app.get("/subscriptions")
def subscriptions(response: Response, pg: Page = Depends(), q: Optional[str] = None, status: Optional[str] = None, customer_id: Optional[str] = None, plan_id: Optional[str] = None,
                  start_from: Optional[date] = None, start_to: Optional[date] = None, expiring_before: Optional[date] = None,
                  u=Depends(current_user), db: Session = Depends(get_db)):
    qry = scope_customer(db, u, select(m.Subscription).join(m.Customer, m.Customer.id == m.Subscription.customer_id), m.Subscription.customer_id)
    if q: qry = qry.where(Q.search(q, m.Subscription.subscription_number, m.Customer.company_name))
    if status:
        k = Q.norm(status)
        if k not in ("DRAFT", "QUOTATION", "CONFIRMED", "ACTIVE", "PAUSED", "CLOSED"): raise HTTPException(422, "Unknown subscription status")
        qry = qry.where(m.Subscription.status == k)
    if customer_id: qry = qry.where(m.Subscription.customer_id == Q.to_uuid(customer_id, "customer_id"))
    if plan_id: qry = qry.where(m.Subscription.plan_id == Q.to_uuid(plan_id, "plan_id"))
    qry = qry.where(*Q.between_dates(m.Subscription.start_date, start_from, start_to))
    if expiring_before: qry = qry.where(m.Subscription.expiry_date.is_not(None), m.Subscription.expiry_date <= expiring_before)
    qry = Q.paginate(db, qry, response, pg).order_by(m.Subscription.created_at.desc(), m.Subscription.id) \
        .options(contains_eager(m.Subscription.customer), joinedload(m.Subscription.plan), selectinload(m.Subscription.lines))
    return [sub_out(x) for x in db.execute(qry).scalars().all()]
@app.post("/subscriptions", status_code=201)
def create_subscription(body: SubIn, request: Request, a=Depends(staff_or_admin), db: Session = Depends(get_db)):
    cust = get_or_404(db, m.Customer, body.customer_id); plan = get_or_404(db, m.SubscriptionPlan, body.plan_id)
    if not cust.is_active: raise HTTPException(409, f"{cust.company_name} is inactive")
    if not plan.is_active or body.start_date < plan.start_date or (plan.end_date and body.start_date > plan.end_date): raise HTTPException(409, "The plan is not available for that start date")
    if body.expiry_date and body.expiry_date <= body.start_date: raise HTTPException(422, "Expiry must be after the start date")
    sub = m.Subscription(subscription_number=s.next_number(db, "SUB"), customer_id=cust.id, plan_id=plan.id, start_date=body.start_date, expiry_date=s.default_expiry(plan, body.start_date, body.expiry_date),
                         payment_terms=body.payment_terms, auto_renew=body.auto_renew, status="DRAFT", created_by=a.id); db.add(sub); db.flush()
    for l in body.lines:
        p = get_or_404(db, m.Product, l.product_id)
        if not p.is_active: raise HTTPException(409, f"{p.name} is inactive")
        if l.quantity < plan.minimum_quantity: raise HTTPException(422, f"{plan.name} needs at least {plan.minimum_quantity} units")
        v = get_or_404(db, m.ProductVariant, l.variant_id) if l.variant_id else None
        sub.lines.append(s.build_sub_line(db, p, v, l.quantity, l.unit_price, l.discount_amount, body.start_date, cust))
    db.add(m.SubscriptionStatusHistory(subscription_id=sub.id, old_status=None, new_status="DRAFT", changed_by=a.id))
    s.audit(db, a, "subscription.created", "subscription", sub.id, None, {"number": sub.subscription_number}, ip(request)); db.commit(); db.refresh(sub)
    return sub_out(sub)
class TransitionIn(BaseModel): reason: Optional[str] = None
CUSTOMER_SUB_ACTIONS = {"pause", "resume", "close", "renew"}   # customers manage their own subscriptions, within plan rules
@app.post("/subscriptions/{sid}/{action}")
def sub_action(sid: str, action: str, body: TransitionIn = TransitionIn(), a=Depends(current_user), db: Session = Depends(get_db)):
    try: sub = db.execute(select(m.Subscription).where(m.Subscription.id == sid).with_for_update()).scalar_one_or_none()
    except Exception: sub = None
    if not sub: raise HTTPException(404, "Subscription not found")
    if a.role == "CUSTOMER":
        check_own_customer(db, a, sub.customer_id)   # someone else's subscription looks like it does not exist
        if action not in CUSTOMER_SUB_ACTIONS: raise HTTPException(403, "You do not have access to this")
    elif a.role not in ("ADMIN", "STAFF"): raise HTTPException(403, "You do not have access to this")
    target = {"quote": "QUOTATION", "confirm": "CONFIRMED", "activate": "ACTIVE", "pause": "PAUSED", "resume": "ACTIVE", "close": "CLOSED"}.get(action)
    if action == "renew": s.renew_subscription(db, sub, a)
    elif target:
        if action == "resume" and sub.status != "PAUSED": raise HTTPException(409, "Only a paused subscription can be resumed")
        if action == "activate" and sub.status == "DRAFT": s.set_status(db, sub, "CONFIRMED", a)
        s.set_status(db, sub, target, a, body.reason)
    else: raise HTTPException(404, "Unknown action")
    db.commit(); db.refresh(sub); return sub_out(sub)
@app.get("/subscriptions/{sid}/history")
def sub_history(sid: str, u=Depends(current_user), db: Session = Depends(get_db)):
    sub = get_or_404(db, m.Subscription, sid); check_own_customer(db, u, sub.customer_id)
    return [{"from": h.old_status, "to": h.new_status, "reason": h.reason, "at": h.created_at.isoformat()} for h in db.execute(select(m.SubscriptionStatusHistory).where(m.SubscriptionStatusHistory.subscription_id == sub.id).order_by(m.SubscriptionStatusHistory.created_at)).scalars()]

# =================== BILLING / INVOICES ===================
class BillIn(BaseModel): as_of: Optional[date] = None; subscription_id: Optional[str] = None
@app.post("/billing/run")
def billing_run(body: BillIn = BillIn(), a=Depends(staff_or_admin), db: Session = Depends(get_db)):
    return s.run_billing(db, body.as_of, body.subscription_id, a)

def inv_out(i: m.Invoice, detail=False):
    st = s.derive_status(i)
    o = {"id": str(i.id), "number": i.invoice_number, "customer": i.customer.company_name, "customer_id": str(i.customer_id), "subscription": i.subscription.subscription_number,
         "date": fmt(i.issue_date), "due": fmt(i.due_date), "due_iso": str(i.due_date), "period": f"{fmt(i.billing_period_start)} – {fmt(i.billing_period_end)}", "subtotal": f(i.subtotal), "discount": f(i.discount_total),
         "tax": f(i.tax_total), "total": f(i.total_amount), "paid": f(i.amount_paid), "balance": f(i.balance_due), "status": {"PARTIALLY_PAID": "Part paid"}.get(st, st.title())}
    o["line_data"] = [{"description": l.description, "quantity": l.quantity, "unit_price": f(l.unit_price), "discount": f(l.discount_amount), "tax_rate": f(l.tax_rate_snapshot), "tax": f(l.tax_amount), "total": f(l.line_total)} for l in i.lines]
    return o
def invoice_query(db, u, customer_id=None, plan_id=None):
    qry = scope_customer(db, u, select(m.Invoice).join(m.Customer, m.Customer.id == m.Invoice.customer_id)
                         .join(m.Subscription, m.Subscription.id == m.Invoice.subscription_id), m.Invoice.customer_id)
    if u.role == "CUSTOMER": qry = qry.where(m.Invoice.status != "DRAFT")
    if customer_id: qry = qry.where(m.Invoice.customer_id == Q.to_uuid(customer_id, "customer_id"))
    if plan_id: qry = qry.where(m.Subscription.plan_id == Q.to_uuid(plan_id, "plan_id"))
    return qry
INV_LOAD = (contains_eager(m.Invoice.customer), contains_eager(m.Invoice.subscription), selectinload(m.Invoice.lines))
@app.get("/invoices")
def invoices(response: Response, pg: Page = Depends(), q: Optional[str] = None, status: Optional[str] = None, customer_id: Optional[str] = None, plan_id: Optional[str] = None,
             subscription_id: Optional[str] = None, issue_from: Optional[date] = None, issue_to: Optional[date] = None, due_from: Optional[date] = None, due_to: Optional[date] = None,
             u=Depends(current_user), db: Session = Depends(get_db)):
    qry = invoice_query(db, u, customer_id, plan_id)
    if q: qry = qry.where(Q.search(q, m.Invoice.invoice_number, m.Customer.company_name, m.Subscription.subscription_number))
    if status: qry = qry.where(Q.invoice_status_filter(status, date.today()))
    if subscription_id: qry = qry.where(m.Invoice.subscription_id == Q.to_uuid(subscription_id, "subscription_id"))
    qry = qry.where(*Q.between_dates(m.Invoice.issue_date, issue_from, issue_to), *Q.between_dates(m.Invoice.due_date, due_from, due_to))
    qry = Q.paginate(db, qry, response, pg).order_by(m.Invoice.created_at.desc(), m.Invoice.id).options(*INV_LOAD)
    return [inv_out(i) for i in db.execute(qry).scalars().all()]
def visible_invoice(db, u, iid):
    inv = get_or_404(db, m.Invoice, iid); check_own_customer(db, u, inv.customer_id)
    if u.role == "CUSTOMER" and inv.status == "DRAFT": raise HTTPException(404, "Invoice not found")
    return inv
@app.get("/invoices/{iid}")
def invoice_detail(iid: str, u=Depends(current_user), db: Session = Depends(get_db)): return inv_out(visible_invoice(db, u, iid))
@app.get("/invoices/{iid}/print", response_class=HTMLResponse)
def invoice_print(iid: str, u=Depends(current_user), db: Session = Depends(get_db)):
    inv = visible_invoice(db, u, iid); st = s.derive_status(inv)
    return HTMLResponse(invoice_html(inv, {"PARTIALLY_PAID": "Part paid"}.get(st, st.title())))
@app.post("/invoices/{iid}/{action}")
def invoice_action(iid: str, action: str, a=Depends(staff_or_admin), db: Session = Depends(get_db)):
    inv = db.execute(select(m.Invoice).where(m.Invoice.id == Q.to_uuid(iid, "invoice id")).with_for_update()).scalar_one_or_none()
    if not inv: raise HTTPException(404, "Invoice not found")
    if action == "confirm": s.confirm_invoice(db, inv, a)
    elif action == "cancel": s.cancel_invoice(db, inv, a)
    elif action == "void": s.cancel_invoice(db, inv, a, void=True)
    elif action == "send": s.send_invoice(db, inv, a)
    else: raise HTTPException(404, "Unknown action")
    db.commit(); db.refresh(inv); return inv_out(inv)

# =================== PAYMENTS ===================
class AllocIn(BaseModel): invoice_id: str; amount: Decimal
class PayIn(BaseModel):
    customer_id: Optional[str] = None; invoice_id: Optional[str] = None; payment_method: str; amount: Decimal; payment_date: Optional[datetime] = None
    reference_number: Optional[str] = None; notes: Optional[str] = None; allocations: list[AllocIn] = []
def pay_out(p: m.Payment):
    return {"id": str(p.id), "ref": p.payment_number, "customer": p.customer.company_name, "invoice": ", ".join(a.invoice.invoice_number for a in p.allocations) or "—",
            "method": p.payment_method.replace("_", " ").title(), "amount": f(p.amount), "date": p.payment_date.strftime("%d %b %Y"), "note": p.notes or p.reference_number or "",
            "status": p.status.title(), "allocations": [{"invoice": a.invoice.invoice_number, "amount": f(a.allocated_amount)} for a in p.allocations]}
@app.get("/payments")
def payments(response: Response, pg: Page = Depends(), q: Optional[str] = None, status: Optional[str] = None, method: Optional[str] = None, customer_id: Optional[str] = None,
             invoice_id: Optional[str] = None, date_from: Optional[date] = None, date_to: Optional[date] = None, u=Depends(current_user), db: Session = Depends(get_db)):
    qry = scope_customer(db, u, select(m.Payment).join(m.Customer, m.Customer.id == m.Payment.customer_id), m.Payment.customer_id)
    if q: qry = qry.where(Q.search(q, m.Payment.payment_number, m.Payment.reference_number, m.Customer.company_name))
    if status:
        if Q.norm(status) not in ("RECORDED", "REVERSED"): raise HTTPException(422, "Status must be Recorded or Reversed")
        qry = qry.where(m.Payment.status == Q.norm(status))
    if method: qry = qry.where(m.Payment.payment_method == Q.norm(method))
    if customer_id: qry = qry.where(m.Payment.customer_id == Q.to_uuid(customer_id, "customer_id"))
    if invoice_id: qry = qry.where(m.Payment.id.in_(select(m.PaymentAllocation.payment_id).where(m.PaymentAllocation.invoice_id == Q.to_uuid(invoice_id, "invoice_id"))))
    qry = qry.where(*Q.between_timestamps(m.Payment.payment_date, date_from, date_to))
    qry = Q.paginate(db, qry, response, pg).order_by(m.Payment.payment_date.desc(), m.Payment.id) \
        .options(contains_eager(m.Payment.customer), selectinload(m.Payment.allocations).joinedload(m.PaymentAllocation.invoice))
    return [pay_out(p) for p in db.execute(qry).scalars().all()]
@app.post("/payments", status_code=201)
def create_payment(body: PayIn, request: Request, a=Depends(staff_or_admin), db: Session = Depends(get_db)):
    if body.payment_method.upper() not in ("CASH", "BANK_TRANSFER", "CARD", "UPI", "OTHER"): raise HTTPException(422, "Unknown payment method")
    allocs = [x.model_dump() for x in body.allocations]; cid = body.customer_id
    if body.invoice_id and not allocs:
        inv = get_or_404(db, m.Invoice, body.invoice_id); cid = cid or str(inv.customer_id)
        allocs = [{"invoice_id": body.invoice_id, "amount": min(body.amount, inv.balance_due)}]
    if not cid: raise HTTPException(422, "Choose a customer or an invoice")
    import uuid as _u
    for x in allocs: x["invoice_id"] = _u.UUID(str(x["invoice_id"]))
    p = s.record_payment(db, a, _u.UUID(str(cid)), body.payment_method.upper(), body.amount, body.payment_date, body.reference_number, body.notes, allocs)
    db.commit(); db.refresh(p); return pay_out(p)
@app.post("/payments/{pid}/reverse")
def reverse(pid: str, a=Depends(admin_only), db: Session = Depends(get_db)):
    p = get_or_404(db, m.Payment, pid); s.reverse_payment(db, a, p); db.commit(); db.refresh(p); return pay_out(p)

# =================== REPORTS / AUDIT / NOTIFICATIONS ===================
@app.get("/reports/summary")
def summary(date_from: Optional[date] = None, date_to: Optional[date] = None, customer_id: Optional[str] = None, plan_id: Optional[str] = None,
            u=Depends(staff_or_admin), db: Session = Depends(get_db)):
    if date_from and date_to and date_to < date_from: raise HTTPException(422, "date_to is before date_from")
    return Q.summary(db, date.today(), date_from, date_to, customer_id, plan_id)

@app.get("/reports/overdue")
def overdue_report(response: Response, pg: Page = Depends(), customer_id: Optional[str] = None, plan_id: Optional[str] = None,
                   u=Depends(staff_or_admin), db: Session = Depends(get_db)):
    """Overdue invoices, oldest first, so they can be chased before they turn into lost revenue."""
    today = date.today()
    qry = invoice_query(db, u, customer_id, plan_id).where(Q.overdue_clause(today))
    qry = Q.paginate(db, qry, response, pg).order_by(m.Invoice.due_date, m.Invoice.id).options(*INV_LOAD)
    return [{**inv_out(i), "days_overdue": (today - i.due_date).days} for i in db.execute(qry).scalars().all()]

# ---------- CSV export of the report lists (same filters as the matching list endpoint) ----------
import csv, io
from fastapi.responses import StreamingResponse
EXPORT_MAX_ROWS = 50000
EXPORTS = {   # kind -> (list endpoint, [(column header, key in the list row)])
    "invoices": (lambda **k: invoices(**k), [("Invoice", "number"), ("Customer", "customer"), ("Subscription", "subscription"), ("Issued", "date"), ("Due", "due"), ("Period", "period"),
                 ("Subtotal", "subtotal"), ("Discount", "discount"), ("Tax", "tax"), ("Total", "total"), ("Paid", "paid"), ("Balance", "balance"), ("Status", "status")]),
    "overdue": (lambda **k: overdue_report(**k), [("Invoice", "number"), ("Customer", "customer"), ("Due", "due"), ("Days overdue", "days_overdue"), ("Total", "total"), ("Balance", "balance")]),
    "payments": (lambda **k: payments(**k), [("Payment", "ref"), ("Customer", "customer"), ("Invoices", "invoice"), ("Method", "method"), ("Amount", "amount"), ("Date", "date"), ("Note", "note"), ("Status", "status")]),
    "subscriptions": (lambda **k: subscriptions(**k), [("Subscription", "number"), ("Customer", "customer"), ("Plan", "plan"), ("Cycle", "cycle"), ("Start", "start"), ("Expiry", "expiry"),
                      ("Next billing", "next_billing"), ("Terms", "terms"), ("Amount", "amount"), ("Status", "status")]),
}
def csv_safe(v):
    """Stop spreadsheet formula injection: a cell that starts with = + - @ is opened as a formula by Excel."""
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r"): return "'" + v
    return "" if v is None else v

@app.get("/reports/export/{kind}")
def export_report(kind: str, request: Request, u=Depends(staff_or_admin), db: Session = Depends(get_db)):
    """Download a list as CSV. Accepts the same query-string filters as /invoices, /reports/overdue, /payments or /subscriptions
    (page and page_size are ignored; at most 50,000 rows). Fetch with the Authorization header and save the blob."""
    if kind not in EXPORTS: raise HTTPException(404, "Unknown export. Use invoices, overdue, payments or subscriptions")
    fn, cols = EXPORTS[kind]
    params = {k: v for k, v in request.query_params.items() if k not in ("page", "page_size")}
    import inspect
    sig = inspect.signature({"invoices": invoices, "overdue": overdue_report, "payments": payments, "subscriptions": subscriptions}[kind]).parameters
    unknown = [k for k in params if k not in sig or k in ("response", "pg", "u", "db")]
    if unknown: raise HTTPException(422, f"Unknown filter: {', '.join(unknown)}")
    def typed(k, v):   # dates arrive as text in the query string; the list functions expect date objects
        return date.fromisoformat(v) if k.endswith(("_from", "_to", "_before")) else v
    try: kw = {k: typed(k, v) for k, v in params.items()}
    except ValueError: raise HTTPException(422, "Dates must look like 2026-01-31")
    out = io.StringIO(); w = csv.writer(out); w.writerow([c[0] for c in cols]); rows = 0
    for page in range(1, EXPORT_MAX_ROWS // 500 + 1):
        chunk = fn(response=Response(), pg=Page(page=page, page_size=500), u=u, db=db, **kw)
        for r in chunk: w.writerow([csv_safe(r.get(c[1])) for c in cols]); rows += 1
        if len(chunk) < 500: break
    out.seek(0)
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="brightloop-{kind}-{date.today()}.csv"', "X-Row-Count": str(rows)})

@app.get("/audit-logs")
def audit_logs(response: Response, limit: int = Query(100, ge=1, le=500), page: int = Query(1, ge=1), action: Optional[str] = None, entity: Optional[str] = None,
               a=Depends(admin_only), db: Session = Depends(get_db)):
    qry = select(m.AuditLog)
    if action: qry = qry.where(m.AuditLog.action.ilike(f"{action}%"))
    if entity: qry = qry.where(m.AuditLog.entity_type == entity)
    qry = Q.paginate(db, qry, response, Page(page=page, page_size=limit)).order_by(m.AuditLog.created_at.desc(), m.AuditLog.id)
    return [{"id": str(l.id), "action": l.action, "entity": l.entity_type, "entity_id": str(l.entity_id), "actor": l.actor_user_id and str(l.actor_user_id), "at": l.created_at.isoformat(), "old": l.old_values, "new": l.new_values}
            for l in db.execute(qry).scalars()]
@app.get("/notifications")
def notifications(u=Depends(current_user), db: Session = Depends(get_db)):
    return [{"id": str(n.id), "type": n.notification_type, "subject": n.subject, "message": n.message, "status": n.status, "at": n.created_at.isoformat()}
            for n in db.execute(select(m.Notification).where(m.Notification.user_id == u.id).order_by(m.Notification.created_at.desc()).limit(50)).scalars()]
@app.get("/health")
def health(db: Session = Depends(get_db)): db.execute(text("select 1")); return {"ok": True}

# =================== BACKGROUND JOBS / OUTBOX / BILLING JOBS ===================
@app.on_event("startup")
def _start_scheduler():
    config.assert_production_ready()      # refuses to boot with placeholder secrets / open CORS / dev tokens when ENVIRONMENT=production
    if SCHEDULER_ENABLED: worker.start_scheduler()
@app.on_event("shutdown")
def _stop_scheduler(): worker.stop_scheduler()

def outbox_out(e: m.OutboxEvent):
    p = {k: v for k, v in e.payload.items() if k != "link"}       # never expose reset/verify links
    return {"id": str(e.id), "event_type": e.event_type, "aggregate_type": e.aggregate_type, "aggregate_id": str(e.aggregate_id), "status": e.status,
            "to": p.get("to"), "attempts": p.get("_attempts", 0), "error": p.get("_error"), "next_try": p.get("_not_before"),
            "created_at": e.created_at.isoformat(), "published_at": e.published_at.isoformat() if e.published_at else None}
@app.get("/admin/outbox")
def admin_outbox(response: Response, pg: Page = Depends(), status: Optional[str] = None, event_type: Optional[str] = None, a=Depends(admin_only), db: Session = Depends(get_db)):
    qry = select(m.OutboxEvent)
    if status:
        if Q.norm(status) not in ("PENDING", "PUBLISHED", "FAILED"): raise HTTPException(422, "Status must be Pending, Published or Failed")
        qry = qry.where(m.OutboxEvent.status == Q.norm(status))
    if event_type: qry = qry.where(m.OutboxEvent.event_type == event_type)
    return [outbox_out(e) for e in db.execute(Q.paginate(db, qry, response, pg).order_by(m.OutboxEvent.created_at.desc(), m.OutboxEvent.id)).scalars()]
@app.post("/admin/outbox/{eid}/retry")
def admin_outbox_retry(eid: str, a=Depends(admin_only), db: Session = Depends(get_db)):
    e = get_or_404(db, m.OutboxEvent, eid)
    if e.status != "FAILED": raise HTTPException(409, "Only a failed event can be retried")
    e.payload = {k: v for k, v in e.payload.items() if k not in ("_attempts", "_error", "_not_before")}; e.status = "PENDING"
    s.audit(db, a, "outbox.retried", "outbox_event", e.id); db.commit(); return outbox_out(e)
@app.post("/admin/jobs/{job}")
def admin_run_job(job: str, a=Depends(admin_only), db: Session = Depends(get_db)):
    """Run a background job now: outbox | reminders | billing | daily."""
    if job == "outbox": return worker.run_outbox()
    if job == "reminders": return {"reminders_queued": worker.send_overdue_reminders(db)}
    if job == "billing": return s.run_billing(db, date.today(), actor=a)
    if job == "daily": return worker.run_daily()
    raise HTTPException(404, "Unknown job")
@app.get("/billing/jobs")
def billing_jobs(response: Response, pg: Page = Depends(), status: Optional[str] = None, subscription_id: Optional[str] = None, u=Depends(staff_or_admin), db: Session = Depends(get_db)):
    """Billing attempts per subscription period; FAILED ones are retried by the next billing run."""
    qry = select(m.BillingJob, m.Subscription.subscription_number).join(m.Subscription, m.Subscription.id == m.BillingJob.subscription_id)
    if status:
        if Q.norm(status) not in ("PENDING", "PROCESSING", "COMPLETED", "FAILED"): raise HTTPException(422, "Unknown job status")
        qry = qry.where(m.BillingJob.status == Q.norm(status))
    if subscription_id: qry = qry.where(m.BillingJob.subscription_id == Q.to_uuid(subscription_id, "subscription_id"))
    rows = db.execute(Q.paginate(db, qry, response, pg).order_by(m.BillingJob.created_at.desc(), m.BillingJob.id)).all()
    return [{"id": str(j.id), "subscription": num, "subscription_id": str(j.subscription_id), "period_start": str(j.billing_period_start), "period_end": str(j.billing_period_end),
             "status": j.status.title(), "attempts": j.attempts, "error": j.error_message, "completed_at": j.completed_at.isoformat() if j.completed_at else None} for j, num in rows]

# =================== E-MAIL WORDING (admin) ===================
class EmailTplIn(BaseModel):
    subject_template: str = Field(min_length=1, max_length=255); body_template: str = Field(min_length=1, max_length=10000); is_active: bool = True
def email_tpl_out(event_type, row):
    d_subj, d_body = worker.DEFAULT_TEMPLATES[event_type]
    return {"event_type": event_type, "subject_template": row.subject_template if row else d_subj, "body_template": row.body_template if row else d_body,
            "is_active": row.is_active if row else True,
            "customised": bool(row) and (row.subject_template, row.body_template, row.is_active) != (d_subj, d_body, True),   # the seed stores the defaults as rows
            "default_subject": d_subj, "default_body": d_body,
            "placeholders": sorted({x for x in __import__("re").findall(r"\$(\w+)", d_subj + d_body)} | {"portal"})}
@app.get("/admin/email-templates")
def email_templates(a=Depends(admin_only), db: Session = Depends(get_db)):
    rows = {r.event_type: r for r in db.execute(select(m.NotificationTemplate)).scalars()}
    return [email_tpl_out(et, rows.get(et)) for et in sorted(worker.DEFAULT_TEMPLATES)]
@app.put("/admin/email-templates/{event_type}")
def set_email_template(event_type: str, body: EmailTplIn, a=Depends(admin_only), db: Session = Depends(get_db)):
    if event_type not in worker.DEFAULT_TEMPLATES: raise HTTPException(404, "Unknown e-mail type")
    if any(c in body.subject_template for c in "\r\n"): raise HTTPException(422, "The subject must be a single line")
    row = db.execute(select(m.NotificationTemplate).where(m.NotificationTemplate.event_type == event_type)).scalar_one_or_none()
    old = {"subject": row.subject_template, "active": row.is_active} if row else None
    if not row: row = m.NotificationTemplate(event_type=event_type, subject_template=body.subject_template, body_template=body.body_template); db.add(row)
    row.subject_template, row.body_template, row.is_active = body.subject_template, body.body_template, body.is_active; db.flush()
    s.audit(db, a, "email_template.updated", "notification_template", row.id, old, {"event_type": event_type, "subject": body.subject_template}); db.commit(); db.refresh(row)
    return email_tpl_out(event_type, row)
@app.delete("/admin/email-templates/{event_type}")
def reset_email_template(event_type: str, a=Depends(admin_only), db: Session = Depends(get_db)):
    """Go back to the built-in wording."""
    if event_type not in worker.DEFAULT_TEMPLATES: raise HTTPException(404, "Unknown e-mail type")
    row = db.execute(select(m.NotificationTemplate).where(m.NotificationTemplate.event_type == event_type)).scalar_one_or_none()
    if row:
        s.audit(db, a, "email_template.reset", "notification_template", row.id, {"subject": row.subject_template}, None); db.delete(row); db.commit()
    return email_tpl_out(event_type, None)

# Serve the front end from the same origin so no CORS/config is needed. FRONTEND_DIR wins; otherwise ../frontend (the folder the
# new UI is built in) if it has an index.html (or a built dist/), else the old prototype in ../brightloop. Set FRONTEND_DIR=none to serve the API only.
from fastapi.staticfiles import StaticFiles
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
def _find_frontend():
    env = os.getenv("FRONTEND_DIR")
    if env: return None if env.lower() == "none" else env
    for cand in ("frontend/dist", "frontend/build", "frontend", "brightloop"):
        if os.path.isfile(os.path.join(_ROOT, cand, "index.html")): return os.path.join(_ROOT, cand)
    return None
_FE = _find_frontend()
if _FE and os.path.isdir(_FE):
    app.mount("/", StaticFiles(directory=_FE, html=True), name="frontend")
