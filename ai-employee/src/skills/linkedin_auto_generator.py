#!/usr/bin/env python3
"""
LinkedIn Auto Generator - Scheduled Post Creation

Automatically generates LinkedIn posts on a schedule.

Schedule:
- Monday 10 AM: Weekly summary
- Wednesday 10 AM: Thought leadership
- Friday 10 AM: Milestone/achievement

Usage:
    python src/skills/linkedin_auto_generator.py
    
Or integrate with orchestrator for automatic scheduling.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import content generator
try:
    from .linkedin_content_generator import LinkedInContentGenerator
except ImportError:
    from linkedin_content_generator import LinkedInContentGenerator


class LinkedInAutoGenerator:
    """
    Scheduled LinkedIn Post Generator
    
    Automatically generates posts based on day-of-week schedule.
    """
    
    def __init__(self):
        """Initialize auto-generator"""
        self.generator = LinkedInContentGenerator()
        
        # Schedule: weekday (0=Monday) -> post type method name
        self.schedule = {
            0: ('weekly_summary', 'generate_weekly_summary_post'),      # Monday
            2: ('thought_leadership', 'generate_thought_leadership_post'),  # Wednesday
            4: ('milestone', 'generate_milestone_post'),                # Friday
        }
        
        # Generation hours (24-hour format)
        self.generation_hour = 10  # 10 AM
        
        # Track last generation to prevent duplicates
        self.last_generation_date = None

    def should_generate_now(self):
        """
        Check if we should generate a post now
        
        Returns:
            bool: True if generation should occur
        """
        now = datetime.now()
        today_weekday = now.weekday()  # 0 = Monday
        current_hour = now.hour
        
        # Check if today is a scheduled day
        if today_weekday not in self.schedule:
            logger.debug(f"Today ({self._weekday_name(today_weekday)}) is not a scheduled generation day")
            return False
        
        # Check if it's generation hour
        if current_hour != self.generation_hour:
            logger.debug(f"Current hour ({current_hour}) is not generation hour ({self.generation_hour})")
            return False
        
        # Check if already generated today
        if self._already_generated_today():
            logger.info("Already generated a post today")
            return False
        
        logger.info(f"Scheduled generation triggered on {self._weekday_name(today_weekday)} at {current_hour}:00")
        return True

    def generate_scheduled_post(self):
        """
        Generate post based on today's schedule
        
        Returns:
            Path: Path to generated post file, or None if failed
        """
        now = datetime.now()
        today_weekday = now.weekday()
        
        # Get today's post type
        post_info = self.schedule.get(today_weekday)
        if not post_info:
            logger.warning(f"No scheduled post type for {self._weekday_name(today_weekday)}")
            return None
        
        post_type_name, method_name = post_info
        
        logger.info(f"Generating scheduled {post_type_name} post")
        
        # Get generator method
        generator_method = getattr(self.generator, method_name, None)
        if not generator_method:
            logger.error(f"Generator method {method_name} not found")
            return None
        
        # Generate content
        try:
            content = generator_method()
        except Exception as e:
            logger.error(f"Error generating content: {e}")
            return None
        
        # Save to Pending_Approval
        try:
            filepath = self.generator.save_post_to_pending(content, post_type_name)
            logger.info(f"✅ Auto-generated post saved: {filepath.name}")
            
            # Update last generation date
            self.last_generation_date = now.date()
            
            return filepath
        except Exception as e:
            logger.error(f"Error saving post: {e}")
            return None

    def _already_generated_today(self):
        """
        Check if we already generated a post today
        
        Returns:
            bool: True if post already generated
        """
        today_str = datetime.now().strftime('%Y%m%d')
        
        try:
            pending_files = list(self.generator.pending_approval.glob(f'LINKEDIN_*{today_str}*.md'))
            return len(pending_files) > 0
        except Exception as e:
            logger.debug(f"Error checking generated posts: {e}")
            return False

    def _weekday_name(self, weekday):
        """Get weekday name from number"""
        names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return names[weekday] if 0 <= weekday < 7 else 'Unknown'

    def force_generate(self, post_type=None):
        """
        Force generate a post regardless of schedule
        
        Args:
            post_type: Optional post type override
            
        Returns:
            Path: Path to generated post file
        """
        now = datetime.now()
        today_weekday = now.weekday()
        
        # Use provided type or get from schedule
        if post_type:
            post_type_name = post_type
            method_name = f'generate_{post_type}_post'
        else:
            post_info = self.schedule.get(today_weekday, ('thought_leadership', 'generate_thought_leadership_post'))
            post_type_name, method_name = post_info
        
        logger.info(f"Force generating {post_type_name} post")
        
        # Get generator method
        generator_method = getattr(self.generator, method_name, None)
        if not generator_method:
            logger.error(f"Generator method {method_name} not found")
            return None
        
        # Generate and save
        content = generator_method()
        filepath = self.generator.save_post_to_pending(content, post_type_name)
        
        logger.info(f"✅ Force-generated post: {filepath.name}")
        return filepath


def main():
    """Main entry point for testing"""
    print("=" * 60)
    print("LinkedIn Auto Generator")
    print("=" * 60)
    print()
    
    auto_gen = LinkedInAutoGenerator()
    
    # Check if should generate
    if auto_gen.should_generate_now():
        print("Scheduled generation triggered...")
        filepath = auto_gen.generate_scheduled_post()
        
        if filepath:
            print(f"\n✅ Post generated: {filepath.name}")
            print(f"📝 Post ready for review in Pending_Approval/")
        else:
            print("\n❌ Post generation failed")
    else:
        print("Not a scheduled generation time.")
        print()
        print("Schedule:")
        print("  Monday 10 AM: Weekly summary")
        print("  Wednesday 10 AM: Thought leadership")
        print("  Friday 10 AM: Milestone")
        print()
        print("To force generate now, use:")
        print("  python src/skills/linkedin_auto_generator.py --force")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='LinkedIn Auto Generator')
    parser.add_argument('--force', action='store_true', help='Force generate post now')
    parser.add_argument('--type', type=str, help='Post type for force generation')
    
    args = parser.parse_args()
    
    if args.force:
        auto_gen = LinkedInAutoGenerator()
        filepath = auto_gen.force_generate(args.type)
        if filepath:
            print(f"✅ Post generated: {filepath.name}")
        else:
            print("❌ Post generation failed")
    else:
        main()
