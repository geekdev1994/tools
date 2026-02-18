"""
Gmail OAuth 2.0 Authentication Service

Setup Instructions:
1. Go to Google Cloud Console: https://console.cloud.google.com/
2. Create a new project (or select existing)
3. Enable Gmail API: APIs & Services > Library > Search "Gmail API" > Enable
4. Create OAuth 2.0 credentials:
   - APIs & Services > Credentials > Create Credentials > OAuth client ID
   - Application type: Desktop app (or Web application)
   - Download the JSON file
5. Place the JSON file at: credentials/google_oauth_credentials.json
6. Run the authorization flow once to generate tokens

Usage:
    from app.services.gmail_oauth import GmailOAuthClient
    
    client = GmailOAuthClient()
    if client.authenticate():
        messages = client.fetch_recent_emails(hours=24)
"""

import os
import json
import base64
import pickle
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List
from dataclasses import dataclass
from io import BytesIO

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False
    print("Google OAuth libraries not installed. Run: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")


# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Paths (for local development)
CREDENTIALS_DIR = Path(__file__).parent.parent.parent / "credentials"
CREDENTIALS_FILE = CREDENTIALS_DIR / "google_oauth_credentials.json"
TOKEN_FILE = CREDENTIALS_DIR / "google_oauth_token.pickle"

# Environment variable names (for Railway/production)
GOOGLE_OAUTH_CREDENTIALS_ENV = "GOOGLE_OAUTH_CREDENTIALS"  # Base64 encoded JSON
GOOGLE_OAUTH_TOKEN_ENV = "GOOGLE_OAUTH_TOKEN"  # Base64 encoded pickle


@dataclass
class GmailMessage:
    """Represents a Gmail message"""
    message_id: str
    thread_id: str
    sender: str
    subject: str
    body: str
    date: datetime
    labels: List[str]


class GmailOAuthClient:
    """
    Gmail client using OAuth 2.0 authentication.
    
    This replaces the IMAP client for Gmail accounts since Google
    deprecated app passwords for Workspace accounts (May 2025).
    
    Supports two modes:
    1. Local: Reads from credentials/ directory
    2. Production: Reads from environment variables (base64 encoded)
    """
    
    def __init__(self, credentials_file: str = None):
        self.credentials_file = Path(credentials_file) if credentials_file else CREDENTIALS_FILE
        self.token_file = TOKEN_FILE
        self.credentials: Optional[Credentials] = None
        self.service = None
        self._using_env_credentials = False
        
        # Check if using environment variables (Railway/production)
        if os.environ.get(GOOGLE_OAUTH_CREDENTIALS_ENV):
            self._using_env_credentials = True
            self._setup_from_env()
        else:
            # Ensure credentials directory exists for local dev
            CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    
    def _setup_from_env(self):
        """Setup credentials from environment variables"""
        try:
            # Decode and write credentials JSON to temp file location
            creds_b64 = os.environ.get(GOOGLE_OAUTH_CREDENTIALS_ENV, "")
            if creds_b64:
                CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
                creds_json = base64.b64decode(creds_b64).decode('utf-8')
                with open(CREDENTIALS_FILE, 'w') as f:
                    f.write(creds_json)
                print("Gmail OAuth: Loaded credentials from environment")
            
            # Decode and write token pickle
            token_b64 = os.environ.get(GOOGLE_OAUTH_TOKEN_ENV, "")
            if token_b64:
                token_bytes = base64.b64decode(token_b64)
                with open(TOKEN_FILE, 'wb') as f:
                    f.write(token_bytes)
                print("Gmail OAuth: Loaded token from environment")
                
        except Exception as e:
            print(f"Gmail OAuth: Error loading from environment: {e}")
    
    def is_available(self) -> bool:
        """Check if Google OAuth libraries are available"""
        return GOOGLE_LIBS_AVAILABLE
    
    def has_credentials(self) -> bool:
        """Check if OAuth credentials file exists (or env var is set)"""
        if os.environ.get(GOOGLE_OAUTH_CREDENTIALS_ENV):
            return True
        return self.credentials_file.exists()
    
    def is_authenticated(self) -> bool:
        """Check if we have valid authentication tokens"""
        # First try to load from env if available
        if self._using_env_credentials and not self.token_file.exists():
            self._setup_from_env()
        
        if not self.token_file.exists():
            return False
        
        try:
            with open(self.token_file, 'rb') as token:
                self.credentials = pickle.load(token)
            
            if self.credentials and self.credentials.valid:
                return True
            
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
                self._save_token()
                return True
                
        except Exception as e:
            print(f"Error checking authentication: {e}")
        
        return False
    
    def authenticate(self, headless: bool = False) -> bool:
        """
        Authenticate with Gmail OAuth 2.0
        
        Args:
            headless: If True, don't open browser (for server use)
            
        Returns:
            True if authentication successful
        """
        if not GOOGLE_LIBS_AVAILABLE:
            print("Google OAuth libraries not installed")
            return False
        
        if not self.has_credentials():
            print(f"OAuth credentials file not found: {self.credentials_file}")
            print("Download from Google Cloud Console and place at the path above")
            return False
        
        # Try to load existing token
        if self.is_authenticated():
            self._build_service()
            return True
        
        # Need to run OAuth flow
        if headless:
            print("OAuth token expired/missing. Run authenticate() interactively first.")
            return False
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_file), 
                SCOPES
            )
            # Force account selection and hint to the correct account
            auth_url, _ = flow.authorization_url(
                prompt='consent',
                access_type='offline',
                login_hint='payments.dev.94@gmail.com'
            )
            print(f"\nOpening browser for authentication...")
            print(f"Please sign in with: payments.dev.94@gmail.com")
            print(f"\nIf wrong account appears, use this URL in incognito/private window:")
            print(f"{auth_url}\n")
            
            self.credentials = flow.run_local_server(
                port=0,  # Auto-select available port
                prompt='consent',
                login_hint='payments.dev.94@gmail.com'
            )
            self._save_token()
            self._build_service()
            print("Gmail OAuth authentication successful!")
            return True
            
        except Exception as e:
            print(f"OAuth authentication failed: {e}")
            return False
    
    def _save_token(self):
        """Save OAuth token to file"""
        with open(self.token_file, 'wb') as token:
            pickle.dump(self.credentials, token)
    
    def _build_service(self):
        """Build Gmail API service"""
        if self.credentials:
            self.service = build('gmail', 'v1', credentials=self.credentials)
    
    def fetch_recent_emails(
        self, 
        hours: int = 24,
        sender_filter: str = None,
        subject_filter: str = None,
        max_results: int = 50
    ) -> List[GmailMessage]:
        """
        Fetch recent emails from Gmail
        
        Args:
            hours: Look back this many hours
            sender_filter: Filter by sender email (partial match)
            subject_filter: Filter by subject (partial match)
            max_results: Maximum messages to return
            
        Returns:
            List of GmailMessage objects
        """
        if not self.service:
            if not self.authenticate(headless=True):
                return []
        
        try:
            # Build search query
            query_parts = []
            
            # Time filter
            after_date = datetime.now() - timedelta(hours=hours)
            query_parts.append(f"after:{after_date.strftime('%Y/%m/%d')}")
            
            # Sender filter
            if sender_filter:
                query_parts.append(f"from:{sender_filter}")
            
            # Subject filter
            if subject_filter:
                query_parts.append(f"subject:{subject_filter}")
            
            query = " ".join(query_parts)
            
            # Fetch message IDs
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                return []
            
            # Fetch full message details
            gmail_messages = []
            for msg in messages:
                full_msg = self.service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full'
                ).execute()
                
                gmail_message = self._parse_message(full_msg)
                if gmail_message:
                    gmail_messages.append(gmail_message)
            
            return gmail_messages
            
        except Exception as e:
            print(f"Error fetching emails: {e}")
            return []
    
    def _parse_message(self, msg: dict) -> Optional[GmailMessage]:
        """Parse Gmail API message to GmailMessage object"""
        try:
            headers = {h['name']: h['value'] for h in msg['payload']['headers']}
            
            # Get body
            body = self._get_message_body(msg['payload'])
            
            # Parse date
            date_str = headers.get('Date', '')
            try:
                # Gmail date format varies, try common formats
                from email.utils import parsedate_to_datetime
                date = parsedate_to_datetime(date_str)
            except:
                date = datetime.now()
            
            return GmailMessage(
                message_id=msg['id'],
                thread_id=msg['threadId'],
                sender=headers.get('From', ''),
                subject=headers.get('Subject', ''),
                body=body,
                date=date,
                labels=msg.get('labelIds', [])
            )
            
        except Exception as e:
            print(f"Error parsing message: {e}")
            return None
    
    def _get_message_body(self, payload: dict) -> str:
        """Extract message body from Gmail payload"""
        body = ""
        
        if 'body' in payload and payload['body'].get('data'):
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        
        elif 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        break
                elif part['mimeType'] == 'multipart/alternative':
                    body = self._get_message_body(part)
                    if body:
                        break
        
        return body
    
    def mark_as_read(self, message_id: str) -> bool:
        """Mark a message as read"""
        if not self.service:
            return False
        
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            return True
        except Exception as e:
            print(f"Error marking message as read: {e}")
            return False


# Singleton instance
gmail_oauth_client = GmailOAuthClient()


def setup_gmail_oauth():
    """
    Interactive setup for Gmail OAuth
    Run this once to authenticate and generate tokens.
    """
    print("=" * 60)
    print("Gmail OAuth 2.0 Setup")
    print("=" * 60)
    print()
    
    if not GOOGLE_LIBS_AVAILABLE:
        print("First, install required libraries:")
        print("  pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        return False
    
    client = GmailOAuthClient()
    
    if not client.has_credentials():
        print(f"OAuth credentials file not found!")
        print(f"Expected path: {CREDENTIALS_FILE}")
        print()
        print("Setup steps:")
        print("1. Go to: https://console.cloud.google.com/")
        print("2. Create/select a project")
        print("3. Enable Gmail API")
        print("4. Create OAuth 2.0 credentials (Desktop app)")
        print("5. Download JSON and save to the path above")
        return False
    
    print(f"Found credentials file: {CREDENTIALS_FILE}")
    print()
    
    if client.is_authenticated():
        print("Already authenticated!")
        return True
    
    print("Starting OAuth flow...")
    print("A browser window will open for Google sign-in.")
    print()
    
    if client.authenticate():
        print()
        print("Authentication successful!")
        print(f"Token saved to: {TOKEN_FILE}")
        return True
    else:
        print("Authentication failed!")
        return False


if __name__ == "__main__":
    setup_gmail_oauth()
