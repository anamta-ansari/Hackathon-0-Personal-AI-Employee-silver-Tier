"""
Helper script to create test LinkedIn posts in Approved folder
"""

from pathlib import Path
from datetime import datetime
import random


def create_test_post():
    """Create a test post in Approved folder"""
    
    # Vault path - use the path the orchestrator is actually using
    vault = Path(r"D:\Hackathon-0\AI_Employee_Vault")
    approved = vault / "Approved"
    
    # Ensure folder exists
    approved.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_linkedin_post_{timestamp}.md"
    filepath = approved / filename
    
    # Random test content
    emojis = ["🚀", "🎉", "✨", "🔥", "💡", "⚡", "🎯"]
    emoji = random.choice(emojis)
    
    content = f"""---
type: linkedin_post
action: linkedin_post
post_type: test
category: social_media
status: approved
created: {datetime.now().isoformat()}
---

## Post Content

{emoji} Auto-posting test #{random.randint(1, 999)}

This is an automated test post created at {datetime.now().strftime("%I:%M %p")}.

The AI Employee orchestrator is:
✅ Monitoring the Approved folder
✅ Detecting new posts every 30 seconds
✅ Auto-posting to LinkedIn

#AIAutomation #LinkedIn #Testing
"""
    
    # Save file
    filepath.write_text(content, encoding='utf-8')
    
    print("="*70)
    print("TEST POST CREATED")
    print("="*70)
    print(f"\n✓ File created: {filepath}")
    print(f"✓ Location: Approved/ folder")
    print(f"\nThe orchestrator should detect this file within 30 seconds.")
    print("\nWatch your orchestrator terminal for:")
    print("  - 'Found approval file: {}'".format(filename))
    print("  - '[LINKEDIN] Processing LinkedIn post'")
    print("\nAfter posting, the file will move to Done/ folder.")
    print("="*70)
    
    return filepath


if __name__ == "__main__":
    create_test_post()
