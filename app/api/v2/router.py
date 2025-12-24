from fastapi import APIRouter
from app.api.v2 import auth, users

router = APIRouter()

# Include all v2 routers
router.include_router(auth.router)
router.include_router(users.router)

# V2 can reuse V1 routers for products and orders if no changes needed
from app.api.v1 import products, orders

router.include_router(products.router)
router.include_router(orders.router)