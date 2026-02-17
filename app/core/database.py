"""
Database Configuration and Session Management
Supports both SQLite (local dev) and PostgreSQL (Neon production)
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# Determine if using SQLite or PostgreSQL
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# Create engine with appropriate settings
if is_sqlite:
    # SQLite requires check_same_thread=False
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL - use connection pooling for production
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,  # Verify connections before using
        pool_size=5,
        max_overflow=10
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    from app.models import account, transaction, category, processed_email, user_account, import_history  # noqa
    Base.metadata.create_all(bind=engine)
    print(f"Database initialized: {'SQLite' if is_sqlite else 'PostgreSQL'}")
