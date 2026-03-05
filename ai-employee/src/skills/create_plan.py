"""
Plan Generation Skill for AI Employee - Silver Tier

This skill creates Plan.md files with structured action plans based on
tasks, emails, or other items in the Needs_Action folder.

Silver Tier Requirement: Claude reasoning loop that creates Plan.md files

Features:
- Analyzes action files in Needs_Action folder
- Generates structured plans with objectives, steps, and timelines
- Creates approval requests for sensitive actions
- Integrates with approval workflow
- Comprehensive logging and tracking
"""

import os

# Environment variable for vault path (set in .env file)
# Default: D:/Hackathon-0/AI_Employee_Vault (root vault)
DEFAULT_VAULT_PATH = os.getenv('VAULT_PATH', 'D:/Hackathon-0/AI_Employee_Vault')

import sys
import json
import logging
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PlanGenerationSkill:
    """
    Plan Generation Skill
    
    Creates structured Plan.md files for tasks and action items.
    Analyzes content and generates step-by-step action plans.
    """
    
    # Plan templates for different action types
    PLAN_TEMPLATES = {
        'email': {
            'objective': 'Process and respond to email from {from_email}',
            'default_steps': [
                'Read and understand email content',
                'Determine required response or action',
                'Draft response or take action',
                'Review and send (if approval obtained)',
                'Archive email after completion'
            ]
        },
        'whatsapp_message': {
            'objective': 'Respond to WhatsApp message from {from_name}',
            'default_steps': [
                'Read message and understand context',
                'Determine urgency and priority',
                'Draft appropriate response',
                'Send response via WhatsApp',
                'Follow up if needed'
            ]
        },
        'payment': {
            'objective': 'Process payment: {payment_details}',
            'default_steps': [
                'Verify payment details and amount',
                'Check available funds',
                'Create payment approval request',
                'Wait for human approval',
                'Execute payment via MCP',
                'Log transaction and update records'
            ]
        },
        'invoice': {
            'objective': 'Generate and send invoice: {invoice_details}',
            'default_steps': [
                'Gather invoice details (amount, recipient, items)',
                'Generate invoice document',
                'Create email approval request',
                'Wait for human approval',
                'Send invoice via email',
                'Log transaction'
            ]
        },
        'general': {
            'objective': 'Complete task: {task_name}',
            'default_steps': [
                'Understand task requirements',
                'Gather necessary resources',
                'Execute task steps',
                'Review completion',
                'Document outcomes'
            ]
        }
    }
    
    # Approval thresholds
    PAYMENT_APPROVAL_THRESHOLD = 100.0  # Require approval for payments >= $100
    EMAIL_BULK_THRESHOLD = 5  # Require approval for bulk emails >= 5
    
    def __init__(
        self,
        vault_path: Optional[str] = None,
        auto_approve_threshold: float = 50.0
    ):
        """
        Initialize Plan Generation Skill
        
        Args:
            vault_path: Path to Obsidian vault
            auto_approve_threshold: Auto-approve payments below this amount
        """
        # Resolve paths
        self.project_root = Path(__file__).parent.parent.parent
        self.vault_path = Path(vault_path) if vault_path else Path(DEFAULT_VAULT_PATH)
        
        # Directories
        self.needs_action_dir = self.vault_path / 'Needs_Action'
        self.plans_dir = self.vault_path / 'Plans'
        self.approval_dir = self.vault_path / 'Pending_Approval'
        self.logs_dir = self.vault_path / 'Logs'
        self.done_dir = self.vault_path / 'Done'
        
        for directory in [self.plans_dir, self.approval_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Configuration
        self.auto_approve_threshold = auto_approve_threshold
        
        logger.info("PlanGenerationSkill initialized")
        logger.info(f"Vault path: {self.vault_path}")
        logger.info(f"Auto-approve threshold: ${self.auto_approve_threshold}")
    
    def analyze_action_file(self, filepath: Path) -> Dict[str, Any]:
        """
        Analyze an action file to determine type and requirements
        
        Args:
            filepath: Path to action file
            
        Returns:
            Dict: Analysis results
        """
        if not filepath.exists():
            return {'error': 'File not found'}
        
        content = filepath.read_text(encoding='utf-8')
        
        # Extract frontmatter
        frontmatter = self._extract_frontmatter(content)
        
        # Determine action type
        action_type = frontmatter.get('type', 'general')
        
        # Map types to plan templates
        type_mapping = {
            'email': 'email',
            'whatsapp_message': 'whatsapp_message',
            'payment': 'payment',
            'invoice': 'invoice',
            'file_drop': 'general'
        }
        
        plan_type = type_mapping.get(action_type, 'general')
        
        # Extract key information
        analysis = {
            'filepath': str(filepath),
            'filename': filepath.name,
            'action_type': action_type,
            'plan_type': plan_type,
            'priority': frontmatter.get('priority', 'medium'),
            'status': frontmatter.get('status', 'pending'),
            'metadata': frontmatter,
            'requires_approval': self._check_requires_approval(frontmatter, content),
            'estimated_steps': len(self.PLAN_TEMPLATES[plan_type]['default_steps'])
        }
        
        # Extract specific details based on type
        if action_type == 'email':
            analysis['from_email'] = frontmatter.get('from', 'Unknown')
            analysis['subject'] = frontmatter.get('subject', 'No Subject')
        
        elif action_type == 'whatsapp_message':
            analysis['from_name'] = frontmatter.get('from', 'Unknown')
        
        elif action_type == 'payment':
            amount = self._extract_amount(frontmatter, content)
            analysis['amount'] = amount
            analysis['requires_approval'] = analysis['requires_approval'] or (amount >= self.PAYMENT_APPROVAL_THRESHOLD)
        
        return analysis
    
    def create_plan(self, analysis: Dict[str, Any]) -> Path:
        """
        Create a Plan.md file based on analysis
        
        Args:
            analysis: Analysis results from analyze_action_file
            
        Returns:
            Path: Path to created plan file
        """
        # Get template
        plan_type = analysis.get('plan_type', 'general')
        template = self.PLAN_TEMPLATES.get(plan_type, self.PLAN_TEMPLATES['general'])
        
        # Generate objective
        objective = template['objective']
        try:
            # Try to format with available metadata
            format_vars = {}
            if 'from_email' in analysis:
                format_vars['from_email'] = analysis['from_email']
            if 'from_name' in analysis:
                format_vars['from_name'] = analysis['from_name']
            if 'payment_details' in analysis:
                format_vars['payment_details'] = analysis.get('payment_details', 'pending')
            if 'invoice_details' in analysis:
                format_vars['invoice_details'] = analysis.get('invoice_details', 'pending')
            
            if format_vars:
                objective = objective.format(**format_vars)
        except KeyError:
            pass  # Use default objective
        
        # Generate steps
        steps = self._generate_steps(analysis, template['default_steps'])
        
        # Determine if approval is required
        requires_approval = analysis.get('requires_approval', False)
        
        # Create plan metadata
        plan_metadata = {
            'created': datetime.now().isoformat(),
            'status': 'pending_approval' if requires_approval else 'in_progress',
            'action_type': analysis.get('action_type', 'unknown'),
            'source_file': analysis.get('filename', 'unknown'),
            'priority': analysis.get('priority', 'medium'),
            'requires_approval': requires_approval
        }
        
        # Build markdown content
        markdown_content = self._build_plan_markdown(
            objective=objective,
            steps=steps,
            metadata=plan_metadata,
            analysis=analysis
        )
        
        # Generate filename
        filename = self._generate_plan_filename(analysis)
        filepath = self.plans_dir / filename
        
        # Write file
        filepath.write_text(markdown_content, encoding='utf-8')
        logger.info(f"Created plan: {filepath}")
        
        # Log action
        self._log_action('create_plan', {
            'filepath': str(filepath),
            'action_type': analysis.get('action_type'),
            'requires_approval': requires_approval
        })
        
        # Create approval request if needed
        if requires_approval:
            self._create_approval_request(filepath, analysis)
        
        return filepath
    
    def _generate_steps(
        self,
        analysis: Dict[str, Any],
        default_steps: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Generate customized steps based on analysis
        
        Args:
            analysis: Analysis results
            default_steps: Default steps from template
            
        Returns:
            List[Dict]: Steps with status and details
        """
        steps = []
        
        for i, step in enumerate(default_steps, 1):
            step_data = {
                'order': i,
                'description': step,
                'status': 'pending',
                'completed': False,
                'requires_approval': self._step_requires_approval(step, analysis)
            }
            steps.append(step_data)
        
        # Add approval step if required
        if analysis.get('requires_approval'):
            # Insert approval step at appropriate position
            approval_step = {
                'order': len(steps) + 1,
                'description': 'Obtain human approval',
                'status': 'pending',
                'completed': False,
                'requires_approval': False,
                'approval_type': 'human_in_loop'
            }
            # Insert before final steps
            insert_pos = max(0, len(steps) - 2)
            steps.insert(insert_pos, approval_step)
        
        return steps
    
    def _step_requires_approval(
        self,
        step: str,
        analysis: Dict[str, Any]
    ) -> bool:
        """
        Check if a step requires approval
        
        Args:
            step: Step description
            analysis: Analysis results
            
        Returns:
            bool: True if approval required
        """
        approval_keywords = ['send', 'pay', 'approve', 'authorize', 'publish']
        
        step_lower = step.lower()
        return any(kw in step_lower for kw in approval_keywords)
    
    def _build_plan_markdown(
        self,
        objective: str,
        steps: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> str:
        """
        Build markdown content for plan file
        
        Args:
            objective: Plan objective
            steps: List of steps
            metadata: Plan metadata
            analysis: Analysis results
            
        Returns:
            str: Markdown content
        """
        # Build frontmatter
        frontmatter = "---\n"
        for key, value in metadata.items():
            frontmatter += f"{key}: {value}\n"
        frontmatter += "---\n\n"
        
        # Build steps markdown
        steps_md = ""
        for step in steps:
            checkbox = "[ ]" if not step['completed'] else "[x]"
            approval_tag = " ⚠️ REQUIRES APPROVAL" if step.get('requires_approval') else ""
            steps_md += f"- {checkbox} {step['description']}{approval_tag}\n"
        
        # Build full content
        content = f"""{frontmatter}
# Action Plan: {analysis.get('filename', 'Unknown')}

## Objective

{objective}

---

## Steps

{steps_md}

---

## Context

**Source File:** {analysis.get('filename', 'Unknown')}
**Action Type:** {analysis.get('action_type', 'Unknown')}
**Priority:** {analysis.get('priority', 'medium')}

---

## Notes

_Add additional notes and observations here_

---

## Completion Status

- [ ] All steps completed
- [ ] Approval obtained (if required)
- [ ] Action file moved to /Done

---
*Generated by AI Employee - Plan Generation Skill*
"""
        return content
    
    def _generate_plan_filename(self, analysis: Dict[str, Any]) -> str:
        """
        Generate safe filename for plan file
        
        Args:
            analysis: Analysis results
            
        Returns:
            str: Safe filename
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        action_type = analysis.get('action_type', 'task')
        source_file = analysis.get('filename', 'unknown')
        
        # Clean source filename
        safe_name = re.sub(r'[^\w\s-]', '', source_file)[:30]
        safe_name = safe_name.strip().replace(' ', '_')
        
        return f"PLAN_{timestamp}_{action_type}_{safe_name}.md"
    
    def _extract_frontmatter(self, content: str) -> Dict[str, Any]:
        """
        Extract YAML frontmatter from markdown
        
        Args:
            content: Markdown content
            
        Returns:
            Dict: Frontmatter dictionary
        """
        frontmatter = {}
        
        # Match frontmatter block
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if match:
            fm_text = match.group(1)
            
            # Parse key-value pairs
            for line in fm_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Convert types
                    if value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                    elif value.isdigit():
                        value = int(value)
                    
                    frontmatter[key] = value
        
        return frontmatter
    
    def _extract_amount(self, frontmatter: Dict[str, Any], content: str) -> float:
        """
        Extract payment amount from content
        
        Args:
            frontmatter: Frontmatter dict
            content: Full content
            
        Returns:
            float: Payment amount
        """
        # Check frontmatter first
        amount = frontmatter.get('amount', 0)
        if isinstance(amount, (int, float)):
            return float(amount)
        
        # Search content for amount patterns
        patterns = [
            r'\$([\d,]+\.?\d*)',  # $100.00
            r'amount[:\s]+\$?([\d,]+\.?\d*)',  # amount: $100
            r'([\d,]+\.?\d*)\s*USD'  # 100 USD
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    return float(amount_str)
                except ValueError:
                    pass
        
        return 0.0
    
    def _check_requires_approval(
        self,
        frontmatter: Dict[str, Any],
        content: str
    ) -> bool:
        """
        Check if action requires human approval
        
        Args:
            frontmatter: Frontmatter dict
            content: Full content
            
        Returns:
            bool: True if approval required
        """
        action_type = frontmatter.get('type', '')
        
        # Payment actions always require approval check
        if action_type == 'payment':
            amount = self._extract_amount(frontmatter, content)
            return amount >= self.auto_approve_threshold
        
        # Email to new contacts
        if action_type == 'email':
            # Check if sender is known (simplified check)
            return True  # Default to requiring approval
        
        # WhatsApp messages
        if action_type == 'whatsapp_message':
            priority = frontmatter.get('priority', 'medium')
            return priority == 'high'
        
        # Default: require approval for sensitive actions
        return True
    
    def _create_approval_request(self, plan_path: Path, analysis: Dict[str, Any]) -> Path:
        """
        Create approval request file for plan
        
        Args:
            plan_path: Path to plan file
            analysis: Analysis results
            
        Returns:
            Path: Path to approval file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        action_type = analysis.get('action_type', 'task')
        
        filename = f"APPROVAL_PLAN_{timestamp}_{action_type}.md"
        filepath = self.approval_dir / filename
        
        content = f"""---
type: approval_request
action: plan_execution
plan_file: {plan_path.name}
created: {datetime.now().isoformat()}
expires: {(datetime.now() + timedelta(days=1)).isoformat()}
status: pending
priority: {analysis.get('priority', 'medium')}
---

# Plan Approval Request

## Summary

**Plan:** {plan_path.name}
**Action Type:** {analysis.get('action_type', 'Unknown')}
**Priority:** {analysis.get('priority', 'medium')}

## Objective

{analysis.get('objective', 'Execute action plan')}

---

## To Approve

Move this file to /Approved folder to execute the plan.

## To Reject

Move this file to /Rejected folder.

## To Modify

Edit the plan file directly and then approve.

---
*Generated by AI Employee - Plan Generation Skill*
"""
        
        filepath.write_text(content, encoding='utf-8')
        logger.info(f"Created approval request: {filepath}")
        
        return filepath
    
    def process_needs_action_folder(self) -> List[Path]:
        """
        Process all action files in Needs_Action folder
        
        Returns:
            List[Path]: List of created plan files
        """
        plans_created = []
        
        if not self.needs_action_dir.exists():
            logger.warning(f"Needs_Action folder not found: {self.needs_action_dir}")
            return plans_created
        
        # Find all markdown files
        action_files = list(self.needs_action_dir.glob('*.md'))
        logger.info(f"Found {len(action_files)} action file(s)")
        
        for filepath in action_files:
            try:
                # Analyze action file
                analysis = self.analyze_action_file(filepath)
                
                if 'error' in analysis:
                    logger.warning(f"Skipping {filepath}: {analysis['error']}")
                    continue
                
                # Create plan
                plan_path = self.create_plan(analysis)
                plans_created.append(plan_path)
                
            except Exception as e:
                logger.error(f"Error processing {filepath}: {e}")
        
        logger.info(f"Created {len(plans_created)} plan(s)")
        return plans_created
    
    def _log_action(self, action_type: str, details: Dict[str, Any]) -> None:
        """Log action to vault logs"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'actor': 'plan_generation_skill',
            'action_type': action_type,
            'details': details
        }
        
        log_file = self.logs_dir / f"plan_generation_{datetime.now().strftime('%Y-%m-%d')}.json"
        
        logs = []
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except:
                logs = []
        
        logs.append(log_entry)
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2)
    
    def get_status(self) -> Dict[str, Any]:
        """Get skill status"""
        return {
            'vault_path': str(self.vault_path),
            'needs_action_count': len(list(self.needs_action_dir.glob('*.md'))) if self.needs_action_dir.exists() else 0,
            'plans_dir': str(self.plans_dir),
            'approval_dir': str(self.approval_dir),
            'auto_approve_threshold': self.auto_approve_threshold
        }


# CLI interface
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Plan Generation Skill')
    parser.add_argument('--vault', type=str, help='Path to Obsidian vault')
    parser.add_argument('--threshold', type=float, default=50.0, help='Auto-approve threshold')
    parser.add_argument('--process', action='store_true', help='Process Needs_Action folder')
    parser.add_argument('--file', type=str, help='Process single action file')
    
    args = parser.parse_args()
    
    skill = PlanGenerationSkill(
        vault_path=args.vault,
        auto_approve_threshold=args.threshold
    )
    
    if args.process:
        print("Processing Needs_Action folder...")
        plans = skill.process_needs_action_folder()
        print(f"Created {len(plans)} plan(s):")
        for plan in plans:
            print(f"  - {plan.name}")
        sys.exit(0)
    
    if args.file:
        filepath = Path(args.file)
        print(f"Analyzing: {filepath}")
        analysis = skill.analyze_action_file(filepath)
        print(f"\nAnalysis:")
        for key, value in analysis.items():
            print(f"  {key}: {value}")
        
        print("\nCreating plan...")
        plan_path = skill.create_plan(analysis)
        print(f"Plan created: {plan_path}")
        sys.exit(0)
    
    # Default: show status
    status = skill.get_status()
    print("Plan Generation Skill Status:")
    for key, value in status.items():
        print(f"  {key}: {value}")
