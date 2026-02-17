# Expense Tracker System

**Requirements Specification Document**

**Version:** 1.5  
**Last Updated:** February 17, 2026

---

## Table of Contents

1. [Overview](#1-overview)
2. [System Architecture](#2-system-architecture)
3. [Functional Requirements](#3-functional-requirements)
4. [Account Management](#4-account-management)
5. [Email Parsing Configuration](#5-email-parsing-configuration)
6. [Data Models](#6-data-models)
7. [API Specifications](#7-api-specifications)
8. [Non-Functional Requirements](#8-non-functional-requirements)
9. [Data Flow](#9-data-flow)
10. [User Interface Requirements](#10-user-interface-requirements)
11. [Export Format](#11-export-format)
12. [Future Extensibility](#12-future-extensibility)
    - 12.1 [Phase 6: Tools & Import Features](#121-phase-6-tools--import-features-planned)
    - 12.2 [Phase 7: User Financial Accounts](#122-phase-7-user-financial-accounts-planned)
    - 12.3 [Phase 8: Transaction Sources & iOS Shortcuts](#123-phase-8-transaction-sources--ios-shortcuts-planned)
    - 12.4 [Other Future Enhancements](#124-other-future-enhancements)
13. [Assumptions & Constraints](#13-assumptions--constraints)
14. [Success Criteria](#14-success-criteria)

---

## 1. Overview

### 1.1 Purpose

Build an iOS-based personal expense tracking system that automatically captures credit card transactions from email notifications, parses them, categorizes them, and stores them locally using SQLite.

The system must support shared category logic between iPhone app and API server.

### 1.2 Scope

- Automatic email monitoring for transaction notifications
- Configurable email parsing rules per credit card account
- Push notification delivery to iOS devices
- Local SQLite storage on iOS
- Category and subcategory management
- Vendor mapping to categories
- Account management (Add/Update/Delete credit card email configurations)
- Support for both Expense and Income transactions
- Export functionality in standard CSV format

### 1.3 Target Users

- Individual users tracking personal expenses
- Users with multiple credit cards from different banks
- Users who receive transaction alerts via email

---

## 2. System Architecture

### 2.1 System Components

| Component | Location | Description |
|-----------|----------|-------------|
| Email Monitoring Service | API Server | Monitors email inbox for new transaction emails |
| Email Parsing Engine | API Server | Parses emails based on configured templates |
| Account Configuration Store | API Server + iOS | Stores credit card account configurations |
| Push Notification Service | API Server | Sends parsed transactions via APNs |
| iOS Application | Client | User interface, local storage, category mapping |
| Local SQLite Database | iOS | Stores transactions, categories, mappings |
| Category Mapping Engine | Shared | Vendor-to-category mapping logic |

### 2.2 Technology Stack

| Layer | Technology |
|-------|------------|
| API Server | Python/Node.js (TBD) |
| Email Protocol | IMAP/Gmail API |
| Push Notifications | Apple Push Notification Service (APNs) |
| iOS App | Swift/SwiftUI |
| Local Database | SQLite |
| Server Database | PostgreSQL/SQLite |

---

## 3. Functional Requirements

### 3.1 Email Monitoring

The system shall:

- Monitor designated email inbox for new credit card transaction emails
- Detect emails from configured credit card providers based on:
  - Sender email address
  - Email subject pattern
- Process emails in near real-time (polling interval configurable)
- Prevent duplicate processing of the same email (using Message-ID)
- Support multiple email accounts (future scope)

### 3.2 Email Parsing (Server-Side)

The system shall:

- Match incoming emails against configured account templates
- Extract transaction data using configured parsing rules
- Extract the following fields:
  - Card identifier (last 4 digits)
  - Transaction amount (Price)
  - Currency
  - Merchant/vendor name (Note)
  - Transaction date
  - Transaction time
  - Transaction type (Expense/Income)
  - Unique transaction reference (if available)
- Normalize extracted data into structured JSON format
- Validate extracted values before forwarding
- Log parsing failures for debugging

### 3.3 Push Notification Delivery

The system shall:

- Send structured transaction data to iOS device using APNs
- Include minimum required transaction fields in push payload
- Ensure idempotency (avoid duplicate transaction entries)
- Support silent push for background updates
- Handle APNs delivery failures gracefully

### 3.4 iOS Application

The iOS app shall:

- Register for push notifications
- Receive push notification payload
- Parse structured transaction data
- Store transaction in local SQLite database
- Apply vendor-to-category mapping
- Display categorized transaction to user
- Allow manual category and subcategory correction
- Prevent duplicate transaction storage
- Provide account management interface
- Support manual transaction entry
- Export transactions in standard CSV format

---

## 4. Account Management

### 4.1 Overview

Users must configure "Accounts" that define how the system identifies and parses transaction emails from different credit card providers. Each account represents a credit card and its associated email notification format.

### 4.2 Account Entity

An Account consists of:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Auto | Unique identifier |
| `account_name` | String | Yes | User-friendly name (e.g., "HDFC Credit Card") |
| `card_last_four` | String(4) | No | Last 4 digits of card for identification |
| `sender_email` | String | Yes | Email address of the sender (e.g., "alerts@hdfcbank.net") |
| `sender_name` | String | No | Display name of sender |
| `subject_pattern` | String | Yes | Pattern/keywords in email subject (e.g., "transaction alert") |
| `subject_regex` | String | No | Optional regex for subject matching |
| `sample_email_body` | Text | Yes | Sample email body for reference/testing |
| `parsing_template` | JSON | Yes | Parsing rules to extract transaction fields |
| `is_active` | Boolean | Yes | Enable/disable this account |
| `currency_default` | String | No | Default currency (e.g., "INR") |
| `default_transaction_type` | String | No | Default type: "Expense" or "Income" |
| `created_at` | DateTime | Auto | Creation timestamp |
| `updated_at` | DateTime | Auto | Last update timestamp |

### 4.3 Account Operations

#### 4.3.1 Add Account

**Trigger:** User wants to configure a new credit card email alert

**Input Required:**
- Account name
- Sender email address
- Email subject (or pattern)
- Sample email body (for parsing template creation)

**Process:**
1. User provides sender email and subject pattern
2. User pastes a sample email body
3. System analyzes sample email body
4. System suggests parsing template (regex/pattern based)
5. User reviews and confirms field mappings
6. Account is saved and activated

**Validation Rules:**
- Sender email must be valid email format
- Subject pattern must not be empty
- Sample email body must contain extractable data
- Parsing template must successfully extract at least: amount, merchant

#### 4.3.2 Update Account

**Trigger:** User wants to modify existing account configuration

**Allowed Updates:**
- Account name
- Sender email
- Subject pattern
- Sample email body
- Parsing template
- Active status
- Default currency
- Default transaction type

**Process:**
1. User selects existing account
2. User modifies required fields
3. If sample email body changed, re-validate parsing template
4. Save changes

#### 4.3.3 Delete Account

**Trigger:** User wants to remove an account

**Process:**
1. User selects account to delete
2. System shows confirmation dialog
3. Options:
   - Delete account only (keep historical transactions)
   - Delete account and all associated transactions
4. User confirms deletion
5. Account is soft-deleted (marked inactive) or hard-deleted based on choice

#### 4.3.4 List Accounts

**Display:**
- Account name
- Card identifier (last 4 digits if available)
- Sender email
- Active/Inactive status
- Transaction count
- Last transaction date

---

## 5. Email Parsing Configuration

### 5.1 Parsing Template Structure

The parsing template defines how to extract transaction data from email body.

```json
{
  "parser_type": "regex",
  "fields": {
    "price": {
      "pattern": "Rs\\.?\\s*([\\d,]+\\.?\\d*)",
      "group": 1,
      "transform": "to_number"
    },
    "note": {
      "pattern": "at\\s+([A-Za-z0-9\\s]+?)\\s+on",
      "group": 1,
      "transform": "trim"
    },
    "card_last_four": {
      "pattern": "card ending (\\d{4})",
      "group": 1,
      "transform": "none"
    },
    "date": {
      "pattern": "on\\s+(\\d{2}-\\d{2}-\\d{4})",
      "group": 1,
      "transform": "to_date",
      "date_format": "DD-MM-YYYY",
      "output_format": "YYYY-MM-DD"
    },
    "time": {
      "pattern": "at\\s+(\\d{2}:\\d{2}:\\d{2})",
      "group": 1,
      "transform": "to_time",
      "output_format": "HH:mm:ss"
    },
    "reference_number": {
      "pattern": "Ref(?:erence)?\\s*(?:No\\.?)?\\s*:?\\s*(\\w+)",
      "group": 1,
      "transform": "none",
      "optional": true
    },
    "transaction_type": {
      "detect_from": "keywords",
      "expense_keywords": ["debited", "spent", "charged", "paid"],
      "income_keywords": ["credited", "received", "refund", "cashback"],
      "default": "Expense"
    }
  },
  "currency": {
    "detect": true,
    "pattern": "(INR|USD|EUR|Rs\\.?)",
    "default": "INR"
  }
}
```

### 5.2 Supported Parser Types

| Type | Description |
|------|-------------|
| `regex` | Regular expression based extraction |
| `template` | Template-based with placeholders |
| `ai` | AI/ML based extraction (future) |

### 5.3 Transform Functions

| Function | Description |
|----------|-------------|
| `none` | No transformation |
| `trim` | Remove leading/trailing whitespace |
| `to_number` | Convert to numeric value (removes commas) |
| `to_date` | Parse as date (output: YYYY-MM-DD) |
| `to_time` | Parse as time (output: HH:mm:ss) |
| `to_uppercase` | Convert to uppercase |
| `to_lowercase` | Convert to lowercase |

### 5.4 Sample Email Formats

#### Example 1: HDFC Bank (Expense)

**Sender:** alerts@hdfcbank.net  
**Subject:** Alert: Transaction on HDFC Bank Credit Card

**Body:**
```
Dear Customer,

Rs. 1,234.50 has been debited from your HDFC Bank Credit Card ending 4567 
at AMAZON INDIA on 15-02-2026 at 14:30:25.

Reference No: TXN123456789

If not done by you, call 1800-XXX-XXXX immediately.
```

**Parsed Output:**
| Field | Value |
|-------|-------|
| Price | 1234.50 |
| Currency | INR |
| Note | AMAZON INDIA |
| Date | 2026-02-15 |
| Time | 14:30:25 |
| Transaction | Expense |

#### Example 2: ICICI Bank Credit Card (Transaction Alert)

**Sender:** credit_cards@icicibank.com  
**Subject:** Transaction alert for your ICICI Bank Credit Card

**Body:**
```
Dear Customer,

Your ICICI Bank Credit Card XX0001 has been used for a transaction of INR 240.00 on Feb 16, 2026 at 10:31:46. Info: TWINS TOWER CASH.

The Available Credit Limit on your card is INR 94,678.14 and Total Credit Limit is INR 1,30,000.00. The above limits are a total of the limits of all the Credit Cards issued to the primary card holder, including any supplementary cards.
This is an auto-generated e-mail. Please do not reply.

Discover a new way of paying your Credit Card bills from your bank account anytime anywhere by using ICICI Bank iMobile Pay. GPRS users, SMS iMobile Pay to 56767661. For details, please click here.
```

**Parsed Output:**
| Field | Value |
|-------|-------|
| Price | 240.00 |
| Currency | INR |
| Note | TWINS TOWER CASH |
| Date | 2026-02-16 |
| Time | 10:31:46 |
| Card Last Four | 0001 |
| Transaction | Expense |
| Account | ICICI Bank Credit Card |

**CSV Export Row:**
```csv
Ledger,Category,Subcategory,Currency,Price,Account,Recorder,Date,Time,Note,Transaction
,Uncategorized,,INR,240.0,ICICI Bank Credit Card,Auto,2026-02-16,10:31:46,TWINS TOWER CASH,Expense
```

#### Example 3: ICICI Bank (Refund/Income)

**Sender:** credit_cards@icicibank.com  
**Subject:** Transaction alert for your ICICI Bank Credit Card

**Body:**
```
Your ICICI Bank Credit Card XX1234 has been credited with INR 2,000.16 
as refund from IRCTC on 09-Feb-2026.
```

**Parsed Output:**
| Field | Value |
|-------|-------|
| Price | 2000.16 |
| Currency | INR |
| Note | IRCTC |
| Date | 2026-02-09 |
| Transaction | Income |

---

## 6. Data Models

### 6.1 Transaction Format Specification

The core transaction format used throughout the system:

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `ledger` | String | No | Ledger/group for accounting | "Personal", "Business" |
| `category` | String | No | Main category | "Food & Dining" |
| `subcategory` | String | No | Sub-category | "Restaurants" |
| `currency` | String | Yes | ISO currency code | "INR", "USD" |
| `price` | Decimal | Yes | Transaction amount (always positive) | 580.70 |
| `account` | String | No | Account/Card name | "SBI Credit Card" |
| `recorder` | String | No | Who recorded the transaction | "Auto", "Manual" |
| `date` | String | Yes | Date in YYYY-MM-DD format | "2026-02-12" |
| `time` | String | No | Time in HH:mm:ss format | "14:30:25" |
| `note` | String | Yes | Merchant/Description | "ZOMATO NEW DELHI IN" |
| `transaction` | String | Yes | Type: "Expense" or "Income" | "Expense" |

### 6.2 Server-Side Database Schema

#### 6.2.1 Users Table

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PRIMARY KEY |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL |
| `device_token` | VARCHAR(255) | APNs device token |
| `created_at` | TIMESTAMP | DEFAULT NOW() |
| `updated_at` | TIMESTAMP | DEFAULT NOW() |

#### 6.2.2 Accounts Table (Server)

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PRIMARY KEY |
| `user_id` | UUID | FOREIGN KEY → Users |
| `account_name` | VARCHAR(100) | NOT NULL |
| `card_last_four` | VARCHAR(4) | |
| `sender_email` | VARCHAR(255) | NOT NULL |
| `sender_name` | VARCHAR(100) | |
| `subject_pattern` | VARCHAR(255) | NOT NULL |
| `subject_regex` | TEXT | |
| `sample_email_body` | TEXT | NOT NULL |
| `parsing_template` | JSONB | NOT NULL |
| `is_active` | BOOLEAN | DEFAULT TRUE |
| `currency_default` | VARCHAR(3) | DEFAULT 'INR' |
| `default_transaction_type` | VARCHAR(10) | DEFAULT 'Expense' |
| `created_at` | TIMESTAMP | DEFAULT NOW() |
| `updated_at` | TIMESTAMP | DEFAULT NOW() |

#### 6.2.3 Processed Emails Table

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PRIMARY KEY |
| `message_id` | VARCHAR(255) | UNIQUE, NOT NULL |
| `account_id` | UUID | FOREIGN KEY → Accounts |
| `processed_at` | TIMESTAMP | DEFAULT NOW() |
| `status` | VARCHAR(20) | 'success', 'failed', 'skipped' |
| `error_message` | TEXT | |

### 6.3 iOS Local Database Schema (SQLite)

#### 6.3.1 Accounts Table (Local)

```sql
CREATE TABLE accounts (
    id TEXT PRIMARY KEY,
    account_name TEXT NOT NULL,
    card_last_four TEXT,
    sender_email TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    currency_default TEXT DEFAULT 'INR',
    default_transaction_type TEXT DEFAULT 'Expense',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    synced_at TEXT
);

CREATE INDEX idx_accounts_name ON accounts(account_name);
```

#### 6.3.2 Ledgers Table

```sql
CREATE TABLE ledgers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_default INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Default ledger
INSERT INTO ledgers (id, name, is_default) VALUES ('default', 'Personal', 1);
```

#### 6.3.3 Categories Table

```sql
CREATE TABLE categories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    icon TEXT,
    color TEXT,
    is_system INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_categories_name ON categories(name);
```

#### 6.3.4 Subcategories Table

```sql
CREATE TABLE subcategories (
    id TEXT PRIMARY KEY,
    category_id TEXT NOT NULL,
    name TEXT NOT NULL,
    icon TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
    UNIQUE(category_id, name)
);

CREATE INDEX idx_subcategories_category ON subcategories(category_id);
```

#### 6.3.5 Transactions Table

```sql
CREATE TABLE transactions (
    id TEXT PRIMARY KEY,
    external_transaction_id TEXT UNIQUE,
    
    -- Core fields matching export format
    ledger_id TEXT,
    category_id TEXT,
    subcategory_id TEXT,
    currency TEXT NOT NULL DEFAULT 'INR',
    price REAL NOT NULL,
    account_id TEXT,
    recorder TEXT DEFAULT 'Auto',
    date TEXT NOT NULL,                    -- Format: YYYY-MM-DD
    time TEXT,                             -- Format: HH:mm:ss
    note TEXT NOT NULL,                    -- Merchant/Description
    transaction_type TEXT NOT NULL DEFAULT 'Expense',  -- 'Expense' or 'Income'
    
    -- Additional metadata
    reference_number TEXT,
    is_manual INTEGER DEFAULT 0,
    is_recurring INTEGER DEFAULT 0,
    tags TEXT,                             -- JSON array of tags
    
    -- Timestamps
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    synced_at TEXT,
    
    -- Foreign keys
    FOREIGN KEY (ledger_id) REFERENCES ledgers(id),
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (subcategory_id) REFERENCES subcategories(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

-- Indexes for common queries
CREATE INDEX idx_transactions_date ON transactions(date DESC);
CREATE INDEX idx_transactions_category ON transactions(category_id);
CREATE INDEX idx_transactions_account ON transactions(account_id);
CREATE INDEX idx_transactions_type ON transactions(transaction_type);
CREATE INDEX idx_transactions_note ON transactions(note);
```

#### 6.3.6 Vendor Category Mapping Table

```sql
CREATE TABLE vendor_category_mappings (
    id TEXT PRIMARY KEY,
    vendor_keyword TEXT NOT NULL,
    category_id TEXT NOT NULL,
    subcategory_id TEXT,
    is_user_defined INTEGER DEFAULT 0,
    match_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (subcategory_id) REFERENCES subcategories(id)
);

CREATE INDEX idx_vendor_mappings_keyword ON vendor_category_mappings(vendor_keyword);
```

### 6.4 Default Categories and Subcategories

| Category | Subcategories | Icon | Color |
|----------|---------------|------|-------|
| Food & Dining | Restaurants, Cafes, Fast Food, Food Delivery | 🍔 | #FF6B6B |
| Shopping | Online Shopping, Clothing, Electronics, Home & Garden | 🛒 | #4ECDC4 |
| Transportation | Cab/Taxi, Public Transport, Parking, Toll | 🚗 | #45B7D1 |
| Entertainment | Movies, Games, Events, Streaming | 🎬 | #96CEB4 |
| Bills & Utilities | Electricity, Water, Gas, Internet, Phone | 📄 | #FFEAA7 |
| Health & Medical | Doctor, Pharmacy, Hospital, Gym | 🏥 | #DDA0DD |
| Travel | Flights, Hotels, Train, Bus | ✈️ | #98D8C8 |
| Groceries | Supermarket, Vegetables, Dairy | 🥬 | #7CB342 |
| Fuel | Petrol, Diesel, CNG, EV Charging | ⛽ | #FF8A65 |
| Subscriptions | Streaming, Software, Magazines | 📱 | #BA68C8 |
| Education | Courses, Books, Tuition | 📚 | #64B5F6 |
| Personal Care | Salon, Spa, Cosmetics | 💅 | #F48FB1 |
| Insurance | Life, Health, Vehicle, Home | 🛡️ | #90A4AE |
| Investments | Mutual Funds, Stocks, FD, RD | 📈 | #4DB6AC |
| Income | Salary, Refund, Cashback, Interest, Gift | 💰 | #66BB6A |
| Transfer | Bank Transfer, Wallet Transfer | 🔄 | #78909C |
| Uncategorized | - | ❓ | #BDBDBD |

### 6.5 Default Vendor Mappings

| Vendor Keyword | Category | Subcategory |
|----------------|----------|-------------|
| ZOMATO | Food & Dining | Food Delivery |
| SWIGGY | Food & Dining | Food Delivery |
| AMAZON | Shopping | Online Shopping |
| FLIPKART | Shopping | Online Shopping |
| UBER | Transportation | Cab/Taxi |
| OLA | Transportation | Cab/Taxi |
| NETFLIX | Subscriptions | Streaming |
| IRCTC | Travel | Train |
| BLINKIT | Groceries | Supermarket |
| BLINK COMMERCE | Groceries | Supermarket |
| GOOGLE CLOUD | Bills & Utilities | Internet |
| MAKEMYTRIP | Travel | Flights |
| TWINS TOWER | Uncategorized | - |
| CASH | Uncategorized | - |
| ATM | Uncategorized | ATM Withdrawal |

---

## 7. API Specifications

### 7.1 Account Management APIs

#### 7.1.1 Create Account

```
POST /api/v1/accounts
```

**Request Body:**
```json
{
  "account_name": "HDFC Credit Card",
  "card_last_four": "4567",
  "sender_email": "alerts@hdfcbank.net",
  "sender_name": "HDFC Bank Alerts",
  "subject_pattern": "Transaction Alert",
  "sample_email_body": "Rs. 1,234.50 has been debited...",
  "parsing_template": { ... },
  "currency_default": "INR",
  "default_transaction_type": "Expense"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid-here",
    "account_name": "HDFC Credit Card",
    ...
  }
}
```

#### 7.1.2 Get All Accounts

```
GET /api/v1/accounts
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid-1",
      "account_name": "HDFC Credit Card",
      "sender_email": "alerts@hdfcbank.net",
      "is_active": true,
      "transaction_count": 45,
      "last_transaction_date": "2026-02-15"
    }
  ]
}
```

#### 7.1.3 Get Account by ID

```
GET /api/v1/accounts/{id}
```

#### 7.1.4 Update Account

```
PUT /api/v1/accounts/{id}
```

**Request Body:** (partial update allowed)
```json
{
  "account_name": "HDFC Platinum Card",
  "is_active": false
}
```

#### 7.1.5 Delete Account

```
DELETE /api/v1/accounts/{id}?delete_transactions=false
```

**Query Parameters:**
- `delete_transactions`: If true, also delete associated transactions

#### 7.1.6 Test Parsing Template

```
POST /api/v1/accounts/test-parser
```

**Request Body:**
```json
{
  "sample_email_body": "Rs. 1,234.50 has been debited...",
  "parsing_template": { ... }
}
```

**Response:**
```json
{
  "success": true,
  "extracted_data": {
    "price": 1234.50,
    "currency": "INR",
    "note": "AMAZON INDIA",
    "date": "2026-02-15",
    "time": "14:30:25",
    "transaction": "Expense"
  },
  "warnings": []
}
```

### 7.2 Transaction APIs

#### 7.2.1 Push Notification Payload

```json
{
  "aps": {
    "content-available": 1
  },
  "transaction": {
    "id": "txn-uuid",
    "ledger": null,
    "category": "Shopping",
    "subcategory": "Online Shopping",
    "currency": "INR",
    "price": 1234.50,
    "account": "HDFC Credit Card",
    "recorder": "Auto",
    "date": "2026-02-15",
    "time": "14:30:25",
    "note": "AMAZON INDIA",
    "transaction": "Expense"
  }
}
```

#### 7.2.2 Get Transactions

```
GET /api/v1/transactions?since={timestamp}&limit={limit}
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "txn-uuid",
      "ledger": null,
      "category": "Shopping",
      "subcategory": "Online Shopping",
      "currency": "INR",
      "price": 1234.50,
      "account": "HDFC Credit Card",
      "recorder": "Auto",
      "date": "2026-02-15",
      "time": "14:30:25",
      "note": "AMAZON INDIA",
      "transaction": "Expense"
    }
  ],
  "pagination": {
    "has_more": true,
    "next_cursor": "cursor-token"
  }
}
```

### 7.3 Category APIs

#### 7.3.1 Get Categories with Subcategories

```
GET /api/v1/categories
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "cat-1",
      "name": "Food & Dining",
      "icon": "🍔",
      "color": "#FF6B6B",
      "subcategories": [
        {"id": "sub-1", "name": "Restaurants"},
        {"id": "sub-2", "name": "Food Delivery"}
      ]
    }
  ]
}
```

#### 7.3.2 Sync Categories

```
POST /api/v1/categories/sync
```

### 7.4 Device Registration

#### 7.4.1 Register Device

```
POST /api/v1/devices/register
```

**Request Body:**
```json
{
  "device_token": "apns-device-token",
  "device_name": "iPhone 15 Pro",
  "os_version": "17.3"
}
```

---

## 8. Non-Functional Requirements

### 8.1 Performance

| Metric | Target |
|--------|--------|
| Email detection latency | < 30 seconds |
| Email parsing time | < 2 seconds |
| Push notification delivery | < 10 seconds from parsing |
| SQLite query response | < 100 ms |
| App launch time | < 2 seconds |
| Daily transaction capacity | 100+ per user |
| Local database size support | Up to 1 GB |

### 8.2 Reliability

- No duplicate transaction entries
- Idempotent processing on server and iOS
- Graceful handling of network failures
- Local data persists across app restarts
- 99.9% uptime for email monitoring service
- Automatic retry for failed push notifications

### 8.3 Security

- No full credit card numbers stored anywhere
- No raw email body stored on server (only on user request)
- HTTPS/TLS for all API communications
- Push payload encrypted
- No sensitive tokens in push notifications
- User data stored only locally unless explicitly synced
- API authentication via JWT tokens

### 8.4 Offline Capability

- App functions fully without internet
- All transaction history accessible offline
- Category mapping works offline
- Pending sync queue for offline changes
- Automatic sync when online

### 8.5 Scalability

- Support 100+ users initially
- Horizontal scaling for email monitoring
- Rate limiting for API endpoints

---

## 9. Data Flow

### 9.1 Email to Transaction Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         DATA FLOW                                │
└─────────────────────────────────────────────────────────────────┘

1. Credit Card Transaction Occurs
           │
           ▼
2. Bank Sends Email Alert
           │
           ▼
3. Email Arrives in Monitored Inbox
           │
           ▼
4. Server Detects New Email
           │
           ▼
5. Server Matches Email to Account
   (using sender_email + subject_pattern)
           │
           ▼
6. Server Parses Email Using Account's Template
           │
           ▼
7. Server Extracts Transaction Data
   {price, currency, note, date, time, transaction_type}
           │
           ▼
8. Server Applies Category Mapping
   (note → category + subcategory)
           │
           ▼
9. Server Sends Push Notification via APNs
           │
           ▼
10. iOS Receives Push Notification
           │
           ▼
11. iOS Stores Transaction in SQLite
    {ledger, category, subcategory, currency, price, 
     account, recorder, date, time, note, transaction}
           │
           ▼
12. Transaction Displayed to User
```

### 9.2 Account Configuration Flow

```
1. User Opens "Add Account" Screen
           │
           ▼
2. User Enters:
   - Account Name
   - Sender Email
   - Subject Pattern
   - Sample Email Body
           │
           ▼
3. System Analyzes Sample Email
           │
           ▼
4. System Suggests Parsing Template
           │
           ▼
5. User Reviews Extracted Fields:
   - Price, Currency, Note, Date, Time, Transaction Type
           │
           ▼
6. User Confirms/Adjusts Mappings
           │
           ▼
7. Account Saved & Activated
           │
           ▼
8. Server Starts Monitoring for This Pattern
```

---

## 10. User Interface Requirements

### 10.1 iOS App Screens

#### 10.1.1 Home / Dashboard ✅ IMPLEMENTED
**Summary Cards (4 KPIs):**
- Total spending for selected period
- Transaction count
- Average transaction amount
- Largest transaction

**Category Pie Chart:**
- Donut chart showing spending by category (top 6)
- Color-coded legend with amounts
- Uses Swift Charts SectorMark

**Spending Trend Chart:**
- Area + Line chart showing daily spending
- X-axis: Date (abbreviated month + day)
- Y-axis: Amount in compact format (K for thousands)
- Gap-filled for continuous display

**Top Merchants Table:**
- Ranked list of top 5 merchants by total spend
- Shows transaction count per merchant
- Sorted by total amount descending

**Recent Transactions:**
- Quick view of last 5 transactions
- Vendor, category, amount, date

**Time Period Filter:**
- Week (7 days)
- Month (30 days) - default
- Quarter (90 days)
- Year (365 days)

**Features:**
- Pull to refresh with backend sync
- Swift Charts integration
- Responsive layout with LazyVGrid

#### 10.1.2 Transactions List
- Chronological transaction list
- Filter by:
  - Date range
  - Category/Subcategory
  - Account
  - Transaction type (Expense/Income)
  - Ledger
- Search by merchant name (note)
- Tap to view details
- Color coding: Red for Expense, Green for Income

#### 10.1.3 Transaction Detail
- All transaction fields displayed:
  - Ledger
  - Category / Subcategory
  - Currency + Price
  - Account
  - Date + Time
  - Note (Merchant)
  - Transaction Type
- Edit option for manual corrections
- Delete option
- Share transaction

#### 10.1.4 Add/Edit Transaction (Manual)
- Ledger selector
- Category selector → Subcategory selector
- Currency selector
- Price input (numeric keyboard)
- Account selector (optional)
- Date picker
- Time picker (optional)
- Note/Description input
- Transaction type toggle (Expense/Income)
- Save/Cancel buttons

#### 10.1.5 Categories
- List of all categories with subcategories
- Transaction count per category
- Edit category (name, icon, color)
- Add custom category
- Add subcategory
- Delete category (with confirmation)

#### 10.1.6 Accounts Management
- List of configured accounts
- Add new account button
- Account status (active/inactive)
- Tap to edit account
- Swipe to delete

#### 10.1.7 Add/Edit Account
- Account name input
- Sender email input
- Subject pattern input
- Sample email body (multiline text)
- Test parsing button
- Parsing result preview showing all fields
- Default currency selector
- Default transaction type selector
- Save/Cancel buttons

#### 10.1.8 Settings
- Push notification preferences
- Default currency
- Default ledger
- Data export options (CSV)
- Import transactions
- About / Help

### 10.2 UI/UX Guidelines

- Clean, minimal design
- Dark mode support
- Haptic feedback for actions
- Pull-to-refresh everywhere
- Swipe gestures for quick actions
- Empty states with helpful messages
- Loading indicators for async operations
- Transaction type color coding:
  - Expense: Red/Orange tint
  - Income: Green tint

---

## 11. Export Format

### 11.1 CSV Export Format

The system exports transactions in the following CSV format:

```csv
Ledger,Category,Subcategory,Currency,Price,Account,Recorder,Date,Time,Note,Transaction
,Food & Dining,Food Delivery,INR,580.7,SBI Card,Auto,2026-02-08,,ZOMATO NEW DELHI IN,Expense
,Shopping,Online Shopping,INR,13998.0,SBI Card,Auto,2026-01-18,,AMAZONIN GURGAON IN,Expense
,Income,Refund,INR,2000.16,SBI Card,Auto,2026-02-09,,IRCTC E TICKETING WEBS NEW DELHI IN,Income
```

### 11.2 Export Field Specifications

| Column | Description | Format | Required |
|--------|-------------|--------|----------|
| Ledger | Ledger name | String | No |
| Category | Category name | String | No |
| Subcategory | Subcategory name | String | No |
| Currency | ISO currency code | "INR", "USD", etc. | Yes |
| Price | Transaction amount | Decimal, positive | Yes |
| Account | Account/Card name | String | No |
| Recorder | Who recorded | "Auto" or "Manual" | No |
| Date | Transaction date | YYYY-MM-DD | Yes |
| Time | Transaction time | HH:mm:ss or empty | No |
| Note | Merchant/Description | String | Yes |
| Transaction | Type | "Expense" or "Income" | Yes |

### 11.3 Import Support

The app shall support importing transactions from CSV files in the same format.

**Import Validation:**
- Date must be valid YYYY-MM-DD
- Price must be positive number
- Transaction must be "Expense" or "Income"
- Currency must be valid ISO code
- Duplicate detection based on Date + Price + Note

---

## 12. Future Extensibility

### 12.1 Phase 6: Tools & Import Features (IMPLEMENTED)

#### 12.1.1 Paytm Excel Import Tool

**Purpose**: Allow users to import transactions from Paytm export Excel files.

**Status**: ✅ IMPLEMENTED

**Features**:

1. **File Upload**
   - Accept Excel files (.xlsx, .xls) exported from Paytm
   - Backend API endpoint: `POST /tools/import/paytm`
   - iOS UI: File picker in Tools tab with document picker

2. **Parsing & Preview**
   - Parse Paytm Excel format columns (Date, Time, Transaction Details, Your Account, Amount, Tags)
   - Automatic column detection and header row identification
   - Category/Subcategory extraction from Tags (format: `#Category: Subcategory`)
   - Emoji prefix removal from tags
   - Show preview table before import with first 5 transactions

3. **Column Mapping (Editable)**
   - Display detected column mappings (Excel Column → Internal Field)
   - User can change mapping via dropdown picker
   - Available internal fields:
     - Date, Time, Notes/Vendor, Amount, Status, Reference ID, Category/Subcategory, Account, "-- Skip --"
   - Sample values shown for each mapping

4. **Import Options (User Configurable)**
   - **Create Categories**: Toggle ON/OFF
     - ON: Create new categories if not found in database
     - OFF: Use existing categories, fallback to "Others" if not matched
   - **Create Subcategories**: Toggle ON/OFF
     - ON: Create new subcategories if not found in database
     - OFF: Use existing subcategories, fallback to "Others" if not matched
   - **Create Accounts**: Toggle ON/OFF
     - ON: Auto-create UserAccount for unique account names (e.g., "ICICI Bank Credit Card")
     - OFF: Store account name as text only, no UserAccount linking

5. **User Confirmation Flow**
   - Display import summary (total rows, valid, skipped)
   - **Smart Category/Subcategory Preview**:
     - Fetch existing categories/subcategories from API
     - Show categories found in file with icons indicating:
       - ✓ (green) = Will use existing category
       - + (blue/purple) = Will create new (if toggle ON)
       - → (orange) = Will map to "Others" (if toggle OFF)
     - Same for subcategories
   - **Account Preview**:
     - Show accounts found in file
     - Display "₹0 balance" for accounts that will be created
   - User options:
     - **Import [N]** → Create transactions with selected options
     - **Download CSV** → Document picker to save parsed data without importing
     - **Cancel** → Abort operation
   - **Detailed Success Notification**:
     - ✓ X transactions imported
     - ✓ Y new categories created (if any)
     - ✓ Z new subcategories created (if any)
     - ✓ N new accounts created (with ₹0 starting balance) (if any)

6. **Duplicate Prevention**
   - Track imported files in `import_history` table
   - Store: filename, file_hash (SHA256), import_date, transaction_count
   - Warn if same file previously imported (duplicate_warning flag)
   - Allow re-import with explicit confirmation

7. **Rollback Import**
   - Each import history entry shows rollback button (⟲)
   - Confirmation dialog before rollback
   - Deletes all transactions from that import using idempotency_key matching
   - Removes import history record
   - Returns count of deleted transactions

8. **CSV Download**
   - Document picker allows user to choose save location
   - Generates CSV with all parsed fields
   - Filename defaults to `{original}_parsed.csv`

**API Endpoints**:
```
POST   /tools/import/paytm                      - Upload and parse Excel, returns preview
POST   /tools/import/paytm/confirm              - Confirm import with options
GET    /tools/import/paytm/download-csv         - Download parsed CSV
GET    /tools/import/history                    - List import history
GET    /tools/import/history/{id}               - Get specific import history
POST   /tools/import/history/{id}/rollback      - Rollback import (delete transactions)
DELETE /tools/import/history/{id}               - Delete history entry
```

**Request: Import Confirm**:
```json
{
  "preview_token": "uuid",
  "user_account_id": "uuid (optional)",
  "create_categories": true,
  "create_subcategories": true,
  "create_accounts": true,
  "column_mappings": [
    {
      "excel_column": "Transaction Details",
      "internal_field": "Notes / Vendor",
      "is_enabled": true
    }
  ]
}
```

**Response: Import Preview**:
```json
{
  "filename": "Paytm_Statement.xlsx",
  "file_hash": "sha256...",
  "file_type": "paytm_excel",
  "total_rows": 58,
  "valid_transactions": 58,
  "skipped_rows": 0,
  "duplicate_warning": false,
  "transactions": [...],
  "preview_token": "uuid",
  "column_mappings": [
    {"excel_column": "Date", "internal_field": "Date", "sample_value": "2026-02-14"},
    {"excel_column": "Your Account", "internal_field": "Account", "sample_value": "ICICI Bank Credit Card"}
  ],
  "unique_accounts": ["ICICI Bank Credit Card", "State Bank Of India - 23", "UPI Lite"]
}
```

**Response: Import Confirm**:
```json
{
  "success": true,
  "message": "Successfully imported 58 transactions. Created 5 categories. Created 12 subcategories. Created 3 accounts.",
  "import_history_id": "uuid",
  "transactions_created": 58,
  "transactions_skipped": 0,
  "categories_created": 5,
  "subcategories_created": 12,
  "accounts_created": 3
}
```

**Response: Rollback**:
```json
{
  "success": true,
  "message": "Rolled back import of Paytm_Statement.xlsx. Deleted 58 transactions.",
  "transactions_deleted": 58,
  "import_history_deleted": true
}
```

**Data Model - ImportHistory**:
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| filename | string | Original file name |
| file_hash | string | SHA256 hash for dedup |
| file_type | string | "paytm_excel", "bank_statement" |
| transaction_count | int | Number of transactions |
| skipped_count | int | Number skipped |
| imported_at | datetime | Timestamp |
| status | string | completed/partial/failed |

**iOS UI Components**:
- `ImportSectionView`: Main import interface in Tools tab
- `ImportPreviewSection`: Shows preview with column mappings and options
- `ColumnMappingRow`: Editable row with picker for field mapping
- `ImportHistoryRow`: History item with rollback button
- `CSVDocument`: FileDocument for save picker

---

### 12.2 Phase 7: User Financial Accounts (IMPLEMENTED)

**Purpose**: Manage user's financial accounts separate from parser profiles.

**Status**: ✅ IMPLEMENTED

**Features**:

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
| name | string | Yes | Display name |
| account_type | enum | Yes | bank_account/credit_card/wallet/cash/investment |
| institution | string | No | Bank/Provider name |
| account_number_last4 | string | No | Last 4 digits |
| currency | string | Yes | Default: INR |
| initial_balance | decimal | No | Starting balance |
| current_balance | decimal | No | Calculated balance |
| is_active | bool | Yes | Show in dropdowns |
| include_in_total | bool | Yes | Include in net worth calculation |
| color | string | No | UI color (hex) |
| icon | string | No | SF Symbol name |
| primary_source | string | No | "email", "import", "manual" |

3. **Transaction Integration**
   - Each transaction links to account via `user_account_id`
   - Filter transactions by account
   - Account balance auto-calculated from transactions
   - Account picker dropdown in Edit Transaction view (shows all UserAccounts)
   - **Automatic Balance Updates**:
     - When transaction created → recalculate linked account balance
     - When transaction updated (amount/type/account changed) → recalculate affected account(s) balance
     - When transaction deleted → recalculate linked account balance
     - Balance formula: `current_balance = initial_balance + sum(Income) - sum(Expense)`

4. **Auto-Create During Import**
   - Import tool can auto-create UserAccount for unique account names
   - Controlled by `create_accounts` toggle
   - Defaults to "wallet" type for Paytm imports
   - New accounts created with ₹0 starting balance
   - Import success notification shows count of accounts created

**API Endpoints**:
```
GET    /user-accounts/              - List accounts
POST   /user-accounts/              - Create account
GET    /user-accounts/{id}          - Get account
PUT    /user-accounts/{id}          - Update account
DELETE /user-accounts/{id}          - Delete account
GET    /user-accounts/{id}/transactions - Account transactions
POST   /user-accounts/transfer      - Transfer between accounts
```

**iOS UI Components**:
- `AccountsView`: Tab for managing accounts (list, create, edit)
- `EditAccountView`: Form for account details
- `EditTransactionView`: 
  - Category picker dropdown (fetches from API)
  - Subcategory picker dropdown (filtered by selected category)
  - Account picker dropdown (shows all UserAccounts)

---

### 12.3 Phase 8: Transaction Sources & iOS Shortcuts (PLANNED)

**Transaction Source Types**:
| Source | recorder value | Description |
|--------|----------------|-------------|
| Email | "Auto" | Parsed from bank email |
| Manual | "Manual" | User entered |
| Import | "Import" | From file (Paytm, etc.) |
| SMS | "SMS" | Via iOS Shortcut |
| API | "API" | External API call |

**iOS Shortcuts Integration**:
- User creates iOS Shortcut triggered by bank SMS
- Shortcut extracts transaction info
- Calls SpendWise API with auth token
- API validates and creates transaction

**Shortcut API Endpoint**:
```
POST /shortcuts/transaction
Headers:
  X-Shortcut-Token: <user-token>
Body:
  {
    "raw_text": "SMS content",
    "source": "sms",
    "sender": "ICICIBK"
  }
```

---

### 12.4 Other Future Enhancements

The system shall be designed to support:

- Multi-device synchronization
- Cloud transaction backup
- Web dashboard
- Analytics and reporting
- Budget tracking and alerts
- Export to CSV/JSON/PDF
- Multi-user/family support
- Multiple email account monitoring
- AI-based category suggestions
- Receipt image attachment
- Bank statement import (HDFC, ICICI, SBI PDF/CSV)
- Recurring transaction detection
- Spending insights and trends
- Split transactions
- Multi-currency support with conversion
- Scheduled/planned transactions

---

## 13. Assumptions & Constraints

### 13.1 Assumptions

- Single-user per device (initially)
- User has access to email receiving transaction alerts
- Email format from banks is consistent
- Approximately 20 transactions per day average
- SQLite sufficient for long-term storage
- Server responsible for email parsing accuracy
- User has stable internet for initial setup
- All amounts are positive (type determines debit/credit)

### 13.2 Constraints

- Initial version: local storage only
- No mandatory cloud database for transactions
- Minimal infrastructure cost
- Low traffic volume (2–3 users initially)
- iOS only (no Android initially)
- English language only (initially)
- Date format: YYYY-MM-DD (ISO 8601)
- Time format: HH:mm:ss (24-hour)

---

## 14. Success Criteria

The system is considered successful when:

| Criteria | Metric |
|----------|--------|
| Email capture rate | > 99% of transaction emails captured |
| Parsing accuracy | > 95% correct field extraction |
| Categorization accuracy | > 90% correct auto-categorization |
| Duplicate prevention | 0% duplicate transactions |
| Data reliability | 100% data persistence |
| Offline functionality | Full feature access offline |
| User satisfaction | Account setup < 5 minutes |
| System cost | < $20/month infrastructure |
| Export compatibility | 100% valid CSV output |

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| Account | A configured credit card email template |
| APNs | Apple Push Notification Service |
| Category | Primary classification group for transactions |
| Subcategory | Secondary classification within a category |
| Ledger | Organizational grouping (e.g., Personal, Business) |
| Note | Merchant name or transaction description |
| Parsing Template | Rules for extracting data from email body |
| Price | Transaction amount (always positive) |
| Recorder | Source of transaction entry (Auto or Manual) |
| Transaction Type | Either "Expense" (debit) or "Income" (credit) |
| Vendor | Merchant/store where transaction occurred |

---

## Appendix B: Sample Parsing Templates

### B.1 HDFC Bank Template

```json
{
  "parser_type": "regex",
  "fields": {
    "price": {
      "pattern": "Rs\\.?\\s*([\\d,]+\\.?\\d*)",
      "group": 1,
      "transform": "to_number"
    },
    "note": {
      "pattern": "at\\s+([A-Za-z0-9\\s]+?)\\s+on",
      "group": 1,
      "transform": "trim"
    },
    "card_last_four": {
      "pattern": "ending\\s+(\\d{4})",
      "group": 1
    },
    "date": {
      "pattern": "on\\s+(\\d{2}-\\d{2}-\\d{4})",
      "group": 1,
      "date_format": "DD-MM-YYYY",
      "output_format": "YYYY-MM-DD"
    },
    "transaction_type": {
      "detect_from": "keywords",
      "expense_keywords": ["debited"],
      "income_keywords": ["credited"],
      "default": "Expense"
    }
  }
}
```

### B.2 ICICI Bank Credit Card Template

**Account Configuration:**
| Field | Value |
|-------|-------|
| Account Name | ICICI Bank Credit Card |
| Sender Email | credit_cards@icicibank.com |
| Subject Pattern | Transaction alert for your ICICI Bank Credit Card |

**Parsing Template:**
```json
{
  "parser_type": "regex",
  "fields": {
    "price": {
      "pattern": "INR\\s*([\\d,]+\\.\\d{2})",
      "group": 1,
      "transform": "to_number"
    },
    "currency": {
      "pattern": "(INR|USD|EUR)",
      "group": 1,
      "default": "INR"
    },
    "note": {
      "pattern": "Info:\\s*([A-Za-z0-9\\s]+?)\\.",
      "group": 1,
      "transform": "trim"
    },
    "card_last_four": {
      "pattern": "Credit Card XX(\\d{4})",
      "group": 1
    },
    "date": {
      "pattern": "on\\s+([A-Za-z]{3}\\s+\\d{1,2},\\s+\\d{4})",
      "group": 1,
      "date_format": "MMM DD, YYYY",
      "output_format": "YYYY-MM-DD"
    },
    "time": {
      "pattern": "at\\s+(\\d{2}:\\d{2}:\\d{2})",
      "group": 1,
      "output_format": "HH:mm:ss"
    },
    "transaction_type": {
      "detect_from": "keywords",
      "expense_keywords": ["has been used", "debited", "transaction of"],
      "income_keywords": ["credited", "refund", "cashback"],
      "default": "Expense"
    }
  }
}
```

**Test Input:**
```
Your ICICI Bank Credit Card XX0001 has been used for a transaction of INR 240.00 on Feb 16, 2026 at 10:31:46. Info: TWINS TOWER CASH.
```

**Expected Output:**
```json
{
  "price": 240.00,
  "currency": "INR",
  "note": "TWINS TOWER CASH",
  "card_last_four": "0001",
  "date": "2026-02-16",
  "time": "10:31:46",
  "transaction_type": "Expense"
}
```

### B.3 SBI Card Template

```json
{
  "parser_type": "regex",
  "fields": {
    "price": {
      "pattern": "Rs\\s*([\\d,]+\\.?\\d*)",
      "group": 1,
      "transform": "to_number"
    },
    "note": {
      "pattern": "at\\s+([A-Za-z0-9\\s]+?)\\s+on",
      "group": 1,
      "transform": "trim"
    },
    "card_last_four": {
      "pattern": "ending\\s+(\\d{4})",
      "group": 1
    },
    "date": {
      "pattern": "on\\s+(\\d{2}/\\d{2}/\\d{4})",
      "group": 1,
      "date_format": "DD/MM/YYYY",
      "output_format": "YYYY-MM-DD"
    },
    "transaction_type": {
      "detect_from": "keywords",
      "expense_keywords": ["used", "debited", "spent"],
      "income_keywords": ["credited", "refund"],
      "default": "Expense"
    }
  }
}
```

---

## Appendix C: Database Migration Scripts

### C.1 Initial Schema Setup (iOS)

```sql
-- Version 1.0

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- Create all tables
CREATE TABLE IF NOT EXISTS ledgers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_default INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    icon TEXT,
    color TEXT,
    is_system INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subcategories (
    id TEXT PRIMARY KEY,
    category_id TEXT NOT NULL,
    name TEXT NOT NULL,
    icon TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
    UNIQUE(category_id, name)
);

CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    account_name TEXT NOT NULL,
    card_last_four TEXT,
    sender_email TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    currency_default TEXT DEFAULT 'INR',
    default_transaction_type TEXT DEFAULT 'Expense',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    synced_at TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    external_transaction_id TEXT UNIQUE,
    ledger_id TEXT,
    category_id TEXT,
    subcategory_id TEXT,
    currency TEXT NOT NULL DEFAULT 'INR',
    price REAL NOT NULL,
    account_id TEXT,
    recorder TEXT DEFAULT 'Auto',
    date TEXT NOT NULL,
    time TEXT,
    note TEXT NOT NULL,
    transaction_type TEXT NOT NULL DEFAULT 'Expense',
    reference_number TEXT,
    is_manual INTEGER DEFAULT 0,
    is_recurring INTEGER DEFAULT 0,
    tags TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    synced_at TEXT,
    FOREIGN KEY (ledger_id) REFERENCES ledgers(id),
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (subcategory_id) REFERENCES subcategories(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS vendor_category_mappings (
    id TEXT PRIMARY KEY,
    vendor_keyword TEXT NOT NULL,
    category_id TEXT NOT NULL,
    subcategory_id TEXT,
    is_user_defined INTEGER DEFAULT 0,
    match_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (subcategory_id) REFERENCES subcategories(id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id);
CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_transactions_note ON transactions(note);
CREATE INDEX IF NOT EXISTS idx_subcategories_category ON subcategories(category_id);
CREATE INDEX IF NOT EXISTS idx_vendor_mappings_keyword ON vendor_category_mappings(vendor_keyword);
CREATE INDEX IF NOT EXISTS idx_accounts_name ON accounts(account_name);
CREATE INDEX IF NOT EXISTS idx_categories_name ON categories(name);

-- Insert default ledger
INSERT OR IGNORE INTO ledgers (id, name, is_default) VALUES ('default', 'Personal', 1);
```

---

**End of Document**
