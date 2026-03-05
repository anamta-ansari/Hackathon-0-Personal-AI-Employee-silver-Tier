"""
WhatsApp Watcher Skill for AI Employee - Silver Tier

This skill monitors WhatsApp Web for new messages containing keywords
and creates action files in the Obsidian vault.

Silver Tier Requirement: WhatsApp watcher for communication monitoring

Features:
- Monitors WhatsApp Web via Playwright
- Filters messages by keywords (urgent, invoice, payment, etc.)
- Creates action files for relevant messages
- Session persistence for continuous monitoring
- Comprehensive error handling
"""

import os

# Environment variable for vault path (set in .env file)
# Default: D:/Hackathon-0/AI_Employee_Vault (root vault)
DEFAULT_VAULT_PATH = os.getenv('VAULT_PATH', 'D:/Hackathon-0/AI_Employee_Vault')

import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
import re

# Playwright dependency
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Playwright not installed. Run: pip install playwright && playwright install")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WhatsAppWatcherSkill:
    """
    WhatsApp Watcher Skill
    
    Monitors WhatsApp Web for new messages and creates action files
    in the Obsidian vault Needs_Action folder.
    
    Features:
    - Polls WhatsApp Web every 30 seconds (configurable)
    - Filters for keywords: urgent, asap, invoice, payment, help
    - Tracks processed messages to avoid duplicates
    - Creates Markdown action files with metadata
    - Session persistence for faster reconnection
    """
    
    # Default configuration
    DEFAULT_CHECK_INTERVAL = 30  # seconds
    DEFAULT_KEYWORDS = [
        'urgent', 'asap', 'emergency', 'immediate',
        'invoice', 'payment', 'bill', 'receipt',
        'help', 'support', 'issue', 'problem',
        'deadline', 'meeting', 'call', 'important'
    ]
    
    # WhatsApp Web selectors (may need updates if WhatsApp changes UI)
    SELECTORS = {
        'chat_list': '[data-testid="chat-list"]',
        'chat': 'div[role="row"]',
        'unread_indicator': '[aria-label*="unread"]',
        'message_content': 'span[dir="auto"]',
        'chat_name': 'span[dir="auto"][title]',
        'search_box': '[data-testid="search"]'
    }
    
    def __init__(
        self,
        vault_path: Optional[str] = None,
        session_path: Optional[str] = None,
        check_interval: int = DEFAULT_CHECK_INTERVAL,
        keywords: Optional[List[str]] = None,
        dry_run: bool = False,
        headless: bool = True
    ):
        """
        Initialize WhatsApp Watcher Skill
        
        Args:
            vault_path: Path to Obsidian vault root
            session_path: Path to store browser session data
            check_interval: Seconds between checks (default: 30)
            keywords: List of keywords to filter messages
            dry_run: If True, log actions without creating files
            headless: Run browser in headless mode
        """
        # Resolve paths
        self.project_root = Path(__file__).parent.parent.parent
        self.vault_path = Path(vault_path) if vault_path else Path(DEFAULT_VAULT_PATH)
        self.session_path = Path(session_path) if session_path else self.project_root / '.whatsapp_session'
        
        # Configuration
        self.check_interval = check_interval
        self.keywords = keywords or self.DEFAULT_KEYWORDS
        self.dry_run = dry_run
        self.headless = headless
        
        # State
        self.processed_messages: Set[str] = set()
        self.is_running = False
        self.browser = None
        self.page = None
        
        # Directories
        self.needs_action_dir = self.vault_path / 'Needs_Action'
        self.logs_dir = self.vault_path / 'Logs'
        self.cache_dir = self.vault_path / '.cache'
        
        for directory in [self.needs_action_dir, self.logs_dir, self.cache_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Load processed messages from cache
        self._load_processed_messages()
        
        logger.info("WhatsAppWatcherSkill initialized")
        logger.info(f"Vault path: {self.vault_path}")
        logger.info(f"Session path: {self.session_path}")
        logger.info(f"Check interval: {self.check_interval}s")
        logger.info(f"Keywords: {self.keywords}")
        logger.info(f"Headless: {self.headless}")
    
    def _load_processed_messages(self) -> None:
        """Load processed message IDs from cache"""
        cache_file = self.cache_dir / 'whatsapp_processed.json'
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.processed_messages = set(data.get('processed', []))
                logger.info(f"Loaded {len(self.processed_messages)} processed messages")
            except Exception as e:
                logger.warning(f"Error loading processed messages: {e}")
                self.processed_messages = set()
        else:
            self.processed_messages = set()
    
    def _save_processed_messages(self) -> None:
        """Save processed message IDs to cache"""
        cache_file = self.cache_dir / 'whatsapp_processed.json'
        
        try:
            # Keep only last 500 to prevent unbounded growth
            messages_list = list(self.processed_messages)[-500:]
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({'processed': messages_list}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving processed messages: {e}")
    
    def _create_message_hash(self, chat_name: str, content: str, timestamp: str) -> str:
        """
        Create unique hash for message deduplication
        
        Args:
            chat_name: Chat/contact name
            content: Message content
            timestamp: Message timestamp
            
        Returns:
            str: Unique message hash
        """
        import hashlib
        combined = f"{chat_name}:{content}:{timestamp}"
        return hashlib.md5(combined.encode()).hexdigest()[:16]
    
    def check_for_updates(self) -> List[Dict[str, Any]]:
        """
        Check WhatsApp for new messages with keywords
        
        Returns:
            List[Dict]: List of new message dictionaries
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright not available")
            return []
        
        messages = []
        
        try:
            with sync_playwright() as p:
                # Launch browser with persistent context
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=str(self.session_path),
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-dev-shm-usage'
                    ]
                )
                
                page = browser.pages[0] if browser.pages else browser.new_page()
                
                # Navigate to WhatsApp Web
                logger.info("Navigating to WhatsApp Web...")
                page.goto('https://web.whatsapp.com', timeout=60000)
                
                # Wait for chat list to load
                try:
                    page.wait_for_selector(self.SELECTORS['chat_list'], timeout=30000)
                    logger.info("WhatsApp Web loaded")
                except PlaywrightTimeout:
                    logger.warning("Timeout waiting for WhatsApp Web to load")
                    browser.close()
                    return messages
                
                # Small delay for content to render
                time.sleep(2)
                
                # Find all chats with unread messages
                try:
                    unread_chats = page.query_selector_all(self.SELECTORS['unread_indicator'])
                    logger.info(f"Found {len(unread_chats)} unread chat(s)")
                    
                    for chat in unread_chats:
                        try:
                            # Extract chat info
                            chat_element = chat.locator('..').locator('..')
                            
                            # Get chat name
                            name_element = chat_element.query_selector(self.SELECTORS['chat_name'])
                            chat_name = name_element.inner_text() if name_element else 'Unknown'
                            
                            # Get message preview
                            message_element = chat_element.query_selector(self.SELECTORS['message_content'])
                            message_text = message_element.inner_text() if message_element else ''
                            
                            # Check if message contains keywords
                            message_lower = message_text.lower()
                            matched_keywords = [kw for kw in self.keywords if kw in message_lower]
                            
                            if matched_keywords:
                                # Create unique hash
                                timestamp = datetime.now().isoformat()
                                msg_hash = self._create_message_hash(chat_name, message_text, timestamp)
                                
                                # Skip if already processed
                                if msg_hash not in self.processed_messages:
                                    messages.append({
                                        'hash': msg_hash,
                                        'chat_name': chat_name,
                                        'content': message_text,
                                        'matched_keywords': matched_keywords,
                                        'timestamp': timestamp
                                    })
                                    self.processed_messages.add(msg_hash)
                                    logger.info(f"New message from {chat_name}: {message_text[:50]}...")
                            
                        except Exception as e:
                            logger.warning(f"Error processing chat: {e}")
                            continue
                    
                except Exception as e:
                    logger.error(f"Error finding unread chats: {e}")
                
                browser.close()
                
        except Exception as e:
            logger.error(f"WhatsApp monitoring error: {e}")
        
        # Save processed messages
        self._save_processed_messages()
        
        logger.info(f"Found {len(messages)} new message(s) with keywords")
        return messages
    
    def create_action_file(self, message: Dict[str, Any]) -> Path:
        """
        Create a Markdown action file for a WhatsApp message
        
        Args:
            message: Message dictionary with chat_name, content, etc.
            
        Returns:
            Path: Path to created action file
        """
        try:
            # Determine priority based on keywords
            priority = self._determine_priority(message['matched_keywords'])
            
            # Generate suggested actions
            suggested_actions = self._generate_suggested_actions(
                message['chat_name'],
                message['content'],
                message['matched_keywords']
            )
            
            # Build metadata
            metadata = {
                'type': 'whatsapp_message',
                'from': message['chat_name'],
                'received': message['timestamp'],
                'priority': priority,
                'status': 'pending',
                'matched_keywords': ', '.join(message['matched_keywords']),
                'message_hash': message['hash']
            }
            
            # Build markdown content
            markdown_content = self._build_markdown_content(
                metadata,
                message['chat_name'],
                message['content'],
                suggested_actions
            )
            
            # Generate filename
            filename = self._generate_filename(message['chat_name'], message['hash'])
            filepath = self.needs_action_dir / filename
            
            # Write file
            if not self.dry_run:
                filepath.write_text(markdown_content, encoding='utf-8')
                logger.info(f"Created action file: {filepath}")
                
                # Log action
                self._log_action('create_action_file', {
                    'hash': message['hash'],
                    'filepath': str(filepath),
                    'from': message['chat_name']
                })
            else:
                logger.info(f"[DRY RUN] Would create: {filepath}")
            
            return filepath
            
        except Exception as e:
            logger.error(f"Error creating action file: {e}")
            raise
    
    def _determine_priority(self, matched_keywords: List[str]) -> str:
        """
        Determine message priority based on keywords
        
        Args:
            matched_keywords: List of matched keywords
            
        Returns:
            str: 'high', 'medium', or 'low'
        """
        high_priority = ['urgent', 'asap', 'emergency', 'immediate', 'invoice', 'payment']
        medium_priority = ['deadline', 'meeting', 'call', 'important', 'help']
        
        for kw in matched_keywords:
            if kw in high_priority:
                return 'high'
        
        for kw in matched_keywords:
            if kw in medium_priority:
                return 'medium'
        
        return 'low'
    
    def _generate_suggested_actions(
        self,
        chat_name: str,
        content: str,
        matched_keywords: List[str]
    ) -> List[str]:
        """
        Generate suggested actions based on message content
        
        Args:
            chat_name: Contact/chat name
            content: Message content
            matched_keywords: Matched keywords
            
        Returns:
            List[str]: Suggested actions
        """
        actions = []
        content_lower = content.lower()
        
        # Payment/Invoice related
        if any(kw in content_lower for kw in ['invoice', 'payment', 'bill']):
            actions.append("Review and process payment/invoice")
            actions.append("Verify amount and due date")
            actions.append("Forward to accounting if needed")
        
        # Urgent items
        if any(kw in content_lower for kw in ['urgent', 'asap', 'emergency']):
            actions.append("Handle with high priority")
            actions.append("Reply within 1 hour")
        
        # Meeting/Scheduling
        if any(kw in content_lower for kw in ['meeting', 'call', 'schedule']):
            actions.append("Check calendar availability")
            actions.append("Respond with available times")
        
        # Help/Support
        if any(kw in content_lower for kw in ['help', 'support', 'issue', 'problem']):
            actions.append("Provide assistance or clarification")
            actions.append("Escalate if beyond scope")
        
        # Default actions
        if not actions:
            actions.append("Read and respond as needed")
        
        # Always add follow-up
        actions.append("Archive after processing")
        
        return actions
    
    def _build_markdown_content(
        self,
        metadata: Dict[str, Any],
        chat_name: str,
        content: str,
        suggested_actions: List[str]
    ) -> str:
        """
        Build markdown content for action file
        
        Args:
            metadata: Message metadata
            chat_name: Contact name
            content: Message content
            suggested_actions: List of actions
            
        Returns:
            str: Markdown content
        """
        # Build frontmatter
        frontmatter = "---\n"
        for key, value in metadata.items():
            frontmatter += f"{key}: {value}\n"
        frontmatter += "---\n\n"
        
        # Build body
        markdown_content = f"""{frontmatter}
# WhatsApp Message: {chat_name}

**From:** {chat_name}
**Received:** {metadata['received']}
**Priority:** {metadata['priority'].upper()}
**Keywords:** {metadata['matched_keywords']}

---

## Message Content

{content}

---

## Suggested Actions

"""
        for i, action in enumerate(suggested_actions, 1):
            markdown_content += f"- [ ] {action}\n"
        
        markdown_content += """
---
## Notes

_Add your notes here_

## Response

_Draft your response here_

## Status

- [ ] In Progress
- [ ] Waiting for Response
- [ ] Completed
"""
        return markdown_content
    
    def _generate_filename(self, chat_name: str, message_hash: str) -> str:
        """
        Generate safe filename for action file
        
        Args:
            chat_name: Contact name
            message_hash: Message hash
            
        Returns:
            str: Safe filename
        """
        # Clean chat name
        safe_name = re.sub(r'[^\w\s-]', '', chat_name)[:30]
        safe_name = safe_name.strip().replace(' ', '_')
        
        # Add timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return f"WHATSAPP_{timestamp}_{safe_name}_{message_hash}.md"
    
    def _log_action(self, action_type: str, details: Dict[str, Any]) -> None:
        """Log action to vault logs"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'actor': 'whatsapp_watcher_skill',
            'action_type': action_type,
            'details': details
        }
        
        log_file = self.logs_dir / f"whatsapp_{datetime.now().strftime('%Y-%m-%d')}.json"
        
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
    
    def run_once(self) -> int:
        """
        Run a single check cycle
        
        Returns:
            int: Number of action files created
        """
        files_created = 0
        
        try:
            messages = self.check_for_updates()
            
            for message in messages:
                try:
                    self.create_action_file(message)
                    files_created += 1
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
            
            logger.info(f"Cycle complete: {files_created} file(s) created")
            
        except Exception as e:
            logger.error(f"Error in run_once: {e}")
        
        return files_created
    
    def run_continuous(self, max_iterations: Optional[int] = None) -> None:
        """
        Run continuous monitoring loop
        
        Args:
            max_iterations: Maximum number of check cycles
        """
        logger.info(f"Starting continuous WhatsApp monitoring (interval: {self.check_interval}s)")
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
                    logger.info(f"Iteration {iteration}: {files_created} file(s) created")
                
                # Wait for next check
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.is_running = False
            logger.info("WhatsApp monitoring stopped")
    
    def stop(self) -> None:
        """Stop continuous monitoring"""
        self.is_running = False
        logger.info("Stop signal sent")
    
    def get_status(self) -> Dict[str, Any]:
        """Get watcher status"""
        return {
            'is_running': self.is_running,
            'playwright_available': PLAYWRIGHT_AVAILABLE,
            'processed_count': len(self.processed_messages),
            'check_interval': self.check_interval,
            'dry_run': self.dry_run,
            'headless': self.headless,
            'keywords': self.keywords,
            'session_path': str(self.session_path)
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test WhatsApp Web connection
        
        Returns:
            Dict: Connection test results
        """
        result = {
            'success': False,
            'playwright_available': PLAYWRIGHT_AVAILABLE,
            'session_exists': self.session_path.exists(),
            'error': None
        }
        
        if not PLAYWRIGHT_AVAILABLE:
            result['error'] = 'Playwright not installed'
            return result
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=str(self.session_path),
                    headless=self.headless
                )
                
                page = browser.pages[0] if browser.pages else browser.new_page()
                
                logger.info("Navigating to WhatsApp Web...")
                page.goto('https://web.whatsapp.com', timeout=60000)
                
                # Wait briefly to see if it loads
                time.sleep(5)
                
                # Check if we're on WhatsApp
                current_url = page.url
                if 'web.whatsapp.com' in current_url:
                    result['success'] = True
                    result['message'] = 'WhatsApp Web accessible'
                    
                    # Check if already logged in
                    chat_list = page.query_selector(self.SELECTORS['chat_list'])
                    result['logged_in'] = chat_list is not None
                    
                    if not result['logged_in']:
                        result['message'] = 'WhatsApp Web loaded. Please scan QR code to login.'
                else:
                    result['error'] = f'Navigated to: {current_url}'
                
                browser.close()
                
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Connection test failed: {e}")
        
        return result


# CLI interface
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='WhatsApp Watcher Skill')
    parser.add_argument('--vault', type=str, help='Path to Obsidian vault')
    parser.add_argument('--session', type=str, help='Path to session directory')
    parser.add_argument('--interval', type=int, default=30, help='Check interval in seconds')
    parser.add_argument('--keywords', type=str, nargs='+', help='Keywords to monitor')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--visible', action='store_true', help='Show browser (not headless)')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--test', action='store_true', help='Test connection')
    
    args = parser.parse_args()
    
    watcher = WhatsAppWatcherSkill(
        vault_path=args.vault,
        session_path=args.session,
        check_interval=args.interval,
        keywords=args.keywords,
        dry_run=args.dry_run,
        headless=not args.visible
    )
    
    if args.test:
        print("Testing WhatsApp Web connection...")
        result = watcher.test_connection()
        print(f"\nTest Results:")
        print(f"  Playwright: {'✓' if result['playwright_available'] else '✗'}")
        print(f"  Session exists: {'✓' if result['session_exists'] else '✗'}")
        print(f"  Success: {'✓' if result['success'] else '✗'}")
        if result.get('logged_in') is not None:
            print(f"  Logged in: {'✓' if result['logged_in'] else '✗'}")
        if result.get('message'):
            print(f"  Message: {result['message']}")
        if result.get('error'):
            print(f"  Error: {result['error']}")
        sys.exit(0 if result['success'] else 1)
    
    if args.once:
        print("Running single check cycle...")
        count = watcher.run_once()
        print(f"Created {count} action file(s)")
        sys.exit(0)
    
    print("Starting WhatsApp Watcher Skill...")
    print("Press Ctrl+C to stop")
    watcher.run_continuous()
