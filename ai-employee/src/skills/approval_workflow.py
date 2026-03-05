"""
Approval Workflow Skill for AI Employee - Silver Tier

This skill manages the human-in-the-loop approval workflow for sensitive actions.
It monitors approval requests, processes approved files, and handles rejections.

Silver Tier Requirement: Human-in-the-loop approval workflow for sensitive actions

Features:
- Monitors Pending_Approval folder for approval requests
- Processes files moved to Approved folder
- Handles rejections and moves to Rejected folder
- Supports multiple action types (email, payment, post, plan)
- Comprehensive audit logging
- Expiration handling for stale approvals
"""

import os

# Environment variable for vault path (set in .env file)
# Default: D:/Hackathon-0/AI_Employee_Vault (root vault)
DEFAULT_VAULT_PATH = os.getenv('VAULT_PATH', 'D:/Hackathon-0/AI_Employee_Vault')

import sys
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ApprovalWorkflowSkill:
    """
    Approval Workflow Skill
    
    Manages human-in-the-loop approval workflow for sensitive actions.
    Monitors approval folders and processes approved/rejected items.
    """
    
    # Action types that require approval
    ACTION_TYPES = [
        'email_send',
        'payment',
        'linkedin_post',
        'plan_execution',
        'bulk_operation',
        'external_api_call'
    ]
    
    # Default expiration time (24 hours)
    DEFAULT_EXPIRATION_HOURS = 24
    
    def __init__(
        self,
        vault_path: Optional[str] = None,
        expiration_check_enabled: bool = True
    ):
        """
        Initialize Approval Workflow Skill
        
        Args:
            vault_path: Path to Obsidian vault
            expiration_check_enabled: Enable expiration checking for stale approvals
        """
        # Resolve paths
        self.project_root = Path(__file__).parent.parent.parent
        self.vault_path = Path(vault_path) if vault_path else Path(DEFAULT_VAULT_PATH)
        
        # Directories
        self.pending_dir = self.vault_path / 'Pending_Approval'
        self.approved_dir = self.vault_path / 'Approved'
        self.rejected_dir = self.vault_path / 'Rejected'
        self.done_dir = self.vault_path / 'Done'
        self.logs_dir = self.vault_path / 'Logs'
        
        for directory in [self.pending_dir, self.approved_dir, self.rejected_dir, self.done_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Configuration
        self.expiration_check_enabled = expiration_check_enabled
        self.expiration_hours = self.DEFAULT_EXPIRATION_HOURS
        
        # Action handlers (registered by external skills)
        self.action_handlers: Dict[str, Callable] = {}
        
        logger.info("ApprovalWorkflowSkill initialized")
        logger.info(f"Vault path: {self.vault_path}")
        logger.info(f"Expiration check: {self.expiration_check_enabled}")
    
    def register_action_handler(self, action_type: str, handler: Callable) -> None:
        """
        Register a handler function for an action type
        
        Args:
            action_type: Type of action (e.g., 'email_send', 'payment')
            handler: Function to call when action is approved
        """
        self.action_handlers[action_type] = handler
        logger.info(f"Registered handler for action type: {action_type}")
    
    def check_pending_approvals(self) -> List[Path]:
        """
        Check Pending_Approval folder for approval requests
        
        Returns:
            List[Path]: List of pending approval files
        """
        if not self.pending_dir.exists():
            return []
        
        pending_files = list(self.pending_dir.glob('*.md'))
        
        # Sort by creation time (oldest first)
        pending_files.sort(key=lambda f: f.stat().st_ctime)
        
        logger.info(f"Found {len(pending_files)} pending approval(s)")
        
        # Check for expired approvals
        if self.expiration_check_enabled:
            self._check_expired_approvals(pending_files)
        
        return pending_files
    
    def check_approved_files(self) -> List[Path]:
        """
        Check Approved folder for files ready to process
        
        Returns:
            List[Path]: List of approved files
        """
        if not self.approved_dir.exists():
            return []
        
        approved_files = list(self.approved_dir.glob('*.md'))
        
        # Sort by modification time (most recently moved first)
        approved_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        logger.info(f"Found {len(approved_files)} approved file(s)")
        
        return approved_files
    
    def check_rejected_files(self) -> List[Path]:
        """
        Check Rejected folder for rejected files
        
        Returns:
            List[Path]: List of rejected files
        """
        if not self.rejected_dir.exists():
            return []
        
        rejected_files = list(self.rejected_dir.glob('*.md'))
        logger.info(f"Found {len(rejected_files)} rejected file(s)")
        
        return rejected_files
    
    def process_approved_files(self) -> List[Dict[str, Any]]:
        """
        Process all approved files with registered handlers
        
        Returns:
            List[Dict]: Processing results for each file
        """
        results = []
        approved_files = self.check_approved_files()
        
        for filepath in approved_files:
            try:
                result = self._process_single_approved_file(filepath)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing {filepath}: {e}")
                results.append({
                    'file': str(filepath),
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    def _process_single_approved_file(self, filepath: Path) -> Dict[str, Any]:
        """
        Process a single approved file
        
        Args:
            filepath: Path to approved file
            
        Returns:
            Dict: Processing result
        """
        result = {
            'file': str(filepath),
            'filename': filepath.name,
            'success': False,
            'action_type': None,
            'handler_called': False,
            'error': None
        }
        
        try:
            # Read file content
            content = filepath.read_text(encoding='utf-8')
            
            # Extract frontmatter
            frontmatter = self._extract_frontmatter(content)
            
            # Get action type
            action_type = frontmatter.get('action', frontmatter.get('type', 'unknown'))
            result['action_type'] = action_type
            
            logger.info(f"Processing approved file: {filepath.name} (type: {action_type})")
            
            # Check if we have a handler for this action type
            if action_type in self.action_handlers:
                handler = self.action_handlers[action_type]
                result['handler_called'] = True
                
                # Call handler with file path and metadata
                handler_result = handler(filepath, frontmatter, content)
                result['handler_result'] = handler_result
                result['success'] = handler_result.get('success', False) if isinstance(handler_result, dict) else True
                
            else:
                # No handler registered - just move to Done
                logger.warning(f"No handler registered for action type: {action_type}")
                self._move_to_done(filepath)
                result['success'] = True
                result['message'] = 'No handler - moved to Done'
            
            # Log the processing
            self._log_action('process_approved', {
                'file': filepath.name,
                'action_type': action_type,
                'success': result['success']
            })
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error processing {filepath}: {e}")
        
        return result
    
    def create_approval_request(
        self,
        action_type: str,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        expiration_hours: Optional[int] = None
    ) -> Path:
        """
        Create a new approval request file
        
        Args:
            action_type: Type of action requiring approval
            title: Title/description of the request
            content: Detailed content of the request
            metadata: Additional metadata
            expiration_hours: Hours until expiration
            
        Returns:
            Path: Path to created approval file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_title = re.sub(r'[^\w\s-]', '', title)[:30]
        
        filename = f"APPROVAL_{action_type}_{safe_title}_{timestamp}.md"
        filepath = self.pending_dir / filename
        
        expiration = datetime.now() + timedelta(hours=expiration_hours or self.expiration_hours)
        
        # Build metadata
        meta = {
            'type': 'approval_request',
            'action': action_type,
            'title': title,
            'created': datetime.now().isoformat(),
            'expires': expiration.isoformat(),
            'status': 'pending'
        }
        
        if metadata:
            meta.update(metadata)
        
        # Build frontmatter
        frontmatter = "---\n"
        for key, value in meta.items():
            frontmatter += f"{key}: {value}\n"
        frontmatter += "---\n\n"
        
        # Build content
        markdown_content = f"""{frontmatter}
# Approval Request: {title}

## Action Type
{action_type}

## Details

{content}

---

## To Approve

Move this file to the /Approved folder.

## To Reject

Move this file to the /Rejected folder with a note explaining why.

## To Request Changes

Edit this file with requested changes and keep in Pending_Approval.

---

*Created: {meta['created']}*
*Expires: {meta['expires']}*

---
*Generated by AI Employee - Approval Workflow Skill*
"""
        
        filepath.write_text(markdown_content, encoding='utf-8')
        logger.info(f"Created approval request: {filepath}")
        
        # Log the creation
        self._log_action('create_approval_request', {
            'file': filepath.name,
            'action_type': action_type,
            'title': title
        })
        
        return filepath
    
    def reject_file(self, filepath: Path, reason: Optional[str] = None) -> bool:
        """
        Move a file to Rejected folder with optional reason
        
        Args:
            filepath: Path to file to reject
            reason: Optional rejection reason
            
        Returns:
            bool: True if successful
        """
        try:
            if not filepath.exists():
                logger.warning(f"File not found: {filepath}")
                return False
            
            # Read and add rejection reason
            content = filepath.read_text(encoding='utf-8')
            
            if reason:
                # Add rejection reason to frontmatter
                rejection_note = f"\n\n## Rejection\n\n**Rejected:** {datetime.now().isoformat()}\n**Reason:** {reason}\n"
                content += rejection_note
            
            # Move to rejected
            dest = self.rejected_dir / filepath.name
            filepath.rename(dest)
            
            # Write updated content
            dest.write_text(content, encoding='utf-8')
            
            logger.info(f"Rejected file: {filepath.name}")
            
            self._log_action('reject_file', {
                'file': filepath.name,
                'reason': reason
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error rejecting file: {e}")
            return False
    
    def _move_to_done(self, filepath: Path) -> bool:
        """
        Move a file to Done folder
        
        Args:
            filepath: Path to file to move
            
        Returns:
            bool: True if successful
        """
        try:
            if not filepath.exists():
                return False
            
            dest = self.done_dir / filepath.name
            
            # Handle duplicate filenames
            counter = 1
            while dest.exists():
                stem = filepath.stem
                suffix = filepath.suffix
                dest = self.done_dir / f"{stem}_{counter}{suffix}"
                counter += 1
            
            shutil.move(str(filepath), str(dest))
            logger.info(f"Moved to Done: {filepath.name} -> {dest.name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error moving to Done: {e}")
            return False
    
    def _check_expired_approvals(self, pending_files: List[Path]) -> List[Path]:
        """
        Check for expired approval requests
        
        Args:
            pending_files: List of pending approval files
            
        Returns:
            List[Path]: List of expired files
        """
        expired = []
        now = datetime.now()
        
        for filepath in pending_files:
            try:
                content = filepath.read_text(encoding='utf-8')
                frontmatter = self._extract_frontmatter(content)
                
                expires_str = frontmatter.get('expires')
                if expires_str:
                    expires = datetime.fromisoformat(expires_str)
                    if now > expires:
                        expired.append(filepath)
                        logger.warning(f"Expired approval: {filepath.name}")
                        
                        # Add expiration note
                        content += f"\n\n## Expired\n\n*This approval request expired on {expires.isoformat()}*\n"
                        filepath.write_text(content, encoding='utf-8')
                        
            except Exception as e:
                logger.error(f"Error checking expiration for {filepath}: {e}")
        
        return expired
    
    def _extract_frontmatter(self, content: str) -> Dict[str, Any]:
        """
        Extract YAML frontmatter from markdown
        
        Args:
            content: Markdown content
            
        Returns:
            Dict: Frontmatter dictionary
        """
        frontmatter = {}
        
        # Match frontmatter block
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if match:
            fm_text = match.group(1)
            
            # Parse key-value pairs
            for line in fm_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Convert types
                    if value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                    elif value.isdigit():
                        value = int(value)
                    
                    frontmatter[key] = value
        
        return frontmatter
    
    def _log_action(self, action_type: str, details: Dict[str, Any]) -> None:
        """Log action to vault logs"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'actor': 'approval_workflow_skill',
            'action_type': action_type,
            'details': details
        }
        
        log_file = self.logs_dir / f"approval_workflow_{datetime.now().strftime('%Y-%m-%d')}.json"
        
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
        pending = self.check_pending_approvals()
        approved = self.check_approved_files()
        rejected = self.check_rejected_files()
        
        return {
            'vault_path': str(self.vault_path),
            'pending_count': len(pending),
            'approved_count': len(approved),
            'rejected_count': len(rejected),
            'registered_handlers': list(self.action_handlers.keys()),
            'expiration_check_enabled': self.expiration_check_enabled
        }
    
    def get_approval_summary(self) -> Dict[str, Any]:
        """
        Get summary of all approval states
        
        Returns:
            Dict: Approval summary
        """
        pending = self.check_pending_approvals()
        approved = self.check_approved_files()
        rejected = self.check_rejected_files()
        
        # Categorize pending by action type
        pending_by_type = {}
        for filepath in pending:
            content = filepath.read_text(encoding='utf-8')
            frontmatter = self._extract_frontmatter(content)
            action_type = frontmatter.get('action', 'unknown')
            
            if action_type not in pending_by_type:
                pending_by_type[action_type] = []
            pending_by_type[action_type].append(filepath.name)
        
        return {
            'total_pending': len(pending),
            'total_approved': len(approved),
            'total_rejected': len(rejected),
            'pending_by_type': pending_by_type,
            'approved_files': [f.name for f in approved],
            'rejected_files': [f.name for f in rejected]
        }


# CLI interface
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Approval Workflow Skill')
    parser.add_argument('--vault', type=str, help='Path to Obsidian vault')
    parser.add_argument('--status', action='store_true', help='Show approval status')
    parser.add_argument('--summary', action='store_true', help='Show approval summary')
    parser.add_argument('--process', action='store_true', help='Process approved files')
    parser.add_argument('--check', action='store_true', help='Check pending approvals')
    
    args = parser.parse_args()
    
    skill = ApprovalWorkflowSkill(vault_path=args.vault)
    
    if args.status:
        status = skill.get_status()
        print("Approval Workflow Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")
        sys.exit(0)
    
    if args.summary:
        summary = skill.get_approval_summary()
        print("Approval Summary:")
        print(f"  Pending: {summary['total_pending']}")
        print(f"  Approved: {summary['total_approved']}")
        print(f"  Rejected: {summary['total_rejected']}")
        if summary['pending_by_type']:
            print("\nPending by Type:")
            for action_type, files in summary['pending_by_type'].items():
                print(f"  {action_type}: {len(files)}")
        sys.exit(0)
    
    if args.process:
        print("Processing approved files...")
        results = skill.process_approved_files()
        print(f"Processed {len(results)} file(s):")
        for result in results:
            status = '✓' if result['success'] else '✗'
            print(f"  {status} {result['filename']}")
        sys.exit(0)
    
    if args.check:
        print("Checking pending approvals...")
        pending = skill.check_pending_approvals()
        if pending:
            print(f"Found {len(pending)} pending approval(s):")
            for f in pending:
                print(f"  - {f.name}")
        else:
            print("No pending approvals")
        sys.exit(0)
    
    # Default: show help
    parser.print_help()
