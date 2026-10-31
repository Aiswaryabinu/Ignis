from pydantic import BaseModel, EmailStr, Field, field_validator

class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    confirm_password: str = Field(min_length=12, max_length=128)
    @field_validator("email")
    @classmethod
    def normalize_email(cls, v): return v.strip().lower()

class SigninIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    @field_validator("email")
    @classmethod
    def normalize_email(cls, v): return v.strip().lower()

class ForgotIn(BaseModel):
    email: EmailStr
    @field_validator("email")
    @classmethod
    def normalize_email(cls, v): return v.strip().lower()

class ResetIn(BaseModel):
    token: str = Field(min_length=20, max_length=256)
    new_password: str = Field(min_length=12, max_length=128)

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class MessageOut(BaseModel):
    message: str
