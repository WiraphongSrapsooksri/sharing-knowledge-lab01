from fastapi import APIRouter, Depends, Query, status
from typing import List, Optional
from datetime import datetime

from app.models.user import UserResponse, UserUpdate, UserInDB
from app.core.database import JSONDatabase
from app.core.exceptions import NotFoundException, ForbiddenException, BadRequestException
from app.dependencies import get_current_active_user, get_current_admin_user

router = APIRouter(prefix="/users", tags=["Users V2"])

@router.get("", response_model=dict)
async def get_users_v2(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    role: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = Query("created_at", regex="^(created_at|username|email|login_count)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """
    ดูรายการผู้ใช้ทั้งหมด (V2 - Enhanced with search, sort, pagination)
    
    New features:
    - Search by username/email
    - Sort by multiple fields
    - Better pagination with metadata
    """
    db = JSONDatabase("users.json")
    
    users = await db.get_all()
    
    # Search filter
    if search:
        search_lower = search.lower()
        users = [
            u for u in users 
            if search_lower in u.get("username", "").lower() 
            or search_lower in u.get("email", "").lower()
            or search_lower in u.get("full_name", "").lower()
        ]
    
    # Role filter
    if role:
        users = [u for u in users if u.get("role") == role]
    
    # Sorting
    reverse = (order == "desc")
    users.sort(key=lambda x: x.get(sort_by, ""), reverse=reverse)
    
    # Count total before pagination
    total = len(users)
    
    # Pagination
    users_page = users[skip : skip + limit]
    
    return {
        "data": [UserResponse(**user) for user in users_page],
        "pagination": {
            "total": total,
            "skip": skip,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }
    }

@router.get("/stats", response_model=dict)
async def get_users_stats(
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """
    ดูสถิติผู้ใช้ (V2 - New endpoint)
    """
    db = JSONDatabase("users.json")
    users = await db.get_all()
    
    total_users = len(users)
    active_users = len([u for u in users if u.get("is_active", True)])
    admin_users = len([u for u in users if u.get("role") == "admin"])
    regular_users = len([u for u in users if u.get("role") == "user"])
    
    # Calculate average login count
    total_logins = sum(u.get("login_count", 0) for u in users)
    avg_logins = total_logins / total_users if total_users > 0 else 0
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": total_users - active_users,
        "admin_users": admin_users,
        "regular_users": regular_users,
        "average_logins_per_user": round(avg_logins, 2),
        "total_logins": total_logins
    }

@router.get("/{user_id}/activity", response_model=dict)
async def get_user_activity(
    user_id: str,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    ดูกิจกรรมของผู้ใช้ (V2 - New endpoint)
    
    - User ทั่วไปดูได้เฉพาะข้อมูลตัวเอง
    - Admin ดูได้ทั้งหมด
    """
    db = JSONDatabase("users.json")
    user = await db.get_by_id(user_id)
    
    if not user:
        raise NotFoundException(f"User with id {user_id} not found")
    
    # ตรวจสอบสิทธิ์
    if current_user.role != "admin" and current_user.id != user_id:
        raise ForbiddenException("Not enough permissions to view this user's activity")
    
    # Get user's orders
    db_orders = JSONDatabase("orders.json")
    orders = await db_orders.filter(user_id=user_id)
    
    return {
        "user_id": user_id,
        "username": user["username"],
        "login_count": user.get("login_count", 0),
        "last_login": user.get("last_login"),
        "created_at": user["created_at"],
        "total_orders": len(orders),
        "pending_orders": len([o for o in orders if o.get("status") == "pending"]),
        "completed_orders": len([o for o in orders if o.get("status") == "completed"]),
        "cancelled_orders": len([o for o in orders if o.get("status") == "cancelled"]),
        "total_spent": sum(o.get("total_amount", 0) for o in orders)
    }

@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """
    ปิดการใช้งานบัญชีผู้ใช้ (V2 - New endpoint)
    """
    db = JSONDatabase("users.json")
    user = await db.get_by_id(user_id)
    
    if not user:
        raise NotFoundException(f"User with id {user_id} not found")
    
    if current_user.id == user_id:
        raise BadRequestException("Cannot deactivate yourself")
    
    await db.update(user_id, {
        "is_active": False,
        "updated_at": datetime.utcnow().isoformat()
    })
    
    return {"message": f"User {user['username']} has been deactivated"}

@router.post("/{user_id}/activate")
async def activate_user(
    user_id: str,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """
    เปิดการใช้งานบัญชีผู้ใช้ (V2 - New endpoint)
    """
    db = JSONDatabase("users.json")
    user = await db.get_by_id(user_id)
    
    if not user:
        raise NotFoundException(f"User with id {user_id} not found")
    
    await db.update(user_id, {
        "is_active": True,
        "updated_at": datetime.utcnow().isoformat()
    })
    
    return {"message": f"User {user['username']} has been activated"}