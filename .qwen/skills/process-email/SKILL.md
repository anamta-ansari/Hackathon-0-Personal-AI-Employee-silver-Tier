---
name: process-email
description: |
  Process email action files from /Needs_Action folder and create action plans.
  Analyzes email content, determines required actions, and moves files through
  the approval workflow. Supports single-file lifecycle tracking.
---

# Process Email Skill

Process email action files and generate action plans with approval workflows.

## When to Use

- New email files appear in `/Needs_Action/` folder
- Need to analyze email content and determine actions
- Email responses require human approval before sending
- Tracking email through completion lifecycle

## Single File Lifecycle

Files maintain the same name as they progress:

```
Needs_Action/EMAIL_123.md
    ↓ (process)
Plans/EMAIL_123.md
    ↓ (approval needed)
Pending_Approval/EMAIL_123.md
    ↓ (approved)
Approved/EMAIL_123.md
    ↓ (executed)
Done/EMAIL_123.md
```

## CLI Usage

```bash
# Process a specific email file
python ai-employee/src/skills/process_email.py \
  "D:\Hackathon-0\AI_Employee_Vault\Needs_Action\EMAIL_123.md" \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Process with dry run (no file moves)
python ai-employee/src/skills/process_email.py \
  "D:\Hackathon-0\AI_Employee_Vault\Needs_Action\EMAIL_123.md" \
  --vault "D:\Hackathon-0\AI_Employee_Vault" \
  --dry-run
```

## Input Format

Email files in `/Needs_Action/` should have this frontmatter:

```markdown
---
type: email
from: client @example.com
subject: Project Update Request
received: 2026-03-29T10:30:00Z
priority: high
status: pending
---

## Email Content

[Email body here]
```

## Output Format

After processing, the file is updated with:

```markdown
---
type: email
from: client @example.com
subject: Project Update Request
received: 2026-03-29T10:30:00Z
priority: high
status: planned
plan_created: 2026-03-29T10:35:00Z
requires_approval: true
---

## Email Content

[Original email body]

## Action Plan

1. Read and understand email content
2. Draft response to client
3. Create approval request for response
4. Wait for human approval
5. Send response via email MCP

## Approval Required

Action: send_email
To: client @example.com
Subject: Re: Project Update Request

Move this file to /Approved to proceed.
```

## Approval Workflow

### Actions Requiring Approval

| Action Type | Auto-Approve | Require Approval |
|-------------|--------------|------------------|
| Reply to known contact | No | Always |
| Reply to new contact | No | Always |
| Forward email | No | Always |
| Archive only | Yes | Never |

### Approval File Location

Files requiring approval are moved to:
`/Pending_Approval/EMAIL_<id>.md`

### Human Approval Process

1. Review file in `/Pending_Approval/`
2. Verify email response content
3. Move file to `/Approved/` to approve
4. Move file to `/Rejected/` to reject

## Integration

This skill integrates with:

- **Gmail Watcher**: Creates initial email files
- **Plan Generation**: Creates structured action plans
- **Approval Workflow**: Manages approval requests
- **Email MCP Server**: Sends approved emails
- **Move to Done**: Archives completed emails

## Error Handling

| Error | Behavior | Recovery |
|-------|----------|----------|
| File not found | Returns error dict | Verify file path |
| Invalid frontmatter | Logs warning, uses defaults | Fix frontmatter format |
| Gmail API error | Logs error, retries | Check credentials |
| Move fails | Logs error, keeps in place | Check file permissions |

## Logging

All operations logged to:
- Console: INFO level
- File: `/Logs/YYYY-MM-DD.json`

Log entry example:
```json
{
  "timestamp": "2026-03-29T10:35:00Z",
  "action_type": "email_process",
  "actor": "process_email_skill",
  "target": "EMAIL_123.md",
  "parameters": {"from": "client @example.com"},
  "result": "success"
}
```

## Troubleshooting

### File not moving to Plans/

**Check:** File has valid frontmatter with `type: email`

**Fix:** Add or fix frontmatter:
```markdown
---
type: email
from: sender @example.com
---
```

### Approval not being requested

**Check:** Email requires action (not just archive)

**Fix:** Ensure email content indicates response needed

### Skill not finding email file

**Check:** File path is absolute and file exists

**Fix:** Use full path: `D:\Hackathon-0\AI_Employee_Vault\Needs_Action\EMAIL_123.md`

## Related Skills

- [`create_plan`](../create-plan/SKILL.md) - Generate detailed action plans
- [`create_approval_request`](../create-approval-request/SKILL.md) - Create approval files
- [`send_email`](../send-email/SKILL.md) - Send emails via Gmail API
- [`move_to_done`](../move-to-done/SKILL.md) - Archive completed items

## Example Workflow

```bash
# 1. Gmail Watcher creates email file
# File: /Needs_Action/EMAIL_abc123.md

# 2. Process the email
python ai-employee/src/skills/process_email.py \
  "D:\Hackathon-0\AI_Employee_Vault\Needs_Action\EMAIL_abc123.md" \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# 3. File moved to /Pending_Approval/ (if approval needed)

# 4. Human reviews and moves to /Approved/

# 5. Orchestrator executes email send

# 6. File moved to /Done/
```

## Version

1.0.0 (Bronze Tier)
