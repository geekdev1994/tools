"""
Account API Endpoints
CRUD operations for parser profiles/accounts
"""
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Account
from app.schemas import AccountCreate, AccountUpdate, AccountResponse, AccountListResponse

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/", response_model=List[AccountListResponse])
def list_accounts(
    skip: int = 0,
    limit: int = 100,
    is_active: bool = None,
    db: Session = Depends(get_db)
):
    """Get all accounts/parser profiles"""
    query = db.query(Account)
    if is_active is not None:
        query = query.filter(Account.is_active == is_active)
    accounts = query.offset(skip).limit(limit).all()
    return accounts


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(account_id: str, db: Session = Depends(get_db)):
    """Get a specific account by ID"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(account_data: AccountCreate, db: Session = Depends(get_db)):
    """Create a new account/parser profile"""
    # Generate ID if not provided
    account_id = account_data.id or str(uuid.uuid4())
    
    # Check if ID already exists
    existing = db.query(Account).filter(Account.id == account_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Account with this ID already exists")
    
    account = Account(
        id=account_id,
        name=account_data.name,
        card_last_four=account_data.card_last_four,
        sender_email=account_data.sender_email,
        sender_name=account_data.sender_name,
        subject_pattern=account_data.subject_pattern,
        amount_regex=account_data.amount_regex,
        date_regex=account_data.date_regex,
        merchant_regex=account_data.merchant_regex,
        account_regex=account_data.account_regex,
        time_regex=account_data.time_regex,
        sample_email_body=account_data.sample_email_body,
        is_active=account_data.is_active,
        currency_default=account_data.currency_default,
        default_transaction_type=account_data.default_transaction_type,
    )
    
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.put("/{account_id}", response_model=AccountResponse)
def update_account(
    account_id: str,
    account_data: AccountUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing account"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Update only provided fields
    update_data = account_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(account, field, value)
    
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_200_OK)
def delete_account(
    account_id: str,
    delete_transactions: bool = False,
    db: Session = Depends(get_db)
):
    """Delete an account"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if delete_transactions:
        # Delete associated transactions
        from app.models import Transaction
        db.query(Transaction).filter(Transaction.account_id == account_id).delete()
    
    db.delete(account)
    db.commit()
    return {"message": "Account deleted successfully"}


@router.post("/sync", response_model=List[AccountResponse])
def sync_accounts(accounts: List[AccountCreate], db: Session = Depends(get_db)):
    """
    Sync accounts from iOS app.
    Creates or updates accounts based on ID.
    """
    results = []
    for account_data in accounts:
        account_id = account_data.id or str(uuid.uuid4())
        
        existing = db.query(Account).filter(Account.id == account_id).first()
        
        if existing:
            # Update existing
            for field, value in account_data.model_dump(exclude={'id'}).items():
                if value is not None:
                    setattr(existing, field, value)
            db.commit()
            db.refresh(existing)
            results.append(existing)
        else:
            # Create new
            account = Account(
                id=account_id,
                **account_data.model_dump(exclude={'id'})
            )
            db.add(account)
            db.commit()
            db.refresh(account)
            results.append(account)
    
    return results
