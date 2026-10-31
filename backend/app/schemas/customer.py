"""Pydantic schemas for customers."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=20)
    address: str | None = None
    gst_number: str | None = Field(None, max_length=20)


class CustomerUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=20)
    address: str | None = None
    gst_number: str | None = Field(None, max_length=20)


class CustomerOut(BaseModel):
    id: UUID
    name: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    gst_number: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
