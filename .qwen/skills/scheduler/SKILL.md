---
name: scheduler
description: |
  Cross-platform task scheduling via Windows Task Scheduler or Unix cron.
  Manages recurring tasks like daily briefings, weekly audits, and periodic
  checks. Supports task registration, enable/disable, and monitoring.
---

# Scheduler Skill

Cross-platform task scheduling and management.

## When to Use

- Schedule recurring tasks (daily, weekly, monthly)
- Set up automated briefings
- Schedule periodic watcher checks
- Manage task lifecycle

## CLI Usage

```bash
# Show scheduler status
python ai-employee/src/skills/scheduler.py \
  --status \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# List scheduled tasks
python ai-employee/src/skills/scheduler.py \
  --list \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Create daily briefing task (8 AM daily)
python ai-employee/src/skills/scheduler.py \
  --create daily_briefing \
  --type daily_briefing \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Create weekly audit (Monday 7 AM)
python ai-employee/src/skills/scheduler.py \
  --create weekly_audit \
  --type weekly_audit \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Delete task
python ai-employee/src/skills/scheduler.py \
  --delete daily_briefing \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Disable task
python ai-employee/src/skills/scheduler.py \
  --disable daily_briefing \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Enable task
python ai-employee/src/skills/scheduler.py \
  --enable daily_briefing \
  --vault "D:\Hackathon-0\AI_Employee_Vault"
```

## Pre-configured Task Types

| Task Type | Schedule | Description |
|-----------|----------|-------------|
| `daily_briefing` | 8:00 AM daily | Generate CEO briefing |
| `weekly_audit` | Monday 7:00 AM | Weekly business audit |
| `gmail_check` | Every 120 min | Check Gmail for new emails |
| `whatsapp_check` | Every 30 min | Check WhatsApp for messages |
| `linkedin_post` | Tue/Thu 10:00 AM | Post to LinkedIn |
| `dashboard_update` | Every 5 min | Update Dashboard.md |

## Task Schedules

### Daily Briefing

```xml
<!-- Windows Task Scheduler XML -->
<Trigger>
  <CalendarTrigger>
    <StartBoundary>2026-03-30T08:00:00</StartBoundary>
    <ScheduleByDay>
      <DaysInterval>1</DaysInterval>
    </ScheduleByDay>
  </CalendarTrigger>
</Trigger>
<Action>
  <Exec>
    <Command>python</Command>
    <Arguments>ai-employee/src/orchestration/orchestrator.py --task daily_briefing</Arguments>
  </Exec>
</Action>
```

### Weekly Audit

```xml
<Trigger>
  <CalendarTrigger>
    <StartBoundary>2026-03-31T07:00:00</StartBoundary>
    <Weekly>
      <DaysOfWeek>
        <Monday />
      </DaysOfWeek>
    </Weekly>
  </CalendarTrigger>
</Trigger>
```

## Python API Usage

```python
from skills.scheduler import SchedulerSkill

# Initialize
scheduler = SchedulerSkill(
    vault_path="D:\\Hackathon-0\\AI_Employee_Vault"
)

# Create task
scheduler.create_task(
    task_name="daily_briefing",
    task_type="daily_briefing",
    hour=8,
    minute=0
)

# List tasks
tasks = scheduler.list_tasks()
for task in tasks:
    print(f"{task['name']}: {task['status']}")

# Delete task
scheduler.delete_task("daily_briefing")
```

## Platform Detection

The scheduler automatically detects the platform:

| Platform | Scheduler |
|----------|-----------|
| Windows | Task Scheduler |
| Linux | cron |
| macOS | launchd / cron |

## Integration

### Called By

- **Orchestrator**: Schedule recurring tasks
- **Setup Scripts**: Initial task registration

### Calls

- **Orchestrator**: Trigger scheduled tasks
- **Skills**: Execute task-specific logic

## Error Handling

| Error | Behavior | Recovery |
|-------|----------|----------|
| Task already exists | Returns error, skips | Delete existing first |
| Scheduler service stopped | Logs error | Start service |
| Invalid task type | Returns error | Use valid type |
| Permission denied | Logs error | Run as admin |

## Troubleshooting

### Tasks not running

**Windows:** Check Task Scheduler service

```bash
# Open Task Scheduler
taskschd.msc

# Find AI Employee tasks
# Check "Last Run Result"
```

**Linux:** Check cron service

```bash
# Check cron status
systemctl status cron

# View cron logs
grep CRON /var/log/syslog
```

### Task created but not executing

**Check:** Python path is correct

**Fix:** Edit task and verify Python executable path

### Permission issues (Windows)

**Fix:** Run as Administrator

```bash
# Run command prompt as Administrator
python ai-employee/src/skills/scheduler.py --create daily_briefing
```

## Related Skills

- [`gmail_watcher`](../gmail-watcher/SKILL.md) - Schedule email checks
- [`whatsapp_watcher`](../whatsapp-watcher/SKILL.md) - Schedule message checks
- [`update_dashboard`](../update-dashboard/SKILL.md) - Schedule updates

## Example: Complete Setup

```bash
# 1. Create all standard tasks
python ai-employee/src/skills/scheduler.py \
  --create daily_briefing --type daily_briefing \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

python ai-employee/src/skills/scheduler.py \
  --create weekly_audit --type weekly_audit \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# 2. Verify tasks
python ai-employee/src/skills/scheduler.py \
  --list \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Output:
# daily_briefing - Enabled - Next run: 2026-03-30 08:00
# weekly_audit - Enabled - Next run: 2026-04-01 07:00
```

## Version

1.0.0 (Silver Tier)
