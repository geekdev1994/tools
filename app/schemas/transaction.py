"""
Transaction Schemas - Request/Response DTOs
Compatible with existing iOS app TransactionResponse
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TransactionBase(BaseModel):
    """Base schema for Transaction"""
    ledger: Optional[str] = None
    category_name: Optional[str] = None
    subcategory: Optional[str] = None
    currency: str = "INR"
    parsed_amount: Optional[float] = None
    account_name: Optional[str] = None
    recorder: str = "Auto"
    parsed_date: Optional[datetime] = None
    parsed_time: Optional[str] = None  # HH:mm:ss
    parsed_vendor: Optional[str] = None
    notes: Optional[str] = None
    transaction_type: str = "Expense"
    status: str = "pending"
    confidence_score: float = 0.0


class TransactionCreate(TransactionBase):
    """Schema for creating a transaction"""
    source_email_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    account_id: Optional[str] = None


class TransactionUpdate(BaseModel):
    """
    Schema for updating a transaction.
    Compatible with iOS TransactionUpdate struct.
    """
    category_name: Optional[str] = None
    subcategory: Optional[str] = None
    notes: Optional[str] = None
    parsed_amount: Optional[float] = None
    parsed_vendor: Optional[str] = None
    parsed_date: Optional[datetime] = None
    parsed_time: Optional[str] = None
    ledger: Optional[str] = None
    transaction_type: Optional[str] = None
    status: Optional[str] = None
    account_name: Optional[str] = None


class TransactionResponse(BaseModel):
    """
    Schema for transaction response.
    Compatible with iOS TransactionResponse struct.
    """
    id: int
    
    # Fields expected by iOS app
    parsed_amount: Optional[float] = None
    parsed_vendor: Optional[str] = None
    parsed_date: Optional[datetime] = None
    category_name: Optional[str] = None
    notes: Optional[str] = None
    status: str = "pending"
    confidence_score: float = 0.0
    
    # Additional fields for enhanced functionality
    ledger: Optional[str] = None
    subcategory: Optional[str] = None
    currency: str = "INR"
    account_name: Optional[str] = None
    recorder: str = "Auto"
    parsed_time: Optional[str] = None
    transaction_type: str = "Expense"
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TransactionCSVRow(BaseModel):
    """Schema matching CSV export format"""
    Ledger: str = ""
    Category: str = ""
    Subcategory: str = ""
    Currency: str = "INR"
    Price: float = 0.0
    Account: str = ""
    Recorder: str = "Auto"
    Date: str = ""  # YYYY-MM-DD
    Time: str = ""  # HH:mm:ss
    Note: str = ""
    Transaction: str = "Expense"
