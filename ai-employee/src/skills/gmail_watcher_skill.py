"""
Gmail Watcher Skill - Enhanced Version for Silver Tier

This skill monitors Gmail for new unread important emails and creates action files
in the Obsidian vault. It integrates with gmail_auth.py for authentication.

Silver Tier Requirement: Gmail watcher for email monitoring
Based on document specification with enhanced error handling and logging
"""

import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
import json
import re

# Environment variable for vault path (set in .env file)
# Default: D:/Hackathon-0/AI_Employee_Vault (root vault)
DEFAULT_VAULT_PATH = os.getenv('VAULT_PATH', 'D:/Hackathon-0/AI_Employee_Vault')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import Gmail auth skill
try:
    from skills.gmail_auth import GmailAuthSkill
except ImportError:
    GmailAuthSkill = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GmailWatcherSkill:
    """
    Gmail Watcher Skill
    
    Monitors Gmail for new unread important emails and creates
    action files in the Obsidian vault Needs_Action folder.
    
    Features:
    - Polls Gmail API every 120 seconds (configurable)
    - Filters for unread AND important messages
    - Tracks processed message IDs to avoid duplicates
    - Creates Markdown action files with metadata
    - Comprehensive error handling and retry logic
    - Dry-run mode for testing
    """
    
    # Default configuration
    DEFAULT_CHECK_INTERVAL = 120  # seconds
    DEFAULT_QUERY = 'is:unread in:inbox'
    MAX_RESULTS = 10  # Max messages to fetch per check
    
    # Keywords for priority classification
    HIGH_PRIORITY_KEYWORDS = [
        'urgent', 'asap', 'emergency', 'immediate', 'critical',
        'invoice', 'payment', 'overdue', 'billing',
        'contract', 'legal', 'deadline'
    ]

    MEDIUM_PRIORITY_KEYWORDS = [
        'meeting', 'schedule', 'calendar', 'appointment',
        'question', 'help', 'support', 'issue',
        'update', 'review', 'feedback'
    ]

    # System/bounce email patterns to filter out
    SYSTEM_SENDER_PATTERNS = [
        # Bounce/Non-delivery notifications
        r'mailer-daemon@',
        r'postmaster@',
        r'daemon@',
        r'bounce@',
        r'no-reply@',
        r'noreply@',
        r'do-not-reply@',
        r'donotreply@',
        
        # Google system emails
        r'googlemail\.com',
        r'notifications\.google\.com',
        r'accounts\.google\.com',
        
        # Common system addresses
        r'automated@',
        r'automation@',
        r'system@',
        r'admin@',
        r'administrator@',
        r'webmaster@',
        r'hostmaster@',
        r'abuse@',
        r'security@',
        r'privacy@',
        
        # Social media notifications
        r'notification@.*\.com',
        r'notifications@.*\.com',
        r'updates@.*\.com',
        r'alerts@.*\.com',
        
        # Marketing/Automated
        r'marketing@',
        r'newsletter@',
        r'promo@',
        r'offers@',
    ]

    # Specific bounce subject patterns
    BOUNCE_SUBJECT_PATTERNS = [
        r'undeliverable',
        r'delivery failed',
        r'mail delivery failed',
        r'returned mail',
        r'undelivered mail',
        r'delivery status notification',
        r'non-delivery report',
        r'bounce notification',
        r'message could not be delivered',
        r'address not found',
        r'user unknown',
        r'mailbox not found',
        r'invalid recipient',
        r'delivery error',
    ]
    
    def __init__(
        self,
        vault_path: Optional[str] = None,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
        check_interval: int = DEFAULT_CHECK_INTERVAL,
        query: str = DEFAULT_QUERY,
        dry_run: bool = False
    ):
        """
        Initialize Gmail Watcher Skill

        Args:
            vault_path: Path to Obsidian vault root (default: VAULT_PATH env var or D:/Hackathon-0/AI_Employee_Vault)
            credentials_path: Path to Gmail OAuth credentials JSON
            token_path: Path to store/load token file
            check_interval: Seconds between checks (default: 120)
            query: Gmail search query for filtering messages
            dry_run: If True, log actions without creating files
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

        self.token_path = Path(token_path) if token_path else self.project_root / 'token.json'
        
        # Configuration
        self.check_interval = check_interval
        self.query = query
        self.dry_run = dry_run
        
        # State
        self.processed_ids: Set[str] = set()
        self.is_running = False
        self.gmail_auth: Optional[GmailAuthSkill] = None
        self.service = None
        
        # Ensure directories exist
        self.needs_action_dir = self.vault_path / 'Needs_Action'
        self.logs_dir = self.vault_path / 'Logs'
        self.cache_dir = self.vault_path / '.cache'
        
        for directory in [self.needs_action_dir, self.logs_dir, self.cache_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Load processed IDs from cache
        self._load_processed_ids()
        
        logger.info(f"GmailWatcherSkill initialized")
        logger.info(f"Vault path: {self.vault_path}")
        logger.info(f"Check interval: {self.check_interval}s")
        logger.info(f"Dry run: {self.dry_run}")
    
    def initialize(self) -> bool:
        """
        Initialize Gmail authentication and service
        
        Returns:
            bool: True if initialization successful
        """
        if GmailAuthSkill:
            self.gmail_auth = GmailAuthSkill(
                credentials_path=str(self.credentials_path),
                token_path=str(self.token_path),
                vault_path=str(self.vault_path)
            )
            
            if self.gmail_auth.authenticate():
                self.service = self.gmail_auth.get_service()
                logger.info("Gmail service initialized via GmailAuthSkill")
                return True
            else:
                logger.error("Failed to authenticate with Gmail")
                return False
        else:
            logger.error("GmailAuthSkill not available")
            return False
    
    def check_for_updates(self) -> List[Dict[str, Any]]:
        """
        Check Gmail for new unread important messages

        Returns:
            List[Dict]: List of message dictionaries with id, snippet, etc.
        """
        if not self.service:
            logger.warning("Gmail service not available, skipping check")
            return []

        try:
            # Call Gmail API to list messages
            logger.info(f"Gmail query: {self.query}")
            results = self.service.users().messages().list(
                userId='me',
                q=self.query,
                maxResults=self.MAX_RESULTS
            ).execute()

            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} email(s) matching query")

            if not messages:
                return []

            # Filter out system/bounce emails and already processed messages
            new_messages = []
            filtered_count = 0

            for message in messages:
                msg_id = message['id']

                # Skip if already processed
                if msg_id in self.processed_ids:
                    continue

                # Fetch message headers to check sender
                msg_data = self.service.users().messages().get(
                    userId='me',
                    id=msg_id,
                    format='metadata',
                    metadataHeaders=['From', 'Subject']
                ).execute()

                headers = {h['name']: h['value'] for h in msg_data['payload']['headers']}
                from_email = headers.get('From', '')
                subject = headers.get('Subject', '')

                # Check if this is a system/bounce email
                if self._is_system_email(from_email, subject):
                    filtered_count += 1
                    logger.info(f"Filtered out system email: {from_email} - {subject[:50]}")
                    # Mark as processed to avoid re-checking
                    self.processed_ids.add(msg_id)
                    continue

                # Add to new messages
                new_messages.append(message)
                self.processed_ids.add(msg_id)

            logger.info(f"Filtered {filtered_count} system email(s), {len(new_messages)} new message(s) to process")

            # Log first few messages
            if new_messages:
                for msg in new_messages[:3]:  # Show first 3
                    msg_data = self.service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='metadata',
                        metadataHeaders=['From', 'Subject']
                    ).execute()
                    headers = {h['name']: h['value'] for h in msg_data['payload']['headers']}
                    logger.info(f"  - From: {headers.get('From', 'Unknown')}, Subject: {headers.get('Subject', 'No subject')}")

            # Save processed IDs to cache
            self._save_processed_ids()

            return new_messages

        except Exception as error:
            logger.error(f"Gmail API error: {error}")
            # Try to re-authenticate on auth errors
            if '401' in str(error) or 'Unauthorized' in str(error):
                logger.warning("Authentication error, attempting to reinitialize")
                self.initialize()
            return []

    def _is_system_email(self, from_email: str, subject: str = '') -> bool:
        """
        Check if an email is from a system/bounce sender

        Args:
            from_email: Sender email address
            subject: Email subject line

        Returns:
            bool: True if this is a system/bounce email that should be filtered
        """
        from_lower = from_email.lower()
        subject_lower = subject.lower()

        # Check sender patterns
        for pattern in self.SYSTEM_SENDER_PATTERNS:
            if re.search(pattern, from_lower, re.IGNORECASE):
                logger.debug(f"Filtered by sender pattern '{pattern}': {from_email}")
                return True

        # Check bounce subject patterns
        for pattern in self.BOUNCE_SUBJECT_PATTERNS:
            if re.search(pattern, subject_lower, re.IGNORECASE):
                logger.debug(f"Filtered by subject pattern '{pattern}': {subject[:50]}")
                return True

        return False
    
    def create_action_file(self, message: Dict[str, str]) -> Path:
        """
        Create a Markdown action file for a Gmail message
        
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
            
            # Extract metadata
            from_email = header_dict.get('From', 'Unknown')
            subject = header_dict.get('Subject', 'No Subject')
            date = header_dict.get('Date', datetime.now().isoformat())
            to_email = header_dict.get('To', '')
            
            # Extract body snippet
            snippet = msg.get('snippet', '')
            
            # Extract full body if available
            body = self._extract_body(msg)
            
            # Determine priority
            priority = self._determine_priority(subject, snippet)
            
            # Get labels
            labels = msg.get('labelIds', [])
            
            # Create metadata for frontmatter
            metadata = {
                'type': 'email',
                'from': from_email,
                'to': to_email,
                'subject': subject,
                'received': datetime.now().isoformat(),
                'original_date': date,
                'priority': priority,
                'status': 'pending',
                'gmail_id': message['id'],
                'labels': labels
            }
            
            # Generate suggested actions
            suggested_actions = self._generate_suggested_actions(
                from_email, subject, snippet, body
            )
            
            # Build markdown content
            markdown_content = self._build_markdown_content(
                metadata, subject, from_email, date, body or snippet, suggested_actions
            )
            
            # Generate filename
            filename = self._generate_filename(subject, message['id'])
            filepath = self.needs_action_dir / filename
            
            # Write file
            if not self.dry_run:
                filepath.write_text(markdown_content, encoding='utf-8')
                logger.info(f"Created action file: {filepath}")
                
                # Log action
                self._log_action('create_action_file', {
                    'message_id': message['id'],
                    'filepath': str(filepath),
                    'subject': subject
                })
            else:
                logger.info(f"[DRY RUN] Would create: {filepath}")
            
            return filepath
            
        except Exception as e:
            logger.error(f"Error creating action file: {e}")
            raise
    
    def _extract_body(self, msg: Dict[str, Any]) -> str:
        """
        Extract email body from message
        
        Args:
            msg: Full Gmail message object
            
        Returns:
            str: Email body text
        """
        body = ""
        
        try:
            payload = msg.get('payload', {})
            parts = payload.get('parts', [])
            
            # Try to find text/plain part
            for part in parts:
                mime_type = part.get('mimeType', '')
                if mime_type == 'text/plain':
                    body_data = part.get('body', {}).get('data', '')
                    if body_data:
                        import base64
                        body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                        break
            
            # Fallback to body if no parts
            if not body:
                body_data = payload.get('body', {}).get('data', '')
                if body_data:
                    import base64
                    body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                    
        except Exception as e:
            logger.warning(f"Error extracting body: {e}")
        
        return body
    
    def _determine_priority(self, subject: str, snippet: str) -> str:
        """
        Determine email priority based on content
        
        Args:
            subject: Email subject
            snippet: Email snippet
            
        Returns:
            str: 'high', 'medium', or 'low'
        """
        text = f"{subject} {snippet}".lower()
        
        # Check high priority keywords
        for keyword in self.HIGH_PRIORITY_KEYWORDS:
            if keyword in text:
                return 'high'
        
        # Check medium priority keywords
        for keyword in self.MEDIUM_PRIORITY_KEYWORDS:
            if keyword in text:
                return 'medium'
        
        return 'low'
    
    def _generate_suggested_actions(
        self,
        from_email: str,
        subject: str,
        snippet: str,
        body: str
    ) -> List[str]:
        """
        Generate suggested actions based on email content
        
        Args:
            from_email: Sender email
            subject: Email subject
            snippet: Email snippet
            body: Full email body
            
        Returns:
            List[str]: Suggested actions
        """
        actions = []
        text = f"{subject} {snippet} {body}".lower()
        
        # Payment/Invoice related
        if any(word in text for word in ['invoice', 'payment', 'bill', 'receipt', 'billing']):
            actions.append("Review and process payment/invoice")
            actions.append("Forward to accounting if needed")
            actions.append("Verify amount and due date")
        
        # Urgent items
        if any(word in text for word in ['urgent', 'asap', 'emergency', 'immediate', 'critical']):
            actions.append("Handle with high priority")
            actions.append("Reply within 2 hours")
        
        # Meeting/Scheduling
        if any(word in text for word in ['meeting', 'schedule', 'calendar', 'appointment', 'invite']):
            actions.append("Check calendar availability")
            actions.append("Respond with available times")
            actions.append("Add to calendar if confirmed")
        
        # Questions/Support
        if any(word in text for word in ['question', 'help', 'support', 'issue', 'problem']):
            actions.append("Provide assistance or clarification")
            actions.append("Escalate if beyond scope")
        
        # Business/Sales
        if any(word in text for word in ['proposal', 'quote', 'estimate', 'contract', 'agreement']):
            actions.append("Review terms and conditions")
            actions.append("Prepare response or counter-proposal")
        
        # Newsletters/Promotional
        if any(word in text for word in ['newsletter', 'unsubscribe', 'promotion', 'offer']):
            actions.append("Review - may be promotional")
            actions.append("Consider unsubscribing if not needed")
        
        # Default actions
        if not actions:
            actions.append("Read and respond as needed")
        
        # Always add archive action
        actions.append("Archive after processing")
        
        return actions
    
    def _build_markdown_content(
        self,
        metadata: Dict[str, Any],
        subject: str,
        from_email: str,
        date: str,
        body: str,
        suggested_actions: List[str]
    ) -> str:
        """
        Build markdown content for action file
        
        Args:
            metadata: Email metadata
            subject: Email subject
            from_email: Sender email
            date: Email date
            body: Email body
            suggested_actions: List of suggested actions
            
        Returns:
            str: Markdown content
        """
        # Build frontmatter
        frontmatter = "---\n"
        for key, value in metadata.items():
            if key == 'labels':
                frontmatter += f"{key}: {', '.join(value)}\n"
            else:
                frontmatter += f"{key}: {value}\n"
        frontmatter += "---\n\n"
        
        # Build body
        content = f"""{frontmatter}
# Email: {subject}

**From:** {from_email}
**Date:** {date}
**Priority:** {metadata.get('priority', 'medium').upper()}

---

## Content

{body if body else 'No content available'}

---

## Suggested Actions

"""
        for i, action in enumerate(suggested_actions, 1):
            content += f"- [ ] {action}\n"
        
        content += """
---
## Notes

_Add your notes here_

## Status

- [ ] In Progress
- [ ] Waiting for Response
- [ ] Completed
"""
        return content
    
    def _generate_filename(self, subject: str, message_id: str) -> str:
        """
        Generate a safe filename for the action file
        
        Args:
            subject: Email subject
            message_id: Gmail message ID
            
        Returns:
            str: Safe filename
        """
        # Clean subject line
        safe_subject = re.sub(r'[^\w\s-]', '', subject)[:50]
        safe_subject = safe_subject.strip().replace(' ', '_')
        
        # Add timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return f"EMAIL_{timestamp}_{safe_subject}_{message_id[:8]}.md"
    
    def _load_processed_ids(self) -> None:
        """Load processed message IDs from cache file"""
        cache_file = self.cache_dir / 'gmail_processed_ids.json'
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.processed_ids = set(data.get('processed_ids', []))
                logger.info(f"Loaded {len(self.processed_ids)} processed IDs from cache")
            except Exception as e:
                logger.warning(f"Error loading processed IDs: {e}")
                self.processed_ids = set()
        else:
            self.processed_ids = set()
    
    def _save_processed_ids(self) -> None:
        """Save processed message IDs to cache file"""
        cache_file = self.cache_dir / 'gmail_processed_ids.json'
        
        try:
            # Keep only last 1000 IDs to prevent unbounded growth
            ids_list = list(self.processed_ids)[-1000:]
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({'processed_ids': ids_list}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving processed IDs: {e}")
    
    def _log_action(self, action_type: str, details: Dict[str, Any]) -> None:
        """
        Log action to vault logs
        
        Args:
            action_type: Type of action
            details: Action details
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'actor': 'gmail_watcher_skill',
            'action_type': action_type,
            'details': details
        }
        
        log_file = self.logs_dir / f"gmail_watcher_{datetime.now().strftime('%Y-%m-%d')}.json"
        
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
    
    def mark_as_read(self, message_id: str) -> bool:
        """
        Mark a Gmail message as read
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            bool: True if successful
        """
        if not self.service:
            return False
        
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            logger.info(f"Marked message {message_id} as read")
            return True
        except Exception as e:
            logger.error(f"Error marking message as read: {e}")
            return False
    
    def run_once(self) -> int:
        """
        Run a single check cycle
        
        Returns:
            int: Number of action files created
        """
        if not self.service:
            logger.warning("Service not initialized, attempting to initialize...")
            if not self.initialize():
                logger.error("Failed to initialize service")
                return 0
        
        files_created = 0
        
        try:
            messages = self.check_for_updates()
            
            for message in messages:
                try:
                    self.create_action_file(message)
                    files_created += 1
                except Exception as e:
                    logger.error(f"Error processing message {message['id']}: {e}")
            
            logger.info(f"Cycle complete: {files_created} file(s) created")
            
        except Exception as e:
            logger.error(f"Error in run_once: {e}")
        
        return files_created
    
    def run_continuous(self, max_iterations: Optional[int] = None) -> None:
        """
        Run continuous monitoring loop
        
        Args:
            max_iterations: Maximum number of check cycles (None for infinite)
        """
        logger.info(f"Starting continuous monitoring (interval: {self.check_interval}s)")
        self.is_running = True
        
        iteration = 0
        
        try:
            while self.is_running:
                if max_iterations and iteration >= max_iterations:
                    logger.info(f"Reached max iterations ({max_iterations})")
                    break
                
                files_created = self.run_once()
                iteration += 1
                
                if files_created > 0:
                    logger.info(f"Total iterations: {iteration}, Files created: {files_created}")
                
                # Wait for next check
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.is_running = False
            logger.info("Continuous monitoring stopped")
    
    def stop(self) -> None:
        """Stop continuous monitoring"""
        self.is_running = False
        logger.info("Stop signal sent")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get watcher status
        
        Returns:
            Dict: Status information
        """
        return {
            'is_running': self.is_running,
            'service_available': self.service is not None,
            'processed_ids_count': len(self.processed_ids),
            'check_interval': self.check_interval,
            'dry_run': self.dry_run,
            'vault_path': str(self.vault_path),
            'needs_action_dir': str(self.needs_action_dir)
        }


# CLI interface
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Gmail Watcher Skill')
    parser.add_argument('--vault', type=str, help='Path to Obsidian vault')
    parser.add_argument('--credentials', type=str, help='Path to credentials.json')
    parser.add_argument('--interval', type=int, default=120, help='Check interval in seconds')
    parser.add_argument('--dry-run', action='store_true', help='Run in dry-run mode')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--init', action='store_true', help='Initialize authentication only')
    
    args = parser.parse_args()
    
    watcher = GmailWatcherSkill(
        vault_path=args.vault,
        credentials_path=args.credentials,
        check_interval=args.interval,
        dry_run=args.dry_run
    )
    
    if args.init:
        print("Initializing Gmail authentication...")
        success = watcher.initialize()
        if success:
            print("✓ Authentication successful!")
            status = watcher.get_status()
            print(f"Service available: {status['service_available']}")
        else:
            print("✗ Authentication failed")
        sys.exit(0 if success else 1)
    
    if args.once:
        print("Running single check cycle...")
        watcher.initialize()
        count = watcher.run_once()
        print(f"Created {count} action file(s)")
        sys.exit(0)
    
    print("Starting Gmail Watcher Skill...")
    watcher.initialize()
    watcher.run_continuous()
