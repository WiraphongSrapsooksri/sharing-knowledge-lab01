from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from typing import Annotated

from app.models.auth import Token, LoginRequest
from app.models.user import UserCreate, UserResponse, UserInDB
from app.core.database import JSONDatabase
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.exceptions import UnauthorizedException, ConflictException
from app.config import settings
from app.dependencies import get_current_active_user

import uuid
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate):
    """
    ลงทะเบียนผู้ใช้ใหม่
    
    - **username**: ชื่อผู้ใช้ (unique)
    - **email**: อีเมล (unique)
    - **password**: รหัสผ่าน (ขั้นต่ำ 6 ตัวอักษร)
    - **full_name**: ชื่อเต็ม (optional)
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
    
    # สร้าง user ใหม่
    user_data = {
        "id": str(uuid.uuid4()),
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "hashed_password": get_password_hash(user.password),
        "role": "user",  # default role
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": None
    }
    
    await db.create(user_data)
    
    return UserResponse(**user_data)

@router.post("/login", response_model=Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """
    Login เพื่อรับ access token
    
    - **username**: ชื่อผู้ใช้
    - **password**: รหัสผ่าน
    """
    db = JSONDatabase("users.json")
    
    # หา user
    user_data = await db.get_by_field("username", form_data.username)
    if not user_data:
        raise UnauthorizedException("Incorrect username or password")
    
    # ตรวจสอบรหัสผ่าน
    if not verify_password(form_data.password, user_data["hashed_password"]):
        raise UnauthorizedException("Incorrect username or password")
    
    # ตรวจสอบว่า active อยู่ไหม
    if not user_data.get("is_active", True):
        raise UnauthorizedException("User account is inactive")
    
    # สร้าง access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_data["username"]},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login-json", response_model=Token)
async def login_json(login_data: LoginRequest):
    """
    Login ด้วย JSON body (alternative)
    
    - **username**: ชื่อผู้ใช้
    - **password**: รหัสผ่าน
    """
    db = JSONDatabase("users.json")
    
    user_data = await db.get_by_field("username", login_data.username)
    if not user_data:
        raise UnauthorizedException("Incorrect username or password")
    
    if not verify_password(login_data.password, user_data["hashed_password"]):
        raise UnauthorizedException("Incorrect username or password")
    
    if not user_data.get("is_active", True):
        raise UnauthorizedException("User account is inactive")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_data["username"]},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserInDB = Depends(get_current_active_user)):
    """
    ดูข้อมูลโปรไฟล์ตัวเอง (ต้อง login)
    """
    return UserResponse(**current_user.dict())

@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: UserInDB = Depends(get_current_active_user)):
    """
    Refresh token (ต้อง login)
    """
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.username},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}