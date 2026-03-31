---
name: send-email
description: |
  Send emails via Gmail API with approval workflow support. Handles email
  composition, attachments, and logging. Integrates with gmail_auth for
  authentication and logs all sent emails for audit trail.
---

# Send Email Skill

Send emails via Gmail API with full audit logging.

## When to Use

- Send approved email responses
- Send invoices to clients
- Send business communications
- Forward important emails

## CLI Usage

```bash
# Send simple email
python ai-employee/src/skills/send_email.py \
  --to "client @example.com" \
  --subject "Invoice #123" \
  --body "Please find attached invoice..." \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Send with attachment
python ai-employee/src/skills/send_email.py \
  --to "client @example.com" \
  --subject "Invoice #123" \
  --body "Please find attached..." \
  --attachment "D:\Invoices\invoice_123.pdf" \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Dry run (test without sending)
python ai-employee/src/skills/send_email.py \
  --to "client @example.com" \
  --subject "Test" \
  --body "Test email" \
  --dry-run \
  --vault "D:\Hackathon-0\AI_Employee_Vault"
```

## Email Flow

```
┌─────────────────────┐
│  Approval File in   │
│  /Approved/         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Parse Approval     │
│  File for Details   │
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
│  Compose Email      │
│  (MIME format)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Attach Files       │
│  (if any)           │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Send via Gmail API │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Log to actions.json│
│  Move file to Done  │
└─────────────────────┘
```

## Input: Approval File Format

Reads from `/Approved/`:

```markdown
---
type: approval_request
action: send_email
to: client @example.com
subject: Invoice #123
created: 2026-03-29T10:30:00Z
status: approved
approved_by: human
---

## Email Body

Dear Client,

Please find attached invoice #123 for January 2026.

Best regards,
Your Company

## Attachments

- invoice_123.pdf
```

## Features

### Supported Content Types

- **Plain text** emails
- **HTML** emails
- **Attachments** (PDF, DOC, images, etc.)
- **CC/BCC** recipients

### Email Templates

```python
# Invoice email template
INVOICE_TEMPLATE = """
Dear {client_name},

Please find attached invoice #{invoice_number} for {amount}.

Payment is due within {days} days.

Thank you for your business!

Best regards,
{company_name}
"""

# Response template
RESPONSE_TEMPLATE = """
Dear {sender},

Thank you for your email regarding {subject}.

{response_body}

Best regards,
{company_name}
"""
```

## Python API Usage

```python
from skills.send_email import SendEmailSkill

# Initialize
email_skill = SendEmailSkill(
    vault_path="D:\\Hackathon-0\\AI_Employee_Vault",
    credentials_path="D:\\Hackathon-0\\credentials.json"
)

# Send email
result = email_skill.send_email(
    to="client @example.com",
    subject="Invoice #123",
    body="Please find attached invoice...",
    attachments=["D:\\Invoices\\invoice_123.pdf"]
)

if result['success']:
    print(f"Email sent: {result['message_id']}")
else:
    print(f"Error: {result['error']}")
```

## Integration

### Called By

- [`approval_workflow`](../approval-workflow/SKILL.md) - Execute approved emails
- [`process_email`](../process-email/SKILL.md) - Send email responses
- **Orchestrator** - Process approved files

### Calls

- [`gmail_auth`](../gmail-auth/SKILL.md) - Gmail API authentication
- [`log_action`](../log-action/SKILL.md) - Log sent emails
- [`move_to_done`](../move-to-done/SKILL.md) - Archive after sending

## Error Handling

| Error | Behavior | Recovery |
|-------|----------|----------|
| Auth failed | Logs error, returns failure | Re-authenticate |
| Invalid recipient | Returns error | Fix email address |
| Attachment missing | Logs warning, sends without | Verify file path |
| API quota exceeded | Waits, retries | Wait for reset |
| Network error | Logs, retries | Check connection |

## Troubleshooting

### Authentication error

**Check:** Token is valid

**Fix:**
```bash
python ai-employee/src/skills/gmail_auth.py auth --force-refresh
```

### Email not sending

**Check:** Gmail API enabled

**Fix:**
1. Go to Google Cloud Console
2. Enable Gmail API
3. Verify OAuth scopes

### Attachment fails

**Check:** File exists and path is correct

**Fix:**
```bash
dir "D:\Invoices\invoice_123.pdf"
```

## Security Notes

⚠️ **Important:**
- All sent emails logged to `/Logs/actions.json`
- Approval required for all external emails
- Never send to unverified recipients
- Review email content before approval

## Related Skills

- [`gmail_auth`](../gmail-auth/SKILL.md) - Authentication required
- [`email_mcp_server`](../email-mcp-server/SKILL.md) - Alternative email interface
- [`create_approval_request`](../create-approval-request/SKILL.md) - Pre-send approval

## Example: Complete Email Flow

```bash
# 1. Email received and processed
# File created: /Needs_Action/EMAIL_abc123.md

# 2. Plan created with approval request
# File moved to: /Pending_Approval/EMAIL_abc123.md

# 3. Human reviews and approves
# File moved to: /Approved/EMAIL_abc123.md

# 4. Orchestrator processes approved file
python ai-employee/src/skills/send_email.py \
  --to "client @example.com" \
  --subject "Re: Invoice Request" \
  --body "Please find attached..." \
  --attachment "invoice.pdf" \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# 5. Email sent and logged
# File moved to: /Done/EMAIL_abc123.md
```

## Version

1.0.0 (Silver Tier)
