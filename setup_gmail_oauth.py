#!/usr/bin/env python3
"""
Gmail OAuth 2.0 Setup Script for SpendWise

This script guides you through setting up Gmail OAuth 2.0 authentication,
which is required for Google Workspace accounts since May 2025.

Usage:
    python setup_gmail_oauth.py
"""

import subprocess
import sys
from pathlib import Path


def check_dependencies():
    """Check if required Google libraries are installed"""
    try:
        import google.auth
        import google_auth_oauthlib
        import googleapiclient
        return True
    except ImportError:
        return False


def install_dependencies():
    """Install required Google OAuth libraries"""
    print("\nInstalling Google OAuth libraries...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install",
        "google-auth>=2.27.0",
        "google-auth-oauthlib>=1.2.0",
        "google-auth-httplib2>=0.2.0",
        "google-api-python-client>=2.118.0"
    ])
    print("Libraries installed successfully!")


def main():
    print("=" * 60)
    print("SpendWise - Gmail OAuth 2.0 Setup")
    print("=" * 60)
    print()
    print("Starting May 2025, Google Workspace accounts require OAuth 2.0")
    print("for IMAP access. App passwords are no longer supported.")
    print()
    
    # Step 1: Check/Install dependencies
    print("Step 1: Checking dependencies...")
    if not check_dependencies():
        print("Google OAuth libraries not found.")
        response = input("Install them now? (y/n): ").strip().lower()
        if response == 'y':
            install_dependencies()
        else:
            print("\nPlease install manually:")
            print("  pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
            sys.exit(1)
    else:
        print("Google OAuth libraries are installed.")
    
    print()
    
    # Step 2: Check for credentials file
    print("Step 2: Checking OAuth credentials...")
    credentials_dir = Path(__file__).parent / "credentials"
    credentials_file = credentials_dir / "google_oauth_credentials.json"
    
    credentials_dir.mkdir(exist_ok=True)
    
    if not credentials_file.exists():
        print()
        print("OAuth credentials file not found!")
        print()
        print("Please follow these steps to create credentials:")
        print()
        print("  1. Go to: https://console.cloud.google.com/")
        print("  2. Create a new project (or select existing)")
        print("  3. Enable Gmail API:")
        print("     - Go to: APIs & Services > Library")
        print("     - Search for 'Gmail API'")
        print("     - Click 'Enable'")
        print("  4. Create OAuth credentials:")
        print("     - Go to: APIs & Services > Credentials")
        print("     - Click 'Create Credentials' > 'OAuth client ID'")
        print("     - Application type: 'Desktop app'")
        print("     - Name: 'SpendWise'")
        print("     - Click 'Create'")
        print("  5. Download the JSON file")
        print(f"  6. Save it to: {credentials_file}")
        print()
        print("Press Enter when you've completed these steps...")
        input()
        
        if not credentials_file.exists():
            print(f"Credentials file still not found at: {credentials_file}")
            print("Please complete the setup and run this script again.")
            sys.exit(1)
    
    print(f"Found credentials file: {credentials_file}")
    print()
    
    # Step 3: Run OAuth flow
    print("Step 3: Authenticating with Google...")
    print("A browser window will open for Google sign-in.")
    print()
    
    from app.services.gmail_oauth import setup_gmail_oauth
    success = setup_gmail_oauth()
    
    if success:
        print()
        print("=" * 60)
        print("Setup Complete!")
        print("=" * 60)
        print()
        print("Next steps:")
        print()
        print("1. Update your .env file:")
        print("   EMAIL_CLIENT_TYPE=gmail_oauth")
        print()
        print("2. Restart the backend:")
        print("   uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload")
        print()
        print("3. Start email monitoring:")
        print("   curl -X POST http://127.0.0.1:8001/email/monitor/start")
        print()
    else:
        print()
        print("Setup failed. Please check the error messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
