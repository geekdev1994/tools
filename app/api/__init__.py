"""
API Routers
"""
from app.api.accounts import router as accounts_router
from app.api.transactions import router as transactions_router
from app.api.categories import router as categories_router
from app.api.devices import router as devices_router
from app.api.email import router as email_router
from app.api.user_accounts import router as user_accounts_router
from app.api.tools import router as tools_router

__all__ = [
    "accounts_router",
    "transactions_router",
    "categories_router",
    "devices_router",
    "email_router",
    "user_accounts_router",
    "tools_router",
]
