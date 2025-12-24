from fastapi import APIRouter, Depends, Query, status
from typing import List, Optional

from app.models.user import UserResponse, UserUpdate, UserInDB
from app.core.database import JSONDatabase
from app.core.exceptions import NotFoundException, ForbiddenException
from app.dependencies import get_current_active_user, get_current_admin_user
from datetime import datetime

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("", response_model=List[UserResponse])
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    role: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """
    ดูรายการผู้ใช้ทั้งหมด (เฉพาะ admin)
    
    - **skip**: ข้ามกี่รายการ
    - **limit**: แสดงสูงสุดกี่รายการ
    - **role**: กรองตาม role (optional)
    """
    db = JSONDatabase("users.json")
    
    if role:
        users = await db.filter(role=role)
    else:
        users = await db.get_all()
    
    # Pagination
    users = users[skip : skip + limit]
    
    return [UserResponse(**user) for user in users]

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    ดูข้อมูลผู้ใช้ตาม ID
    
    - User ทั่วไปดูได้เฉพาะข้อมูลตัวเอง
    - Admin ดูได้ทั้งหมด
    """
    db = JSONDatabase("users.json")
    user = await db.get_by_id(user_id)
    
    if not user:
        raise NotFoundException(f"User with id {user_id} not found")
    
    # ตรวจสอบสิทธิ์
    if current_user.role != "admin" and current_user.id != user_id:
        raise ForbiddenException("Not enough permissions to view this user")
    
    return UserResponse(**user)

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    อัพเดทข้อมูลผู้ใช้
    
    - User ทั่วไปแก้ไขได้เฉพาะข้อมูลตัวเอง
    - Admin แก้ไขได้ทั้งหมด
    """
    db = JSONDatabase("users.json")
    user = await db.get_by_id(user_id)
    
    if not user:
        raise NotFoundException(f"User with id {user_id} not found")
    
    # ตรวจสอบสิทธิ์
    if current_user.role != "admin" and current_user.id != user_id:
        raise ForbiddenException("Not enough permissions to update this user")
    
    # Prepare updates
    update_data = user_update.dict(exclude_unset=True)
    
    # ถ้ามีการเปลี่ยน password ให้ hash
    if "password" in update_data:
        from app.core.security import get_password_hash
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    update_data["updated_at"] = datetime.utcnow().isoformat()
    
    updated_user = await db.update(user_id, update_data)
    return UserResponse(**updated_user)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """
    ลบผู้ใช้ (เฉพาะ admin)
    """
    db = JSONDatabase("users.json")
    user = await db.get_by_id(user_id)
    
    if not user:
        raise NotFoundException(f"User with id {user_id} not found")
    
    # ห้ามลบตัวเอง
    if current_user.id == user_id:
        raise ForbiddenException("Cannot delete yourself")
    
    await db.delete(user_id)
    return None