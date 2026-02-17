# SpendWise - AI Context File

> **Purpose**: This file provides context for AI assistants to understand the application architecture, codebase structure, and implementation details. Read this file first when working on this project.

---

## 1. PROJECT OVERVIEW

**Name**: SpendWise (formerly Expense Tracker / Transaction Parser)  
**Type**: Full-stack application (Python Backend + iOS App)  
**Purpose**: Automatically parse credit card transaction emails and sync expenses to iOS app

### Core Workflow
```
Email (ICICI, HDFC, SBI) → Backend Parser → Transaction DB → iOS App Sync
```

### Key Features
- Email parsing using regex patterns (configurable per bank)
- Email monitoring with dual authentication support:
  - IMAP with app password (Yahoo, Outlook, custom servers)
  - Gmail OAuth 2.0 (required for Google Workspace since May 2025)
- REST API for iOS app integration
- CSV export in specific 11-column format
- Category and vendor mapping management
- Local notifications for iOS (APNs requires paid developer account)

---

## 2. REPOSITORY STRUCTURE

### Backend (Python/FastAPI)
```
/Users/devendra14.kumar/PycharmProjects/Tools/email-parser-sync/
├── app/
│   ├── main.py                 # FastAPI entry point (port 8001)
│   ├── core/
│   │   ├── config.py           # Pydantic settings (env vars)
│   │   └── database.py         # SQLAlchemy setup (SQLite)
│   ├── models/
│   │   ├── account.py          # Parser profile config
│   │   ├── transaction.py      # Transaction with CSV export
│   │   ├── category.py         # Category + Subcategory + VendorMapping
│   │   └── processed_email.py  # Email tracking + Device registration
│   ├── schemas/
│   │   ├── account.py          # AccountCreate, AccountUpdate, AccountResponse
│   │   ├── transaction.py      # TransactionCreate, TransactionUpdate, TransactionResponse
│   │   ├── category.py         # Category DTOs + VendorMappingBulk
│   │   └── device.py           # DeviceRegister, DeviceResponse
│   ├── api/
│   │   ├── accounts.py         # /accounts/ CRUD + /accounts/sync
│   │   ├── transactions.py     # /transactions/ CRUD + /transactions/export/csv
│   │   ├── categories.py       # /categories/ + /categories/mappings/sync
│   │   ├── devices.py          # /devices/ registration
│   │   └── email.py            # /email/ parsing, monitoring, testing
│   ├── services/
│   │   ├── seed_data.py        # Default categories & vendor mappings
│   │   ├── email_parser.py     # Regex-based email parsing engine
│   │   ├── email_monitor.py    # Email monitoring (IMAP + Gmail OAuth)
│   │   └── gmail_oauth.py      # Gmail OAuth 2.0 authentication
│   └── tests/
│       ├── test_email_parser.py # Parser unit tests (9 tests)
│       └── test_api.py          # API integration tests (20 tests)
├── requirements.txt
├── .env.example
├── requirement.md              # Full requirements document
├── CONTEXT.md                  # THIS FILE
├── ARCHITECTURE.md             # System architecture diagrams
├── ROADMAP.md                  # Feature roadmap (PLANNED features)
│
│   # ─── PLANNED FILES (Phase 6-8) ───
│   ├── app/models/import_history.py    # 🔄 Import tracking model
│   ├── app/models/user_account.py      # 🔄 User financial accounts
│   ├── app/schemas/import.py           # 🔄 Import DTOs
│   ├── app/schemas/user_account.py     # 🔄 User account DTOs
│   ├── app/api/tools.py                # 🔄 /tools/ import endpoints
│   ├── app/api/user_accounts.py        # 🔄 /user-accounts/ CRUD
│   └── app/services/excel_parser.py    # 🔄 Paytm Excel parser
```

### iOS App (Swift/SwiftUI/SwiftData)
```
/Users/devendra14.kumar/ios-projects/transaction-app/
└── Transaction Parser/
    └── Transaction Parser/
        ├── Transaction_ParserApp.swift
        ├── ContentView.swift           # TabView with 7 tabs
        ├── DashboardView.swift         # Analytics dashboard with charts
        ├── Models/
        │   └── Transaction.swift       # SwiftData model (11 fields)
        ├── Network/
        │   └── APIClient.swift         # All API calls to backend
        ├── Services/
        │   └── NotificationService.swift # Local notifications & polling
        ├── TransactionListView.swift   # Transaction list + sync
        ├── EditTransactionView.swift   # Edit transaction form
        ├── ParserListView.swift        # Parser profiles + backend sync
        ├── EditParserView.swift        # Edit regex patterns
        ├── CategoryListView.swift      # Category management
        ├── EditCategoryView.swift
        ├── CSVExportView.swift         # CSV export (local/server)
        ├── ImportView.swift            # Statement upload
        ├── SettingsView.swift          # App settings & notifications
        ├── CategoryManager.swift       # Vendor→Category mappings
        ├── ParserManager.swift         # Local parser profiles
        └── TransactionParser.swift     # Regex parsing logic
```

---

## 3. DATA MODELS

### Transaction (Core Entity)
CSV Export Format (11 columns):
```
Ledger,Category,Subcategory,Currency,Price,Account,Recorder,Date,Time,Note,Transaction
```

**Backend Model** (`app/models/transaction.py`):
| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Auto-increment PK |
| source_email_id | String | Email message ID (dedup) |
| idempotency_key | String | Client-side dedup key |
| ledger | String | "Personal", "Business", etc. |
| category_name | String | "Food & Dining", etc. |
| subcategory | String | "Restaurants", etc. |
| currency | String | "INR" (default) |
| parsed_amount | Float | Transaction amount (positive) |
| account_name | String | "ICICI Bank Credit Card XX0001" |
| account_id | FK→Account | Links to parser profile |
| recorder | String | "Auto" or "Manual" |
| parsed_date | DateTime | Transaction date |
| parsed_time | String | "HH:mm:ss" format |
| parsed_vendor | String | Merchant name (Note in CSV) |
| notes | Text | Additional notes |
| transaction_type | String | "Expense" or "Income" |
| status | String | "pending", "confirmed", "ignored" |
| confidence_score | Float | Parser confidence (0-1) |

**iOS Model** (`Transaction.swift`):
- Uses SwiftData `@Model`
- Has `backendId: Int?` for server sync
- Methods: `toCreateDTO()`, `toUpdateDTO()`, `updateFrom(response)`, `fromResponse()`, `toCSVRow()`

### Account (Parser Profile)
**Backend Model** (`app/models/account.py`):
| Field | Type | Description |
|-------|------|-------------|
| id | String(UUID) | Primary key |
| name | String | "ICICI Bank Credit Card" |
| card_last_four | String | "0001" |
| sender_email | String | "credit_cards@icicibank.com" |
| subject_pattern | String | "Transaction alert" |
| amount_regex | Text | `INR\s*([\d,]+\.\d{2})` |
| date_regex | Text | `(\w{3}\s+\d{1,2},\s+\d{4})` |
| merchant_regex | Text | `Info:\s*(.+?)\.` |
| account_regex | Text | `XX(\d{4})` |
| time_regex | Text | `(\d{2}:\d{2}:\d{2})` |
| sample_email_body | Text | Test email for validation |
| is_active | Boolean | Enable/disable parsing |
| currency_default | String | "INR" |
| default_transaction_type | String | "Expense" |

### Category System
- **Category**: name, icon (emoji), color (hex), is_system
- **Subcategory**: name, icon, FK→Category
- **VendorMapping**: vendor_keyword, FK→Category, FK→Subcategory, is_user_defined

---

## 4. API REFERENCE

**Base URL**: `http://127.0.0.1:8001`

### Transactions
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/transactions/?days=60` | List transactions (iOS sync) |
| GET | `/transactions/{id}` | Get single transaction |
| POST | `/transactions/` | Create transaction |
| PUT | `/transactions/{id}` | Update transaction |
| DELETE | `/transactions/{id}` | Delete transaction |
| GET | `/transactions/export/csv?days=365` | Export CSV |
| POST | `/transactions/bulk` | Bulk create |

### Accounts (Parser Profiles)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/accounts/` | List all accounts |
| GET | `/accounts/{id}` | Get single account |
| POST | `/accounts/` | Create account |
| PUT | `/accounts/{id}` | Update account |
| DELETE | `/accounts/{id}` | Delete account |
| POST | `/accounts/sync` | Sync from iOS (upsert) |

### Categories
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/categories/` | List with subcategories |
| POST | `/categories/` | Create category |
| GET | `/categories/mappings/` | List vendor mappings |
| POST | `/categories/mappings/sync` | Sync vendor mappings |
| GET | `/categories/mappings/export` | Export for iOS |

### Devices
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/devices/` | Register device token |
| POST | `/devices/register` | Register device token (alias) |
| DELETE | `/devices/{token}` | Unregister device |

### Email Parsing & Monitoring
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/email/parse` | Parse email (optional create transaction) |
| POST | `/email/test-parser` | Test parser config against email |
| POST | `/email/poll` | Trigger manual email poll (background) |
| GET | `/email/monitor/status` | Get monitor status (IMAP + OAuth) |
| POST | `/email/monitor/start` | Start continuous polling |
| POST | `/email/monitor/stop` | Stop polling |
| GET | `/email/processed` | List processed emails |
| POST | `/email/reload-parsers` | Reload parser configs |
| GET | `/email/gmail-oauth/status` | Get Gmail OAuth setup status |
| POST | `/email/gmail-oauth/test` | Test Gmail OAuth connection |

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | App info |
| GET | `/health` | Health check |

---

## 5. iOS APP ARCHITECTURE

### Tabs (ContentView.swift)
1. **Dashboard** - Analytics charts & spending insights
2. **Transactions** - List, sync, add, edit transactions
3. **Parsers** - Manage regex parser profiles
4. **Categories** - Manage categories & vendor mappings
5. **Export** - CSV export (local or server)
6. **Import** - Upload bank statements
7. **Settings** - Server connection, notifications, sync options

### UI Pattern: Floating Action Button (FAB)
The following views use a bottom-right floating action button for adding new items:
- **TransactionListView** - Blue circular FAB with "+" icon
- **ParserListView** - Blue circular FAB with "+" icon  
- **CategoryListView** - Blue circular FAB with "+" icon

FAB Design:
- Size: 56x56 points
- Color: Blue background, white icon
- Shadow: 0.3 opacity black, radius 4
- Position: 20pt from right edge, 20pt from bottom

### App Branding
**App Name**: SpendWise  
**Tagline**: Smart Expense Tracker  
**Bundle ID**: com.dev.SpendWise

### App Icon
Custom app icon with 3 variants for iOS:
- **Light Mode**: Gradient background (emerald to blue), white credit card with gold chip, ₹ symbol, upward arrow
- **Dark Mode**: Dark slate gradient, dark card with border, same elements
- **Tinted**: Monochrome white outline version for iOS tinted icon support

Icon elements represent:
- Credit card → Financial tracking
- ₹ (Rupee) symbol → Indian currency focus
- Upward arrow → Growth/tracking theme

### Key Components

**APIClient.swift** - Singleton with async/await methods:
- `fetchTransactions(days:)` → `[TransactionResponse]`
- `createTransaction(_:)` → `TransactionResponse`
- `updateTransaction(id:update:)` → `TransactionResponse`
- `deleteTransaction(id:)`
- `fetchAccounts()` → `[AccountResponse]`
- `createAccount(_:)` / `updateAccount(id:update:)` / `deleteAccount(id:)`
- `syncAccounts(_:)` → `[AccountResponse]`
- `fetchCategories()` → `[CategoryResponse]`
- `fetchVendorMappings()` → `[String: VendorMappingInfo]`
- `syncVendorMappings(_:)` → `SyncResult`
- `exportTransactionsCSV(days:)` → `URL`
- `healthCheck()` → `Bool`

**Transaction.swift** - SwiftData model with:
- All 11 CSV fields + metadata
- `toCreateDTO()` / `toUpdateDTO()` for API calls
- `updateFrom(_:)` / `fromResponse(_:)` for sync
- `toCSVRow()` / `csvHeader` for export

**CategoryManager.swift** - Observable class:
- `mappings: [String: ActionCategory]`
- `getCategory(for:)` - Lookup vendor→category
- `exportMappings()` / `importMappings(_:)` - Server sync

---

## 6. EMAIL PARSING

### Supported Banks
1. **ICICI Bank** - `credit_cards@icicibank.com`
2. **HDFC Bank** - Transaction alerts
3. **SBI** - Credit card alerts

### Sample ICICI Email
```
Subject: Transaction alert for your ICICI Bank Credit Card

Dear Customer,

Your ICICI Bank Credit Card XX0001 has been used for a transaction of INR 240.00 
on Feb 16, 2026 at 10:31:46. Info: TWINS TOWER CASH.

The Available Credit Limit on your card is INR 94,678.14...
```

### Regex Patterns (ICICI)
```
amount_regex: INR\s*([\d,]+\.\d{2})
date_regex: (\w{3}\s+\d{1,2},\s+\d{4})
time_regex: (\d{2}:\d{2}:\d{2})
merchant_regex: Info:\s*(.+?)\.
account_regex: XX(\d{4})
```

### Parsed Output
```json
{
  "parsed_amount": 240.00,
  "parsed_date": "2026-02-16T10:31:46",
  "parsed_time": "10:31:46",
  "parsed_vendor": "TWINS TOWER CASH",
  "account_name": "ICICI Bank Credit Card XX0001",
  "transaction_type": "Expense",
  "currency": "INR"
}
```

---

## 7. DEFAULT DATA

### Categories (12)
Food & Dining, Transportation, Shopping, Entertainment, Bills & Utilities, 
Health & Fitness, Travel, Education, Personal Care, Income, Transfer, Others

### Vendor Mappings (Examples)
| Vendor | Category | Subcategory |
|--------|----------|-------------|
| ZOMATO | Food & Dining | Food Delivery |
| SWIGGY | Food & Dining | Food Delivery |
| AMAZON | Shopping | Online Shopping |
| UBER | Transportation | Taxi/Cab |
| IRCTC | Transportation | Train |
| NETFLIX | Entertainment | Streaming |
| GOOGLE CLOUD | Bills & Utilities | Internet |

---

## 8. RUNNING THE APP

### Backend
```bash
cd /Users/devendra14.kumar/PycharmProjects/Tools/email-parser-sync
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Environment Variables (.env)
```bash
DATABASE_URL=sqlite:///./expense_tracker.db

# Email Client Type: "imap" or "gmail_oauth"
EMAIL_CLIENT_TYPE=imap

# For IMAP (Yahoo, Outlook, custom servers):
IMAP_SERVER=imap.mail.yahoo.com
IMAP_PORT=993
IMAP_USERNAME=your-email@yahoo.com
IMAP_PASSWORD=your-app-password

# For Gmail OAuth (required for Google Workspace since May 2025):
# 1. pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client
# 2. Set up Google Cloud project with Gmail API
# 3. Download OAuth credentials to: credentials/google_oauth_credentials.json
# 4. Run: python -m app.services.gmail_oauth
# 5. Set EMAIL_CLIENT_TYPE=gmail_oauth
```

### iOS App
- Open in Xcode: `/Users/devendra14.kumar/ios-projects/transaction-app/`
- API endpoint: `http://127.0.0.1:8001` (change for device testing)

---

## 9. IMPLEMENTATION STATUS

### Phase 1: Backend API Server ✅
- [x] FastAPI project structure & config
- [x] Database models (Account, Transaction, Category, ProcessedEmail)
- [x] Account CRUD APIs (/accounts/)
- [x] Transaction APIs (/transactions/)
- [x] Category & VendorMapping APIs (/categories/)
- [x] Device registration API (/devices/)

### Phase 2: iOS App API Integration ✅
- [x] APIClient updated with all endpoints
- [x] Transaction model expanded (11 fields)
- [x] Account/ParserProfile sync
- [x] CSV export functionality

### Phase 3: Email Parser Service ✅
- [x] Regex-based email parser engine (app/services/email_parser.py)
- [x] Parser template storage & management via Account model
- [x] Unit tests (9 tests passing) - ICICI, HDFC, SBI formats

### Phase 4: Email Monitoring ✅
- [x] IMAP connection service (app/services/email_monitor.py)
- [x] Gmail OAuth 2.0 support (app/services/gmail_oauth.py)
- [x] Email polling & matching by sender/subject
- [x] Duplicate prevention (processed_emails table)
- [x] API endpoints for control (/email/*)
- [x] Google Workspace compatible (OAuth required since May 2025)

### Phase 5: Testing ✅
- [x] Parser unit tests: 9/9 passing
- [x] API integration tests: 20/20 passing

### Local Notifications (Implemented)
- [x] NotificationService for background polling
- [x] Testing mode: 30 seconds, Production mode: 15 minutes
- [x] Local notifications for new transactions
- [x] Notification actions: Confirm, Ignore, View
- [x] Settings UI for notification control
- [x] Auto-sync transactions to SwiftData on poll (saves fetched transactions locally)

### Dashboard & Analytics ✅
- [x] DashboardView with Swift Charts integration
- [x] Summary cards: Total Spent, Transaction Count, Average, Largest
- [x] Category spending pie chart (SectorMark)
- [x] Spending trend line/area chart over time
- [x] Top 5 merchants ranking table
- [x] Recent transactions quick view
- [x] Time period filter: Week, Month, Quarter, Year
- [x] Pull-to-refresh with backend sync

### Phase 6: Tools & Import (PLANNED)
- [ ] Paytm Excel Import tool
  - Upload .xlsx file from Paytm export
  - Parse and preview transactions
  - User confirms import or downloads CSV
  - Import history tracking (prevent duplicates by filename/hash)
- [ ] Backend API: /tools/import/paytm
- [ ] ImportHistory model (filename, file_hash, transaction_count)
- [ ] iOS Tools tab UI with file picker

### Phase 7: User Financial Accounts (PLANNED)
- [ ] UserAccount model (bank, credit card, wallet, cash)
- [ ] Accounts tab in iOS app
- [ ] Link transactions to accounts
- [ ] Account balance tracking
- [ ] Transfer between accounts

### Phase 8: Transaction Sources (PLANNED)
- [ ] Track transaction source (Email, Manual, Import, SMS, API)
- [ ] iOS Shortcuts integration for SMS parsing
- [ ] Shortcut API endpoint with auth token

### Future Enhancements (Optional)
- Push notifications via APNs (requires paid developer account)
- Multi-device sync
- Budget tracking & reports
- Multiple currency support
- ML-based categorization

---

## 10. DASHBOARD ANALYTICS

### DashboardView.swift Components

**Summary Cards** (4 metrics):
| Card | Icon | Color | Calculation |
|------|------|-------|-------------|
| Total Spent | `indianrupeesign.circle.fill` | Red | Sum of all expense amounts in period |
| Transactions | `list.bullet.rectangle` | Blue | Count of transactions |
| Average | `chart.bar.fill` | Orange | Total / Count |
| Largest | `arrow.up.circle.fill` | Purple | Max single transaction |

**Category Pie Chart**:
- Uses Swift Charts `SectorMark` with inner radius donut style
- Shows top 6 categories by spending
- Legend below chart with color, name, amount
- Dynamic color assignment based on category name hash

**Spending Trend Chart**:
- `AreaMark` + `LineMark` combination
- Daily aggregation of expenses
- Fills missing days with zero for continuous line
- X-axis: Date (abbreviated month + day)
- Y-axis: Amount in compact format (K for thousands)

**Top Merchants Table**:
- Ranked list of top 5 merchants by total spend
- Shows transaction count per merchant
- Sorted by total amount descending

**Time Period Filter**:
| Period | Days | Use Case |
|--------|------|----------|
| Week | 7 | Recent activity |
| Month | 30 | Monthly budget review |
| Quarter | 90 | Quarterly analysis |
| Year | 365 | Annual overview |

**Data Models** (view-local):
```swift
struct CategorySpending { let category: String; let amount: Decimal }
struct DailySpending { let date: Date; let amount: Decimal }
struct MerchantSpending { let merchant: String; let amount: Decimal; let count: Int }
```

**Algorithms**:
1. **Category Aggregation**: O(n) dictionary aggregation, O(k log k) sort
2. **Daily Trend**: O(n) date grouping, O(d) gap filling, O(d log d) sort
3. **Merchant Ranking**: O(n) aggregation, O(m log m) sort, O(5) prefix

---

## 11. IMPORTANT NOTES

1. **API Trailing Slash**: FastAPI differentiates `/transactions` vs `/transactions/`. iOS client uses trailing slash.

2. **Date Handling**: Backend uses UTC, iOS handles timezone conversion. Date format: ISO8601.

3. **Transaction Deduplication**: Uses `source_email_id` (from email) or `idempotency_key` (from client).

4. **Sync Strategy**: iOS fetches last 60 days by default. Updates existing by `backendId`, creates new otherwise.

5. **CSV Export Format**: Must match exactly - `Ledger,Category,Subcategory,Currency,Price,Account,Recorder,Date,Time,Note,Transaction`

6. **SwiftData Migration**: If model fields change, handle migration or reset data.

---

## 12. PLANNED FEATURES SUMMARY

See **ROADMAP.md** for detailed feature specifications.

### Tools Tab - Paytm Import
```
User uploads Paytm Excel → Backend parses → Preview shown → User confirms → Transactions created
```

**Key Points:**
- File types: .xlsx, .xls
- Duplicate prevention via file hash (SHA256)
- Preview before import
- Option to download as CSV without importing
- Import history tracking

### Accounts Tab - User Financial Accounts
```
Accounts: Bank Account | Credit Card | Wallet | Cash | Investment
```

**Key Points:**
- Separate from Parser Profiles (existing "Parsers" tab)
- Each transaction links to an account
- Balance tracking (initial + calculated)
- Transfer between accounts

### iOS Tab Structure (Planned)
| # | Tab | Status |
|---|-----|--------|
| 1 | Dashboard | ✅ Implemented |
| 2 | Transactions | ✅ Implemented |
| 3 | **Accounts** | 🔄 Planned (NEW) |
| 4 | Parsers | ✅ Implemented |
| 5 | Categories | ✅ Implemented |
| 6 | **Tools** | 🔄 Planned (Import + Export merged) |
| 7 | Settings | ✅ Implemented |

*Note: Export tab merged into Tools tab to consolidate import/export features*

---

*Last Updated: February 17, 2026*
*For full requirements, see: requirement.md*
*For roadmap, see: ROADMAP.md*
