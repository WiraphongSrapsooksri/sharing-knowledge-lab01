from fastapi import APIRouter, Depends, Query, status
from typing import List, Optional

from app.models.order import OrderCreate, OrderResponse, OrderUpdateStatus, OrderInDB
from app.models.user import UserInDB
from app.core.database import JSONDatabase
from app.core.exceptions import NotFoundException, BadRequestException, ForbiddenException
from app.dependencies import get_current_active_user, get_current_admin_user

import uuid
from datetime import datetime

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.get("", response_model=List[OrderResponse])
async def get_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    ดูรายการ orders
    
    - User ทั่วไปดูได้เฉพาะ order ตัวเอง
    - Admin ดูได้ทั้งหมด
    """
    db = JSONDatabase("orders.json")
    
    # CRITICAL: ต้องตรวจสอบ role และกรอง user_id อย่างถูกต้อง
    if current_user.role == "admin":
        # Admin เท่านั้นที่ดูได้ทั้งหมด
        orders = await db.get_all()
        print(f"[ADMIN] User {current_user.username} requested all orders: {len(orders)} found")
    else:
        # User ธรรมดาต้องดูเฉพาะของตัวเอง
        orders = await db.filter(user_id=current_user.id)
        print(f"[USER] User {current_user.username} (ID: {current_user.id}) requested orders: {len(orders)} found")
    
    # Filter by status ถ้ามี
    if status:
        orders = [o for o in orders if o.get("status") == status]
    
    # Pagination
    total_before_pagination = len(orders)
    orders = orders[skip : skip + limit]
    
    print(f"[RESPONSE] Returning {len(orders)} orders (total: {total_before_pagination})")
    
    return [OrderResponse(**order) for order in orders]

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    ดูรายละเอียด order
    
    - User ทั่วไปดูได้เฉพาะ order ตัวเอง
    - Admin ดูได้ทั้งหมด
    """
    db = JSONDatabase("orders.json")
    order = await db.get_by_id(order_id)
    
    if not order:
        raise NotFoundException(f"Order with id {order_id} not found")
    
    # CRITICAL: ตรวจสอบสิทธิ์
    if current_user.role != "admin" and order["user_id"] != current_user.id:
        print(f"[FORBIDDEN] User {current_user.username} (ID: {current_user.id}) tried to access order {order_id} (owner: {order['user_id']})")
        raise ForbiddenException("Not enough permissions to view this order")
    
    print(f"[ACCESS GRANTED] User {current_user.username} accessed order {order_id}")
    return OrderResponse(**order)

@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order: OrderCreate,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    สร้าง order ใหม่ (ต้อง login)
    """
    db_products = JSONDatabase("products.json")
    db_orders = JSONDatabase("orders.json")
    
    # ตรวจสอบสินค้าและ stock
    total_amount = 0
    for item in order.items:
        product = await db_products.get_by_id(item.product_id)
        
        if not product:
            raise BadRequestException(f"Product {item.product_id} not found")
        
        if product["stock"] < item.quantity:
            raise BadRequestException(
                f"Insufficient stock for product {product['name']}. Available: {product['stock']}"
            )
        
        total_amount += item.quantity * item.price
    
    # CRITICAL: ใช้ user_id จาก current_user (token) ไม่ใช่จาก request
    order_data = {
        "id": str(uuid.uuid4()),
        "user_id": current_user.id,  # บังคับใช้ ID จาก token
        "items": [item.dict() for item in order.items],
        "status": "pending",
        "total_amount": total_amount,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": None
    }
    
    print(f"[ORDER CREATED] User {current_user.username} (ID: {current_user.id}) created order {order_data['id']}")
    
    # ลด stock
    for item in order.items:
        product = await db_products.get_by_id(item.product_id)
        new_stock = product["stock"] - item.quantity
        await db_products.update(item.product_id, {
            "stock": new_stock,
            "updated_at": datetime.utcnow().isoformat()
        })
    
    await db_orders.create(order_data)
    return OrderResponse(**order_data)

@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    status_update: OrderUpdateStatus,
    current_user: UserInDB = Depends(get_current_admin_user)  # CRITICAL: เฉพาะ admin!
):
    """
    อัพเดทสถานะ order (เฉพาะ admin)
    """
    db = JSONDatabase("orders.json")
    order = await db.get_by_id(order_id)
    
    if not order:
        raise NotFoundException(f"Order with id {order_id} not found")
    
    print(f"[STATUS UPDATE] Admin {current_user.username} changed order {order_id} status to {status_update.status}")
    
    update_data = {
        "status": status_update.status,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    updated_order = await db.update(order_id, update_data)
    return OrderResponse(**updated_order)

@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_order(
    order_id: str,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    ยกเลิก order
    
    - User ทั่วไปยกเลิกได้เฉพาะ order ตัวเอง (ถ้ายังเป็น pending)
    - Admin ยกเลิกได้ทั้งหมด
    """
    db_orders = JSONDatabase("orders.json")
    db_products = JSONDatabase("products.json")
    
    order = await db_orders.get_by_id(order_id)
    
    if not order:
        raise NotFoundException(f"Order with id {order_id} not found")
    
    # CRITICAL: ตรวจสอบสิทธิ์
    if current_user.role != "admin":
        # User ธรรมดาต้องตรวจสอบ 2 อย่าง
        if order["user_id"] != current_user.id:
            print(f"[FORBIDDEN] User {current_user.username} tried to cancel order {order_id} (not owner)")
            raise ForbiddenException("Not enough permissions to cancel this order")
        
        if order["status"] != "pending":
            raise BadRequestException("Can only cancel pending orders")
    
    print(f"[ORDER CANCELLED] User {current_user.username} cancelled order {order_id}")
    
    # คืน stock
    for item in order["items"]:
        product = await db_products.get_by_id(item["product_id"])
        if product:
            new_stock = product["stock"] + item["quantity"]
            await db_products.update(item["product_id"], {
                "stock": new_stock,
                "updated_at": datetime.utcnow().isoformat()
            })
    
    # อัพเดทสถานะเป็น cancelled
    await db_orders.update(order_id, {
        "status": "cancelled",
        "updated_at": datetime.utcnow().isoformat()
    })
    
    return None