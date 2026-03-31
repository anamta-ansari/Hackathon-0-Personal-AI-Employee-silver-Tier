---
name: log-action
description: |
  Write audit log entries for all AI Employee actions. Creates timestamped,
  structured JSON logs for compliance, debugging, and activity tracking.
  Every significant action should be logged.
---

# Log Action Skill

Comprehensive audit logging for all AI Employee actions.

## When to Use

- **Before** executing any action
- **After** completing any action
- When action requires audit trail
- For compliance and debugging

## CLI Usage

```bash
# Log a simple action
python ai-employee/src/skills/log_action.py \
  "D:\Hackathon-0\AI_Employee_Vault" \
  "email_send" \
  "qwen_code" \
  "client @example.com" \
  --parameters "{\"subject\": \"Invoice #123\"}" \
  --result "success"

# Log with approval status
python ai-employee/src/skills/log_action.py \
  "D:\Hackathon-0\AI_Employee_Vault" \
  "payment_execute" \
  "orchestrator" \
  "vendor_abc" \
  --parameters "{\"amount\": 500.00}" \
  --approval-status "approved" \
  --approved-by "human" \
  --result "success"
```

## Log Entry Schema

```json
{
  "timestamp": "2026-03-29T10:30:00Z",
  "action_type": "email_send",
  "actor": "qwen_code",
  "target": "client @example.com",
  "parameters": {
    "subject": "Invoice #123",
    "has_attachment": true
  },
  "approval_status": "approved",
  "approved_by": "human",
  "result": "success",
  "message": "Email sent successfully"
}
```

## Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | ISO8601 | Yes | Auto-generated |
| `action_type` | string | Yes | Type of action (e.g., `email_send`) |
| `actor` | string | Yes | Who/what performed action |
| `target` | string | Yes | Target of action |
| `parameters` | object | No | Action-specific details |
| `approval_status` | string | No | `not_required`, `pending`, `approved`, `rejected` |
| `approved_by` | string | No | Who approved (if applicable) |
| `result` | string | Yes | `success`, `failure`, `pending` |
| `message` | string | No | Human-readable note |

## Actor Values

| Actor | Description |
|-------|-------------|
| `qwen_code` | Qwen Code reasoning engine |
| `orchestrator` | Main orchestration script |
| `gmail_watcher` | Gmail monitoring script |
| `filesystem_watcher` | File system monitor |
| `whatsapp_watcher` | WhatsApp Web monitor |
| `human` | Human user action |

## Action Types

### Communication
- `email_send` - Email sent
- `email_draft` - Draft created
- `whatsapp_send` - WhatsApp message sent
- `linkedin_post` - LinkedIn post published

### File Operations
- `file_move` - File moved between folders
- `file_create` - New file created
- `file_update` - File content updated
- `file_delete` - File deleted

### Approval Workflow
- `approval_request` - Approval requested
- `approval_granted` - Approval granted
- `approval_rejected` - Approval rejected
- `approval_expired` - Approval timeout

### System
- `dashboard_update` - Dashboard refreshed
- `plan_create` - Action plan generated
- `task_complete` - Task finished
- `error_occurred` - Error encountered

## Log File Location

Logs stored in:
```
/Vault/Logs/YYYY-MM-DD.json
```

Example:
```
/Vault/Logs/2026-03-29.json
```

## Log File Format

Daily log files contain array of entries:
```json
[
  {
    "timestamp": "2026-03-29T10:30:00Z",
    "action_type": "email_send",
    ...
  },
  {
    "timestamp": "2026-03-29T10:35:00Z",
    "action_type": "dashboard_update",
    ...
  }
]
```

## Python API Usage

```python
from skills.log_action import log_action, LogEntry

# Simple log
log_action(
    vault_path="D:\\Hackathon-0\\AI_Employee_Vault",
    action_type="email_send",
    actor="qwen_code",
    target="client @example.com",
    parameters={"subject": "Invoice #123"},
    result="success"
)

# Using LogEntry class
entry = LogEntry(
    timestamp=datetime.now().isoformat(),
    action_type="payment_execute",
    actor="orchestrator",
    target="vendor_abc",
    parameters={"amount": 500.00},
    approval_status="approved",
    approved_by="human",
    result="success"
)
log_action(vault_path, entry)
```

## Integration

### Called By

- **All Skills**: Every skill logs its actions
- **Orchestrator**: System events
- **Watchers**: Detection events
- **MCP Servers**: External API calls

### Related Skills

- [`process_email`](../process-email/SKILL.md) - Logs email processing
- [`update_dashboard`](../update-dashboard/SKILL.md) - Logs dashboard updates
- [`create_approval_request`](../create-approval-request/SKILL.md) - Logs approval requests
- [`move_to_done`](../move-to-done/SKILL.md) - Logs file moves

## Error Handling

| Error | Behavior | Recovery |
|-------|----------|----------|
| Log directory missing | Creates `/Logs/` folder | Auto-recovery |
| JSON write fails | Logs to console, retries | Check disk space |
| Invalid parameters | Logs error entry | Fix parameter format |
| Permission denied | Logs to stderr | Check file permissions |

## Troubleshooting

### Logs not appearing

**Check:** `/Logs/` folder exists and is writable

**Fix:**
```bash
# Create logs folder manually
mkdir "D:\Hackathon-0\AI_Employee_Vault\Logs"
```

### Log file corrupted

**Check:** JSON format valid

**Fix:**
```bash
# Backup and recreate
copy 2026-03-29.json 2026-03-29.json.bak
echo [] > 2026-03-29.json
```

### Missing log entries

**Check:** Skills calling `log_action`

**Fix:** Add logging to skill:
```python
from skills.log_action import log_action

def my_skill():
    # Do work
    log_action(vault, "my_action", "skill_name", "target", result="success")
```

## Best Practices

1. **Log before and after** important actions
2. **Include relevant parameters** for debugging
3. **Use consistent action_type** values
4. **Set approval_status** for sensitive actions
5. **Add descriptive messages** for failures

## Example: Complete Logging Flow

```python
from skills.log_action import log_action

def send_approved_email(email_data):
    vault = "D:\\Hackathon-0\\AI_Employee_Vault"
    
    # Log start
    log_action(
        vault_path=vault,
        action_type="email_send",
        actor="email_skill",
        target=email_data['to'],
        parameters=email_data,
        approval_status="approved",
        result="pending"
    )
    
    try:
        # Send email
        result = gmail_api.send(email_data)
        
        # Log success
        log_action(
            vault_path=vault,
            action_type="email_send",
            actor="email_skill",
            target=email_data['to'],
            parameters={"message_id": result.id},
            result="success"
        )
    except Exception as e:
        # Log failure
        log_action(
            vault_path=vault,
            action_type="email_send",
            actor="email_skill",
            target=email_data['to'],
            parameters={"error": str(e)},
            result="failure"
        )
```

## Version

1.0.0 (Bronze Tier)
