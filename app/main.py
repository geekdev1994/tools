"""
Expense Tracker System - FastAPI Server
Main application entry point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api import (
    accounts_router, transactions_router, categories_router, 
    devices_router, email_router, user_accounts_router, tools_router
)
from app.services.seed_data import seed_default_categories


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle events"""
    # Startup
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    init_db()
    seed_default_categories()
    print("Database initialized")
    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API for Expense Tracker iOS App - Email parsing and transaction management",
    lifespan=lifespan
)

# CORS middleware for iOS app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers - without API prefix for iOS app compatibility
app.include_router(accounts_router)
app.include_router(transactions_router)
app.include_router(categories_router)
app.include_router(devices_router)
app.include_router(email_router)
app.include_router(user_accounts_router)
app.include_router(tools_router)


@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.DEBUG
    )
