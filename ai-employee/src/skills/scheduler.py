"""
Scheduler Skill for AI Employee - Silver Tier

This skill handles scheduled operations via cron (Linux/Mac) or Task Scheduler (Windows).
It enables timed execution of AI Employee tasks like daily briefings, periodic checks, etc.

Silver Tier Requirement: Basic scheduling via cron or Task Scheduler

Features:
- Cross-platform scheduling (Windows Task Scheduler + cron)
- Schedule recurring tasks (daily, weekly, monthly)
- Schedule one-time tasks
- Task registration and management
- Integration with orchestrator and skills
- Comprehensive logging
"""

import os

# Environment variable for vault path (set in .env file)
# Default: D:/Hackathon-0/AI_Employee_Vault (root vault)
DEFAULT_VAULT_PATH = os.getenv('VAULT_PATH', 'D:/Hackathon-0/AI_Employee_Vault')

import sys
import json
import subprocess
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
import xml.etree.ElementTree as ET

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SchedulerSkill:
    """
    Scheduler Skill
    
    Manages scheduled tasks for the AI Employee.
    Supports Windows Task Scheduler and Unix cron.
    """
    
    # Task types
    TASK_TYPES = [
        'daily_briefing',
        'weekly_audit',
        'gmail_check',
        'whatsapp_check',
        'linkedin_post',
        'custom'
    ]
    
    # Default schedules
    DEFAULT_SCHEDULES = {
        'daily_briefing': {'hour': 8, 'minute': 0},  # 8:00 AM daily
        'weekly_audit': {'weekday': 0, 'hour': 7, 'minute': 0},  # Monday 7:00 AM
        'gmail_check': {'interval_minutes': 120},  # Every 2 hours
        'whatsapp_check': {'interval_minutes': 30},  # Every 30 minutes
    }
    
    def __init__(
        self,
        vault_path: Optional[str] = None,
        orchestrator_path: Optional[str] = None,
        python_path: Optional[str] = None
    ):
        """
        Initialize Scheduler Skill
        
        Args:
            vault_path: Path to Obsidian vault
            orchestrator_path: Path to orchestrator.py
            python_path: Path to Python executable
        """
        # Resolve paths
        self.project_root = Path(__file__).parent.parent.parent
        self.vault_path = Path(vault_path) if vault_path else Path(DEFAULT_VAULT_PATH)
        # Check if project_root already ends with ai-employee
        if self.project_root.name == 'ai-employee':
            self.orchestrator_path = Path(orchestrator_path) if orchestrator_path else self.project_root / 'src' / 'orchestration' / 'orchestrator.py'
        else:
            self.orchestrator_path = Path(orchestrator_path) if orchestrator_path else self.project_root / 'ai-employee' / 'src' / 'orchestration' / 'orchestrator.py'
        self.python_path = Path(python_path) if python_path else sys.executable
        
        # Directories
        self.logs_dir = self.vault_path / 'Logs'
        self.schedules_dir = self.vault_path / 'Schedules'
        
        for directory in [self.logs_dir, self.schedules_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Platform detection
        self.is_windows = sys.platform == 'win32'
        self.is_macos = sys.platform == 'darwin'
        self.is_linux = sys.platform == 'linux'
        
        logger.info("SchedulerSkill initialized")
        logger.info(f"Platform: {sys.platform}")
        logger.info(f"Python path: {self.python_path}")
        logger.info(f"Orchestrator path: {self.orchestrator_path}")
    
    def create_scheduled_task(
        self,
        task_name: str,
        task_type: str,
        schedule_config: Dict[str, Any],
        script_path: Optional[str] = None,
        script_args: Optional[List[str]] = None,
        enabled: bool = True
    ) -> Dict[str, Any]:
        """
        Create a scheduled task
        
        Args:
            task_name: Unique task name
            task_type: Type of task (daily_briefing, weekly_audit, etc.)
            schedule_config: Schedule configuration
            script_path: Path to script to run (default: orchestrator)
            script_args: Additional script arguments
            enabled: If True, enable the task
            
        Returns:
            Dict: Task creation result
        """
        result = {
            'success': False,
            'task_name': task_name,
            'platform': 'windows' if self.is_windows else 'unix',
            'error': None
        }
        
        # Validate task type
        if task_type not in self.TASK_TYPES:
            result['error'] = f"Unknown task type: {task_type}"
            return result
        
        # Determine script to run
        if script_path:
            script = Path(script_path)
        else:
            script = self.orchestrator_path
        
        if not script.exists():
            result['error'] = f"Script not found: {script}"
            return result
        
        # Build command
        cmd = [str(self.python_path), str(script)]
        if script_args:
            cmd.extend(script_args)
        cmd.append(f'--task={task_type}')
        
        # Create schedule file (for reference)
        schedule_file = self._create_schedule_file(
            task_name, task_type, schedule_config, cmd, enabled
        )
        
        # Register with platform scheduler
        if self.is_windows:
            result = self._create_windows_task(task_name, cmd, schedule_config, enabled)
        else:
            result = self._create_cron_task(task_name, cmd, schedule_config, enabled)
        
        result['schedule_file'] = str(schedule_file)
        
        # Log action
        self._log_action('create_scheduled_task', {
            'task_name': task_name,
            'task_type': task_type,
            'success': result['success']
        })
        
        return result
    
    def _create_schedule_file(
        self,
        task_name: str,
        task_type: str,
        schedule_config: Dict[str, Any],
        cmd: List[str],
        enabled: bool
    ) -> Path:
        """Create schedule definition file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"SCHEDULE_{task_name}_{timestamp}.md"
        filepath = self.schedules_dir / filename
        
        content = f"""---
type: schedule_definition
task_name: {task_name}
task_type: {task_type}
created: {datetime.now().isoformat()}
enabled: {enabled}
platform: {'windows' if self.is_windows else 'unix'}
---

# Scheduled Task: {task_name}

## Configuration

**Type:** {task_type}
**Platform:** {'Windows Task Scheduler' if self.is_windows else 'cron'}
**Enabled:** {enabled}

## Schedule

```json
{json.dumps(schedule_config, indent=2)}
```

## Command

```bash
{' '.join(cmd)}
```

---

## Status

- [ ] Task registered with system scheduler
- [ ] Test run completed successfully
- [ ] Logging verified

---
*Generated by AI Employee - Scheduler Skill*
"""
        
        filepath.write_text(content, encoding='utf-8')
        return filepath
    
    def _create_windows_task(
        self,
        task_name: str,
        cmd: List[str],
        schedule_config: Dict[str, Any],
        enabled: bool
    ) -> Dict[str, Any]:
        """
        Create Windows Task Scheduler task
        
        Args:
            task_name: Task name
            cmd: Command to execute
            schedule_config: Schedule configuration
            enabled: Enable task
            
        Returns:
            Dict: Result
        """
        result = {
            'success': False,
            'method': 'schtasks',
            'task_name': task_name
        }
        
        try:
            # Build schtasks command
            # Daily trigger
            if 'hour' in schedule_config and 'minute' in schedule_config:
                trigger = '/SC DAILY'
                trigger += f' /ST {schedule_config["hour"]:02d}:{schedule_config["minute"]:02d}'
            
            # Weekly trigger
            elif 'weekday' in schedule_config:
                days = {0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THU', 4: 'FRI', 5: 'SAT', 6: 'SUN'}
                day_str = days.get(schedule_config['weekday'], 'MON')
                trigger = f'/SC WEEKLY /D {day_str}'
                trigger += f' /ST {schedule_config.get("hour", 8):02d}:{schedule_config.get("minute", 0):02d}'
            
            # Interval trigger (for continuous tasks)
            elif 'interval_minutes' in schedule_config:
                trigger = f'/SC MINUTE /MO {schedule_config["interval_minutes"]}'
            
            else:
                result['error'] = 'Invalid schedule configuration'
                return result
            
            # Build full command
            program = cmd[0]
            args = ' '.join(f'"{arg}"' for arg in cmd[1:]) if len(cmd) > 1 else ''
            
            schtasks_cmd = [
                'schtasks', '/Create',
                '/TN', f'AI_Employee_{task_name}',
                '/TR', f'{program} {args}',
                '/RL', 'HIGHEST',
                '/F'  # Force overwrite if exists
            ]
            
            if enabled:
                schtasks_cmd.append('/ENABLE')
            else:
                schtasks_cmd.append('/DISABLE')
            
            # Add trigger
            schtasks_cmd.extend(trigger.split())
            
            logger.info(f"Creating Windows task: {' '.join(schtasks_cmd)}")
            
            # Execute
            proc = subprocess.run(
                schtasks_cmd,
                capture_output=True,
                text=True
            )
            
            if proc.returncode == 0:
                result['success'] = True
                result['message'] = f"Task created: AI_Employee_{task_name}"
                logger.info(f"Windows task created: {task_name}")
            else:
                result['error'] = proc.stderr
                logger.error(f"Failed to create Windows task: {proc.stderr}")
        
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error creating Windows task: {e}")
        
        return result
    
    def _create_cron_task(
        self,
        task_name: str,
        cmd: List[str],
        schedule_config: Dict[str, Any],
        enabled: bool
    ) -> Dict[str, Any]:
        """
        Create cron task (Linux/Mac)
        
        Args:
            task_name: Task name
            cmd: Command to execute
            schedule_config: Schedule configuration
            enabled: Enable task
            
        Returns:
            Dict: Result
        """
        result = {
            'success': False,
            'method': 'cron',
            'task_name': task_name
        }
        
        try:
            # Build cron expression
            if 'hour' in schedule_config and 'minute' in schedule_config:
                # Daily
                cron_expr = f'{schedule_config["minute"]} {schedule_config["hour"]} * * *'
            
            elif 'weekday' in schedule_config:
                # Weekly
                cron_expr = f'{schedule_config.get("minute", 0)} {schedule_config.get("hour", 8)} * * {schedule_config["weekday"]}'
            
            elif 'interval_minutes' in schedule_config:
                # For interval-based, we need a different approach
                # This is a limitation of cron - use a wrapper script
                result['warning'] = 'Interval scheduling requires wrapper script'
                cron_expr = f'*/{schedule_config["interval_minutes"]} * * * *'
            
            else:
                result['error'] = 'Invalid schedule configuration'
                return result
            
            # Build cron line
            command = ' '.join(str(c) for c in cmd)
            cron_line = f'{cron_expr} {command} >> {self.logs_dir}/cron_{task_name}.log 2>&1'
            
            if not enabled:
                cron_line = f'# {cron_line}  # Disabled'
            
            # Get current crontab
            get_crontab = subprocess.run(
                ['crontab', '-l'],
                capture_output=True,
                text=True
            )
            
            current_crontab = get_crontab.stdout if get_crontab.returncode == 0 else ''
            
            # Check if task already exists
            lines = current_crontab.split('\n')
            new_lines = []
            task_exists = False
            
            for line in lines:
                if f'AI_Employee_{task_name}' in line or f'--task={task_name}' in line:
                    # Replace existing task
                    new_lines.append(cron_line)
                    task_exists = True
                else:
                    new_lines.append(line)
            
            if not task_exists:
                new_lines.append(cron_line)
            
            # Write new crontab
            new_crontab = '\n'.join(new_lines)
            
            set_crontab = subprocess.run(
                ['crontab', '-'],
                input=new_crontab,
                capture_output=True,
                text=True
            )
            
            if set_crontab.returncode == 0:
                result['success'] = True
                result['message'] = f"Cron task created: {task_name}"
                result['cron_expression'] = cron_expr
                logger.info(f"Cron task created: {task_name}")
            else:
                result['error'] = set_crontab.stderr
                logger.error(f"Failed to create cron task: {set_crontab.stderr}")
        
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error creating cron task: {e}")
        
        return result
    
    def delete_scheduled_task(self, task_name: str) -> Dict[str, Any]:
        """
        Delete a scheduled task
        
        Args:
            task_name: Task name to delete
            
        Returns:
            Dict: Result
        """
        result = {
            'success': False,
            'task_name': task_name
        }
        
        try:
            if self.is_windows:
                # Delete Windows task
                proc = subprocess.run(
                    ['schtasks', '/Delete', '/TN', f'AI_Employee_{task_name}', '/F'],
                    capture_output=True,
                    text=True
                )
                
                if proc.returncode == 0:
                    result['success'] = True
                    result['message'] = f"Task deleted: AI_Employee_{task_name}"
                else:
                    result['error'] = proc.stderr
                    
            else:
                # Delete cron task
                get_crontab = subprocess.run(
                    ['crontab', '-l'],
                    capture_output=True,
                    text=True
                )
                
                if get_crontab.returncode == 0:
                    lines = get_crontab.stdout.split('\n')
                    new_lines = []
                    
                    for line in lines:
                        if f'AI_Employee_{task_name}' not in line and f'--task={task_name}' not in line:
                            new_lines.append(line)
                    
                    new_crontab = '\n'.join(new_lines)
                    
                    set_crontab = subprocess.run(
                        ['crontab', '-'],
                        input=new_crontab,
                        capture_output=True,
                        text=True
                    )
                    
                    if set_crontab.returncode == 0:
                        result['success'] = True
                        result['message'] = f"Cron task deleted: {task_name}"
                    else:
                        result['error'] = set_crontab.stderr
        
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error deleting task: {e}")
        
        return result
    
    def list_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """
        List all AI Employee scheduled tasks
        
        Returns:
            List[Dict]: List of tasks
        """
        tasks = []
        
        try:
            if self.is_windows:
                # List Windows tasks
                proc = subprocess.run(
                    ['schtasks', '/Query', '/FO', 'CSV'],
                    capture_output=True,
                    text=True
                )
                
                if proc.returncode == 0:
                    lines = proc.stdout.strip().split('\n')
                    for line in lines[1:]:  # Skip header
                        parts = line.split(',')
                        if len(parts) >= 2 and 'AI_Employee' in parts[1]:
                            tasks.append({
                                'name': parts[1].replace('AI_Employee_', ''),
                                'status': 'enabled' if 'Ready' in parts[0] else 'disabled',
                                'platform': 'windows'
                            })
            
            else:
                # List cron tasks
                proc = subprocess.run(
                    ['crontab', '-l'],
                    capture_output=True,
                    text=True
                )
                
                if proc.returncode == 0:
                    lines = proc.stdout.split('\n')
                    for line in lines:
                        if 'AI_Employee' in line or '--task=' in line:
                            enabled = not line.strip().startswith('#')
                            tasks.append({
                                'name': 'cron_task',
                                'cron_expression': line.split()[0:5] if enabled else None,
                                'enabled': enabled,
                                'platform': 'unix'
                            })
        
        except Exception as e:
            logger.error(f"Error listing tasks: {e}")
        
        return tasks
    
    def enable_task(self, task_name: str) -> Dict[str, Any]:
        """Enable a scheduled task"""
        if self.is_windows:
            proc = subprocess.run(
                ['schtasks', '/Change', '/TN', f'AI_Employee_{task_name}', '/ENABLE'],
                capture_output=True,
                text=True
            )
            return {
                'success': proc.returncode == 0,
                'task_name': task_name,
                'error': proc.stderr if proc.returncode != 0 else None
            }
        else:
            # For cron, tasks are enabled by default when not commented
            return {'success': True, 'task_name': task_name, 'message': 'Use crontab -e to uncomment'}
    
    def disable_task(self, task_name: str) -> Dict[str, Any]:
        """Disable a scheduled task"""
        if self.is_windows:
            proc = subprocess.run(
                ['schtasks', '/Change', '/TN', f'AI_Employee_{task_name}', '/DISABLE'],
                capture_output=True,
                text=True
            )
            return {
                'success': proc.returncode == 0,
                'task_name': task_name,
                'error': proc.stderr if proc.returncode != 0 else None
            }
        else:
            return {'success': True, 'task_name': task_name, 'message': 'Use crontab -e to comment out'}
    
    def _log_action(self, action_type: str, details: Dict[str, Any]) -> None:
        """Log action to vault logs"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'actor': 'scheduler_skill',
            'action_type': action_type,
            'details': details
        }
        
        log_file = self.logs_dir / f"scheduler_{datetime.now().strftime('%Y-%m-%d')}.json"
        
        logs = []
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except:
                logs = []
        
        logs.append(log_entry)
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2)
    
    def get_status(self) -> Dict[str, Any]:
        """Get skill status"""
        tasks = self.list_scheduled_tasks()
        
        return {
            'platform': 'windows' if self.is_windows else ('macos' if self.is_macos else 'linux'),
            'python_path': str(self.python_path),
            'orchestrator_path': str(self.orchestrator_path),
            'scheduled_tasks_count': len(tasks),
            'scheduled_tasks': tasks
        }


# CLI interface
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Scheduler Skill')
    parser.add_argument('--vault', type=str, help='Path to Obsidian vault')
    parser.add_argument('--status', action='store_true', help='Show scheduler status')
    parser.add_argument('--list', action='store_true', help='List scheduled tasks')
    parser.add_argument('--create', type=str, help='Create new task (name)')
    parser.add_argument('--delete', type=str, help='Delete task (name)')
    parser.add_argument('--type', type=str, help='Task type')
    parser.add_argument('--enable', type=str, help='Enable task')
    parser.add_argument('--disable', type=str, help='Disable task')
    
    args = parser.parse_args()
    
    skill = SchedulerSkill(vault_path=args.vault)
    
    if args.status:
        status = skill.get_status()
        print("Scheduler Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")
        sys.exit(0)
    
    if args.list:
        tasks = skill.list_scheduled_tasks()
        if tasks:
            print(f"Found {len(tasks)} scheduled task(s):")
            for task in tasks:
                print(f"  - {task['name']} ({task['platform']})")
        else:
            print("No scheduled tasks found")
        sys.exit(0)
    
    if args.create:
        if not args.type:
            print("Error: --type required with --create")
            sys.exit(1)
        
        schedule_config = DEFAULT_SCHEDULES.get(args.type, {'hour': 8, 'minute': 0})
        result = skill.create_scheduled_task(args.create, args.type, schedule_config)
        print(f"Create task result: {result}")
        sys.exit(0 if result['success'] else 1)
    
    if args.delete:
        result = skill.delete_scheduled_task(args.delete)
        print(f"Delete task result: {result}")
        sys.exit(0 if result['success'] else 1)
    
    if args.enable:
        result = skill.enable_task(args.enable)
        print(f"Enable task result: {result}")
        sys.exit(0 if result['success'] else 1)
    
    if args.disable:
        result = skill.disable_task(args.disable)
        print(f"Disable task result: {result}")
        sys.exit(0 if result['success'] else 1)
    
    # Default: show help
    parser.print_help()
