from fastapi import APIRouter
from app.api.v1 import auth, users, products, orders

router = APIRouter()

# Include all v1 routers
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(products.router)
router.include_router(orders.router)