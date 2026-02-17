"""
ImportHistory Model - Tracks imported files to prevent duplicates
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text

from app.core.database import Base


class ImportHistory(Base):
    """
    ImportHistory tracks files that have been imported to prevent duplicates.
    Uses file hash (SHA256) for reliable duplicate detection.
    """
    __tablename__ = "import_history"

    id = Column(String(36), primary_key=True, index=True)
    
    # File identification
    filename = Column(String(255), nullable=False)  # Original filename
    file_hash = Column(String(64), nullable=False, unique=True, index=True)  # SHA256 hash
    file_size = Column(Integer, nullable=True)  # File size in bytes
    
    # Import type
    file_type = Column(String(50), nullable=False)  # "paytm_excel", "hdfc_statement", etc.
    
    # Import results
    transaction_count = Column(Integer, default=0)  # Number of transactions imported
    skipped_count = Column(Integer, default=0)  # Number of rows skipped
    
    # Status
    status = Column(String(20), default="completed")  # completed, partial, failed
    error_message = Column(Text, nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Timestamps
    imported_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ImportHistory(id={self.id}, filename={self.filename}, status={self.status})>"
