---
name: linkedin-auth
description: |
  Handle LinkedIn authentication using email/password or API credentials.
  Manages secure credential storage in .env file, validates authentication,
  and provides authenticated LinkedIn API instances.
---

# LinkedIn Auth Skill

LinkedIn authentication management for automated posting.

## When to Use

- Initial LinkedIn setup
- Credential validation
- Re-authentication after session expiry
- Testing LinkedIn connectivity

## Prerequisites

```bash
# Install LinkedIn API library
pip install linkedin-api

# Install python-dotenv for credential management
pip install python-dotenv
```

## CLI Usage

```bash
# Set up LinkedIn credentials (interactive)
python ai-employee/src/skills/linkedin_auth.py \
  auth \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Test credentials
python ai-employee/src/skills/linkedin_auth.py \
  test \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Check authentication status
python ai-employee/src/skills/linkedin_auth.py \
  status \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Revoke credentials
python ai-employee/src/skills/linkedin_auth.py \
  revoke \
  --vault "D:\Hackathon-0\AI_Employee_Vault"
```

## Authentication Flow

```
┌─────────────────────┐
│  Run: auth command  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Prompt for Email   │
│  and Password       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Store in .env      │
│  (encrypted)        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Test Connection    │
│  via LinkedIn API   │
└──────────┬──────────┘
           │
      ┌────┴────┐
      │         │
    Success   Failed
      │         │
      ▼         ▼
┌─────────┐ ┌──────────┐
│Ready    │ │Error     │
│to Post  │ │Message   │
└─────────┘ └──────────┘
```

## Credential Storage

Credentials stored in `.env` file (project root):

```bash
# .env file
LINKEDIN_EMAIL=your.email@example.com
LINKEDIN_PASSWORD=your_secure_password
```

⚠️ **Security Notes:**
- Never commit `.env` to version control
- Use strong, unique password
- Consider using LinkedIn API credentials instead of email/password
- Review LinkedIn Terms of Service for automation

## Python API Usage

```python
from skills.linkedin_auth import LinkedInAuthManager

# Initialize
auth = LinkedInAuthManager(
    vault_path="D:\\Hackathon-0\\AI_Employee_Vault"
)

# Test authentication
if not auth.test_credentials():
    print("Authentication failed")
    exit(1)

# Get authenticated LinkedIn instance
linkedin = auth.get_linkedin_instance()

# Use LinkedIn API
profile = linkedin.get_profile()
print(f"Logged in as: {profile['firstName']} {profile['lastName']}")
```

## Integration

### Called By

- [`linkedin_post`](../linkedin-post/SKILL.md) - Before posting
- [`linkedin_browser_post`](../linkedin-browser-post/SKILL.md) - For browser auth
- [`linkedin_mcp_server`](../linkedin-mcp-server/SKILL.md) - For MCP operations

### Calls

- [`log_action`](../log-action/SKILL.md) - Log auth events
- **File System**: Read/write .env file

## Error Handling

| Error | Behavior | Recovery |
|-------|----------|----------|
| Invalid credentials | Returns error | Re-enter credentials |
| LinkedIn API unavailable | Logs error | Check library install |
| .env file missing | Creates new file | Auto-recovery |
| Network error | Logs error | Check connection |

## Troubleshooting

### Authentication fails

**Check:** Credentials are correct

**Fix:**
```bash
# Revoke and re-enter
python ai-employee/src/skills/linkedin_auth.py revoke
python ai-employee/src/skills/linkedin_auth.py auth
```

### LinkedIn API not available

**Fix:**
```bash
pip install linkedin-api
```

### .env file not found

**Fix:** Create manually:
```bash
# In project root
echo LINKEDIN_EMAIL=your.email@example.com >> .env
echo LINKEDIN_PASSWORD=your_password >> .env
```

## Related Skills

- [`linkedin_post`](../linkedin-post/SKILL.md) - Post creation
- [`linkedin_browser_post`](../linkedin-browser-post/SKILL.md) - Browser posting
- [`gmail_auth`](../gmail-auth/SKILL.md) - Similar auth pattern

## Example: Complete Setup

```bash
# 1. Install dependencies
pip install linkedin-api python-dotenv

# 2. Run authentication
python ai-employee/src/skills/linkedin_auth.py auth

# Enter email: your.email@example.com
# Enter password: ********

# 3. Test connection
python ai-employee/src/skills/linkedin_auth.py test

# Output: ✓ LinkedIn authentication successful

# 4. Check status
python ai-employee/src/skills/linkedin_auth.py status

# Output:
# Email: your.email@example.com
# Status: Authenticated
# Last tested: 2026-03-29 18:00:00
```

## Version

1.0.0 (Silver Tier)
