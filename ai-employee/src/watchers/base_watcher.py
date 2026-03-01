"""
Base Watcher Module

Specification: BASE-WATCHER-001
Purpose: Provide abstract base class for all watcher implementations.

All watchers must inherit from this class and implement:
- check_for_updates(): Returns list of new items to process
- create_action_file(item): Creates .md file in Needs_Action folder
"""

import time
import logging
from pathlib import Path
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Any, Optional
import json


class BaseWatcher(ABC):
    """
    Abstract base class for all watcher implementations.
    
    Attributes:
        vault_path (Path): Path to Obsidian vault root
        needs_action (Path): Path to Needs_Action folder
        check_interval (int): Seconds between checks
        logger (logging.Logger): Instance logger
        processed_ids (set): Track processed item IDs to avoid duplicates
    """
    
    def __init__(self, vault_path: str, check_interval: int = 60):
        """
        Initialize the base watcher.
        
        Args:
            vault_path: Path to the Obsidian vault root directory
            check_interval: Time in seconds between polling checks (default: 60)
        """
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / 'Needs_Action'
        self.check_interval = check_interval
        self.processed_ids: set = set()
        self.dry_run = False
        
        # Ensure Needs_Action folder exists
        self.needs_action.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Load processed IDs from cache if exists
        self._load_processed_ids()
        
    def _setup_logging(self) -> logging.Logger:
        """
        Setup logging configuration for the watcher.
        
        Returns:
            logging.Logger: Configured logger instance
        """
        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(logging.INFO)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        # Add handler to logger
        if not logger.handlers:
            logger.addHandler(console_handler)
        
        return logger
    
    def _load_processed_ids(self) -> None:
        """Load previously processed IDs from cache file."""
        cache_file = self.vault_path / '.cache' / f'{self.__class__.__name__}_processed.json'
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    self.processed_ids = set(json.load(f))
                self.logger.info(f"Loaded {len(self.processed_ids)} processed IDs from cache")
            except Exception as e:
                self.logger.warning(f"Could not load processed IDs cache: {e}")
                self.processed_ids = set()
        else:
            self.processed_ids = set()
    
    def _save_processed_ids(self) -> None:
        """Save processed IDs to cache file."""
        cache_file = self.vault_path / '.cache' / f'{self.__class__.__name__}_processed.json'
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(list(self.processed_ids), f)
        except Exception as e:
            self.logger.error(f"Could not save processed IDs cache: {e}")
    
    def _generate_filename(self, item_type: str, item_id: str) -> str:
        """
        Generate a unique filename for an action file.
        
        Args:
            item_type: Type prefix (EMAIL, WHATSAPP, FILE, etc.)
            item_id: Unique identifier for the item
            
        Returns:
            str: Filename in format {TYPE}_{id}_{timestamp}.md
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        # Sanitize item_id to be filesystem-safe
        safe_id = ''.join(c if c.isalnum() or c in '-_' else '_' for c in item_id)
        return f"{item_type}_{safe_id}_{timestamp}.md"
    
    def _create_action_file_content(self, metadata: dict, content: str, suggested_actions: List[str]) -> str:
        """
        Create standardized Markdown content for action files.
        
        Args:
            metadata: Dictionary of frontmatter metadata
            content: Main content body
            suggested_actions: List of suggested action items
            
        Returns:
            str: Complete Markdown content with YAML frontmatter
        """
        # Build YAML frontmatter
        frontmatter = "---\n"
        for key, value in metadata.items():
            frontmatter += f"{key}: {value}\n"
        frontmatter += "---\n\n"
        
        # Build suggested actions section
        actions_text = ""
        if suggested_actions:
            actions_text = "\n## Suggested Actions\n"
            for action in suggested_actions:
                actions_text += f"- [ ] {action}\n"
        
        return f"{frontmatter}## Content\n{content}{actions_text}"
    
    @abstractmethod
    def check_for_updates(self) -> List[Any]:
        """
        Check for new items to process.
        
        Returns:
            List[Any]: List of new items (format depends on implementation)
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement check_for_updates()")
    
    @abstractmethod
    def create_action_file(self, item: Any) -> Path:
        """
        Create a Markdown action file for an item.
        
        Args:
            item: Item to create action file for
            
        Returns:
            Path: Path to created action file
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement create_action_file()")
    
    def run(self) -> None:
        """
        Main run loop for the watcher.
        
        Continuously checks for updates and creates action files.
        Handles errors gracefully to prevent watcher death.
        """
        self.logger.info(f"Starting {self.__class__.__name__}")
        self.logger.info(f"Vault path: {self.vault_path}")
        self.logger.info(f"Check interval: {self.check_interval} seconds")
        
        if self.dry_run:
            self.logger.info("Running in DRY RUN mode - no files will be created")
        
        iteration = 0
        while True:
            iteration += 1
            try:
                self.logger.debug(f"Iteration {iteration}: Checking for updates...")
                
                # Check for new items
                items = self.check_for_updates()
                
                if items:
                    self.logger.info(f"Found {len(items)} new item(s) to process")
                    
                    for item in items:
                        if self.dry_run:
                            self.logger.info(f"[DRY RUN] Would process item: {item}")
                        else:
                            try:
                                filepath = self.create_action_file(item)
                                self.logger.info(f"Created action file: {filepath.name}")
                            except Exception as e:
                                self.logger.error(f"Error creating action file: {e}")
                else:
                    self.logger.debug("No new items found")
                
                # Save processed IDs periodically (every 10 iterations)
                if iteration % 10 == 0:
                    self._save_processed_ids()
                
            except Exception as e:
                self.logger.error(f"Error in watcher loop: {e}", exc_info=True)
            
            # Wait before next check
            time.sleep(self.check_interval)
    
    def set_dry_run(self, dry_run: bool) -> None:
        """
        Enable or disable dry run mode.
        
        Args:
            dry_run: If True, log actions without creating files
        """
        self.dry_run = dry_run
        self.logger.info(f"Dry run mode: {dry_run}")
