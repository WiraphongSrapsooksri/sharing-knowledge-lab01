from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

class OrderItem(BaseModel):
    product_id: str
    product_name: str
    quantity: int = Field(..., gt=0)
    price: float = Field(..., gt=0)
    
    @property
    def subtotal(self) -> float:
        return self.quantity * self.price

class OrderBase(BaseModel):
    user_id: str
    items: List[OrderItem] = Field(..., min_items=1)
    
class OrderCreate(BaseModel):
    items: List[OrderItem] = Field(..., min_items=1)

class OrderInDB(OrderBase):
    id: str
    status: Literal["pending", "processing", "completed", "cancelled"] = "pending"
    total_amount: float
    created_at: str
    updated_at: Optional[str] = None

class OrderResponse(OrderInDB):
    class Config:
        from_attributes = True

class OrderUpdateStatus(BaseModel):
    status: Literal["pending", "processing", "completed", "cancelled"]