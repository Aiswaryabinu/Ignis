"""Quotation CRUD routes + convert-to-invoice."""

import uuid as _uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.catalog import Product
from app.models.quotation import Quotation, QuotationItem
from app.models.invoice import Invoice, InvoiceItem
from app.schemas.quotation import QuotationCreate, QuotationUpdate, QuotationOut, QuotationItemOut
from app.utils.deps import CurrentUser

router = APIRouter(prefix="/api/quotations", tags=["quotations"])


def _next_number(db: Session, company_id, prefix: str = "QT") -> str:
    """Generate a sequential quotation number like QT-00001."""
    last = (
        db.query(Quotation)
        .filter(Quotation.company_id == company_id)
        .order_by(Quotation.created_at.desc())
        .first()
    )
    if last and last.quotation_number.startswith(prefix):
        try:
            seq = int(last.quotation_number.split("-")[1]) + 1
        except (IndexError, ValueError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}-{seq:05d}"


def _build_quotation_out(q: Quotation) -> QuotationOut:
    """Map ORM Quotation to QuotationOut schema."""
    return QuotationOut(
        id=q.id,
        quotation_number=q.quotation_number,
        customer_id=q.customer_id,
        customer_name=q.customer.name if q.customer else None,
        status=q.status,
        subtotal=q.subtotal,
        tax_amount=q.tax_amount,
        discount_amount=q.discount_amount,
        total=q.total,
        notes=q.notes,
        valid_until=q.valid_until,
        items=[QuotationItemOut.model_validate(i) for i in q.items],
        created_at=q.created_at,
    )


@router.get("", response_model=list[QuotationOut])
def list_quotations(user: CurrentUser, db: Session = Depends(get_db)):
    """List quotations for the user's company."""
    rows = (
        db.query(Quotation)
        .options(joinedload(Quotation.customer), joinedload(Quotation.items))
        .filter(Quotation.company_id == user.company_id)
        .order_by(Quotation.created_at.desc())
        .all()
    )
    # Deduplicate from joinedload
    seen = set()
    unique = []
    for r in rows:
        if r.id not in seen:
            seen.add(r.id)
            unique.append(r)
    return [_build_quotation_out(q) for q in unique]


@router.post("", response_model=QuotationOut, status_code=status.HTTP_201_CREATED)
def create_quotation(body: QuotationCreate, user: CurrentUser, db: Session = Depends(get_db)):
    """Create a quotation with line items."""
    quot = Quotation(
        company_id=user.company_id,
        customer_id=body.customer_id,
        quotation_number=_next_number(db, user.company_id),
        notes=body.notes,
        valid_until=body.valid_until,
        created_by=user.id,
    )

    subtotal = Decimal("0")
    for item in body.items:
        product = db.query(Product).filter(
            Product.id == item.product_id,
            Product.company_id == user.company_id,
        ).first()
        if not product:
            raise HTTPException(status_code=400, detail=f"Product {item.product_id} not found")
        line_total = item.quantity * item.price
        subtotal += line_total
        qi = QuotationItem(
            product_id=product.id,
            product_name=product.name,
            quantity=item.quantity,
            unit_price=item.price,
            line_total=line_total,
        )
        quot.items.append(qi)

    quot.subtotal = subtotal
    quot.total = subtotal  # tax/discount can be added later
    db.add(quot)
    db.commit()
    db.refresh(quot)
    return _build_quotation_out(quot)


@router.put("/{quot_id}", response_model=QuotationOut)
def update_quotation(quot_id: UUID, body: QuotationUpdate, user: CurrentUser, db: Session = Depends(get_db)):
    """Update quotation header + replace items."""
    quot = (
        db.query(Quotation)
        .options(joinedload(Quotation.items))
        .filter(Quotation.id == quot_id, Quotation.company_id == user.company_id)
        .first()
    )
    if not quot:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if quot.status == "converted":
        raise HTTPException(status_code=400, detail="Cannot edit a converted quotation")

    quot.customer_id = body.customer_id
    quot.notes = body.notes
    quot.valid_until = body.valid_until

    # Remove old items
    for old_item in list(quot.items):
        db.delete(old_item)

    subtotal = Decimal("0")
    for item in body.items:
        product = db.query(Product).filter(
            Product.id == item.product_id,
            Product.company_id == user.company_id,
        ).first()
        if not product:
            raise HTTPException(status_code=400, detail=f"Product {item.product_id} not found")
        line_total = item.quantity * item.price
        subtotal += line_total
        qi = QuotationItem(
            product_id=product.id,
            product_name=product.name,
            quantity=item.quantity,
            unit_price=item.price,
            line_total=line_total,
        )
        quot.items.append(qi)

    quot.subtotal = subtotal
    quot.total = subtotal
    db.commit()
    db.refresh(quot)
    return _build_quotation_out(quot)


@router.delete("/{quot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quotation(quot_id: UUID, user: CurrentUser, db: Session = Depends(get_db)):
    """Hard-delete a quotation and its items."""
    quot = (
        db.query(Quotation)
        .filter(Quotation.id == quot_id, Quotation.company_id == user.company_id)
        .first()
    )
    if not quot:
        raise HTTPException(status_code=404, detail="Quotation not found")
    db.delete(quot)
    db.commit()


@router.patch("/{quot_id}/convert", response_model=dict)
def convert_to_invoice(quot_id: UUID, user: CurrentUser, db: Session = Depends(get_db)):
    """Convert a quotation into an invoice."""
    quot = (
        db.query(Quotation)
        .options(joinedload(Quotation.items))
        .filter(Quotation.id == quot_id, Quotation.company_id == user.company_id)
        .first()
    )
    if not quot:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if quot.status == "converted":
        raise HTTPException(status_code=400, detail="Already converted")

    # Generate invoice number
    last_inv = (
        db.query(Invoice)
        .filter(Invoice.company_id == user.company_id)
        .order_by(Invoice.created_at.desc())
        .first()
    )
    if last_inv and last_inv.invoice_number.startswith("INV"):
        try:
            seq = int(last_inv.invoice_number.split("-")[1]) + 1
        except (IndexError, ValueError):
            seq = 1
    else:
        seq = 1
    inv_number = f"INV-{seq:05d}"

    invoice = Invoice(
        company_id=user.company_id,
        customer_id=quot.customer_id,
        quotation_id=quot.id,
        invoice_number=inv_number,
        status="draft",
        subtotal=quot.subtotal,
        tax_amount=quot.tax_amount,
        discount_amount=quot.discount_amount,
        total=quot.total,
        notes=quot.notes,
        due_date=(datetime.now(timezone.utc) + timedelta(days=30)).date(),
        created_by=user.id,
    )

    for qi in quot.items:
        inv_item = InvoiceItem(
            product_id=qi.product_id,
            product_name=qi.product_name,
            quantity=qi.quantity,
            unit_price=qi.unit_price,
            discount_type=qi.discount_type,
            discount_value=qi.discount_value,
            tax_rate_id=qi.tax_rate_id,
            tax_percentage=qi.tax_percentage,
            line_total=qi.line_total,
        )
        invoice.items.append(inv_item)

    quot.status = "converted"
    db.add(invoice)
    db.commit()

    return {"message": "Quotation converted to invoice", "invoice_id": str(invoice.id)}
