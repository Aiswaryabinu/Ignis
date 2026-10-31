"""Pydantic schemas for quotations."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class QuotationItemIn(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(..., gt=0)
    price: Decimal = Field(..., ge=0)


class QuotationCreate(BaseModel):
    customer_id: UUID
    valid_until: date | None = None
    notes: str | None = None
    items: list[QuotationItemIn] = Field(..., min_length=1)


class QuotationUpdate(BaseModel):
    customer_id: UUID
    valid_until: date | None = None
    notes: str | None = None
    items: list[QuotationItemIn] = Field(..., min_length=1)


class QuotationItemOut(BaseModel):
    id: UUID
    product_id: UUID | None = None
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal

    model_config = {"from_attributes": True}


class QuotationOut(BaseModel):
    id: UUID
    quotation_number: str
    customer_id: UUID | None = None
    customer_name: str | None = None
    status: str
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total: Decimal
    notes: str | None = None
    valid_until: date | None = None
    items: list[QuotationItemOut] = []
    created_at: datetime

    model_config = {"from_attributes": True}
