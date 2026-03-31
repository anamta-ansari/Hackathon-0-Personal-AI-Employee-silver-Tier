#!/usr/bin/env python3
"""
LinkedIn Content Generator - AI-Powered Post Creation

Interactive tool for generating LinkedIn posts with multiple options.

Usage:
    python src/skills/linkedin_content_generator.py
    
Interactive mode:
    - Shows post type options (1-8)
    - Generates content based on selection
    - Shows preview
    - Saves to Pending_Approval/
    - Ready for approval
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json
import re

# Handle Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')


class LinkedInContentGenerator:
    """
    AI-Powered LinkedIn Content Generator
    
    Generates professional LinkedIn posts based on business data and user selection.
    """
    
    def __init__(self):
        """Initialize content generator with vault paths"""
        # Resolve paths
        self.project_root = Path(__file__).parent.parent.parent
        self.vault_path = self.project_root.parent / 'AI_Employee_Vault'
        self.pending_approval = self.vault_path / 'Pending_Approval'
        self.business_goals = self.vault_path / 'Business_Goals.md'
        self.company_handbook = self.vault_path / 'Company_Handbook.md'
        self.done_folder = self.vault_path / 'Done'
        self.logs_folder = self.vault_path / 'Logs'
        
        # Ensure pending approval folder exists
        self.pending_approval.mkdir(parents=True, exist_ok=True)
        
        # Post type definitions
        self.post_types = {
            '1': {
                'name': '🏆 Milestone/Achievement',
                'desc': 'Celebrate wins, goals reached, company milestones',
                'generator': self.generate_milestone_post
            },
            '2': {
                'name': '💡 Thought Leadership',
                'desc': 'Share tips, insights, advice on AI/automation',
                'generator': self.generate_thought_leadership_post
            },
            '3': {
                'name': '📢 Product Update',
                'desc': 'Announce new features, releases, improvements',
                'generator': self.generate_product_update_post
            },
            '4': {
                'name': '👥 Team Highlight',
                'desc': 'Behind the scenes, culture, team stories',
                'generator': self.generate_team_highlight_post
            },
            '5': {
                'name': '📊 Weekly Summary',
                'desc': 'Stats, progress, tasks completed this week',
                'generator': self.generate_weekly_summary_post
            },
            '6': {
                'name': '🎉 Celebration',
                'desc': 'Anniversaries, user milestones, achievements',
                'generator': self.generate_celebration_post
            },
            '7': {
                'name': '📚 Industry Insight',
                'desc': 'AI trends, automation tips, predictions',
                'generator': self.generate_industry_insight_post
            },
            '8': {
                'name': '🔥 Custom',
                'desc': 'Describe what you want to post about',
                'generator': self.generate_custom_post
            },
        }

    def show_post_options(self):
        """Display post type options to user"""
        print("\n" + "=" * 60)
        print("LinkedIn Post Generator")
        print("=" * 60)
        print("\nWhat type of LinkedIn post would you like to create?\n")
        
        for key, value in self.post_types.items():
            print(f"{key}. {value['name']}")
            print(f"   {value['desc']}\n")
        
        return self.post_types

    def get_user_selection(self):
        """Get user's post type selection"""
        while True:
            choice = input("Enter your choice (1-8): ").strip()
            if choice in self.post_types:
                return choice
            print("Invalid choice. Please enter 1-8.")

    def generate_milestone_post(self):
        """Generate milestone/achievement post"""
        achievements = self._read_business_goals()
        
        content = f"""🎉 Exciting milestone achieved!

I'm thrilled to share that our AI Employee automation system has reached a major breakthrough.

Recent accomplishments:
✅ {achievements[0] if achievements else 'Automated email processing'}
✅ {achievements[1] if len(achievements) > 1 else 'LinkedIn integration complete'}
✅ {achievements[2] if len(achievements) > 2 else 'Dashboard monitoring live'}

This wouldn't be possible without continuous innovation and testing.

What automation milestones are you celebrating this week?

#AI #Automation #Milestone #Innovation #Productivity"""
        
        return content

    def generate_thought_leadership_post(self):
        """Generate thought leadership post"""
        content = """💡 3 Lessons from Building an AI Employee

After implementing autonomous AI systems, here's what I've learned:

1️⃣ Human-in-the-loop is essential
   Automation works best with human oversight, not replacement.

2️⃣ Start small, scale gradually
   Begin with one workflow, perfect it, then expand.

3️⃣ Monitor everything
   Dashboards and audit logs are non-negotiable for trust.

The future isn't about AI replacing humans—it's about AI amplifying human potential.

What's your experience with AI automation?

#AI #Leadership #Automation #FutureOfWork #Productivity"""
        
        return content

    def generate_product_update_post(self):
        """Generate product update post"""
        recent_tasks = self._get_recent_tasks()
        task_count = len(recent_tasks)
        
        content = f"""🚀 Product Update: New Features Live!

Excited to announce the latest improvements to our AI Employee system:

✨ What's New:
- LinkedIn browser automation with session persistence
- Real-time dashboard monitoring
- Advanced approval workflows
- Automated content generation

📊 Impact:
- {task_count} tasks automated recently
- 80% reduction in manual posting time
- Seamless email + social media integration

The future of productivity is here. What features would you like to see next?

#ProductUpdate #AI #Innovation #Automation #TechNews"""
        
        return content

    def generate_team_highlight_post(self):
        """Generate team highlight post"""
        content = """👥 Behind the Scenes: Building AI Employee

Ever wonder what goes into building an autonomous AI system?

Our team's approach:
🔹 Daily standups to sync on automation workflows
🔹 Continuous testing of new integration points
🔹 Human-in-the-loop reviews for quality assurance
🔹 Dashboard monitoring for real-time visibility

The secret? Collaboration between human creativity and AI efficiency.

What's your team's secret to productivity?

#TeamWork #AI #Culture #Innovation #BehindTheScenes"""
        
        return content

    def generate_weekly_summary_post(self):
        """Generate weekly summary post"""
        stats = self._get_weekly_stats()
        
        content = f"""📊 Weekly Automation Update

This week's AI Employee achievements:

🎯 Productivity Stats:
- Tasks Processed: {stats.get('tasks', 0)}
- Emails Handled: {stats.get('emails', 0)}
- LinkedIn Posts: {stats.get('linkedin', 0)}
- Time Saved: ~{int(stats.get('time_saved', 0))} hours

🚀 Key Wins:
- All approvals reviewed within 24h
- Zero missed notifications
- 100% audit trail maintained

Automation is transforming how we work. What's your biggest productivity win this week?

#WeeklyUpdate #Productivity #AI #Automation #Results"""
        
        return content

    def generate_celebration_post(self):
        """Generate celebration post"""
        content = """🎉 Celebrating a Special Milestone!

Today marks an important achievement in our AI automation journey!

What we're celebrating:
✨ Another year of continuous innovation
✨ Thousands of tasks automated
✨ Countless hours of human potential unlocked
✨ A community of forward-thinking professionals

Grateful for everyone who's been part of this journey. Here's to amplifying human potential through AI!

What milestones are you celebrating today?

#Celebration #Milestone #AI #Gratitude #Innovation"""
        
        return content

    def generate_industry_insight_post(self):
        """Generate industry insight post"""
        content = """🔮 The Future of AI Automation in 2026

3 trends I'm watching closely:

1️⃣ Human-AI Collaboration
   Moving beyond simple task automation to true partnership.
   AI handles repetitive work, humans focus on strategy.

2️⃣ Personal AI Employees
   Every professional will have AI assistants managing their workflows.
   Email, social media, scheduling—all automated with oversight.

3️⃣ Trust Through Transparency
   Audit logs, approval workflows, explainable AI.
   The key is control, not black boxes.

We're not replacing humans—we're amplifying their potential.

What AI trends are you most excited about?

#AI #FutureOfWork #Automation #Innovation #Technology"""
        
        return content

    def generate_custom_post(self):
        """Generate custom post based on user input"""
        print("\nDescribe what you'd like to post about:")
        print("(e.g., 'Our new dashboard feature', 'Tips for email automation')")
        
        topic = input("\nTopic: ").strip()
        
        if not topic:
            print("No topic provided. Generating thought leadership post instead.")
            return self.generate_thought_leadership_post()
        
        content = f"""💭 Insights on {topic}

[AI-generated content based on: {topic}]

Key points:
• Innovation in this area is accelerating
• Best practices are still emerging
• Early adopters are seeing significant benefits

The future belongs to those who embrace automation while maintaining human oversight.

What's your perspective on {topic}?

#AI #Automation #Innovation #Productivity #{topic.replace(' ', '').replace('/', '')[:20]}"""
        
        return content

    def save_post_to_pending(self, content, post_type):
        """Save generated post to Pending_Approval folder"""
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_type = re.sub(r'[^a-zA-Z0-9]', '_', post_type.lower())[:20]
        filename = f"LINKEDIN_{safe_type}_{timestamp}.md"
        filepath = self.pending_approval / filename
        
        # Create frontmatter
        frontmatter = f"""---
type: approval_request
action: linkedin_post
post_type: {post_type}
category: social_media
status: awaiting_approval
created: {datetime.now().isoformat()}
generated_by: ai_content_generator
---

# LinkedIn Post Approval Request

## Post Content

{content}

---

## Approval Instructions

Review the post content above.

**✅ To Publish:** Move this file to `/Approved/`
**❌ To Reject:** Move this file to `/Rejected/`
**✏️ To Edit:** Modify content above and then move to `/Approved/`

---
*Generated by AI Employee - LinkedIn Content Generator*
"""
        
        # Save file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(frontmatter)
        
        return filepath

    def _read_business_goals(self):
        """Extract achievements from Business_Goals.md"""
        if not self.business_goals.exists():
            return ['Automated email processing', 'LinkedIn integration complete', 'Dashboard monitoring live']
        
        try:
            with open(self.business_goals, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract bullet points or achievements
            achievements = re.findall(r'^[-*]\s+(.+)$', content, re.MULTILINE)
            return achievements[:5] if achievements else ['Business growth', 'Process optimization', 'Team expansion']
        except Exception as e:
            print(f"Warning: Could not read Business_Goals.md: {e}")
            return ['Automated email processing', 'LinkedIn integration complete', 'Dashboard monitoring live']

    def _get_recent_tasks(self):
        """Get recent tasks from Done folder"""
        if not self.done_folder.exists():
            return []
        
        try:
            tasks = list(self.done_folder.glob('*.md'))
            return sorted(tasks, key=lambda x: x.stat().st_mtime, reverse=True)[:10]
        except:
            return []

    def _get_weekly_stats(self):
        """Calculate weekly statistics"""
        if not self.done_folder.exists():
            return {'tasks': 0, 'emails': 0, 'linkedin': 0, 'time_saved': 0}
        
        week_ago = datetime.now() - timedelta(days=7)
        
        # Count files from past week
        done_files = list(self.done_folder.glob('*.md'))
        weekly_files = [
            f for f in done_files
            if datetime.fromtimestamp(f.stat().st_mtime) > week_ago
        ]
        
        # Categorize
        emails = [f for f in weekly_files if 'EMAIL' in f.name.upper()]
        linkedin = [f for f in weekly_files if 'LINKEDIN' in f.name.upper()]
        tasks = [f for f in weekly_files if 'TASK' in f.name.upper() or 'ACTION' in f.name.upper()]
        
        return {
            'tasks': len(tasks),
            'emails': len(emails),
            'linkedin': len(linkedin),
            'time_saved': len(weekly_files) * 0.5  # Estimate 30 min per task
        }

    def run_interactive(self):
        """Run interactive post generation"""
        # Show options
        self.show_post_options()
        
        # Get user selection
        choice = self.get_user_selection()
        
        # Generate content based on selection
        post_info = self.post_types[choice]
        print(f"\n✨ Generating {post_info['name']}...\n")
        
        content = post_info['generator']()
        
        # Show preview
        print("\n" + "=" * 60)
        print("GENERATED POST PREVIEW")
        print("=" * 60)
        print(content)
        print("=" * 60)
        
        # Confirm
        confirm = input("\n✅ Save this post to Pending_Approval? (y/n): ").strip().lower()
        
        if confirm == 'y':
            filepath = self.save_post_to_pending(content, post_info['name'])
            
            print(f"\n✅ Post saved to: {filepath.name}")
            print(f"\n📝 Next steps:")
            print(f"   1. Review: type \"{filepath}\"")
            print(f"   2. Approve: move {filepath} AI_Employee_Vault\\Approved\\")
            print(f"   3. Watch automation publish it to LinkedIn!")
            print()
        else:
            print("\n❌ Post discarded. Run again to generate a new one.")


def main():
    """Main entry point for interactive post generation"""
    print("\n" + "=" * 60)
    print("AI Employee - LinkedIn Content Generator")
    print("=" * 60)
    
    generator = LinkedInContentGenerator()
    generator.run_interactive()


if __name__ == "__main__":
    main()
