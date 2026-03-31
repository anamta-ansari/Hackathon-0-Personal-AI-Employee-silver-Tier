---
name: whatsapp-watcher
description: |
  Monitor WhatsApp Web for messages containing keywords (urgent, invoice, payment).
  Uses Playwright for browser automation. Creates action files in /Needs_Action
  for messages requiring attention.
---

# WhatsApp Watcher Skill

WhatsApp Web monitoring for keyword-containing messages.

## When to Use

- Monitor WhatsApp for business messages
- Filter important messages from chat noise
- Create actionable tasks from WhatsApp
- Track client communications

## Prerequisites

```bash
# Install Playwright
pip install playwright
playwright install chromium
```

## CLI Usage

```bash
# Test connection (visible browser)
python ai-employee/src/skills/whatsapp_watcher.py \
  --test \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Run once (check for new messages)
python ai-employee/src/skills/whatsapp_watcher.py \
  --once \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Continuous monitoring
python ai-employee/src/skills/whatsapp_watcher.py \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Visible browser (debug mode)
python ai-employee/src/skills/whatsapp_watcher.py \
  --visible \
  --once \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Dry run (test without creating files)
python ai-employee/src/skills/whatsapp_watcher.py \
  --dry-run \
  --once
```

## How It Works

```
┌─────────────────────┐
│  Start WhatsApp     │
│  Watcher            │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Launch Browser     │
│  (WhatsApp Web)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Load Session       │
│  (if exists)        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Wait for QR Scan   │
│  (first time only)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Scan Chat List     │
│  for Unread         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Filter by Keywords │
│  (urgent, invoice)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Create Action File │
│  in Needs_Action    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Wait 30 seconds    │
│  (repeat)           │
└─────────────────────┘
```

## Keyword Filters

### Default Keywords

| Category | Keywords |
|----------|----------|
| **Urgency** | urgent, asap, emergency, immediate |
| **Financial** | invoice, payment, bill, receipt |
| **Support** | help, support, issue, problem |
| **Business** | deadline, meeting, call, important |

### Custom Keywords

Edit `whatsapp_watcher.py`:
```python
DEFAULT_KEYWORDS = [
    'urgent', 'asap', 'your-keyword-here'
]
```

## Action File Format

Creates files in `/Needs_Action/`:

```markdown
---
type: whatsapp_message
from: +1234567890
chat_name: Client ABC
received: 2026-03-29T10:30:00Z
priority: high
matched_keywords: ["urgent", "invoice"]
status: pending
---

## WhatsApp Message

**From:** Client ABC
**Time:** 10:30 AM

> Hi, I need the invoice urgently. Please send ASAP.

## Suggested Actions

- [ ] Generate invoice
- [ ] Send via email/WhatsApp
- [ ] Follow up with client

## Reply via WhatsApp

- [ ] Acknowledge receipt
- [ ] Provide timeline
```

## Session Management

### Session Location
```
D:\Hackathon-0\AI_Employee_Vault\.cache\whatsapp_session\
```

### First Run
1. Browser launches (visible)
2. QR code displayed
3. Scan with WhatsApp phone
4. Session saved

### Subsequent Runs
- Session loaded automatically
- No QR scan needed
- Faster startup

## Error Handling

| Error | Behavior | Recovery |
|-------|----------|----------|
| Playwright not installed | Logs error, exits | Run `playwright install` |
| QR scan timeout | Waits for manual scan | Scan QR code |
| Session expired | Requests re-scan | Scan QR again |
| WhatsApp Web changed | Selector mismatch | Update selectors in code |

## Troubleshooting

### Browser doesn't launch

**Check:** Playwright installed

**Fix:**
```bash
pip install playwright
playwright install chromium
```

### QR code not showing

**Check:** WhatsApp Web accessible

**Fix:**
```bash
# Run with visible browser to see issue
python ai-employee/src/skills/whatsapp_watcher.py --visible --test
```

### Session not saving

**Check:** Session path is writable

**Fix:**
```bash
# Check permissions
dir "D:\Hackathon-0\AI_Employee_Vault\.cache"
```

### No messages detected

**Check:** Unread messages exist in WhatsApp

**Fix:** Send test message to yourself

## Security Notes

⚠️ **Important:**
- Session gives access to your WhatsApp
- Never commit session files to version control
- Use dedicated business WhatsApp account
- Review WhatsApp Web permissions regularly

## Integration

### Called By

- **Orchestrator**: Starts watcher on schedule
- **Scheduler**: Continuous monitoring

### Calls

- [`log_action`](../log-action/SKILL.md) - Log detection events
- **File System**: Create action files

## Related Skills

- [`gmail_watcher`](../gmail-watcher/SKILL.md) - Email monitoring
- [`process_email`](../process-email/SKILL.md) - Similar processing flow
- [`linkedin_post`](../linkedin-post/SKILL.md) - Communication channel

## Example: Start Monitoring

```bash
# 1. First time setup (visible browser for QR scan)
python ai-employee/src/skills/whatsapp_watcher.py \
  --visible \
  --test

# 2. Scan QR code with phone

# 3. Start continuous monitoring
python ai-employee/src/skills/whatsapp_watcher.py \
  --vault "D:\Hackathon-0\AI_Employee_Vault"
```

## Running as Background Service (Windows)

```batch
# Create batch file: start_whatsapp_watcher.bat
@echo off
cd /d D:\Hackathon-0\ai-employee
start /B python src\skills\whatsapp_watcher.py --vault "D:\Hackathon-0\AI_Employee_Vault"
```

## Version

1.0.0 (Silver Tier)
