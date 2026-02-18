"""
Email Monitor Service
Monitors IMAP mailbox for new transaction emails and processes them

Supports two authentication methods:
1. IMAP with app password (for non-Google providers)
2. Gmail OAuth 2.0 (required for Google Workspace accounts since May 2025)
"""
import asyncio
import email
import uuid
from email.header import decode_header
from datetime import datetime, timedelta
from typing import Optional, List, Callable, Literal
from dataclasses import dataclass
import imaplib
import ssl

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import Account, Transaction, ProcessedEmail
from app.services.email_parser import email_parser_service, ParsedTransaction

# Email client type
EmailClientType = Literal["imap", "gmail_oauth"]


@dataclass
class EmailMessage:
    """Represents an email message"""
    message_id: str
    sender: str
    subject: str
    body: str
    date: datetime
    uid: str


class IMAPClient:
    """
    IMAP client for connecting to email servers.
    """
    
    def __init__(
        self,
        server: str = None,
        port: int = None,
        username: str = None,
        password: str = None,
        use_ssl: bool = True
    ):
        self.server = server or settings.IMAP_SERVER
        self.port = port or settings.IMAP_PORT
        self.username = username or settings.IMAP_USERNAME
        self.password = password or settings.IMAP_PASSWORD
        self.use_ssl = use_ssl if use_ssl is not None else settings.IMAP_USE_SSL
        
        self.connection: Optional[imaplib.IMAP4_SSL] = None
    
    def connect(self) -> bool:
        """Connect to IMAP server"""
        try:
            if self.use_ssl:
                context = ssl.create_default_context()
                self.connection = imaplib.IMAP4_SSL(
                    self.server, 
                    self.port,
                    ssl_context=context
                )
            else:
                self.connection = imaplib.IMAP4(self.server, self.port)
            
            # Login
            self.connection.login(self.username, self.password)
            print(f"Connected to IMAP server: {self.server}")
            return True
            
        except Exception as e:
            print(f"Failed to connect to IMAP: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from IMAP server"""
        if self.connection:
            try:
                self.connection.logout()
            except:
                pass
            self.connection = None
    
    def select_folder(self, folder: str = "INBOX") -> bool:
        """Select mailbox folder"""
        if not self.connection:
            return False
        
        try:
            status, _ = self.connection.select(folder)
            return status == "OK"
        except Exception as e:
            print(f"Failed to select folder {folder}: {e}")
            return False
    
    def search_emails(
        self, 
        since_date: datetime = None,
        from_address: str = None,
        subject_contains: str = None,
        unseen_only: bool = True
    ) -> List[str]:
        """
        Search for emails matching criteria.
        Returns list of email UIDs.
        """
        if not self.connection:
            return []
        
        # Build search criteria
        criteria = []
        
        if unseen_only:
            criteria.append("UNSEEN")
        
        if since_date:
            date_str = since_date.strftime("%d-%b-%Y")
            criteria.append(f'SINCE "{date_str}"')
        
        if from_address:
            criteria.append(f'FROM "{from_address}"')
        
        if subject_contains:
            criteria.append(f'SUBJECT "{subject_contains}"')
        
        # Default to all if no criteria
        search_str = " ".join(criteria) if criteria else "ALL"
        
        try:
            status, data = self.connection.search(None, search_str)
            if status == "OK" and data[0]:
                return data[0].decode().split()
            return []
        except Exception as e:
            print(f"Email search failed: {e}")
            return []
    
    def fetch_email(self, uid: str) -> Optional[EmailMessage]:
        """Fetch a single email by UID"""
        if not self.connection:
            return None
        
        try:
            status, data = self.connection.fetch(uid.encode(), "(RFC822)")
            if status != "OK" or not data[0]:
                return None
            
            # Parse email
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Extract headers
            message_id = msg.get("Message-ID", f"<{uuid.uuid4()}@local>")
            
            # Decode sender
            sender = self._decode_header(msg.get("From", ""))
            
            # Decode subject
            subject = self._decode_header(msg.get("Subject", ""))
            
            # Parse date
            date_str = msg.get("Date", "")
            try:
                date = email.utils.parsedate_to_datetime(date_str)
            except:
                date = datetime.now()
            
            # Extract body
            body = self._get_email_body(msg)
            
            return EmailMessage(
                message_id=message_id,
                sender=sender,
                subject=subject,
                body=body,
                date=date,
                uid=uid
            )
            
        except Exception as e:
            print(f"Failed to fetch email {uid}: {e}")
            return None
    
    def _decode_header(self, header: str) -> str:
        """Decode email header"""
        if not header:
            return ""
        
        decoded_parts = decode_header(header)
        result = []
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    result.append(part.decode(encoding or "utf-8", errors="replace"))
                except:
                    result.append(part.decode("utf-8", errors="replace"))
            else:
                result.append(part)
        
        return " ".join(result)
    
    def _get_email_body(self, msg: email.message.Message) -> str:
        """Extract text body from email"""
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                
                # Get text content
                if content_type == "text/plain":
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or "utf-8"
                        body = payload.decode(charset, errors="replace")
                        break
                    except:
                        continue
                elif content_type == "text/html" and not body:
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or "utf-8"
                        body = payload.decode(charset, errors="replace")
                        # Strip HTML tags (basic)
                        import re
                        body = re.sub(r'<[^>]+>', ' ', body)
                        body = re.sub(r'\s+', ' ', body)
                    except:
                        continue
        else:
            try:
                payload = msg.get_payload(decode=True)
                charset = msg.get_content_charset() or "utf-8"
                body = payload.decode(charset, errors="replace")
            except:
                body = str(msg.get_payload())
        
        return body.strip()
    
    def mark_as_read(self, uid: str) -> bool:
        """Mark email as read"""
        if not self.connection:
            return False
        
        try:
            self.connection.store(uid.encode(), "+FLAGS", "\\Seen")
            return True
        except:
            return False


class EmailMonitorService:
    """
    Service that monitors mailbox for new transaction emails.
    
    Supports two modes:
    1. IMAP mode (default) - For Yahoo, Outlook, custom servers
    2. Gmail OAuth mode - For Gmail/Google Workspace (required since May 2025)
    
    Set EMAIL_CLIENT_TYPE in settings to choose mode.
    """
    
    def __init__(self, client_type: EmailClientType = None):
        self.client_type = client_type or getattr(settings, 'EMAIL_CLIENT_TYPE', 'imap')
        self.imap_client = IMAPClient()
        self.gmail_client = None  # Lazy loaded
        self.is_running = False
        self.poll_interval = settings.EMAIL_POLL_INTERVAL_SECONDS
        self.on_transaction_callback: Optional[Callable] = None
    
    def _get_gmail_client(self):
        """Lazy load Gmail OAuth client"""
        if self.gmail_client is None:
            try:
                from app.services.gmail_oauth import GmailOAuthClient
                self.gmail_client = GmailOAuthClient()
            except ImportError:
                print("Gmail OAuth client not available")
        return self.gmail_client
    
    def is_email_processed(self, message_id: str) -> bool:
        """Check if email has already been processed"""
        db = SessionLocal()
        try:
            existing = db.query(ProcessedEmail).filter(
                ProcessedEmail.message_id == message_id
            ).first()
            return existing is not None
        finally:
            db.close()
    
    def mark_email_processed(
        self, 
        message_id: str, 
        account_id: str = None,
        status: str = "success",
        error_message: str = None
    ):
        """Mark email as processed"""
        db = SessionLocal()
        try:
            processed = ProcessedEmail(
                id=str(uuid.uuid4()),
                message_id=message_id,
                account_id=account_id,
                status=status,
                error_message=error_message
            )
            db.add(processed)
            db.commit()
        finally:
            db.close()
    
    def process_email(self, email_msg: EmailMessage) -> Optional[Transaction]:
        """
        Process a single email and create transaction if valid.
        Returns the created Transaction or None.
        """
        # Check if already processed
        if self.is_email_processed(email_msg.message_id):
            print(f"Email already processed: {email_msg.message_id}")
            return None
        
        # Try to parse
        result = email_parser_service.parse_email(
            sender=email_msg.sender,
            subject=email_msg.subject,
            body=email_msg.body
        )
        
        if not result:
            # No matching account or parsing failed
            self.mark_email_processed(
                message_id=email_msg.message_id,
                status="skipped",
                error_message="No matching account or parsing failed"
            )
            return None
        
        account, parsed = result
        
        # Use email received date as transaction date (more reliable than parsed date)
        parsed.date = email_msg.date
        
        # Create transaction
        db = SessionLocal()
        try:
            transaction = email_parser_service.create_transaction_from_parsed(
                account=account,
                parsed=parsed,
                source_email_id=email_msg.message_id
            )
            
            db.add(transaction)
            db.commit()
            db.refresh(transaction)
            
            # Mark email as processed
            self.mark_email_processed(
                message_id=email_msg.message_id,
                account_id=account.id,
                status="success"
            )
            
            print(f"Created transaction: {transaction.parsed_vendor} - {transaction.parsed_amount}")
            
            # Callback for push notification etc.
            if self.on_transaction_callback:
                self.on_transaction_callback(transaction)
            
            return transaction
            
        except Exception as e:
            db.rollback()
            self.mark_email_processed(
                message_id=email_msg.message_id,
                status="failed",
                error_message=str(e)
            )
            print(f"Failed to create transaction: {e}")
            return None
        finally:
            db.close()
    
    def poll_once(self) -> List[Transaction]:
        """
        Poll mailbox once and process new emails.
        Returns list of created transactions.
        
        Automatically uses the configured client type (IMAP or Gmail OAuth).
        """
        if self.client_type == "gmail_oauth":
            return self._poll_gmail_oauth()
        else:
            return self._poll_imap()
    
    def _poll_imap(self) -> List[Transaction]:
        """Poll using traditional IMAP client"""
        transactions = []
        
        # Connect to IMAP
        if not self.imap_client.connect():
            print("Failed to connect to IMAP server")
            return transactions
        
        try:
            # Select inbox
            if not self.imap_client.select_folder("INBOX"):
                print("Failed to select INBOX")
                return transactions
            
            # Get active accounts to know what senders to look for
            db = SessionLocal()
            try:
                accounts = db.query(Account).filter(Account.is_active == True).all()
            finally:
                db.close()
            
            # Search for emails from each account's sender
            for account in accounts:
                if not account.sender_email:
                    continue
                
                # Search recent emails from this sender
                since_date = datetime.now() - timedelta(days=7)
                uids = self.imap_client.search_emails(
                    since_date=since_date,
                    from_address=account.sender_email,
                    unseen_only=False  # Check all, we track processed separately
                )
                
                print(f"Found {len(uids)} emails from {account.sender_email}")
                
                for uid in uids:
                    email_msg = self.imap_client.fetch_email(uid)
                    if not email_msg:
                        continue
                    
                    transaction = self.process_email(email_msg)
                    if transaction:
                        transactions.append(transaction)
                        # Mark as read
                        self.imap_client.mark_as_read(uid)
        
        finally:
            self.imap_client.disconnect()
        
        return transactions
    
    def _poll_gmail_oauth(self) -> List[Transaction]:
        """Poll using Gmail OAuth 2.0 API"""
        transactions = []
        
        gmail_client = self._get_gmail_client()
        if not gmail_client:
            print("Gmail OAuth client not available")
            return transactions
        
        if not gmail_client.is_available():
            print("Google OAuth libraries not installed")
            print("Run: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
            return transactions
        
        if not gmail_client.authenticate(headless=True):
            print("Gmail OAuth authentication failed")
            print("Run the setup script first: python -m app.services.gmail_oauth")
            return transactions
        
        # Get active accounts to know what senders to look for
        db = SessionLocal()
        try:
            accounts = db.query(Account).filter(Account.is_active == True).all()
        finally:
            db.close()
        
        # Fetch emails from each account's sender
        for account in accounts:
            if not account.sender_email:
                continue
            
            # Fetch recent emails from this sender
            gmail_messages = gmail_client.fetch_recent_emails(
                hours=24 * 7,  # Last 7 days
                sender_filter=account.sender_email,
                max_results=50
            )
            
            print(f"Found {len(gmail_messages)} emails from {account.sender_email}")
            
            for gmail_msg in gmail_messages:
                # Convert to EmailMessage format
                email_msg = EmailMessage(
                    message_id=gmail_msg.message_id,
                    sender=gmail_msg.sender,
                    subject=gmail_msg.subject,
                    body=gmail_msg.body,
                    date=gmail_msg.date,
                    uid=gmail_msg.message_id
                )
                
                transaction = self.process_email(email_msg)
                if transaction:
                    transactions.append(transaction)
                    # Mark as read
                    gmail_client.mark_as_read(gmail_msg.message_id)
        
        return transactions
    
    async def start_polling(self):
        """Start continuous polling (async)"""
        self.is_running = True
        print(f"Starting email monitor, polling every {self.poll_interval} seconds")
        
        while self.is_running:
            try:
                transactions = self.poll_once()
                if transactions:
                    print(f"Processed {len(transactions)} new transactions")
            except Exception as e:
                print(f"Error during poll: {e}")
            
            await asyncio.sleep(self.poll_interval)
    
    def stop_polling(self):
        """Stop continuous polling"""
        self.is_running = False
        print("Stopping email monitor")


# Singleton instance
email_monitor_service = EmailMonitorService()
