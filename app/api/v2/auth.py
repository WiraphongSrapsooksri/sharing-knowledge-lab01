from fastapi import APIRouter, Depends, status, Header
from typing import Optional, List
from datetime import datetime, timedelta

from app.models.auth import Token, LoginRequest
from app.models.user import UserCreate, UserResponse, UserInDB
from app.core.database import JSONDatabase
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.exceptions import UnauthorizedException, ConflictException, BadRequestException
from app.config import settings
from app.dependencies import get_current_active_user

import uuid
import httpx

router = APIRouter(prefix="/auth", tags=["Authentication V2"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_v2(user: UserCreate, user_agent: Optional[str] = Header(None)):
    """
    ลงทะเบียนผู้ใช้ใหม่ (V2 - Enhanced with logging)
    
    Improvements:
    - บันทึก user agent
    - ส่ง welcome email (simulated)
    - Enhanced validation
    """
    db = JSONDatabase("users.json")
    
    # ตรวจสอบว่า username ซ้ำไหม
    existing_user = await db.get_by_field("username", user.username)
    if existing_user:
        raise ConflictException(f"Username '{user.username}' already exists")
    
    # ตรวจสอบว่า email ซ้ำไหม
    existing_email = await db.get_by_field("email", user.email)
    if existing_email:
        raise ConflictException(f"Email '{user.email}' already registered")
    
    # Enhanced password validation
    if len(user.password) < 8:
        raise BadRequestException("Password must be at least 8 characters")
    
    if not any(char.isdigit() for char in user.password):
        raise BadRequestException("Password must contain at least one digit")
    
    # สร้าง user ใหม่
    user_data = {
        "id": str(uuid.uuid4()),
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "hashed_password": get_password_hash(user.password),
        "role": "user",
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": None,
        "last_login": None,
        "login_count": 0,
        "registered_from": user_agent or "Unknown"
    }
    
    await db.create(user_data)
    
    # Simulate sending welcome email
    print(f"📧 [Simulated] Sending welcome email to {user.email}")
    
    return UserResponse(**user_data)

@router.post("/login", response_model=Token)
async def login_v2(
    login_data: LoginRequest,
    user_agent: Optional[str] = Header(None)
):
    """
    Login (V2 - Enhanced with tracking)
    
    Improvements:
    - บันทึก login history
    - Track login count
    - Device tracking
    """
    db = JSONDatabase("users.json")
    
    user_data = await db.get_by_field("username", login_data.username)
    if not user_data:
        raise UnauthorizedException("Incorrect username or password")
    
    if not verify_password(login_data.password, user_data["hashed_password"]):
        raise UnauthorizedException("Incorrect username or password")
    
    if not user_data.get("is_active", True):
        raise UnauthorizedException("User account is inactive")
    
    # Update login info
    login_count = user_data.get("login_count", 0) + 1
    await db.update(user_data["id"], {
        "last_login": datetime.utcnow().isoformat(),
        "login_count": login_count,
        "last_device": user_agent or "Unknown"
    })
    
    # สร้าง token with additional claims
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user_data["username"],
            "role": user_data["role"],
            "user_id": user_data["id"]
        },
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=dict)
async def get_me_v2(current_user: UserInDB = Depends(get_current_active_user)):
    """
    ดูข้อมูลโปรไฟล์ตัวเอง (V2 - Enhanced with stats)
    
    Returns additional information:
    - Login statistics
    - Account age
    - Activity summary
    """
    user_dict = current_user.dict()
    
    # Calculate account age
    created_at = datetime.fromisoformat(current_user.created_at)
    account_age_days = (datetime.utcnow() - created_at).days
    
    # Add statistics
    user_dict["statistics"] = {
        "account_age_days": account_age_days,
        "login_count": user_dict.get("login_count", 0),
        "last_login": user_dict.get("last_login"),
        "registered_from": user_dict.get("registered_from", "Unknown")
    }
    
    return user_dict

@router.post("/logout")
async def logout_v2(current_user: UserInDB = Depends(get_current_active_user)):
    """
    Logout (V2 - Track logout)
    
    Note: JWT tokens cannot be invalidated on server side,
    client should discard the token
    """
    print(f"👋 User {current_user.username} logged out")
    
    return {
        "message": "Successfully logged out",
        "note": "Please discard your access token on the client side"
    }

@router.get("/verify-token")
async def verify_token(current_user: UserInDB = Depends(get_current_active_user)):
    """
    ตรวจสอบว่า token ยังใช้งานได้อยู่หรือไม่
    """
    return {
        "valid": True,
        "username": current_user.username,
        "role": current_user.role,
        "message": "Token is valid"
    }