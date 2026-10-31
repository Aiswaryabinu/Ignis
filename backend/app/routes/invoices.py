"""Invoice routes: list, detail, status update."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceOut, InvoiceItemOut, InvoiceStatusUpdate
from app.utils.deps import CurrentUser

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


def _build_invoice_out(inv: Invoice) -> InvoiceOut:
    """Map ORM Invoice to InvoiceOut schema."""
    return InvoiceOut(
        id=inv.id,
        invoice_number=inv.invoice_number,
        customer_id=inv.customer_id,
        customer_name=inv.customer.name if inv.customer else None,
        quotation_id=inv.quotation_id,
        status=inv.status,
        subtotal=inv.subtotal,
        tax_amount=inv.tax_amount,
        discount_amount=inv.discount_amount,
        total=inv.total,
        notes=inv.notes,
        due_date=inv.due_date,
        paid_amount=inv.paid_amount,
        items=[InvoiceItemOut.model_validate(i) for i in inv.items],
        created_at=inv.created_at,
    )


@router.get("", response_model=list[InvoiceOut])
def list_invoices(user: CurrentUser, db: Session = Depends(get_db)):
    """List all invoices for the user's company."""
    rows = (
        db.query(Invoice)
        .options(joinedload(Invoice.customer), joinedload(Invoice.items))
        .filter(Invoice.company_id == user.company_id)
        .order_by(Invoice.created_at.desc())
        .all()
    )
    seen = set()
    unique = []
    for r in rows:
        if r.id not in seen:
            seen.add(r.id)
            unique.append(r)
    return [_build_invoice_out(inv) for inv in unique]


@router.get("/{inv_id}", response_model=InvoiceOut)
def get_invoice(inv_id: UUID, user: CurrentUser, db: Session = Depends(get_db)):
    """Get a single invoice with items (for print/detail view)."""
    inv = (
        db.query(Invoice)
        .options(joinedload(Invoice.customer), joinedload(Invoice.items))
        .filter(Invoice.id == inv_id, Invoice.company_id == user.company_id)
        .first()
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _build_invoice_out(inv)


@router.patch("/{inv_id}/status", response_model=InvoiceOut)
def update_invoice_status(
    inv_id: UUID,
    body: InvoiceStatusUpdate,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Update the status of an invoice."""
    inv = (
        db.query(Invoice)
        .options(joinedload(Invoice.customer), joinedload(Invoice.items))
        .filter(Invoice.id == inv_id, Invoice.company_id == user.company_id)
        .first()
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    inv.status = body.status
    db.commit()
    db.refresh(inv)
    return _build_invoice_out(inv)
