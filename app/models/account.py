"""
Account Model - Represents a credit card email parser configuration
Maps to iOS ParserProfile
"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Text, DateTime, JSON
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON

from app.core.database import Base


class Account(Base):
    """
    Account stores email parser configuration for a credit card.
    This maps to ParserProfile in the iOS app.
    """
    __tablename__ = "accounts"

    id = Column(String(36), primary_key=True, index=True)
    
    # Basic Info
    name = Column(String(100), nullable=False)  # e.g., "ICICI Bank Credit Card"
    card_last_four = Column(String(4), nullable=True)
    
    # Email Matching
    sender_email = Column(String(255), nullable=True)  # e.g., "credit_cards@icicibank.com"
    sender_name = Column(String(100), nullable=True)
    subject_pattern = Column(String(255), nullable=True)  # e.g., "Transaction alert"
    
    # Parser Configuration (regex patterns)
    amount_regex = Column(Text, nullable=False)
    date_regex = Column(Text, nullable=False)
    merchant_regex = Column(Text, nullable=False)
    account_regex = Column(Text, nullable=True)
    time_regex = Column(Text, nullable=True)
    
    # Sample email for testing
    sample_email_body = Column(Text, nullable=True)
    
    # Settings
    is_active = Column(Boolean, default=True)
    currency_default = Column(String(3), default="INR")
    default_transaction_type = Column(String(10), default="Expense")  # "Expense" or "Income"
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Account(id={self.id}, name={self.name})>"
