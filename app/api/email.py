"""
Email API Endpoints
For email parsing and monitoring control
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Account, Transaction, ProcessedEmail
from app.services.email_parser import email_parser_service, EmailParser, ParsedTransaction
from app.services.email_monitor import email_monitor_service
from app.schemas import TransactionResponse

router = APIRouter(prefix="/email", tags=["email"])


class ParseEmailRequest(BaseModel):
    """Request to parse an email"""
    sender: str
    subject: str
    body: str
    create_transaction: bool = False


class ParseEmailResponse(BaseModel):
    """Response from parsing an email"""
    success: bool
    message: str
    amount: Optional[float] = None
    vendor: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    account_name: Optional[str] = None
    transaction_id: Optional[int] = None


class TestParserRequest(BaseModel):
    """Request to test a parser configuration"""
    account_id: str
    email_body: str


class MonitorStatusResponse(BaseModel):
    """Email monitor status"""
    is_running: bool
    poll_interval_seconds: int
    email_client_type: str
    imap_server: str
    imap_configured: bool
    gmail_oauth_configured: bool
    gmail_oauth_authenticated: bool


class GmailOAuthStatusResponse(BaseModel):
    """Gmail OAuth status"""
    libraries_installed: bool
    credentials_file_exists: bool
    is_authenticated: bool
    setup_instructions: str


@router.post("/parse/debug")
def parse_email_debug(request: ParseEmailRequest):
    """
    Debug endpoint to trace email parsing step by step.
    """
    import re
    from app.core.database import SessionLocal
    from app.models import Account
    
    debug_info = {
        "input": {
            "sender": request.sender,
            "subject": request.subject,
            "body_preview": request.body[:200] if request.body else None
        },
        "steps": []
    }
    
    db = SessionLocal()
    try:
        accounts = db.query(Account).filter(Account.is_active == True).all()
        debug_info["total_accounts"] = len(accounts)
        
        for account in accounts:
            account_debug = {
                "name": account.name,
                "sender_email": account.sender_email,
                "subject_pattern": account.subject_pattern
            }
            
            # Check sender match
            if account.sender_email:
                sender_match = account.sender_email.lower() in request.sender.lower()
                account_debug["sender_match"] = sender_match
                if not sender_match:
                    account_debug["skip_reason"] = "sender_mismatch"
                    debug_info["steps"].append(account_debug)
                    continue
            
            # Check subject match
            if account.subject_pattern:
                subject_match = account.subject_pattern.lower() in request.subject.lower()
                account_debug["subject_match"] = subject_match
                if not subject_match:
                    account_debug["skip_reason"] = "subject_mismatch"
                    debug_info["steps"].append(account_debug)
                    continue
            
            account_debug["matched"] = True
            
            # Test regex patterns
            if account.amount_regex:
                match = re.search(account.amount_regex, request.body)
                account_debug["amount_match"] = match.group(1) if match else None
            
            if account.date_regex:
                match = re.search(account.date_regex, request.body)
                account_debug["date_match"] = match.group(1) if match else None
            
            if account.merchant_regex:
                match = re.search(account.merchant_regex, request.body)
                account_debug["merchant_match"] = match.group(1) if match else None
            
            debug_info["steps"].append(account_debug)
            break
        
        return debug_info
    finally:
        db.close()


@router.post("/parse", response_model=ParseEmailResponse)
def parse_email(
    request: ParseEmailRequest,
    db: Session = Depends(get_db)
):
    """
    Parse an email and optionally create a transaction.
    Useful for testing parser configurations.
    """
    result = email_parser_service.parse_email(
        sender=request.sender,
        subject=request.subject,
        body=request.body
    )
    
    if not result:
        return ParseEmailResponse(
            success=False,
            message="No matching account or parsing failed"
        )
    
    account, parsed = result
    
    response = ParseEmailResponse(
        success=True,
        message=f"Parsed successfully with account: {account.name}",
        amount=parsed.amount,
        vendor=parsed.vendor,
        date=parsed.date.isoformat() if parsed.date else None,
        time=parsed.time,
        category=parsed.category,
        subcategory=parsed.subcategory,
        account_name=account.name
    )
    
    # Create transaction if requested
    if request.create_transaction:
        import uuid
        transaction = email_parser_service.create_transaction_from_parsed(
            account=account,
            parsed=parsed,
            source_email_id=f"manual-{uuid.uuid4()}"
        )
        
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        
        response.transaction_id = transaction.id
        response.message = f"Transaction created with ID: {transaction.id}"
    
    return response


@router.post("/test-parser", response_model=ParseEmailResponse)
def test_parser(
    request: TestParserRequest,
    db: Session = Depends(get_db)
):
    """
    Test a specific parser configuration against sample email body.
    """
    account = db.query(Account).filter(Account.id == request.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    parser = EmailParser(account)
    result = parser.parse(request.email_body)
    
    if not result:
        return ParseEmailResponse(
            success=False,
            message="Parsing failed - check regex patterns"
        )
    
    return ParseEmailResponse(
        success=True,
        message="Parsed successfully",
        amount=result.amount,
        vendor=result.vendor,
        date=result.date.isoformat() if result.date else None,
        time=result.time,
        category=result.category,
        subcategory=result.subcategory,
        account_name=account.name
    )


@router.post("/poll")
def poll_emails(background_tasks: BackgroundTasks):
    """
    Trigger a manual email poll.
    Runs in background and returns immediately.
    """
    def do_poll():
        try:
            transactions = email_monitor_service.poll_once()
            print(f"Poll completed: {len(transactions)} transactions created")
        except Exception as e:
            print(f"Poll error: {e}")
    
    background_tasks.add_task(do_poll)
    
    return {"message": "Email poll started in background"}


@router.get("/monitor/status", response_model=MonitorStatusResponse)
def get_monitor_status():
    """Get email monitor status"""
    from app.core.config import settings
    
    imap_configured = bool(
        settings.IMAP_SERVER and 
        settings.IMAP_USERNAME and 
        settings.IMAP_PASSWORD
    )
    
    # Check Gmail OAuth status
    gmail_oauth_configured = False
    gmail_oauth_authenticated = False
    try:
        from app.services.gmail_oauth import gmail_oauth_client
        gmail_oauth_configured = gmail_oauth_client.has_credentials()
        gmail_oauth_authenticated = gmail_oauth_client.is_authenticated()
    except ImportError:
        pass
    
    return MonitorStatusResponse(
        is_running=email_monitor_service.is_running,
        poll_interval_seconds=email_monitor_service.poll_interval,
        email_client_type=settings.EMAIL_CLIENT_TYPE,
        imap_server=settings.IMAP_SERVER or "Not configured",
        imap_configured=imap_configured,
        gmail_oauth_configured=gmail_oauth_configured,
        gmail_oauth_authenticated=gmail_oauth_authenticated
    )


@router.post("/monitor/start")
async def start_monitor(background_tasks: BackgroundTasks):
    """Start the email monitor (continuous polling)"""
    if email_monitor_service.is_running:
        return {"message": "Monitor is already running"}
    
    background_tasks.add_task(email_monitor_service.start_polling)
    
    return {"message": "Email monitor started"}


@router.post("/monitor/stop")
def stop_monitor():
    """Stop the email monitor"""
    if not email_monitor_service.is_running:
        return {"message": "Monitor is not running"}
    
    email_monitor_service.stop_polling()
    
    return {"message": "Email monitor stopped"}


@router.get("/processed", response_model=List[dict])
def list_processed_emails(
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List processed emails"""
    query = db.query(ProcessedEmail)
    
    if status:
        query = query.filter(ProcessedEmail.status == status)
    
    emails = query.order_by(ProcessedEmail.processed_at.desc()).limit(limit).all()
    
    return [
        {
            "id": e.id,
            "message_id": e.message_id,
            "account_id": e.account_id,
            "status": e.status,
            "error_message": e.error_message,
            "processed_at": e.processed_at.isoformat() if e.processed_at else None
        }
        for e in emails
    ]


@router.post("/reload-parsers")
def reload_parsers():
    """Reload all parser configurations"""
    email_parser_service.reload_parsers()
    return {"message": f"Reloaded {len(email_parser_service.parsers)} parsers"}


# ============================================================================
# Gmail OAuth 2.0 Endpoints
# ============================================================================

@router.get("/gmail-oauth/status", response_model=GmailOAuthStatusResponse)
def get_gmail_oauth_status():
    """
    Get Gmail OAuth 2.0 configuration status.
    
    Gmail OAuth is required for Google Workspace accounts since May 2025.
    """
    try:
        from app.services.gmail_oauth import (
            GmailOAuthClient, 
            GOOGLE_LIBS_AVAILABLE,
            CREDENTIALS_FILE
        )
        
        client = GmailOAuthClient()
        
        setup_instructions = ""
        if not GOOGLE_LIBS_AVAILABLE:
            setup_instructions = """
Step 1: Install required libraries:
    pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client

Step 2: Set up Google Cloud credentials:
    1. Go to https://console.cloud.google.com/
    2. Create/select a project
    3. Enable Gmail API (APIs & Services > Library > Gmail API)
    4. Create OAuth credentials (APIs & Services > Credentials > Create > OAuth client ID > Desktop app)
    5. Download JSON and save to: credentials/google_oauth_credentials.json

Step 3: Run OAuth setup:
    python -m app.services.gmail_oauth

Step 4: Update .env:
    EMAIL_CLIENT_TYPE=gmail_oauth
"""
        elif not client.has_credentials():
            setup_instructions = f"""
Credentials file not found at: {CREDENTIALS_FILE}

Step 1: Go to https://console.cloud.google.com/
Step 2: Enable Gmail API
Step 3: Create OAuth 2.0 credentials (Desktop app)
Step 4: Download JSON and save to: {CREDENTIALS_FILE}
Step 5: Run: python -m app.services.gmail_oauth
Step 6: Update .env: EMAIL_CLIENT_TYPE=gmail_oauth
"""
        elif not client.is_authenticated():
            setup_instructions = """
Credentials found but not authenticated.

Run: python -m app.services.gmail_oauth

This will open a browser window to complete Google sign-in.
"""
        else:
            setup_instructions = "Gmail OAuth is fully configured and authenticated!"
        
        return GmailOAuthStatusResponse(
            libraries_installed=GOOGLE_LIBS_AVAILABLE,
            credentials_file_exists=client.has_credentials(),
            is_authenticated=client.is_authenticated(),
            setup_instructions=setup_instructions.strip()
        )
        
    except ImportError:
        return GmailOAuthStatusResponse(
            libraries_installed=False,
            credentials_file_exists=False,
            is_authenticated=False,
            setup_instructions="Gmail OAuth module not available. Install required libraries."
        )


@router.get("/gmail-oauth/debug")
def debug_gmail_oauth():
    """
    Debug Gmail OAuth configuration - check env vars and file state.
    """
    import os
    import base64
    import pickle
    from pathlib import Path
    
    debug_info = {}
    
    try:
        from app.services.gmail_oauth import (
            GmailOAuthClient, 
            CREDENTIALS_FILE,
            TOKEN_FILE,
            GOOGLE_OAUTH_CREDENTIALS_ENV,
            GOOGLE_OAUTH_TOKEN_ENV
        )
        
        creds_env = os.environ.get(GOOGLE_OAUTH_CREDENTIALS_ENV, "")
        token_env = os.environ.get(GOOGLE_OAUTH_TOKEN_ENV, "")
        
        debug_info["credentials_env_set"] = bool(creds_env)
        debug_info["credentials_env_length"] = len(creds_env)
        debug_info["token_env_set"] = bool(token_env)
        debug_info["token_env_length"] = len(token_env)
        debug_info["credentials_file_path"] = str(CREDENTIALS_FILE)
        debug_info["credentials_file_exists"] = CREDENTIALS_FILE.exists()
        debug_info["token_file_path"] = str(TOKEN_FILE)
        debug_info["token_file_exists"] = TOKEN_FILE.exists()
        debug_info["token_file_size"] = TOKEN_FILE.stat().st_size if TOKEN_FILE.exists() else 0
        
        # Try to decode token directly and check its validity
        if token_env:
            try:
                token_bytes = base64.b64decode(token_env)
                debug_info["token_decode_success"] = True
                debug_info["token_bytes_length"] = len(token_bytes)
                
                # Try to load as pickle
                try:
                    creds = pickle.loads(token_bytes)
                    debug_info["token_pickle_load_success"] = True
                    debug_info["token_type"] = str(type(creds))
                    debug_info["token_valid"] = getattr(creds, 'valid', 'N/A')
                    debug_info["token_expired"] = getattr(creds, 'expired', 'N/A')
                    debug_info["has_refresh_token"] = bool(getattr(creds, 'refresh_token', None))
                except Exception as pe:
                    debug_info["token_pickle_load_success"] = False
                    debug_info["token_pickle_error"] = str(pe)
            except Exception as de:
                debug_info["token_decode_success"] = False
                debug_info["token_decode_error"] = str(de)
        
        # Now test the client
        client = GmailOAuthClient()
        debug_info["using_env_credentials"] = client._using_env_credentials
        debug_info["is_authenticated"] = client.is_authenticated()
        
        return debug_info
    except Exception as e:
        debug_info["error"] = str(e)
        import traceback
        debug_info["traceback"] = traceback.format_exc()
        return debug_info


@router.post("/gmail-oauth/test")
def test_gmail_oauth():
    """
    Test Gmail OAuth connection by fetching recent emails.
    """
    try:
        from app.services.gmail_oauth import GmailOAuthClient
        
        client = GmailOAuthClient()
        
        if not client.is_available():
            raise HTTPException(
                status_code=400, 
                detail="Google OAuth libraries not installed"
            )
        
        if not client.has_credentials():
            raise HTTPException(
                status_code=400, 
                detail="OAuth credentials file not found"
            )
        
        if not client.authenticate(headless=True):
            raise HTTPException(
                status_code=400, 
                detail="Not authenticated. Run: python -m app.services.gmail_oauth"
            )
        
        # Try to fetch recent emails
        messages = client.fetch_recent_emails(hours=24, max_results=5)
        
        return {
            "success": True,
            "message": f"Successfully connected to Gmail. Found {len(messages)} emails in last 24 hours.",
            "sample_emails": [
                {
                    "subject": msg.subject[:50] + "..." if len(msg.subject) > 50 else msg.subject,
                    "sender": msg.sender,
                    "date": msg.date.isoformat()
                }
                for msg in messages[:3]
            ]
        }
        
    except ImportError:
        raise HTTPException(
            status_code=500, 
            detail="Gmail OAuth module not available"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Gmail OAuth test failed: {str(e)}"
        )
