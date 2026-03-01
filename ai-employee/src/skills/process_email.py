"""
Process Email Skill

Specification: AGENT-SKILLS-001 (process_email)

Purpose: Process an email action file and create a plan

Input: 
    - file_path: Path to email .md file in /Needs_Action
    
Output:
    - Creates Plan.md in /Plans/
    - Updates original file status
    - If action requires approval, creates file in /Pending_Approval/

Behavior:
    1. Read email content
    2. Analyze sender, subject, urgency
    3. Generate suggested actions
    4. Create Plan.md with checkboxes
    5. If action requires approval, create file in /Pending_Approval/
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import re

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
    
    # Check if new sender
    if 'new_sender' not in frontmatter:
        # Simple heuristic: if no previous interaction recorded
        analysis['requires_approval'] = analysis['requires_approval'] or '@new' in sender
    
    return analysis


def create_plan(
    email_path: Path,
    frontmatter: Dict[str, Any],
    analysis: Dict[str, Any],
    vault_path: Path
) -> Path:
    """
    Create a Plan.md file for processing the email.
    
    Args:
        email_path: Path to original email file
        frontmatter: Email metadata
        analysis: Email analysis results
        vault_path: Path to vault root
        
    Returns:
        Path: Path to created plan file
    """
    # Generate plan filename
    email_id = frontmatter.get('gmail_id', email_path.stem)
    plan_filename = f"PLAN_{email_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    plan_path = vault_path / 'Plans' / plan_filename
    
    # Build plan content
    actions_list = '\n'.join([f"- [ ] {action}" for action in analysis['actions']])
    
    approval_note = ""
    if analysis['requires_approval']:
        approval_note = """
> ⚠️ **This email requires human approval before proceeding.**
> Review the details below and move to /Approved/ when ready.
"""
    
    plan_content = f"""---
type: plan
created: {datetime.now().isoformat()}
status: pending
email_file: {email_path.name}
category: {analysis['category']}
priority: {analysis['priority']}
requires_approval: {str(analysis['requires_approval']).lower()}
---

# Email Processing Plan

## Email Details
- **From:** {frontmatter.get('from', 'Unknown')}
- **Subject:** {frontmatter.get('subject', 'No Subject')}
- **Received:** {frontmatter.get('received', 'Unknown')}
- **Category:** {analysis['category']}
- **Priority:** {analysis['priority']}
{approval_note}
## Action Items

{actions_list}

## Notes

Add any additional context or instructions here.

---
*Generated by AI Employee v1.0.0*
"""
    
    # Write plan file
    plan_path.write_text(plan_content, encoding='utf-8')
    
    return plan_path


def create_approval_request(
    email_path: Path,
    frontmatter: Dict[str, Any],
    analysis: Dict[str, Any],
    plan_path: Path,
    vault_path: Path
) -> Optional[Path]:
    """
    Create an approval request file if needed.
    
    Args:
        email_path: Path to original email file
        frontmatter: Email metadata
        analysis: Email analysis results
        plan_path: Path to plan file
        vault_path: Path to vault root
        
    Returns:
        Path: Path to approval request file, or None if not required
    """
    if not analysis['requires_approval']:
        return None
    
    # Generate approval request filename
    approval_filename = f"APPROVAL_{frontmatter.get('gmail_id', email_path.stem)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    approval_path = vault_path / 'Pending_Approval' / approval_filename
    
    # Build approval request content
    approval_content = f"""---
type: approval_request
action: email_response
created: {datetime.now().isoformat()}
email_from: {frontmatter.get('from', 'Unknown')}
email_subject: {frontmatter.get('subject', 'No Subject')}
category: {analysis['category']}
priority: {analysis['priority']}
plan_file: {plan_path.name}
status: pending
expires: {(datetime.now().replace(hour=23, minute=59, second=59)).isoformat()}
---

# Approval Required: Email Response

## Email Summary
- **From:** {frontmatter.get('from', 'Unknown')}
- **Subject:** {frontmatter.get('subject', 'No Subject')}
- **Category:** {analysis['category']}
- **Priority:** {analysis['priority']}

## Reason for Approval
This email requires human review before proceeding because:
- {analysis['category'].capitalize()} matter requiring oversight
{f"- Amount exceeds $500 threshold" if analysis['category'] == 'financial' else ""}
{f"- New sender - first time contact" if '@new' in str(frontmatter.get('from', '')).lower() else ""}

## Proposed Actions
{chr(10).join(['- ' + action for action in analysis['actions']])}

## Instructions

**To Approve:**
1. Review the email and proposed actions
2. Move this file to `/Approved/` folder
3. AI Employee will proceed with the plan

**To Reject:**
1. Move this file to `/Rejected/` folder
2. Add a note explaining the rejection

**To Modify:**
1. Edit this file with your changes
2. Move to `/Approved/` when ready

---
*Generated by AI Employee v1.0.0*
"""
    
    # Write approval request file
    approval_path.write_text(approval_content, encoding='utf-8')
    
    return approval_path


def process_email(file_path: str, vault_path: str) -> Dict[str, Any]:
    """
    Main skill function to process an email action file.
    
    Args:
        file_path: Path to email .md file in /Needs_Action
        vault_path: Path to Obsidian vault root
        
    Returns:
        Dict: Processing results with status and created files
    """
    result = {
        'success': False,
        'email_file': file_path,
        'plan_file': None,
        'approval_file': None,
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
        
        # Create plan
        plan_path = create_plan(email_path, frontmatter, analysis, vault)
        result['plan_file'] = str(plan_path)
        
        # Create approval request if needed
        if analysis['requires_approval']:
            approval_path = create_approval_request(
                email_path, frontmatter, analysis, plan_path, vault
            )
            if approval_path:
                result['approval_file'] = str(approval_path)
        
        # Update email file status
        result['success'] = True
        
    except Exception as e:
        result['error'] = str(e)
    
    return result


def main():
    """
    Main entry point for testing the skill.
    
    Usage:
        python process_email.py <email_file_path> <vault_path>
    """
    import json
    
    if len(sys.argv) < 3:
        print("Usage: python process_email.py <email_file_path> <vault_path>")
        sys.exit(1)
    
    email_file = sys.argv[1]
    vault = sys.argv[2]
    
    result = process_email(email_file, vault)
    print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()
