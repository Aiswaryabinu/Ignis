"""Authentication routes: login & register."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company import Company
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, AuthResponse, UserOut
from app.utils.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate a user with email & password and return a JWT."""
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    token = create_access_token({"sub": str(user.id), "company_id": str(user.company_id)})
    return AuthResponse(
        token=token,
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user and company, then return a JWT."""
    # Check for duplicate email
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create company
    company = Company(name=body.company_name)
    db.add(company)
    db.flush()  # get company.id

    # Create user as admin of the new company
    user = User(
        company_id=company.id,
        email=body.email,
        password_hash=hash_password(body.password),
        name=body.name,
        phone=body.phone,
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "company_id": str(user.company_id)})
    return AuthResponse(
        token=token,
        user=UserOut.model_validate(user),
    )
