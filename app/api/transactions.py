"""
Transaction API Endpoints
Compatible with existing iOS app
"""
from datetime import datetime, timedelta
from typing import List, Optional
from io import StringIO
import csv

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models import Transaction
from app.models.user_account import UserAccount
from app.schemas import TransactionCreate, TransactionUpdate, TransactionResponse

router = APIRouter(prefix="/transactions", tags=["transactions"])


def update_account_balance(db: Session, account_name: str):
    """
    Recalculate and update the balance for a user account based on all linked transactions.
    Balance = initial_balance + sum(Income) - sum(Expense)
    """
    if not account_name:
        return
    
    # Find the user account by name (case-insensitive)
    user_account = db.query(UserAccount).filter(
        func.lower(UserAccount.name) == account_name.lower()
    ).first()
    
    if not user_account:
        return
    
    # Calculate income (Money Received transactions)
    income = db.query(func.sum(Transaction.parsed_amount)).filter(
        func.lower(Transaction.account_name) == account_name.lower(),
        Transaction.transaction_type == "Income"
    ).scalar() or 0.0
    
    # Calculate expenses (Expense transactions)
    expenses = db.query(func.sum(Transaction.parsed_amount)).filter(
        func.lower(Transaction.account_name) == account_name.lower(),
        Transaction.transaction_type == "Expense"
    ).scalar() or 0.0
    
    # Update balance
    user_account.current_balance = user_account.initial_balance + income - expenses
    db.flush()


@router.get("/", response_model=List[TransactionResponse])
def list_transactions(
    days: int = Query(60, description="Number of days to fetch"),
    skip: int = 0,
    limit: int = 1000,
    status_filter: Optional[str] = None,
    category: Optional[str] = None,
    transaction_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get transactions for the last N days.
    Compatible with iOS fetchTransactions(days:) method.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(Transaction).filter(Transaction.parsed_date >= cutoff_date)
    
    if status_filter:
        query = query.filter(Transaction.status == status_filter)
    if category:
        query = query.filter(Transaction.category_name == category)
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)
    
    transactions = query.order_by(Transaction.parsed_date.desc()).offset(skip).limit(limit).all()
    return transactions


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
    """Get a specific transaction by ID"""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(txn_data: TransactionCreate, db: Session = Depends(get_db)):
    """Create a new transaction"""
    # Check for duplicate using idempotency key or source_email_id
    if txn_data.idempotency_key:
        existing = db.query(Transaction).filter(
            Transaction.idempotency_key == txn_data.idempotency_key
        ).first()
        if existing:
            return existing  # Return existing instead of error (idempotent)
    
    if txn_data.source_email_id:
        existing = db.query(Transaction).filter(
            Transaction.source_email_id == txn_data.source_email_id
        ).first()
        if existing:
            return existing
    
    transaction = Transaction(**txn_data.model_dump())
    db.add(transaction)
    db.flush()
    
    # Update account balance if account is linked
    if transaction.account_name:
        update_account_balance(db, transaction.account_name)
    
    db.commit()
    db.refresh(transaction)
    return transaction


@router.put("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    txn_data: TransactionUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing transaction.
    Compatible with iOS updateTransaction(id:update:) method.
    """
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Track old account for balance update
    old_account_name = transaction.account_name
    
    # Update only provided fields
    update_data = txn_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(transaction, field, value)
    
    transaction.updated_at = datetime.utcnow()
    db.flush()
    
    # Update account balances if account changed or amount/type changed
    new_account_name = transaction.account_name
    
    # Update old account balance (if it had one)
    if old_account_name:
        update_account_balance(db, old_account_name)
    
    # Update new account balance (if different from old)
    if new_account_name and new_account_name != old_account_name:
        update_account_balance(db, new_account_name)
    elif new_account_name and new_account_name == old_account_name:
        # Same account, but amount/type might have changed - already updated above
        pass
    
    db.commit()
    db.refresh(transaction)
    return transaction


@router.delete("/{transaction_id}", status_code=status.HTTP_200_OK)
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    """
    Delete a transaction.
    Compatible with iOS deleteTransaction(id:) method.
    """
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Store account name before deletion
    account_name = transaction.account_name
    
    db.delete(transaction)
    db.flush()
    
    # Update account balance after deletion
    if account_name:
        update_account_balance(db, account_name)
    
    db.commit()
    return {"message": "Transaction deleted successfully"}


@router.get("/export/csv")
def export_transactions_csv(
    days: int = Query(365, description="Number of days to export"),
    db: Session = Depends(get_db)
):
    """
    Export transactions as CSV in the required format:
    Ledger,Category,Subcategory,Currency,Price,Account,Recorder,Date,Time,Note,Transaction
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    transactions = db.query(Transaction).filter(
        Transaction.parsed_date >= cutoff_date
    ).order_by(Transaction.parsed_date.desc()).all()
    
    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Ledger", "Category", "Subcategory", "Currency", "Price",
        "Account", "Recorder", "Date", "Time", "Note", "Transaction"
    ])
    
    # Write data rows
    for txn in transactions:
        writer.writerow([
            txn.ledger or "",
            txn.category_name or "",
            txn.subcategory or "",
            txn.currency or "INR",
            txn.parsed_amount or 0.0,
            txn.account_name or "",
            txn.recorder or "Auto",
            txn.parsed_date.strftime("%Y-%m-%d") if txn.parsed_date else "",
            txn.parsed_time or "",
            txn.parsed_vendor or "",
            txn.transaction_type or "Expense"
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=transactions.csv"}
    )


@router.post("/bulk", response_model=List[TransactionResponse])
def create_transactions_bulk(
    transactions: List[TransactionCreate],
    db: Session = Depends(get_db)
):
    """Create multiple transactions at once"""
    results = []
    affected_accounts = set()
    
    for txn_data in transactions:
        # Skip duplicates
        if txn_data.idempotency_key:
            existing = db.query(Transaction).filter(
                Transaction.idempotency_key == txn_data.idempotency_key
            ).first()
            if existing:
                results.append(existing)
                continue
        
        transaction = Transaction(**txn_data.model_dump())
        db.add(transaction)
        results.append(transaction)
        
        # Track affected accounts
        if transaction.account_name:
            affected_accounts.add(transaction.account_name)
    
    db.flush()
    
    # Update all affected account balances
    for account_name in affected_accounts:
        update_account_balance(db, account_name)
    
    db.commit()
    for txn in results:
        db.refresh(txn)
    
    return results
