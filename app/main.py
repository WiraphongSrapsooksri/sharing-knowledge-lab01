from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import time

from app.config import settings
from app.api.v1.router import router as v1_router
from app.api.v2.router import router as v2_router
from app.core.exceptions import (
    NotFoundException,
    UnauthorizedException,
    ForbiddenException,
    BadRequestException,
    ConflictException
)

# Lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown events
    """
    # Startup
    print("Starting up FastAPI Lab...")
    print(f"App Name:\t{settings.APP_NAME}")
    print(f"Version:\t{settings.VERSION}")
    print(f"Debug Mode:\t{settings.DEBUG}")
    
    # Initialize data files if needed
    from app.core.database import JSONDatabase
    from app.core.security import get_password_hash
    import uuid
    from datetime import datetime
    
    # Create default admin user if not exists
    db = JSONDatabase("users.json")
    users = await db.get_all()
    
    if not users:
        print("Creating default admin user...")
        admin_user = {
            "id": str(uuid.uuid4()),
            "username": "admin",
            "email": "admin@example.com",
            "full_name": "System Administrator",
            "hashed_password": get_password_hash("admin123"),
            "role": "admin",
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": None,
            "login_count": 0
        }
        await db.create(admin_user)
        print("Default admin created (username: admin, password: admin123)")
    
    # Create sample products if not exists
    db_products = JSONDatabase("products.json")
    products = await db_products.get_all()
    
    if not products:
        print("Creating sample products...")
        sample_products = [
            {
                "id": str(uuid.uuid4()),
                "name": "Laptop Dell XPS 13",
                "description": "High-performance ultrabook",
                "price": 45900.00,
                "stock": 10,
                "category": "Electronics",
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "iPhone 15 Pro",
                "description": "Latest iPhone model",
                "price": 42900.00,
                "stock": 15,
                "category": "Electronics",
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Nike Air Max",
                "description": "Running shoes",
                "price": 4500.00,
                "stock": 30,
                "category": "Fashion",
                "created_at": datetime.utcnow().isoformat()
            },
        ]
        for product in sample_products:
            await db_products.create(product)
        print(f"Created {len(sample_products)} sample products")
    
    print("Startup complete!")
    
    yield
    
    # Shutdown
    print("Shutting down FastAPI Lab...")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="FastAPI Lab - Learning RESTful API with Authentication",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": exc.errors()
        }
    )

@app.exception_handler(NotFoundException)
async def not_found_exception_handler(request: Request, exc: NotFoundException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(UnauthorizedException)
async def unauthorized_exception_handler(request: Request, exc: UnauthorizedException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers
    )

@app.exception_handler(ForbiddenException)
async def forbidden_exception_handler(request: Request, exc: ForbiddenException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(BadRequestException)
async def bad_request_exception_handler(request: Request, exc: BadRequestException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(ConflictException)
async def conflict_exception_handler(request: Request, exc: ConflictException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Welcome endpoint
    """
    return {
        "message": "Welcome to FastAPI Lab!",
        "version": settings.VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "api": {
            "v1": settings.API_V1_PREFIX,
            "v2": settings.API_V2_PREFIX
        }
    }

# Health check
@app.get("/health", tags=["Root"])
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "timestamp": time.time()
    }

# Include API routers
app.include_router(v1_router, prefix=settings.API_V1_PREFIX)
app.include_router(v2_router, prefix=settings.API_V2_PREFIX)