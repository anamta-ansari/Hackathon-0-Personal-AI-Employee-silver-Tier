"""
Move to Done Skill

Specification: AGENT-SKILLS-003

Purpose: Archive completed items to /Done/ folder

Input:
    - file_path: Path to file in Needs_Action, Approved, or other folder
    - vault_path: Path to vault root
    
Output:
    - File moved to /Done/ with timestamp
    - Status updated in file frontmatter
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import re


def move_to_done(
    file_path: str,
    vault_path: str,
    add_completion_note: bool = True,
    completion_note: Optional[str] = None
) -> Dict[str, Any]:
    """
    Move a file to the Done folder and update its status.
    
    Args:
        file_path: Path to file to move
        vault_path: Path to Obsidian vault root
        add_completion_note: Whether to add completion metadata
        completion_note: Optional custom completion note
        
    Returns:
        Dict: Result with success status and new file path
    """
    result = {
        'success': False,
        'original_path': file_path,
        'new_path': None,
        'error': None
    }
    
    try:
        # Convert to Path objects
        src_path = Path(file_path)
        vault = Path(vault_path)
        done_dir = vault / 'Done'
        
        # Ensure Done directory exists
        done_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate source file exists
        if not src_path.exists():
            result['error'] = f"File not found: {file_path}"
            return result
        
        # Read original content
        content = src_path.read_text(encoding='utf-8')
        
        # Add completion metadata if requested
        if add_completion_note:
            content = add_completion_metadata(content, completion_note)
        
        # Generate new filename with completion timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_filename = f"DONE_{src_path.stem}_{timestamp}{src_path.suffix}"
        dst_path = done_dir / new_filename
        
        # Write to destination
        dst_path.write_text(content, encoding='utf-8')
        
        # Remove original file
        src_path.unlink()
        
        result['success'] = True
        result['new_path'] = str(dst_path)
        
    except Exception as e:
        result['error'] = str(e)
    
    return result


def add_completion_metadata(content: str, custom_note: Optional[str] = None) -> str:
    """
    Add completion metadata to file content.
    
    Args:
        content: Original file content
        custom_note: Optional custom completion note
        
    Returns:
        str: Updated content with completion metadata
    """
    completion_timestamp = datetime.now().isoformat()
    
    # Check if content has frontmatter
    if content.startswith('---'):
        # Find end of frontmatter
        end_match = re.search(r'\n---\n', content[3:])
        if end_match:
            # Insert completion info in frontmatter
            frontmatter_end = end_match.start() + 3
            frontmatter = content[3:frontmatter_end]
            rest = content[frontmatter_end:]
            
            # Add completion fields
            new_frontmatter = frontmatter.rstrip()
            new_frontmatter += f"\ncompleted: {completion_timestamp}\nstatus: completed\n"
            if custom_note:
                new_frontmatter += f"completion_note: {custom_note}\n"
            
            content = f"---{new_frontmatter}{rest}"
        else:
            # No proper frontmatter end, add at beginning
            completion_section = f"""---
completed: {completion_timestamp}
status: completed
---

"""
            if custom_note:
                completion_section += f"> **Completion Note:** {custom_note}\n\n"
            content = completion_section + content
    else:
        # No frontmatter, add at beginning
        completion_section = f"""---
completed: {completion_timestamp}
status: completed
---

"""
        if custom_note:
            completion_section += f"> **Completion Note:** {custom_note}\n\n"
        content = completion_section + content
    
    return content


def move_multiple_files(
    file_paths: list,
    vault_path: str,
    add_completion_note: bool = True
) -> Dict[str, Any]:
    """
    Move multiple files to Done folder.
    
    Args:
        file_paths: List of file paths to move
        vault_path: Path to vault root
        add_completion_note: Whether to add completion metadata
        
    Returns:
        Dict: Results with success count and individual results
    """
    results = {
        'total': len(file_paths),
        'successful': 0,
        'failed': 0,
        'results': []
    }
    
    for file_path in file_paths:
        result = move_to_done(file_path, vault_path, add_completion_note)
        results['results'].append(result)
        
        if result['success']:
            results['successful'] += 1
        else:
            results['failed'] += 1
    
    return results


def archive_folder_contents(
    source_folder: str,
    vault_path: str,
    pattern: Optional[str] = None,
    add_completion_note: bool = True
) -> Dict[str, Any]:
    """
    Archive all files from a source folder to Done.
    
    Args:
        source_folder: Folder to archive from (e.g., 'Needs_Action')
        vault_path: Path to vault root
        pattern: Optional glob pattern to filter files
        add_completion_note: Whether to add completion metadata
        
    Returns:
        Dict: Results with archived files
    """
    vault = Path(vault_path)
    src_dir = vault / source_folder
    
    if not src_dir.exists():
        return {
            'success': False,
            'error': f"Source folder not found: {source_folder}"
        }
    
    # Get files to archive
    if pattern:
        files = list(src_dir.glob(pattern))
    else:
        files = [f for f in src_dir.iterdir() if f.is_file()]
    
    file_paths = [str(f) for f in files]
    
    return move_multiple_files(file_paths, vault_path, add_completion_note)


def get_completion_stats(vault_path: str, days: int = 7) -> Dict[str, Any]:
    """
    Get completion statistics for the past N days.
    
    Args:
        vault_path: Path to vault root
        days: Number of days to analyze
        
    Returns:
        Dict: Statistics about completed items
    """
    from collections import defaultdict
    
    vault = Path(vault_path)
    done_dir = vault / 'Done'
    
    if not done_dir.exists():
        return {'error': 'Done folder not found'}
    
    stats = {
        'total_completed': 0,
        'by_type': defaultdict(int),
        'by_day': defaultdict(int),
        'files': []
    }
    
    cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
    
    for file_path in done_dir.iterdir():
        if not file_path.is_file():
            continue
        
        try:
            # Check file modification time
            mtime = file_path.stat().st_mtime
            if mtime < cutoff_date:
                continue
            
            # Read file to get type
            content = file_path.read_text(encoding='utf-8')
            
            # Extract type from frontmatter
            type_match = re.search(r'type:\s*(\w+)', content)
            file_type = type_match.group(1) if type_match else 'unknown'
            
            # Extract completion date
            completed_match = re.search(r'completed:\s*([\d\-T:]+)', content)
            if completed_match:
                try:
                    completed_date = completed_match.group(1)[:10]  # YYYY-MM-DD
                    stats['by_day'][completed_date] += 1
                except:
                    pass
            
            stats['total_completed'] += 1
            stats['by_type'][file_type] += 1
            stats['files'].append({
                'name': file_path.name,
                'type': file_type,
                'completed': completed_match.group(1) if completed_match else 'unknown'
            })
            
        except Exception as e:
            continue
    
    # Convert defaultdicts to regular dicts for JSON serialization
    stats['by_type'] = dict(stats['by_type'])
    stats['by_day'] = dict(stats['by_day'])
    
    return stats


def main():
    """
    Main entry point for testing the skill.
    
    Usage:
        python move_to_done.py <file_path> <vault_path>
    """
    import json
    
    if len(sys.argv) < 3:
        print("Usage: python move_to_done.py <file_path> <vault_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    vault_path = sys.argv[2]
    
    result = move_to_done(file_path, vault_path)
    print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()
