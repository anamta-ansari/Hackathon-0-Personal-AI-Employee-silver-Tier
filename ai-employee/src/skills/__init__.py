"""
Agent Skills Package

This package contains modular skills for Qwen Code to execute specific tasks
in the AI Employee system.

Available Skills:
- process_email: Process email action files and create plans
- update_dashboard: Refresh Dashboard.md with current vault state
- log_action: Write actions to audit log
- create_approval_request: Generate approval request files
- move_to_done: Archive completed items
"""

from .process_email import process_email
from .update_dashboard import update_dashboard
from .log_action import log_action, LogEntry
from .create_approval_request import create_approval_request
from .move_to_done import move_to_done

__all__ = [
    'process_email',
    'update_dashboard',
    'log_action',
    'LogEntry',
    'create_approval_request',
    'move_to_done',
]

__version__ = '1.0.0'
