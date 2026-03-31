---
name: gmail-watcher
description: |
  Monitor Gmail for new unread important emails and create action files
  in /Needs_Action folder. Polls Gmail API every 120 seconds, filters
  for important messages, and tracks processed emails to avoid duplicates.
---

# Gmail Watcher Skill

Continuous Gmail monitoring for new important emails.

## When to Use

- Continuous email monitoring (runs as daemon)
- Need to process emails as they arrive
- Filter important emails from noise
- Create actionable tasks from emails

## CLI Usage

```bash
# Run once (check for new emails)
python ai-employee/src/skills/gmail_watcher_skill.py \
  --once \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Continuous monitoring (daemon mode)
python ai-employee/src/skills/gmail_watcher_skill.py \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Dry run (test without creating files)
python ai-employee/src/skills/gmail_watcher_skill.py \
  --dry-run \
  --once \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Custom check interval
python ai-employee/src/skills/gmail_watcher_skill.py \
  --interval 60 \
  --vault "D:\Hackathon-0\AI_Employee_Vault"
```

## How It Works

```
┌─────────────────────┐
│  Start Watcher      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Authenticate with  │
│  Gmail API          │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Query: is:unread   │
│  in:inbox           │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Filter: Important  │
│  & Not System       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  For each new email:│
│  - Classify priority│
│  - Create action file│
│  - Track ID         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Wait 120 seconds   │
│  (repeat)           │
└─────────────────────┘
```

## Action File Format

Creates files in `/Needs_Action/`:

```markdown
---
type: email
from: client @example.com
subject: Invoice Request
received: 2026-03-29T10:30:00Z
priority: high
status: pending
message_id: 18e4f2a3b5c6d7e8
---

## Email Content

Hi,

Could you please send the invoice for January?

Thanks,
Client

## Suggested Actions

- [ ] Generate invoice
- [ ] Send via email
- [ ] Log transaction
```

## Priority Classification

### High Priority
- Keywords: `urgent`, `asap`, `emergency`, `invoice`, `payment`, `deadline`
- Senders: Known clients, VIP contacts

### Medium Priority
- Keywords: `meeting`, `schedule`, `question`, `help`, `review`
- Regular business correspondence

### Low Priority
- Everything else
- Newsletters, notifications

## Filtered Emails (Ignored)

The watcher automatically filters out:
- Bounce notifications (mailer-daemon@)
- Google notifications
- No-reply addresses
- System administrators
- Already processed messages

## Configuration

### Environment Variables

```bash
# In .env file
VAULT_PATH=D:/Hackathon-0/AI_Employee_Vault
GMAIL_CHECK_INTERVAL=120
GMAIL_QUERY=is:unread in:inbox
```

### Custom Keywords

Edit `gmail_watcher_skill.py`:
```python
HIGH_PRIORITY_KEYWORDS = [
    'urgent', 'asap', 'your-keyword-here'
]
```

## Integration

### Called By

- **Orchestrator**: Starts watcher on schedule
- **Scheduler**: Daily briefing trigger

### Calls

- [`gmail_auth`](../gmail-auth/SKILL.md) - Gmail API authentication
- [`log_action`](../log-action/SKILL.md) - Log detection events
- **File System**: Create action files

## Error Handling

| Error | Behavior | Recovery |
|-------|----------|----------|
| Auth failed | Logs error, retries | Re-authenticate |
| API quota exceeded | Waits, retries | Wait for quota reset |
| Network error | Logs, retries in 120s | Check connection |
| Invalid credentials | Stops, alerts user | Re-setup OAuth |

## Troubleshooting

### No emails being detected

**Check:** Gmail query is correct

**Fix:** Test query in Gmail:
```
is:unread in:inbox
```

### Authentication errors

**Check:** Token exists and is valid

**Fix:**
```bash
python ai-employee/src/skills/gmail_auth.py auth --force-refresh
```

### Duplicate emails being processed

**Check:** Cache file exists

**Fix:** Check cache at:
```
D:\Hackathon-0\AI_Employee_Vault\.cache\gmail_processed_ids.json
```

## Related Skills

- [`gmail_auth`](../gmail-auth/SKILL.md) - Authentication required
- [`process_email`](../process-email/SKILL.md) - Processes created files
- [`send_email`](../send-email/SKILL.md) - Send replies

## Example: Start Continuous Monitoring

```bash
# Start watcher in background (Windows)
start /B python ai-employee/src/skills/gmail_watcher_skill.py \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Or use Task Scheduler for auto-start
python ai-employee/src/skills/scheduler.py \
  --create gmail_watcher \
  --type watcher \
  --vault "D:\Hackathon-0\AI_Employee_Vault"
```

## Version

1.0.0 (Silver Tier)
