"""
Email MCP Server Skill for AI Employee - Silver Tier

This skill implements an MCP (Model Context Protocol) server for email operations.
It handles sending emails, managing drafts, and email-related operations.

Silver Tier Requirement: One working MCP server for external action (e.g., sending emails)

Features:
- Send emails via Gmail API
- Create and manage drafts
- Search and read emails
- Handle attachments
- Approval-based sending workflow
- Comprehensive logging
"""

import os

# Environment variable for vault path (set in .env file)
# Default: D:/Hackathon-0/AI_Employee_Vault (root vault)
DEFAULT_VAULT_PATH = os.getenv('VAULT_PATH', 'D:/Hackathon-0/AI_Employee_Vault')

import sys
import json
import base64
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import re

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


class EmailMCPServerSkill:
    """
    Email MCP Server Skill
    
    Implements MCP-style email operations for the AI Employee.
    Provides send, draft, search, and read capabilities.
    """
    
    def __init__(
        self,
        vault_path: Optional[str] = None,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
        dry_run: bool = False
    ):
        """
        Initialize Email MCP Server Skill
        
        Args:
            vault_path: Path to Obsidian vault
            credentials_path: Path to Gmail credentials JSON
            token_path: Path to token file
            dry_run: If True, log actions without sending
        """
        # Resolve paths
        self.project_root = Path(__file__).parent.parent.parent
        self.vault_path = Path(vault_path) if vault_path else Path(DEFAULT_VAULT_PATH)
        self.credentials_path = Path(credentials_path) if credentials_path else self.project_root / 'credentials.json'
        self.token_path = Path(token_path) if token_path else self.project_root / 'token.json'
        
        # State
        self.dry_run = dry_run
        self.gmail_auth: Optional[GmailAuthSkill] = None
        self.service = None
        
        # Directories
        self.sent_dir = self.vault_path / 'Sent'
        self.drafts_dir = self.vault_path / 'Drafts'
        self.logs_dir = self.vault_path / 'Logs'
        
        for directory in [self.sent_dir, self.drafts_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        logger.info("EmailMCPServerSkill initialized")
        logger.info(f"Vault path: {self.vault_path}")
        logger.info(f"Dry run: {self.dry_run}")
    
    def initialize(self) -> bool:
        """
        Initialize Gmail authentication
        
        Returns:
            bool: True if successful
        """
        if GmailAuthSkill:
            self.gmail_auth = GmailAuthSkill(
                credentials_path=str(self.credentials_path),
                token_path=str(self.token_path),
                vault_path=str(self.vault_path)
            )
            
            if self.gmail_auth.authenticate():
                self.service = self.gmail_auth.get_service()
                logger.info("Email MCP Server initialized")
                return True
            else:
                logger.error("Failed to authenticate for Email MCP")
                return False
        else:
            logger.error("GmailAuthSkill not available")
            return False
    
    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        attachment_paths: Optional[List[str]] = None,
        html: bool = False,
        requires_approval: bool = True
    ) -> Dict[str, Any]:
        """
        Send an email via Gmail API
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body content
            cc: CC recipients (comma-separated)
            bcc: BCC recipients (comma-separated)
            attachment_paths: List of file paths to attach
            html: If True, treat body as HTML
            requires_approval: If True, create approval request first
            
        Returns:
            Dict: Send result with status and message ID
        """
        result = {
            'success': False,
            'message_id': None,
            'status': 'pending',
            'error': None,
            'requires_approval': requires_approval
        }
        
        # Ensure authentication
        if not self.service:
            if not self.initialize():
                result['error'] = 'Authentication failed'
                return result
        
        # Create approval request if required
        if requires_approval:
            approval_file = self._create_send_approval_request(
                to, subject, body, cc, bcc, attachment_paths, html
            )
            result['status'] = 'pending_approval'
            result['approval_file'] = str(approval_file)
            result['message'] = f"Approval request created: {approval_file}"
            logger.info(f"Created approval request for email to {to}")
            return result
        
        # Send directly if no approval required
        if self.dry_run:
            logger.info(f"[DRY RUN] Would send email to {to}: {subject}")
            result['status'] = 'dry_run'
            result['success'] = True
            result['message'] = 'Dry run - no email sent'
            return result
        
        try:
            # Create message
            message = self._create_message(to, subject, body, cc, bcc, attachment_paths, html)
            
            # Send via Gmail API
            sent_message = self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            
            result['success'] = True
            result['message_id'] = sent_message.get('id')
            result['status'] = 'sent'
            result['message'] = f"Email sent successfully to {to}"
            
            logger.info(f"Email sent to {to}: {subject} (ID: {result['message_id']})")
            
            # Log action
            self._log_action('send_email', {
                'to': to,
                'subject': subject,
                'message_id': result['message_id']
            })
            
            # Save sent record
            self._save_sent_record(to, subject, body, result['message_id'])
            
        except Exception as e:
            result['error'] = str(e)
            result['status'] = 'failed'
            logger.error(f"Failed to send email: {e}")
            
            self._log_action('send_email', {
                'status': 'failed',
                'to': to,
                'subject': subject,
                'error': str(e)
            })
        
        return result
    
    def _create_message(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        attachment_paths: Optional[List[str]] = None,
        html: bool = False
    ) -> Dict[str, Any]:
        """
        Create MIME message for Gmail API
        
        Args:
            to: Recipient email
            subject: Subject
            body: Body content
            cc: CC recipients
            bcc: BCC recipients
            attachment_paths: Attachment file paths
            html: If True, use HTML format
            
        Returns:
            Dict: Gmail API message object
        """
        # Create base message
        if attachment_paths:
            message = MIMEMultipart()
            message.attach(MIMEText(body, 'html' if html else 'plain'))
            
            # Add attachments
            for file_path in attachment_paths:
                self._attach_file(message, file_path)
        else:
            message = MIMEText(body, 'html' if html else 'plain')
        
        # Set headers
        message['to'] = to
        message['subject'] = subject
        if cc:
            message['cc'] = cc
        if bcc:
            message['bcc'] = bcc
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        return {'raw': raw_message}
    
    def _attach_file(self, message: MIMEMultipart, file_path: str) -> None:
        """
        Attach a file to the message
        
        Args:
            message: MIME message
            file_path: Path to file
        """
        try:
            with open(file_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
            
            encoders.encode_base64(part)
            
            # Set filename
            filename = os.path.basename(file_path)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename="{filename}"'
            )
            
            message.attach(part)
            logger.info(f"Attached file: {filename}")
            
        except Exception as e:
            logger.error(f"Error attaching file {file_path}: {e}")
            raise
    
    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        attachment_paths: Optional[List[str]] = None,
        html: bool = False
    ) -> Dict[str, Any]:
        """
        Create an email draft
        
        Args:
            to: Recipient email
            subject: Subject
            body: Body content
            cc: CC recipients
            attachment_paths: Attachment paths
            html: If True, use HTML format
            
        Returns:
            Dict: Draft result
        """
        result = {
            'success': False,
            'draft_id': None,
            'error': None
        }
        
        # Ensure authentication
        if not self.service:
            if not self.initialize():
                result['error'] = 'Authentication failed'
                return result
        
        try:
            # Create message
            message = self._create_message(to, subject, body, cc, None, attachment_paths, html)
            
            # Create draft via Gmail API
            draft = self.service.users().drafts().create(
                userId='me',
                body={'message': message}
            ).execute()
            
            result['success'] = True
            result['draft_id'] = draft.get('id')
            result['message'] = f"Draft created: {result['draft_id']}"
            
            logger.info(f"Draft created: {result['draft_id']}")
            
            # Log action
            self._log_action('create_draft', {
                'to': to,
                'subject': subject,
                'draft_id': result['draft_id']
            })
            
            # Save draft record
            self._save_draft_record(to, subject, body, result['draft_id'])
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Failed to create draft: {e}")
        
        return result
    
    def send_draft(self, draft_id: str) -> Dict[str, Any]:
        """
        Send an existing draft
        
        Args:
            draft_id: Gmail draft ID
            
        Returns:
            Dict: Send result
        """
        result = {
            'success': False,
            'message_id': None,
            'error': None
        }
        
        if not self.service:
            if not self.initialize():
                result['error'] = 'Authentication failed'
                return result
        
        try:
            # Send draft via Gmail API
            sent_message = self.service.users().drafts().send(
                userId='me',
                body={'id': draft_id}
            ).execute()
            
            result['success'] = True
            result['message_id'] = sent_message.get('id')
            result['message'] = f"Draft sent: {result['message_id']}"
            
            logger.info(f"Draft sent: {draft_id} -> {result['message_id']}")
            
            self._log_action('send_draft', {
                'draft_id': draft_id,
                'message_id': result['message_id']
            })
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Failed to send draft: {e}")
        
        return result
    
    def search_emails(
        self,
        query: str,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search emails in Gmail
        
        Args:
            query: Gmail search query
            max_results: Maximum results to return
            
        Returns:
            List[Dict]: List of email summaries
        """
        if not self.service:
            if not self.initialize():
                return []
        
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            email_summaries = []
            
            for msg in messages:
                # Get full message details
                full_msg = self.service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'To', 'Subject', 'Date']
                ).execute()
                
                headers = full_msg.get('payload', {}).get('headers', [])
                header_dict = {h['name']: h['value'] for h in headers}
                
                email_summaries.append({
                    'id': msg['id'],
                    'from': header_dict.get('From', 'Unknown'),
                    'to': header_dict.get('To', 'Unknown'),
                    'subject': header_dict.get('Subject', 'No Subject'),
                    'date': header_dict.get('Date', 'Unknown'),
                    'snippet': full_msg.get('snippet', '')
                })
            
            return email_summaries
            
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return []
    
    def read_email(self, message_id: str) -> Dict[str, Any]:
        """
        Read a specific email
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            Dict: Email details
        """
        if not self.service:
            if not self.initialize():
                return {'error': 'Authentication failed'}
        
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = message.get('payload', {}).get('headers', [])
            header_dict = {h['name']: h['value'] for h in headers}
            
            # Extract body
            body = self._extract_body(message)
            
            return {
                'id': message['id'],
                'from': header_dict.get('From', 'Unknown'),
                'to': header_dict.get('To', 'Unknown'),
                'subject': header_dict.get('Subject', 'No Subject'),
                'date': header_dict.get('Date', 'Unknown'),
                'body': body,
                'snippet': message.get('snippet', ''),
                'labels': message.get('labelIds', [])
            }
            
        except Exception as e:
            logger.error(f"Error reading email: {e}")
            return {'error': str(e)}
    
    def _extract_body(self, message: Dict[str, Any]) -> str:
        """Extract email body from message"""
        body = ""
        
        try:
            payload = message.get('payload', {})
            parts = payload.get('parts', [])
            
            # Try to find text/plain or text/html part
            for part in parts:
                mime_type = part.get('mimeType', '')
                if mime_type in ['text/plain', 'text/html']:
                    body_data = part.get('body', {}).get('data', '')
                    if body_data:
                        body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                        break
            
            # Fallback to body if no parts
            if not body:
                body_data = payload.get('body', {}).get('data', '')
                if body_data:
                    body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                    
        except Exception as e:
            logger.warning(f"Error extracting body: {e}")
        
        return body
    
    def _create_send_approval_request(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str],
        bcc: Optional[str],
        attachment_paths: Optional[List[str]],
        html: bool
    ) -> Path:
        """Create approval request for sending email"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_subject = re.sub(r'[^\w\s-]', '', subject)[:30]
        
        filename = f"EMAIL_SEND_{safe_subject}_{timestamp}.md"
        filepath = self.vault_path / 'Pending_Approval' / filename
        
        content = f"""---
type: approval_request
action: email_send
to: {to}
subject: {subject}
created: {datetime.now().isoformat()}
status: pending
---

# Email Send Approval Request

## Recipients
- **To:** {to}
{f'- **CC:** {cc}' if cc else ''}
{f'- **BCC:** {bcc}' if bcc else ''}

## Subject
{subject}

## Body

{body}

{f'## Attachments\n\n{chr(10).join(attachment_paths)}' if attachment_paths else ''}

---

## To Approve

Move this file to /Approved folder to send the email.

## To Reject

Move this file to /Rejected folder.

---
*Generated by AI Employee - Email MCP Server*
"""
        
        filepath.write_text(content, encoding='utf-8')
        return filepath
    
    def _save_sent_record(
        self,
        to: str,
        subject: str,
        body: str,
        message_id: str
    ) -> Path:
        """Save sent email record"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"SENT_{timestamp}_{message_id[:8]}.md"
        filepath = self.sent_dir / filename
        
        content = f"""---
type: sent_email
to: {to}
subject: {subject}
sent: {datetime.now().isoformat()}
message_id: {message_id}
status: sent
---

# Sent Email

## To: {to}
## Subject: {subject}

{body}

---
*Sent by AI Employee - Email MCP Server*
"""
        
        filepath.write_text(content, encoding='utf-8')
        return filepath
    
    def _save_draft_record(
        self,
        to: str,
        subject: str,
        body: str,
        draft_id: str
    ) -> Path:
        """Save draft email record"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"DRAFT_{timestamp}_{draft_id[:8]}.md"
        filepath = self.drafts_dir / filename
        
        content = f"""---
type: draft_email
to: {to}
subject: {subject}
created: {datetime.now().isoformat()}
draft_id: {draft_id}
status: draft
---

# Email Draft

## To: {to}
## Subject: {subject}

{body}

---
*Draft created by AI Employee - Email MCP Server*
"""
        
        filepath.write_text(content, encoding='utf-8')
        return filepath
    
    def _log_action(self, action_type: str, details: Dict[str, Any]) -> None:
        """Log action to vault logs"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'actor': 'email_mcp_server_skill',
            'action_type': action_type,
            'details': details
        }
        
        log_file = self.logs_dir / f"email_mcp_{datetime.now().strftime('%Y-%m-%d')}.json"
        
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
    
    def get_status(self) -> Dict[str, Any]:
        """Get skill status"""
        return {
            'authenticated': self.service is not None,
            'dry_run': self.dry_run,
            'vault_path': str(self.vault_path),
            'sent_dir': str(self.sent_dir),
            'drafts_dir': str(self.drafts_dir)
        }


# CLI interface
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Email MCP Server Skill')
    parser.add_argument('--vault', type=str, help='Path to Obsidian vault')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--status', action='store_true', help='Show status')
    parser.add_argument('--send', action='store_true', help='Send test email')
    parser.add_argument('--to', type=str, help='Recipient email')
    parser.add_argument('--subject', type=str, help='Email subject')
    parser.add_argument('--body', type=str, help='Email body')
    
    args = parser.parse_args()
    
    skill = EmailMCPServerSkill(
        vault_path=args.vault,
        dry_run=args.dry_run
    )
    
    if args.status:
        status = skill.get_status()
        print("Email MCP Server Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")
        sys.exit(0)
    
    if args.send:
        print("Initializing Email MCP Server...")
        skill.initialize()
        
        to = args.to or 'test@example.com'
        subject = args.subject or 'Test Email from AI Employee'
        body = args.body or 'This is a test email sent by the Email MCP Server Skill.'
        
        print(f"Sending email to {to}...")
        result = skill.send_email(
            to=to,
            subject=subject,
            body=body,
            requires_approval=False  # Direct send for test
        )
        
        print(f"Result: {result}")
        sys.exit(0 if result['success'] else 1)
    
    # Default: show help
    parser.print_help()
