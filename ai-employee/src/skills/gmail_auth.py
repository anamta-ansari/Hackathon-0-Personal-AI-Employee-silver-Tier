"""
Gmail Authentication Skill for AI Employee - Silver Tier

This skill handles OAuth 2.0 authentication with Gmail API using the credentials.json file.
It manages token refresh, credential validation, and provides authenticated Gmail service instances.

Silver Tier Requirement: Gmail watcher authentication
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

# Environment variable for vault path (set in .env file)
# Default: D:/Hackathon-0/AI_Employee_Vault (root vault)
DEFAULT_VAULT_PATH = os.getenv('VAULT_PATH', 'D:/Hackathon-0/AI_Employee_Vault')

# Google API dependencies
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from google_auth_httplib2 import AuthorizedHttp
    import httplib2
    import requests
    GOOGLE_AVAILABLE = True
except ImportError as e:
    GOOGLE_AVAILABLE = False
    logger.warning(f"Google API import error: {e}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress Google API discovery cache warnings
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)


class GmailAuthSkill:
    """
    Gmail Authentication Skill

    Handles OAuth 2.0 flow for Gmail API access.
    Manages token storage, refresh, and validation.
    """

    # Gmail API scopes - minimal required permissions
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',  # Read emails
        'https://www.googleapis.com/auth/gmail.send',       # Send emails
        'https://www.googleapis.com/auth/gmail.labels',     # Manage labels
    ]

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
        vault_path: Optional[str] = None
    ):
        """
        Initialize Gmail Authentication Skill

        Args:
            credentials_path: Path to credentials.json (OAuth client config)
            token_path: Path to store/load token.json (refresh token)
            vault_path: Path to Obsidian vault (default: VAULT_PATH env var or D:/Hackathon-0/AI_Employee_Vault)
        """
        # Resolve paths - use environment variable or default to root vault
        self.vault_path = Path(vault_path) if vault_path else Path(DEFAULT_VAULT_PATH)
        self.project_root = Path(__file__).parent.parent.parent
        
        # Look for credentials.json in multiple locations
        if credentials_path:
            self.credentials_path = Path(credentials_path)
        else:
            # Try parent directory first (D:\Hackathon-0\credentials.json)
            parent_credentials = self.project_root.parent / 'credentials.json'
            if parent_credentials.exists():
                self.credentials_path = parent_credentials
            else:
                # Fallback to project root
                self.credentials_path = self.project_root / 'credentials.json'
        
        # Token path
        self.token_path = Path(token_path) if token_path else self.project_root / 'token.json'
        
        # Auth state
        self.creds: Optional[Credentials] = None
        self.service = None
        self.is_authenticated = False
        
        # Ensure logging directory exists
        self.logs_dir = self.vault_path / 'Logs'
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"GmailAuthSkill initialized")
        logger.info(f"Credentials path: {self.credentials_path}")
        logger.info(f"Token path: {self.token_path}")
    
    def validate_credentials_file(self) -> bool:
        """
        Validate that credentials.json exists and is properly formatted
        
        Returns:
            bool: True if credentials are valid, False otherwise
        """
        if not self.credentials_path.exists():
            logger.error(f"Credentials file not found: {self.credentials_path}")
            return False
        
        try:
            with open(self.credentials_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Validate structure
            if 'installed' not in config and 'web' not in config:
                logger.error("Invalid credentials format. Missing 'installed' or 'web' section")
                return False
            
            auth_section = config.get('installed') or config.get('web')
            required_fields = ['client_id', 'client_secret', 'auth_uri', 'token_uri']
            
            for field in required_fields:
                if field not in auth_section:
                    logger.error(f"Missing required field in credentials: {field}")
                    return False
            
            logger.info("Credentials file validated successfully")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in credentials file: {e}")
            return False
        except Exception as e:
            logger.error(f"Error validating credentials: {e}")
            return False
    
    def authenticate(self, force_refresh: bool = False) -> bool:
        """
        Authenticate with Gmail API
        
        Attempts to load existing token, or initiates OAuth flow if needed.
        
        Args:
            force_refresh: If True, force re-authentication even if token exists
            
        Returns:
            bool: True if authentication successful, False otherwise
        """
        if not GOOGLE_AVAILABLE:
            logger.error("Google API libraries not installed. Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
            return False
        
        if not self.validate_credentials_file():
            return False
        
        try:
            # Try to load existing token
            if not force_refresh and self.token_path.exists():
                logger.info("Loading existing token...")
                self.creds = Credentials.from_authorized_user_file(
                    self.token_path, 
                    self.SCOPES
                )
            
            # Check if token is valid or needs refresh
            if self.creds and self.creds.valid:
                logger.info("Existing token is valid")
                self.is_authenticated = True
                self._build_service()
                return True
            
            # Token expired or invalid - refresh if possible
            if self.creds and self.creds.expired and self.creds.refresh_token:
                logger.info("Refreshing expired token...")
                try:
                    self.creds.refresh(Request())
                    self._save_token()
                    self.is_authenticated = True
                    self._build_service()
                    logger.info("Token refreshed successfully")
                    return True
                except Exception as e:
                    logger.warning(f"Token refresh failed: {e}. Will re-authenticate.")
                    self.creds = None
            
            # No valid token - initiate OAuth flow
            logger.info("Initiating OAuth 2.0 flow...")
            return self._oauth_flow()
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            self.is_authenticated = False
            return False
    
    def _oauth_flow(self) -> bool:
        """
        Execute OAuth 2.0 installed app flow

        Opens browser for user authorization.

        Returns:
            bool: True if flow completes successfully
        """
        try:
            # Load client config
            with open(self.credentials_path, 'r', encoding='utf-8') as f:
                client_config = json.load(f)

            # Create flow
            flow = InstalledAppFlow.from_client_config(
                client_config,
                self.SCOPES
            )

            # Run local server for OAuth callback
            logger.info("Opening browser for authorization...")
            logger.info("Please complete the authorization in your browser")
            logger.info("If browser doesn't open automatically, follow the URL shown")

            # Use port 0 for random available port, or try common ports
            self.creds = flow.run_local_server(
                port=0,  # Use random available port
                bind_address='127.0.0.1',
                open_browser=True
            )

            # Save token for future use
            if self.creds:
                self._save_token()
                self.is_authenticated = True
                self._build_service()
                logger.info("OAuth flow completed successfully")
                return True

            return False
            
        except Exception as e:
            logger.error(f"OAuth flow error: {e}")
            return False
    
    def _save_token(self) -> None:
        """Save current credentials to token file"""
        if not self.creds:
            return
        
        try:
            # Ensure parent directory exists
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.token_path, 'w', encoding='utf-8') as f:
                f.write(self.creds.to_json())
            
            # Set restrictive permissions (Windows)
            os.chmod(self.token_path, 0o600)
            
            logger.info(f"Token saved to: {self.token_path}")
            
        except Exception as e:
            logger.error(f"Error saving token: {e}")
    
    def _build_service(self) -> None:
        """Build Gmail API service instance"""
        if not self.creds or not self.creds.valid:
            return

        try:
            from google.auth.transport.requests import Request
            import traceback
            
            # Refresh credentials to ensure they are valid
            self.creds.refresh(Request())
            
            # Manually fetch the discovery document
            discovery_url = "https://www.googleapis.com/discovery/v1/apis/gmail/v1/rest"
            try:
                response = requests.get(discovery_url, timeout=10)
                response.raise_for_status()
                discovery_doc = response.json()
                
                # Build service from discovery document
                from googleapiclient.discovery import build_from_document
                self.service = build_from_document(discovery_doc, credentials=self.creds)
                logger.info("Gmail service built successfully from manual discovery doc")
            except Exception as fetch_error:
                logger.warning(f"Manual discovery failed: {fetch_error}")
                # Fallback to standard build
                self.service = build('gmail', 'v1', credentials=self.creds, cache_discovery=False)
                logger.info("Gmail service built successfully with fallback method")
                
        except Exception as e:
            logger.error(f"Error building Gmail service: {e}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            self.service = None
    
    def get_service(self):
        """
        Get authenticated Gmail service instance
        
        Returns:
            Gmail API service instance or None if not authenticated
        """
        if not self.is_authenticated or not self.service:
            if not self.authenticate():
                return None
        return self.service
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test Gmail API connection
        
        Returns:
            dict: Connection test results
        """
        result = {
            'success': False,
            'authenticated': self.is_authenticated,
            'email': None,
            'error': None
        }
        
        try:
            service = self.get_service()
            if not service:
                result['error'] = 'Failed to get Gmail service'
                return result
            
            # Get profile to test connection
            profile = service.users().getProfile(userId='me').execute()
            result['success'] = True
            result['email'] = profile.get('emailAddress')
            result['messages_total'] = profile.get('messagesTotal', 0)
            result['threads_total'] = profile.get('threadsTotal', 0)
            
            logger.info(f"Connection test successful. Email: {result['email']}")
            
        except HttpError as e:
            result['error'] = f"API Error: {e.resp.status} - {e.content.decode()}"
            logger.error(result['error'])
        except Exception as e:
            result['error'] = f"Error: {str(e)}"
            logger.error(result['error'])
        
        return result
    
    def revoke_access(self) -> bool:
        """
        Revoke OAuth access and delete stored token
        
        Returns:
            bool: True if revocation successful
        """
        try:
            # Revoke token with Google
            if self.creds:
                import requests
                requests.post(
                    'https://oauth2.googleapis.com/revoke',
                    params={'token': self.creds.token},
                    headers={'content-type': 'application/x-www-form-urlencoded'}
                )
                logger.info("Token revoked with Google")
            
            # Delete local token
            if self.token_path.exists():
                self.token_path.unlink()
                logger.info(f"Local token deleted: {self.token_path}")
            
            self.creds = None
            self.service = None
            self.is_authenticated = False
            
            return True
            
        except Exception as e:
            logger.error(f"Error revoking access: {e}")
            return False
    
    def get_auth_status(self) -> Dict[str, Any]:
        """
        Get current authentication status
        
        Returns:
            dict: Auth status information
        """
        status = {
            'authenticated': self.is_authenticated,
            'credentials_file_exists': self.credentials_path.exists(),
            'token_file_exists': self.token_path.exists(),
            'token_valid': False,
            'token_expired': False,
            'email': None,
            'scopes': self.SCOPES
        }
        
        if self.token_path.exists():
            try:
                with open(self.token_path, 'r', encoding='utf-8') as f:
                    token_data = json.load(f)
                status['token_valid'] = True
                status['token_expired'] = False  # Would need to check expiry
                
                if self.creds and self.creds.valid:
                    status['email'] = 'Authenticated'
            except Exception as e:
                status['token_valid'] = False
                logger.warning(f"Error reading token: {e}")
        
        return status
    
    def log_auth_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """
        Log authentication event to vault logs
        
        Args:
            event_type: Type of auth event
            details: Event details to log
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'actor': 'gmail_auth_skill',
            'details': details
        }
        
        log_file = self.logs_dir / f"gmail_auth_{datetime.now().strftime('%Y-%m-%d')}.json"
        
        # Append to log file
        logs = []
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except:
                logs = []
        
        logs.append(log_entry)
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2)


# CLI interface for testing
if __name__ == '__main__':
    import sys
    import argparse
    
    # Handle Windows console encoding
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    
    parser = argparse.ArgumentParser(description='Gmail Authentication Skill')
    parser.add_argument('command', nargs='?', default='status', 
                        choices=['status', 'auth', 'revoke', 'test'],
                        help='Command to run')
    parser.add_argument('--credentials', type=str, help='Path to credentials.json')
    parser.add_argument('--token', type=str, help='Path to token.json')
    parser.add_argument('--vault', type=str, help='Path to Obsidian vault')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Gmail Authentication Skill - Test Mode")
    print("=" * 60)
    
    auth = GmailAuthSkill(
        credentials_path=args.credentials,
        token_path=args.token,
        vault_path=args.vault
    )
    
    if args.command == 'status':
        print("\nAuth Status:")
        status = auth.get_auth_status()
        for key, value in status.items():
            print(f"  {key}: {value}")
    
    elif args.command == 'auth':
        print("\nStarting authentication...")
        success = auth.authenticate()
        if success:
            print("[OK] Authentication successful!")
            result = auth.test_connection()
            print(f"\nConnection Test:")
            print(f"  Email: {result.get('email', 'N/A')}")
            print(f"  Messages: {result.get('messages_total', 'N/A')}")
        else:
            print("[FAIL] Authentication failed")
    
    elif args.command == 'revoke':
        print("\nRevoking access...")
        success = auth.revoke_access()
        print("[OK] Access revoked" if success else "[FAIL] Revocation failed")
    
    elif args.command == 'test':
        print("\nTesting connection...")
        result = auth.test_connection()
        print(f"  Success: {result.get('success', False)}")
        print(f"  Email: {result.get('email', 'N/A')}")
        if result.get('error'):
            print(f"  Error: {result['error']}")
    
    print("\nDone.")
