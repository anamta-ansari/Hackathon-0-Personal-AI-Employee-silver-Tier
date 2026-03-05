"""
Process Email Skill

Specification: AGENT-SKILLS-001 (process_email)

Purpose: Process an email action file and create a plan

Input:
    - file_path: Path to email .md file in /Needs_Action

Output:
    - UPDATES the same file with plan section
    - MOVES file from Needs_Action/ to Plans/
    - If action requires approval, UPDATES file and MOVES to Pending_Approval/

SINGLE FILE LIFECYCLE:
    1. Email detected: Needs_Action/TASK_12345.md
    2. Plan created: Plans/TASK_12345.md (same file, moved + updated)
    3. Approval needed: Pending_Approval/TASK_12345.md (same file, moved + updated)
    4. Approved: Approved/TASK_12345.md (same file, moved)
    5. Executed: Done/TASK_12345.md (same file, moved + updated)
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import re
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def read_frontmatter(content: str) -> Dict[str, Any]:
    """
    Extract YAML frontmatter from Markdown content.

    Args:
        content: Full Markdown content with frontmatter

    Returns:
        Dict: Parsed frontmatter as dictionary
    """
    frontmatter = {}

    # Check for frontmatter delimiters
    if not content.startswith('---'):
        return frontmatter

    # Find end of frontmatter
    end_match = re.search(r'\n---\n', content[3:])
    if not end_match:
        return frontmatter

    frontmatter_text = content[3:end_match.start() + 3]

    # Parse simple YAML (key: value format)
    for line in frontmatter_text.strip().split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()

            # Handle basic types
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            elif value.isdigit():
                value = int(value)

            frontmatter[key] = value

    return frontmatter


def update_frontmatter(content: str, updates: Dict[str, Any]) -> str:
    """
    Update YAML frontmatter in Markdown content.

    Args:
        content: Full Markdown content with frontmatter
        updates: Dictionary of key-value pairs to update/add

    Returns:
        str: Updated content with new frontmatter
    """
    if not content.startswith('---'):
        # No frontmatter, add it
        frontmatter_str = "---\n"
        for key, value in updates.items():
            if isinstance(value, bool):
                frontmatter_str += f"{key}: {str(value).lower()}\n"
            else:
                frontmatter_str += f"{key}: {value}\n"
        frontmatter_str += "---\n\n"
        return frontmatter_str + content

    # Find end of frontmatter
    end_match = re.search(r'\n---\n', content[3:])
    if not end_match:
        return content  # Malformed, return as-is

    frontmatter_end = end_match.start() + 3
    frontmatter_text = content[3:frontmatter_end]
    rest = content[frontmatter_end:]

    # Parse existing frontmatter lines
    lines = frontmatter_text.strip().split('\n')
    updated_lines = []
    updated_keys = set()

    for line in lines:
        if ':' in line:
            key = line.split(':', 1)[0].strip()
            if key in updates:
                # Update existing key
                value = updates[key]
                if isinstance(value, bool):
                    updated_lines.append(f"{key}: {str(value).lower()}")
                else:
                    updated_lines.append(f"{key}: {value}")
                updated_keys.add(key)
                continue
        updated_lines.append(line)

    # Add new keys that weren't in original frontmatter
    for key, value in updates.items():
        if key not in updated_keys:
            if isinstance(value, bool):
                updated_lines.append(f"{key}: {str(value).lower()}")
            else:
                updated_lines.append(f"{key}: {value}")

    new_frontmatter = '\n'.join(updated_lines) + '\n'
    return f"---\n{new_frontmatter}---{rest}"


def analyze_email(frontmatter: Dict[str, Any], content: str) -> Dict[str, Any]:
    """
    Analyze email content to determine priority and required actions.

    Args:
        frontmatter: Email metadata
        content: Email body content

    Returns:
        Dict: Analysis results including priority, category, actions
    """
    analysis = {
        'priority': frontmatter.get('priority', 'medium'),
        'category': 'general',
        'requires_approval': False,
        'actions': [],
        'urgency_score': 0
    }

    # Get subject and sender
    subject = frontmatter.get('subject', '').lower()
    sender = frontmatter.get('from', '').lower()

    # Combine text for analysis
    text = f"{subject} {content}".lower()

    # Check for urgency keywords
    urgency_keywords = ['urgent', 'asap', 'emergency', 'immediate', 'deadline', 'today']
    for keyword in urgency_keywords:
        if keyword in text:
            analysis['urgency_score'] += 1
            analysis['priority'] = 'high'

    # Categorize email
    if any(word in text for word in ['invoice', 'payment', 'bill', 'receipt', 'price']):
        analysis['category'] = 'financial'
        analysis['actions'].append('Review financial details')
        analysis['actions'].append('Verify amount and vendor')

        # Check for large amounts
        amount_match = re.search(r'\$?(\d+(?:,\d{3})*(?:\.\d{2})?)', text)
        if amount_match:
            amount = float(amount_match.group(1).replace(',', ''))
            if amount > 500:
                analysis['requires_approval'] = True
                analysis['actions'].append('Requires human approval (amount > $500)')

    if any(word in text for word in ['meeting', 'schedule', 'calendar', 'appointment', 'zoom']):
        analysis['category'] = 'scheduling'
        analysis['actions'].append('Check calendar availability')
        analysis['actions'].append('Propose meeting times')

    if any(word in text for word in ['contract', 'agreement', 'legal', 'terms']):
        analysis['category'] = 'legal'
        analysis['requires_approval'] = True
        analysis['actions'].append('Requires human review (legal document)')

    if any(word in text for word in ['question', 'help', 'support', 'issue', 'problem']):
        analysis['category'] = 'support'
        analysis['actions'].append('Provide assistance')
        analysis['actions'].append('Escalate if needed')

    if any(word in text for word in ['unsubscribe', 'newsletter', 'promo', 'offer']):
        analysis['category'] = 'promotional'
        analysis['priority'] = 'low'
        analysis['actions'].append('Review - may be promotional')

    # Default actions if none identified
    if not analysis['actions']:
        analysis['actions'] = ['Read and respond as needed']

    # Always add these
    analysis['actions'].append('Draft response')
    analysis['actions'].append('Archive after processing')

    # Silver Tier: ALL email responses require human approval for safety
    analysis['requires_approval'] = True

    return analysis


def generate_draft_reply(
    frontmatter: Dict[str, Any],
    body: str,
    analysis: Dict[str, Any]
) -> str:
    """
    Generate a draft reply based on email content and analysis.

    This is a simple template-based reply generator.
    In production, Qwen Code would generate the actual reply content.

    Args:
        frontmatter: Email metadata
        body: Email body content
        analysis: Email analysis results

    Returns:
        str: Draft reply body
    """
    sender = frontmatter.get('from', 'there')
    subject = frontmatter.get('subject', 'your email')
    category = analysis.get('category', 'general')

    # Extract sender name (first part before email)
    sender_name = sender.split('<')[0].strip() if '<' in sender else sender.split('@')[0]

    # Category-specific templates
    templates = {
        'financial': f"""Dear {sender_name},

Thank you for your email regarding "{subject}".

I have received your message and will review the financial details shortly. I will get back to you with confirmation or any questions within 24 hours.

Best regards""",

        'scheduling': f"""Hi {sender_name},

Thanks for reaching out about "{subject}".

I'd be happy to schedule a meeting. Please let me know your availability for the coming week, and I'll find a time that works.

Looking forward to hearing from you.

Best regards""",

        'support': f"""Hello {sender_name},

Thank you for contacting us about "{subject}".

I understand you need assistance. I'm looking into this matter and will provide a solution or update as soon as possible.

Is there any additional information you can provide that might help?

Best regards""",

        'legal': f"""Dear {sender_name},

I have received your email regarding "{subject}".

This matter requires careful review. I will examine the documents and get back to you with a response within 48 hours.

Thank you for your patience.

Best regards""",

        'promotional': f"""Hi {sender_name},

Thank you for your message about "{subject}".

I've reviewed your information and will keep it on file for future reference.

Best regards""",

        'general': f"""Hi {sender_name},

Thank you for your email about "{subject}".

I've received your message and will respond with more details soon.

Best regards"""
    }

    return templates.get(category, templates['general'])


def add_action_plan(content: str, actions: List[str], plan_created: datetime) -> str:
    """
    Add an Action Plan section to the file content.

    Args:
        content: Current file content
        actions: List of action items
        plan_created: Timestamp when plan was created

    Returns:
        str: Updated content with action plan section
    """
    # Check if Action Plan section already exists
    if '## Action Plan' in content:
        return content  # Already has action plan

    # Find the end of the file or last section
    action_plan_section = f"""
## Action Plan
*Created: {plan_created.isoformat()}*

"""
    for action in actions:
        action_plan_section += f"- [ ] {action}\n"

    return content + action_plan_section


def add_approval_section(content: str, analysis: Dict[str, Any], 
                         frontmatter: Dict[str, Any], reply_body: str) -> str:
    """
    Add an Approval Required section to the file content.

    Args:
        content: Current file content
        analysis: Email analysis results
        frontmatter: Email metadata
        reply_body: Draft reply body

    Returns:
        str: Updated content with approval section
    """
    # Check if Approval section already exists
    if '## Approval Required' in content:
        return content  # Already has approval section

    # Extract reply-to email
    original_from = frontmatter.get('from', '')
    reply_to = original_from
    if '<' in original_from and '>' in original_from:
        match = re.search(r'<([^>]+)>', original_from)
        if match:
            reply_to = match.group(1)

    approval_section = f"""
## Approval Required
*Added: {datetime.now().isoformat()}*

**Risk Level:** {analysis.get('priority', 'medium').title()}
**Action Type:** Send email reply

**Reason for Approval:**
- {analysis['category'].capitalize()} matter requiring oversight

**Proposed Actions:**
"""
    for action in analysis.get('actions', []):
        approval_section += f"- {action}\n"

    approval_section += f"""
**Draft Reply:**

**To:** {reply_to}
**Subject:** Re: {frontmatter.get('subject', 'No Subject')}

```
{reply_body}
```

**Instructions:**
- Move this file to `/Approved/` to approve and send
- Move to `/Rejected/` to decline
- Edit the draft reply above before moving if modifications needed
"""

    return content + approval_section


def add_execution_result(content: str, execution_details: Dict[str, Any]) -> str:
    """
    Add an Execution Result section to the file content.

    Args:
        content: Current file content
        execution_details: Details about the execution result

    Returns:
        str: Updated content with execution result section
    """
    # Check if Execution Result section already exists
    if '## Execution Result' in content:
        return content  # Already has execution result

    execution_section = f"""
## Execution Result
*Added: {datetime.now().isoformat()}*

**Status:** {'✅ Success' if execution_details.get('success') else '❌ Failed'}
"""
    
    if execution_details.get('message_id'):
        execution_section += f"**Message ID:** {execution_details['message_id']}\n"
    
    if execution_details.get('sent_to'):
        execution_section += f"**Sent to:** {execution_details['sent_to']}\n"
    
    if execution_details.get('message'):
        execution_section += f"**Message:** {execution_details['message']}\n"

    return content + execution_section


def move_file(src_path: Path, dst_dir: Path, keep_filename: bool = True) -> Path:
    """
    Move a file from source to destination directory.

    Args:
        src_path: Source file path
        dst_dir: Destination directory
        keep_filename: Whether to keep the same filename (default: True)

    Returns:
        Path: New file path
    """
    dst_dir.mkdir(parents=True, exist_ok=True)
    
    if keep_filename:
        dst_path = dst_dir / src_path.name
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dst_path = dst_dir / f"{src_path.stem}_{timestamp}{src_path.suffix}"
    
    shutil.move(str(src_path), str(dst_path))
    return dst_path


def process_email(file_path: str, vault_path: str) -> Dict[str, Any]:
    """
    Main skill function to process an email action file.

    SINGLE FILE LIFECYCLE:
    1. Read email file from Needs_Action/
    2. Analyze email and generate action plan
    3. UPDATE the same file with plan section
    4. MOVE file from Needs_Action/ to Plans/
    5. If approval needed, UPDATE file and MOVE to Pending_Approval/

    Args:
        file_path: Path to email .md file in /Needs_Action
        vault_path: Path to Obsidian vault root

    Returns:
        Dict: Processing results with status and file paths
    """
    result = {
        'success': False,
        'email_file': file_path,
        'current_file': None,  # Current location of the single file
        'previous_location': None,
        'category': None,
        'priority': None,
        'requires_approval': False,
        'error': None
    }

    try:
        # Convert to Path objects
        email_path = Path(file_path)
        vault = Path(vault_path)

        # Validate file exists
        if not email_path.exists():
            result['error'] = f"Email file not found: {file_path}"
            return result

        # Read email content
        content = email_path.read_text(encoding='utf-8')

        # Parse frontmatter
        frontmatter = read_frontmatter(content)

        # Extract body (after frontmatter)
        body_match = re.search(r'---\n.*?\n---\n(.*)', content, re.DOTALL)
        body = body_match.group(1) if body_match else content

        # Analyze email
        analysis = analyze_email(frontmatter, body)

        result['category'] = analysis['category']
        result['priority'] = analysis['priority']
        result['requires_approval'] = analysis['requires_approval']

        # STEP 1: Update frontmatter with plan metadata
        plan_created = datetime.now()
        frontmatter_updates = {
            'status': 'planned',
            'plan_created': plan_created.isoformat(),
            'category': analysis['category'],
            'priority': analysis['priority'],
            'requires_approval': analysis['requires_approval']
        }
        content = update_frontmatter(content, frontmatter_updates)

        # STEP 2: Add Action Plan section
        content = add_action_plan(content, analysis['actions'], plan_created)

        # STEP 3: Write updated content
        email_path.write_text(content, encoding='utf-8')

        # STEP 4: Move file from Needs_Action/ to Plans/
        plans_dir = vault / 'Plans'
        new_path = move_file(email_path, plans_dir, keep_filename=True)
        
        result['current_file'] = str(new_path)
        result['previous_location'] = str(email_path)

        print(f"INFO: Moved file from Needs_Action/ to Plans/: {new_path.name}")

        # STEP 5: If approval needed, update and move to Pending_Approval/
        if analysis['requires_approval']:
            # Generate draft reply
            reply_body = generate_draft_reply(frontmatter, body, analysis)

            # Add approval section to content
            content = new_path.read_text(encoding='utf-8')
            content = add_approval_section(content, analysis, frontmatter, reply_body)

            # Update frontmatter for approval
            approval_updates = {
                'status': 'awaiting_approval',
                'approval_requested': datetime.now().isoformat()
            }
            content = update_frontmatter(content, approval_updates)

            # Write updated content
            new_path.write_text(content, encoding='utf-8')

            # Move to Pending_Approval/
            pending_dir = vault / 'Pending_Approval'
            approval_path = move_file(new_path, pending_dir, keep_filename=True)
            
            result['current_file'] = str(approval_path)
            result['previous_location'] = str(new_path)

            print(f"INFO: Moved file from Plans/ to Pending_Approval/: {approval_path.name}")

        # Update email file status
        result['success'] = True

    except Exception as e:
        result['error'] = str(e)
        import traceback
        result['traceback'] = traceback.format_exc()

    return result


def main():
    """
    Main entry point for testing the skill.

    Usage:
        python process_email.py <email_file_path> <vault_path>
    """
    import json
    import logging

    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

    if len(sys.argv) < 3:
        print("Usage: python process_email.py <email_file_path> <vault_path>")
        sys.exit(1)

    email_file = sys.argv[1]
    vault = sys.argv[2]

    result = process_email(email_file, vault)
    print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()
