---
name: update-dashboard
description: |
  Refresh Dashboard.md with current vault state. Counts files in each folder,
  reads recent activity logs, updates timestamps, and displays key metrics.
  Run periodically to keep Dashboard.md synchronized with vault state.
---

# Update Dashboard Skill

Automatically refresh the main Dashboard.md file with real-time vault statistics and activity.

## When to Use

- After completing any significant action
- On a schedule (e.g., every 5 minutes via orchestrator)
- When user requests dashboard refresh
- After batch processing multiple files

## CLI Usage

```bash
# Update dashboard (default vault path from .env)
python ai-employee/src/skills/update_dashboard.py \
  "D:\Hackathon-0\AI_Employee_Vault"

# Update with custom vault path
python ai-employee/src/skills/update_dashboard.py \
  "D:\Hackathon-0\AI_Employee_Vault" \
  --verbose
```

## Dashboard Sections Updated

### 1. System Status
- Last update timestamp
- System health indicator
- Active watchers status

### 2. File Counts
| Folder | Count Displayed |
|--------|-----------------|
| `/Inbox/` | Pending files |
| `/Needs_Action/` | Awaiting processing |
| `/Plans/` | Active plans |
| `/Pending_Approval/` | Awaiting human review |
| `/Approved/` | Ready for execution |
| `/Done/` | Completed today |

### 3. Recent Activity
- Last 10 actions from logs
- Timestamped entries
- Action type and result

### 4. Key Metrics
- Tasks completed today
- Pending approvals count
- Average processing time

## Output Format

Dashboard.md structure:

```markdown
# AI Employee Dashboard

**Last Updated:** 2026-03-29 18:30:00
**Status:** 🟢 Operational

---

## Quick Stats

| Metric | Count |
|--------|-------|
| 📥 Inbox | 0 |
| ⚠️ Needs Action | 3 |
| 📋 Plans | 2 |
| ⏳ Pending Approval | 1 |
| ✅ Done Today | 5 |

---

## Recent Activity

| Time | Action | Result |
|------|--------|--------|
| 18:25 | email_process | success |
| 18:20 | linkedin_post | pending_approval |
| 18:15 | update_dashboard | success |

---

## Pending Approvals

| File | Action | Expires |
|------|--------|---------|
| EMAIL_abc123.md | send_email | 2026-03-30 |
| LINKEDIN_post_456.md | social_post | 2026-03-30 |

---

## System Health

- Gmail Watcher: ✅ Running
- File Watcher: ✅ Running
- Orchestrator: ✅ Running
```

## Integration Points

### Called By

- **Orchestrator**: Every 5 minutes
- **Scheduler**: Daily briefing generation
- **Manual**: User-initiated refresh

### Calls

- **Log Action**: Records dashboard update
- **File System**: Reads folder contents
- **Log Files**: Reads recent activity

## Customization

### Update Frequency

Edit orchestrator settings:
```python
DASHBOARD_UPDATE_INTERVAL = 300  # 5 minutes
```

### Metrics to Track

Add custom metrics in `update_dashboard.py`:
```python
custom_metrics = {
    'emails_processed_today': count_emails('Done', 'email'),
    'pending_high_priority': count_priority('Needs_Action', 'high'),
}
```

## Error Handling

| Error | Behavior | Recovery |
|-------|----------|----------|
| Dashboard.md missing | Creates new file | Auto-recovery |
| Log file unreadable | Shows "No recent activity" | Continues gracefully |
| Folder not found | Shows 0 count | Creates folder if missing |
| Permission denied | Logs error, skips | Check file permissions |

## Logging

All updates logged to:
- Console: "Dashboard updated successfully"
- File: `/Logs/YYYY-MM-DD.json`

```json
{
  "timestamp": "2026-03-29T18:30:00Z",
  "action_type": "dashboard_update",
  "actor": "update_dashboard_skill",
  "target": "Dashboard.md",
  "result": "success"
}
```

## Troubleshooting

### Dashboard not updating

**Check:** Vault path is correct and writable

**Fix:** 
```bash
# Verify vault exists
dir "D:\Hackathon-0\AI_Employee_Vault"

# Check Dashboard.md permissions
```

### Counts showing 0

**Check:** Folders exist and contain files

**Fix:** Verify folder structure:
```bash
dir "D:\Hackathon-0\AI_Employee_Vault\Needs_Action"
```

### Recent activity empty

**Check:** Log files exist in `/Logs/`

**Fix:** Check log file format:
```bash
type "D:\Hackathon-0\AI_Employee_Vault\Logs\2026-03-29.json"
```

## Related Skills

- [`log_action`](../log-action/SKILL.md) - Record actions to audit log
- [`process_email`](../process-email/SKILL.md) - Process email files
- [`scheduler`](../scheduler/SKILL.md) - Schedule periodic updates

## Example: Manual Dashboard Refresh

```bash
# Quick refresh
python ai-employee/src/skills/update_dashboard.py \
  "D:\Hackathon-0\AI_Employee_Vault"

# Verify update
type "D:\Hackathon-0\AI_Employee_Vault\Dashboard.md"
```

## Example: Scheduled Updates

In orchestrator.py:
```python
from skills.update_dashboard import update_dashboard

# Update dashboard every 5 minutes
while running:
    update_dashboard(vault_path)
    time.sleep(300)
```

## Version

1.0.0 (Bronze Tier)
