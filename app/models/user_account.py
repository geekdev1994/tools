"""
UserAccount Model - Represents user's financial accounts (bank, credit card, wallet, etc.)
Each account can optionally have a linked parser for automatic email parsing.
"""
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class AccountType(str, enum.Enum):
    """Types of financial accounts"""
    BANK_SAVINGS = "bank_savings"
    BANK_CURRENT = "bank_current"
    CREDIT_CARD = "credit_card"
    WALLET = "wallet"  # Paytm, PhonePe, GPay, etc.
    CASH = "cash"
    INVESTMENT = "investment"
    OTHER = "other"


class UserAccount(Base):
    """
    UserAccount represents a user's financial account.
    
    Examples:
    - HDFC Savings Account (bank_savings)
    - ICICI Credit Card XX0001 (credit_card) - linked to ICICI parser
    - Paytm Wallet (wallet)
    - Cash (cash)
    
    Transactions are linked to user accounts, not parsers directly.
    """
    __tablename__ = "user_accounts"

    id = Column(String(36), primary_key=True, index=True)
    
    # Basic Info
    name = Column(String(100), nullable=False)  # e.g., "HDFC Savings", "ICICI Credit Card"
    account_type = Column(String(20), nullable=False, default="other")  # AccountType enum value
    
    # Institution details
    institution = Column(String(100), nullable=True)  # e.g., "HDFC Bank", "ICICI Bank", "Paytm"
    account_number_last4 = Column(String(4), nullable=True)  # Last 4 digits for identification
    
    # Balance tracking
    currency = Column(String(3), default="INR")
    initial_balance = Column(Float, default=0.0)  # Starting balance when account was added
    current_balance = Column(Float, default=0.0)  # Calculated or manually updated
    
    # UI customization
    color = Column(String(7), nullable=True)  # Hex color e.g., "#FF5733"
    icon = Column(String(50), nullable=True)  # SF Symbol name e.g., "creditcard.fill"
    
    # Linked parser (optional) - for automatic email parsing
    linked_parser_id = Column(String(36), ForeignKey("accounts.id"), nullable=True)
    
    # Settings
    is_active = Column(Boolean, default=True)  # Show in transaction dropdowns
    include_in_total = Column(Boolean, default=True)  # Include in total balance calculation
    
    # Transaction source preference
    # "email" - primarily from email parsing
    # "manual" - primarily manual entry
    # "import" - primarily from file imports
    # "mixed" - combination of sources
    primary_source = Column(String(20), default="mixed")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<UserAccount(id={self.id}, name={self.name}, type={self.account_type})>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response"""
        return {
            "id": self.id,
            "name": self.name,
            "account_type": self.account_type,
            "institution": self.institution,
            "account_number_last4": self.account_number_last4,
            "currency": self.currency,
            "initial_balance": self.initial_balance,
            "current_balance": self.current_balance,
            "color": self.color,
            "icon": self.icon,
            "linked_parser_id": self.linked_parser_id,
            "is_active": self.is_active,
            "include_in_total": self.include_in_total,
            "primary_source": self.primary_source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
