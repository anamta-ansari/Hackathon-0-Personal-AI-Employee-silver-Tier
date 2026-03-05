"""
Send Email Skill - Silver Tier

This skill sends emails via Gmail API using existing authentication from gmail_auth.py.
It supports the approval workflow and logs all sent emails to actions.json.

Silver Tier Requirement: Email sending capability with human-in-the-loop approval
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
import json
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

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


class SendEmailSkill:
    """
    Send Email Skill

    Sends emails via Gmail API with approval workflow support.
    Logs all sent emails to actions.json for audit trail.
    """

    def __init__(
        self,
        vault_path: Optional[str] = None,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
        dry_run: bool = False
    ):
        """
        Initialize Send Email Skill

        Args:
            vault_path: Path to Obsidian vault root (default: VAULT_PATH env var or D:/Hackathon-0/AI_Employee_Vault)
            credentials_path: Path to Gmail OAuth credentials JSON
            token_path: Path to store/load token file
            dry_run: If True, log actions without sending emails
        """
        # Resolve paths - use environment variable or default to root vault
        self.vault_path = Path(vault_path) if vault_path else Path(DEFAULT_VAULT_PATH)
        self.project_root = Path(__file__).parent.parent.parent

        # Look for credentials.json in multiple locations
        if credentials_path:
            self.credentials_path = Path(credentials_path)
        else:
            parent_credentials = self.project_root.parent / 'credentials.json'
            if parent_credentials.exists():
                self.credentials_path = parent_credentials
            else:
                self.credentials_path = self.project_root / 'credentials.json'

        self.token_path = Path(token_path) if token_path else self.project_root / 'token.json'

        # Configuration
        self.dry_run = dry_run

        # State
        self.gmail_auth: Optional[GmailAuthSkill] = None
        self.service = None

        # Ensure directories exist
        self.logs_dir = self.vault_path / 'Logs'
        self.approved_dir = self.vault_path / 'Approved'
        self.pending_dir = self.vault_path / 'Pending_Approval'
        self.done_dir = self.vault_path / 'Done'

        for directory in [self.logs_dir, self.approved_dir, self.pending_dir, self.done_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        logger.info(f"SendEmailSkill initialized")
        logger.info(f"Vault path: {self.vault_path}")
        logger.info(f"Dry run: {self.dry_run}")

    def initialize(self) -> bool:
        """
        Initialize Gmail authentication and service

        Returns:
            bool: True if initialization successful
        """
        if not GmailAuthSkill:
            logger.error("GmailAuthSkill not available")
            return False

        self.gmail_auth = GmailAuthSkill(
            credentials_path=str(self.credentials_path),
            token_path=str(self.token_path),
            vault_path=str(self.vault_path)
        )

        if self.gmail_auth.authenticate():
            self.service = self.gmail_auth.get_service()
            logger.info("Gmail service initialized for sending emails")
            return True
        else:
            logger.error("Failed to authenticate with Gmail")
            return False

    def send_email(
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
        Send an email via Gmail API

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body text
            cc: CC recipient(s)
            bcc: BCC recipient(s)
            attachment_paths: List of file paths to attach
            html: If True, treat body as HTML

        Returns:
            dict: Result with success status, message_id, and error if any
        """
        if not self.service:
            if not self.initialize():
                return {
                    'success': False,
                    'error': 'Failed to initialize Gmail service',
                    'message_id': None
                }

        try:
            # Create message
            message = self._create_message(
                to=to,
                subject=subject,
                body=body,
                cc=cc,
                bcc=bcc,
                attachment_paths=attachment_paths,
                html=html
            )

            if self.dry_run:
                logger.info(f"[DRY RUN] Would send email to {to}")
                logger.info(f"[DRY RUN] Subject: {subject}")
                return {
                    'success': True,
                    'message_id': 'dry-run-' + datetime.now().strftime('%Y%m%d%H%M%S'),
                    'dry_run': True
                }

            # Send email
            sent_message = self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()

            message_id = sent_message.get('id')
            thread_id = sent_message.get('threadId')

            logger.info(f"Email sent successfully to {to}")
            logger.info(f"Message ID: {message_id}")

            # Log the action
            self._log_email_action(
                action_type='email_send',
                to=to,
                subject=subject,
                message_id=message_id,
                thread_id=thread_id,
                cc=cc,
                bcc=bcc,
                attachments=attachment_paths
            )

            return {
                'success': True,
                'message_id': message_id,
                'thread_id': thread_id
            }

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            self._log_email_action(
                action_type='email_send_failed',
                to=to,
                subject=subject,
                error=str(e)
            )
            return {
                'success': False,
                'error': str(e),
                'message_id': None
            }

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
            to: Recipient email address
            subject: Email subject
            body: Email body text
            cc: CC recipient(s)
            bcc: BCC recipient(s)
            attachment_paths: List of file paths to attach
            html: If True, treat body as HTML

        Returns:
            dict: Gmail API message with raw RFC822 data
        """
        # Get sender email from profile
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            from_email = profile.get('emailAddress', '')
        except Exception:
            from_email = ''

        # Create message
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
        message['from'] = from_email
        message['subject'] = subject

        if cc:
            message['cc'] = cc

        if bcc:
            # BCC is not added to headers, just used in send
            pass

        # Create recipients list for Gmail API
        recipients = [to]
        if cc:
            recipients.extend([c.strip() for c in cc.split(',')])
        if bcc:
            recipients.extend([b.strip() for b in bcc.split(',')])

        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

        return {
            'raw': raw_message,
            'to': ','.join(recipients)
        }

    def _attach_file(self, message: MIMEMultipart, file_path: str) -> None:
        """
        Attach a file to the message

        Args:
            message: MIMEMultipart message
            file_path: Path to file to attach
        """
        file_path = Path(file_path)

        if not file_path.exists():
            logger.warning(f"Attachment not found: {file_path}")
            return

        try:
            with open(file_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())

            encoders.encode_base64(part)

            # Set filename
            filename = file_path.name
            part.add_header(
                'Content-Disposition',
                f'attachment; filename="{filename}"'
            )

            message.attach(part)
            logger.info(f"Attached file: {filename}")

        except Exception as e:
            logger.error(f"Error attaching file {file_path}: {e}")

    def _log_email_action(
        self,
        action_type: str,
        to: str,
        subject: str,
        message_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Log email action to actions.json

        Args:
            action_type: Type of action (email_send, email_send_failed, etc.)
            to: Recipient email
            subject: Email subject
            message_id: Gmail message ID
            thread_id: Gmail thread ID
            cc: CC recipients
            bcc: BCC recipients
            attachments: List of attachment paths
            error: Error message if failed
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action_type': action_type,
            'actor': 'send_email_skill',
            'to': to,
            'subject': subject,
            'message_id': message_id,
            'thread_id': thread_id,
            'cc': cc,
            'bcc': bcc,
            'attachments': attachments or [],
            'dry_run': self.dry_run
        }

        if error:
            log_entry['error'] = error

        # Load existing logs
        actions_file = self.logs_dir / 'actions.json'
        actions = []

        if actions_file.exists():
            try:
                with open(actions_file, 'r', encoding='utf-8') as f:
                    actions = json.load(f)
            except Exception:
                actions = []

        # Append new entry
        actions.append(log_entry)

        # Save back
        with open(actions_file, 'w', encoding='utf-8') as f:
            json.dump(actions, f, indent=2)

        logger.debug(f"Logged action to {actions_file}")

    def process_approval_queue(self) -> Dict[str, Any]:
        """
        Process pending email approvals from Approved folder

        Returns:
            dict: Results with counts of processed, succeeded, failed
        """
        results = {
            'processed': 0,
            'succeeded': 0,
            'failed': 0,
            'errors': []
        }

        if not self.service:
            if not self.initialize():
                return results

        # Find approval files
        approval_files = list(self.approved_dir.glob('EMAIL_*.md'))

        for approval_file in approval_files:
            try:
                # Parse approval file
                email_data = self._parse_approval_file(approval_file)

                if not email_data:
                    results['failed'] += 1
                    results['errors'].append(f"Failed to parse: {approval_file.name}")
                    continue

                # Send email
                result = self.send_email(
                    to=email_data.get('to', ''),
                    subject=email_data.get('subject', ''),
                    body=email_data.get('body', ''),
                    cc=email_data.get('cc'),
                    bcc=email_data.get('bcc'),
                    attachment_paths=email_data.get('attachments', []),
                    html=email_data.get('html', False)
                )

                results['processed'] += 1

                if result.get('success'):
                    results['succeeded'] += 1
                    # Move to Done
                    done_file = self.done_dir / approval_file.name
                    approval_file.rename(done_file)
                    logger.info(f"Moved approval file to Done: {done_file.name}")
                else:
                    results['failed'] += 1
                    results['errors'].append(f"Send failed for {approval_file.name}: {result.get('error')}")

            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Error processing {approval_file.name}: {e}")
                logger.error(f"Error processing approval file: {e}")

        logger.info(f"Approval queue processed: {results['succeeded']}/{results['processed']} succeeded")
        return results

    def _parse_approval_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Parse approval request file to extract email data

        Args:
            file_path: Path to approval file

        Returns:
            dict: Email data or None if parsing failed
        """
        try:
            content = file_path.read_text(encoding='utf-8')

            # Extract frontmatter
            data = {}

            # Simple YAML-like parsing for frontmatter
            in_frontmatter = False
            frontmatter_lines = []

            for line in content.split('\n'):
                if line.strip() == '---':
                    if not in_frontmatter:
                        in_frontmatter = True
                    else:
                        in_frontmatter = False
                        break
                elif in_frontmatter:
                    frontmatter_lines.append(line)

            # Parse frontmatter
            for line in frontmatter_lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')

                    if key == 'attachments':
                        # Parse list
                        if value.startswith('[') and value.endswith(']'):
                            data[key] = [a.strip().strip('"\'') for a in value[1:-1].split(',')]
                        else:
                            data[key] = []
                    elif key == 'html':
                        data[key] = value.lower() == 'true'
                    else:
                        data[key] = value

            # Extract body (everything after frontmatter and headers)
            body_start = content.find('## Email Body')
            if body_start != -1:
                body_start = content.find('\n', body_start) + 1
                data['body'] = content[body_start:].strip()
            elif 'body' not in data:
                data['body'] = ''

            return data

        except Exception as e:
            logger.error(f"Error parsing approval file {file_path}: {e}")
            return None

    def create_approval_request(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        attachment_paths: Optional[List[str]] = None,
        html: bool = False,
        reason: str = ''
    ) -> Path:
        """
        Create an approval request file in Pending_Approval folder

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body
            cc: CC recipients
            bcc: BCC recipients
            attachment_paths: List of attachment paths
            html: If True, body is HTML
            reason: Reason for approval request

        Returns:
            Path: Path to created approval file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_subject = ''.join(c if c.isalnum() else '_' for c in subject[:30])
        filename = f'EMAIL_APPROVAL_{timestamp}_{safe_subject}.md'
        file_path = self.pending_dir / filename

        content = f'''---
type: approval_request
action: send_email
to: {to}
subject: {subject}
cc: {cc or ''}
bcc: {bcc or ''}
attachments: {attachment_paths or []}
html: {html}
created: {datetime.now().isoformat()}
status: pending
reason: {reason}
---

## Email Details

**To:** {to}
**Subject:** {subject}
**CC:** {cc or 'None'}
**BCC:** {bcc or 'None'}
**Attachments:** {', '.join(attachment_paths) if attachment_paths else 'None'}
**Format:** {'HTML' if html else 'Plain Text'}

## Email Body

{body}

---

## Approval Instructions

Move this file to `/Approved` to send the email.
Move this file to `/Rejected` to cancel.

*Created by SendEmailSkill*
'''

        file_path.write_text(content, encoding='utf-8')
        logger.info(f"Created approval request: {file_path}")

        # Log the action
        self._log_email_action(
            action_type='email_approval_requested',
            to=to,
            subject=subject,
            cc=cc,
            bcc=bcc,
            attachments=attachment_paths
        )

        return file_path

    def send_test_email(self) -> Dict[str, Any]:
        """
        Send a test email to the authenticated user's own address

        Returns:
            dict: Result with success status and message_id
        """
        if not self.service:
            if not self.initialize():
                return {
                    'success': False,
                    'error': 'Failed to initialize Gmail service',
                    'message_id': None
                }

        # Get own email address
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            own_email = profile.get('emailAddress', '')
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get profile: {e}',
                'message_id': None
            }

        # Create test email content
        timestamp = datetime.now().isoformat()
        subject = f'SendEmailSkill Test - {timestamp}'
        body = f'''
<html>
<body>
    <h2>✅ SendEmailSkill Test Successful!</h2>
    <p>This is an automated test email from the SendEmailSkill.</p>
    
    <h3>Details:</h3>
    <ul>
        <li><strong>Sent at:</strong> {timestamp}</li>
        <li><strong>From:</strong> {own_email}</li>
        <li><strong>To:</strong> {own_email}</li>
        <li><strong>Skill:</strong> SendEmailSkill v1.0 (Silver Tier)</li>
    </ul>
    
    <p>If you received this email, the SendEmailSkill is working correctly!</p>
    
    <hr>
    <p style="color: #666; font-size: 12px;">
        Generated by AI Employee SendEmailSkill<br>
        Message ID: Test - {datetime.now().strftime('%Y%m%d%H%M%S')}
    </p>
</body>
</html>
'''

        logger.info(f"Sending test email to {own_email}...")

        return self.send_email(
            to=own_email,
            subject=subject,
            body=body,
            html=True
        )

    def get_email_stats(self) -> Dict[str, Any]:
        """
        Get email sending statistics from logs

        Returns:
            dict: Statistics about sent emails
        """
        actions_file = self.logs_dir / 'actions.json'

        stats = {
            'total_sent': 0,
            'total_failed': 0,
            'total_approval_requested': 0,
            'unique_recipients': set(),
            'last_sent': None
        }

        if not actions_file.exists():
            stats['unique_recipients'] = 0
            return stats

        try:
            with open(actions_file, 'r', encoding='utf-8') as f:
                actions = json.load(f)

            for action in actions:
                action_type = action.get('action_type', '')

                if action_type == 'email_send':
                    stats['total_sent'] += 1
                    stats['unique_recipients'].add(action.get('to', ''))
                    stats['last_sent'] = action.get('timestamp')
                elif action_type == 'email_send_failed':
                    stats['total_failed'] += 1
                elif action_type == 'email_approval_requested':
                    stats['total_approval_requested'] += 1

            stats['unique_recipients'] = len(stats['unique_recipients'])

        except Exception as e:
            logger.error(f"Error reading email stats: {e}")
            stats['unique_recipients'] = 0

        return stats


# CLI interface for testing
if __name__ == '__main__':
    import argparse

    # Handle Windows console encoding
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

    parser = argparse.ArgumentParser(description='Send Email Skill')
    parser.add_argument('command', nargs='?', default='status',
                        choices=['status', 'send', 'test', 'process', 'stats'],
                        help='Command to run')
    parser.add_argument('--to', type=str, help='Recipient email address')
    parser.add_argument('--subject', type=str, help='Email subject')
    parser.add_argument('--body', type=str, help='Email body')
    parser.add_argument('--vault', type=str, help='Path to Obsidian vault')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')

    args = parser.parse_args()

    print("=" * 60)
    print("Send Email Skill - Test Mode")
    print("=" * 60)

    skill = SendEmailSkill(vault_path=args.vault, dry_run=args.dry_run)

    if args.command == 'status':
        print("\nInitialization Status:")
        initialized = skill.initialize()
        print(f"  Initialized: {initialized}")
        if initialized:
            profile = skill.service.users().getProfile(userId='me').execute()
            print(f"  Email: {profile.get('emailAddress')}")

    elif args.command == 'send':
        if not args.to or not args.subject:
            print("Error: --to and --subject are required for send command")
            sys.exit(1)

        print(f"\nSending email to {args.to}...")
        result = skill.send_email(
            to=args.to,
            subject=args.subject,
            body=args.body or 'Test email from SendEmailSkill'
        )
        print(f"  Success: {result.get('success', False)}")
        if result.get('message_id'):
            print(f"  Message ID: {result['message_id']}")
        if result.get('error'):
            print(f"  Error: {result['error']}")

    elif args.command == 'test':
        print("\n🧪 Sending test email to your own address...")
        result = skill.send_test_email()
        print(f"  Success: {result.get('success', False)}")
        if result.get('message_id'):
            print(f"  Message ID: {result['message_id']}")
            print(f"  Check your inbox!")
        if result.get('error'):
            print(f"  Error: {result['error']}")

    elif args.command == 'process':
        print("\nProcessing approval queue...")
        results = skill.process_approval_queue()
        print(f"  Processed: {results['processed']}")
        print(f"  Succeeded: {results['succeeded']}")
        print(f"  Failed: {results['failed']}")
        if results['errors']:
            print("  Errors:")
            for error in results['errors']:
                print(f"    - {error}")

    elif args.command == 'stats':
        print("\nEmail Statistics:")
        stats = skill.get_email_stats()
        print(f"  Total Sent: {stats['total_sent']}")
        print(f"  Total Failed: {stats['total_failed']}")
        print(f"  Approval Requests: {stats['total_approval_requested']}")
        print(f"  Unique Recipients: {stats['unique_recipients']}")
        if stats['last_sent']:
            print(f"  Last Sent: {stats['last_sent']}")

    print("\nDone.")
