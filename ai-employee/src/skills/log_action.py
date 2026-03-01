"""
Log Action Skill

Specification: AGENT-SKILLS-001 (log_action)

Purpose: Write action to audit log

Input:
    - action_type: str
    - actor: str (qwen_code/watcher/orchestrator)
    - target: str
    - parameters: dict
    - result: str (success/failure/pending)
    
Output:
    - JSON entry in /Logs/{date}.json
    
Schema:
{
    "timestamp": "ISO8601",
    "action_type": "string",
    "actor": "string",
    "target": "string",
    "parameters": {},
    "approval_status": "string",
    "approved_by": "string|null",
    "result": "string"
}
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict


@dataclass
class LogEntry:
    """Represents a single audit log entry."""
    
    timestamp: str
    action_type: str
    actor: str
    target: str
    parameters: Dict[str, Any]
    approval_status: str = "not_required"
    approved_by: Optional[str] = None
    result: str = "success"
    message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


def get_log_file_path(vault_path: str) -> Path:
    """
    Get the path to today's log file.
    
    Args:
        vault_path: Path to vault root
        
    Returns:
        Path: Path to log file
    """
    vault = Path(vault_path)
    logs_dir = vault / 'Logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    date_str = datetime.now().strftime('%Y-%m-%d')
    return logs_dir / f"{date_str}.json"


def load_log_entries(vault_path: str) -> List[Dict[str, Any]]:
    """
    Load existing log entries for today.
    
    Args:
        vault_path: Path to vault root
        
    Returns:
        List[Dict]: List of existing log entries
    """
    log_file = get_log_file_path(vault_path)
    
    if not log_file.exists():
        return []
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        # If file is corrupted, start fresh
        print(f"Warning: Could not load log file: {e}")
        return []


def save_log_entries(vault_path: str, entries: List[Dict[str, Any]]) -> bool:
    """
    Save log entries to today's log file.
    
    Args:
        vault_path: Path to vault root
        entries: List of log entries to save
        
    Returns:
        bool: True if successful, False otherwise
    """
    log_file = get_log_file_path(vault_path)
    
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(entries, f, indent=2, default=str)
        return True
    except IOError as e:
        print(f"Error saving log file: {e}")
        return False


def log_action(
    vault_path: str,
    action_type: str,
    actor: str,
    target: str,
    parameters: Optional[Dict[str, Any]] = None,
    approval_status: str = "not_required",
    approved_by: Optional[str] = None,
    result: str = "success",
    message: Optional[str] = None
) -> LogEntry:
    """
    Write an action to the audit log.
    
    Args:
        vault_path: Path to Obsidian vault root
        action_type: Type of action (e.g., "email_processed", "file_created")
        actor: Who/what performed the action (e.g., "qwen_code", "gmail_watcher")
        target: What the action was performed on (e.g., file path, email ID)
        parameters: Additional parameters/details about the action
        approval_status: "not_required", "pending", "approved", "rejected"
        approved_by: Who approved the action (if applicable)
        result: "success", "failure", "pending"
        message: Optional human-readable message
        
    Returns:
        LogEntry: The created log entry
    """
    # Create log entry
    entry = LogEntry(
        timestamp=datetime.now().isoformat(),
        action_type=action_type,
        actor=actor,
        target=target,
        parameters=parameters or {},
        approval_status=approval_status,
        approved_by=approved_by,
        result=result,
        message=message
    )
    
    # Load existing entries
    entries = load_log_entries(vault_path)
    
    # Add new entry
    entries.append(entry.to_dict())
    
    # Save updated entries
    save_log_entries(vault_path, entries)
    
    return entry


def get_recent_logs(
    vault_path: str,
    limit: int = 10,
    actor: Optional[str] = None,
    action_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get recent log entries with optional filtering.
    
    Args:
        vault_path: Path to vault root
        limit: Maximum number of entries to return
        actor: Filter by actor (optional)
        action_type: Filter by action type (optional)
        
    Returns:
        List[Dict]: Filtered log entries
    """
    entries = load_log_entries(vault_path)
    
    # Apply filters
    if actor:
        entries = [e for e in entries if e.get('actor') == actor]
    if action_type:
        entries = [e for e in entries if e.get('action_type') == action_type]
    
    # Return most recent
    return entries[-limit:] if len(entries) > limit else entries


def get_stats_for_date(vault_path: str, date_str: Optional[str] = None) -> Dict[str, Any]:
    """
    Get statistics for a specific date.
    
    Args:
        vault_path: Path to vault root
        date_str: Date string in YYYY-MM-DD format (default: today)
        
    Returns:
        Dict: Statistics including counts by actor, action type, result
    """
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    log_file = Path(vault_path) / 'Logs' / f"{date_str}.json"
    
    if not log_file.exists():
        return {'error': 'No logs found for date', 'date': date_str}
    
    entries = load_log_entries(vault_path)
    
    stats = {
        'date': date_str,
        'total_actions': len(entries),
        'by_result': {},
        'by_actor': {},
        'by_action_type': {},
        'requiring_approval': 0,
        'errors': 0
    }
    
    for entry in entries:
        # Count by result
        result = entry.get('result', 'unknown')
        stats['by_result'][result] = stats['by_result'].get(result, 0) + 1
        
        # Count by actor
        actor = entry.get('actor', 'unknown')
        stats['by_actor'][actor] = stats['by_actor'].get(actor, 0) + 1
        
        # Count by action type
        action_type = entry.get('action_type', 'unknown')
        stats['by_action_type'][action_type] = stats['by_action_type'].get(action_type, 0) + 1
        
        # Count approvals
        if entry.get('approval_status') != 'not_required':
            stats['requiring_approval'] += 1
        
        # Count errors
        if result == 'failure':
            stats['errors'] += 1
    
    return stats


def main():
    """
    Main entry point for testing the skill.
    
    Usage:
        python log_action.py <vault_path> <action_type> <actor> <target>
    """
    if len(sys.argv) < 5:
        print("Usage: python log_action.py <vault_path> <action_type> <actor> <target>")
        sys.exit(1)
    
    vault_path = sys.argv[1]
    action_type = sys.argv[2]
    actor = sys.argv[3]
    target = sys.argv[4]
    
    entry = log_action(
        vault_path=vault_path,
        action_type=action_type,
        actor=actor,
        target=target,
        parameters={'test': True}
    )
    
    print(f"Log entry created: {entry.to_dict()}")


if __name__ == '__main__':
    main()
