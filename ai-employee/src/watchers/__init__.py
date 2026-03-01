"""
Watchers Package

This package contains all watcher implementations for the AI Employee system.

Watchers are lightweight Python scripts that run continuously in the background,
monitoring various inputs (Gmail, WhatsApp, file systems) and creating actionable
files for Qwen Code to process.

Available Watchers:
- GmailWatcher: Monitor Gmail for new unread important emails
- FilesystemWatcher: Monitor a folder for new files
- WhatsAppWatcher: Monitor WhatsApp Web (requires Playwright)

Usage:
    from watchers import GmailWatcher, FilesystemWatcher
    
    watcher = GmailWatcher(vault_path="/path/to/vault")
    watcher.run()
"""

from watchers.base_watcher import BaseWatcher
from watchers.gmail_watcher import GmailWatcher
from watchers.filesystem_watcher import FilesystemWatcher

__all__ = [
    'BaseWatcher',
    'GmailWatcher',
    'FilesystemWatcher',
]

# Optional imports
try:
    from watchers.whatsapp_watcher import WhatsAppWatcher
    __all__.append('WhatsAppWatcher')
except ImportError:
    pass

__version__ = '1.0.0'
