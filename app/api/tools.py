"""
Tools API Endpoints
Import/Export tools for transactions
"""
import uuid
import io
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models import ImportHistory, Transaction, UserAccount
from app.models.category import Category, Subcategory
from pydantic import BaseModel
from app.schemas.import_tool import (
    ImportHistoryResponse, ImportHistoryListResponse,
    ImportPreviewResponse, ImportConfirmRequest, ImportConfirmResponse,
    ParsedTransaction as ParsedTransactionSchema
)

router = APIRouter(prefix="/tools", tags=["tools"])

# In-memory cache for preview data (in production, use Redis)
_preview_cache = {}


@router.post("/import/paytm", response_model=ImportPreviewResponse)
async def import_paytm_excel(
    file: UploadFile = File(..., description="Paytm Excel export file (.xlsx)"),
    db: Session = Depends(get_db)
):
    """
    Upload and parse a Paytm Excel export file.
    
    Returns a preview of parsed transactions. Use /import/paytm/confirm to actually import.
    
    Supported formats:
    - .xlsx (Excel 2007+)
    - .xls (Legacy Excel)
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400, 
            detail="Invalid file type. Only .xlsx and .xls files are supported."
        )
    
    # Read file content
    content = await file.read()
    
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")
    
    # Import parser (lazy load to handle missing openpyxl gracefully)
    try:
        from app.services.excel_parser import parse_paytm_excel, get_file_hash
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail="Excel parsing not available. Install openpyxl: pip install openpyxl"
        )
    
    # Parse the file
    try:
        result = parse_paytm_excel(content, file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")
    
    # Check for duplicate import
    existing_import = db.query(ImportHistory).filter(
        ImportHistory.file_hash == result.file_hash
    ).first()
    
    duplicate_warning = existing_import is not None
    previous_import_id = existing_import.id if existing_import else None
    previous_import_date = existing_import.imported_at if existing_import else None
    
    # Store in cache for confirmation
    _preview_cache[result.preview_token] = {
        "result": result,
        "content": content,
        "filename": file.filename,
        "created_at": datetime.utcnow()
    }
    
    # Clean old cache entries (older than 1 hour)
    cutoff = datetime.utcnow()
    keys_to_remove = [
        k for k, v in _preview_cache.items() 
        if (cutoff - v["created_at"]).total_seconds() > 3600
    ]
    for k in keys_to_remove:
        del _preview_cache[k]
    
    # Import ColumnMapping schema
    from app.schemas.import_tool import ColumnMapping
    
    return ImportPreviewResponse(
        filename=file.filename,
        file_hash=result.file_hash,
        file_type=result.file_type,
        total_rows=result.total_rows,
        valid_transactions=result.valid_count,
        skipped_rows=result.skipped_count,
        duplicate_warning=duplicate_warning,
        previous_import_id=previous_import_id,
        previous_import_date=previous_import_date,
        transactions=[
            ParsedTransactionSchema(**t.to_dict()) 
            for t in result.transactions[:100]  # Limit preview to 100
        ],
        preview_token=result.preview_token,
        column_mappings=[
            ColumnMapping(
                excel_column=m.excel_column,
                internal_field=m.internal_field,
                sample_value=m.sample_value
            ) for m in result.column_mappings
        ],
        unique_accounts=result.unique_accounts
    )


@router.post("/import/paytm/confirm", response_model=ImportConfirmResponse)
def confirm_paytm_import(
    request: ImportConfirmRequest,
    db: Session = Depends(get_db)
):
    """
    Confirm and execute the import after reviewing preview.
    
    Requires the preview_token from the /import/paytm response.
    """
    # Get cached preview data
    cache_entry = _preview_cache.get(request.preview_token)
    if not cache_entry:
        raise HTTPException(
            status_code=400, 
            detail="Preview token expired or invalid. Please upload the file again."
        )
    
    result = cache_entry["result"]
    filename = cache_entry["filename"]
    
    # Check for duplicate if skip_duplicates is True
    if request.skip_duplicates:
        existing = db.query(ImportHistory).filter(
            ImportHistory.file_hash == result.file_hash
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"This file was already imported on {existing.imported_at}. "
                       f"Set skip_duplicates=false to import anyway."
            )
    
    # Get user account if specified
    user_account = None
    if request.user_account_id:
        user_account = db.query(UserAccount).filter(
            UserAccount.id == request.user_account_id
        ).first()
        if not user_account:
            raise HTTPException(status_code=404, detail="User account not found")
    
    # Create transactions
    created_count = 0
    skipped_count = 0
    categories_created = 0
    subcategories_created = 0
    accounts_created = 0
    
    # Cache for categories, subcategories, and accounts to avoid repeated queries
    category_cache = {}  # name -> Category object
    subcategory_cache = {}  # (category_id, name) -> Subcategory object
    account_cache = {}  # name -> UserAccount object
    
    for txn in result.transactions:
        if not txn.is_valid:
            skipped_count += 1
            continue
        
        try:
            # Parse date
            parsed_date = None
            if txn.date:
                parsed_date = datetime.strptime(txn.date, "%Y-%m-%d")
            
            # Category is already cleaned in the parser (emoji removed)
            category_name = txn.category.strip() if txn.category else None
            subcategory_name = txn.subcategory.strip() if txn.subcategory else None
            
            # Handle category: create if enabled, or use existing, or fallback to "Others"
            category_obj = None
            category_cache_key = category_name.lower() if category_name else None
            
            if category_name:
                if category_cache_key not in category_cache:
                    # Check if category exists in database
                    existing_category = db.query(Category).filter(
                        func.lower(Category.name) == category_cache_key
                    ).first()
                    
                    if existing_category:
                        category_cache[category_cache_key] = existing_category
                    elif request.create_categories:
                        # Create new category only if enabled
                        new_category = Category(
                            name=category_name,  # Keep original case for display
                            is_system=False
                        )
                        db.add(new_category)
                        db.flush()  # Get the ID
                        category_cache[category_cache_key] = new_category
                        categories_created += 1
                    else:
                        # Fallback to "Others" when create_categories is disabled
                        others_category = db.query(Category).filter(
                            func.lower(Category.name) == "others"
                        ).first()
                        if others_category:
                            category_cache[category_cache_key] = others_category
                            category_cache["others"] = others_category
                            category_name = "Others"  # Update for transaction
                        else:
                            # Create "Others" if it doesn't exist
                            others_category = Category(name="Others", is_system=True)
                            db.add(others_category)
                            db.flush()
                            category_cache["others"] = others_category
                            category_cache[category_cache_key] = others_category
                            category_name = "Others"
                
                category_obj = category_cache.get(category_cache_key)
                
                # Handle subcategory: create if enabled, or use existing, or fallback to "Others"
                if subcategory_name and category_obj:
                    subcategory_cache_key = (category_obj.id, subcategory_name.lower())
                    if subcategory_cache_key not in subcategory_cache:
                        # Check if subcategory exists in database
                        existing_subcategory = db.query(Subcategory).filter(
                            Subcategory.category_id == category_obj.id,
                            func.lower(Subcategory.name) == subcategory_name.lower()
                        ).first()
                        
                        if existing_subcategory:
                            subcategory_cache[subcategory_cache_key] = existing_subcategory
                        elif request.create_subcategories:
                            # Create new subcategory only if enabled
                            new_subcategory = Subcategory(
                                category_id=category_obj.id,
                                name=subcategory_name  # Keep original case for display
                            )
                            db.add(new_subcategory)
                            db.flush()  # Get the ID
                            subcategory_cache[subcategory_cache_key] = new_subcategory
                            subcategories_created += 1
                        else:
                            # Fallback to "Others" when create_subcategories is disabled
                            others_key = (category_obj.id, "others")  # lowercase for consistency
                            if others_key not in subcategory_cache:
                                others_sub = db.query(Subcategory).filter(
                                    Subcategory.category_id == category_obj.id,
                                    func.lower(Subcategory.name) == "others"
                                ).first()
                                if not others_sub:
                                    others_sub = Subcategory(category_id=category_obj.id, name="Others")
                                    db.add(others_sub)
                                    db.flush()
                                subcategory_cache[others_key] = others_sub
                            subcategory_cache[subcategory_cache_key] = subcategory_cache[others_key]
                            subcategory_name = "Others"  # Update for transaction
            
            # Build notes: description is the main note, reference is metadata
            notes_parts = []
            if txn.description:
                notes_parts.append(txn.description)
            if txn.reference_id:
                notes_parts.append(f"Ref: {txn.reference_id}")
            notes = " | ".join(notes_parts) if notes_parts else None
            
            # Determine account name: use "Your Account" from Excel, fallback to user account or "Paytm"
            account_name = txn.account.strip() if txn.account else (user_account.name if user_account else "Paytm")
            
            # Auto-create UserAccount if enabled and doesn't exist
            user_account_id = request.user_account_id
            account_cache_key = account_name.lower() if account_name else None
            
            if request.create_accounts and account_name and account_cache_key not in account_cache:
                # Check if account exists in database (case-insensitive)
                existing_account = db.query(UserAccount).filter(
                    func.lower(UserAccount.name) == account_cache_key
                ).first()
                
                if existing_account:
                    account_cache[account_cache_key] = existing_account
                else:
                    # Create new UserAccount
                    new_account = UserAccount(
                        id=str(uuid.uuid4()),
                        name=account_name,  # Keep original case for display
                        account_type="wallet",  # Default to wallet for Paytm imports
                        currency="INR",
                        is_active=True,
                        include_in_total=True,
                        primary_source="import"
                    )
                    db.add(new_account)
                    db.flush()
                    account_cache[account_cache_key] = new_account
                    accounts_created += 1
            elif not request.create_accounts and account_name and account_cache_key:
                # Check if account already exists even if create_accounts is false
                if account_cache_key not in account_cache:
                    existing_account = db.query(UserAccount).filter(
                        func.lower(UserAccount.name) == account_cache_key
                    ).first()
                    if existing_account:
                        account_cache[account_cache_key] = existing_account
            
            # Link transaction to the UserAccount if available
            if account_cache_key and account_cache_key in account_cache:
                user_account_id = account_cache[account_cache_key].id
            
            transaction = Transaction(
                parsed_amount=txn.amount,
                parsed_vendor=txn.description,  # Transaction Details -> vendor
                parsed_date=parsed_date,
                parsed_time=txn.time,
                transaction_type=txn.transaction_type,
                category_name=category_name,
                subcategory=subcategory_name,
                currency="INR",
                recorder="Import",
                account_name=account_name,  # From "Your Account" column
                user_account_id=user_account_id,  # Link to UserAccount
                status="confirmed",
                notes=notes,  # Transaction Details + Reference
                idempotency_key=f"paytm_import_{result.file_hash}_{txn.row_number}"
            )
            
            db.add(transaction)
            created_count += 1
            
        except Exception as e:
            skipped_count += 1
    
    # Create import history record
    import_history = ImportHistory(
        id=str(uuid.uuid4()),
        filename=filename,
        file_hash=result.file_hash,
        file_size=len(cache_entry["content"]),
        file_type="paytm_excel",
        transaction_count=created_count,
        skipped_count=skipped_count,
        status="completed" if skipped_count == 0 else "partial",
        imported_at=datetime.utcnow()
    )
    
    db.add(import_history)
    db.commit()
    
    # Clean up cache
    del _preview_cache[request.preview_token]
    
    # Update user account balance if specified
    if user_account:
        # Recalculate balance
        expenses = db.query(func.sum(Transaction.parsed_amount)).filter(
            Transaction.user_account_id == user_account.id,
            Transaction.transaction_type == "Expense"
        ).scalar() or 0
        
        income = db.query(func.sum(Transaction.parsed_amount)).filter(
            Transaction.user_account_id == user_account.id,
            Transaction.transaction_type == "Income"
        ).scalar() or 0
        
        user_account.current_balance = user_account.initial_balance + income - expenses
        db.commit()
    
    # Build message with category and account info
    message_parts = [f"Successfully imported {created_count} transactions from {filename}"]
    if categories_created > 0:
        message_parts.append(f"Created {categories_created} new categories")
    if subcategories_created > 0:
        message_parts.append(f"Created {subcategories_created} new subcategories")
    if accounts_created > 0:
        message_parts.append(f"Created {accounts_created} new accounts")
    
    return ImportConfirmResponse(
        success=True,
        message=". ".join(message_parts),
        import_history_id=import_history.id,
        transactions_created=created_count,
        transactions_skipped=skipped_count,
        categories_created=categories_created,
        subcategories_created=subcategories_created,
        accounts_created=accounts_created
    )


@router.get("/import/paytm/download-csv")
def download_parsed_csv(
    preview_token: str = Query(..., description="Preview token from upload"),
):
    """
    Download the parsed transactions as CSV without importing.
    """
    cache_entry = _preview_cache.get(preview_token)
    if not cache_entry:
        raise HTTPException(
            status_code=400,
            detail="Preview token expired or invalid. Please upload the file again."
        )
    
    from app.services.excel_parser import generate_csv_content
    
    result = cache_entry["result"]
    csv_content = generate_csv_content(result.transactions, include_invalid=False)
    
    # Create streaming response
    output = io.StringIO(csv_content)
    
    filename = cache_entry["filename"].rsplit(".", 1)[0] + "_parsed.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/import/history", response_model=List[ImportHistoryListResponse])
def list_import_history(
    skip: int = 0,
    limit: int = 50,
    file_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get import history"""
    query = db.query(ImportHistory)
    
    if file_type:
        query = query.filter(ImportHistory.file_type == file_type)
    
    history = query.order_by(ImportHistory.imported_at.desc()).offset(skip).limit(limit).all()
    return history


@router.get("/import/history/{history_id}", response_model=ImportHistoryResponse)
def get_import_history(history_id: str, db: Session = Depends(get_db)):
    """Get specific import history entry"""
    history = db.query(ImportHistory).filter(ImportHistory.id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Import history not found")
    return history


class RollbackResponse(BaseModel):
    """Response for rollback operation"""
    success: bool
    message: str
    transactions_deleted: int
    import_history_deleted: bool

@router.post("/import/history/{history_id}/rollback", response_model=RollbackResponse)
def rollback_import(
    history_id: str,
    db: Session = Depends(get_db)
):
    """
    Rollback an import - delete all transactions from this import and the history entry.
    
    This completely reverses an import operation.
    """
    history = db.query(ImportHistory).filter(ImportHistory.id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Import history not found")
    
    # Count transactions to be deleted
    transactions_to_delete = db.query(Transaction).filter(
        Transaction.idempotency_key.like(f"paytm_import_{history.file_hash}_%")
    ).count()
    
    # Delete transactions that have matching idempotency keys
    db.query(Transaction).filter(
        Transaction.idempotency_key.like(f"paytm_import_{history.file_hash}_%")
    ).delete(synchronize_session=False)
    
    filename = history.filename
    
    # Delete the import history
    db.delete(history)
    db.commit()
    
    return RollbackResponse(
        success=True,
        message=f"Rolled back import of {filename}. Deleted {transactions_to_delete} transactions.",
        transactions_deleted=transactions_to_delete,
        import_history_deleted=True
    )


@router.delete("/import/history/{history_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_import_history(
    history_id: str,
    delete_transactions: bool = Query(False, description="Also delete imported transactions"),
    db: Session = Depends(get_db)
):
    """
    Delete import history entry.
    
    This allows re-importing the same file (duplicate check uses file hash).
    Optionally delete the transactions that were imported.
    """
    history = db.query(ImportHistory).filter(ImportHistory.id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Import history not found")
    
    if delete_transactions:
        # Delete transactions that have matching idempotency keys
        db.query(Transaction).filter(
            Transaction.idempotency_key.like(f"paytm_import_{history.file_hash}_%")
        ).delete(synchronize_session=False)
    
    db.delete(history)
    db.commit()
    return None


# ============== EXPORT ENDPOINTS ==============

@router.get("/export/csv")
def export_transactions_csv(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    user_account_id: Optional[str] = Query(None, description="Filter by user account"),
    transaction_type: Optional[str] = Query(None, description="Expense or Income"),
    db: Session = Depends(get_db)
):
    """
    Export transactions as CSV.
    
    Format: Ledger,Category,Subcategory,Currency,Price,Account,Recorder,Date,Time,Note,Transaction
    """
    query = db.query(Transaction)
    
    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(Transaction.parsed_date >= start)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format")
    
    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d")
            query = query.filter(Transaction.parsed_date <= end)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format")
    
    if user_account_id:
        query = query.filter(Transaction.user_account_id == user_account_id)
    
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)
    
    transactions = query.order_by(Transaction.parsed_date.desc()).all()
    
    # Build CSV
    lines = ["Ledger,Category,Subcategory,Currency,Price,Account,Recorder,Date,Time,Note,Transaction"]
    
    for t in transactions:
        row = t.to_csv_row()
        # Escape note field
        note = row["Note"]
        if "," in note or '"' in note:
            note = '"' + note.replace('"', '""') + '"'
        
        line = f'{row["Ledger"]},{row["Category"]},{row["Subcategory"]},{row["Currency"]},{row["Price"]},{row["Account"]},{row["Recorder"]},{row["Date"]},{row["Time"]},{note},{row["Transaction"]}'
        lines.append(line)
    
    csv_content = "\n".join(lines)
    
    # Generate filename
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"spendwise_export_{date_str}.csv"
    
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/export/summary")
def export_summary(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get export summary statistics.
    """
    query = db.query(Transaction)
    
    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(Transaction.parsed_date >= start)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format")
    
    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d")
            query = query.filter(Transaction.parsed_date <= end)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format")
    
    total_count = query.count()
    
    total_expenses = query.filter(Transaction.transaction_type == "Expense").with_entities(
        func.sum(Transaction.parsed_amount)
    ).scalar() or 0
    
    total_income = query.filter(Transaction.transaction_type == "Income").with_entities(
        func.sum(Transaction.parsed_amount)
    ).scalar() or 0
    
    # Get category breakdown
    category_breakdown = query.filter(Transaction.transaction_type == "Expense").with_entities(
        Transaction.category_name,
        func.sum(Transaction.parsed_amount).label("total"),
        func.count(Transaction.id).label("count")
    ).group_by(Transaction.category_name).all()
    
    return {
        "total_transactions": total_count,
        "total_expenses": total_expenses,
        "total_income": total_income,
        "net": total_income - total_expenses,
        "date_range": {
            "start": start_date,
            "end": end_date
        },
        "category_breakdown": [
            {"category": c[0] or "Uncategorized", "total": c[1], "count": c[2]}
            for c in category_breakdown
        ]
    }
