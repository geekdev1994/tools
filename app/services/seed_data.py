"""
Seed default data - categories and vendor mappings
"""
from app.core.database import SessionLocal
from app.models import Category, Subcategory, VendorMapping

# Default categories with subcategories
DEFAULT_CATEGORIES = {
    "Food & Dining": {
        "icon": "🍽️",
        "color": "#FF6B6B",
        "subcategories": ["Restaurants", "Fast Food", "Groceries", "Coffee", "Food Delivery", "Alcohol & Bars"]
    },
    "Transportation": {
        "icon": "🚗",
        "color": "#4ECDC4",
        "subcategories": ["Fuel", "Public Transit", "Taxi/Cab", "Parking", "Flight", "Train", "Auto/Maintenance"]
    },
    "Shopping": {
        "icon": "🛍️",
        "color": "#45B7D1",
        "subcategories": ["Clothing", "Electronics", "Home & Garden", "Online Shopping", "Personal Care"]
    },
    "Entertainment": {
        "icon": "🎬",
        "color": "#96CEB4",
        "subcategories": ["Movies", "Games", "Streaming", "Events", "Hobbies"]
    },
    "Bills & Utilities": {
        "icon": "💡",
        "color": "#DDA0DD",
        "subcategories": ["Electricity", "Water", "Gas", "Internet", "Phone", "Insurance"]
    },
    "Health & Fitness": {
        "icon": "💪",
        "color": "#98D8C8",
        "subcategories": ["Gym", "Medical", "Pharmacy", "Sports", "Wellness"]
    },
    "Travel": {
        "icon": "✈️",
        "color": "#F7DC6F",
        "subcategories": ["Hotels", "Flights", "Vacation", "Visa/Passport"]
    },
    "Education": {
        "icon": "📚",
        "color": "#BB8FCE",
        "subcategories": ["Courses", "Books", "Tuition", "Supplies"]
    },
    "Personal Care": {
        "icon": "💇",
        "color": "#F8B500",
        "subcategories": ["Haircut", "Spa", "Cosmetics"]
    },
    "Income": {
        "icon": "💰",
        "color": "#2ECC71",
        "subcategories": ["Salary", "Refund", "Interest", "Dividend", "Other Income"]
    },
    "Transfer": {
        "icon": "🔄",
        "color": "#3498DB",
        "subcategories": ["Bank Transfer", "Credit Card Payment", "Investment"]
    },
    "Others": {
        "icon": "📦",
        "color": "#BDC3C7",
        "subcategories": ["Miscellaneous", "ATM Withdrawal", "Cash"]
    }
}

# Default vendor to category mappings
DEFAULT_VENDOR_MAPPINGS = {
    # Food & Dining
    "ZOMATO": {"category": "Food & Dining", "subcategory": "Food Delivery"},
    "SWIGGY": {"category": "Food & Dining", "subcategory": "Food Delivery"},
    "DOMINOS": {"category": "Food & Dining", "subcategory": "Fast Food"},
    "MCDONALDS": {"category": "Food & Dining", "subcategory": "Fast Food"},
    "STARBUCKS": {"category": "Food & Dining", "subcategory": "Coffee"},
    "CAFE COFFEE DAY": {"category": "Food & Dining", "subcategory": "Coffee"},
    "TWINS TOWER": {"category": "Food & Dining", "subcategory": "Restaurants"},
    
    # Transportation
    "UBER": {"category": "Transportation", "subcategory": "Taxi/Cab"},
    "OLA": {"category": "Transportation", "subcategory": "Taxi/Cab"},
    "INDIAN OIL": {"category": "Transportation", "subcategory": "Fuel"},
    "HP PETROL": {"category": "Transportation", "subcategory": "Fuel"},
    "BHARAT PETROLEUM": {"category": "Transportation", "subcategory": "Fuel"},
    "IRCTC": {"category": "Transportation", "subcategory": "Train"},
    
    # Shopping
    "AMAZON": {"category": "Shopping", "subcategory": "Online Shopping"},
    "FLIPKART": {"category": "Shopping", "subcategory": "Online Shopping"},
    "MYNTRA": {"category": "Shopping", "subcategory": "Clothing"},
    "DMART": {"category": "Shopping", "subcategory": "Groceries"},
    "BIG BAZAAR": {"category": "Shopping", "subcategory": "Groceries"},
    
    # Entertainment
    "NETFLIX": {"category": "Entertainment", "subcategory": "Streaming"},
    "PRIME VIDEO": {"category": "Entertainment", "subcategory": "Streaming"},
    "HOTSTAR": {"category": "Entertainment", "subcategory": "Streaming"},
    "PVR": {"category": "Entertainment", "subcategory": "Movies"},
    "INOX": {"category": "Entertainment", "subcategory": "Movies"},
    
    # Bills & Utilities
    "AIRTEL": {"category": "Bills & Utilities", "subcategory": "Phone"},
    "JIO": {"category": "Bills & Utilities", "subcategory": "Phone"},
    "VODAFONE": {"category": "Bills & Utilities", "subcategory": "Phone"},
    "TATA POWER": {"category": "Bills & Utilities", "subcategory": "Electricity"},
    "BSES": {"category": "Bills & Utilities", "subcategory": "Electricity"},
    
    # Cloud Services
    "GOOGLE CLOUD": {"category": "Bills & Utilities", "subcategory": "Internet"},
    "AWS": {"category": "Bills & Utilities", "subcategory": "Internet"},
    "AZURE": {"category": "Bills & Utilities", "subcategory": "Internet"},
}


def seed_default_categories():
    """Seed default categories and vendor mappings if not exist"""
    db = SessionLocal()
    try:
        # Check if categories already exist
        existing_count = db.query(Category).count()
        if existing_count > 0:
            print(f"Categories already exist ({existing_count}), skipping seed")
            return
        
        print("Seeding default categories...")
        
        # Create categories and subcategories
        category_map = {}
        for cat_name, cat_data in DEFAULT_CATEGORIES.items():
            category = Category(
                name=cat_name,
                icon=cat_data.get("icon"),
                color=cat_data.get("color"),
                is_system=True
            )
            db.add(category)
            db.flush()  # Get the ID
            category_map[cat_name] = {"id": category.id, "subcategories": {}}
            
            # Create subcategories
            for sub_name in cat_data.get("subcategories", []):
                subcategory = Subcategory(
                    category_id=category.id,
                    name=sub_name
                )
                db.add(subcategory)
                db.flush()
                category_map[cat_name]["subcategories"][sub_name] = subcategory.id
        
        print(f"Created {len(category_map)} categories")
        
        # Create vendor mappings
        for vendor, mapping_data in DEFAULT_VENDOR_MAPPINGS.items():
            cat_name = mapping_data["category"]
            sub_name = mapping_data.get("subcategory")
            
            if cat_name not in category_map:
                continue
            
            cat_id = category_map[cat_name]["id"]
            sub_id = category_map[cat_name]["subcategories"].get(sub_name)
            
            mapping = VendorMapping(
                vendor_keyword=vendor,
                category_id=cat_id,
                subcategory_id=sub_id,
                is_user_defined=False
            )
            db.add(mapping)
        
        db.commit()
        print(f"Seeded {len(DEFAULT_VENDOR_MAPPINGS)} vendor mappings")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
    finally:
        db.close()
