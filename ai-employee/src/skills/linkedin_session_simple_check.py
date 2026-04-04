#!/usr/bin/env python3
"""
Simple LinkedIn Session Validator - No Playwright

This script validates LinkedIn session by checking cookie format and expiry.
Use this when Playwright keeps crashing due to memory issues.
"""

import json
from pathlib import Path
from datetime import datetime

# Go up two levels from src/skills to project root, then to config
project_root = Path(__file__).parent.parent.parent
config_dir = project_root / 'config'
session_file = config_dir / 'linkedin_session.json'

print("=" * 60)
print("LinkedIn Session Validator (Simple Mode)")
print("=" * 60)
print()

if not session_file.exists():
    print("❌ Session file NOT found!")
    print(f"   Expected: {session_file}")
    print()
    print("You need to login first:")
    print("   python src/skills/linkedin_session_auth.py login")
    exit(1)

print(f"✓ Session file found: {session_file}")
print()

try:
    with open(session_file, 'r', encoding='utf-8') as f:
        session = json.load(f)
except Exception as e:
    print(f"❌ Error reading session file: {e}")
    exit(1)

# Check cookies
cookies = session.get('cookies', [])
print(f"📊 Cookies found: {len(cookies)}")

# Find li_at cookie (most important)
li_at_cookie = None
for cookie in cookies:
    if cookie.get('name') == 'li_at':
        li_at_cookie = cookie
        break

if li_at_cookie:
    print("✓ li_at cookie found (primary auth cookie)")
    print(f"  Domain: {li_at_cookie.get('domain')}")
    print(f"  Value starts with: {li_at_cookie.get('value', '')[:50]}...")
    
    # Check expiry
    expires = li_at_cookie.get('expires')
    if expires:
        expiry_date = datetime.fromtimestamp(expires)
        days_until_expiry = (expiry_date - datetime.now()).days
        print(f"  Expires: {expiry_date.strftime('%Y-%m-%d')} ({days_until_expiry} days from now)")
        
        if days_until_expiry < 0:
            print("  ❌ EXPIRED!")
        elif days_until_expiry < 7:
            print("  ⚠️  Expires soon - consider re-login")
        else:
            print("  ✓ Valid")
else:
    print("❌ li_at cookie NOT found!")
    print("   This is required for LinkedIn authentication.")
    print()
    print("Re-login required:")
    print("   python src/skills/linkedin_session_auth.py login")
    exit(1)

print()

# Check user agent
user_agent = session.get('user_agent')
if user_agent:
    print(f"✓ User agent present")
    print(f"  {user_agent[:80]}...")
else:
    print("⚠️  No user agent saved")

print()

# Check saved timestamp
saved_at = session.get('saved_at')
if saved_at:
    saved_dt = datetime.fromisoformat(saved_at)
    age_hours = (datetime.now() - saved_dt).total_seconds() / 3600
    print(f"✓ Session saved: {saved_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Age: {age_hours:.1f} hours ago")
    
    if age_hours > 720:  # More than 30 days
        print("  ⚠️  Session is old - may need re-login")
    else:
        print("  ✓ Recent session")

print()
print("=" * 60)
print("VALIDATION SUMMARY")
print("=" * 60)
print()

# Final verdict
if li_at_cookie and days_until_expiry > 0 and age_hours < 720:
    print("✅ Session appears VALID based on cookie checks")
    print()
    print("Note: This is a basic validation. To fully test:")
    print("  1. Open browser and go to linkedin.com")
    print("  2. Check if you're automatically logged in")
    print()
    print("If LinkedIn posting still fails, try:")
    print("  python src/skills/linkedin_session_auth.py login")
    print("  (to get fresh cookies)")
    exit(0)
else:
    print("❌ Session appears INVALID or EXPIRED")
    print()
    print("Re-login required:")
    print("  python src/skills/linkedin_session_auth.py login")
    exit(1)
