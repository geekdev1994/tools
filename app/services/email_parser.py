"""
Email Parser Service
Parses transaction emails using regex patterns from Account configurations
"""
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from app.models import Account, Transaction, Category, VendorMapping
from app.core.database import SessionLocal


@dataclass
class ParsedTransaction:
    """Result of parsing an email"""
    amount: float
    vendor: str
    date: datetime
    time: Optional[str] = None
    account_number: Optional[str] = None
    currency: str = "INR"
    transaction_type: str = "Expense"
    confidence_score: float = 1.0
    
    # Categorization
    category: str = "Others"
    subcategory: str = "Others"


class EmailParser:
    """
    Parses transaction emails using regex patterns.
    Mirrors the iOS TransactionParser logic.
    """
    
    # Date format mappings for normalization
    MONTH_MAP = {
        'jan': '01', 'january': '01',
        'feb': '02', 'february': '02',
        'mar': '03', 'march': '03',
        'apr': '04', 'april': '04',
        'may': '05',
        'jun': '06', 'june': '06',
        'jul': '07', 'july': '07',
        'aug': '08', 'august': '08',
        'sep': '09', 'september': '09',
        'oct': '10', 'october': '10',
        'nov': '11', 'november': '11',
        'dec': '12', 'december': '12'
    }
    
    def __init__(self, account: Account):
        """Initialize parser with account configuration"""
        self.account = account
        self.amount_pattern = re.compile(account.amount_regex, re.IGNORECASE)
        self.date_pattern = re.compile(account.date_regex, re.IGNORECASE)
        self.merchant_pattern = re.compile(account.merchant_regex, re.IGNORECASE)
        
        self.time_pattern = None
        if account.time_regex:
            self.time_pattern = re.compile(account.time_regex, re.IGNORECASE)
        
        self.account_pattern = None
        if account.account_regex:
            self.account_pattern = re.compile(account.account_regex, re.IGNORECASE)
    
    def parse(self, email_body: str) -> Optional[ParsedTransaction]:
        """
        Parse email body and extract transaction details.
        Returns None if parsing fails.
        """
        try:
            # Extract amount
            amount = self._extract_amount(email_body)
            if amount is None:
                return None
            
            # Extract date
            date = self._extract_date(email_body)
            if date is None:
                return None
            
            # Extract merchant
            vendor = self._extract_merchant(email_body)
            if not vendor:
                return None
            
            # Extract optional fields
            time_str = self._extract_time(email_body)
            account_number = self._extract_account_number(email_body)
            
            # Build account name
            account_name = self.account.name
            if account_number:
                account_name = f"{self.account.name} XX{account_number}"
            
            # Create parsed result
            result = ParsedTransaction(
                amount=amount,
                vendor=vendor,
                date=date,
                time=time_str,
                account_number=account_number,
                currency=self.account.currency_default,
                transaction_type=self.account.default_transaction_type
            )
            
            # Apply category mapping
            self._apply_category(result, vendor)
            
            return result
            
        except Exception as e:
            print(f"Error parsing email: {e}")
            return None
    
    def _extract_amount(self, text: str) -> Optional[float]:
        """Extract transaction amount"""
        match = self.amount_pattern.search(text)
        if not match:
            return None
        
        # Get the captured group (amount value)
        amount_str = match.group(1)
        
        # Remove commas and convert to float
        amount_str = amount_str.replace(',', '')
        
        try:
            return float(amount_str)
        except ValueError:
            return None
    
    def _extract_date(self, text: str) -> Optional[datetime]:
        """Extract and normalize transaction date"""
        match = self.date_pattern.search(text)
        if not match:
            return None
        
        date_str = match.group(1) if match.lastindex else match.group(0)
        return self._normalize_date(date_str)
    
    def _normalize_date(self, date_str: str) -> Optional[datetime]:
        """
        Normalize various date formats to datetime.
        Handles formats like:
        - "Feb 16, 2026"
        - "16-02-2026"
        - "2026-02-16"
        - "16/02/2026"
        """
        date_str = date_str.strip()
        
        # Try common formats
        formats = [
            "%b %d, %Y",      # Feb 16, 2026
            "%B %d, %Y",      # February 16, 2026
            "%d-%m-%Y",       # 16-02-2026
            "%Y-%m-%d",       # 2026-02-16
            "%d/%m/%Y",       # 16/02/2026
            "%d %b %Y",       # 16 Feb 2026
            "%d %B %Y",       # 16 February 2026
            "%d-%b-%Y",       # 16-Feb-2026
            "%d-%B-%Y",       # 16-February-2026
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Try manual parsing for "Feb 16, 2026" format with variations
        try:
            parts = re.split(r'[\s,]+', date_str)
            if len(parts) >= 3:
                month_str = parts[0].lower()
                day_str = parts[1].strip(',')
                year_str = parts[2]
                
                if month_str in self.MONTH_MAP:
                    month = int(self.MONTH_MAP[month_str])
                    day = int(day_str)
                    year = int(year_str)
                    return datetime(year, month, day)
        except (ValueError, IndexError):
            pass
        
        return None
    
    def _extract_time(self, text: str) -> Optional[str]:
        """Extract transaction time"""
        if not self.time_pattern:
            return None
        
        match = self.time_pattern.search(text)
        if not match:
            return None
        
        return match.group(1) if match.lastindex else match.group(0)
    
    def _extract_merchant(self, text: str) -> Optional[str]:
        """Extract merchant/vendor name"""
        match = self.merchant_pattern.search(text)
        if not match:
            return None
        
        vendor = match.group(1) if match.lastindex else match.group(0)
        
        # Clean up vendor name
        vendor = vendor.strip()
        vendor = re.sub(r'\s+', ' ', vendor)  # Normalize whitespace
        
        return vendor
    
    def _extract_account_number(self, text: str) -> Optional[str]:
        """Extract last 4 digits of card/account"""
        if not self.account_pattern:
            return None
        
        match = self.account_pattern.search(text)
        if not match:
            return None
        
        return match.group(1) if match.lastindex else match.group(0)
    
    def _apply_category(self, result: ParsedTransaction, vendor: str):
        """Apply category based on vendor mapping"""
        db = SessionLocal()
        try:
            # Normalize vendor for matching
            vendor_upper = vendor.upper()
            
            # Try exact match first
            mapping = db.query(VendorMapping).filter(
                VendorMapping.vendor_keyword == vendor_upper
            ).first()
            
            # Try partial match
            if not mapping:
                mappings = db.query(VendorMapping).all()
                for m in mappings:
                    if m.vendor_keyword in vendor_upper or vendor_upper in m.vendor_keyword:
                        mapping = m
                        break
            
            if mapping:
                category = db.query(Category).filter(
                    Category.id == mapping.category_id
                ).first()
                
                if category:
                    result.category = category.name
                
                if mapping.subcategory_id:
                    from app.models import Subcategory
                    subcategory = db.query(Subcategory).filter(
                        Subcategory.id == mapping.subcategory_id
                    ).first()
                    if subcategory:
                        result.subcategory = subcategory.name
        finally:
            db.close()


class EmailParserService:
    """
    Service to manage email parsing across multiple accounts.
    """
    
    def __init__(self):
        self.parsers: Dict[str, EmailParser] = {}
        # Don't load parsers on init - tables might not exist yet
        # They will be loaded lazily on first use
    
    def _load_parsers(self):
        """Load all active account parsers"""
        db = SessionLocal()
        try:
            accounts = db.query(Account).filter(Account.is_active == True).all()
            for account in accounts:
                self.parsers[account.id] = EmailParser(account)
                print(f"Loaded parser for: {account.name}")
        except Exception as e:
            print(f"Warning: Could not load parsers (tables may not exist yet): {e}")
        finally:
            db.close()
    
    def reload_parsers(self):
        """Reload all parsers (call after account changes)"""
        self.parsers.clear()
        self._load_parsers()
    
    def get_parser(self, account_id: str) -> Optional[EmailParser]:
        """Get parser for a specific account"""
        return self.parsers.get(account_id)
    
    def find_matching_account(self, sender: str, subject: str) -> Optional[Account]:
        """
        Find account that matches the email sender and subject.
        Returns None if no match found.
        
        An account must have sender_email set to be matched.
        """
        db = SessionLocal()
        try:
            accounts = db.query(Account).filter(Account.is_active == True).all()
            
            for account in accounts:
                # Account must have sender_email configured to match
                if not account.sender_email:
                    continue
                
                # Check sender match
                if account.sender_email.lower() not in sender.lower():
                    continue
                
                # Check subject match (optional)
                if account.subject_pattern:
                    if account.subject_pattern.lower() not in subject.lower():
                        continue
                
                return account
            
            return None
        finally:
            db.close()
    
    def parse_email(
        self, 
        sender: str, 
        subject: str, 
        body: str
    ) -> Optional[tuple[Account, ParsedTransaction]]:
        """
        Parse an email and return the matched account and parsed transaction.
        Returns None if no matching account or parsing fails.
        """
        # Find matching account
        account = self.find_matching_account(sender, subject)
        if not account:
            print(f"No matching account for sender: {sender}, subject: {subject}")
            return None
        
        # Get or create parser
        parser = self.parsers.get(account.id)
        if not parser:
            parser = EmailParser(account)
            self.parsers[account.id] = parser
        
        # Parse email
        result = parser.parse(body)
        if not result:
            print(f"Failed to parse email with account: {account.name}")
            return None
        
        return (account, result)
    
    def create_transaction_from_parsed(
        self, 
        account: Account, 
        parsed: ParsedTransaction,
        source_email_id: str
    ) -> Transaction:
        """
        Create a Transaction model from parsed result.
        """
        # Build account name
        account_name = account.name
        if parsed.account_number:
            account_name = f"{account.name} XX{parsed.account_number}"
        
        return Transaction(
            source_email_id=source_email_id,
            ledger="",
            category_name=parsed.category,
            subcategory=parsed.subcategory,
            currency=parsed.currency,
            parsed_amount=parsed.amount,
            account_name=account_name,
            account_id=account.id,
            recorder="Auto",
            parsed_date=parsed.date,
            parsed_time=parsed.time,
            parsed_vendor=parsed.vendor,
            transaction_type=parsed.transaction_type,
            status="pending",
            confidence_score=parsed.confidence_score
        )


# Singleton instance
email_parser_service = EmailParserService()
