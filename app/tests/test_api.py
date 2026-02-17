"""
API Integration Tests
Tests all API endpoints
"""
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:8001"


def print_result(test_name: str, success: bool, details: str = ""):
    """Print test result"""
    status = "✓" if success else "✗"
    print(f"{status} {test_name}")
    if details and not success:
        print(f"  Details: {details}")


class APITester:
    """API Test Suite"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.created_ids = {
            "accounts": [],
            "transactions": [],
            "categories": [],
        }
    
    def test_health(self) -> bool:
        """Test health endpoint"""
        try:
            r = requests.get(f"{self.base_url}/health", timeout=5)
            success = r.status_code == 200 and r.json().get("status") == "healthy"
            print_result("Health Check", success, r.text)
            return success
        except Exception as e:
            print_result("Health Check", False, str(e))
            return False
    
    # ==================== ACCOUNT TESTS ====================
    
    def test_create_account(self) -> bool:
        """Test creating an account"""
        try:
            account_data = {
                "id": "test-account-001",
                "name": "Test ICICI Card",
                "card_last_four": "1234",
                "sender_email": "credit_cards@icicibank.com",
                "subject_pattern": "Transaction alert",
                "amount_regex": r"INR\s*([\d,]+\.\d{2})",
                "date_regex": r"(\w{3}\s+\d{1,2},\s+\d{4})",
                "merchant_regex": r"Info:\s*(.+?)\.",
                "time_regex": r"(\d{2}:\d{2}:\d{2})",
                "account_regex": r"XX(\d{4})",
                "sample_email_body": "Your ICICI Bank Credit Card XX1234 has been used for a transaction of INR 240.00 on Feb 16, 2026 at 10:31:46. Info: TEST MERCHANT.",
                "is_active": True,
                "currency_default": "INR",
                "default_transaction_type": "Expense"
            }
            
            r = requests.post(f"{self.base_url}/accounts/", json=account_data)
            success = r.status_code == 200 or r.status_code == 201
            
            if success:
                self.created_ids["accounts"].append(account_data["id"])
            
            print_result("Create Account", success, r.text if not success else "")
            return success
        except Exception as e:
            print_result("Create Account", False, str(e))
            return False
    
    def test_list_accounts(self) -> bool:
        """Test listing accounts"""
        try:
            r = requests.get(f"{self.base_url}/accounts/")
            success = r.status_code == 200 and isinstance(r.json(), list)
            print_result("List Accounts", success, r.text if not success else f"Found {len(r.json())} accounts")
            return success
        except Exception as e:
            print_result("List Accounts", False, str(e))
            return False
    
    def test_get_account(self) -> bool:
        """Test getting a single account"""
        if not self.created_ids["accounts"]:
            print_result("Get Account", False, "No account created")
            return False
        
        try:
            account_id = self.created_ids["accounts"][0]
            r = requests.get(f"{self.base_url}/accounts/{account_id}")
            success = r.status_code == 200 and r.json().get("id") == account_id
            print_result("Get Account", success, r.text if not success else "")
            return success
        except Exception as e:
            print_result("Get Account", False, str(e))
            return False
    
    def test_update_account(self) -> bool:
        """Test updating an account"""
        if not self.created_ids["accounts"]:
            print_result("Update Account", False, "No account created")
            return False
        
        try:
            account_id = self.created_ids["accounts"][0]
            update_data = {
                "name": "Test ICICI Card Updated",
                "is_active": True
            }
            
            r = requests.put(f"{self.base_url}/accounts/{account_id}", json=update_data)
            success = r.status_code == 200 and "Updated" in r.json().get("name", "")
            print_result("Update Account", success, r.text if not success else "")
            return success
        except Exception as e:
            print_result("Update Account", False, str(e))
            return False
    
    # ==================== TRANSACTION TESTS ====================
    
    def test_create_transaction(self) -> bool:
        """Test creating a transaction"""
        try:
            txn_data = {
                "ledger": "Personal",
                "category_name": "Food & Dining",
                "subcategory": "Restaurants",
                "currency": "INR",
                "parsed_amount": 500.00,
                "account_name": "Test Account",
                "recorder": "API Test",
                "parsed_date": datetime.now().isoformat(),
                "parsed_time": "12:30:00",
                "parsed_vendor": "Test Restaurant",
                "transaction_type": "Expense"
            }
            
            r = requests.post(f"{self.base_url}/transactions/", json=txn_data)
            success = r.status_code == 200 or r.status_code == 201
            
            if success:
                txn_id = r.json().get("id")
                if txn_id:
                    self.created_ids["transactions"].append(txn_id)
            
            print_result("Create Transaction", success, r.text if not success else f"ID: {r.json().get('id')}")
            return success
        except Exception as e:
            print_result("Create Transaction", False, str(e))
            return False
    
    def test_list_transactions(self) -> bool:
        """Test listing transactions"""
        try:
            r = requests.get(f"{self.base_url}/transactions/", params={"days": 30})
            success = r.status_code == 200 and isinstance(r.json(), list)
            print_result("List Transactions", success, f"Found {len(r.json())} transactions" if success else r.text)
            return success
        except Exception as e:
            print_result("List Transactions", False, str(e))
            return False
    
    def test_get_transaction(self) -> bool:
        """Test getting a single transaction"""
        if not self.created_ids["transactions"]:
            print_result("Get Transaction", False, "No transaction created")
            return False
        
        try:
            txn_id = self.created_ids["transactions"][0]
            r = requests.get(f"{self.base_url}/transactions/{txn_id}")
            success = r.status_code == 200 and r.json().get("id") == txn_id
            print_result("Get Transaction", success, r.text if not success else "")
            return success
        except Exception as e:
            print_result("Get Transaction", False, str(e))
            return False
    
    def test_update_transaction(self) -> bool:
        """Test updating a transaction"""
        if not self.created_ids["transactions"]:
            print_result("Update Transaction", False, "No transaction created")
            return False
        
        try:
            txn_id = self.created_ids["transactions"][0]
            update_data = {
                "parsed_vendor": "Updated Restaurant",
                "parsed_amount": 600.00,
                "status": "confirmed"
            }
            
            r = requests.put(f"{self.base_url}/transactions/{txn_id}", json=update_data)
            success = r.status_code == 200 and r.json().get("parsed_vendor") == "Updated Restaurant"
            print_result("Update Transaction", success, r.text if not success else "")
            return success
        except Exception as e:
            print_result("Update Transaction", False, str(e))
            return False
    
    def test_export_transactions_csv(self) -> bool:
        """Test CSV export"""
        try:
            r = requests.get(f"{self.base_url}/transactions/export/csv", params={"days": 365})
            success = r.status_code == 200 and "text/csv" in r.headers.get("content-type", "")
            print_result("Export CSV", success, f"Content-Type: {r.headers.get('content-type')}" if not success else "")
            return success
        except Exception as e:
            print_result("Export CSV", False, str(e))
            return False
    
    # ==================== CATEGORY TESTS ====================
    
    def test_list_categories(self) -> bool:
        """Test listing categories"""
        try:
            r = requests.get(f"{self.base_url}/categories/")
            success = r.status_code == 200 and isinstance(r.json(), list)
            print_result("List Categories", success, f"Found {len(r.json())} categories" if success else r.text)
            return success
        except Exception as e:
            print_result("List Categories", False, str(e))
            return False
    
    def test_create_category(self) -> bool:
        """Test creating a category"""
        try:
            import random
            cat_data = {
                "name": f"Test Category {random.randint(1000, 9999)}",
                "icon": "🧪",
                "color": "#FF0000"
            }
            
            r = requests.post(f"{self.base_url}/categories/", json=cat_data)
            success = r.status_code == 200 or r.status_code == 201
            
            if success:
                cat_id = r.json().get("id")
                if cat_id:
                    self.created_ids["categories"].append(cat_id)
            
            print_result("Create Category", success, r.text if not success else "")
            return success
        except Exception as e:
            print_result("Create Category", False, str(e))
            return False
    
    def test_list_vendor_mappings(self) -> bool:
        """Test listing vendor mappings"""
        try:
            r = requests.get(f"{self.base_url}/categories/mappings")
            success = r.status_code == 200 and isinstance(r.json(), list)
            print_result("List Vendor Mappings", success, f"Found {len(r.json())} mappings" if success else r.text)
            return success
        except Exception as e:
            print_result("List Vendor Mappings", False, str(e))
            return False
    
    # ==================== DEVICE TESTS ====================
    
    def test_register_device(self) -> bool:
        """Test device registration"""
        try:
            device_data = {
                "device_token": "test-push-token-123",
                "environment": "sandbox",
                "device_name": "Test iPhone",
                "os_version": "17.0"
            }
            
            r = requests.post(f"{self.base_url}/devices/register", json=device_data)
            success = r.status_code == 200 or r.status_code == 201
            print_result("Register Device", success, r.text if not success else "")
            return success
        except Exception as e:
            print_result("Register Device", False, str(e))
            return False
    
    # ==================== EMAIL PARSER TESTS ====================
    
    def test_email_parse(self) -> bool:
        """Test email parsing endpoint"""
        try:
            parse_data = {
                "sender": "credit_cards@icicibank.com",
                "subject": "Transaction alert",
                "body": "Your ICICI Bank Credit Card XX1234 has been used for a transaction of INR 240.00 on Feb 16, 2026 at 10:31:46. Info: TEST MERCHANT.",
                "create_transaction": False
            }
            
            r = requests.post(f"{self.base_url}/email/parse", json=parse_data)
            success = r.status_code == 200
            
            if success:
                result = r.json()
                success = result.get("success") == True or result.get("amount") is not None
            
            print_result("Email Parse", success, json.dumps(r.json(), indent=2) if success else r.text)
            return success
        except Exception as e:
            print_result("Email Parse", False, str(e))
            return False
    
    def test_email_test_parser(self) -> bool:
        """Test parser testing endpoint"""
        if not self.created_ids["accounts"]:
            print_result("Test Parser", False, "No account created")
            return False
        
        try:
            account_id = self.created_ids["accounts"][0]
            test_data = {
                "account_id": account_id,
                "email_body": "Your ICICI Bank Credit Card XX1234 has been used for a transaction of INR 500.00 on Feb 20, 2026 at 14:30:00. Info: ANOTHER MERCHANT."
            }
            
            r = requests.post(f"{self.base_url}/email/test-parser", json=test_data)
            success = r.status_code == 200
            
            if success:
                result = r.json()
                success = result.get("success") == True and result.get("amount") == 500.00
            
            print_result("Test Parser", success, json.dumps(r.json(), indent=2) if success else r.text)
            return success
        except Exception as e:
            print_result("Test Parser", False, str(e))
            return False
    
    def test_email_monitor_status(self) -> bool:
        """Test email monitor status"""
        try:
            r = requests.get(f"{self.base_url}/email/monitor/status")
            success = r.status_code == 200 and "is_running" in r.json()
            print_result("Monitor Status", success, r.text if not success else "")
            return success
        except Exception as e:
            print_result("Monitor Status", False, str(e))
            return False
    
    def test_reload_parsers(self) -> bool:
        """Test reloading parsers"""
        try:
            r = requests.post(f"{self.base_url}/email/reload-parsers")
            success = r.status_code == 200
            print_result("Reload Parsers", success, r.text if not success else "")
            return success
        except Exception as e:
            print_result("Reload Parsers", False, str(e))
            return False
    
    # ==================== CLEANUP TESTS ====================
    
    def test_delete_transaction(self) -> bool:
        """Test deleting a transaction"""
        if not self.created_ids["transactions"]:
            print_result("Delete Transaction", True, "No transaction to delete")
            return True
        
        try:
            txn_id = self.created_ids["transactions"][0]
            r = requests.delete(f"{self.base_url}/transactions/{txn_id}")
            success = r.status_code == 200 or r.status_code == 204
            print_result("Delete Transaction", success, r.text if not success else "")
            return success
        except Exception as e:
            print_result("Delete Transaction", False, str(e))
            return False
    
    def test_delete_account(self) -> bool:
        """Test deleting an account"""
        if not self.created_ids["accounts"]:
            print_result("Delete Account", True, "No account to delete")
            return True
        
        try:
            account_id = self.created_ids["accounts"][0]
            r = requests.delete(f"{self.base_url}/accounts/{account_id}")
            success = r.status_code == 200 or r.status_code == 204
            print_result("Delete Account", success, r.text if not success else "")
            return success
        except Exception as e:
            print_result("Delete Account", False, str(e))
            return False
    
    def run_all_tests(self) -> dict:
        """Run all tests and return summary"""
        print("=" * 60)
        print("RUNNING API TESTS")
        print(f"Base URL: {self.base_url}")
        print("=" * 60)
        
        tests = [
            # Health
            ("Health Check", self.test_health),
            
            # Accounts
            ("Create Account", self.test_create_account),
            ("List Accounts", self.test_list_accounts),
            ("Get Account", self.test_get_account),
            ("Update Account", self.test_update_account),
            
            # Transactions
            ("Create Transaction", self.test_create_transaction),
            ("List Transactions", self.test_list_transactions),
            ("Get Transaction", self.test_get_transaction),
            ("Update Transaction", self.test_update_transaction),
            ("Export CSV", self.test_export_transactions_csv),
            
            # Categories
            ("List Categories", self.test_list_categories),
            ("Create Category", self.test_create_category),
            ("List Vendor Mappings", self.test_list_vendor_mappings),
            
            # Devices
            ("Register Device", self.test_register_device),
            
            # Email Parser
            ("Email Parse", self.test_email_parse),
            ("Test Parser", self.test_email_test_parser),
            ("Monitor Status", self.test_email_monitor_status),
            ("Reload Parsers", self.test_reload_parsers),
            
            # Cleanup
            ("Delete Transaction", self.test_delete_transaction),
            ("Delete Account", self.test_delete_account),
        ]
        
        results = {
            "total": len(tests),
            "passed": 0,
            "failed": 0,
            "failures": []
        }
        
        print("\n--- Running Tests ---\n")
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                    results["failures"].append(test_name)
            except Exception as e:
                results["failed"] += 1
                results["failures"].append(f"{test_name}: {e}")
                print_result(test_name, False, str(e))
        
        print("\n" + "=" * 60)
        print(f"RESULTS: {results['passed']}/{results['total']} tests passed")
        
        if results["failures"]:
            print("\nFAILED TESTS:")
            for failure in results["failures"]:
                print(f"  - {failure}")
        
        print("=" * 60)
        
        return results


def main():
    """Run API tests"""
    tester = APITester()
    results = tester.run_all_tests()
    
    exit_code = 0 if results["failed"] == 0 else 1
    exit(exit_code)


if __name__ == "__main__":
    main()
