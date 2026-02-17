"""
Tests for Email Parser Service
"""
from datetime import datetime

from app.services.email_parser import EmailParser, ParsedTransaction
from app.models import Account


# Sample ICICI email
ICICI_EMAIL = """
Dear Customer,

Your ICICI Bank Credit Card XX0001 has been used for a transaction of INR 240.00 on Feb 16, 2026 at 10:31:46. Info: TWINS TOWER CASH.

The Available Credit Limit on your card is INR 94,678.14 and Total Credit Limit is INR 1,30,000.00. The above limits are a total of the limits of all the Credit Cards issued to the primary card holder, including any supplementary cards.

This is an auto-generated e-mail. Please do not reply.
"""

# Sample HDFC email
HDFC_EMAIL = """
Dear Customer,

INR 1,234.56 has been debited from your HDFC Bank Credit Card ending 5678 on 15-02-2026 at AMAZON PAY INDIA.

Available Limit: INR 50,000.00
"""

# Sample SBI email
SBI_EMAIL = """
Dear Customer,

Your SBI Credit Card ending with 9012 has been used for INR 599.00 at NETFLIX INDIA on 2026-02-14.

Thank you for using SBI Card.
"""


def create_icici_account():
    """Create a test ICICI account configuration"""
    return Account(
        id="test-icici-001",
        name="ICICI Bank Credit Card",
        sender_email="credit_cards@icicibank.com",
        subject_pattern="Transaction alert",
        amount_regex=r"INR\s*([\d,]+\.\d{2})",
        date_regex=r"(\w{3}\s+\d{1,2},\s+\d{4})",
        merchant_regex=r"Info:\s*(.+?)\.",
        time_regex=r"(\d{2}:\d{2}:\d{2})",
        account_regex=r"XX(\d{4})",
        currency_default="INR",
        default_transaction_type="Expense"
    )


def create_hdfc_account():
    """Create a test HDFC account configuration"""
    return Account(
        id="test-hdfc-001",
        name="HDFC Bank Credit Card",
        sender_email="alerts@hdfcbank.net",
        subject_pattern="Transaction Alert",
        amount_regex=r"INR\s*([\d,]+\.\d{2})",
        date_regex=r"(\d{2}-\d{2}-\d{4})",
        merchant_regex=r"at\s+(.+?)(?:\.|$)",
        time_regex=None,
        account_regex=r"ending\s+(\d{4})",
        currency_default="INR",
        default_transaction_type="Expense"
    )


def create_sbi_account():
    """Create a test SBI account configuration"""
    return Account(
        id="test-sbi-001",
        name="SBI Credit Card",
        sender_email="alerts@sbicard.com",
        subject_pattern="Transaction",
        amount_regex=r"INR\s*([\d,]+\.\d{2})",
        date_regex=r"(\d{4}-\d{2}-\d{2})",
        merchant_regex=r"at\s+(.+?)\s+on",
        time_regex=None,
        account_regex=r"ending with\s+(\d{4})",
        currency_default="INR",
        default_transaction_type="Expense"
    )


class TestEmailParser:
    """Test cases for EmailParser"""
    
    def test_parse_icici_email(self):
        """Test parsing ICICI transaction email"""
        account = create_icici_account()
        parser = EmailParser(account)
        
        result = parser.parse(ICICI_EMAIL)
        
        assert result is not None
        assert result.amount == 240.00
        assert result.vendor == "TWINS TOWER CASH"
        assert result.time == "10:31:46"
        assert result.account_number == "0001"
        assert result.currency == "INR"
        assert result.transaction_type == "Expense"
        
        # Check date parsing
        assert result.date is not None
        assert result.date.year == 2026
        assert result.date.month == 2
        assert result.date.day == 16
    
    def test_parse_hdfc_email(self):
        """Test parsing HDFC transaction email"""
        account = create_hdfc_account()
        parser = EmailParser(account)
        
        result = parser.parse(HDFC_EMAIL)
        
        assert result is not None
        assert result.amount == 1234.56
        assert "AMAZON" in result.vendor.upper()
        assert result.account_number == "5678"
        
        # Check date parsing (DD-MM-YYYY format)
        assert result.date is not None
        assert result.date.year == 2026
        assert result.date.month == 2
        assert result.date.day == 15
    
    def test_parse_sbi_email(self):
        """Test parsing SBI transaction email"""
        account = create_sbi_account()
        parser = EmailParser(account)
        
        result = parser.parse(SBI_EMAIL)
        
        assert result is not None
        assert result.amount == 599.00
        assert "NETFLIX" in result.vendor.upper()
        assert result.account_number == "9012"
        
        # Check date parsing (YYYY-MM-DD format)
        assert result.date is not None
        assert result.date.year == 2026
        assert result.date.month == 2
        assert result.date.day == 14
    
    def test_parse_invalid_email(self):
        """Test parsing email with no transaction data"""
        account = create_icici_account()
        parser = EmailParser(account)
        
        result = parser.parse("This is a random email with no transaction data.")
        
        assert result is None
    
    def test_parse_amount_with_commas(self):
        """Test parsing amounts with comma separators"""
        email_body = """
        Your card has been used for a transaction of INR 12,345.67 on Feb 10, 2026 at 14:30:00. Info: BIG PURCHASE.
        """
        
        account = create_icici_account()
        parser = EmailParser(account)
        
        result = parser.parse(email_body)
        
        assert result is not None
        assert result.amount == 12345.67
    
    def test_date_normalization_various_formats(self):
        """Test date normalization for various formats"""
        parser = EmailParser(create_icici_account())
        
        # Test "Feb 16, 2026" format
        date1 = parser._normalize_date("Feb 16, 2026")
        assert date1 is not None
        assert date1.month == 2
        assert date1.day == 16
        assert date1.year == 2026
        
        # Test "16-02-2026" format
        date2 = parser._normalize_date("16-02-2026")
        assert date2 is not None
        assert date2.day == 16
        assert date2.month == 2
        
        # Test "2026-02-16" format
        date3 = parser._normalize_date("2026-02-16")
        assert date3 is not None
        assert date3.year == 2026
        assert date3.month == 2
        assert date3.day == 16


class TestParserEdgeCases:
    """Test edge cases for parser"""
    
    def test_empty_email(self):
        """Test with empty email body"""
        parser = EmailParser(create_icici_account())
        result = parser.parse("")
        assert result is None
    
    def test_partial_match(self):
        """Test email with only some fields matching"""
        email_body = "Transaction of INR 100.00 on unknown date."
        
        parser = EmailParser(create_icici_account())
        result = parser.parse(email_body)
        
        # Should fail because date pattern doesn't match
        assert result is None
    
    def test_vendor_with_special_characters(self):
        """Test vendor name with special characters"""
        email_body = """
        Transaction of INR 50.00 on Feb 1, 2026 at 09:00:00. Info: CAFE & BAKERY (MAIN ST).
        """
        
        account = create_icici_account()
        # Adjust regex to capture more characters
        account.merchant_regex = r"Info:\s*(.+?)(?:\.|$)"
        parser = EmailParser(account)
        
        result = parser.parse(email_body)
        
        assert result is not None
        assert "CAFE" in result.vendor


def run_tests():
    """Run all tests and print results"""
    print("=" * 60)
    print("RUNNING EMAIL PARSER TESTS")
    print("=" * 60)
    
    test_classes = [TestEmailParser, TestParserEdgeCases]
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        instance = test_class()
        methods = [m for m in dir(instance) if m.startswith("test_")]
        
        for method_name in methods:
            total_tests += 1
            method = getattr(instance, method_name)
            
            try:
                method()
                passed_tests += 1
                print(f"✓ {test_class.__name__}.{method_name}")
            except AssertionError as e:
                failed_tests.append(f"{test_class.__name__}.{method_name}: {e}")
                print(f"✗ {test_class.__name__}.{method_name}: {e}")
            except Exception as e:
                failed_tests.append(f"{test_class.__name__}.{method_name}: {e}")
                print(f"✗ {test_class.__name__}.{method_name}: ERROR - {e}")
    
    print("=" * 60)
    print(f"RESULTS: {passed_tests}/{total_tests} tests passed")
    
    if failed_tests:
        print("\nFAILED TESTS:")
        for failure in failed_tests:
            print(f"  - {failure}")
    
    print("=" * 60)
    
    return len(failed_tests) == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
