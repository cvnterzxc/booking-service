from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models import UserRole

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=100)
    phone: str | None = None

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    phone: str | None
    role: UserRole
    created_at: datetime