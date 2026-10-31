from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from app.api.deps import current_user
from app.models.user import User

router = APIRouter(prefix="/users", tags=["users"])

class UserOut(BaseModel):
    id: int
    email: EmailStr
    model_config = {"from_attributes": True}

@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user
