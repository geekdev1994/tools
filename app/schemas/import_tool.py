"""
Import Tool Schemas - Request/Response DTOs for file imports
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ImportHistoryResponse(BaseModel):
    """Schema for import history response"""
    id: str
    filename: str
    file_hash: str
    file_size: Optional[int] = None
    file_type: str
    transaction_count: int
    skipped_count: int
    status: str
    error_message: Optional[str] = None
    notes: Optional[str] = None
    imported_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class ImportHistoryListResponse(BaseModel):
    """Schema for list of import history"""
    id: str
    filename: str
    file_type: str
    transaction_count: int
    status: str
    imported_at: datetime

    class Config:
        from_attributes = True


class ParsedTransaction(BaseModel):
    """Schema for a single parsed transaction from import"""
    row_number: int
    date: Optional[str] = None
    time: Optional[str] = None
    description: Optional[str] = None  # Transaction Details -> notes/vendor
    amount: Optional[float] = None
    transaction_type: str = "Expense"  # Expense or Income
    category: Optional[str] = None  # From Tags (first part before :)
    subcategory: Optional[str] = None  # From Tags (second part after :)
    account: Optional[str] = None  # From "Your Account" column
    status: Optional[str] = None  # Original status from file (e.g., "SUCCESS")
    reference_id: Optional[str] = None
    is_valid: bool = True
    error_message: Optional[str] = None


class ColumnMapping(BaseModel):
    """Mapping of Excel column to internal field"""
    excel_column: str  # Original column name from Excel
    internal_field: str  # Internal field name
    sample_value: Optional[str] = None  # Sample value from first row

class ImportPreviewResponse(BaseModel):
    """Response for import preview (before confirmation)"""
    filename: str
    file_hash: str
    file_type: str
    total_rows: int
    valid_transactions: int
    skipped_rows: int
    duplicate_warning: bool = False
    previous_import_id: Optional[str] = None
    previous_import_date: Optional[datetime] = None
    transactions: List[ParsedTransaction]
    preview_token: str  # Token to confirm import
    column_mappings: List[ColumnMapping] = []  # Column mapping info
    unique_accounts: List[str] = []  # Unique account names found


class ColumnMappingOverride(BaseModel):
    """Override for column mapping"""
    excel_column: str
    internal_field: str
    is_enabled: bool = True


class ImportConfirmRequest(BaseModel):
    """Request to confirm import after preview"""
    preview_token: str = Field(..., description="Token from preview response")
    user_account_id: Optional[str] = Field(None, description="User account to assign transactions to")
    skip_duplicates: bool = Field(default=True, description="Skip if file was previously imported")
    create_categories: bool = Field(default=True, description="Whether to create new categories if not found")
    create_subcategories: bool = Field(default=True, description="Whether to create new subcategories if not found")
    create_accounts: bool = Field(default=True, description="Whether to create UserAccount for unique accounts")
    column_mappings: Optional[List[ColumnMappingOverride]] = Field(None, description="Optional column mapping overrides")


class ImportConfirmResponse(BaseModel):
    """Response after confirming import"""
    success: bool
    message: str
    import_history_id: str
    transactions_created: int
    transactions_skipped: int
    categories_created: int = 0
    subcategories_created: int = 0
    accounts_created: int = 0


class ImportDownloadRequest(BaseModel):
    """Request to download parsed data as CSV"""
    preview_token: str = Field(..., description="Token from preview response")


class PaytmExcelMapping(BaseModel):
    """Column mapping for Paytm Excel format"""
    date_column: str = "Date"
    description_column: str = "Activity"
    debit_column: str = "Debit"
    credit_column: str = "Credit"
    status_column: str = "Status"
    transaction_id_column: str = "Transaction ID"


class GenericImportRequest(BaseModel):
    """Generic import configuration"""
    file_type: str = Field(..., description="Type of file: paytm_excel, hdfc_csv, etc.")
    user_account_id: Optional[str] = Field(None, description="Target user account")
    column_mapping: Optional[dict] = Field(None, description="Custom column mapping")
