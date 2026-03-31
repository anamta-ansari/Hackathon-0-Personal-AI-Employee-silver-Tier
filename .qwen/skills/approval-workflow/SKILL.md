---
name: approval-workflow
description: |
  Manage human-in-the-loop approval workflow. Monitors Pending_Approval,
  Approved, and Rejected folders. Processes approved files, handles rejections,
  and checks for expired approvals. Central hub for approval management.
---

# Approval Workflow Skill

Human-in-the-loop approval management system.

## When to Use

- Monitor approval requests in real-time
- Process files moved to Approved folder
- Handle rejections and expirations
- Track approval audit trail

## CLI Usage

```bash
# Show approval status
python ai-employee/src/skills/approval_workflow.py \
  --status \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Show summary of all approvals
python ai-employee/src/skills/approval_workflow.py \
  --summary \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Process approved files
python ai-employee/src/skills/approval_workflow.py \
  --process \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Check for expired approvals
python ai-employee/src/skills/approval_workflow.py \
  --check-expired \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Continuous monitoring
python ai-employee/src/skills/approval_workflow.py \
  --watch \
  --vault "D:\Hackathon-0\AI_Employee_Vault"
```

## Workflow States

```
┌──────────────────┐
│ Pending_Approval │ ← Approval request created
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌──────────┐
│Approved│ │Rejected  │
└───┬────┘ └──────────┘
    │
    ▼
┌──────────────────┐
│ Execute Action   │
│ (via MCP/Skill)  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Done             │ ← Archive after execution
└──────────────────┘
```

## Folder Structure

```
/Vault/
├── Pending_Approval/
│   ├── EMAIL_123.md      ← Awaiting human review
│   ├── PAYMENT_456.md    ← Awaiting payment approval
│   └── LINKEDIN_789.md   ← Awaiting post approval
├── Approved/
│   └── (files ready for execution)
├── Rejected/
│   └── (files with rejection notes)
└── Done/
    └── (completed actions)
```

## Approval File Format

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

[Email body here]

---

## How to Approve

1. **Review** the action details above
2. **Move this file** to `/Approved/` to approve
3. **Move this file** to `/Rejected/` to reject

## To Approve
Move to: `D:\Hackathon-0\AI_Employee_Vault\Approved\`

## To Reject
Move to: `D:\Hackathon-0\AI_Employee_Vault\Rejected\`
```

## Action Handlers

Registered handlers for different action types:

| Action Type | Handler | Description |
|-------------|---------|-------------|
| `email_send` | `send_email` | Send via Gmail API |
| `payment` | `execute_payment` | Process payment |
| `linkedin_post` | `post_linkedin` | Publish to LinkedIn |
| `plan_execution` | `execute_plan` | Execute action plan |

## Expiration Handling

### Default Expiration Times

| Priority | Expiration |
|----------|------------|
| **High** | 4 hours |
| **Normal** | 24 hours |
| **Low** | 48 hours |

### Expired Approvals

- Status changed to `expired`
- File moved to `/Rejected/`
- Logged as `approval_expired`
- Optional notification to human

## Python API Usage

```python
from skills.approval_workflow import ApprovalWorkflowSkill

# Initialize
workflow = ApprovalWorkflowSkill(
    vault_path="D:\\Hackathon-0\\AI_Employee_Vault"
)

# Get pending approvals
pending = workflow.get_pending_approvals()
print(f"Pending: {len(pending)} approvals")

# Process approved files
results = workflow.process_approved()
for result in results:
    print(f"Processed: {result['file']} - {result['status']}")

# Check for expired
expired = workflow.check_expired()
for file in expired:
    print(f"Expired: {file}")
```

## Integration

### Called By

- **Orchestrator**: Continuous approval monitoring
- **Scheduler**: Periodic expiration checks

### Calls

- [`send_email`](../send-email/SKILL.md) - Execute approved emails
- [`linkedin_post`](../linkedin-post/SKILL.md) - Execute approved posts
- [`move_to_done`](../move-to-done/SKILL.md) - Archive after execution
- [`log_action`](../log-action/SKILL.md) - Log approval events

## Error Handling

| Error | Behavior | Recovery |
|-------|----------|----------|
| No handler registered | Logs warning, skips | Register handler |
| Execution fails | Logs error, moves to Rejected | Review error |
| File move fails | Logs error, keeps in place | Check permissions |
| Expiration check fails | Logs warning, continues | Next check will retry |

## Troubleshooting

### Approved files not being processed

**Check:** Orchestrator is running

**Fix:**
```bash
python ai-employee/src/orchestration/orchestrator.py
```

### Handler not found for action type

**Check:** Handler is registered

**Fix:**
```python
workflow.register_action_handler('email_send', send_email_handler)
```

### Expiration not working

**Check:** Expiration check is enabled

**Fix:**
```python
workflow = ApprovalWorkflowSkill(
    vault_path=vault,
    expiration_check_enabled=True
)
```

## Related Skills

- [`create_approval_request`](../create-approval-request/SKILL.md) - Create approval files
- [`send_email`](../send-email/SKILL.md) - Execute approved emails
- [`move_to_done`](../move-to-done/SKILL.md) - Archive completed

## Example: Human Approval Process

```bash
# 1. AI creates approval request
# File: /Pending_Approval/EMAIL_123.md

# 2. Human reviews file
type "D:\Hackathon-0\AI_Employee_Vault\Pending_Approval\EMAIL_123.md"

# 3. Human approves (moves file)
move "D:\Hackathon-0\AI_Employee_Vault\Pending_Approval\EMAIL_123.md" \
     "D:\Hackathon-0\AI_Employee_Vault\Approved\"

# 4. Orchestrator detects and processes
python ai-employee/src/skills/approval_workflow.py \
  --process \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# 5. Email sent, file moved to Done
```

## Version

1.0.0 (Silver Tier)
