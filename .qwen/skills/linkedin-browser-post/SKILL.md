---
name: linkedin-browser-post
description: |
  Post to LinkedIn via browser automation using Playwright. Bypasses API
  limitations by automating the LinkedIn web interface. Supports text posts,
  image attachments, and engagement tracking.
---

# LinkedIn Browser Post Skill

Browser-based LinkedIn posting via Playwright automation.

## When to Use

- API posting fails or is limited
- Need to post with images/media
- Want to verify post appearance
- Testing post before scheduling

## Prerequisites

```bash
# Install Playwright
pip install playwright
playwright install chromium
```

## CLI Usage

```bash
# Test LinkedIn session (visible browser)
python ai-employee/src/skills/linkedin_browser_post.py \
  --test \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Post content (requires saved session)
python ai-employee/src/skills/linkedin_browser_post.py \
  --post \
  --content "Excited to announce our new product launch! 🚀" \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Post with image
python ai-employee/src/skills/linkedin_browser_post.py \
  --post \
  --content "Check out our latest milestone!" \
  --image "D:\Images\milestone.jpg" \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Visible browser (debug mode)
python ai-employee/src/skills/linkedin_browser_post.py \
  --post \
  --content "Test post" \
  --visible \
  --vault "D:\Hackathon-0\AI_Employee_Vault"
```

## Posting Flow

```
┌─────────────────────┐
│  Start Browser      │
│  (Playwright)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Navigate to        │
│  linkedin.com       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Load Session       │
│  (if saved)         │
└──────────┬──────────┘
           │
      ┌────┴────┐
      │         │
   Logged   Not
   In       Logged In
      │         │
      │         ▼
      │    ┌─────────┐
      │    │Login    │
      │    │Page     │
      │    └─────────┘
      │
      ▼
┌─────────────────────┐
│  Click "Start Post" │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Enter Content      │
│  (text + image)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Click "Post"       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Verify Posted      │
│  (screenshot)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Log Result         │
│  Save Session       │
└─────────────────────┘
```

## Session Management

### Session Location
```
D:\Hackathon-0\AI_Employee_Vault\.cache\linkedin_browser_session\
```

### First Run
1. Browser launches (visible)
2. Manual LinkedIn login required
3. Session cookies saved
4. Future runs use saved session

### Subsequent Runs
- Session loaded automatically
- No login needed
- Faster posting

## Python API Usage

```python
from skills.linkedin_browser_post import LinkedInBrowserPostSkill

# Initialize
poster = LinkedInBrowserPostSkill(
    vault_path="D:\\Hackathon-0\\AI_Employee_Vault"
)

# Post text only
result = poster.post_to_linkedin(
    content="Excited to share our Q1 results! 📊",
    visible=False
)

# Post with image
result = poster.post_to_linkedin(
    content="New product launch!",
    image_path="D:\\Images\\product.jpg",
    visible=True  # Watch browser for debugging
)

if result['success']:
    print(f"Post successful: {result['post_id']}")
else:
    print(f"Error: {result['error']}")
```

## Integration

### Called By

- [`approval_workflow`](../approval-workflow/SKILL.md) - Execute approved posts
- [`linkedin_post`](../linkedin-post/SKILL.md) - Alternative posting method
- **Orchestrator** - Scheduled posting

### Calls

- [`log_action`](../log-action/SKILL.md) - Log post events
- [`linkedin_auth`](../linkedin-auth/SKILL.md) - Credential management

## Error Handling

| Error | Behavior | Recovery |
|-------|----------|----------|
| Session expired | Attempts re-login | Manual login required |
| LinkedIn UI changed | Selector mismatch | Update selectors |
| Image not found | Returns error | Verify file path |
| Browser crash | Restarts browser | Auto-retry |

## Troubleshooting

### Browser doesn't launch

**Check:** Playwright installed

**Fix:**
```bash
pip install playwright
playwright install chromium
```

### Login required every time

**Check:** Session folder exists and is writable

**Fix:**
```bash
dir "D:\Hackathon-0\AI_Employee_Vault\.cache\linkedin_browser_session"
```

### Post button not found

**Check:** LinkedIn UI may have changed

**Fix:** Update selectors in `linkedin_browser_post.py`

## Security Notes

⚠️ **Important:**
- Session cookies provide account access
- Never commit session files to version control
- Review LinkedIn Terms of Service for automation
- Use responsibly to avoid account restrictions

## Related Skills

- [`linkedin_post`](../linkedin-post/SKILL.md) - Content generation
- [`linkedin_auth`](../linkedin-auth/SKILL.md) - Authentication
- [`browsing-with-playwright`](../browsing-with-playwright/SKILL.md) - Browser automation

## Version

1.0.0 (Silver Tier)
