"""
Transaction Model - Represents a parsed expense/income transaction
"""
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.core.database import Base


class Transaction(Base):
    """
    Transaction stores parsed expense/income data.
    Matches the CSV export format:
    Ledger, Category, Subcategory, Currency, Price, Account, Recorder, Date, Time, Note, Transaction
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    
    # External reference (email message ID for deduplication)
    source_email_id = Column(String(255), nullable=True, unique=True, index=True)
    idempotency_key = Column(String(255), nullable=True, unique=True, index=True)
    
    # Core transaction fields (matches CSV export format)
    ledger = Column(String(100), nullable=True)  # e.g., "Personal", "Business"
    category_name = Column(String(100), nullable=True)  # e.g., "Food & Dining"
    subcategory = Column(String(100), nullable=True)  # e.g., "Restaurants"
    currency = Column(String(3), default="INR")
    
    # Amount - always positive, type determines debit/credit
    parsed_amount = Column(Float, nullable=True)
    
    # Account/Card name
    account_name = Column(String(100), nullable=True)  # e.g., "ICICI Bank Credit Card XX0001"
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=True)  # Parser profile
    
    # User Account (bank account, credit card, wallet, etc.)
    user_account_id = Column(String(36), ForeignKey("user_accounts.id"), nullable=True)
    
    # Recorder - who/what created this entry
    recorder = Column(String(50), default="Auto")  # "Auto" or "Manual"
    
    # Date and Time (separate fields for CSV export)
    parsed_date = Column(DateTime, nullable=True)
    parsed_time = Column(String(8), nullable=True)  # HH:mm:ss format
    
    # Merchant/Description (Note field in CSV)
    parsed_vendor = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Transaction Type - "Expense" or "Income"
    transaction_type = Column(String(10), default="Expense")
    
    # Processing status
    status = Column(String(20), default="pending")  # pending, confirmed, ignored
    confidence_score = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Transaction(id={self.id}, vendor={self.parsed_vendor}, amount={self.parsed_amount})>"
    
    def to_csv_row(self) -> dict:
        """Convert to CSV export format"""
        return {
            "Ledger": self.ledger or "",
            "Category": self.category_name or "",
            "Subcategory": self.subcategory or "",
            "Currency": self.currency or "INR",
            "Price": self.parsed_amount or 0.0,
            "Account": self.account_name or "",
            "Recorder": self.recorder or "Auto",
            "Date": self.parsed_date.strftime("%Y-%m-%d") if self.parsed_date else "",
            "Time": self.parsed_time or "",
            "Note": self.parsed_vendor or "",
            "Transaction": self.transaction_type or "Expense"
        }
