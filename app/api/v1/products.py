from fastapi import APIRouter, Depends, Query, status
from typing import List, Optional

from app.models.product import ProductCreate, ProductUpdate, ProductResponse, ProductInDB
from app.models.user import UserInDB
from app.core.database import JSONDatabase
from app.core.exceptions import NotFoundException
from app.dependencies import get_current_active_user, get_current_admin_user

import uuid
from datetime import datetime

router = APIRouter(prefix="/products", tags=["Products"])

@router.get("", response_model=List[ProductResponse])
async def get_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    category: Optional[str] = None,
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0)
):
    """
    ดูรายการสินค้าทั้งหมด (ไม่ต้อง login)
    
    - **skip**: ข้ามกี่รายการ
    - **limit**: แสดงสูงสุดกี่รายการ
    - **category**: กรองตามหมวดหมู่
    - **min_price**: ราคาขั้นต่ำ
    - **max_price**: ราคาสูงสุด
    """
    db = JSONDatabase("products.json")
    
    products = await db.get_all()
    
    # Filter by category
    if category:
        products = [p for p in products if p.get("category") == category]
    
    # Filter by price range
    if min_price is not None:
        products = [p for p in products if p.get("price", 0) >= min_price]
    
    if max_price is not None:
        products = [p for p in products if p.get("price", 0) <= max_price]
    
    # Pagination
    products = products[skip : skip + limit]
    
    return [ProductResponse(**product) for product in products]

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str):
    """
    ดูรายละเอียดสินค้า (ไม่ต้อง login)
    """
    db = JSONDatabase("products.json")
    product = await db.get_by_id(product_id)
    
    if not product:
        raise NotFoundException(f"Product with id {product_id} not found")
    
    return ProductResponse(**product)

@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductCreate,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """
    สร้างสินค้าใหม่ (เฉพาะ admin)
    """
    db = JSONDatabase("products.json")
    
    product_data = {
        "id": str(uuid.uuid4()),
        **product.dict(),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": None
    }
    
    await db.create(product_data)
    return ProductResponse(**product_data)

@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_update: ProductUpdate,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """
    อัพเดทสินค้า (เฉพาะ admin)
    """
    db = JSONDatabase("products.json")
    product = await db.get_by_id(product_id)
    
    if not product:
        raise NotFoundException(f"Product with id {product_id} not found")
    
    update_data = product_update.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow().isoformat()
    
    updated_product = await db.update(product_id, update_data)
    return ProductResponse(**updated_product)

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """
    ลบสินค้า (เฉพาะ admin)
    """
    db = JSONDatabase("products.json")
    product = await db.get_by_id(product_id)
    
    if not product:
        raise NotFoundException(f"Product with id {product_id} not found")
    
    await db.delete(product_id)
    return None