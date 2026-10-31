"""Pydantic schemas for settings endpoints."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# --------------- Profile ---------------

class ProfileOut(BaseModel):
    id: UUID
    name: str
    email: str
    phone: str | None = None
    role: str

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str | None = Field(None, max_length=20)


class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=6, max_length=128)
    new_password: str = Field(..., min_length=6, max_length=128)


# --------------- Company ---------------

class CompanyOut(BaseModel):
    id: UUID
    name: str
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    gst_number: str | None = None
    logo_url: str | None = None

    model_config = {"from_attributes": True}


class CompanyUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    address: str | None = None
    phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    gst_number: str | None = Field(None, max_length=20)
    logo_url: str | None = None


# --------------- Tax Rates ---------------

class TaxRateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    rate: Decimal = Field(..., ge=0, le=100)


class TaxRateOut(BaseModel):
    id: UUID
    name: str
    rate: Decimal
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
