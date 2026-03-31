"""
Create Approval Request Skill

Specification: AGENT-SKILLS-002

Purpose: Generate approval request files for actions requiring human oversight

SINGLE FILE LIFECYCLE:
- For email tasks: Approval section is added by process_email.py
- For non-email tasks: This skill updates the existing file and moves it

Input:
    - file_path: Path to existing task file (for single-file lifecycle)
    - action_type: str (email_send, payment, file_operation, etc.)
    - action_details: dict with action-specific details
    - vault_path: str path to vault root

Output:
    - Updates existing file with approval section
    - Moves file from Plans/ to Pending_Approval/
    - Returns path to updated file
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import re
import shutil


def read_frontmatter(content: str) -> Dict[str, Any]:
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


def update_frontmatter(content: str, updates: Dict[str, Any]) -> str:
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


def add_approval_section(content: str, action_type: str, 
                         action_details: Dict[str, Any],
                         priority: str = "medium") -> str:
    """
    Add an Approval Required section to the file content.

    Args:
        content: Current file content
        action_type: Type of action requiring approval
        action_details: Action-specific details
        priority: Priority level

    Returns:
        str: Updated content with approval section
    """
    if '## Approval Required' in content:
        return content  # Already has approval section

    priority_emoji = {'low': '🟢', 'medium': '🟡', 'high': '🟠', 'urgent': '🔴'}.get(priority, '🟡')
    
    details_section = build_details_section(action_type, action_details)
    instructions = build_instructions(action_type, action_details)

    approval_section = f"""
## Approval Required
*Added: {datetime.now().isoformat()}*

{priority_emoji} **Action Type:** {action_type.replace('_', ' ').title()}
**Priority:** {priority.title()}

{details_section}
## Instructions

{instructions}

**To Approve:**
1. Review the details above
2. Move this file to `/Approved/` folder
3. AI Employee will execute the action automatically

**To Reject:**
1. Move this file to `/Rejected/` folder
2. Optionally add a note explaining why

**To Modify:**
1. Edit this file with your changes
2. Move to `/Approved/` when ready
"""

    return content + approval_section


def build_details_section(action_type: str, details: Dict[str, Any]) -> str:
    """Build the details section based on action type."""
    if action_type == 'email_send' or action_type == 'email_response':
        return f"""## Email Details

| Field | Value |
|-------|-------|
| **To** | {details.get('to', 'Not specified')} |
| **Subject** | {details.get('subject', 'Not specified')} |
| **Priority** | {details.get('priority', 'normal')} |

## Email Content

{details.get('body', details.get('content', 'No content provided'))}

{f"## Attachment: {details.get('attachment', 'None')}" if details.get('attachment') else ""}
"""

    elif action_type == 'payment':
        return f"""## Payment Details

| Field | Value |
|-------|-------|
| **Amount** | ${details.get('amount', '0.00')} |
| **Recipient** | {details.get('recipient', 'Not specified')} |
| **Reference** | {details.get('reference', 'Not specified')} |
| **Due Date** | {details.get('due_date', 'Not specified')} |

## Payment Information

{details.get('description', details.get('notes', 'No additional information'))}

⚠️ **Note:** This payment requires human approval as per Company Handbook rules.
"""

    elif action_type == 'social_post':
        return f"""## Social Media Post Details

| Field | Value |
|-------|-------|
| **Platform** | {details.get('platform', 'Not specified')} |
| **Content** | {details.get('content', 'No content provided')} |
| **Scheduled Time** | {details.get('scheduled_time', 'Immediate')} |

{f"## Image/Media: {details.get('media', 'None')}" if details.get('media') else ""}
"""

    elif action_type == 'file_operation':
        return f"""## File Operation Details

| Field | Value |
|-------|-------|
| **Operation** | {details.get('operation', 'Not specified')} |
| **Source** | {details.get('source', 'Not specified')} |
| **Destination** | {details.get('destination', 'Not specified')} |

## Description

{details.get('description', details.get('notes', 'No additional information'))}
"""

    elif action_type == 'meeting_schedule':
        return f"""## Meeting Details

| Field | Value |
|-------|-------|
| **Title** | {details.get('title', 'Not specified')} |
| **Attendees** | {', '.join(details.get('attendees', []))} |
| **Proposed Time** | {details.get('proposed_time', 'Not specified')} |
| **Duration** | {details.get('duration', 'Not specified')} |

## Description

{details.get('description', details.get('notes', 'No additional information'))}
"""

    elif action_type == 'plan_execution':
        return f"""## Plan Details

| Field | Value |
|-------|-------|
| **Plan File** | {details.get('plan_file', 'Not specified')} |
| **Task File** | {details.get('task_file', 'Not specified')} |

## Action Summary

{details.get('action_summary', 'No summary provided')}
"""

    else:
        details_list = '\n'.join([f"- **{k.replace('_', ' ').title()}:** {v}" for k, v in details.items()])
        return f"""## Details

{details_list}
"""


def build_instructions(action_type: str, details: Dict[str, Any]) -> str:
    """Build instructions based on action type."""
    instructions = {
        'email_send': """This email is ready to send. Please review:
- Recipient email address is correct
- Content is appropriate and professional
- Any attachments are included""",

        'email_response': """This email response is ready to send. Please review:
- Recipient email address is correct
- Draft reply content is appropriate
- Subject line is correct
- Any attachments are included""",

        'payment': """This payment requires your authorization. Please verify:
- Amount is correct
- Recipient is legitimate
- Payment is due and authorized
- Reference/invoice number is correct""",

        'social_post': """This social media post is ready to publish. Please review:
- Content aligns with brand voice
- No typos or errors
- Timing is appropriate
- Any media attachments are correct""",

        'file_operation': """This file operation will be performed. Please confirm:
- Source file/folder exists
- Destination is correct
- Operation won't cause data loss
- You understand the consequences""",

        'meeting_schedule': """This meeting is ready to schedule. Please confirm:
- Time works with your schedule
- Attendees are appropriate
- Duration is sufficient
- Meeting purpose is clear""",

        'plan_execution': """This plan is ready to execute. Please review:
- Plan actions are appropriate
- No risks or concerns
- You understand what will be done"""
    }

    return instructions.get(action_type, """Please review this action carefully. Consider:
- Is this action appropriate?
- Are all details correct?
- Are there any risks or concerns?
- Should any modifications be made?""")


def move_file(src_path: Path, dst_dir: Path) -> Path:
    """Move a file from source to destination directory."""
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst_path = dst_dir / src_path.name
    shutil.move(str(src_path), str(dst_path))
    return dst_path


def create_approval_request(
    vault_path: str,
    action_type: str,
    action_details: Dict[str, Any],
    priority: str = "medium",
    expires_hours: int = 24,
    file_path: Optional[str] = None  # NEW: For single-file lifecycle
) -> Dict[str, Any]:
    """
    Create an approval request file or update existing file.

    SINGLE FILE LIFECYCLE MODE:
    - If file_path is provided: Update that file and move to Pending_Approval/
    - If file_path is None: Create new approval file (legacy mode)

    Args:
        vault_path: Path to Obsidian vault root
        action_type: Type of action requiring approval
        action_details: Dictionary with action-specific details
        priority: low, medium, high, urgent
        expires_hours: Hours until approval expires
        file_path: Optional path to existing file to update (single-file mode)

    Returns:
        Dict: Result with success status and file path
    """
    result = {
        'success': False,
        'file_path': None,
        'previous_location': None,
        'mode': 'single_file' if file_path else 'legacy',
        'error': None
    }

    try:
        vault = Path(vault_path)
        pending_dir = vault / 'Pending_Approval'
        pending_dir.mkdir(parents=True, exist_ok=True)

        if file_path:
            # SINGLE FILE MODE: Update existing file and move
            return _update_existing_file(
                file_path, vault, action_type, action_details,
                priority, expires_hours, result, pending_dir  # Added pending_dir parameter
            )
        else:
            # LEGACY MODE: Create new approval file
            return _create_new_file(
                vault, action_type, action_details,
                priority, expires_hours, result
            )

    except Exception as e:
        result['error'] = str(e)
        import traceback
        result['traceback'] = traceback.format_exc()

    return result


def _update_existing_file(
    file_path: str,
    vault: Path,
    action_type: str,
    action_details: Dict[str, Any],
    priority: str,
    expires_hours: int,
    result: Dict[str, Any],
    pending_dir: Path  # NEW: Pass pending_dir as parameter
) -> Dict[str, Any]:
    """Update existing file with approval section and move to Pending_Approval/."""
    src_path = Path(file_path)

    if not src_path.exists():
        result['error'] = f"File not found: {file_path}"
        return result

    # Read current content
    content = src_path.read_text(encoding='utf-8')

    # Parse existing frontmatter
    frontmatter = read_frontmatter(content)

    # Calculate expiration
    expires = datetime.now() + timedelta(hours=expires_hours)

    # Update frontmatter
    frontmatter_updates = {
        'status': 'awaiting_approval',
        'approval_requested': datetime.now().isoformat(),
        'expires': expires.isoformat(),
        'action': action_type,
        'priority': priority
    }

    # Add action details to frontmatter
    for key, value in action_details.items():
        frontmatter_updates[f'detail_{key}'] = value

    content = update_frontmatter(content, frontmatter_updates)

    # Add approval section
    content = add_approval_section(content, action_type, action_details, priority)

    # Write updated content
    src_path.write_text(content, encoding='utf-8')

    # Determine source directory to move from
    plans_dir = vault / 'Plans'
    needs_action_dir = vault / 'Needs_Action'

    if src_path.parent == plans_dir:
        result['previous_location'] = 'Plans/'
    elif src_path.parent == needs_action_dir:
        result['previous_location'] = 'Needs_Action/'
    else:
        result['previous_location'] = str(src_path.parent)

    # Move to Pending_Approval/ (using passed pending_dir parameter)
    new_path = move_file(src_path, pending_dir)

    result['success'] = True
    result['file_path'] = str(new_path)

    print(f"INFO: Updated and moved file to Pending_Approval/: {new_path.name}")

    return result


def _create_new_file(
    vault: Path,
    action_type: str,
    action_details: Dict[str, Any],
    priority: str,
    expires_hours: int,
    result: Dict[str, Any]
) -> Dict[str, Any]:
    """Create a new approval request file (legacy mode)."""
    # Generate unique filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    action_id = action_details.get('id', f"{action_type}_{timestamp}")
    safe_id = ''.join(c if c.isalnum() or c in '-_' else '_' for c in str(action_id))
    filename = f"APPROVAL_{safe_id}_{timestamp}.md"
    filepath = vault / 'Pending_Approval' / filename

    # Calculate expiration
    expires = datetime.now() + timedelta(hours=expires_hours)

    # Build sections
    details_section = build_details_section(action_type, action_details)
    instructions = build_instructions(action_type, action_details)

    # Build frontmatter
    frontmatter = {
        'type': 'approval_request',
        'action': action_type,
        'created': datetime.now().isoformat(),
        'expires': expires.isoformat(),
        'priority': priority,
        'status': 'pending'
    }

    # Add action-specific frontmatter
    for key, value in action_details.items():
        if key not in ['description', 'content']:
            frontmatter[f'detail_{key}'] = value

    # Build frontmatter string
    frontmatter_str = "---\n"
    for key, value in frontmatter.items():
        frontmatter_str += f"{key}: {value}\n"
    frontmatter_str += "---\n\n"

    # Build content
    priority_emoji = {'low': '🟢', 'medium': '🟡', 'high': '🟠', 'urgent': '🔴'}.get(priority, '🟡')

    content = f"""{frontmatter_str}# {priority_emoji} Approval Required: {action_type.replace('_', ' ').title()}

{details_section}
## Instructions

{instructions}

**To Approve:**
1. Review the details above
2. Move this file to `/Approved/` folder
3. AI Employee will execute the action automatically

**To Reject:**
1. Move this file to `/Rejected/` folder
2. Optionally add a note explaining why

**To Modify:**
1. Edit this file with your changes
2. Move to `/Approved/` when ready

---

## Metadata

- **Created:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
- **Expires:** {expires.strftime('%Y-%m-%d %H:%M')} ({expires_hours} hours)
- **Priority:** {priority.title()}

---
*Generated by AI Employee v1.0.0*
"""

    # Write file
    filepath.write_text(content, encoding='utf-8')

    result['success'] = True
    result['file_path'] = str(filepath)

    return result


def main():
    """
    Main entry point for testing the skill.

    Usage:
        python create_approval_request.py <vault_path> <action_type> [details_json] [file_path]
    """
    import json

    if len(sys.argv) < 3:
        print("Usage: python create_approval_request.py <vault_path> <action_type> [details_json] [file_path]")
        sys.exit(1)

    vault_path = sys.argv[1]
    action_type = sys.argv[2]

    # Parse details if provided
    details = {}
    if len(sys.argv) > 3:
        try:
            details = json.loads(sys.argv[3])
        except json.JSONDecodeError:
            print("Error: Invalid JSON for details")
            sys.exit(1)

    # Optional file path for single-file mode
    file_path = sys.argv[4] if len(sys.argv) > 4 else None

    result = create_approval_request(
        vault_path=vault_path,
        action_type=action_type,
        action_details=details,
        file_path=file_path
    )

    print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()
