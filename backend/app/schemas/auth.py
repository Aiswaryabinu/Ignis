"""Pydantic schemas for authentication endpoints."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str | None = Field(None, max_length=20)
    password: str = Field(..., min_length=6, max_length=128)
    company_name: str = Field(..., min_length=1, max_length=200)


class UserOut(BaseModel):
    id: UUID
    name: str
    email: str
    phone: str | None = None
    role: str

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    token: str
    user: UserOut
