"""
File System Watcher Module

Specification: FILESYSTEM-WATCHER-001
Purpose: Monitor a folder for new files and create action files in Obsidian vault.

This watcher is useful for:
- Testing the AI Employee system without Gmail API setup
- Manual file drops for processing
- Monitoring shared folders or cloud sync directories
"""

import os
import sys
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("Warning: watchdog not installed. File system watcher will use polling mode.")

from watchers.base_watcher import BaseWatcher


class FileDropHandler(FileSystemEventHandler):
    """
    Event handler for file system watcher.
    
    Processes file creation events and triggers the watcher.
    """
    
    def __init__(self, watcher_callback):
        """
        Initialize the handler.
        
        Args:
            watcher_callback: Function to call when new file detected
        """
        self.watcher_callback = watcher_callback
        self.processed_files = set()
    
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        if event.src_path not in self.processed_files:
            self.processed_files.add(event.src_path)
            self.watcher_callback(event.src_path)


class FilesystemWatcher(BaseWatcher):
    """
    File System Watcher implementation.
    
    Monitors a folder for new files and creates action files
    in the Obsidian vault Needs_Action folder.
    """
    
    def __init__(
        self,
        vault_path: str,
        watch_folder: Optional[str] = None,
        check_interval: int = 30,
        use_polling: bool = True
    ):
        """
        Initialize the File System Watcher.
        
        Args:
            vault_path: Path to Obsidian vault root
            watch_folder: Folder to monitor (default: vault/Inbox)
            check_interval: Seconds between checks (default: 30)
            use_polling: Use polling instead of events (default: True)
        """
        super().__init__(vault_path, check_interval)
        
        # Set watch folder
        self.watch_folder = Path(watch_folder) if watch_folder else self.vault_path / 'Inbox'
        self.watch_folder.mkdir(parents=True, exist_ok=True)
        
        # Track processed files by hash
        self.processed_hashes = set()
        self._load_processed_hashes()
        
        # Setup watchdog if available
        self.observer = None
        if WATCHDOG_AVAILABLE and not use_polling:
            self._setup_watchdog()
    
    def _load_processed_hashes(self) -> None:
        """Load previously processed file hashes from cache."""
        cache_file = self.vault_path / '.cache' / f'{self.__class__.__name__}_processed.json'
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    self.processed_hashes = set(data.get('hashes', []))
                    self.processed_ids = set(data.get('ids', []))
                self.logger.info(f"Loaded {len(self.processed_hashes)} file hashes from cache")
            except Exception as e:
                self.logger.warning(f"Could not load processed hashes cache: {e}")
                self.processed_hashes = set()
        else:
            self.processed_hashes = set()
    
    def _save_processed_hashes(self) -> None:
        """Save processed file hashes to cache file."""
        cache_file = self.vault_path / '.cache' / f'{self.__class__.__name__}_processed.json'
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(cache_file, 'w') as f:
                json.dump({
                    'hashes': list(self.processed_hashes),
                    'ids': list(self.processed_ids)
                }, f)
        except Exception as e:
            self.logger.error(f"Could not save processed hashes cache: {e}")
    
    def _setup_watchdog(self) -> None:
        """Setup watchdog observer for event-based monitoring."""
        try:
            handler = FileDropHandler(self._process_file)
            self.observer = Observer()
            self.observer.schedule(handler, str(self.watch_folder), recursive=False)
            self.observer.start()
            self.logger.info(f"Watchdog observer started for {self.watch_folder}")
        except Exception as e:
            self.logger.warning(f"Could not start watchdog observer: {e}")
            self.observer = None
    
    def _calculate_file_hash(self, filepath: Path) -> str:
        """
        Calculate SHA256 hash of a file.
        
        Args:
            filepath: Path to file
            
        Returns:
            str: SHA256 hash hex string
        """
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _process_file(self, filepath: str) -> None:
        """
        Process a newly detected file.
        
        Args:
            filepath: Path to the new file
        """
        try:
            file_path = Path(filepath)
            
            # Skip hidden files and temp files
            if file_path.name.startswith('.') or file_path.suffix in ['.tmp', '.part', '.crdownload']:
                return
            
            # Calculate hash to check if already processed
            file_hash = self._calculate_file_hash(file_path)
            
            if file_hash in self.processed_hashes:
                self.logger.debug(f"File already processed: {file_path.name}")
                return
            
            # Create action file
            self.processed_hashes.add(file_hash)
            self.create_action_file({
                'path': str(file_path),
                'name': file_path.name,
                'hash': file_hash
            })
            
        except Exception as e:
            self.logger.error(f"Error processing file {filepath}: {e}")
    
    def check_for_updates(self) -> List[Dict[str, Any]]:
        """
        Check watch folder for new files (polling mode).
        
        Returns:
            List[Dict]: List of new file dictionaries
        """
        new_files = []
        
        try:
            # Get all files in watch folder
            files = [f for f in self.watch_folder.iterdir() if f.is_file()]
            
            for file_path in files:
                # Skip hidden files and temp files
                if file_path.name.startswith('.') or file_path.suffix in ['.tmp', '.part', '.crdownload']:
                    continue
                
                # Calculate hash
                try:
                    file_hash = self._calculate_file_hash(file_path)
                except (PermissionError, OSError) as e:
                    self.logger.warning(f"Could not read file {file_path}: {e}")
                    continue
                
                # Check if already processed
                if file_hash not in self.processed_hashes:
                    new_files.append({
                        'path': str(file_path),
                        'name': file_path.name,
                        'hash': file_hash
                    })
                    self.processed_hashes.add(file_hash)
            
            if new_files:
                self.logger.info(f"Found {len(new_files)} new file(s) in watch folder")
            
            return new_files
            
        except Exception as e:
            self.logger.error(f"Error checking watch folder: {e}")
            return []
    
    def create_action_file(self, item: Dict[str, Any]) -> Path:
        """
        Create a Markdown action file for a dropped file.
        
        Args:
            item: File dictionary with 'path', 'name', 'hash'
            
        Returns:
            Path: Path to created action file
        """
        try:
            file_path = Path(item['path'])
            file_name = item['name']
            file_hash = item['hash']
            
            # Get file metadata
            try:
                stat = file_path.stat()
                file_size = stat.st_size
                modified_time = datetime.fromtimestamp(stat.st_mtime).isoformat()
            except Exception as e:
                self.logger.warning(f"Could not get file stats: {e}")
                file_size = 0
                modified_time = datetime.now().isoformat()
            
            # Determine file type
            file_type = file_path.suffix.lower().lstrip('.')
            if not file_type:
                file_type = 'unknown'
            
            # Create metadata for frontmatter
            metadata = {
                'type': 'file_drop',
                'original_name': file_name,
                'file_type': file_type,
                'file_size': file_size,
                'file_hash': file_hash[:16],  # First 16 chars of hash
                'received': datetime.now().isoformat(),
                'modified': modified_time,
                'status': 'pending'
            }
            
            # Generate suggested actions based on file type
            suggested_actions = self._generate_suggested_actions(file_type, file_name)
            
            # Build content
            content = f"""
**File:** {file_name}
**Type:** {file_type}
**Size:** {self._format_file_size(file_size)}
**Modified:** {modified_time}

---

File is ready for processing.
"""
            
            # Generate full Markdown content
            markdown_content = self._create_action_file_content(
                metadata=metadata,
                content=content,
                suggested_actions=suggested_actions
            )
            
            # Generate filename
            filename = self._generate_filename('FILE', file_hash[:12])
            filepath = self.needs_action / filename
            
            # Write file
            if not self.dry_run:
                filepath.write_text(markdown_content, encoding='utf-8')
                self.logger.info(f"Created action file: {filepath}")
            
            # Save hashes after each file
            self._save_processed_hashes()
            
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error creating action file: {e}")
            raise
    
    def _generate_suggested_actions(self, file_type: str, file_name: str) -> List[str]:
        """
        Generate suggested actions based on file type.
        
        Args:
            file_type: File extension
            file_name: Original file name
            
        Returns:
            List[str]: List of suggested action strings
        """
        actions = []
        
        # Type-specific actions
        type_actions = {
            'pdf': ['Review document content', 'Extract key information', 'Archive after processing'],
            'doc': ['Review document', 'Edit if needed', 'Convert to Markdown if appropriate'],
            'docx': ['Review document', 'Edit if needed', 'Convert to Markdown if appropriate'],
            'txt': ['Read text content', 'Process information', 'Archive or delete'],
            'csv': ['Analyze data', 'Import to database if needed', 'Generate insights'],
            'xlsx': ['Review spreadsheet', 'Extract relevant data', 'Create summary'],
            'jpg': ['Review image', 'Add to media library', 'Extract text if needed (OCR)'],
            'jpeg': ['Review image', 'Add to media library', 'Extract text if needed (OCR)'],
            'png': ['Review image', 'Add to media library', 'Extract text if needed (OCR)'],
            'zip': ['Extract contents', 'Review extracted files', 'Organize appropriately'],
            'rar': ['Extract contents', 'Review extracted files', 'Organize appropriately'],
            'md': ['Review Markdown content', 'Move to appropriate vault folder', 'Update links if needed'],
        }
        
        actions = type_actions.get(file_type, [
            'Review file content',
            'Determine appropriate action',
            'Archive or process as needed'
        ])
        
        # Check for specific patterns in filename
        name_lower = file_name.lower()
        
        if 'invoice' in name_lower or 'receipt' in name_lower:
            actions.insert(0, "Process as financial document")
            actions.insert(1, "Extract payment information")
        
        if 'contract' in name_lower or 'agreement' in name_lower:
            actions.insert(0, "Review legal document carefully")
            actions.insert(1, "Flag for human review if needed")
        
        if 'resume' in name_lower or 'cv' in name_lower:
            actions.insert(0, "Review candidate information")
            actions.insert(1, "Extract key qualifications")
        
        return actions
    
    def _format_file_size(self, size_bytes: int) -> str:
        """
        Format file size in human-readable format.
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            str: Formatted size string
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
    def run(self) -> None:
        """
        Main run loop for the file system watcher.
        
        Uses polling by default, or watchdog events if available.
        """
        if self.observer:
            # Watchdog mode - observer is already running
            self.logger.info(f"Starting {self.__class__.__name__} (watchdog mode)")
            self.logger.info(f"Watch folder: {self.watch_folder}")
            
            try:
                while True:
                    time.sleep(self.check_interval)
            except KeyboardInterrupt:
                self.logger.info("Shutting down...")
                self.observer.stop()
                self.observer.join()
                self._save_processed_hashes()
        else:
            # Polling mode - use parent implementation
            super().run()
    
    def stop(self) -> None:
        """Stop the watcher and cleanup resources."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
        self._save_processed_hashes()
        self.logger.info("Filesystem watcher stopped")


# Import time for the run method
import time


def main():
    """
    Main entry point for running File System Watcher standalone.
    
    Usage:
        python filesystem_watcher.py [--vault PATH] [--watch-folder PATH] [--dry-run]
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='File System Watcher for AI Employee')
    parser.add_argument(
        '--vault',
        type=str,
        default=os.getenv('OBSIDIAN_VAULT_PATH', 'D:\\Hackathon-0\\AI_Employee_Vault'),
        help='Path to Obsidian vault'
    )
    parser.add_argument(
        '--watch-folder',
        type=str,
        default=None,
        help='Folder to monitor (default: vault/Inbox)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=30,
        help='Check interval in seconds (default: 30)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in dry-run mode (no side effects)'
    )
    parser.add_argument(
        '--use-watchdog',
        action='store_true',
        help='Use watchdog for event-based monitoring (requires watchdog package)'
    )
    
    args = parser.parse_args()
    
    # Create watcher
    watcher = FilesystemWatcher(
        vault_path=args.vault,
        watch_folder=args.watch_folder,
        check_interval=args.interval,
        use_polling=not args.use_watchdog
    )
    
    # Set dry run mode
    if args.dry_run:
        watcher.set_dry_run(True)
    
    # Start watching
    try:
        watcher.run()
    except KeyboardInterrupt:
        print("\nShutting down File System Watcher...")
        watcher.stop()
        print("Goodbye!")


if __name__ == '__main__':
    main()
