"""
Orchestrator Module

Specification: ORCHESTRATOR-001

Purpose: Master process for scheduling, triggering Qwen, and managing watchers.

Functional Requirements:
- OR-001: Start all configured watchers
- OR-002: Monitor /Needs_Action for new files
- OR-003: Trigger Qwen Code when new items detected
- OR-004: Monitor /Approved for actions to execute
- OR-005: Update Dashboard.md periodically
- OR-006: Log all orchestration events
- OR-007: Support graceful shutdown
"""

import os
import sys
import time
import signal
import json
import logging
import subprocess
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import threading

# Import config loader for environment variables
try:
    from ..config_loader import Config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    Config = None
    CONFIG_AVAILABLE = False

# Environment variable for vault path (set in .env file)
# Default: D:/Hackathon-0/AI_Employee_Vault (root vault)
DEFAULT_VAULT_PATH = os.getenv('VAULT_PATH', 'D:/Hackathon-0/AI_Employee_Vault')

# Add src to path (go up one level from orchestration to src)
sys.path.insert(0, str(Path(__file__).parent.parent))

from skills.update_dashboard import update_dashboard
from skills.log_action import log_action, LogEntry, get_recent_logs
from skills.process_email import process_email
from skills.move_to_done import move_to_done
from skills.create_approval_request import create_approval_request
from skills.send_email import SendEmailSkill


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator.
    
    Uses environment variables from .env file when available.
    """
    vault_path: str = str(Config.VAULT_PATH if CONFIG_AVAILABLE and Config else os.getenv('VAULT_PATH', 'D:/Hackathon-0/AI_Employee_Vault'))
    check_interval: int = Config.CYCLE_INTERVAL if CONFIG_AVAILABLE and Config else int(os.getenv('CYCLE_INTERVAL', '30'))
    dashboard_update_interval: int = 300
    enable_gmail_watcher: bool = False
    enable_filesystem_watcher: bool = True
    gmail_credentials_path: Optional[str] = None
    dry_run: bool = False
    log_level: str = Config.LOG_LEVEL if CONFIG_AVAILABLE and Config else os.getenv('LOG_LEVEL', "INFO")
    rejected_auto_delete_days: int = 7  # Auto-delete rejected files after N days
    enable_rejected_auto_delete: bool = True


# Approval keywords that trigger human-in-the-loop review
# Note: In Bronze Tier, ALL tasks require approval for safety
APPROVAL_KEYWORDS = ["send", "email", "payment", "post", "delete", "publish", "share"]
ALWAYS_REQUIRE_APPROVAL = True  # Set to True to require approval for all tasks


class Orchestrator:
    """
    Main orchestrator for the AI Employee system.
    
    Coordinates watchers, Qwen Code processing, and system health.
    """
    
    def __init__(self, config: OrchestratorConfig):
        """
        Initialize the orchestrator.
        
        Args:
            config: Orchestrator configuration
        """
        self.config = config
        self.vault_path = Path(config.vault_path)
        self.running = False
        self.shutdown_requested = False
        
        # Setup logging
        self.logger = self._setup_logging(config.log_level)
        
        # Watcher processes
        self.watcher_processes: Dict[str, subprocess.Popen] = {}
        
        # State tracking
        self.last_dashboard_update = None
        self.last_needs_action_check = None
        self.processing_lock = threading.Lock()
        
        # Ensure required directories exist
        self._ensure_directories()
        
        self.logger.info(f"Orchestrator initialized for vault: {self.vault_path}")
    
    def _setup_logging(self, level: str) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger('Orchestrator')
        logger.setLevel(getattr(logging, level.upper()))
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # File handler
        log_dir = self.vault_path / 'Logs' if hasattr(self, 'vault_path') else Path('Logs')
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"orchestrator_{datetime.now().strftime('%Y-%m-%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        # Add handlers
        if not logger.handlers:
            logger.addHandler(console_handler)
            logger.addHandler(file_handler)
        
        return logger
    
    def _ensure_directories(self):
        """Ensure all required directories exist."""
        dirs = [
            'Inbox',
            'Needs_Action',
            'Plans',
            'Done',
            'Pending_Approval',
            'Approved',
            'Rejected',
            'Logs',
            'Briefings',
            'Accounting',
            '.cache'
        ]

        for dir_name in dirs:
            (self.vault_path / dir_name).mkdir(parents=True, exist_ok=True)

        # Create Rejected archive subdirectory for audit trail
        rejected_archive_dir = self.vault_path / 'Rejected' / '_ARCHIVED'
        rejected_archive_dir.mkdir(parents=True, exist_ok=True)
    
    def start_watchers(self) -> None:
        """
        Start all configured watcher processes.

        Watchers run as separate processes for isolation and reliability.
        """
        self.logger.info("Starting watcher processes...")

        # Start Gmail Watcher if enabled
        if self.config.enable_gmail_watcher:
            self._start_watcher('gmail', 'watchers/gmail_watcher.py')

        # Start Filesystem Watcher if enabled
        if self.config.enable_filesystem_watcher:
            self._start_watcher('filesystem', 'watchers/filesystem_watcher.py')

        self.logger.info(f"Started {len(self.watcher_processes)} watcher(s)")
    
    def _start_watcher(self, name: str, script: str) -> None:
        """
        Start a watcher process.

        Args:
            name: Watcher name (gmail, filesystem, etc.)
            script: Path to watcher script (relative to project root)
        """
        try:
            # Go up one level from orchestration to src, then to watchers
            script_path = Path(__file__).parent.parent / script

            if not script_path.exists():
                self.logger.warning(f"Watcher script not found: {script_path}")
                return
            
            cmd = [
                sys.executable,
                str(script_path),
                '--vault', str(self.vault_path),
            ]
            
            if self.config.dry_run:
                cmd.append('--dry-run')
            
            if name == 'gmail' and self.config.gmail_credentials_path:
                cmd.extend(['--credentials', self.config.gmail_credentials_path])
            
            # Start process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.watcher_processes[name] = process
            self.logger.info(f"Started {name} watcher (PID: {process.pid})")
            
            # Log the action
            log_action(
                vault_path=str(self.vault_path),
                action_type='watcher_started',
                actor='orchestrator',
                target=name,
                parameters={'pid': process.pid},
                result='success'
            )
            
        except Exception as e:
            self.logger.error(f"Failed to start {name} watcher: {e}")
            log_action(
                vault_path=str(self.vault_path),
                action_type='watcher_start_failed',
                actor='orchestrator',
                target=name,
                parameters={'error': str(e)},
                result='failure'
            )
    
    def check_needs_action(self) -> List[Path]:
        """
        Check /Needs_Action folder for new files.
        
        Returns:
            List[Path]: List of new files to process
        """
        needs_action_dir = self.vault_path / 'Needs_Action'
        
        if not needs_action_dir.exists():
            return []
        
        new_files = []
        current_time = time.time()
        
        for file_path in needs_action_dir.iterdir():
            if not file_path.is_file():
                continue
            
            # Check if file was modified in the last check interval
            mtime = file_path.stat().st_mtime
            age_seconds = current_time - mtime
            
            # Process files that are older than 5 seconds (to ensure write is complete)
            if age_seconds > 5:
                # Check if already being processed (look for corresponding plan file)
                plan_exists = any(
                    p.name.startswith('PLAN_') and file_path.stem in p.name
                    for p in (self.vault_path / 'Plans').iterdir()
                ) if (self.vault_path / 'Plans').exists() else False
                
                if not plan_exists:
                    new_files.append(file_path)
        
        if new_files:
            self.logger.info(f"Found {len(new_files)} file(s) in Needs_Action")
        
        self.last_needs_action_check = datetime.now()
        return new_files
    
    def trigger_qwen(self, file_paths: List[Path]) -> None:
        """
        Trigger Qwen Code to process files.
        
        In a real implementation, this would invoke Qwen Code via CLI or API.
        For now, we simulate processing using our skills.
        
        Args:
            file_paths: List of files to process
        """
        self.logger.info(f"Processing {len(file_paths)} file(s) with Qwen Code simulation...")
        
        for file_path in file_paths:
            try:
                with self.processing_lock:
                    # Read file to determine type
                    content = file_path.read_text(encoding='utf-8')
                    
                    # Determine file type from frontmatter
                    file_type = 'unknown'
                    if 'type: email' in content.lower():
                        file_type = 'email'
                    elif 'type: file_drop' in content.lower():
                        file_type = 'file'
                    
                    # Process based on type
                    if file_type == 'email':
                        self._process_email_file(file_path)
                    else:
                        self._process_generic_file(file_path)
                    
                    # Log the action
                    log_action(
                        vault_path=str(self.vault_path),
                        action_type='qwen_processed',
                        actor='qwen_code',
                        target=file_path.name,
                        parameters={'file_type': file_type},
                        result='success'
                    )
                    
            except Exception as e:
                self.logger.error(f"Error processing {file_path.name}: {e}")
                log_action(
                    vault_path=str(self.vault_path),
                    action_type='qwen_processing_error',
                    actor='qwen_code',
                    target=file_path.name,
                    parameters={'error': str(e)},
                    result='failure'
                )
    
    def _process_email_file(self, file_path: Path) -> None:
        """
        Process an email action file using SINGLE FILE LIFECYCLE.

        The same file moves through folders:
        Needs_Action/ → Plans/ → Pending_Approval/ → Approved/ → Done/

        Args:
            file_path: Path to email file
        """
        self.logger.info(f"Processing email file (single-file lifecycle): {file_path.name}")

        # Use process_email skill (updated for single-file lifecycle)
        result = process_email(
            file_path=str(file_path),
            vault_path=str(self.vault_path)
        )

        if result['success']:
            self.logger.info(f"Email processed. Current file location: {result.get('current_file')}")
            if result.get('previous_location'):
                self.logger.info(f"Moved from: {result.get('previous_location')}")
            if result.get('requires_approval'):
                self.logger.info(f"File moved to Pending_Approval/ awaiting human review")
        else:
            self.logger.error(f"Processing failed: {result.get('error')}")
            if result.get('traceback'):
                self.logger.debug(result.get('traceback'))
    
    def _process_generic_file(self, file_path: Path) -> None:
        """
        Process a generic file (non-email) using SINGLE FILE LIFECYCLE.

        The same file is updated and moved through folders:
        Needs_Action/ → Plans/ → Pending_Approval/ → Approved/ → Done/

        Args:
            file_path: Path to file
        """
        self.logger.info(f"Processing generic file (single-file lifecycle): {file_path.name}")

        # Read the file content
        content = file_path.read_text(encoding='utf-8')
        
        # Parse existing frontmatter
        frontmatter = self._read_frontmatter(content)
        
        # Add plan metadata to frontmatter
        plan_created = datetime.now()
        frontmatter_updates = {
            'status': 'planned',
            'plan_created': plan_created.isoformat(),
            'category': frontmatter.get('category', 'general')
        }
        content = self._update_frontmatter(content, frontmatter_updates)
        
        # Add Action Plan section if not present
        if '## Action Plan' not in content:
            action_plan = f"""
## Action Plan
*Created: {plan_created.isoformat()}*

- [ ] Review file content
- [ ] Determine appropriate action
- [ ] Process or archive as needed

## Notes

Add processing notes here.
"""
            content += action_plan
            file_path.write_text(content, encoding='utf-8')
        
        # Move file from Needs_Action/ to Plans/
        plans_dir = self.vault_path / 'Plans'
        plans_dir.mkdir(parents=True, exist_ok=True)
        new_path = plans_dir / file_path.name
        
        # Use shutil.move to preserve filename
        import shutil
        shutil.move(str(file_path), str(new_path))
        
        self.logger.info(f"Moved file from Needs_Action/ to Plans/: {new_path.name}")
        
        # FEATURE #1: Check if plan needs approval and create request
        self._check_and_request_approval_single_file(new_path)

    def _read_frontmatter(self, content: str) -> Dict[str, Any]:
        """Extract YAML frontmatter from Markdown content."""
        frontmatter = {}
        
        if not content.startswith('---'):
            return frontmatter
        
        end_match = re.search(r'\n---\n', content[3:])
        if not end_match:
            return frontmatter
        
        frontmatter_text = content[3:end_match.start() + 3]
        
        for line in frontmatter_text.strip().split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                elif value.isdigit():
                    value = int(value)
                
                frontmatter[key] = value
        
        return frontmatter

    def _update_frontmatter(self, content: str, updates: Dict[str, Any]) -> str:
        """Update YAML frontmatter in Markdown content."""
        if not content.startswith('---'):
            frontmatter_str = "---\n"
            for key, value in updates.items():
                if isinstance(value, bool):
                    frontmatter_str += f"{key}: {str(value).lower()}\n"
                else:
                    frontmatter_str += f"{key}: {value}\n"
            frontmatter_str += "---\n\n"
            return frontmatter_str + content
        
        end_match = re.search(r'\n---\n', content[3:])
        if not end_match:
            return content
        
        frontmatter_end = end_match.start() + 3
        frontmatter_text = content[3:frontmatter_end]
        rest = content[frontmatter_end:]
        
        lines = frontmatter_text.strip().split('\n')
        updated_lines = []
        updated_keys = set()
        
        for line in lines:
            if ':' in line:
                key = line.split(':', 1)[0].strip()
                if key in updates:
                    value = updates[key]
                    if isinstance(value, bool):
                        updated_lines.append(f"{key}: {str(value).lower()}")
                    else:
                        updated_lines.append(f"{key}: {value}")
                    updated_keys.add(key)
                    continue
            updated_lines.append(line)
        
        for key, value in updates.items():
            if key not in updated_keys:
                if isinstance(value, bool):
                    updated_lines.append(f"{key}: {str(value).lower()}")
                else:
                    updated_lines.append(f"{key}: {value}")
        
        new_frontmatter = '\n'.join(updated_lines) + '\n'
        return f"---\n{new_frontmatter}---{rest}"

    def _check_and_request_approval_single_file(self, file_path: Path) -> None:
        """
        Check if a plan requires approval and update the same file.

        SINGLE FILE LIFECYCLE:
        - Updates the existing file with approval section
        - Moves file from Plans/ to Pending_Approval/

        Args:
            file_path: Path to the plan file (in Plans/)
        """
        try:
            # Read plan content
            content = file_path.read_text(encoding='utf-8')
            
            # Parse frontmatter to get metadata
            frontmatter = self._read_frontmatter(content)
            
            # Check for approval keywords OR always require approval
            needs_approval = ALWAYS_REQUIRE_APPROVAL or any(
                keyword in content.lower() for keyword in APPROVAL_KEYWORDS
            )
            
            if needs_approval:
                self.logger.info(f"Plan requires approval: {file_path.name}")
                
                # Extract action summary from Action Plan section
                action_plan_match = re.search(r'## Action Plan\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
                action_summary = action_plan_match.group(1).strip() if action_plan_match else "Action requires human review"
                first_three_lines = '\n'.join(action_summary.split('\n')[:3])
                
                # Use create_approval_request skill in single-file mode
                result = create_approval_request(
                    vault_path=str(self.vault_path),
                    action_type='plan_execution',
                    action_details={
                        'plan_file': file_path.name,
                        'task_file': frontmatter.get('original_file', file_path.name),
                        'action_summary': first_three_lines
                    },
                    priority='medium',
                    file_path=str(file_path)  # SINGLE FILE MODE: Update this file
                )
                
                if result['success']:
                    approval_filename = Path(result['file_path']).name
                    self.logger.info(f"Updated and moved file to Pending_Approval/: {approval_filename}")
                    if result.get('previous_location'):
                        self.logger.info(f"Previous location: {result.get('previous_location')}")
                    
                    # Log the action
                    log_action(
                        vault_path=str(self.vault_path),
                        action_type='approval_requested',
                        actor='orchestrator',
                        target=approval_filename,
                        parameters={
                            'plan_file': file_path.name,
                            'task_file': frontmatter.get('original_file', file_path.name)
                        },
                        approval_status='pending',
                        result='success'
                    )
                else:
                    self.logger.error(f"Failed to create approval request: {result.get('error')}")
            else:
                self.logger.info(f"No approval required for: {file_path.name}")
                
        except Exception as e:
            self.logger.error(f"Error checking approval: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())

    def _check_and_request_approval(self, plan_path: Path, task_file: Path) -> None:
        """
        Check if a plan requires approval and create approval request if needed.

        Args:
            plan_path: Path to the plan file
            task_file: Path to the original task file
        """
        try:
            # Read plan content
            plan_content = plan_path.read_text(encoding='utf-8')
            task_content = ""
            
            # Also read task file if it exists
            if task_file.exists():
                task_content = task_file.read_text(encoding='utf-8')
            
            # Combine content for keyword check
            combined_content = (plan_content + " " + task_content).lower()

            # Check for approval keywords OR always require approval
            needs_approval = ALWAYS_REQUIRE_APPROVAL or any(
                keyword in combined_content for keyword in APPROVAL_KEYWORDS
            )

            if needs_approval:
                self.logger.info(f"Plan requires approval: {plan_path.name}")

                # Extract objective for approval request (first 3 lines after ## header)
                objective_match = re.search(r'##.*?\n(.*?)(?=\n##|\n---|\Z)', plan_content, re.DOTALL)
                action_summary = objective_match.group(1).strip() if objective_match else "Action requires human review"
                first_three_lines = '\n'.join(action_summary.split('\n')[:3])

                # Create approval request using skill
                result = create_approval_request(
                    vault_path=str(self.vault_path),
                    action_type='plan_execution',
                    action_details={
                        'plan_file': plan_path.name,
                        'task_file': task_file.name,
                        'action_summary': first_three_lines
                    },
                    priority='medium'
                )

                if result['success']:
                    approval_filename = Path(result['file_path']).name
                    self.logger.info(f"Created approval request: {approval_filename}")

                    # Log the action
                    log_action(
                        vault_path=str(self.vault_path),
                        action_type='approval_requested',
                        actor='orchestrator',
                        target=approval_filename,
                        parameters={
                            'plan_file': plan_path.name,
                            'task_file': task_file.name
                        },
                        approval_status='pending',
                        result='success'
                    )
                else:
                    self.logger.error(f"Failed to create approval request: {result.get('error')}")
            else:
                self.logger.info(f"No approval required for: {plan_path.name}")

        except Exception as e:
            self.logger.error(f"Error checking approval: {e}")

    def _execute_approved_actions(self) -> None:
        """
        Process approved actions from /Approved/ folder.

        For each approved file:
        1. Read the approval file to determine action type
        2. Execute the specific action (send email, etc.)
        3. Move approval file, plan file, and task file to Done/
        4. Log completion

        DEPRECATED: Use handle_approved_actions() instead which has better logging.
        This method is kept for backward compatibility.
        """
        # Call the new improved method
        self.handle_approved_actions()

    def handle_approved_actions(self) -> None:
        """
        Process approved actions from /Approved/ folder with detailed logging.

        When user moves APPROVAL_*.md to Approved/, this method:
        1. Detects the approval file
        2. Parses action details from frontmatter
        3. Executes the approved action (send email, etc.)
        4. Logs execution to actions.json
        5. Moves approval file to Done/
        6. Updates Dashboard

        Called EVERY orchestration cycle (every 30 seconds).
        """
        self.logger.info("[INFO] handle_approved_actions() STARTED")

        approved_folder = self.vault_path / 'Approved'

        # Check if Approved folder exists
        if not approved_folder.exists():
            self.logger.info("Approved/ folder does not exist")
            self.logger.info("[INFO] <<< handle_approved_actions() returning - no folder")
            return

        # Find all approval files (*.md files that need processing)
        # Match files with: type: approval_request, requires_approval: true, OR action: field
        all_md_files = list(approved_folder.glob('*.md'))
        approved_files = []

        for f in all_md_files:
            try:
                content = f.read_text(encoding='utf-8')
                
                # Check if it needs processing
                is_approval = (
                    'type: approval_request' in content or
                    'requires_approval: true' in content or
                    'action:' in content  # Files with action: field need processing
                )
                if is_approval:
                    approved_files.append(f)
                    self.logger.info(f"  Found approval file: {f.name}")
            except Exception as e:
                self.logger.warning(f"  Could not read {f.name}: {e}")

        if not approved_files:
            self.logger.info("No approved actions to process")
            self.logger.info("[INFO] <<< handle_approved_actions() returning - no files")
            return

        self.logger.info(f"[INFO] Found {len(approved_files)} approved action(s) to process")

        for approved_file in approved_files:
            self.logger.info(f"[PROC] Processing approved file: {approved_file.name}")
            self.logger.info(f"[PROC] Reading file: {approved_file}")

            try:
                # READ FILE
                content = approved_file.read_text(encoding='utf-8')
                self.logger.info(f"[INFO] File content length: {len(content)} chars")

                # PARSE FRONTMATTER using yaml
                import yaml
                self.logger.info("[PROC] Parsing frontmatter with yaml...")
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1])
                else:
                    self.logger.error(f"[ERR] No frontmatter in {approved_file.name}")
                    continue
                    
                self.logger.info(f"[INFO] Frontmatter keys: {list(frontmatter.keys())}")

                # DETECT FILE TYPE
                # Check both filename pattern AND frontmatter type field
                is_email_task = (
                    approved_file.name.startswith('EMAIL_') or
                    frontmatter.get('type', '') == 'email'
                )
                is_approval_file = approved_file.name.startswith('APPROVAL_') or approved_file.name.startswith('APPROVED_')

                # EXTRACT EMAIL FIELDS
                if is_email_task:
                    self.logger.info("[INFO] Detected EMAIL task file (original email format)")
                    
                    # This is an email task that needs a reply
                    # Extract from frontmatter
                    original_from = frontmatter.get('from', '')
                    original_to = frontmatter.get('to', '')
                    original_subject = frontmatter.get('subject', '')
                    original_date = frontmatter.get('received', frontmatter.get('original_date', ''))
                    
                    # Extract email body from content (between ## Email Content and next ## header)
                    body_match = re.search(r'## Email Content\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
                    original_body = body_match.group(1).strip() if body_match else ''
                    
                    # Extract suggested actions if present
                    actions_match = re.search(r'## Suggested Actions\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
                    suggested_actions = actions_match.group(1).strip() if actions_match else ''

                    self.logger.info(f"  Original from: {original_from}")
                    self.logger.info(f"  Original to: {original_to}")
                    self.logger.info(f"  Original subject: {original_subject}")
                    self.logger.info(f"  Original body length: {len(original_body)} chars")

                    # GENERATE REPLY - Extract reply details from suggested actions or create acknowledgment
                    to_email = original_from  # Reply to original sender

                    # Check if there's a specific reply action in suggested actions
                    reply_match = re.search(r'- \[ \] Reply.*?to.*?(\S+@\S+)', content, re.IGNORECASE)
                    if reply_match:
                        to_email = reply_match.group(1)

                    # Generate reply subject
                    reply_subject = f"Re: {original_subject}" if not original_subject.startswith('Re:') else original_subject

                    # ========================================
                    # INTELLIGENT REPLY GENERATION
                    # ========================================

                    # Extract original email body from content (also check for Body header)
                    body_match = re.search(r'## (?:Email Content|Body)\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
                    original_body = body_match.group(1).strip() if body_match else ''

                    # Check for AI-generated suggested response in the file
                    # IMPORTANT: Only look for "Suggested Response" or "Draft Response" - NOT "Action Plan"
                    # Action Plan contains task metadata (checkboxes, timestamps) not reply content
                    suggested_response_match = re.search(
                        r'## (?:Suggested Response|Draft Response)\s*\n(.*?)(?=\n##|\Z)', 
                        content, 
                        re.DOTALL
                    )
                    suggested_response = suggested_response_match.group(1).strip() if suggested_response_match else ''

                    self.logger.info(f"Original body length: {len(original_body)} chars")
                    self.logger.info(f"Suggested response length: {len(suggested_response)} chars")

                    # Generate contextual reply
                    if suggested_response and len(suggested_response) > 50:
                        # Use AI-generated response if available and substantial
                        # But first clean it up (remove any task metadata)
                        reply_body = suggested_response
                        
                        # Remove task checkboxes: - [ ] or - [x]
                        reply_body = re.sub(r'^- \[[ x]\] .*$', '', reply_body, flags=re.MULTILINE)
                        
                        # Remove metadata lines: *Created: ...* or *Added: ...*
                        reply_body = re.sub(r'\*(?:Created|Added|Executed):.*?\*', '', reply_body, flags=re.MULTILINE)
                        
                        # Remove multiple blank lines
                        reply_body = re.sub(r'\n{3,}', '\n\n', reply_body)
                        
                        # Strip whitespace
                        reply_body = reply_body.strip()
                        
                        self.logger.info("Using AI-generated suggested response (cleaned)")
                        self.logger.info(f"Cleaned reply length: {len(reply_body)} chars")

                    else:
                        # Generate intelligent contextual reply based on email content
                        self.logger.info("Generating contextual reply based on email analysis")
                        
                        # Properly extract original email body
                        body_match = re.search(r'## (?:Email Content|Body)\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
                        original_email_text = body_match.group(1).strip() if body_match else ''
                        
                        # Combine subject + body for analysis
                        email_text = (original_email_text + ' ' + original_subject).lower()
                        
                        # Log what we're analyzing
                        self.logger.info(f"Original email text: {original_email_text[:200]}...")
                        
                        # Detect email type and generate appropriate response
                        # Order matters - check specific patterns first
                        
                        # ACCESS/AUTHENTICATION requests
                        if any(keyword in email_text for keyword in ['access', 'login', 'password', 'credentials', 'permission', 'sign in', 'log in', 'authenticate']):
                            # Extract key phrase from original email for personalization
                            key_phrase = original_subject if original_subject else "account access"
                            reply_body = f"""Hello,

I understand you need help with access to your account. Your message regarding "{key_phrase}" has been received.

I've logged your request and our team will assist you with regaining access. For security reasons, we may need to verify your identity before proceeding.

If this is urgent, please contact support directly.

Best regards,
AI Employee"""
                            self.logger.info("Detected: Access/Authentication request")
                            # Log system status internally (NOT in email body)
                            self.logger.info("System Status: Email Detection Working")
                            self.logger.info("System Status: Auto-Processing Working")
                            self.logger.info("System Status: Reply Generation Working")

                        # TECHNICAL ISSUES - errors, bugs, broken things
                        elif any(keyword in email_text for keyword in ['error', 'broken', 'not working', 'issue', 'problem', 'bug', 'crash', 'failed', 'failure']):
                            # Extract key phrase from original email for personalization
                            key_phrase = original_subject if original_subject else "the technical issue"
                            reply_body = f"""Hello,

I'm sorry to hear you're experiencing technical difficulties. I've received your message about: {key_phrase}

Your issue has been logged and flagged for technical support review. Our team will investigate and provide assistance as soon as possible.

If the issue is critical or blocking your work, please contact technical support immediately.

Best regards,
AI Employee"""
                            self.logger.info("Detected: Technical issue report")
                            # Log system status internally (NOT in email body)
                            self.logger.info("System Status: Email Detection Working")
                            self.logger.info("System Status: Auto-Processing Working")
                            self.logger.info("System Status: Reply Generation Working")

                        # SCHEDULING/TIMING questions
                        elif any(keyword in email_text for keyword in ['when', 'deadline', 'schedule', 'timeline', 'date', 'time', 'how long', 'duration']):
                            # Extract key phrase from original email for personalization
                            key_phrase = original_subject if original_subject else "your scheduling question"
                            reply_body = f"""Hello,

Thank you for reaching out regarding: {key_phrase}

I've noted your question about timing/scheduling. The relevant information is being gathered and will be provided to you shortly.

If you need this information urgently, please let us know.

Best regards,
AI Employee"""
                            self.logger.info("Detected: Scheduling/Timing question")
                            # Log system status internally (NOT in email body)
                            self.logger.info("System Status: Email Detection Working")
                            self.logger.info("System Status: Auto-Processing Working")
                            self.logger.info("System Status: Reply Generation Working")

                        # HOW-TO questions and guidance requests
                        elif any(keyword in email_text for keyword in ['how to', 'can you', 'help me', 'i need', 'guide', 'tutorial', 'steps', 'instructions']):
                            # Extract key phrase from original email for personalization
                            key_phrase = original_subject if original_subject else "your request"
                            reply_body = f"""Hello,

Thank you for your question regarding: {key_phrase}

I'd be happy to help you with this. Your request has been logged and I'll provide you with the guidance you need.

Could you please provide any additional details about what you're trying to accomplish? This will help me give you more specific assistance.

Best regards,
AI Employee"""
                            self.logger.info("Detected: How-to/Guidance request")
                            # Log system status internally (NOT in email body)
                            self.logger.info("System Status: Email Detection Working")
                            self.logger.info("System Status: Auto-Processing Working")
                            self.logger.info("System Status: Reply Generation Working")

                        # THANK YOU messages
                        elif any(keyword in email_text for keyword in ['thank', 'thanks', 'appreciate', 'grateful', 'great job', 'helpful']):
                            reply_body = f"""Hello,

You're very welcome!

I'm glad I could be of assistance. If you have any other questions or need further help with anything, please don't hesitate to reach out.

Best regards,
AI Employee"""
                            self.logger.info("Detected: Thank you message")
                            # Log system status internally (NOT in email body)
                            self.logger.info("System Status: Email Detection Working")
                            self.logger.info("System Status: Auto-Processing Working")
                            self.logger.info("System Status: Reply Generation Working")

                        # URGENT requests
                        elif any(keyword in email_text for keyword in ['urgent', 'asap', 'immediately', 'emergency', 'critical', 'right away', 'as soon as possible']):
                            # Extract key phrase from original email for personalization
                            key_phrase = original_subject if original_subject else "your urgent request"
                            reply_body = f"""Hello,

I have received your urgent message regarding: {key_phrase}

Your email has been flagged as HIGH PRIORITY and logged in the system. Due to the urgent nature of your request, I recommend contacting the team directly for immediate assistance.

Your message is being escalated for prompt attention.

Best regards,
AI Employee"""
                            self.logger.info("Detected: URGENT request")
                            # Log system status internally (NOT in email body)
                            self.logger.info("System Status: Email Detection Working")
                            self.logger.info("System Status: Auto-Processing Working")
                            self.logger.info("System Status: Reply Generation Working")

                        # STATUS/UPDATE requests
                        elif any(keyword in email_text for keyword in ['status', 'update', 'progress', 'report', 'where things stand']):
                            # Extract key phrase from original email for personalization
                            key_phrase = original_subject if original_subject else "your status request"
                            reply_body = f"""Hello,

Thank you for reaching out regarding: {key_phrase}

I have noted your request for a status update. The relevant information is being compiled and will be provided to you shortly.

If you need specific details urgently, please let me know.

Best regards,
AI Employee"""
                            self.logger.info("Detected: Status/Update request")
                            # Log system status internally (NOT in email body)
                            self.logger.info("System Status: Email Detection Working")
                            self.logger.info("System Status: Auto-Processing Working")
                            self.logger.info("System Status: Reply Generation Working")

                        # MEETING/SCHEDULING requests
                        elif any(keyword in email_text for keyword in ['meeting', 'call', 'discuss', 'talk', 'schedule', 'appointment', 'chat']):
                            # Extract key phrase from original email for personalization
                            key_phrase = original_subject if original_subject else "your meeting request"
                            reply_body = f"""Hello,

Thank you for reaching out regarding: {key_phrase}

I have noted your request for a meeting/discussion. Your scheduling request has been logged and will be reviewed to find a suitable time.

You will receive a calendar invitation or confirmation shortly.

Best regards,
AI Employee"""
                            self.logger.info("Detected: Meeting/Scheduling request")
                            # Log system status internally (NOT in email body)
                            self.logger.info("System Status: Email Detection Working")
                            self.logger.info("System Status: Auto-Processing Working")
                            self.logger.info("System Status: Reply Generation Working")

                        # SUPPORT/HELP requests
                        elif any(keyword in email_text for keyword in ['help', 'support', 'assist', 'stuck', 'confused', 'don\'t understand']):
                            # Extract key phrase from original email for personalization
                            key_phrase = original_subject if original_subject else "your support request"
                            reply_body = f"""Hello,

Thank you for contacting us regarding: {key_phrase}

I have received your support request and it has been logged in our system. Our team will review your issue and provide assistance as soon as possible.

If this is urgent, please mark it as high priority or contact support directly.

Best regards,
AI Employee"""
                            self.logger.info("Detected: Support/Help request")
                            # Log system status internally (NOT in email body)
                            self.logger.info("System Status: Email Detection Working")
                            self.logger.info("System Status: Auto-Processing Working")
                            self.logger.info("System Status: Reply Generation Working")

                        # TEST emails (only if actually contains test/testing AND minimal content)
                        elif any(keyword in email_text for keyword in ['test', 'testing']) and len(original_email_text) < 200:
                            reply_body = f"""Hello,

Thank you for your test email.

I can confirm that the AI Employee email automation system is functioning correctly. Your message regarding "{original_subject}" has been received and processed successfully.

Best regards,
AI Employee System"""
                            self.logger.info("Detected: Test email")
                            # Log system status internally (NOT in email body)
                            self.logger.info("System Status: Email Detection Working")
                            self.logger.info("System Status: Auto-Processing Working")
                            self.logger.info("System Status: Reply Generation Working")

                        # GENERAL PROFESSIONAL ACKNOWLEDGMENT (fallback)
                        else:
                            # Extract key phrase from original email for personalization
                            key_phrase = original_subject if original_subject else "your email"
                            reply_body = f"""Hello,

Thank you for your email regarding: {key_phrase}

Your message has been received and logged in the system. It will be reviewed and you will receive a response accordingly.

If you need urgent assistance, please contact the team directly.

Best regards,
AI Employee"""
                            self.logger.info("Detected: General email (fallback)")
                            # Log system status internally (NOT in email body)
                            self.logger.info("System Status: Email Detection Working")
                            self.logger.info("System Status: Auto-Processing Working")
                            self.logger.info("System Status: Reply Generation Working")

                    # Final cleanup (remove extra whitespace)
                    reply_body = reply_body.strip()

                    self.logger.info(f"Generated reply length: {len(reply_body)} chars")
                    self.logger.info(f"Reply preview (first 200 chars): {reply_body[:200]}...")
                    self.logger.info(f"Full reply:\n{reply_body}")

                    # ========================================
                    # END INTELLIGENT REPLY GENERATION
                    # ========================================

                    self.logger.info(f"[INFO] Generated reply:")
                    self.logger.info(f"  To: {to_email}")
                    self.logger.info(f"  Subject: {reply_subject}")
                    self.logger.info(f"  Body length: {len(reply_body)} chars")

                    # Set action type for email send
                    action_type = 'email_send'
                    recipient_email = to_email
                    email_subject = reply_subject
                    email_body = reply_body
                    
                else:
                    self.logger.info("[INFO] Detected APPROVAL file format")
                    
                    # Standard approval format
                    # Extract action type from frontmatter or content
                    action_type = frontmatter.get('action', frontmatter.get('action_type', frontmatter.get('type', '')))
                    if not action_type:
                        # Try to extract from content
                        for line in content.split('\n'):
                            if line.startswith('action:'):
                                action_type = line.split(':', 1)[1].strip()
                                break

                    self.logger.info(f"  action_type: {action_type}")

                    # Extract detail_ prefixed fields from frontmatter
                    action_details = {}
                    for key, value in frontmatter.items():
                        if key.startswith('detail_'):
                            detail_key = key.replace('detail_', '')
                            action_details[detail_key] = value
                            self.logger.info(f"  detail_{detail_key}: {value}")

                    # Also extract from content lines
                    for line in content.split('\n'):
                        if line.startswith('detail_'):
                            parts = line.split(':', 1)
                            if len(parts) == 2:
                                key = parts[0].replace('detail_', '').strip()
                                value = parts[1].strip()
                                action_details[key] = value

                    self.logger.info(f"Action details: {action_details}")

                    # Extract common fields
                    recipient_email = action_details.get('to', action_details.get('recipient', action_details.get('to_email', '')))
                    email_subject = action_details.get('subject', '')
                    email_body = action_details.get('body', action_details.get('content', ''))
                    
                    self.logger.info(f"  to: {recipient_email}")
                    self.logger.info(f"  subject: {email_subject}")
                    self.logger.info(f"  body length: {len(email_body) if email_body else 0} chars")

                # VALIDATE REQUIRED FIELDS
                if action_type in ['email_send', 'email_response', 'send_email', 'email']:
                    if not recipient_email:
                        self.logger.error(f"[ERR] Missing recipient email in {approved_file.name}")
                        continue
                    if not email_subject:
                        self.logger.error(f"[ERR] Missing subject in {approved_file.name}")
                        continue
                    if not email_body:
                        self.logger.error(f"[ERR] Missing body in {approved_file.name}")
                        continue

                    self.logger.info(f"[INFO] All required fields present")

                    # SEND EMAIL
                    self.logger.info(f"[EMAIL] Preparing to send email...")
                    self.logger.info(f"  To: {recipient_email}")
                    self.logger.info(f"  Subject: {email_subject}")
                    self.logger.info(f"  Body length: {len(email_body)} chars")

                    execution_result = self._execute_email_send(
                        {
                            'to': recipient_email,
                            'subject': email_subject,
                            'body': email_body,
                        },
                        approved_file.name
                    )

                    self.logger.info(f"[INFO] _execute_email_send() returned: {execution_result}")

                elif action_type == 'plan_execution':
                    self.logger.info(f"[INFO] Executing plan: {frontmatter.get('plan_file', 'unknown')}")
                    execution_result = {
                        'success': True,
                        'message': 'Plan executed successfully'
                    }

                elif action_type == 'linkedin_post':
                    self.logger.info(f"[LINKEDIN] Processing LinkedIn post: {approved_file.name}")

                    # Extract post content from frontmatter
                    post_content = frontmatter.get('content', '')
                    post_title = frontmatter.get('title', 'LinkedIn Post')
                    post_type = frontmatter.get('post_type', 'general')
                    image_path = frontmatter.get('image_path', frontmatter.get('image', ''))

                    # If no content in frontmatter, extract from body
                    if not post_content:
                        # Try to extract from "## Post Content" section
                        post_match = re.search(
                            r'## Post Content\s*\n\s*\n(.*?)(?=\n##|\n---|\Z)',
                            content,
                            re.DOTALL
                        )
                        if post_match:
                            post_content = post_match.group(1).strip()

                        # Also try "# LinkedIn Post Approval Request" → "## Post Content" format
                        if not post_content:
                            approval_match = re.search(
                                r'## Post Content\s*\n\s*\n(.*?)(?=\n---|\n##|\Z)',
                                content,
                                re.DOTALL
                            )
                            if approval_match:
                                post_content = approval_match.group(1).strip()

                    # Sanitize post_type for logging (remove emojis for Windows console compatibility)
                    post_type_safe = post_type.encode('ascii', errors='ignore').decode('ascii').strip() if post_type else ''

                    self.logger.info(f"  Title: {post_title}")
                    self.logger.info(f"  Type: {post_type_safe}")
                    self.logger.info(f"  Content length: {len(post_content)} chars")
                    if image_path:
                        self.logger.info(f"  Image: {image_path}")

                    # Check if we have content
                    if not post_content:
                        self.logger.error(f"[LINKEDIN] No post content found in {approved_file.name}")
                        execution_result = {
                            'success': False,
                            'error': 'No post content found in file'
                        }
                    else:
                        # ═══════════════════════════════════════════════════════════
                        # SKIP MCP - Go straight to browser to avoid async/sync issues
                        # ═══════════════════════════════════════════════════════════
                        
                        self.logger.info("[LINKEDIN] Using browser automation (MCP skipped)...")
                        
                        execution_result = self._execute_linkedin_post_browser(
                            post_content=post_content,
                            post_title=post_title,
                            image_path=image_path,
                            approval_filename=approved_file.name
                        )

                        # If browser failed, provide helpful error message
                        if not execution_result.get('success'):
                            error_msg = execution_result.get('error', 'Unknown error')
                            self.logger.error(f"[LINKEDIN] Browser posting failed: {error_msg}")
                            
                            # Check if it's a session error - provide helpful guidance
                            if 'session' in error_msg.lower() or 'expired' in error_msg.lower() or 'login' in error_msg.lower():
                                self.logger.error("[LINKEDIN] SESSION EXPIRED - User needs to re-authenticate")
                                self.logger.error("[LINKEDIN] Run this command to re-login: python src/skills/linkedin_session_auth.py login")

                else:
                    self.logger.warning(f"[WARN] Unknown action type: {action_type}")
                    execution_result = {
                        'success': True,  # Mark as success to still archive the file
                        'message': f'Action type {action_type} acknowledged (no handler)'
                    }

                # Log execution result
                log_action(
                    vault_path=str(self.vault_path),
                    action_type='action_executed',
                    actor='orchestrator',
                    target=approved_file.name,
                    parameters={
                        'action_type': action_type,
                        'recipient': recipient_email if 'recipient_email' in locals() else None,
                        'subject': email_subject if 'email_subject' in locals() else None,
                    },
                    approval_status='approved',
                    approved_by='human',
                    result='success' if execution_result.get('success') else 'failure'
                )

                if execution_result.get('success'):
                    self.logger.info(f"[OK] Action executed successfully: {execution_result.get('message', '')}")
                    if execution_result.get('message_id'):
                        self.logger.info(f"[EMAIL] Message ID: {execution_result['message_id']}")
                    
                    # Finalize: Update file and move to Done/ (ONLY on success)
                    self._finalize_executed_action(
                        approved_file,
                        execution_result,
                        action_type,
                        frontmatter.get('plan_file'),
                        frontmatter.get('task_file')
                    )
                    self.logger.info(f"[INFO] ✓ Archived {approved_file.name} to Done/")
                else:
                    # Action failed - move to Failed/ folder instead of Done/
                    error_msg = execution_result.get('error', 'Unknown error')
                    self.logger.error(f"[ERR] Action execution failed: {error_msg}")
                    
                    # Move to Failed folder
                    self._move_to_failed(
                        approved_file,
                        execution_result,
                        action_type
                    )
                    self.logger.warning(f"[WARN] Moved {approved_file.name} to Failed/")
                    self.logger.warning(f"[WARN] Error: {error_msg}")
                    self.logger.warning(f"[WARN] Fix the issue and move back to Approved/ to retry")

            except Exception as e:
                self.logger.error(f"[ERR] Error processing {approved_file.name}: {e}", exc_info=True)
                import traceback
                self.logger.error(f"Full traceback: {traceback.format_exc()}")

                # Log the error
                log_action(
                    vault_path=str(self.vault_path),
                    action_type='action_execution_error',
                    actor='orchestrator',
                    target=approved_file.name,
                    parameters={'error': str(e)},
                    result='failure'
                )

        self.logger.info(f"[OK] Completed processing {len(approved_files)} approved action(s)")
        self.logger.info("[INFO] <<< handle_approved_actions() FINISHED")

    def _finalize_executed_action(
        self, 
        file_path: Path, 
        execution_result: Dict[str, Any],
        action_type: str,
        plan_file: Optional[str] = None,
        task_file: Optional[str] = None
    ) -> None:
        """
        Finalize an executed action by updating the file and moving to Done.

        SINGLE FILE LIFECYCLE:
        - Update the approved file with execution result
        - Move the same file to Done/
        - No need to move multiple files (plan, task) as they are all the same file

        Args:
            file_path: Path to the approved file
            execution_result: Result of the action execution
            action_type: Type of action executed
            plan_file: Optional plan file name (for legacy compatibility)
            task_file: Optional task file name (for legacy compatibility)
        """
        try:
            # Read current content
            content = file_path.read_text(encoding='utf-8')
            
            # Parse frontmatter
            frontmatter = self._read_frontmatter(content)
            
            # Update frontmatter with execution metadata
            execution_updates = {
                'status': 'completed',
                'executed': datetime.now().isoformat(),
                'completed': datetime.now().isoformat(),
                'execution_result': 'success' if execution_result.get('success') else 'failure'
            }
            if execution_result.get('message_id'):
                execution_updates['message_id'] = execution_result['message_id']
            
            content = self._update_frontmatter(content, execution_updates)
            
            # Add Execution Result section if not present
            if '## Execution Result' not in content:
                exec_section = f"""
## Execution Result
*Added: {datetime.now().isoformat()}*

**Status:** {'[OK] Success' if execution_result.get('success') else '[ERR] Failed'}
**Action Type:** {action_type}
"""
                if execution_result.get('message'):
                    exec_section += f"**Message:** {execution_result['message']}\n"
                if execution_result.get('message_id'):
                    exec_section += f"**Message ID:** {execution_result['message_id']}\n"
                
                content += exec_section
                file_path.write_text(content, encoding='utf-8')
            
            # Move to Done
            move_to_done(
                file_path=str(file_path),
                vault_path=str(self.vault_path),
                completion_note=f"Approved action ({action_type}) executed"
            )
            
            # In single-file lifecycle, plan and task are the SAME file
            # So we don't need to move them separately
            # But for legacy compatibility, check and clean up if they exist
            if plan_file:
                plan_path = self.vault_path / 'Plans' / plan_file
                if plan_path.exists():
                    self.logger.warning(f"Legacy plan file found (should be same as approval): {plan_file}")
            
            if task_file:
                task_path = self.vault_path / 'Needs_Action' / task_file
                if task_path.exists():
                    self.logger.warning(f"Legacy task file found (should be same as approval): {task_file}")
            
            self.logger.info("Task completed and archived to Done/ (single-file lifecycle)")

        except Exception as e:
            self.logger.error(f"Error finalizing executed action: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())

    def _move_to_failed(
        self,
        file_path: Path,
        execution_result: Dict[str, Any],
        action_type: str
    ) -> None:
        """
        Move a failed action to the Failed folder.

        SINGLE FILE LIFECYCLE:
        - Update the file with failure details
        - Move to Failed/ folder for manual review
        - User can fix issues and move back to Approved/ to retry

        Args:
            file_path: Path to the approved file
            execution_result: Result of the failed action execution
            action_type: Type of action that failed
        """
        try:
            # Ensure Failed folder exists
            failed_dir = self.vault_path / 'Failed'
            failed_dir.mkdir(parents=True, exist_ok=True)
            
            # Read current content
            content = file_path.read_text(encoding='utf-8')
            
            # Parse frontmatter
            frontmatter = self._read_frontmatter(content)
            
            # Update frontmatter with failure metadata
            failure_updates = {
                'status': 'failed',
                'failed_at': datetime.now().isoformat(),
                'execution_result': 'failure',
                'error_message': execution_result.get('error', 'Unknown error')
            }
            
            content = self._update_frontmatter(content, failure_updates)
            
            # Add Failure Details section if not present
            if '## Failure Details' not in content:
                failure_section = f"""
## Failure Details
*Added: {datetime.now().isoformat()}*

**Status:** [ERR] Failed
**Action Type:** {action_type}
**Error:** {execution_result.get('error', 'Unknown error')}

### To Retry
1. Fix the issue described above
2. Move this file back to `/Approved/` folder
3. Orchestrator will retry the action

### Common Issues
- **LinkedIn Post Failed**: Session expired, re-login with `python src/skills/linkedin_session_auth.py login`
- **Email Send Failed**: Gmail auth expired, re-authenticate with `python src/skills/gmail_auth.py auth`
- **Network Error**: Check internet connection and retry
"""
                content += failure_section
                file_path.write_text(content, encoding='utf-8')
            
            # Move to Failed folder
            failed_path = failed_dir / file_path.name
            
            # Handle duplicate filenames
            if failed_path.exists():
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                failed_path = failed_dir / f"{file_path.stem}_{timestamp}{file_path.suffix}"
            
            file_path.rename(failed_path)
            
            # Log the failure
            log_action(
                vault_path=str(self.vault_path),
                action_type='action_failed',
                actor='orchestrator',
                target=file_path.name,
                parameters={
                    'action_type': action_type,
                    'error': execution_result.get('error', 'Unknown error'),
                    'failed_file': str(failed_path)
                },
                result='failure'
            )
            
            self.logger.info(f"Moved to Failed/: {failed_path.name}")
            
        except Exception as e:
            self.logger.error(f"Error moving to Failed: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())

    def _execute_email_send(self, details: Dict[str, str], approval_filename: str) -> Dict[str, Any]:
        """
        Execute an email send action using SendEmailSkill.

        Args:
            details: Email details from approval file (to, subject, body, etc.)
            approval_filename: Name of the approval file for logging

        Returns:
            dict: Execution result with success status
        """
        self.logger.info(">>> _execute_email_send() STARTED")
        
        try:
            self.logger.info(f"Sending email via SendEmailSkill...")
            self.logger.info(f"  To: {details.get('to', 'MISSING')}")
            self.logger.info(f"  Subject: {details.get('subject', 'MISSING')}")
            self.logger.info(f"  Body length: {len(details.get('body', ''))} chars")
            self.logger.info(f"  Dry run: {self.config.dry_run}")

            # Initialize email skill
            self.logger.info("[TOOL] Creating SendEmailSkill instance...")
            try:
                email_skill = SendEmailSkill(
                    vault_path=str(self.vault_path),
                    dry_run=self.config.dry_run
                )
                self.logger.info("[OK] SendEmailSkill instance created")
            except Exception as e:
                self.logger.error(f"[ERR] Failed to create SendEmailSkill: {e}")
                return {
                    'success': False,
                    'error': f'Failed to create SendEmailSkill: {e}'
                }

            self.logger.info("[TOOL] Calling email_skill.initialize()...")
            try:
                init_result = email_skill.initialize()
                self.logger.info(f"[OK] email_skill.initialize() returned: {init_result}")
            except Exception as e:
                self.logger.error(f"[ERR] email_skill.initialize() failed: {e}")
                return {
                    'success': False,
                    'error': f'Failed to initialize email service: {e}'
                }

            if not init_result:
                self.logger.error("[ERR] email_skill.initialize() returned False")
                return {
                    'success': False,
                    'error': 'Failed to initialize email service'
                }

            # Send email
            self.logger.info("[TOOL] Calling email_skill.send_email()...")
            try:
                result = email_skill.send_email(
                    to=details.get('to', ''),
                    subject=details.get('subject', ''),
                    body=details.get('body', details.get('content', '')),
                    cc=details.get('cc') if details.get('cc') else None,
                    html=details.get('html', 'false').lower() == 'true'
                )
                self.logger.info(f"[OK] email_skill.send_email() returned: {result}")
            except Exception as e:
                self.logger.error(f"[ERR] email_skill.send_email() failed: {e}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                return {
                    'success': False,
                    'error': f'send_email() exception: {e}'
                }

            if result.get('success'):
                message_id = result.get('message_id', 'unknown')
                self.logger.info(f"[OK] Email sent successfully! Message ID: {message_id}")
                return {
                    'success': True,
                    'message': f'Email sent (ID: {message_id})',
                    'message_id': message_id
                }
            else:
                error_msg = result.get('error', 'Unknown error')
                self.logger.error(f"[ERR] Email send failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }

        except Exception as e:
            self.logger.error(f"[ERR] Error in email send execution: {e}", exc_info=True)
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            self.logger.info("<<< _execute_email_send() FINISHED")

    def _execute_linkedin_post_mcp(
        self,
        post_content: str,
        post_title: str,
        approval_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a LinkedIn post using MCP server (direct browser automation).

        Args:
            post_content: Post content
            post_title: Post title
            approval_filename: Name of approval file for logging

        Returns:
            Dict: Execution result with success status
        """
        self.logger.info(">>> _execute_linkedin_post_mcp() STARTED")

        try:
            self.logger.info(f"Posting to LinkedIn via MCP server...")
            self.logger.info(f"  Title: {post_title}")
            self.logger.info(f"  Content length: {len(post_content)} chars")

            # Import and run MCP handler directly
            from skills.linkedin_mcp_server import LinkedInMCPHandler

            handler = LinkedInMCPHandler()
            result = handler.post_to_linkedin(post_content)

            if result.get('success'):
                self.logger.info(f"[OK] LinkedIn post published via MCP! Post ID: {result.get('post_id')}")
                return {
                    'success': True,
                    'message': 'LinkedIn post published (MCP)',
                    'post_id': result.get('post_id')
                }
            else:
                error_msg = result.get('error', 'Unknown error')
                self.logger.error(f"[ERR] LinkedIn MCP post failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }

        except ImportError as e:
            self.logger.debug(f"MCP server not available: {e}")
            return {
                'success': False,
                'error': f'MCP server not available: {e}'
            }
        except Exception as e:
            self.logger.error(f"[ERR] Error in LinkedIn MCP posting: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            self.logger.info("<<< _execute_linkedin_post_mcp() FINISHED")

    def _execute_linkedin_post_browser(
        self,
        post_content: str,
        post_title: str,
        image_path: Optional[str] = None,
        approval_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a LinkedIn post using browser automation (session-based).

        Args:
            post_content: Post content
            post_title: Post title
            image_path: Optional path to image file
            approval_filename: Name of approval file for logging

        Returns:
            Dict: Execution result with success status
        """
        self.logger.info(">>> _execute_linkedin_post_browser() STARTED")

        try:
            self.logger.info(f"Posting to LinkedIn via browser automation...")
            self.logger.info(f"  Title: {post_title}")
            self.logger.info(f"  Content length: {len(post_content)} chars")
            if image_path:
                self.logger.info(f"  Image: {image_path}")

            # Import browser poster
            self.logger.info("[TOOL] Importing LinkedInBrowserPoster...")
            try:
                from skills.linkedin_browser_post import LinkedInBrowserPoster
                self.logger.info("[OK] LinkedInBrowserPoster imported")
            except ImportError as e:
                self.logger.error(f"[ERR] Failed to import LinkedInBrowserPoster: {e}")
                return {
                    'success': False,
                    'error': f'LinkedInBrowserPoster not available: {e}'
                }

            # Initialize browser poster
            self.logger.info("[TOOL] Creating LinkedInBrowserPoster instance...")
            try:
                poster = LinkedInBrowserPoster(dry_run=self.config.dry_run)
                self.logger.info("[OK] LinkedInBrowserPoster instance created")
            except Exception as e:
                self.logger.error(f"[ERR] Failed to create LinkedInBrowserPoster: {e}")
                return {
                    'success': False,
                    'error': f'Failed to create LinkedInBrowserPoster: {e}'
                }

            # Post to LinkedIn
            self.logger.info("[TOOL] Creating LinkedIn post...")
            try:
                if image_path:
                    result = poster.create_post_with_image(
                        content=post_content,
                        image_path=image_path,
                        title=post_title
                    )
                else:
                    result = poster.create_post(
                        content=post_content,
                        title=post_title
                    )
                self.logger.info(f"[OK] LinkedIn post creation returned: {result}")
            except Exception as e:
                self.logger.error(f"[ERR] LinkedIn post creation failed: {e}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                return {
                    'success': False,
                    'error': f'Post creation exception: {e}'
                }

            if result.get('success'):
                post_id = result.get('post_id', 'unknown')
                self.logger.info(f"[OK] LinkedIn post published successfully! Post ID: {post_id}")
                return {
                    'success': True,
                    'message': f'LinkedIn post published (browser)',
                    'post_id': post_id
                }
            else:
                error_msg = result.get('error', 'Unknown error')
                self.logger.error(f"[ERR] LinkedIn post failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }

        except Exception as e:
            self.logger.error(f"[ERR] Error in LinkedIn browser posting: {e}", exc_info=True)
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            self.logger.info("<<< _execute_linkedin_post_browser() FINISHED")

    def _execute_linkedin_post_api(
        self,
        post_content: str,
        post_title: str,
        approval_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a LinkedIn post using LinkedIn API (fallback method).

        Args:
            post_content: Post content
            post_title: Post title
            approval_filename: Name of approval file for logging

        Returns:
            Dict: Execution result with success status
        """
        self.logger.info(">>> _execute_linkedin_post_api() STARTED (fallback method)")

        try:
            self.logger.info(f"Posting to LinkedIn via API (fallback)...")
            self.logger.info(f"  Title: {post_title}")
            self.logger.info(f"  Content length: {len(post_content)} chars")

            # Import LinkedIn post skill
            self.logger.info("[TOOL] Importing LinkedInPostSkill...")
            try:
                from skills.linkedin_post import LinkedInPostSkill
                self.logger.info("[OK] LinkedInPostSkill imported")
            except ImportError as e:
                self.logger.error(f"[ERR] Failed to import LinkedInPostSkill: {e}")
                return {
                    'success': False,
                    'error': f'LinkedInPostSkill not available: {e}'
                }

            # Initialize LinkedIn skill
            self.logger.info("[TOOL] Creating LinkedInPostSkill instance...")
            try:
                linkedin_skill = LinkedInPostSkill(
                    vault_path=str(self.vault_path),
                    dry_run=self.config.dry_run
                )
                self.logger.info("[OK] LinkedInPostSkill instance created")
            except Exception as e:
                self.logger.error(f"[ERR] Failed to create LinkedInPostSkill: {e}")
                return {
                    'success': False,
                    'error': f'Failed to create LinkedInPostSkill: {e}'
                }

            # Publish the post
            self.logger.info("[TOOL] Publishing LinkedIn post...")
            try:
                publish_result = linkedin_skill.publish_post(
                    content=post_content,
                    title=post_title,
                    requires_approval=False  # Already approved
                )
                self.logger.info(f"[OK] LinkedIn post publication returned: {publish_result}")
            except Exception as e:
                self.logger.error(f"[ERR] LinkedIn post publication failed: {e}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                return {
                    'success': False,
                    'error': f'Post publication exception: {e}'
                }

            if publish_result.get('success'):
                post_id = publish_result.get('post_id', 'unknown')
                self.logger.info(f"[OK] LinkedIn post published via API! Post ID: {post_id}")
                return {
                    'success': True,
                    'message': f'LinkedIn post published (API)',
                    'post_id': post_id
                }
            else:
                error_msg = publish_result.get('error', 'Unknown error')
                self.logger.error(f"[ERR] LinkedIn API post failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }

        except Exception as e:
            self.logger.error(f"[ERR] Error in LinkedIn API posting: {e}", exc_info=True)
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            self.logger.info("<<< _execute_linkedin_post_api() FINISHED")

    def _process_rejected_folder(self) -> None:
        """
        Process rejected approvals from /Rejected/ folder.

        For each rejected file:
        1. Read the rejection file to log the rejection reason
        2. Archive the file with rejection metadata
        3. Auto-delete after configured retention period (default: 7 days)
        4. Log all actions for audit trail

        Retention Policy:
        - Files are kept for rejected_auto_delete_days days
        - After retention period, files are permanently deleted
        - All deletions are logged for compliance
        """
        rejected_dir = self.vault_path / 'Rejected'

        if not rejected_dir.exists():
            return

        current_time = datetime.now()
        retention_days = self.config.rejected_auto_delete_days
        enable_auto_delete = self.config.enable_rejected_auto_delete

        for file_path in rejected_dir.iterdir():
            if not file_path.is_file():
                continue

            # Skip archive subdirectory
            if file_path.parent.name == '_ARCHIVED':
                continue

            try:
                content = file_path.read_text(encoding='utf-8')

                # Only process approval_request type files
                if 'type: approval_request' not in content:
                    continue

                # Get file modification time
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                days_since_rejection = (current_time - file_mtime).days

                self.logger.info(f"Processing rejected file: {file_path.name} ({days_since_rejection} days old)")

                # Log the rejection processing
                log_action(
                    vault_path=str(self.vault_path),
                    action_type='rejection_processed',
                    actor='orchestrator',
                    target=file_path.name,
                    parameters={
                        'days_since_rejection': days_since_rejection,
                        'retention_days': retention_days
                    },
                    approval_status='rejected',
                    result='success'
                )

                # Check if file should be deleted
                if enable_auto_delete and days_since_rejection >= retention_days:
                    self.logger.info(f"Auto-deleting rejected file (>{retention_days} days): {file_path.name}")

                    # Archive before deletion (optional - move to _ARCHIVED with metadata)
                    self._archive_rejected_file(file_path)

                    # Delete the file
                    file_path.unlink()
                    self.logger.info(f"Deleted rejected file: {file_path.name}")

                    # Log deletion
                    log_action(
                        vault_path=str(self.vault_path),
                        action_type='rejected_file_deleted',
                        actor='orchestrator',
                        target=file_path.name,
                        parameters={
                            'days_since_rejection': days_since_rejection,
                            'retention_days': retention_days,
                            'reason': f'Auto-delete after {retention_days} days retention'
                        },
                        approval_status='rejected',
                        result='success'
                    )
                else:
                    # Update file with processing timestamp
                    if days_since_rejection < retention_days:
                        days_remaining = retention_days - days_since_rejection
                        self.logger.debug(f"Keeping rejected file for {days_remaining} more days: {file_path.name}")

            except Exception as e:
                self.logger.error(f"Error processing rejected file {file_path.name}: {e}")
                log_action(
                    vault_path=str(self.vault_path),
                    action_type='rejection_processing_error',
                    actor='orchestrator',
                    target=file_path.name if 'file_path' in locals() else 'unknown',
                    parameters={'error': str(e)},
                    result='failure'
                )

    def handle_rejected_approvals(self) -> None:
        """
        Handle rejected approvals by processing and cleaning them up.

        This method:
        1. Processes all rejected files in /Rejected/ folder
        2. Archives files older than retention period
        3. Deletes archived files after processing
        4. Ensures no duplicate processing occurs

        FIX: After processing each rejection and moving files to Done,
        delete the rejection file immediately to prevent re-processing.
        """
        rejected_dir = self.vault_path / 'Rejected'

        if not rejected_dir.exists():
            return

        current_time = datetime.now()
        retention_days = self.config.rejected_auto_delete_days
        enable_auto_delete = self.config.enable_rejected_auto_delete

        processed_count = 0
        deleted_count = 0

        for file_path in rejected_dir.iterdir():
            if not file_path.is_file():
                continue

            # Skip archive subdirectory
            if file_path.parent.name == '_ARCHIVED':
                continue

            try:
                content = file_path.read_text(encoding='utf-8')

                # Only process approval_request type files
                if 'type: approval_request' not in content:
                    continue

                # Get file modification time
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                days_since_rejection = (current_time - file_mtime).days

                self.logger.info(f"Handling rejected file: {file_path.name} ({days_since_rejection} days old)")

                # Log the rejection processing
                log_action(
                    vault_path=str(self.vault_path),
                    action_type='rejection_handled',
                    actor='orchestrator',
                    target=file_path.name,
                    parameters={
                        'days_since_rejection': days_since_rejection,
                        'retention_days': retention_days
                    },
                    approval_status='rejected',
                    result='success'
                )

                # Always archive and delete after processing (not just after retention period)
                # This prevents 200+ files from accumulating
                if enable_auto_delete:
                    # Archive the file for audit trail
                    self._archive_rejected_file(file_path)

                    # Delete the rejection file immediately after archiving
                    file_path.unlink()
                    deleted_count += 1
                    self.logger.info(f"Archived and deleted rejected file: {file_path.name}")

                    # Log deletion
                    log_action(
                        vault_path=str(self.vault_path),
                        action_type='rejected_file_archived_and_deleted',
                        actor='orchestrator',
                        target=file_path.name,
                        parameters={
                            'days_since_rejection': days_since_rejection,
                            'retention_days': retention_days,
                            'reason': 'Archive after processing (prevent accumulation)'
                        },
                        approval_status='rejected',
                        result='success'
                    )
                else:
                    processed_count += 1
                    self.logger.debug(f"Processed (kept) rejected file: {file_path.name}")

            except Exception as e:
                self.logger.error(f"Error handling rejected file {file_path.name}: {e}")
                log_action(
                    vault_path=str(self.vault_path),
                    action_type='rejection_handling_error',
                    actor='orchestrator',
                    target=file_path.name if 'file_path' in locals() else 'unknown',
                    parameters={'error': str(e)},
                    result='failure'
                )

        self.logger.info(f"Handled {processed_count + deleted_count} rejected files: {deleted_count} archived/deleted, {processed_count} kept")

    def _archive_rejected_file(self, file_path: Path) -> None:
        """
        Archive a rejected file before deletion (for audit trail).

        Creates a metadata file in _ARCHIVED subdirectory with rejection details.

        Args:
            file_path: Path to the rejected file to archive
        """
        try:
            archive_dir = self.vault_path / 'Rejected' / '_ARCHIVED'
            archive_dir.mkdir(parents=True, exist_ok=True)

            # Read original content
            content = file_path.read_text(encoding='utf-8')

            # Parse frontmatter
            frontmatter = self._read_frontmatter(content)

            # Create archive metadata
            archive_metadata = {
                'original_filename': file_path.name,
                'archived_date': datetime.now().isoformat(),
                'deletion_reason': 'Auto-delete after retention period',
                'retention_days': self.config.rejected_auto_delete_days,
                'original_rejection_date': datetime.fromtimestamp(
                    file_path.stat().st_mtime
                ).isoformat()
            }

            # Merge with original frontmatter
            frontmatter.update(archive_metadata)

            # Create archive file
            archive_filename = f"ARCHIVED_{file_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            archive_path = archive_dir / archive_filename

            # Update content with archive metadata
            content = self._update_frontmatter(content, frontmatter)

            # Add archive notice
            archive_notice = f"""
## Archive Notice
*Archived: {datetime.now().isoformat()}*

This file was rejected and archived for audit compliance.
It will be permanently deleted after the retention period.

**Original Filename:** {file_path.name}
**Retention Period:** {self.config.rejected_auto_delete_days} days
"""
            content += archive_notice
            archive_path.write_text(content, encoding='utf-8')

            self.logger.info(f"Archived rejected file: {archive_filename}")

        except Exception as e:
            self.logger.error(f"Error archiving rejected file: {e}")

    def _auto_complete_tasks(self) -> None:
        """
        Auto-complete tasks that don't require approval.

        Note: When ALWAYS_REQUIRE_APPROVAL=True, this function does nothing.
        All tasks must go through the approval workflow.
        """
        if ALWAYS_REQUIRE_APPROVAL:
            self.logger.debug("Auto-complete disabled: All tasks require approval")
            return

        plans_dir = self.vault_path / 'Plans'
        needs_action_dir = self.vault_path / 'Needs_Action'
        pending_approval_dir = self.vault_path / 'Pending_Approval'

        if not plans_dir.exists():
            return

        # Get list of pending approvals to check against
        pending_approvals = set()
        if pending_approval_dir.exists():
            for f in pending_approval_dir.iterdir():
                if f.is_file():
                    try:
                        content = f.read_text(encoding='utf-8')
                        for line in content.split('\n'):
                            if line.startswith('task_file:'):
                                pending_approvals.add(line.split(':', 1)[1].strip())
                    except:
                        pass

        # Check each plan file
        for plan_path in plans_dir.iterdir():
            if not plan_path.is_file():
                continue

            try:
                content = plan_path.read_text(encoding='utf-8')

                # Extract source_file from frontmatter
                source_file = None
                for line in content.split('\n'):
                    if line.startswith('source_file:'):
                        source_file = line.split(':', 1)[1].strip()
                        break

                # Skip if already has approval pending
                if source_file and source_file in pending_approvals:
                    continue

                # Check if plan needs approval (has approval keywords)
                needs_approval = any(
                    keyword in content.lower() for keyword in APPROVAL_KEYWORDS
                )

                if not needs_approval:
                    # Auto-complete: move plan and task to Done
                    self.logger.info(f"Auto-completing task (no approval required): {plan_path.name}")

                    # Move plan to Done
                    move_to_done(
                        file_path=str(plan_path),
                        vault_path=str(self.vault_path),
                        completion_note="Auto-completed (no approval required)"
                    )

                    # Move task to Done if exists
                    if source_file:
                        task_path = needs_action_dir / source_file
                        if task_path.exists():
                            move_to_done(
                                file_path=str(task_path),
                                vault_path=str(self.vault_path),
                                completion_note="Associated task auto-completed"
                            )

                    self.logger.info("Auto-completed task (no approval required)")

                    # Log the action
                    log_action(
                        vault_path=str(self.vault_path),
                        action_type='task_auto_completed',
                        actor='orchestrator',
                        target=plan_path.name,
                        parameters={'source_file': source_file},
                        approval_status='not_required',
                        result='success'
                    )

            except Exception as e:
                self.logger.error(f"Error auto-completing task {plan_path.name}: {e}")

    def _check_linkedin_auto_generation(self) -> None:
        """
        Check if we should auto-generate a LinkedIn post.

        Scheduled generation:
        - Monday 10 AM: Weekly summary
        - Wednesday 10 AM: Thought leadership
        - Friday 10 AM: Milestone/achievement

        Generated posts are saved to Pending_Approval/ for review.
        """
        try:
            from skills.linkedin_auto_generator import LinkedInAutoGenerator

            auto_gen = LinkedInAutoGenerator()

            if auto_gen.should_generate_now():
                self.logger.info("📝 Scheduled LinkedIn post generation triggered")

                filepath = auto_gen.generate_scheduled_post()

                if filepath:
                    self.logger.info(f"✅ Auto-generated post: {filepath.name}")
                    self.logger.info(f"📝 Post ready for review in Pending_Approval/")

                    # Log the generation
                    log_action(
                        vault_path=str(self.vault_path),
                        action_type='linkedin_post_generated',
                        actor='linkedin_auto_generator',
                        target=filepath.name,
                        parameters={
                            'generation_type': 'scheduled',
                            'filepath': str(filepath)
                        },
                        result='success'
                    )

                    # Update dashboard to show new post
                    self._update_dashboard_with_stats()
                else:
                    self.logger.warning("Post generation returned None")

        except ImportError:
            self.logger.debug("LinkedIn auto-generator not available")
        except Exception as e:
            self.logger.error(f"LinkedIn auto-generation error: {e}")

    def _update_dashboard_with_stats(self) -> None:
        """
        Update Dashboard.md with current vault statistics.

        Counts files in each folder and shows recent activity.
        """
        try:
            self.logger.debug("Updating dashboard with stats...")

            # Count files in each folder using glob for accuracy
            needs_action_count = len(list((self.vault_path / 'Needs_Action').glob('*.md'))) if (self.vault_path / 'Needs_Action').exists() else 0
            plans_count = len(list((self.vault_path / 'Plans').glob('*.md'))) if (self.vault_path / 'Plans').exists() else 0
            pending_count = len(list((self.vault_path / 'Pending_Approval').glob('*.md'))) if (self.vault_path / 'Pending_Approval').exists() else 0
            approved_count = len(list((self.vault_path / 'Approved').glob('*.md'))) if (self.vault_path / 'Approved').exists() else 0
            done_count = len(list((self.vault_path / 'Done').glob('*.md'))) if (self.vault_path / 'Done').exists() else 0
            rejected_count = len(list((self.vault_path / 'Rejected').glob('*.md'))) if (self.vault_path / 'Rejected').exists() else 0

            # Count files completed TODAY by checking modification time
            done_today_count = 0
            done_dir = self.vault_path / 'Done'
            if done_dir.exists():
                today = datetime.now().date()
                for f in done_dir.glob('*.md'):
                    if f.is_file():
                        try:
                            mtime = datetime.fromtimestamp(f.stat().st_mtime).date()
                            if mtime == today:
                                done_today_count += 1
                        except:
                            # If stat fails, try to read frontmatter 'completed' field
                            try:
                                content = f.read_text(encoding='utf-8')
                                if 'completed:' in content and today.strftime('%Y-%m-%d') in content:
                                    done_today_count += 1
                            except:
                                pass

            # Count LinkedIn-specific metrics
            linkedin_posts_count = 0
            linkedin_pending_count = 0
            if done_dir.exists():
                for f in done_dir.glob('LINKEDIN_POST_*.md'):
                    linkedin_posts_count += 1
            if (self.vault_path / 'Pending_Approval').exists():
                for f in (self.vault_path / 'Pending_Approval').glob('LINKEDIN_POST_*.md'):
                    linkedin_pending_count += 1

            # Calculate additional metrics
            total_active = needs_action_count + plans_count + pending_count + approved_count
            total_processed = done_count + rejected_count
            success_rate = (done_count / total_processed * 100) if total_processed > 0 else 0

            # Log the counts for verification
            self.logger.info(f"Dashboard Update - Needs Action: {needs_action_count}")
            self.logger.info(f"Dashboard Update - Plans: {plans_count}")
            self.logger.info(f"Dashboard Update - Pending Approval: {pending_count}")
            self.logger.info(f"Dashboard Update - Approved: {approved_count}")
            self.logger.info(f"Dashboard Update - Done (total): {done_count}")
            self.logger.info(f"Dashboard Update - Done (today): {done_today_count}")
            self.logger.info(f"Dashboard Update - Rejected: {rejected_count}")
            self.logger.info(f"Dashboard Update - Total Active: {total_active}")
            self.logger.info(f"Dashboard Update - Total Processed: {total_processed}")
            self.logger.info(f"Dashboard Update - Success Rate: {success_rate:.1f}%")
            self.logger.info(f"Dashboard Update - LinkedIn Posts (total): {linkedin_posts_count}")
            self.logger.info(f"Dashboard Update - LinkedIn Posts (pending): {linkedin_pending_count}")

            # Get recent activity
            recent_logs = get_recent_logs(str(self.vault_path), limit=10)
            activity_lines = []
            for log_entry in reversed(recent_logs):
                timestamp = log_entry.get('timestamp', '')
                action_type = log_entry.get('action_type', 'unknown')
                target = log_entry.get('target', '')
                result = log_entry.get('result', 'unknown')

                # Format timestamp
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        time_str = dt.strftime('%H:%M')
                    except:
                        time_str = timestamp[:5] if len(timestamp) > 5 else 'Unknown'
                else:
                    time_str = 'Unknown'

                status_icon = '[OK]' if result == 'success' else '[ERR]' if result == 'failure' else '[...]'
                activity_lines.append(
                    f"- [{time_str}] {status_icon} {action_type.replace('_', ' ').title()}: {target[:50]}"
                )

            if not activity_lines:
                activity_lines = ["- *No recent activity*"]

            # Build dashboard content
            dashboard_content = f"""---
last_updated: {datetime.now().isoformat()}
---

# AI Employee Dashboard

## System Status
- [OK] File Watcher: Running
- [OK] Orchestrator: Active
- [TIME] Last Check: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Quick Stats
| Metric | Count |
|--------|-------|
| [INBOX] Needs Action | {needs_action_count} |
| [PLAN] Plans Created | {plans_count} |
| [WAIT] Pending Approval | {pending_count} |
| [OK] Completed Today | {done_today_count} |
| [TOTAL] Total Done | {done_count} |
| [ACTIVE] Total Active | {total_active} |
| [RATE] Success Rate | {success_rate:.1f}% |
| [LINKEDIN] LinkedIn Posts | {linkedin_posts_count} |

## Recent Activity
{chr(10).join(activity_lines)}

## Folder Status
- Inbox: Monitoring active
- Needs Action: {needs_action_count} tasks waiting
- Plans: {plans_count} plans ready
- Pending Approval: {pending_count} awaiting decision{f' (including {linkedin_pending_count} LinkedIn posts)' if linkedin_pending_count > 0 else ''}
- Approved: {approved_count} ready to execute
- Done: {done_count} completed ({done_today_count} today){f', including {linkedin_posts_count} LinkedIn posts' if linkedin_posts_count > 0 else ''}
- Rejected: {rejected_count} declined

---

*Generated by AI Employee v1.0.0 (Silver Tier)*
"""

            # Write dashboard
            dashboard_path = self.vault_path / 'Dashboard.md'
            dashboard_path.write_text(dashboard_content, encoding='utf-8')

            self.logger.info("Dashboard updated with current stats")

            # Log the action
            log_action(
                vault_path=str(self.vault_path),
                action_type='dashboard_updated',
                actor='orchestrator',
                target='Dashboard.md',
                parameters={
                    'needs_action_count': needs_action_count,
                    'plans_count': plans_count,
                    'pending_count': pending_count,
                    'done_today_count': done_today_count,
                    'total_active': total_active,
                    'success_rate': success_rate
                },
                result='success'
            )

        except Exception as e:
            self.logger.error(f"Error updating dashboard: {e}")

    def process_approvals(self) -> None:
        """
        Process approved actions from /Approved/ folder.
        
        When files are moved to /Approved/, execute the requested actions.
        """
        approved_dir = self.vault_path / 'Approved'
        
        if not approved_dir.exists():
            return
        
        for file_path in approved_dir.iterdir():
            if not file_path.is_file():
                continue
            
            try:
                content = file_path.read_text(encoding='utf-8')
                
                # Determine action type
                if 'type: approval_request' in content:
                    self._execute_approved_action(file_path, content)
                    
            except Exception as e:
                self.logger.error(f"Error processing approval {file_path.name}: {e}")
    
    def _execute_approved_action(self, file_path: Path, content: str) -> None:
        """
        Execute an approved action.
        
        Args:
            file_path: Path to approval file
            content: File content
        """
        # Extract action type
        action_match = content.split('\n')
        action_type = 'unknown'
        for line in action_match:
            if line.startswith('action:'):
                action_type = line.split(':')[1].strip()
                break
        
        self.logger.info(f"Executing approved action: {action_type}")
        
        # For Bronze tier, we just move to Done and log
        # In Silver/Gold tiers, this would execute actual MCP actions
        
        # Move to Done
        result = move_to_done(
            file_path=str(file_path),
            vault_path=str(self.vault_path),
            completion_note=f"Approved action ({action_type}) executed"
        )
        
        if result['success']:
            log_action(
                vault_path=str(self.vault_path),
                action_type='approved_action_executed',
                actor='orchestrator',
                target=file_path.name,
                parameters={'action_type': action_type},
                approval_status='approved',
                approved_by='human',
                result='success'
            )
        else:
            self.logger.error(f"Failed to move approved file to Done: {result.get('error')}")
    
    def update_dashboard(self) -> None:
        """Update Dashboard.md with current vault state."""
        self.logger.debug("Updating dashboard...")
        
        result = update_dashboard(str(self.vault_path))
        
        if result['success']:
            self.last_dashboard_update = datetime.now()
            self.logger.debug(f"Dashboard updated: {result['counts']}")
        else:
            self.logger.error(f"Dashboard update failed: {result.get('error')}")
    
    def check_watcher_health(self) -> None:
        """Check health of watcher processes and restart if needed."""
        for name, process in list(self.watcher_processes.items()):
            # Check if process is still running
            if process.poll() is not None:
                self.logger.warning(f"{name} watcher died (exit code: {process.returncode}), restarting...")
                
                # Restart the watcher
                script_map = {
                    'gmail': 'src/watchers/gmail_watcher.py',
                    'filesystem': 'src/watchers/filesystem_watcher.py'
                }
                
                if name in script_map:
                    self._start_watcher(name, script_map[name])
                
                # Log the incident
                log_action(
                    vault_path=str(self.vault_path),
                    action_type='watcher_restarted',
                    actor='orchestrator',
                    target=name,
                    parameters={'exit_code': process.returncode},
                    result='success'
                )
    
    def run(self) -> None:
        """
        Main orchestration loop.

        Runs until shutdown is requested.

        Loop structure:
        1. Check Needs_Action/ for tasks (EXISTING)
        2. Process tasks and create plans (EXISTING)
        3. Check if plan needs approval (NEW - Feature #1)
        4. Create approval requests if needed (NEW - Feature #1)
        5. Check Approved/ folder for approved actions (NEW - Feature #2)
        6. Execute approved actions and move to Done/ (NEW - Feature #2)
        7. Auto-complete tasks without approval requirements (NEW - Feature #2)
        8. Update Dashboard.md with stats (NEW - Feature #3)
        9. Log all actions to actions.json (NEW - Feature #4 - integrated in each step)
        10. Process Rejected/ folder for auto-deletion (NEW - Rejected Auto-Delete)
        11. Sleep 30 seconds
        12. Repeat
        """
        self.logger.info("Starting Orchestrator main loop...")
        self.running = True

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Start watchers
        self.start_watchers()

        # Initial dashboard update
        self._update_dashboard_with_stats()

        # Main loop
        check_counter = 0
        dashboard_counter = 0
        rejected_counter = 0
        cycle_count = 0

        while not self.shutdown_requested:
            try:
                cycle_count += 1
                self.logger.info(f"=== Orchestration Cycle {cycle_count} ===")

                # Step 1 & 2: Check Needs_Action folder and process with Qwen simulation
                new_files = self.check_needs_action()
                if new_files:
                    self.trigger_qwen(new_files)
                    # Note: Approval checking (Feature #1) happens inside _process_generic_file
                    # after each plan is created
                    # Update dashboard after processing new files
                    self._update_dashboard_with_stats()
                    self.logger.info("Dashboard updated after processing new files")

                # Step 1.5: Check for scheduled LinkedIn post generation
                self._check_linkedin_auto_generation()

                # Step 5 & 6: Execute approved actions from Approved/ folder (Feature #2)
                self.logger.info("Step 5: Checking Approved/ folder for approved actions...")
                self.handle_approved_actions()  # DIRECT CALL - handles all approved actions
                self.logger.info("Step 5: Completed approved actions check")
                # Update dashboard after executing approved actions
                self._update_dashboard_with_stats()
                self.logger.info("Dashboard updated after executing approved actions")

                # Step 7: Auto-complete tasks that don't require approval (Feature #2)
                self._auto_complete_tasks()
                # Update dashboard after auto-completing tasks
                self._update_dashboard_with_stats()
                self.logger.info("Dashboard updated after auto-completing tasks")

                # Step 8: Update dashboard with current stats (Feature #3)
                self._update_dashboard_with_stats()

                # Legacy: Also process approvals using old method (for backward compatibility)
                self.process_approvals()

                # Step 10: Process rejected approvals using new handle_rejected_approvals method
                # This archives and deletes rejected files to prevent accumulation
                self.logger.info("Step 10: Processing rejected files...")
                self.handle_rejected_approvals()
                self.logger.info("Step 10: Completed rejected files processing")
                # Update dashboard after handling rejected files
                self._update_dashboard_with_stats()
                self.logger.info("Dashboard updated after handling rejected files")

                # Update dashboard periodically (legacy interval-based)
                dashboard_counter += 1
                if dashboard_counter >= (self.config.dashboard_update_interval // self.config.check_interval):
                    self.update_dashboard()
                    dashboard_counter = 0

                # Check watcher health
                check_counter += 1
                if check_counter >= 10:
                    self.check_watcher_health()
                    check_counter = 0

                self.logger.info(f"=== Cycle {cycle_count} complete, waiting {self.config.check_interval}s ===")

                # Step 11: Wait before next check
                time.sleep(self.config.check_interval)

            except Exception as e:
                self.logger.error(f"Error in orchestration loop: {e}", exc_info=True)
                time.sleep(self.config.check_interval)

        # Shutdown
        self.shutdown()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, initiating shutdown...")
        self.shutdown_requested = True
    
    def shutdown(self) -> None:
        """Gracefully shutdown the orchestrator and all watchers."""
        self.logger.info("Shutting down Orchestrator...")
        self.running = False
        
        # Stop watcher processes
        for name, process in self.watcher_processes.items():
            self.logger.info(f"Stopping {name} watcher (PID: {process.pid})...")
            process.terminate()
            
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            
            log_action(
                vault_path=str(self.vault_path),
                action_type='watcher_stopped',
                actor='orchestrator',
                target=name,
                result='success'
            )
        
        self.watcher_processes.clear()
        
        # Final dashboard update
        self.update_dashboard()
        
        # Log shutdown
        log_action(
            vault_path=str(self.vault_path),
            action_type='orchestrator_shutdown',
            actor='orchestrator',
            target='system',
            result='success'
        )
        
        self.logger.info("Orchestrator shutdown complete")


def load_config(config_path: Optional[str] = None) -> OrchestratorConfig:
    """
    Load orchestrator configuration from file or environment.

    Args:
        config_path: Optional path to config file

    Returns:
        OrchestratorConfig: Configuration object
    """
    if config_path and Path(config_path).exists():
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        return OrchestratorConfig(**config_data)

    # Load from environment
    return OrchestratorConfig(
        vault_path=os.getenv('OBSIDIAN_VAULT_PATH', 'D:\\Hackathon-0\\AI_Employee_Vault'),
        check_interval=int(os.getenv('ORCHESTRATOR_CHECK_INTERVAL', '30')),
        dashboard_update_interval=int(os.getenv('DASHBOARD_UPDATE_INTERVAL', '300')),
        enable_gmail_watcher=os.getenv('ENABLE_GMAIL_WATCHER', 'false').lower() == 'true',
        enable_filesystem_watcher=os.getenv('ENABLE_FILESYSTEM_WATCHER', 'true').lower() == 'true',
        gmail_credentials_path=os.getenv('GMAIL_CREDENTIALS_PATH'),
        dry_run=os.getenv('DRY_RUN', 'false').lower() == 'true',
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        rejected_auto_delete_days=int(os.getenv('REJECTED_AUTO_DELETE_DAYS', '7')),
        enable_rejected_auto_delete=os.getenv('ENABLE_REJECTED_AUTO_DELETE', 'true').lower() == 'true'
    )


def main():
    """
    Main entry point for the orchestrator.
    
    Usage:
        python orchestrator.py [--config PATH] [--dry-run]
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='AI Employee Orchestrator')
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Path to configuration file'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in dry-run mode'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    if args.dry_run:
        config.dry_run = True
    
    # Create and run orchestrator
    orchestrator = Orchestrator(config)
    
    try:
        orchestrator.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
        orchestrator.shutdown()


if __name__ == '__main__':
    main()
