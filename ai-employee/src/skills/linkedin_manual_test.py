#!/usr/bin/env python3
"""
LinkedIn Manual Test - Opens visible browser for debugging

This script opens a VISIBLE browser window so you can see what's happening.
Use this to diagnose LinkedIn posting issues.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Set memory limits BEFORE importing playwright
os.environ['NODE_OPTIONS'] = '--max-old-space-size=1024'

from playwright.sync_api import sync_playwright

project_root = Path(__file__).parent.parent.parent
config_dir = project_root / 'config'
session_file = config_dir / 'linkedin_session.json'
logs_dir = project_root / 'logs'

print("=" * 60)
print("LinkedIn Manual Browser Test")
print("=" * 60)
print()

# Load session
if not session_file.exists():
    print("❌ Session file not found!")
    print("Run: python src/skills/linkedin_session_auth.py login")
    sys.exit(1)

with open(session_file, 'r', encoding='utf-8') as f:
    session = json.load(f)

print(f"✓ Session loaded from {session_file}")
print(f"  Cookies: {len(session.get('cookies', []))}")
print(f"  Saved: {session.get('saved_at', 'unknown')}")
print()

print("Opening VISIBLE browser window...")
print("Watch the browser window to see what happens!")
print()

try:
    playwright = sync_playwright().start()
    
    # Launch VISIBLE browser with persistent context (for cookies to work)
    import tempfile
    temp_dir = tempfile.mkdtemp(prefix='linkedin_test_')
    print(f"Using temp profile: {temp_dir}")
    
    # Use launch_persistent_context for proper cookie support
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=temp_dir,
        headless=False,  # VISIBLE!
        args=[
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-dev-shm-usage',
        ],
        viewport={'width': 1280, 'height': 800},
        user_agent=session.get('user_agent'),
        timeout=60000  # 60 second launch timeout
    )
    
    # Add cookies to the persistent context
    cookies = session.get('cookies', [])
    if cookies:
        context.add_cookies(cookies)
        print(f"✓ Loaded {len(cookies)} cookies")
    
    page = context.pages[0]  # Get the first page from persistent context
    
    # Navigate to LinkedIn
    print("Navigating to LinkedIn...")
    print("WATCH THE BROWSER WINDOW!")
    print()
    
    try:
        page.goto('https://www.linkedin.com', wait_until='domcontentloaded', timeout=60000)
        page.wait_for_timeout(10000)  # Wait 10 seconds
        
        print(f"Current URL: {page.url}")
        
        # Check if logged in
        if 'login' in page.url:
            print()
            print("❌ REDIRECTED TO LOGIN PAGE")
            print("Your session cookies are not working.")
            print()
            print("Solution:")
            print("  1. Close this browser window")
            print("  2. Run: python src/skills/linkedin_session_auth.py login")
            print("  3. Log in MANUALLY in the browser that opens")
            print("  4. Wait for 'SESSION SAVED SUCCESSFULLY' message")
        else:
            print()
            print("✓ Successfully reached LinkedIn")
            print()
            print("If you see the LinkedIn feed, you're logged in!")
            print()
            print("Testing post creation...")
            
            # Try to find "Start a post" button
            try:
                post_btn = page.wait_for_selector('button:has-text("Start a post")', timeout=5000)
                if post_btn:
                    print("✓ 'Start a post' button found")
            except:
                print("⚠ 'Start a post' button not found")
        
        # Save screenshot
        screenshot = logs_dir / f"linkedin_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        page.screenshot(path=str(screenshot))
        print(f"✓ Screenshot saved: {screenshot}")
        
    except Exception as e:
        print(f"❌ Navigation error: {e}")
        print()
        print("Possible causes:")
        print("  1. No internet connection")
        print("  2. LinkedIn is down")
        print("  3. Firewall/proxy blocking access")
        print("  4. LinkedIn blocking automated browsers")
    
    print()
    print("Browser will close in 5 seconds...")
    page.wait_for_timeout(5000)
    
    context.close()
    playwright.stop()
    
    print()
    print("=" * 60)
    print("Test complete!")
    print("=" * 60)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
