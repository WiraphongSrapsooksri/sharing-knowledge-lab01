from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Literal
from datetime import datetime

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = None
    
class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None

class UserInDB(UserBase):
    id: str
    hashed_password: str
    role: Literal["admin", "user"] = "user"
    is_active: bool = True
    created_at: str
    updated_at: Optional[str] = None

class UserResponse(UserBase):
    id: str
    role: str
    is_active: bool
    created_at: str
    
    class Config:
        from_attributes = True