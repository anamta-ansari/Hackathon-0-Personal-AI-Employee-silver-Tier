# AI Employee Agent Skills Index

Complete index of all Agent Skills for the Personal AI Employee Hackathon 0.

**Total Skills:** 19
**Tiers:** Bronze (5) + Silver (14)

---

## Quick Reference by Category

### 📧 Email & Communication

| Skill | Tier | Description |
|-------|------|-------------|
| [`process-email`](./process-email/SKILL.md) | Bronze | Process email action files |
| [`send-email`](./send-email/SKILL.md) | Silver | Send emails via Gmail API |
| [`gmail-auth`](./gmail-auth/SKILL.md) | Silver | Gmail OAuth authentication |
| [`gmail-watcher`](./gmail-watcher/SKILL.md) | Silver | Monitor Gmail for new emails |
| [`email-mcp-server`](./email-mcp-server/SKILL.md) | Silver | MCP server for email operations |

### 💬 Messaging

| Skill | Tier | Description |
|-------|------|-------------|
| [`whatsapp-watcher`](./whatsapp-watcher/SKILL.md) | Silver | Monitor WhatsApp Web |

### 💼 LinkedIn

| Skill | Tier | Description |
|-------|------|-------------|
| [`linkedin-post`](./linkedin-post/SKILL.md) | Silver | Create LinkedIn posts |
| [`linkedin-auth`](./linkedin-auth/SKILL.md) | Silver | LinkedIn authentication |
| [`linkedin-browser-post`](./linkedin-browser-post/SKILL.md) | Silver | Browser-based posting |
| [`linkedin-content-generator`](./linkedin-content-generator/SKILL.md) | Silver | Generate post content |
| [`linkedin-mcp-server`](./linkedin-mcp-server/SKILL.md) | Silver | MCP server for LinkedIn |

### 📋 Workflow & Approval

| Skill | Tier | Description |
|-------|------|-------------|
| [`create-approval-request`](./create-approval-request/SKILL.md) | Bronze | Create approval files |
| [`approval-workflow`](./approval-workflow/SKILL.md) | Silver | Manage approval workflow |
| [`move-to-done`](./move-to-done/SKILL.md) | Bronze | Archive completed items |
| [`create-plan`](./create-plan/SKILL.md) | Silver | Generate action plans |

### 📊 Dashboard & Logging

| Skill | Tier | Description |
|-------|------|-------------|
| [`update-dashboard`](./update-dashboard/SKILL.md) | Bronze | Refresh Dashboard.md |
| [`log-action`](./log-action/SKILL.md) | Bronze | Audit logging |

### ⏰ Scheduling

| Skill | Tier | Description |
|-------|------|-------------|
| [`scheduler`](./scheduler/SKILL.md) | Silver | Task scheduling |

### 🌐 Browser Automation

| Skill | Tier | Description |
|-------|------|-------------|
| [`browsing-with-playwright`](./browsing-with-playwright/SKILL.md) | Built-in | Playwright browser automation |

---

## Skills by Tier

### Bronze Tier (Foundation) - 5 Skills

```
.qwen/skills/
├── process-email/
│   └── SKILL.md
├── update-dashboard/
│   └── SKILL.md
├── log-action/
│   └── SKILL.md
├── create-approval-request/
│   └── SKILL.md
└── move-to-done/
    └── SKILL.md
```

**Purpose:** Core workflow management - process inputs, track actions, manage approvals, archive completions.

### Silver Tier (Functional) - 14 Skills

```
.qwen/skills/
├── gmail-auth/
│   └── SKILL.md
├── gmail-watcher/
│   └── SKILL.md
├── whatsapp-watcher/
│   └── SKILL.md
├── send-email/
│   └── SKILL.md
├── create-plan/
│   └── SKILL.md
├── approval-workflow/
│   └── SKILL.md
├── email-mcp-server/
│   └── SKILL.md
├── scheduler/
│   └── SKILL.md
├── linkedin-post/
│   └── SKILL.md
├── linkedin-auth/
│   └── SKILL.md
├── linkedin-browser-post/
│   └── SKILL.md
├── linkedin-content-generator/
│   └── SKILL.md
├── linkedin-mcp-server/
│   └── SKILL.md
└── browsing-with-playwright/
    └── SKILL.md
```

**Purpose:** External integrations - Gmail, WhatsApp, LinkedIn, scheduling, MCP servers.

---

## Skill Architecture

### Standard Skill Structure

Each skill follows this pattern:

```
.qwen/skills/<skill-name>/
├── SKILL.md           # Manifest (what, when, how to use)
└── references/        # Optional: Additional documentation
    └── <topic>.md
```

### Python Implementation

```
ai-employee/src/skills/
├── <skill_name>.py    # Python implementation
└── __init__.py        # Package exports
```

### SKILL.md Sections

Every SKILL.md contains:

1. **Frontmatter** - Name and description
2. **When to Use** - Trigger conditions
3. **CLI Usage** - Command-line examples
4. **How It Works** - Flow diagrams
5. **Input/Output** - Data formats
6. **Python API** - Programmatic usage
7. **Integration** - Calls and called by
8. **Error Handling** - Common errors and recovery
9. **Troubleshooting** - Common issues and fixes
10. **Related Skills** - Cross-references

---

## Usage Examples

### Example 1: Process New Email

```bash
# 1. Gmail Watcher detects email
python ai-employee/src/skills/gmail_watcher_skill.py --once

# 2. Process email and create plan
python ai-employee/src/skills/process_email.py \
  "D:\Hackathon-0\AI_Employee_Vault\Needs_Action\EMAIL_123.md"

# 3. Approval created in Pending_Approval
# 4. Human approves (moves to Approved)
# 5. Send email
python ai-employee/src/skills/send_email.py \
  --to "client@example.com" \
  --subject "Re: Inquiry" \
  --body "Thank you for your email..."

# 6. Archive to Done
python ai-employee/src/skills/move_to_done.py \
  "D:\Hackathon-0\AI_Employee_Vault\Approved\EMAIL_123.md"
```

### Example 2: LinkedIn Post Workflow

```bash
# 1. Generate content
python ai-employee/src/skills/linkedin_content_generator.py \
  --source business_goals

# 2. Create post with approval
python ai-employee/src/skills/linkedin_post.py \
  --generate milestone

# 3. Human approves (moves file to Approved)

# 4. Post to LinkedIn
python ai-employee/src/skills/linkedin_browser_post.py \
  --post \
  --content "🎉 Business Milestone Achieved!..."
```

### Example 3: Scheduled Daily Briefing

```bash
# Create scheduled task
python ai-employee/src/skills/scheduler.py \
  --create daily_briefing \
  --type daily_briefing

# Task runs daily at 8 AM:
# - Reads Business_Goals.md
# - Reads Dashboard.md
# - Generates CEO Briefing
# - Updates Dashboard.md
```

---

## Integration Map

```
┌─────────────────────────────────────────────────────────────┐
│                    EXTERNAL SOURCES                         │
│   Gmail API │ WhatsApp Web │ LinkedIn │ File System         │
└────────┬────────────┬──────────────┬────────────┬───────────┘
         │            │              │            │
         ▼            ▼              ▼            ▼
┌─────────────────────────────────────────────────────────────┐
│                   PERCEPTION SKILLS                         │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────────┐ │
│  │gmail-watcher │ │whatsapp-     │ │filesystem_watcher   │ │
│  │              │ │watcher       │ │(Python script)      │ │
│  └──────────────┘ └──────────────┘ └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
         │            │              │
         ▼            ▼              ▼
┌─────────────────────────────────────────────────────────────┐
│                  PROCESSING SKILLS                          │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────────┐ │
│  │process-email │ │create-plan   │ │update-dashboard     │ │
│  └──────────────┘ └──────────────┘ └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
         │            │              │
         ▼            ▼              ▼
┌─────────────────────────────────────────────────────────────┐
│                 APPROVAL SKILLS                             │
│  ┌──────────────────────────┐ ┌───────────────────────────┐ │
│  │create-approval-request   │ │approval-workflow          │ │
│  └──────────────────────────┘ └───────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
         │            │              │
         ▼            ▼              ▼
┌─────────────────────────────────────────────────────────────┐
│                   ACTION SKILLS                             │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────────┐ │
│  │send-email    │ │linkedin-post │ │log-action           │ │
│  │email-mcp     │ │linkedin-mcp  │ │move-to-done         │ │
│  └──────────────┘ └──────────────┘ └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
         │            │              │
         ▼            ▼              ▼
┌─────────────────────────────────────────────────────────────┐
│                   SUPPORT SKILLS                            │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────────┐ │
│  │gmail-auth    │ │linkedin-auth │ │scheduler            │ │
│  │browsing-with-playwright       │ │content-generator    │ │
│  └──────────────┘ └──────────────┘ └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Installation & Setup

### 1. Install Python Dependencies

```bash
# Core dependencies
pip install google-auth google-auth-oauthlib google-auth-httplib2 \
            google-api-python-client

# Playwright for browser automation
pip install playwright
playwright install chromium

# LinkedIn API
pip install linkedin-api

# Environment management
pip install python-dotenv
```

### 2. Configure MCP Servers

Add to Qwen Code MCP configuration:

```json
{
  "servers": {
    "email": {
      "command": "python",
      "args": ["ai-employee/src/skills/email_mcp_server.py", "--serve"],
      "env": {
        "VAULT_PATH": "D:/Hackathon-0/AI_Employee_Vault"
      }
    },
    "linkedin": {
      "command": "python",
      "args": ["ai-employee/src/skills/linkedin_mcp_server.py", "--serve"],
      "env": {
        "VAULT_PATH": "D:/Hackathon-0/AI_Employee_Vault",
        "LINKEDIN_EMAIL": "your.email@example.com",
        "LINKEDIN_PASSWORD": "your_password"
      }
    }
  }
}
```

### 3. Set Up Credentials

```bash
# Gmail OAuth
# Place credentials.json in project root

# LinkedIn
python ai-employee/src/skills/linkedin_auth.py auth

# Verify all skills
python ai-employee/src/skills/gmail_auth.py status
python ai-employee/src/skills/linkedin_auth.py status
```

---

## Testing

### Test All Skills

```bash
cd D:\Hackathon-0\ai-employee

# Bronze Tier
python src/skills/process_email.py --help
python src/skills/update_dashboard.py --help
python src/skills/log_action.py --help
python src/skills/create_approval_request.py --help
python src/skills/move_to_done.py --help

# Silver Tier
python src/skills/gmail_auth.py status
python src/skills/gmail_watcher_skill.py --dry-run --once
python src/skills/whatsapp_watcher.py --test
python src/skills/send_email.py --help
python src/skills/create_plan.py --help
python src/skills/approval_workflow.py --status
python src/skills/scheduler.py --list
python src/skills/linkedin_post.py --help
python src/skills/linkedin_auth.py status
```

---

## Troubleshooting

### Common Issues

| Issue | Affected Skills | Solution |
|-------|----------------|----------|
| Module not found | All | `pip install -r requirements.txt` |
| Credentials error | gmail-auth, linkedin-auth | Re-run auth command |
| Browser doesn't launch | whatsapp-watcher, linkedin-browser-post | `playwright install chromium` |
| File not found | All | Check vault path in .env |
| Permission denied | All | Run as Administrator |

### Get Help

```bash
# Any skill's help
python ai-employee/src/skills/<skill_name>.py --help

# Check skill documentation
type .qwen\skills\<skill-name>\SKILL.md
```

---

## Version

**Skills Index Version:** 1.0.0
**Last Updated:** 2026-03-29
**Hackathon:** Personal AI Employee Hackathon 0

---

## Contributing

To add a new skill:

1. Create folder: `.qwen/skills/<skill-name>/`
2. Create SKILL.md using template
3. Implement Python skill: `ai-employee/src/skills/<skill_name>.py`
4. Add to this index
5. Test thoroughly

---

*Generated for Personal AI Employee Hackathon 0*
*Built with Qwen Code*
