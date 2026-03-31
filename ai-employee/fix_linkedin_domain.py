"""
Fix LinkedIn Session Domain

This script fixes the domain mismatch in LinkedIn session cookies.
LinkedIn sessions often fail because li_at cookie is saved with wrong domain.
"""

import json
from pathlib import Path

def fix_linkedin_session_domain():
    """Fix domain mismatch in LinkedIn session cookies"""
    
    config_dir = Path(__file__).parent / 'config'
    session_file = config_dir / 'linkedin_session.json'
    
    if not session_file.exists():
        print("❌ No session file found!")
        print("Run: python src/skills/linkedin_session_auth.py login")
        return
    
    # Load session
    with open(session_file, 'r', encoding='utf-8') as f:
        session_data = json.load(f)
    
    cookies = session_data.get('cookies', [])
    fixed_count = 0
    
    print("Fixing LinkedIn session domains...")
    print("-" * 60)
    
    for cookie in cookies:
        name = cookie.get('name', '')
        domain = cookie.get('domain', '')
        
        # Fix li_at and liap domain to .linkedin.com (not .www.linkedin.com)
        if name in ['li_at', 'liap', 'li_rm'] and domain == '.www.linkedin.com':
            old_domain = domain
            cookie['domain'] = '.linkedin.com'
            print(f"✓ Fixed {name}: {old_domain} → {cookie['domain']}")
            fixed_count += 1
        
        # Also fix JSESSIONID
        if name == 'JSESSIONID' and domain == '.www.linkedin.com':
            old_domain = domain
            cookie['domain'] = '.www.linkedin.com'  # Keep this one as is
            print(f"  Kept {name}: {domain} (correct)")
    
    # Save fixed session
    with open(session_file, 'w', encoding='utf-8') as f:
        json.dump(session_data, f, indent=2)
    
    print("-" * 60)
    print(f"✅ Fixed {fixed_count} cookie(s)")
    print()
    print("Now test the session:")
    print("  python src/skills/linkedin_session_auth.py test")


if __name__ == '__main__':
    fix_linkedin_session_domain()
