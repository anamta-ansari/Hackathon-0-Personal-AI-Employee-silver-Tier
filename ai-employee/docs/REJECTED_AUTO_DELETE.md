# Rejected Approval Auto-Delete Feature

## Overview

The orchestrator now automatically processes and deletes rejected approval files after a configurable retention period. This feature ensures compliance while preventing the Rejected folder from accumulating unlimited files.

## How It Works

### Processing Cycle

1. **Detection**: Every 5 orchestration cycles (~2.5 minutes with default 30s interval), the orchestrator scans the `/Rejected/` folder.

2. **Age Check**: For each rejected file, the system calculates days since rejection based on file modification time.

3. **Logging**: All rejected files are logged with their age and retention status.

4. **Archive**: Files older than the retention period are archived to `/Rejected/_ARCHIVED/` with metadata.

5. **Deletion**: After archiving, the original file is permanently deleted.

### Retention Policy

| Setting | Default | Description |
|---------|---------|-------------|
| `REJECTED_AUTO_DELETE_DAYS` | 7 | Days to keep rejected files before deletion |
| `ENABLE_REJECTED_AUTO_DELETE` | true | Enable/disable auto-delete functionality |

## File Lifecycle

```
┌─────────────────┐
│  Pending_       │
│  Approval/      │
└────────┬────────┘
         │ User rejects
         ▼
┌─────────────────┐
│  Rejected/      │ ◄── Kept for 7 days
│  (file.md)      │     (logged each cycle)
└────────┬────────┘
         │ After 7 days
         ▼
┌─────────────────┐
│  Rejected/      │
│  _ARCHIVED/     │ ◄── Archived with metadata
│  (ARCHIVED_     │     (permanent audit record)
│   file_*.md)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  DELETED        │
│  (original file │
│   removed)      │
└─────────────────┘
```

## Archive Metadata

When a file is archived, the following metadata is added to its frontmatter:

```yaml
original_filename: APPROVAL_19c85cf545f109e9_20260305_212520.md
archived_date: 2026-03-12T10:30:00
deletion_reason: Auto-delete after retention period
retention_days: 7
original_rejection_date: 2026-03-05T21:25:20
```

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Enable/disable auto-delete
ENABLE_REJECTED_AUTO_DELETE=true

# Days to keep rejected files (default: 7)
REJECTED_AUTO_DELETE_DAYS=7
```

### Programmatic Configuration

```python
from src.orchestration.orchestrator import Orchestrator, OrchestratorConfig

config = OrchestratorConfig(
    vault_path="D:/Hackathon-0/AI_Employee_Vault",
    rejected_auto_delete_days=14,  # Keep for 2 weeks
    enable_rejected_auto_delete=True
)

orchestrator = Orchestrator(config)
```

## Logging

All rejected file operations are logged to `/Logs/actions.json`:

### Rejection Processed (every cycle)
```json
{
  "timestamp": "2026-03-06T08:00:00",
  "action_type": "rejection_processed",
  "actor": "orchestrator",
  "target": "APPROVAL_19c85cf545f109e9_20260305_212520.md",
  "parameters": {
    "days_since_rejection": 1,
    "retention_days": 7
  },
  "approval_status": "rejected",
  "result": "success"
}
```

### File Deleted (after retention period)
```json
{
  "timestamp": "2026-03-12T10:30:00",
  "action_type": "rejected_file_deleted",
  "actor": "orchestrator",
  "target": "APPROVAL_19c85cf545f109e9_20260305_212520.md",
  "parameters": {
    "days_since_rejection": 7,
    "retention_days": 7,
    "reason": "Auto-delete after 7 days retention"
  },
  "approval_status": "rejected",
  "result": "success"
}
```

## Disabling Auto-Delete

To keep rejected files indefinitely:

```bash
ENABLE_REJECTED_AUTO_DELETE=false
```

Files will still be processed and logged, but not deleted.

## Manual Operations

### Manually Delete Old Rejected Files

```python
from pathlib import Path
from datetime import datetime, timedelta

vault_path = Path("D:/Hackathon-0/AI_Employee_Vault")
rejected_dir = vault_path / "Rejected"
cutoff = datetime.now() - timedelta(days=7)

for file_path in rejected_dir.iterdir():
    if file_path.is_file() and file_path.parent.name != "_ARCHIVED":
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        if mtime < cutoff:
            file_path.unlink()
            print(f"Deleted: {file_path.name}")
```

### View Archive

All archived files are stored in `/Rejected/_ARCHIVED/`:

```bash
dir D:\Hackathon-0\AI_Employee_Vault\Rejected\_ARCHIVED
```

## Compliance & Audit

### What Gets Logged

- ✅ Every time a rejected file is processed
- ✅ Days since rejection for each file
- ✅ When a file is archived
- ✅ When a file is permanently deleted
- ✅ Retention policy settings at time of deletion

### Audit Trail

The archive in `/Rejected/_ARCHIVED/` provides a permanent record of:
- Original filename
- Rejection date
- Archive date
- Retention policy applied
- Reason for deletion

## Troubleshooting

### Files Not Being Deleted

1. Check `ENABLE_REJECTED_AUTO_DELETE=true` in `.env`
2. Verify file age: files must be >= `REJECTED_AUTO_DELETE_DAYS` old
3. Check logs for errors: `/Logs/orchestrator_*.log`
4. Ensure orchestrator has write permissions to vault

### Archive Directory Missing

The `_ARCHIVED` subdirectory is created automatically when the orchestrator starts. If missing:

```python
from pathlib import Path
vault_path = Path("D:/Hackathon-0/AI_Employee_Vault")
(vault_path / "Rejected" / "_ARCHIVED").mkdir(parents=True, exist_ok=True)
```

## Best Practices

1. **Review Before Rejecting**: Move files to Rejected only after careful review
2. **Adjust Retention**: Set `REJECTED_AUTO_DELETE_DAYS` based on your compliance requirements
3. **Monitor Logs**: Regularly check rejection logs for patterns
4. **Backup Archives**: Include `_ARCHIVED` in your backup strategy
5. **Test First**: Run with `DRY_RUN=true` to verify behavior before enabling

## Related Documentation

- [Orchestrator Specification](../SPECIFICATIONS.md)
- [Human-in-the-Loop Workflow](./HITL_WORKFLOW.md)
- [Audit Logging](./AUDIT_LOGGING.md)
