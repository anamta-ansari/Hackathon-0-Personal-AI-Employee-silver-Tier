# LinkedIn Posting Troubleshooting Guide

## Problem: LinkedIn Posts Failing with "Session expired or invalid"

### Symptoms
- Files moving from `Approved/` to `Failed/` folder
- Error message: `Session expired or invalid`
- MCP server crashes with "JavaScript heap out of memory"
- Browser fallback fails with connection errors

### Root Cause
The LinkedIn session cookies saved in `config/linkedin_session.json` have expired. LinkedIn sessions typically last 30-90 days, but can expire sooner due to:
- Password changes
- Security updates from LinkedIn
- Account activity from other devices
- LinkedIn clearing old sessions

### Solution: Re-authenticate LinkedIn

**Step 1: Stop the orchestrator** (if running)
```bash
# Press Ctrl+C in the orchestrator terminal
```

**Step 2: Run LinkedIn authentication**
```bash
cd D:\Hackathon-0\ai-employee
python src/skills/linkedin_session_auth.py login
```

**Step 3: Complete the login**
1. A browser window will open automatically
2. Log into LinkedIn with your email/password
3. Complete any 2FA if prompted
4. Wait for the automatic detection (takes ~5-10 seconds after login)
5. You should see: `✓ SESSION SAVED SUCCESSFULLY`

**Step 4: Verify session**
```bash
python src/skills/linkedin_session_auth.py test
```

Expected output: `✓ Session is valid`

**Step 5: Retry failed posts**
1. Navigate to `D:\Hackathon-0\AI_Employee_Vault\Failed\`
2. Find the LinkedIn post files (e.g., `LINKEDIN___thought_leadership_*.md`)
3. Move them to `D:\Hackathon-0\AI_Employee_Vault\Approved\`
4. Restart the orchestrator:
   ```bash
   python src/orchestration/orchestrator.py
   ```

---

## Prevention: Keep LinkedIn Session Active

### Option 1: Regular Re-authentication (Recommended)
Set a reminder to re-authenticate every 30 days:
```bash
# Add to your calendar or task scheduler
python src/skills/linkedin_session_auth.py login
```

### Option 2: Use Environment Variable (Advanced)
If you have a LinkedIn `li_at` cookie token, add to `.env`:
```env
LINKEDIN_SESSION_TOKEN=your_li_at_cookie_value_here
LINKEDIN_COOKIE_DOMAIN=.linkedin.com
```

To get your `li_at` cookie:
1. Log into LinkedIn in your browser
2. Open Developer Tools (F12)
3. Go to Application/Storage → Cookies → linkedin.com
4. Copy the value of the `li_at` cookie
5. Paste into `.env` file

---

## Technical Details

### What Was Fixed

**Issue 1: MCP Server Memory Crash**
- **Problem**: Playwright processes running out of JavaScript heap memory
- **Fix**: Added memory limits (`--js-flags="--max-old-space-size=512"`) and proper cleanup

**Issue 2: Async/Sync API Conflict**
- **Problem**: Using sync_playwright() inside asyncio loop
- **Fix**: Removed context manager usage, manual start/stop of playwright

**Issue 3: Slow Content Typing**
- **Problem**: Character-by-character typing causing timeouts
- **Fix**: JavaScript injection for instant content insertion

**Issue 4: Poor Error Messages**
- **Problem**: Generic errors without actionable guidance
- **Fix**: Added specific error messages with re-authentication instructions

### Files Modified
1. `src/skills/linkedin_mcp_server.py` - Fixed memory issues and async conflicts
2. `src/orchestration/orchestrator.py` - Added better error handling and user guidance

---

## Quick Reference Commands

```bash
# Check session status
python src/skills/linkedin_session_auth.py status

# Login (saves new session)
python src/skills/linkedin_session_auth.py login

# Test current session
python src/skills/linkedin_session_auth.py test

# Clear session (logout)
python src/skills/linkedin_session_auth.py logout

# Run orchestrator
python src/orchestration/orchestrator.py
```

---

## Still Having Issues?

### Debug Steps

1. **Check if Playwright is installed**:
   ```bash
   python -m playwright install chromium
   ```

2. **Check session file exists**:
   ```bash
   dir config\linkedin_session.json
   ```

3. **Check logs**:
   - `D:\Hackathon-0\ai-employee\logs\linkedin_session_YYYY-MM-DD.json`
   - `D:\Hackathon-0\AI_Employee_Vault\Logs\orchestrator_YYYY-MM-DD.log`

4. **Manual browser test**:
   ```bash
   python src/skills/linkedin_session_auth.py login
   # When browser opens, manually navigate to linkedin.com/feed
   # Check if you're logged in
   ```

### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `Session expired or invalid` | Cookies expired | Re-run `login` command |
| `No LinkedIn session found` | Session file missing | Re-run `login` command |
| `Playwright not available` | Playwright not installed | `pip install playwright playwright-stealth` |
| `Navigation timeout` | Slow internet or LinkedIn down | Check connection, retry |
| `Not logged in` | Manual login not completed | Complete login in browser window |

---

## Contact & Support

For additional help:
- Check the main documentation: `qwen.md`
- Review logs in `D:\Hackathon-0\AI_Employee_Vault\Logs\`
- Join the Wednesday Research Meeting (Zoom link in qwen.md)
