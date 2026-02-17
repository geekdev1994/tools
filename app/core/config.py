"""
Application Configuration
"""
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "SpendWise - Smart Expense Tracker"
    APP_VERSION: str = "1.0.0"
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
    # Credentials are stored in: credentials/google_oauth_credentials.json
    # Tokens are stored in: credentials/google_oauth_token.pickle
    # Run: python -m app.services.gmail_oauth to set up OAuth
    
    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
