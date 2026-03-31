---
name: create-approval-request
description: |
  Generate approval request files for actions requiring human oversight.
  Creates structured Markdown files in /Pending_Approval/ with clear
  action details, expiration, and approval instructions.
---

# Create Approval Request Skill

Human-in-the-loop approval workflow for sensitive actions.

## When to Use

- Before sending emails to external contacts
- Before making payments or financial transactions
- Before posting to social media
- Before deleting files or data
- Any action marked as requiring approval

## CLI Usage

```bash
# Create approval request for email send
python ai-employee/src/skills/create_approval_request.py \
  --file "D:\Hackathon-0\AI_Employee_Vault\Plans\EMAIL_123.md" \
  --vault "D:\Hackathon-0\AI_Employee_Vault" \
  --action-type "email_send" \
  --action-details "{\"to\": \"client @example.com\", \"subject\": \"Invoice #123\"}"

# Create approval for payment
python ai-employee/src/skills/create_approval_request.py \
  --vault "D:\Hackathon-0\AI_Employee_Vault" \
  --action-type "payment" \
  --action-details "{\"amount\": 500.00, \"recipient\": \"Vendor ABC\", \"reason\": \"Invoice #456\"}"
```

## Approval File Format

Location: `/Pending_Approval/<ACTION>_<description>_<timestamp>.md`

```markdown
---
type: approval_request
action: email_send
to: client @example.com
subject: Invoice #123
created: 2026-03-29T10:30:00Z
expires: 2026-03-30T10:30:00Z
status: pending
priority: normal
---

# Approval Request: Send Email

## Action Details

| Field | Value |
|-------|-------|
| **Action** | Send Email |
| **To** | client @example.com |
| **Subject** | Invoice #123 |
| **Created** | 2026-03-29 10:30 |
| **Expires** | 2026-03-30 10:30 |

## Email Content

```
Dear Client,

Please find attached invoice #123 for services rendered...
```

## Attachments

- invoice_123.pdf

---

## How to Approve

1. **Review** the action details above
2. **Move this file** to `/Approved/` to approve
3. **Move this file** to `/Rejected/` to reject
4. **Let expire** for automatic rejection

## To Approve
Move this file to: `D:\Hackathon-0\AI_Employee_Vault\Approved\`

## To Reject
Move this file to: `D:\Hackathon-0\AI_Employee_Vault\Rejected\`
```

## Approval Actions Requiring Human Review

| Action Type | Auto-Approve Threshold | Always Require Approval |
|-------------|----------------------|------------------------|
| `email_send` | Never | All external emails |
| `payment` | Never | All payments |
| `linkedin_post` | Never | All posts |
| `whatsapp_send` | Known contacts < $100 | New contacts, > $100 |
| `file_delete` | Temporary files | Permanent deletions |
| `api_call` | Read-only | Write operations |

## Expiration Handling

### Default Expiration
- **Normal priority**: 24 hours
- **High priority**: 4 hours
- **Low priority**: 48 hours

### Expired Approvals
- Status changed to `expired`
- File moved to `/Rejected/`
- Logged as `approval_expired`

## Human Approval Process

### To Approve

```bash
# Move file to Approved folder
move "D:\Hackathon-0\AI_Employee_Vault\Pending_Approval\EMAIL_123.md" \
     "D:\Hackathon-0\AI_Employee_Vault\Approved\"
```

### To Reject

```bash
# Move file to Rejected folder
move "D:\Hackathon-0\AI_Employee_Vault\Pending_Approval\EMAIL_123.md" \
     "D:\Hackathon-0\AI_Employee_Vault\Rejected\"
```

### Add Rejection Note (Optional)

Edit file before moving to Rejected:
```markdown
## Rejection Reason
Incorrect amount. Should be $450, not $500.
```

## Python API Usage

```python
from skills.create_approval_request import create_approval_request

# Create approval request
result = create_approval_request(
    vault_path="D:\\Hackathon-0\\AI_Employee_Vault",
    action_type="email_send",
    action_details={
        "to": "client @example.com",
        "subject": "Invoice #123",
        "body": "Please find attached..."
    },
    file_path="D:\\Hackathon-0\\AI_Employee_Vault\\Plans\\EMAIL_123.md",
    priority="normal",
    expiration_hours=24
)

print(f"Approval file created: {result['file_path']}")
```

## Integration

### Called By

- **Process Email**: When email response needs approval
- **LinkedIn Post**: Before publishing posts
- **Payment Skills**: Before executing payments
- **Send Email**: For external email sends

### Calls

- **Log Action**: Records approval request creation
- **File System**: Moves file to Pending_Approval
- **Update Dashboard**: Updates pending approvals count

## Approval Workflow States

```
┌─────────────────┐
│  Plan Created   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Approval Needed?│──No──▶ Execute
└────────┬────────┘
         │
        Yes
         │
         ▼
┌─────────────────┐
│ Pending_Approval│
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐ ┌─────────┐
│Approved│ │Rejected │
└───┬───┘ └─────────┘
    │
    ▼
┌─────────┐
│ Execute │
└─────────┘
```

## Error Handling

| Error | Behavior | Recovery |
|-------|----------|----------|
| File not found | Returns error dict | Verify file path |
| Invalid action type | Logs warning, uses generic template | Use valid action type |
| Cannot create file | Logs error, returns failure | Check permissions |
| Cannot move file | Logs error, keeps in place | Check if file open |

## Troubleshooting

### Approval file not created

**Check:** Action type is registered

**Fix:** Add action type to `create_approval_request.py`

### File not moving to Pending_Approval

**Check:** Destination folder exists

**Fix:**
```bash
mkdir "D:\Hackathon-0\AI_Employee_Vault\Pending_Approval"
```

### Approval expired too quickly

**Check:** Expiration hours setting

**Fix:** Adjust in skill call:
```python
create_approval_request(..., expiration_hours=48)
```

## Related Skills

- [`process_email`](../process-email/SKILL.md) - Triggers approval for emails
- [`approval_workflow`](../approval-workflow/SKILL.md) - Manages approval processing
- [`move_to_done`](../move-to-done/SKILL.md) - Archives after approval
- [`log_action`](../log-action/SKILL.md) - Logs approval events

## Example: Email Approval Flow

```python
# 1. Email received and processed
# File: /Needs_Action/EMAIL_abc123.md

# 2. Process email determines approval needed
from skills.process_email import process_email
result = process_email(
    file_path="D:\\Hackathon-0\\AI_Employee_Vault\\Needs_Action\\EMAIL_abc123.md",
    vault_path="D:\\Hackathon-0\\AI_Employee_Vault"
)

# 3. Approval request created
# File moved to: /Pending_Approval/EMAIL_abc123.md

# 4. Human reviews and approves
# File moved to: /Approved/EMAIL_abc123.md

# 5. Orchestrator executes action
# Email sent via MCP

# 6. File archived
# File moved to: /Done/EMAIL_abc123.md
```

## Version

1.0.0 (Bronze Tier)
