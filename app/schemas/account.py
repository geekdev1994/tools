"""
Account Schemas - Request/Response DTOs
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AccountBase(BaseModel):
    """Base schema for Account"""
    name: str = Field(..., min_length=1, max_length=100)
    card_last_four: Optional[str] = Field(None, max_length=4)
    sender_email: Optional[str] = None
    sender_name: Optional[str] = None
    subject_pattern: Optional[str] = None
    
    # Regex patterns
    amount_regex: str = Field(..., description="Regex to extract amount")
    date_regex: str = Field(..., description="Regex to extract date")
    merchant_regex: str = Field(..., description="Regex to extract merchant")
    account_regex: Optional[str] = Field(None, description="Regex to extract card/account")
    time_regex: Optional[str] = Field(None, description="Regex to extract time")
    
    sample_email_body: Optional[str] = None
    
    is_active: bool = True
    currency_default: str = "INR"
    default_transaction_type: str = "Expense"


class AccountCreate(AccountBase):
    """Schema for creating an account"""
    id: Optional[str] = None  # Can be provided or auto-generated


class AccountUpdate(BaseModel):
    """Schema for updating an account (all fields optional)"""
    name: Optional[str] = None
    card_last_four: Optional[str] = None
    sender_email: Optional[str] = None
    sender_name: Optional[str] = None
    subject_pattern: Optional[str] = None
    
    amount_regex: Optional[str] = None
    date_regex: Optional[str] = None
    merchant_regex: Optional[str] = None
    account_regex: Optional[str] = None
    time_regex: Optional[str] = None
    
    sample_email_body: Optional[str] = None
    
    is_active: Optional[bool] = None
    currency_default: Optional[str] = None
    default_transaction_type: Optional[str] = None


class AccountResponse(AccountBase):
    """Schema for account response"""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AccountListResponse(BaseModel):
    """Schema for list of accounts"""
    id: str
    name: str
    card_last_four: Optional[str] = None
    sender_email: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
