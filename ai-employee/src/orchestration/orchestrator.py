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
    """Configuration for the orchestrator."""
    vault_path: str = str(DEFAULT_VAULT_PATH)
    check_interval: int = 30
    dashboard_update_interval: int = 300
    enable_gmail_watcher: bool = False
    enable_filesystem_watcher: bool = True
    gmail_credentials_path: Optional[str] = None
    dry_run: bool = False
    log_level: str = "INFO"


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
        """
        approved_dir = self.vault_path / 'Approved'

        if not approved_dir.exists():
            return

        for file_path in approved_dir.iterdir():
            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text(encoding='utf-8')

                # Only process approval_request type files
                if 'type: approval_request' not in content:
                    continue

                self.logger.info(f"Executing approved action: {file_path.name}")

                # Extract action type
                action_type = None
                for line in content.split('\n'):
                    if line.startswith('action:'):
                        action_type = line.split(':', 1)[1].strip()
                        break

                # Extract detail_ prefixed fields
                action_details = {}
                for line in content.split('\n'):
                    if line.startswith('detail_'):
                        key = line.split(':', 1)[0].replace('detail_', '').strip()
                        value = line.split(':', 1)[1].strip()
                        action_details[key] = value

                # Extract plan_file and task_file from frontmatter
                plan_file = action_details.get('plan_file')
                task_file = action_details.get('task_file')

                # Execute based on action type
                execution_result = {'success': True, 'message': ''}

                if action_type == 'email_send' or action_type == 'email_response':
                    execution_result = self._execute_email_send(action_details, file_path.name)
                elif action_type == 'plan_execution':
                    # Generic plan execution - just log and move files
                    execution_result = {'success': True, 'message': 'Plan executed'}
                else:
                    self.logger.warning(f"Unknown action type: {action_type}")
                    execution_result = {'success': False, 'message': f'Unknown action type: {action_type}'}

                # Log execution
                log_action(
                    vault_path=str(self.vault_path),
                    action_type='action_executed',
                    actor='orchestrator',
                    target=file_path.name,
                    parameters={
                        'action_type': action_type,
                        'plan_file': plan_file,
                        'task_file': task_file,
                        'execution_result': execution_result
                    },
                    approval_status='approved',
                    approved_by='human',
                    result='success' if execution_result['success'] else 'failure'
                )

                if execution_result['success']:
                    self.logger.info(f"Action executed successfully: {execution_result.get('message', '')}")
                else:
                    self.logger.error(f"Action execution failed: {execution_result.get('error', '')}")

                # SINGLE FILE LIFECYCLE: Update file with execution result and move to Done
                self._finalize_executed_action(file_path, execution_result, action_type, plan_file, task_file)

            except Exception as e:
                self.logger.error(f"Error executing approved action {file_path.name}: {e}")
                log_action(
                    vault_path=str(self.vault_path),
                    action_type='action_execution_error',
                    actor='orchestrator',
                    target=file_path.name,
                    parameters={'error': str(e)},
                    result='failure'
                )

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

**Status:** {'✅ Success' if execution_result.get('success') else '❌ Failed'}
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

    def _execute_email_send(self, details: Dict[str, str], approval_filename: str) -> Dict[str, Any]:
        """
        Execute an email send action using SendEmailSkill.

        Args:
            details: Email details from approval file (to, subject, body, etc.)
            approval_filename: Name of the approval file for logging

        Returns:
            dict: Execution result with success status
        """
        try:
            self.logger.info(f"Sending email via SendEmailSkill...")

            # Initialize email skill
            email_skill = SendEmailSkill(
                vault_path=str(self.vault_path),
                dry_run=self.config.dry_run
            )

            if not email_skill.initialize():
                return {
                    'success': False,
                    'error': 'Failed to initialize email service'
                }

            # Send email
            result = email_skill.send_email(
                to=details.get('to', ''),
                subject=details.get('subject', ''),
                body=details.get('body', details.get('content', '')),
                cc=details.get('cc') if details.get('cc') else None,
                html=details.get('html', 'false').lower() == 'true'
            )

            if result.get('success'):
                message_id = result.get('message_id', 'unknown')
                self.logger.info(f"Email sent successfully! Message ID: {message_id}")
                return {
                    'success': True,
                    'message': f'Email sent (ID: {message_id})',
                    'message_id': message_id
                }
            else:
                error_msg = result.get('error', 'Unknown error')
                self.logger.error(f"Email send failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }

        except Exception as e:
            self.logger.error(f"Error in email send execution: {e}")
            return {
                'success': False,
                'error': str(e)
            }

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

    def _update_dashboard_with_stats(self) -> None:
        """
        Update Dashboard.md with current vault statistics.

        Counts files in each folder and shows recent activity.
        """
        try:
            self.logger.debug("Updating dashboard with stats...")

            # Count files in each folder
            needs_action_count = sum(
                1 for f in (self.vault_path / 'Needs_Action').iterdir()
                if f.is_file()
            ) if (self.vault_path / 'Needs_Action').exists() else 0

            plans_count = sum(
                1 for f in (self.vault_path / 'Plans').iterdir()
                if f.is_file()
            ) if (self.vault_path / 'Plans').exists() else 0

            pending_count = sum(
                1 for f in (self.vault_path / 'Pending_Approval').iterdir()
                if f.is_file()
            ) if (self.vault_path / 'Pending_Approval').exists() else 0

            # Count files created today in Done folder
            done_today_count = 0
            done_dir = self.vault_path / 'Done'
            if done_dir.exists():
                today_str = datetime.now().strftime('%Y-%m-%d')
                for f in done_dir.iterdir():
                    if f.is_file():
                        try:
                            mtime = datetime.fromtimestamp(f.stat().st_mtime)
                            if mtime.strftime('%Y-%m-%d') == today_str:
                                done_today_count += 1
                        except:
                            pass

            # Get recent activity
            recent_logs = get_recent_logs(str(self.vault_path), limit=5)
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

                emoji = '✅' if result == 'success' else '❌' if result == 'failure' else '⏳'
                activity_lines.append(
                    f"- [{time_str}] {emoji} {action_type.replace('_', ' ').title()}: {target[:50]}"
                )

            if not activity_lines:
                activity_lines = ["- *No recent activity*"]

            # Build dashboard content
            dashboard_content = f"""---
last_updated: {datetime.now().isoformat()}
---

# 🎯 AI Employee Dashboard

## System Status
- 🟢 File Watcher: Running
- 🟢 Orchestrator: Active
- ⏰ Last Check: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Quick Stats
| Metric | Count |
|--------|-------|
| 📥 Needs Action | {needs_action_count} |
| 📋 Plans Created | {plans_count} |
| ⏰ Pending Approval | {pending_count} |
| ✅ Completed Today | {done_today_count} |

## Recent Activity
{chr(10).join(activity_lines)}

## Folder Status
- Inbox: Monitoring active
- Needs Action: {needs_action_count} tasks waiting
- Plans: {plans_count} plans ready
- Pending Approval: {pending_count} awaiting decision
- Done: {done_today_count} completed today

---

*Generated by AI Employee v1.0.0 (Bronze Tier)*
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
                    'done_today_count': done_today_count
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
        10. Sleep 30 seconds
        11. Repeat
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

        while not self.shutdown_requested:
            try:
                # Step 1 & 2: Check Needs_Action folder and process with Qwen simulation
                new_files = self.check_needs_action()
                if new_files:
                    self.trigger_qwen(new_files)
                    # Note: Approval checking (Feature #1) happens inside _process_generic_file
                    # after each plan is created

                # Step 5 & 6: Execute approved actions from Approved/ folder (Feature #2)
                self._execute_approved_actions()

                # Step 7: Auto-complete tasks that don't require approval (Feature #2)
                self._auto_complete_tasks()

                # Step 8: Update dashboard with current stats (Feature #3)
                self._update_dashboard_with_stats()

                # Legacy: Also process approvals using old method (for backward compatibility)
                self.process_approvals()

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

                # Step 10: Wait before next check
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
        log_level=os.getenv('LOG_LEVEL', 'INFO')
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
