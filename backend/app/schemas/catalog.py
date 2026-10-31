"""Pydantic schemas for catalog (categories & products)."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


# --------------- Categories ---------------

class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class CategoryUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class CategoryOut(BaseModel):
    id: UUID
    name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --------------- Products ---------------

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category_id: UUID | None = None
    unit: str = Field("piece", max_length=50)
    price: Decimal = Field(..., ge=0)


class ProductUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category_id: UUID | None = None
    unit: str = Field("piece", max_length=50)
    price: Decimal = Field(..., ge=0)


class ProductOut(BaseModel):
    id: UUID
    name: str
    category_id: UUID | None = None
    category_name: str | None = None
    unit: str
    price: Decimal
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
