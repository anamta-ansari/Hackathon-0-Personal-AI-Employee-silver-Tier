"""
LinkedIn Posting Skill for AI Employee - Silver Tier

This skill handles automated LinkedIn posting for business content generation.
It supports creating posts, scheduling, and tracking engagement.

Silver Tier Requirement: Automatically Post on LinkedIn about business to generate sales

Features:
- Create and publish LinkedIn posts
- Schedule posts for optimal times
- Generate business content from vault data
- Track post performance
- Human-in-the-loop approval for posts
"""

import os

# Environment variable for vault path (set in .env file)
# Default: D:/Hackathon-0/AI_Employee_Vault (root vault)
DEFAULT_VAULT_PATH = os.getenv('VAULT_PATH', 'D:/Hackathon-0/AI_Employee_Vault')

import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import re

# LinkedIn API dependencies
try:
    from linkedin_api import Linkedin
    LINKEDIN_API_AVAILABLE = True
except ImportError:
    LINKEDIN_API_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("linkedin-api not installed. Run: pip install linkedin-api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LinkedInPostSkill:
    """
    LinkedIn Posting Skill
    
    Handles automated LinkedIn posting for business content.
    Supports post creation, scheduling, and approval workflow.
    """
    
    # Post templates for different business scenarios
    POST_TEMPLATES = {
        'milestone': """
🎉 Business Update: {title}

{content}

Key Achievement: {achievement}

#BusinessGrowth #Milestone #Success

---
Posted by AI Employee Assistant
""",
        
        'product_launch': """
🚀 Exciting News: {title}

{content}

What this means for you: {benefit}

Learn more: {link}

#ProductLaunch #Innovation #Business

---
Posted by AI Employee Assistant
""",
        
        'thought_leadership': """
💡 Industry Insight: {title}

{content}

Key takeaway: {insight}

What's your perspective on this? Share in the comments!

#ThoughtLeadership #Industry #Insights

---
Posted by AI Employee Assistant
""",
        
        'client_success': """
⭐ Client Success Story: {title}

{content}

Results achieved: {results}

Ready to achieve similar results? Let's connect!

#ClientSuccess #CaseStudy #Results

---
Posted by AI Employee Assistant
""",
        
        'weekly_update': """
📊 Weekly Business Update

{content}

This week's highlights:
{highlights}

Looking ahead to next week: {outlook}

#WeeklyUpdate #Business #Progress

---
Posted by AI Employee Assistant
"""
    }
    
    def __init__(
        self,
        vault_path: Optional[str] = None,
        linkedin_email: Optional[str] = None,
        linkedin_password: Optional[str] = None,
        dry_run: bool = False
    ):
        """
        Initialize LinkedIn Posting Skill
        
        Args:
            vault_path: Path to Obsidian vault
            linkedin_email: LinkedIn account email
            linkedin_password: LinkedIn account password (use env var in production)
            dry_run: If True, log actions without posting
        """
        # Resolve paths
        self.project_root = Path(__file__).parent.parent.parent
        self.vault_path = Path(vault_path) if vault_path else Path(DEFAULT_VAULT_PATH)
        
        # Credentials (prefer environment variables)
        self.linkedin_email = linkedin_email or os.getenv('LINKEDIN_EMAIL')
        self.linkedin_password = linkedin_password or os.getenv('LINKEDIN_PASSWORD')
        
        # State
        self.api = None
        self.is_authenticated = False
        self.dry_run = dry_run
        self.profile_urn = None
        
        # Directories
        self.posts_dir = self.vault_path / 'Posts'
        self.approval_dir = self.vault_path / 'Pending_Approval'
        self.logs_dir = self.vault_path / 'Logs'
        self.done_dir = self.vault_path / 'Done'
        
        for directory in [self.posts_dir, self.approval_dir, self.logs_dir, self.done_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        logger.info("LinkedInPostSkill initialized")
        logger.info(f"Vault path: {self.vault_path}")
        logger.info(f"Dry run: {self.dry_run}")
    
    def authenticate(self) -> bool:
        """
        Authenticate with LinkedIn
        
        Returns:
            bool: True if authentication successful
        """
        if not LINKEDIN_API_AVAILABLE:
            logger.error("linkedin-api library not available")
            return False
        
        if not self.linkedin_email or not self.linkedin_password:
            logger.error("LinkedIn credentials not provided")
            return False
        
        try:
            self.api = Linkedin(self.linkedin_email, self.linkedin_password)
            self.is_authenticated = True
            
            # Get profile info
            profile = self.api.get_profile()
            self.profile_urn = profile.get('urn_id', '')
            
            logger.info(f"Authenticated as: {profile.get('firstName', 'User')}")
            
            self._log_auth_event('authenticate', {'success': True})
            return True
            
        except Exception as e:
            logger.error(f"LinkedIn authentication failed: {e}")
            self._log_auth_event('authenticate', {'success': False, 'error': str(e)})
            return False
    
    def create_post(
        self,
        content: str,
        title: Optional[str] = None,
        post_type: str = 'general',
        template_vars: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a LinkedIn post from content or template
        
        Args:
            content: Post content or template variables
            title: Post title
            post_type: Type of post (milestone, product_launch, etc.)
            template_vars: Variables for template
            
        Returns:
            str: Generated post content
        """
        # Use template if specified
        if post_type in self.POST_TEMPLATES and template_vars:
            template = self.POST_TEMPLATES[post_type]
            try:
                post_content = template.format(**template_vars)
            except KeyError as e:
                logger.warning(f"Missing template variable: {e}")
                post_content = content
        else:
            post_content = content
        
        # Validate post length (LinkedIn limit: 3000 characters)
        if len(post_content) > 3000:
            logger.warning(f"Post exceeds 3000 characters: {len(post_content)}")
            post_content = post_content[:2997] + "..."
        
        return post_content
    
    def publish_post(
        self,
        content: str,
        title: Optional[str] = None,
        requires_approval: bool = True
    ) -> Dict[str, Any]:
        """
        Publish a post to LinkedIn
        
        Args:
            content: Post content
            title: Post title for tracking
            requires_approval: If True, create approval request first
            
        Returns:
            Dict: Post result with status and ID
        """
        result = {
            'success': False,
            'post_id': None,
            'status': 'pending',
            'error': None,
            'requires_approval': requires_approval
        }
        
        # Ensure authentication
        if not self.is_authenticated:
            if not self.authenticate():
                result['error'] = 'Authentication failed'
                return result
        
        # Create approval request if required
        if requires_approval:
            approval_file = self._create_approval_request(content, title)
            result['status'] = 'pending_approval'
            result['approval_file'] = str(approval_file)
            result['message'] = f"Approval request created: {approval_file}"
            logger.info(f"Created approval request: {approval_file}")
            return result
        
        # Publish directly if no approval required
        if self.dry_run:
            logger.info(f"[DRY RUN] Would publish post: {content[:100]}...")
            result['status'] = 'dry_run'
            result['success'] = True
            result['message'] = 'Dry run - no post published'
            return result
        
        try:
            # Publish to LinkedIn
            response = self.api.create_post(content)
            
            result['success'] = True
            result['post_id'] = response.get('id', 'unknown')
            result['status'] = 'published'
            result['message'] = f"Post published successfully: {result['post_id']}"
            
            logger.info(f"Post published: {result['post_id']}")
            
            # Log action
            self._log_action('publish_post', {
                'post_id': result['post_id'],
                'title': title,
                'content_preview': content[:200]
            })
            
            # Save post record
            self._save_post_record(title or 'Untitled', content, result['post_id'])
            
        except Exception as e:
            result['error'] = str(e)
            result['status'] = 'failed'
            logger.error(f"Failed to publish post: {e}")
            
            self._log_action('publish_post', {
                'status': 'failed',
                'error': str(e),
                'title': title
            })
        
        return result
    
    def _create_approval_request(self, content: str, title: Optional[str]) -> Path:
        """
        Create approval request file for post
        
        Args:
            content: Post content
            title: Post title
            
        Returns:
            Path: Path to approval file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_title = re.sub(r'[^\w\s-]', '', title or 'LinkedIn_Post')[:30]
        
        filename = f"LINKEDIN_POST_{safe_title}_{timestamp}.md"
        filepath = self.approval_dir / filename
        
        content_md = f"""---
type: approval_request
action: linkedin_post
title: {title or 'LinkedIn Post'}
created: {datetime.now().isoformat()}
expires: {(datetime.now() + timedelta(days=1)).isoformat()}
status: pending
platform: LinkedIn
---

# LinkedIn Post Approval Request

## Post Content

{content}

---

## To Approve
Move this file to /Approved folder to publish.

## To Reject
Move this file to /Rejected folder.

## To Edit
Edit the content above and move to /Approved.

---
*Generated by AI Employee - LinkedIn Post Skill*
"""
        
        filepath.write_text(content_md, encoding='utf-8')
        return filepath
    
    def _save_post_record(self, title: str, content: str, post_id: str) -> Path:
        """
        Save post record to Posts directory
        
        Args:
            title: Post title
            content: Post content
            post_id: LinkedIn post ID
            
        Returns:
            Path: Path to saved post file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"POST_{timestamp}_{post_id[:8]}.md"
        filepath = self.posts_dir / filename
        
        content_md = f"""---
type: linkedin_post
title: {title}
post_id: {post_id}
published: {datetime.now().isoformat()}
platform: LinkedIn
status: published
---

# Published LinkedIn Post

## {title}

{content}

---
*Posted by AI Employee*
"""
        
        filepath.write_text(content_md, encoding='utf-8')
        return filepath
    
    def generate_business_post(
        self,
        business_goals_path: Optional[str] = None,
        dashboard_path: Optional[str] = None,
        post_type: str = 'weekly_update'
    ) -> str:
        """
        Generate a business post from vault data
        
        Args:
            business_goals_path: Path to Business_Goals.md
            dashboard_path: Path to Dashboard.md
            post_type: Type of post to generate
            
        Returns:
            str: Generated post content
        """
        business_goals_path = Path(business_goals_path) if business_goals_path else self.vault_path / 'Business_Goals.md'
        dashboard_path = Path(dashboard_path) if dashboard_path else self.vault_path / 'Dashboard.md'
        
        # Read business goals
        goals_content = ""
        if business_goals_path.exists():
            goals_content = business_goals_path.read_text(encoding='utf-8')
        
        # Read dashboard
        dashboard_content = ""
        if dashboard_path.exists():
            dashboard_content = dashboard_path.read_text(encoding='utf-8')
        
        # Extract key information
        highlights = self._extract_highlights(dashboard_content)
        goals = self._extract_goals(goals_content)
        
        # Generate post based on type
        if post_type == 'weekly_update':
            template_vars = {
                'title': 'Weekly Business Progress',
                'content': f"Here's what we've been working on this week.",
                'highlights': highlights,
                'outlook': 'Continuing progress on active projects'
            }
        elif post_type == 'milestone':
            template_vars = {
                'title': goals.get('current_goal', 'Business Milestone'),
                'content': 'We\'ve reached an important milestone in our business journey.',
                'achievement': goals.get('achievement', 'Continued growth and progress')
            }
        elif post_type == 'thought_leadership':
            template_vars = {
                'title': 'Industry Insights',
                'content': 'Sharing some thoughts on recent industry developments.',
                'insight': 'Adaptation and innovation are key to success'
            }
        else:
            template_vars = {
                'title': 'Business Update',
                'content': 'Sharing our latest progress and updates.'
            }
        
        return self.create_post(content="", post_type=post_type, template_vars=template_vars)
    
    def _extract_highlights(self, dashboard_content: str) -> str:
        """Extract highlights from dashboard"""
        highlights = []
        
        # Look for completed tasks
        completed_pattern = r'- \[x\] (.+)'
        completed = re.findall(completed_pattern, dashboard_content)
        for task in completed[:3]:  # Top 3 completed
            highlights.append(f"✓ {task}")
        
        if not highlights:
            highlights.append("✓ Ongoing project work")
        
        return "\n".join(highlights)
    
    def _extract_goals(self, goals_content: str) -> Dict[str, str]:
        """Extract goals from business goals file"""
        goals = {
            'current_goal': 'Business Growth',
            'achievement': 'Making steady progress'
        }
        
        # Extract revenue target if present
        revenue_match = re.search(r'Monthly goal:?\s*\$?([\d,]+)', goals_content)
        if revenue_match:
            goals['current_goal'] = f"Revenue Target: ${revenue_match.group(1)}"
        
        # Extract current MTD
        mtd_match = re.search(r'Current MTD:?\s*\$?([\d,]+)', goals_content)
        if mtd_match:
            goals['achievement'] = f"MTD: ${mtd_match.group(1)}"
        
        return goals
    
    def check_approval_files(self) -> List[Path]:
        """
        Check for approved post files in Pending_Approval directory
        
        Returns:
            List[Path]: List of approved post files
        """
        approved_dir = self.vault_path / 'Approved'
        approved_files = []
        
        if approved_dir.exists():
            for file in approved_dir.glob('LINKEDIN_POST_*.md'):
                approved_files.append(file)
        
        return approved_files
    
    def process_approved_posts(self) -> List[Dict[str, Any]]:
        """
        Process all approved post files
        
        Returns:
            List[Dict]: Results for each processed post
        """
        results = []
        approved_files = self.check_approval_files()
        
        for filepath in approved_files:
            result = self._process_single_approved_file(filepath)
            results.append(result)
        
        return results
    
    def _process_single_approved_file(self, filepath: Path) -> Dict[str, Any]:
        """
        Process a single approved post file
        
        Args:
            filepath: Path to approved file
            
        Returns:
            Dict: Processing result
        """
        result = {
            'file': str(filepath),
            'success': False,
            'post_id': None,
            'error': None
        }
        
        try:
            # Read file content
            content = filepath.read_text(encoding='utf-8')
            
            # Extract post content (between ## and ---)
            post_match = re.search(r'## LinkedIn Post Approval Request\s*\n\s*\n(.*?)\n\s*\n---', content, re.DOTALL)
            if not post_match:
                # Try alternative pattern
                post_match = re.search(r'## Post Content\s*\n\s*\n(.*?)\n\s*\n---', content, re.DOTALL)
            
            if post_match:
                post_content = post_match.group(1).strip()
            else:
                post_content = content  # Use full content as fallback
            
            # Publish post
            publish_result = self.publish_post(
                content=post_content,
                requires_approval=False  # Already approved
            )
            
            result['success'] = publish_result['success']
            result['post_id'] = publish_result.get('post_id')
            
            if publish_result['success']:
                # Move file to Done
                done_file = self.done_dir / filepath.name
                filepath.rename(done_file)
                logger.info(f"Moved {filepath.name} to Done")
            else:
                result['error'] = publish_result.get('error')
                
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error processing {filepath}: {e}")
        
        return result
    
    def schedule_post(
        self,
        content: str,
        scheduled_time: datetime,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Schedule a post for future publishing
        
        Args:
            content: Post content
            scheduled_time: When to publish
            title: Post title
            
        Returns:
            Dict: Schedule result
        """
        schedule_file = self._create_schedule_file(content, scheduled_time, title)
        
        return {
            'success': True,
            'scheduled_time': scheduled_time.isoformat(),
            'schedule_file': str(schedule_file),
            'message': f"Post scheduled for {scheduled_time}"
        }
    
    def _create_schedule_file(
        self,
        content: str,
        scheduled_time: datetime,
        title: Optional[str]
    ) -> Path:
        """Create schedule file for post"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"SCHEDULED_{timestamp}.md"
        filepath = self.posts_dir / 'Scheduled' / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        content_md = f"""---
type: scheduled_post
title: {title or 'Scheduled Post'}
scheduled_time: {scheduled_time.isoformat()}
created: {datetime.now().isoformat()}
status: scheduled
platform: LinkedIn
---

# Scheduled LinkedIn Post

{content}

---
*Will be published at {scheduled_time.strftime('%Y-%m-%d %H:%M')}*
"""
        
        filepath.write_text(content_md, encoding='utf-8')
        return filepath
    
    def _log_action(self, action_type: str, details: Dict[str, Any]) -> None:
        """Log action to vault logs"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'actor': 'linkedin_post_skill',
            'action_type': action_type,
            'details': details
        }
        
        log_file = self.logs_dir / f"linkedin_{datetime.now().strftime('%Y-%m-%d')}.json"
        
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
    
    def _log_auth_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log authentication event"""
        self._log_action(f'auth_{event_type}', details)
    
    def get_status(self) -> Dict[str, Any]:
        """Get skill status"""
        return {
            'authenticated': self.is_authenticated,
            'dry_run': self.dry_run,
            'vault_path': str(self.vault_path),
            'posts_dir': str(self.posts_dir),
            'approval_dir': str(self.approval_dir)
        }


# CLI interface
if __name__ == '__main__':
    import argparse
    
    # Handle Windows console encoding
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    
    parser = argparse.ArgumentParser(description='LinkedIn Post Skill')
    parser.add_argument('--vault', type=str, help='Path to Obsidian vault')
    parser.add_argument('--email', type=str, help='LinkedIn email')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--auth', action='store_true', help='Test authentication')
    parser.add_argument('--generate', type=str, help='Generate post type')
    parser.add_argument('--content', type=str, help='Direct post content')
    
    args = parser.parse_args()
    
    skill = LinkedInPostSkill(
        vault_path=args.vault,
        linkedin_email=args.email,
        dry_run=args.dry_run
    )
    
    if args.auth:
        print("Testing LinkedIn authentication...")
        success = skill.authenticate()
        if success:
            print("[OK] Authentication successful!")
            status = skill.get_status()
            print(f"Status: {status}")
        else:
            print("[FAIL] Authentication failed")
        sys.exit(0 if success else 1)
    
    if args.generate:
        print(f"Generating {args.generate} post...")
        content = skill.generate_business_post(post_type=args.generate)
        print("\nGenerated Post:")
        print("=" * 60)
        # Remove emojis for Windows console compatibility
        content_ascii = content.encode('ascii', 'ignore').decode('ascii')
        print(content_ascii)
        print("=" * 60)
        print("[OK] Post generated (save to Pending_Approval for review)")
        sys.exit(0)
    
    if args.content:
        print("Publishing post...")
        skill.authenticate()
        result = skill.publish_post(args.content, requires_approval=True)
        print(f"Result: {result}")
        sys.exit(0)
    
    # Default: show help
    parser.print_help()
