"""
UserAccount Schemas - Request/Response DTOs for user financial accounts
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class AccountTypeEnum(str, Enum):
    """Types of financial accounts"""
    BANK_SAVINGS = "bank_savings"
    BANK_CURRENT = "bank_current"
    CREDIT_CARD = "credit_card"
    WALLET = "wallet"
    CASH = "cash"
    INVESTMENT = "investment"
    OTHER = "other"


class UserAccountBase(BaseModel):
    """Base schema for UserAccount"""
    name: str = Field(..., min_length=1, max_length=100, description="Account display name")
    account_type: AccountTypeEnum = Field(default=AccountTypeEnum.OTHER, description="Type of account")
    institution: Optional[str] = Field(None, max_length=100, description="Bank/Provider name")
    account_number_last4: Optional[str] = Field(None, max_length=4, description="Last 4 digits")
    currency: str = Field(default="INR", max_length=3)
    initial_balance: float = Field(default=0.0, description="Starting balance")
    color: Optional[str] = Field(None, description="Hex color for UI e.g., #FF5733")
    icon: Optional[str] = Field(None, description="SF Symbol name e.g., creditcard.fill")
    linked_parser_id: Optional[str] = Field(None, description="Linked parser profile ID")
    is_active: bool = Field(default=True, description="Show in transaction dropdowns")
    include_in_total: bool = Field(default=True, description="Include in total balance")
    primary_source: str = Field(default="mixed", description="Primary transaction source")


class UserAccountCreate(UserAccountBase):
    """Schema for creating a user account"""
    id: Optional[str] = None  # Can be provided or auto-generated


class UserAccountUpdate(BaseModel):
    """Schema for updating a user account (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    account_type: Optional[AccountTypeEnum] = None
    institution: Optional[str] = None
    account_number_last4: Optional[str] = None
    currency: Optional[str] = None
    initial_balance: Optional[float] = None
    current_balance: Optional[float] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    linked_parser_id: Optional[str] = None
    is_active: Optional[bool] = None
    include_in_total: Optional[bool] = None
    primary_source: Optional[str] = None


class UserAccountResponse(UserAccountBase):
    """Schema for user account response"""
    id: str
    current_balance: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserAccountListResponse(BaseModel):
    """Schema for list of user accounts"""
    id: str
    name: str
    account_type: str
    institution: Optional[str] = None
    account_number_last4: Optional[str] = None
    currency: str
    current_balance: float
    color: Optional[str] = None
    icon: Optional[str] = None
    is_active: bool
    linked_parser_id: Optional[str] = None

    class Config:
        from_attributes = True


class UserAccountWithTransactionCount(UserAccountListResponse):
    """User account with transaction count"""
    transaction_count: int = 0


class TransferRequest(BaseModel):
    """Request for transferring between accounts"""
    from_account_id: str = Field(..., description="Source account ID")
    to_account_id: str = Field(..., description="Destination account ID")
    amount: float = Field(..., gt=0, description="Amount to transfer")
    description: Optional[str] = Field(None, description="Transfer description")
    date: Optional[datetime] = Field(None, description="Transfer date")


class TransferResponse(BaseModel):
    """Response for transfer operation"""
    success: bool
    message: str
    from_transaction_id: Optional[int] = None
    to_transaction_id: Optional[int] = None
