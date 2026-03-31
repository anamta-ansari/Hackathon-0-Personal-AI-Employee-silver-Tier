---
name: gmail-auth
description: |
  Handle OAuth 2.0 authentication with Gmail API. Manages credentials validation,
  token storage, refresh, and provides authenticated Gmail service instances.
  Required for all Gmail-related operations.
---

# Gmail Auth Skill

OAuth 2.0 authentication for Gmail API access.

## When to Use

- Before any Gmail API operations
- When token needs refresh
- To validate credentials setup
- For testing Gmail connectivity

## Prerequisites

### 1. Google Cloud Project Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing
3. Enable **Gmail API**
4. Create **OAuth 2.0 Client ID** (Desktop application)
5. Download `credentials.json`

### 2. Required API Scopes

```
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.send
https://www.googleapis.com/auth/gmail.labels
```

## CLI Usage

```bash
# Check authentication status
python ai-employee/src/skills/gmail_auth.py \
  status \
  --credentials "D:\Hackathon-0\credentials.json"

# Run authentication (opens browser)
python ai-employee/src/skills/gmail_auth.py \
  auth \
  --credentials "D:\Hackathon-0\credentials.json"

# Test Gmail connection
python ai-employee/src/skills/gmail_auth.py \
  test \
  --credentials "D:\Hackathon-0\credentials.json"

# Force token refresh
python ai-employee/src/skills/gmail_auth.py \
  auth \
  --credentials "D:\Hackathon-0\credentials.json" \
  --force-refresh
```

## Authentication Flow

```
┌─────────────────────┐
│  Check for token    │
│  (token.json)       │
└──────┬──────────────┘
       │
   ┌───┴───┐
   │       │
  Yes     No
   │       │
   ▼       ▼
┌─────┐ ┌──────────────┐
│Load │ │OAuth Flow    │
│Token│ │(Browser)     │
└──┬──┘ └──────┬───────┘
   │           │
   │      ┌────┴────┐
   │      │User     │
   │      │Grants   │
   │      │Access   │
   │      └────┬────┘
   │           │
   ▼           ▼
┌─────────────────┐
│  Validate Token │
│  (Not expired)  │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
  Valid   Expired
    │         │
    ▼         ▼
┌────────┐ ┌──────────┐
│Ready   │ │Refresh   │
│to Use  │ │Token     │
└────────┘ └──────────┘
```

## File Locations

| File | Purpose | Location |
|------|---------|----------|
| `credentials.json` | OAuth client config | Project root |
| `token.json` | User access token | Project root |
| `gmail_auth_log.txt` | Auth logs | `/Logs/` |

## Python API Usage

```python
from skills.gmail_auth import GmailAuthSkill

# Initialize
auth = GmailAuthSkill(
    credentials_path="D:\\Hackathon-0\\credentials.json",
    vault_path="D:\\Hackathon-0\\AI_Employee_Vault"
)

# Check if credentials file is valid
if not auth.validate_credentials_file():
    print("Invalid credentials.json")
    exit(1)

# Authenticate (opens browser if needed)
if not auth.authenticate():
    print("Authentication failed")
    exit(1)

# Get authenticated service
service = auth.get_service()

# Use Gmail API
results = service.users().messages().list(userId='me').execute()
```

## Output Messages

### Success
```
✓ Credentials file validated
✓ Token loaded successfully
✓ Gmail API connection test passed
✓ Authentication complete
```

### Errors
```
✗ Credentials file not found: <path>
✗ Invalid credentials format
✗ Token expired and refresh failed
✗ Gmail API connection failed: <error>
```

## Troubleshooting

### credentials.json not found

**Fix:**
1. Download from Google Cloud Console
2. Place in project root: `D:\Hackathon-0\credentials.json`

### Invalid credentials format

**Fix:** Ensure JSON structure:
```json
{
  "installed": {
    "client_id": "...",
    "client_secret": "...",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token"
  }
}
```

### Browser doesn't open

**Fix:** Manual auth URL:
1. Run auth command
2. Copy URL from console
3. Open in browser manually
4. Complete OAuth flow
5. Save token.json when prompted

### Token expired

**Fix:**
```bash
# Force refresh token
python ai-employee/src/skills/gmail_auth.py auth --force-refresh
```

### Gmail API not enabled

**Fix:**
1. Go to Google Cloud Console
2. Select your project
3. APIs & Services → Library
4. Search "Gmail API"
5. Click Enable

## Security Notes

⚠️ **Important:**
- Never commit `credentials.json` to version control
- Never commit `token.json` to version control
- Store credentials securely
- Rotate credentials periodically
- Use minimal required scopes

## Integration

### Used By

- [`gmail_watcher`](../gmail-watcher/SKILL.md) - Read emails
- [`email_mcp_server`](../email-mcp-server/SKILL.md) - Send emails
- [`send_email`](../send-email/SKILL.md) - Direct email sending

### Related Skills

- [`send_email`](../send-email/SKILL.md) - Send emails after auth
- [`gmail_watcher`](../gmail-watcher/SKILL.md) - Monitor Gmail
- [`email_mcp_server`](../email-mcp-server/SKILL.md) - MCP email operations

## Example: Complete Auth Flow

```bash
# 1. Verify credentials exist
dir credentials.json

# 2. Run authentication
python ai-employee/src/skills/gmail_auth.py auth

# Browser opens → Grant permission → token.json created

# 3. Test connection
python ai-employee/src/skills/gmail_auth.py test

# Output: ✓ Gmail API connection test passed
```

## Version

1.0.0 (Silver Tier)
