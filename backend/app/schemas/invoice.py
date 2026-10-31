"""Pydantic schemas for invoices."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class InvoiceItemOut(BaseModel):
    id: UUID
    product_id: UUID | None = None
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal

    model_config = {"from_attributes": True}


class InvoiceOut(BaseModel):
    id: UUID
    invoice_number: str
    customer_id: UUID | None = None
    customer_name: str | None = None
    quotation_id: UUID | None = None
    status: str
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total: Decimal
    notes: str | None = None
    due_date: date | None = None
    paid_amount: Decimal
    items: list[InvoiceItemOut] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceStatusUpdate(BaseModel):
    status: str = Field(
        ...,
        pattern="^(draft|sent|paid|partially_paid|overdue|cancelled)$",
    )
