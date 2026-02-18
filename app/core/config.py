"""
Application Configuration
"""
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Literal, Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "SpendWise - Smart Expense Tracker"
    APP_VERSION: str = "1.5.0"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "sqlite:///./expense_tracker.db"
    
    # Email Client Type
    # - "imap": Traditional IMAP (for Yahoo, Outlook, custom servers)
    # - "gmail_oauth": Gmail OAuth 2.0 (required for Google Workspace since May 2025)
    EMAIL_CLIENT_TYPE: Literal["imap", "gmail_oauth"] = "imap"
    
    # Email Configuration (IMAP) - For non-Google providers
    IMAP_SERVER: str = ""
    IMAP_PORT: int = 993
    IMAP_USERNAME: str = ""
    IMAP_PASSWORD: str = ""
    IMAP_USE_SSL: bool = True
    EMAIL_POLL_INTERVAL_SECONDS: int = 60
    
    # Gmail OAuth 2.0 Configuration
    # For local dev: credentials/google_oauth_credentials.json and token.pickle
    # For production (Railway): Use these environment variables (base64 encoded)
    GOOGLE_OAUTH_CREDENTIALS: Optional[str] = None  # Base64 encoded credentials JSON
    GOOGLE_OAUTH_TOKEN: Optional[str] = None  # Base64 encoded token pickle
    
    # Auto-start email monitor on startup (useful for production)
    EMAIL_MONITOR_AUTO_START: bool = False
    
    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
