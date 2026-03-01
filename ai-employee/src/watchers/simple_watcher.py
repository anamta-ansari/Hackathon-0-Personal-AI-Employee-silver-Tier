"""
Simple Filesystem Watcher - For Bronze Tier Demo

This is a simplified, reliable watcher for demonstration purposes.
"""

import time
import hashlib
import logging
from pathlib import Path
from datetime import datetime
import json
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('watcher.log')
    ]
)
logger = logging.getLogger(__name__)


def calculate_hash(filepath: Path) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def load_processed(cache_file: Path) -> set:
    """Load previously processed file hashes."""
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                return set(json.load(f))
        except:
            pass
    return set()


def save_processed(cache_file: Path, hashes: set) -> None:
    """Save processed file hashes."""
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump(list(hashes), f)


def create_action_file(vault_path: Path, file_path: Path, file_hash: str) -> Path:
    """Create an action file for the detected file."""
    needs_action = vault_path / 'Needs_Action'
    needs_action.mkdir(parents=True, exist_ok=True)
    
    # Get file info
    stat = file_path.stat()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_hash = file_hash[:16]
    
    # Create action file
    action_file = needs_action / f"FILE_{safe_hash}_{timestamp}.md"
    
    content = f"""---
type: file_drop
original_name: {file_path.name}
file_type: {file_path.suffix.lstrip('.')}
file_size: {stat.st_size}
file_hash: {safe_hash}
received: {datetime.now().isoformat()}
status: pending
---

## Content

**File:** {file_path.name}
**Type:** {file_path.suffix.lstrip('.')}
**Size:** {stat.st_size} bytes

---

File is ready for processing.

## Suggested Actions
- [ ] Review file content
- [ ] Process information
- [ ] Archive or take action
"""
    
    action_file.write_text(content, encoding='utf-8')
    logger.info(f"Created action file: {action_file.name}")
    return action_file


def main():
    """Main watcher loop."""
    # Parse arguments
    vault_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('AI_Employee_Vault')
    watch_folder = vault_path / 'Inbox'
    check_interval = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    # Ensure folders exist
    watch_folder.mkdir(parents=True, exist_ok=True)
    (vault_path / 'Needs_Action').mkdir(parents=True, exist_ok=True)
    
    # Load processed files
    cache_file = vault_path / '.cache' / 'simple_watcher.json'
    processed_hashes = load_processed(cache_file)
    
    logger.info(f"Simple Filesystem Watcher started")
    logger.info(f"Monitoring: {watch_folder}")
    logger.info(f"Check interval: {check_interval} seconds")
    logger.info(f"Previously processed files: {len(processed_hashes)}")
    
    iteration = 0
    while True:
        iteration += 1
        try:
            # Get all files in watch folder
            files = [f for f in watch_folder.iterdir() if f.is_file()]
            
            new_count = 0
            for file_path in files:
                # Skip hidden and temp files
                if file_path.name.startswith('.') or file_path.suffix in ['.tmp', '.part']:
                    continue
                
                # Calculate hash
                try:
                    file_hash = calculate_hash(file_path)
                except Exception as e:
                    logger.warning(f"Could not hash {file_path.name}: {e}")
                    continue
                
                # Check if already processed
                if file_hash not in processed_hashes:
                    logger.info(f"New file detected: {file_path.name}")
                    create_action_file(vault_path, file_path, file_hash)
                    processed_hashes.add(file_hash)
                    new_count += 1
            
            if new_count > 0:
                save_processed(cache_file, processed_hashes)
                logger.info(f"Processed {new_count} new file(s)")
            else:
                logger.debug(f"Iteration {iteration}: No new files")
            
        except Exception as e:
            logger.error(f"Error in watcher loop: {e}")
        
        time.sleep(check_interval)


if __name__ == '__main__':
    main()
