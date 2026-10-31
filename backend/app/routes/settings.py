"""Settings routes: profile, company, tax rates."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company import Company
from app.models.user import User
from app.models.tax_rate import TaxRate
from app.schemas.settings import (
    ProfileOut, ProfileUpdate, PasswordChange,
    CompanyOut, CompanyUpdate,
    TaxRateCreate, TaxRateOut,
)
from app.utils.deps import CurrentUser
from app.utils.security import verify_password, hash_password

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ==================== Profile ====================

@router.get("/profile", response_model=ProfileOut)
def get_profile(user: CurrentUser):
    """Return the authenticated user's profile."""
    return ProfileOut.model_validate(user)


@router.put("/profile", response_model=ProfileOut)
def update_profile(body: ProfileUpdate, user: CurrentUser, db: Session = Depends(get_db)):
    """Update the authenticated user's profile."""
    # Check email uniqueness if changed
    if body.email != user.email:
        existing = db.query(User).filter(User.email == body.email).first()
        if existing:
            raise HTTPException(status_code=409, detail="Email already in use")

    user.name = body.name
    user.email = body.email
    user.phone = body.phone
    db.commit()
    db.refresh(user)
    return ProfileOut.model_validate(user)


@router.put("/password", status_code=status.HTTP_200_OK)
def change_password(body: PasswordChange, user: CurrentUser, db: Session = Depends(get_db)):
    """Change the authenticated user's password."""
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "Password updated successfully"}


# ==================== Company ====================

@router.get("/company", response_model=CompanyOut)
def get_company(user: CurrentUser, db: Session = Depends(get_db)):
    """Return the user's company details."""
    company = db.query(Company).filter(Company.id == user.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return CompanyOut.model_validate(company)


@router.put("/company", response_model=CompanyOut)
def update_company(body: CompanyUpdate, user: CurrentUser, db: Session = Depends(get_db)):
    """Update company details."""
    company = db.query(Company).filter(Company.id == user.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    company.name = body.name
    company.address = body.address
    company.phone = body.phone
    company.email = body.email
    company.gst_number = body.gst_number
    company.logo_url = body.logo_url
    db.commit()
    db.refresh(company)
    return CompanyOut.model_validate(company)


# ==================== Tax Rates ====================

@router.get("/tax-rates", response_model=list[TaxRateOut])
def list_tax_rates(user: CurrentUser, db: Session = Depends(get_db)):
    """List all active tax rates."""
    return (
        db.query(TaxRate)
        .filter(TaxRate.company_id == user.company_id, TaxRate.is_active.is_(True))
        .order_by(TaxRate.name)
        .all()
    )


@router.post("/tax-rates", response_model=TaxRateOut, status_code=status.HTTP_201_CREATED)
def create_tax_rate(body: TaxRateCreate, user: CurrentUser, db: Session = Depends(get_db)):
    """Create a new tax rate."""
    tr = TaxRate(
        company_id=user.company_id,
        name=body.name,
        rate=body.rate,
    )
    db.add(tr)
    db.commit()
    db.refresh(tr)
    return tr


@router.delete("/tax-rates/{rate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tax_rate(rate_id: UUID, user: CurrentUser, db: Session = Depends(get_db)):
    """Soft-delete a tax rate."""
    tr = (
        db.query(TaxRate)
        .filter(TaxRate.id == rate_id, TaxRate.company_id == user.company_id)
        .first()
    )
    if not tr:
        raise HTTPException(status_code=404, detail="Tax rate not found")
    tr.is_active = False
    db.commit()
