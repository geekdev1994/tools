"""
User Account API Endpoints
CRUD operations for user financial accounts (bank accounts, credit cards, wallets, etc.)
"""
import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models import UserAccount, Transaction
from app.schemas.user_account import (
    UserAccountCreate, UserAccountUpdate, UserAccountResponse, 
    UserAccountListResponse, UserAccountWithTransactionCount,
    TransferRequest, TransferResponse
)

router = APIRouter(prefix="/user-accounts", tags=["user-accounts"])


@router.get("/", response_model=List[UserAccountWithTransactionCount])
def list_user_accounts(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    account_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all user financial accounts with transaction counts.
    
    - **is_active**: Filter by active status
    - **account_type**: Filter by type (bank_savings, credit_card, wallet, etc.)
    """
    query = db.query(UserAccount)
    
    if is_active is not None:
        query = query.filter(UserAccount.is_active == is_active)
    
    if account_type:
        query = query.filter(UserAccount.account_type == account_type)
    
    accounts = query.order_by(UserAccount.name).offset(skip).limit(limit).all()
    
    # Get transaction counts for each account
    result = []
    for account in accounts:
        txn_count = db.query(func.count(Transaction.id)).filter(
            Transaction.user_account_id == account.id
        ).scalar() or 0
        
        account_dict = {
            "id": account.id,
            "name": account.name,
            "account_type": account.account_type,
            "institution": account.institution,
            "account_number_last4": account.account_number_last4,
            "currency": account.currency,
            "current_balance": account.current_balance,
            "color": account.color,
            "icon": account.icon,
            "is_active": account.is_active,
            "linked_parser_id": account.linked_parser_id,
            "transaction_count": txn_count
        }
        result.append(account_dict)
    
    return result


@router.get("/{account_id}", response_model=UserAccountResponse)
def get_user_account(account_id: str, db: Session = Depends(get_db)):
    """Get a specific user account by ID"""
    account = db.query(UserAccount).filter(UserAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="User account not found")
    return account


@router.post("/", response_model=UserAccountResponse, status_code=status.HTTP_201_CREATED)
def create_user_account(account_data: UserAccountCreate, db: Session = Depends(get_db)):
    """
    Create a new user financial account.
    
    Account types:
    - bank_savings: Savings bank account
    - bank_current: Current/Checking account
    - credit_card: Credit card
    - wallet: Digital wallet (Paytm, PhonePe, GPay)
    - cash: Cash
    - investment: Investment account
    - other: Other
    """
    account_id = account_data.id or str(uuid.uuid4())
    
    # Check if ID already exists
    existing = db.query(UserAccount).filter(UserAccount.id == account_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Account with this ID already exists")
    
    account = UserAccount(
        id=account_id,
        name=account_data.name,
        account_type=account_data.account_type.value if hasattr(account_data.account_type, 'value') else account_data.account_type,
        institution=account_data.institution,
        account_number_last4=account_data.account_number_last4,
        currency=account_data.currency,
        initial_balance=account_data.initial_balance,
        current_balance=account_data.initial_balance,  # Start with initial balance
        color=account_data.color,
        icon=account_data.icon,
        linked_parser_id=account_data.linked_parser_id,
        is_active=account_data.is_active,
        include_in_total=account_data.include_in_total,
        primary_source=account_data.primary_source
    )
    
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.put("/{account_id}", response_model=UserAccountResponse)
def update_user_account(
    account_id: str, 
    account_data: UserAccountUpdate, 
    db: Session = Depends(get_db)
):
    """Update a user account"""
    account = db.query(UserAccount).filter(UserAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="User account not found")
    
    update_data = account_data.model_dump(exclude_unset=True)
    
    # Handle enum conversion
    if 'account_type' in update_data and update_data['account_type'] is not None:
        if hasattr(update_data['account_type'], 'value'):
            update_data['account_type'] = update_data['account_type'].value
    
    for field, value in update_data.items():
        setattr(account, field, value)
    
    account.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_account(
    account_id: str, 
    force: bool = Query(False, description="Force delete even if transactions exist"),
    db: Session = Depends(get_db)
):
    """
    Delete a user account.
    
    - **force**: If True, unlinks transactions from this account before deletion
    """
    account = db.query(UserAccount).filter(UserAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="User account not found")
    
    # Check for linked transactions
    txn_count = db.query(func.count(Transaction.id)).filter(
        Transaction.user_account_id == account_id
    ).scalar() or 0
    
    if txn_count > 0 and not force:
        raise HTTPException(
            status_code=400, 
            detail=f"Account has {txn_count} linked transactions. Use force=true to unlink and delete."
        )
    
    if txn_count > 0:
        # Unlink transactions
        db.query(Transaction).filter(
            Transaction.user_account_id == account_id
        ).update({Transaction.user_account_id: None})
    
    db.delete(account)
    db.commit()
    return None


@router.get("/{account_id}/transactions")
def get_account_transactions(
    account_id: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get transactions for a specific user account"""
    account = db.query(UserAccount).filter(UserAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="User account not found")
    
    transactions = db.query(Transaction).filter(
        Transaction.user_account_id == account_id
    ).order_by(Transaction.parsed_date.desc()).offset(skip).limit(limit).all()
    
    return {
        "account_id": account_id,
        "account_name": account.name,
        "total_count": db.query(func.count(Transaction.id)).filter(
            Transaction.user_account_id == account_id
        ).scalar() or 0,
        "transactions": [
            {
                "id": t.id,
                "date": t.parsed_date.strftime("%Y-%m-%d") if t.parsed_date else None,
                "vendor": t.parsed_vendor,
                "amount": t.parsed_amount,
                "type": t.transaction_type,
                "category": t.category_name,
                "recorder": t.recorder
            }
            for t in transactions
        ]
    }


@router.post("/transfer", response_model=TransferResponse)
def transfer_between_accounts(
    transfer: TransferRequest,
    db: Session = Depends(get_db)
):
    """
    Transfer amount between two user accounts.
    Creates two linked transactions: expense from source, income to destination.
    """
    # Validate accounts
    from_account = db.query(UserAccount).filter(UserAccount.id == transfer.from_account_id).first()
    to_account = db.query(UserAccount).filter(UserAccount.id == transfer.to_account_id).first()
    
    if not from_account:
        raise HTTPException(status_code=404, detail="Source account not found")
    if not to_account:
        raise HTTPException(status_code=404, detail="Destination account not found")
    if from_account.id == to_account.id:
        raise HTTPException(status_code=400, detail="Cannot transfer to same account")
    
    transfer_date = transfer.date or datetime.utcnow()
    description = transfer.description or f"Transfer to {to_account.name}"
    
    # Create expense transaction (from source)
    expense_txn = Transaction(
        user_account_id=from_account.id,
        account_name=from_account.name,
        parsed_amount=transfer.amount,
        parsed_vendor=f"Transfer to {to_account.name}",
        parsed_date=transfer_date,
        transaction_type="Expense",
        category_name="Transfer",
        recorder="Manual",
        notes=description,
        status="confirmed"
    )
    
    # Create income transaction (to destination)
    income_txn = Transaction(
        user_account_id=to_account.id,
        account_name=to_account.name,
        parsed_amount=transfer.amount,
        parsed_vendor=f"Transfer from {from_account.name}",
        parsed_date=transfer_date,
        transaction_type="Income",
        category_name="Transfer",
        recorder="Manual",
        notes=description,
        status="confirmed"
    )
    
    db.add(expense_txn)
    db.add(income_txn)
    
    # Update balances
    from_account.current_balance -= transfer.amount
    to_account.current_balance += transfer.amount
    
    db.commit()
    db.refresh(expense_txn)
    db.refresh(income_txn)
    
    return TransferResponse(
        success=True,
        message=f"Transferred {transfer.amount} from {from_account.name} to {to_account.name}",
        from_transaction_id=expense_txn.id,
        to_transaction_id=income_txn.id
    )


@router.post("/{account_id}/recalculate-balance")
def recalculate_balance(account_id: str, db: Session = Depends(get_db)):
    """
    Recalculate current balance based on initial balance and all transactions.
    """
    account = db.query(UserAccount).filter(UserAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="User account not found")
    
    # Get sum of expenses
    expenses = db.query(func.sum(Transaction.parsed_amount)).filter(
        Transaction.user_account_id == account_id,
        Transaction.transaction_type == "Expense"
    ).scalar() or 0
    
    # Get sum of income
    income = db.query(func.sum(Transaction.parsed_amount)).filter(
        Transaction.user_account_id == account_id,
        Transaction.transaction_type == "Income"
    ).scalar() or 0
    
    # Calculate new balance
    new_balance = account.initial_balance + income - expenses
    old_balance = account.current_balance
    account.current_balance = new_balance
    
    db.commit()
    
    return {
        "account_id": account_id,
        "account_name": account.name,
        "initial_balance": account.initial_balance,
        "total_income": income,
        "total_expenses": expenses,
        "old_balance": old_balance,
        "new_balance": new_balance
    }


@router.get("/sync/all")
def sync_all_accounts(db: Session = Depends(get_db)):
    """Get all active user accounts for iOS sync"""
    accounts = db.query(UserAccount).filter(UserAccount.is_active == True).all()
    return {
        "count": len(accounts),
        "accounts": [account.to_dict() for account in accounts]
    }
