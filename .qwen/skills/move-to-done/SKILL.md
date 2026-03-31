---
name: move-to-done
description: |
  Archive completed items to /Done/ folder. Moves files through the workflow
  lifecycle, adds completion metadata, and preserves filenames for tracking.
  Final step in any task workflow.
---

# Move to Done Skill

Archive completed tasks and add completion metadata.

## When to Use

- After successfully completing any action
- When task workflow is finished
- To archive approved and executed items
- For compliance and record-keeping

## CLI Usage

```bash
# Move file to Done
python ai-employee/src/skills/move_to_done.py \
  "D:\Hackathon-0\AI_Employee_Vault\Approved\EMAIL_123.md" \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Move with completion note
python ai-employee/src/skills/move_to_done.py \
  "D:\Hackathon-0\AI_Employee_Vault\Approved\EMAIL_123.md" \
  --vault "D:\Hackathon-0\AI_Employee_Vault" \
  --note "Email sent successfully to client"

# Dry run (preview only)
python ai-employee/src/skills/move_to_done.py \
  "D:\Hackathon-0\AI_Employee_Vault\Approved\EMAIL_123.md" \
  --vault "D:\Hackathon-0\AI_Employee_Vault" \
  --dry-run
```

## Single File Lifecycle

Files maintain the same name throughout their journey:

```
┌──────────────────┐
│  Needs_Action/   │  ← File created by watcher
│  EMAIL_123.md    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Plans/          │  ← Plan added by process_email
│  EMAIL_123.md    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Pending_Approval│  ← Approval request added
│  EMAIL_123.md    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Approved/       │  ← Human moved to Approved
│  EMAIL_123.md    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Done/           │  ← Final destination
│  EMAIL_123.md    │
└──────────────────┘
```

## File Content Transformation

### Before (In Approved/)

```markdown
---
type: email
from: client @example.com
subject: Invoice Request
status: approved
approved_by: human
---

## Email Content

Please send invoice for January.

## Action Plan

1. Generate invoice
2. Send via email
3. Log transaction
```

### After (In Done/)

```markdown
---
type: email
from: client @example.com
subject: Invoice Request
status: completed
completed_at: 2026-03-29T18:30:00Z
approved_by: human
execution_result: success
---

## Email Content

Please send invoice for January.

## Action Plan

1. Generate invoice ✅
2. Send via email ✅
3. Log transaction ✅

## Completion Notes

- Invoice generated: invoice_jan_2026.pdf
- Email sent: 2026-03-29 18:25
- Transaction logged: TXN-2026-001

---
*Completed automatically by AI Employee*
```

## Completion Metadata Added

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Changed to `completed` |
| `completed_at` | ISO8601 | Completion timestamp |
| `execution_result` | string | `success`, `partial`, `failed` |
| `completion_notes` | string | Summary of actions taken |

## Python API Usage

```python
from skills.move_to_done import move_to_done

# Basic move to done
result = move_to_done(
    file_path="D:\\Hackathon-0\\AI_Employee_Vault\\Approved\\EMAIL_123.md",
    vault_path="D:\\Hackathon-0\\AI_Employee_Vault"
)

# With completion note
result = move_to_done(
    file_path="D:\\Hackathon-0\\AI_Employee_Vault\\Approved\\EMAIL_123.md",
    vault_path="D:\\Hackathon-0\\AI_Employee_Vault",
    add_completion_note=True,
    completion_note="Email sent successfully. Invoice attached."
)

if result['success']:
    print(f"File archived to: {result['new_path']}")
else:
    print(f"Error: {result['error']}")
```

## Integration

### Called By

- **Orchestrator**: After action execution
- **Email Skills**: After sending emails
- **LinkedIn Skills**: After posting
- **Payment Skills**: After transactions
- **Approval Workflow**: After approved actions

### Calls

- **Log Action**: Records completion
- **Update Dashboard**: Updates done count

## Error Handling

| Error | Behavior | Recovery |
|-------|----------|----------|
| Source file not found | Returns error dict | Verify file path |
| Destination not writable | Logs error, keeps in place | Check permissions |
| File already in Done | Logs warning, skips | Check if already completed |
| Content update fails | Moves file, logs warning | Manual metadata update |

## Troubleshooting

### File not moving

**Check:** Source file exists and isn't open

**Fix:**
```bash
# Verify file exists
dir "D:\Hackathon-0\AI_Employee_Vault\Approved\EMAIL_123.md"

# Check if file is locked (Windows)
# Close any editors with the file open
```

### Done folder missing

**Check:** Folder structure exists

**Fix:**
```bash
mkdir "D:\Hackathon-0\AI_Employee_Vault\Done"
```

### Metadata not added

**Check:** File has valid Markdown format

**Fix:** Ensure file has frontmatter:
```markdown
---
type: email
---
```

## Related Skills

- [`create_approval_request`](../create-approval-request/SKILL.md) - Precedes completion
- [`approval_workflow`](../approval-workflow/SKILL.md) - Manages approval to completion
- [`log_action`](../log-action/SKILL.md) - Logs completion
- [`update_dashboard`](../update-dashboard/SKILL.md) - Shows completion stats

## Example: Complete Workflow

```python
from skills.process_email import process_email
from skills.approval_workflow import check_approvals
from skills.email_mcp_server import send_email
from skills.move_to_done import move_to_done
from skills.log_action import log_action

vault = "D:\\Hackathon-0\\AI_Employee_Vault"

# 1. Process email (creates plan, requests approval)
process_email(
    file_path=f"{vault}\\Needs_Action\\EMAIL_123.md",
    vault_path=vault
)
# File → Pending_Approval/

# 2. Human approves (moves to Approved/)
# Manual action by user

# 3. Execute approved action
approved_files = check_approvals(vault)
for file in approved_files:
    if file['action'] == 'email_send':
        # Send email
        send_email(file['details'])
        
        # Log success
        log_action(
            vault_path=vault,
            action_type="email_send",
            actor="orchestrator",
            target=file['details']['to'],
            result="success"
        )
        
        # Archive
        move_to_done(
            file_path=file['path'],
            vault_path=vault,
            completion_note="Email sent successfully"
        )
        # File → Done/
```

## Batch Archiving

```bash
# Move all approved files to Done
for %%f in ("D:\Hackathon-0\AI_Employee_Vault\Approved\*.md") do (
    python ai-employee/src/skills/move_to_done.py "%%f" --vault "D:\Hackathon-0\AI_Employee_Vault"
)
```

## Version

1.0.0 (Bronze Tier)
