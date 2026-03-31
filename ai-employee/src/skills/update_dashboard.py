"""
Update Dashboard Skill

Specification: AGENT-SKILLS-001 (update_dashboard)

Purpose: Refresh Dashboard.md with current vault state

Input: None (reads vault state)

Output:
    - Updated Dashboard.md
    
Behavior:
    1. Count files in each folder
    2. Read recent logs
    3. Update timestamp
    4. Write new Dashboard.md
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional


def count_files_in_folder(folder_path: Path) -> int:
    """
    Count files in a folder (non-recursive).
    
    Args:
        folder_path: Path to folder
        
    Returns:
        int: Number of files
    """
    if not folder_path.exists():
        return 0
    return sum(1 for f in folder_path.iterdir() if f.is_file())


def get_recent_activity(vault_path: Path, limit: int = 10) -> List[str]:
    """
    Get recent activity from logs.
    
    Args:
        vault_path: Path to vault root
        limit: Maximum number of activities to return
        
    Returns:
        List[str]: List of activity descriptions
    """
    activities = []
    
    # Try to read today's log file
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = vault_path / 'Logs' / f"{today}.json"
    
    if log_file.exists():
        try:
            import json
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            
            # Get most recent entries
            recent_logs = logs[-limit:] if len(logs) > limit else logs
            
            for log in reversed(recent_logs):
                action_type = log.get('action_type', 'unknown')
                actor = log.get('actor', 'unknown')
                target = log.get('target', '')
                result = log.get('result', 'unknown')
                timestamp = log.get('timestamp', '')
                
                # Format timestamp
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        time_str = dt.strftime('%H:%M')
                    except:
                        time_str = timestamp[:5] if len(timestamp) > 5 else timestamp
                else:
                    time_str = '??:??'
                
                # Create activity description
                emoji = '✅' if result == 'success' else '❌' if result == 'failure' else '⏳'
                activities.append(
                    f"- [{time_str}] {emoji} {action_type.replace('_', ' ').title()}: {target[:50]}"
                )
        except Exception as e:
            activities.append(f"- Error reading logs: {e}")
    
    if not activities:
        activities.append("- *No recent activity*")
    
    return activities


def get_alerts(vault_path: Path) -> List[str]:
    """
    Check for items requiring immediate attention.
    
    Args:
        vault_path: Path to vault root
        
    Returns:
        List[str]: List of alert messages
    """
    alerts = []
    
    # Check Pending_Approval folder
    pending_approval = vault_path / 'Pending_Approval'
    if pending_approval.exists():
        count = count_files_in_folder(pending_approval)
        if count > 0:
            alerts.append(f"- ⚠️ {count} item(s) awaiting approval in /Pending_Approval/")
    
    # Check Needs_Action folder for old items
    needs_action = vault_path / 'Needs_Action'
    if needs_action.exists():
        old_items = []
        for f in needs_action.iterdir():
            if f.is_file():
                try:
                    mtime = datetime.fromtimestamp(f.stat().st_mtime)
                    age = datetime.now() - mtime
                    if age.days > 1:
                        old_items.append(f.name)
                except:
                    pass
        
        if old_items:
            alerts.append(f"- ⚠️ {len(old_items)} item(s) pending for over 24 hours")
    
    # Check for errors in recent logs
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = vault_path / 'Logs' / f"{today}.json"
    if log_file.exists():
        try:
            import json
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            
            errors = [l for l in logs if l.get('result') == 'failure']
            if errors:
                alerts.append(f"- ❌ {len(errors)} error(s) in today's logs")
        except:
            pass
    
    if not alerts:
        alerts.append("- *No active alerts*")
    
    return alerts


def get_system_health(vault_path: Path) -> Dict[str, Dict[str, str]]:
    """
    Get system health status for each component.
    
    Args:
        vault_path: Path to vault root
        
    Returns:
        Dict: Health status for each component
    """
    health = {
        'Gmail Watcher': {'status': '🟡 Not Started', 'last_check': '-'},
        'Filesystem Watcher': {'status': '🟡 Not Started', 'last_check': '-'},
        'Qwen Code Integration': {'status': '🟡 Not Configured', 'last_check': '-'},
        'Orchestrator': {'status': '🟡 Not Started', 'last_check': '-'},
    }
    
    # Check for watcher cache files (indicates recent activity)
    cache_dir = vault_path / '.cache'
    if cache_dir.exists():
        # Gmail Watcher
        gmail_cache = cache_dir / 'GmailWatcher_processed.json'
        if gmail_cache.exists():
            try:
                mtime = datetime.fromtimestamp(gmail_cache.stat().st_mtime)
                age = datetime.now() - mtime
                if age.total_seconds() < 300:  # 5 minutes
                    health['Gmail Watcher'] = {
                        'status': '🟢 Running',
                        'last_check': f"{int(age.total_seconds() / 60)}m ago"
                    }
                else:
                    health['Gmail Watcher'] = {
                        'status': '🟠 Inactive',
                        'last_check': f"{int(age.total_seconds() / 60)}m ago"
                    }
            except:
                pass
        
        # Filesystem Watcher
        fs_cache = cache_dir / 'FilesystemWatcher_processed.json'
        if fs_cache.exists():
            try:
                mtime = datetime.fromtimestamp(fs_cache.stat().st_mtime)
                age = datetime.now() - mtime
                if age.total_seconds() < 300:  # 5 minutes
                    health['Filesystem Watcher'] = {
                        'status': '🟢 Running',
                        'last_check': f"{int(age.total_seconds() / 60)}m ago"
                    }
                else:
                    health['Filesystem Watcher'] = {
                        'status': '🟠 Inactive',
                        'last_check': f"{int(age.total_seconds() / 60)}m ago"
                    }
            except:
                pass
    
    return health


def get_active_projects(vault_path: Path) -> List[Dict[str, str]]:
    """
    Get active projects from Business_Goals.md.
    
    Args:
        vault_path: Path to vault root
        
    Returns:
        List[Dict]: List of project information
    """
    projects = []
    
    goals_file = vault_path / 'Business_Goals.md'
    if goals_file.exists():
        try:
            content = goals_file.read_text(encoding='utf-8')
            
            # Simple parsing - look for project table
            in_projects = False
            for line in content.split('\n'):
                if 'Active Projects' in line:
                    in_projects = True
                    continue
                if in_projects and line.startswith('| #'):
                    continue  # Skip header
                if in_projects and line.startswith('|'):
                    parts = [p.strip() for p in line.split('|') if p.strip()]
                    if len(parts) >= 5:
                        projects.append({
                            'name': parts[1] if len(parts) > 1 else 'Unknown',
                            'status': parts[2] if len(parts) > 2 else 'Unknown',
                            'due_date': parts[3] if len(parts) > 3 else 'Unknown',
                            'budget': parts[4] if len(parts) > 4 else 'Unknown'
                        })
                elif in_projects and line.startswith('---'):
                    break
        except Exception as e:
            pass
    
    if not projects:
        projects.append({
            'name': 'AI Employee Setup',
            'status': 'In Progress',
            'due_date': '2026-03-15',
            'budget': '-'
        })
    
    return projects


def get_linkedin_metrics(vault_path: Path, config_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Get LinkedIn activity metrics.

    Args:
        vault_path: Path to vault root
        config_dir: Path to config directory (for session info)

    Returns:
        Dict: LinkedIn metrics
    """
    metrics = {
        'total_posts': 0,
        'pending': 0,
        'approved': 0,
        'done': 0,
        'rejected': 0,
        'latest_post': None,
        'latest_post_time': None,
        'posts_this_week': 0,
        'posts_this_month': 0,
        'session_status': 'Not authenticated',
        'session_age_days': None,
    }

    # Count LinkedIn posts in each folder
    done_dir = vault_path / 'Done'
    pending_approval = vault_path / 'Pending_Approval'
    approved_dir = vault_path / 'Approved'
    rejected_dir = vault_path / 'Rejected'

    if done_dir.exists():
        linkedin_done = [f for f in done_dir.iterdir() if f.is_file() and f.name.startswith('LINKEDIN_')]
        metrics['done'] = len(linkedin_done)
        metrics['total_posts'] = len(linkedin_done)

        # Find latest post
        if linkedin_done:
            latest = max(linkedin_done, key=lambda f: f.stat().st_mtime)
            metrics['latest_post'] = latest.stem
            latest_time = datetime.fromtimestamp(latest.stat().st_mtime)
            metrics['latest_post_time'] = latest_time

            # Posts this week
            week_ago = datetime.now() - timedelta(days=7)
            metrics['posts_this_week'] = sum(1 for f in linkedin_done if datetime.fromtimestamp(f.stat().st_mtime) > week_ago)

            # Posts this month
            month_ago = datetime.now() - timedelta(days=30)
            metrics['posts_this_month'] = sum(1 for f in linkedin_done if datetime.fromtimestamp(f.stat().st_mtime) > month_ago)

    if pending_approval.exists():
        metrics['pending'] = len([f for f in pending_approval.iterdir() if f.is_file() and f.name.startswith('LINKEDIN_')])

    if approved_dir.exists():
        metrics['approved'] = len([f for f in approved_dir.iterdir() if f.is_file() and f.name.startswith('LINKEDIN_')])

    if rejected_dir.exists():
        metrics['rejected'] = len([f for f in rejected_dir.iterdir() if f.is_file() and f.name.startswith('LINKEDIN_')])

    # Check session status
    if config_dir is None:
        # Try multiple possible config locations - check for actual session file
        possible_config_dirs = [
            Path(__file__).parent.parent / 'config',  # D:\Hackathon-0\ai-employee\config (most likely)
            vault_path.parent / 'config',  # D:\Hackathon-0\config
            vault_path.parent.parent / 'config',  # D:\Hackathon-0\config (if vault is nested)
        ]
        for config in possible_config_dirs:
            if config.exists() and (config / 'linkedin_session.json').exists():
                config_dir = config
                break
    
    session_file = config_dir / 'linkedin_session.json' if config_dir else None
    
    if session_file and session_file.exists():
        try:
            mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
            age = datetime.now() - mtime
            metrics['session_status'] = 'Active'
            metrics['session_age_days'] = age.days
        except:
            pass

    return metrics


def update_dashboard(vault_path: str) -> Dict[str, Any]:
    """
    Update Dashboard.md with current vault state.

    Args:
        vault_path: Path to Obsidian vault root

    Returns:
        Dict: Update results including counts and status
    """
    result = {
        'success': False,
        'vault_path': vault_path,
        'counts': {},
        'error': None
    }

    try:
        vault = Path(vault_path)

        # Determine config directory path
        config_dir = vault.parent / 'config'

        # Count files in each folder
        counts = {
            'pending_items': count_files_in_folder(vault / 'Needs_Action'),
            'pending_approval': count_files_in_folder(vault / 'Pending_Approval'),
            'completed_today': 0,
            'processing_errors': 0
        }

        # Check for errors in today's logs
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = vault / 'Logs' / f"{today}.json"
        if log_file.exists():
            try:
                import json
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                counts['processing_errors'] = sum(1 for l in logs if l.get('result') == 'failure')
                counts['completed_today'] = sum(1 for l in logs if 'done' in l.get('action_type', '').lower())
            except:
                pass

        result['counts'] = counts

        # Get system health
        health = get_system_health(vault)

        # Get recent activity
        activity = get_recent_activity(vault)

        # Get alerts
        alerts = get_alerts(vault)

        # Get active projects
        projects = get_active_projects(vault)

        # Get LinkedIn metrics
        linkedin_metrics = get_linkedin_metrics(vault, config_dir)

        # Build dashboard content
        projects_table = "| Project | Status | Due Date | Budget |\n"
        projects_table += "|---------|--------|----------|--------|\n"
        for project in projects:
            projects_table += f"| {project['name']} | {project['status']} | {project['due_date']} | {project['budget']} |\n"

        activity_text = '\n'.join(activity)
        alerts_text = '\n'.join(alerts)

        health_table = "| Component | Status | Last Check |\n"
        health_table += "|-----------|--------|------------|\n"
        for component, info in health.items():
            health_table += f"| {component} | {info['status']} | {info['last_check']} |\n"

        # LinkedIn section
        session_status_emoji = '✅' if linkedin_metrics['session_status'] == 'Active' else '❌'
        session_info = f"{session_status_emoji} {linkedin_metrics['session_status']}"
        if linkedin_metrics['session_age_days'] is not None:
            session_info += f" ({linkedin_metrics['session_age_days']} days old)"

        latest_post_info = linkedin_metrics['latest_post'] if linkedin_metrics['latest_post'] else 'None yet'
        if linkedin_metrics['latest_post_time']:
            time_ago = datetime.now() - linkedin_metrics['latest_post_time']
            if time_ago.days > 0:
                latest_post_info += f" ({time_ago.days}d ago)"
            elif time_ago.seconds >= 3600:
                latest_post_info += f" ({time_ago.seconds // 3600}h ago)"
            elif time_ago.seconds >= 60:
                latest_post_info += f" ({time_ago.seconds // 60}m ago)"
            else:
                latest_post_info += " (just now)"

        dashboard_content = f"""# Dashboard

**Last Updated:** {datetime.now().isoformat()}

**System Status:** 🟢 Operational

---

## Quick Stats

| Metric | Value |
|--------|-------|
| Pending Items | {counts['pending_items']} |
| Pending Approval | {counts['pending_approval']} |
| Completed Today | {counts['completed_today']} |
| Processing Errors | {counts['processing_errors']} |

---

## 📱 LinkedIn Activity

| Metric | Value |
|--------|-------|
| **Total Posts Published** | {linkedin_metrics['total_posts']} |
| **Pending Approval** | {linkedin_metrics['pending']} |
| **Awaiting Publishing** | {linkedin_metrics['approved']} |
| **Rejected Posts** | {linkedin_metrics['rejected']} |
| **Latest Post** | {latest_post_info} |
| **Posts This Week** | {linkedin_metrics['posts_this_week']} |
| **Posts This Month** | {linkedin_metrics['posts_this_month']} |
| **Session Status** | {session_info} |

---

## Active Projects

{projects_table}
---

## Recent Activity

{activity_text}

---

## Alerts

{alerts_text}

---

## System Health

{health_table}
---

## Quick Links

- [[Company Handbook]] - Rules and guidelines
- [[Business Goals]] - Objectives and metrics
- /Needs_Action/ - Items requiring attention
- /Pending_Approval/ - Awaiting human decision
- /Done/ - Completed items archive
- /Logs/ - System audit logs

---

## Notes

This dashboard is automatically updated by the AI Employee orchestrator.
Manual edits will be preserved but may be overwritten during the next update cycle.

---

*Generated by AI Employee v1.0.0 (Silver Tier - LinkedIn Enabled)*
"""

        # Write dashboard file
        dashboard_file = vault / 'Dashboard.md'
        dashboard_file.write_text(dashboard_content, encoding='utf-8')

        result['success'] = True

    except Exception as e:
        result['error'] = str(e)

    return result


def main():
    """
    Main entry point for testing the skill.
    
    Usage:
        python update_dashboard.py <vault_path>
    """
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python update_dashboard.py <vault_path>")
        sys.exit(1)
    
    vault_path = sys.argv[1]
    result = update_dashboard(vault_path)
    print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()
