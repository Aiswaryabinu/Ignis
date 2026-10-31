"""Customer CRUD routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerOut
from app.utils.deps import CurrentUser

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("", response_model=list[CustomerOut])
def list_customers(user: CurrentUser, db: Session = Depends(get_db)):
    """List all active customers for the user's company."""
    return (
        db.query(Customer)
        .filter(Customer.company_id == user.company_id, Customer.is_active.is_(True))
        .order_by(Customer.name)
        .all()
    )


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(body: CustomerCreate, user: CurrentUser, db: Session = Depends(get_db)):
    """Create a new customer."""
    cust = Customer(
        company_id=user.company_id,
        name=body.name,
        email=body.email,
        phone=body.phone,
        address=body.address,
        gst_number=body.gst_number,
    )
    db.add(cust)
    db.commit()
    db.refresh(cust)
    return cust


@router.put("/{cust_id}", response_model=CustomerOut)
def update_customer(cust_id: UUID, body: CustomerUpdate, user: CurrentUser, db: Session = Depends(get_db)):
    """Update a customer."""
    cust = (
        db.query(Customer)
        .filter(Customer.id == cust_id, Customer.company_id == user.company_id)
        .first()
    )
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")
    cust.name = body.name
    cust.email = body.email
    cust.phone = body.phone
    cust.address = body.address
    cust.gst_number = body.gst_number
    db.commit()
    db.refresh(cust)
    return cust


@router.delete("/{cust_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(cust_id: UUID, user: CurrentUser, db: Session = Depends(get_db)):
    """Soft-delete a customer."""
    cust = (
        db.query(Customer)
        .filter(Customer.id == cust_id, Customer.company_id == user.company_id)
        .first()
    )
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")
    cust.is_active = False
    db.commit()
