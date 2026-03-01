"""
Gmail Watcher Module

Specification: GMAIL-WATCHER-001
Purpose: Monitor Gmail for new unread important emails and create action files.

Functional Requirements:
- GW-001: Poll Gmail API every 120 seconds
- GW-002: Filter for unread AND important messages
- GW-003: Track processed message IDs to avoid duplicates
- GW-004: Create Markdown file in /Needs_Action for each new email
- GW-005: Log all operations to console and file
- GW-006: Handle API errors gracefully with retry logic
- GW-007: Support dry-run mode for testing
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from watchers.base_watcher import BaseWatcher


class GmailWatcher(BaseWatcher):
    """
    Gmail Watcher implementation.
    
    Monitors Gmail for new unread important emails and creates
    action files in the Obsidian vault Needs_Action folder.
    """
    
    # Gmail API scopes
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    def __init__(
        self, 
        vault_path: str, 
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
        check_interval: int = 120,
        query: str = 'is:unread is:important'
    ):
        """
        Initialize the Gmail Watcher.
        
        Args:
            vault_path: Path to Obsidian vault root
            credentials_path: Path to Gmail OAuth credentials JSON file
            token_path: Path to store/load token file (default: .cache/gmail_token.json)
            check_interval: Seconds between checks (default: 120)
            query: Gmail search query for filtering messages
        """
        super().__init__(vault_path, check_interval)
        
        self.credentials_path = credentials_path
        self.token_path = token_path or str(self.vault_path / '.cache' / 'gmail_token.json')
        self.query = query
        self.service = None
        
        # Ensure cache directory exists
        Path(self.vault_path) / '.cache'.mkdir(parents=True, exist_ok=True)
        
        # Initialize Gmail service
        self._initialize_service()
    
    def _initialize_service(self) -> None:
        """
        Initialize Gmail API service with authentication.
        
        Tries multiple authentication methods:
        1. OAuth 2.0 with credentials file
        2. Service account
        3. Environment variable for token
        """
        try:
            creds = None
            
            # Try loading from token file first
            if os.path.exists(self.token_path):
                try:
                    creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
                    self.logger.info("Loaded credentials from token file")
                except Exception as e:
                    self.logger.warning(f"Could not load token file: {e}")
            
            # If no valid credentials, try OAuth flow
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                        self.logger.info("Refreshed expired credentials")
                    except Exception as e:
                        self.logger.warning(f"Could not refresh credentials: {e}")
                        creds = None
                
                if not creds and self.credentials_path and os.path.exists(self.credentials_path):
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            self.credentials_path, self.SCOPES
                        )
                        creds = flow.run_local_server(port=0, open_browser=False)
                        self.logger.info("OAuth flow completed successfully")
                        
                        # Save credentials for future use
                        os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
                        with open(self.token_path, 'w') as token:
                            token.write(creds.to_json())
                        self.logger.info(f"Saved token to {self.token_path}")
                    except Exception as e:
                        self.logger.error(f"OAuth flow failed: {e}")
            
            # Try service account as fallback
            if not creds:
                service_account_path = os.getenv('GMAIL_SERVICE_ACCOUNT_PATH')
                if service_account_path and os.path.exists(service_account_path):
                    try:
                        creds = service_account.Credentials.from_service_account_file(
                            service_account_path, scopes=self.SCOPES
                        )
                        self.logger.info("Loaded service account credentials")
                    except Exception as e:
                        self.logger.warning(f"Could not load service account: {e}")
            
            # Try environment variable as last resort
            if not creds:
                token_env = os.getenv('GMAIL_TOKEN_JSON')
                if token_env:
                    try:
                        import json
                        creds = Credentials.from_authorized_user_info(
                            json.loads(token_env), self.SCOPES
                        )
                        self.logger.info("Loaded credentials from environment variable")
                    except Exception as e:
                        self.logger.warning(f"Could not load credentials from env: {e}")
            
            # Build service if we have credentials
            if creds:
                self.service = build('gmail', 'v1', credentials=creds)
                self.logger.info("Gmail service initialized successfully")
            else:
                self.logger.warning(
                    "No valid Gmail credentials found. "
                    "Watcher will run in simulation mode."
                )
                
        except HttpError as error:
            self.logger.error(f"Gmail API error: {error}")
            self.service = None
        except Exception as e:
            self.logger.error(f"Failed to initialize Gmail service: {e}")
            self.service = None
    
    def check_for_updates(self) -> List[Dict[str, Any]]:
        """
        Check Gmail for new unread important messages.
        
        Returns:
            List[Dict]: List of message dictionaries with id, snippet, etc.
        """
        if not self.service:
            self.logger.warning("Gmail service not available, skipping check")
            return []
        
        try:
            # Call Gmail API to list messages
            results = self.service.users().messages().list(
                userId='me',
                q=self.query,
                maxResults=10  # Limit to 10 messages per check
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                return []
            
            # Filter out already processed messages
            new_messages = []
            for message in messages:
                msg_id = message['id']
                if msg_id not in self.processed_ids:
                    new_messages.append(message)
                    self.processed_ids.add(msg_id)
            
            self.logger.info(f"Found {len(new_messages)} new message(s)")
            return new_messages
            
        except HttpError as error:
            self.logger.error(f"Gmail API error: {error}")
            if error.resp.status == 401:
                self.logger.warning("Authentication error, attempting to reinitialize")
                self._initialize_service()
            return []
        except Exception as e:
            self.logger.error(f"Error checking Gmail: {e}")
            return []
    
    def create_action_file(self, message: Dict[str, str]) -> Path:
        """
        Create a Markdown action file for a Gmail message.
        
        Args:
            message: Gmail message dictionary with 'id' key
            
        Returns:
            Path: Path to created action file
        """
        try:
            # Fetch full message details
            msg = self.service.users().messages().get(
                userId='me',
                id=message['id'],
                format='full'
            ).execute()
            
            # Extract headers
            headers = msg.get('payload', {}).get('headers', [])
            header_dict = {}
            for header in headers:
                name = header.get('name', '')
                value = header.get('value', '')
                header_dict[name] = value
            
            # Extract sender, subject, date
            from_email = header_dict.get('From', 'Unknown')
            subject = header_dict.get('Subject', 'No Subject')
            date = header_dict.get('Date', datetime.now().isoformat())
            
            # Extract body snippet
            snippet = msg.get('snippet', '')
            
            # Determine priority based on labels
            labels = msg.get('labelIds', [])
            priority = 'high' if 'IMPORTANT' in labels else 'medium'
            
            # Create metadata for frontmatter
            metadata = {
                'type': 'email',
                'from': from_email,
                'subject': subject,
                'received': datetime.now().isoformat(),
                'original_date': date,
                'priority': priority,
                'status': 'pending',
                'gmail_id': message['id']
            }
            
            # Create suggested actions based on content
            suggested_actions = self._generate_suggested_actions(
                from_email, subject, snippet
            )
            
            # Build content
            content = f"""
**From:** {from_email}
**Subject:** {subject}
**Date:** {date}

---

{snippet}
"""
            
            # Generate full Markdown content
            markdown_content = self._create_action_file_content(
                metadata=metadata,
                content=content,
                suggested_actions=suggested_actions
            )
            
            # Generate filename
            filename = self._generate_filename('EMAIL', message['id'])
            filepath = self.needs_action / filename
            
            # Write file
            if not self.dry_run:
                filepath.write_text(markdown_content, encoding='utf-8')
                self.logger.info(f"Created action file: {filepath}")
            
            return filepath
            
        except HttpError as error:
            self.logger.error(f"Error fetching message details: {error}")
            raise
        except Exception as e:
            self.logger.error(f"Error creating action file: {e}")
            raise
    
    def _generate_suggested_actions(
        self, 
        from_email: str, 
        subject: str, 
        snippet: str
    ) -> List[str]:
        """
        Generate suggested actions based on email content.
        
        Args:
            from_email: Sender email address
            subject: Email subject
            snippet: Email body snippet
            
        Returns:
            List[str]: List of suggested action strings
        """
        actions = []
        
        # Combine text for analysis
        text = f"{subject} {snippet}".lower()
        
        # Check for common patterns
        if any(word in text for word in ['invoice', 'payment', 'bill', 'receipt']):
            actions.append("Review and process payment/invoice")
            actions.append("Forward to accounting if needed")
        
        if any(word in text for word in ['urgent', 'asap', 'emergency', 'immediate']):
            actions.append("Handle with high priority")
            actions.append("Reply within 2 hours")
        
        if any(word in text for word in ['meeting', 'schedule', 'calendar', 'appointment']):
            actions.append("Check calendar availability")
            actions.append("Respond with available times")
        
        if any(word in text for word in ['question', 'help', 'support', 'issue']):
            actions.append("Provide assistance or escalate")
        
        if 'unsubscribe' in text or 'newsletter' in text:
            actions.append("Review - may be promotional")
            actions.append("Consider unsubscribing if not needed")
        
        # Default actions if no specific pattern matched
        if not actions:
            actions.append("Read and respond as needed")
        
        # Always add these
        actions.append("Archive after processing")
        
        return actions
    
    def mark_as_read(self, message_id: str) -> bool:
        """
        Mark a Gmail message as read.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.service:
            return False
        
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            self.logger.info(f"Marked message {message_id} as read")
            return True
        except HttpError as error:
            self.logger.error(f"Error marking message as read: {error}")
            return False
    
    def set_dry_run(self, dry_run: bool) -> None:
        """
        Enable or disable dry run mode.
        
        In dry run mode, the watcher logs actions but doesn't
        actually mark emails as read or create files.
        
        Args:
            dry_run: If True, log actions without side effects
        """
        self.dry_run = dry_run
        self.logger.info(f"Dry run mode: {dry_run}")


def main():
    """
    Main entry point for running Gmail Watcher standalone.
    
    Usage:
        python gmail_watcher.py [--vault PATH] [--credentials PATH] [--dry-run]
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Gmail Watcher for AI Employee')
    parser.add_argument(
        '--vault', 
        type=str,
        default=os.getenv('OBSIDIAN_VAULT_PATH', 'D:\\Hackathon-0\\AI_Employee_Vault'),
        help='Path to Obsidian vault'
    )
    parser.add_argument(
        '--credentials',
        type=str,
        default=os.getenv('GMAIL_CREDENTIALS_PATH'),
        help='Path to Gmail OAuth credentials JSON file'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=120,
        help='Check interval in seconds (default: 120)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in dry-run mode (no side effects)'
    )
    
    args = parser.parse_args()
    
    # Create watcher
    watcher = GmailWatcher(
        vault_path=args.vault,
        credentials_path=args.credentials,
        check_interval=args.interval
    )
    
    # Set dry run mode
    if args.dry_run:
        watcher.set_dry_run(True)
    
    # Start watching
    try:
        watcher.run()
    except KeyboardInterrupt:
        print("\nShutting down Gmail Watcher...")
        watcher._save_processed_ids()
        print("Goodbye!")


if __name__ == '__main__':
    main()
