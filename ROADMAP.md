# SpendWise - Feature Roadmap

> **Purpose**: Track planned features, their requirements, and implementation status.

---

## Phase 6: Tools & Import Features (PLANNED)

### 6.1 Paytm Excel Import Tool

**Status**: 🔄 Planned

**Description**: Import transactions from Paytm export Excel files (.xlsx) into SpendWise.

#### Requirements

1. **File Upload**
   - Accept Excel files (.xlsx, .xls) from Paytm export
   - Backend API endpoint: `POST /tools/import/paytm`
   - iOS UI: File picker in Tools tab

2. **Parsing & Preview**
   - Parse Paytm Excel format (columns: Date, Description, Amount, Status, etc.)
   - Map to SpendWise transaction format
   - Show preview table with parsed transactions
   - Highlight any parsing issues or missing data

3. **User Confirmation**
   - Display import summary:
     - Total transactions found
     - Valid transactions ready to import
     - Skipped/invalid transactions
   - User options:
     - ✅ Import All
     - 📥 Download as CSV (parsed format)
     - ❌ Cancel

4. **Duplicate Prevention**
   - Track imported files in `import_history` table
   - Store: filename, file_hash (SHA256), import_date, transaction_count
   - Warn user if same file was previously imported
   - Allow re-import with confirmation

5. **Transaction Mapping**

| Paytm Column | SpendWise Field |
|--------------|-----------------|
| Date | parsed_date |
| Description | parsed_vendor |
| Amount | parsed_amount |
| Status | status (filter: only "SUCCESS") |
| Category (if exists) | category_name |
| - | recorder = "Import" |
| - | account_name = "Paytm Wallet" |

#### API Endpoints

```
POST /tools/import/paytm
  - Upload Excel file
  - Returns: preview of parsed transactions

POST /tools/import/paytm/confirm
  - Confirm import after preview
  - Creates transactions in database

GET /tools/import/paytm/download-csv
  - Download parsed data as CSV (without importing)

GET /tools/import/history
  - List previous imports

DELETE /tools/import/history/{id}
  - Delete import history entry (allows re-import)
```

#### Data Model: ImportHistory

```python
class ImportHistory(Base):
    id: str (UUID)
    filename: str
    file_hash: str (SHA256)
    file_type: str ("paytm_excel", "bank_statement", etc.)
    transaction_count: int
    imported_at: datetime
    status: str ("completed", "partial", "failed")
    notes: str (optional)
```

---

### 6.2 Bank Statement Import (Future)

**Status**: 📋 Backlog

Support importing from other bank statement formats:
- HDFC Bank PDF/CSV
- ICICI Bank PDF/CSV
- SBI Statement
- Generic CSV format

---

## Phase 7: User Financial Accounts (PLANNED)

### 7.1 Accounts Tab (User Financial Accounts)

**Status**: 🔄 Planned

**Description**: Manage user's financial accounts (bank accounts, credit cards, wallets) separate from parser profiles.

#### Requirements

1. **Account Types**
   - Bank Account (Savings, Current)
   - Credit Card
   - Wallet (Paytm, PhonePe, GPay)
   - Cash
   - Investment Account

2. **Account Fields**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Unique identifier |
| name | string | Yes | Display name (e.g., "HDFC Savings") |
| type | enum | Yes | bank_account, credit_card, wallet, cash, investment |
| institution | string | No | Bank/Provider name |
| account_number_last4 | string | No | Last 4 digits for identification |
| currency | string | Yes | Default: INR |
| initial_balance | decimal | No | Starting balance |
| current_balance | decimal | No | Calculated from transactions |
| is_active | bool | Yes | Show in transaction dropdowns |
| color | string | No | UI color for charts |
| icon | string | No | SF Symbol name |
| linked_parser_id | UUID | No | Link to parser profile for auto-import |
| created_at | datetime | Yes | |
| updated_at | datetime | Yes | |

3. **UI Components**
   - Account list view (grouped by type)
   - Add/Edit account form
   - Account detail view with transaction history
   - Balance summary card

4. **Transaction Integration**
   - Each transaction links to an account (account_id)
   - Filter transactions by account
   - Transfer between accounts (creates 2 linked transactions)

#### API Endpoints

```
GET /user-accounts/
POST /user-accounts/
GET /user-accounts/{id}
PUT /user-accounts/{id}
DELETE /user-accounts/{id}
GET /user-accounts/{id}/transactions
POST /user-accounts/transfer  (account-to-account transfer)
```

#### Data Model: UserAccount

```python
class UserAccount(Base):
    id: str (UUID)
    name: str
    type: str  # bank_account, credit_card, wallet, cash, investment
    institution: str (optional)
    account_number_last4: str (optional)
    currency: str = "INR"
    initial_balance: float = 0
    is_active: bool = True
    color: str (optional)  # hex color
    icon: str (optional)   # SF Symbol
    linked_parser_id: str (optional)  # FK to Account (parser)
    created_at: datetime
    updated_at: datetime
```

---

## Phase 8: Transaction Sources (PLANNED)

### 8.1 Transaction Source Types

**Status**: 📋 Backlog

Track how each transaction was created:

| Source | Description | recorder value |
|--------|-------------|----------------|
| Email | Parsed from bank email | "Auto" |
| Manual | User entered manually | "Manual" |
| Import | Imported from file (Paytm, etc.) | "Import" |
| SMS | Parsed from SMS (via iOS Shortcut) | "SMS" |
| API | Created via external API | "API" |

### 8.2 iOS Shortcuts Integration (Future)

**Status**: 📋 Backlog

Allow iOS Shortcuts to send transaction data to SpendWise:
1. User creates iOS Shortcut that triggers on SMS from bank
2. Shortcut extracts transaction info
3. Shortcut calls SpendWise API to create transaction
4. SpendWise validates and saves

#### API Endpoint for Shortcuts

```
POST /shortcuts/transaction
Headers:
  X-Shortcut-Token: <user-generated-token>
Body:
  {
    "raw_text": "..SMS content...",
    "source": "sms",
    "sender": "ICICIBK"
  }
```

---

## iOS App Tab Structure (Updated)

### Current (7 tabs):
1. Dashboard
2. Transactions
3. Parsers
4. Categories
5. Export
6. Import
7. Settings

### Proposed (7 tabs):
1. **Dashboard** - Analytics & charts
2. **Transactions** - Transaction list
3. **Accounts** - User financial accounts (NEW)
4. **Parsers** - Email parser profiles
5. **Categories** - Category management
6. **Tools** - Import & Export combined (CONSOLIDATED)
7. **Settings** - App settings

### Tools Tab Contents:
- **Import Section**
  - Paytm Excel Import
  - Bank Statement Import (future)
  - Import History
- **Export Section**
  - CSV Export (existing functionality moved here)
  - Export to local/server

---

## Implementation Priority

| Priority | Feature | Effort | Dependencies |
|----------|---------|--------|--------------|
| 1 | Paytm Excel Import (Backend) | Medium | openpyxl library |
| 2 | Import History Model | Low | None |
| 3 | Tools Tab UI (iOS) | Medium | Backend API |
| 4 | User Accounts Model | Medium | None |
| 5 | Accounts Tab UI (iOS) | Medium | Backend API |
| 6 | Link Accounts to Transactions | Low | User Accounts |
| 7 | iOS Shortcuts Integration | High | Security token system |

---

## Technical Notes

### Excel Parsing (Backend)
- Use `openpyxl` library for .xlsx files
- Use `xlrd` library for .xls files (legacy)
- Validate file format before parsing
- Handle encoding issues (UTF-8)

### File Hash for Duplicate Detection
```python
import hashlib

def get_file_hash(file_content: bytes) -> str:
    return hashlib.sha256(file_content).hexdigest()
```

### Paytm Excel Format (Expected)
Typical Paytm export columns:
- Date
- Transaction ID
- Description/Narration
- Debit/Credit
- Amount
- Status
- Balance

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Feb 17, 2026 | Initial roadmap created |
