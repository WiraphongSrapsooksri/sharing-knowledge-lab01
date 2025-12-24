from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from app.core.security import decode_token
from app.core.database import JSONDatabase
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.models.user import UserInDB

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    """ดึงข้อมูล user จาก token"""
    payload = decode_token(token)
    
    if payload is None:
        raise UnauthorizedException("Could not validate credentials")
    
    username: str = payload.get("sub")
    if username is None:
        raise UnauthorizedException("Could not validate credentials")
    
    # ดึงข้อมูล user จาก database
    db = JSONDatabase("users.json")
    user_data = await db.get_by_field("username", username)
    
    if user_data is None:
        raise UnauthorizedException("User not found")
    
    return UserInDB(**user_data)

async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user)
) -> UserInDB:
    """ตรวจสอบว่า user ยัง active อยู่"""
    if not current_user.is_active:
        raise ForbiddenException("Inactive user")
    return current_user

async def get_current_admin_user(
    current_user: UserInDB = Depends(get_current_active_user)
) -> UserInDB:
    """ตรวจสอบว่าเป็น admin"""
    if current_user.role != "admin":
        raise ForbiddenException("Not enough permissions")
    return current_user