"""
Demo: ALL Tasks Require Approval

Shows that every task goes through approval workflow regardless of content.
"""

import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from orchestration.orchestrator import Orchestrator, OrchestratorConfig, ALWAYS_REQUIRE_APPROVAL

VAULT_PATH = Path(__file__).parent / 'AI_Employee_Vault'

def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def cleanup():
    folders = ['Inbox', 'Needs_Action', 'Plans', 'Pending_Approval', 'Approved', 'Done']
    for folder in folders:
        fpath = VAULT_PATH / folder
        if fpath.exists():
            for f in fpath.iterdir():
                if f.is_file():
                    f.unlink()

def test_task(name, content, should_require_approval=True):
    """Test a single task."""
    print(f"\n--- Testing: {name} ---")
    print(f"Content: {content}")
    
    # Create task
    needs_action_dir = VAULT_PATH / 'Needs_Action'
    needs_action_dir.mkdir(parents=True, exist_ok=True)
    
    task_file = needs_action_dir / f"TASK_{name.replace(' ', '_')}.md"
    task_file.write_text(f"""---
type: task
created: {datetime.now().isoformat()}
---

{content}
""")
    
    # Wait for file age check (orchestrator only processes files > 5 seconds old)
    time.sleep(6)
    
    # Process with orchestrator
    config = OrchestratorConfig(vault_path=str(VAULT_PATH), check_interval=5, dry_run=True)
    orchestrator = Orchestrator(config)
    
    new_files = orchestrator.check_needs_action()
    if new_files:
        orchestrator.trigger_qwen(new_files)
    
    # Check if approval was created
    pending_dir = VAULT_PATH / 'Pending_Approval'
    approvals = list(pending_dir.glob("APPROVAL_*.md")) if pending_dir.exists() else []
    
    if approvals:
        print(f"Result: [REQUIRES APPROVAL] -> {approvals[-1].name}")
        # Clean up for next test
        for f in pending_dir.glob("APPROVAL_*.md"):
            f.unlink()
        for f in (VAULT_PATH / 'Plans').glob("PLAN_*.md"):
            f.unlink()
        task_file.unlink()
        return True
    else:
        print(f"Result: [NO APPROVAL] Auto-completed")
        # Clean up
        for f in (VAULT_PATH / 'Plans').glob("PLAN_*.md"):
            f.unlink()
        for f in (VAULT_PATH / 'Done').glob("DONE_*.md"):
            f.unlink()
        task_file.unlink()
        return False

def main():
    cleanup()
    
    print_header("ALL TASKS REQUIRE APPROVAL DEMO")
    print(f"\nConfiguration: ALWAYS_REQUIRE_APPROVAL = {ALWAYS_REQUIRE_APPROVAL}")
    
    test_cases = [
        ("Simple Note", "Remember to buy groceries", True),
        ("Meeting Reminder", "Team meeting at 3pm tomorrow", True),
        ("File Review", "Review the quarterly report", True),
        ("Phone Call", "Call dentist for appointment", True),
        ("Research", "Research new project tools", True),
    ]
    
    print("\n" + "=" * 70)
    print("TESTING TASKS (All should require approval)")
    print("=" * 70)
    
    all_required_approval = True
    for name, content, expected in test_cases:
        result = test_task(name, content, expected)
        if result != expected:
            all_required_approval = False
            print(f"  [FAIL] {name}: Expected approval={expected}, Got approval={result}")
        else:
            print(f"  [OK] {name}: Correctly required approval")
    
    print("\n" + "=" * 70)
    if all_required_approval:
        print("  SUCCESS: ALL TASKS REQUIRED APPROVAL")
        print("  Human-in-the-loop safety is ENABLED")
    else:
        print("  FAILURE: Some tasks bypassed approval")
    print("=" * 70)
    
    print("""
  BRONZE TIER SAFETY MODEL:
  
  [OK] Every task requires human approval before execution
  [OK] No autonomous actions without human review
  [OK] Full audit trail of all decisions
  [OK] Human maintains control of all actions
    """)

if __name__ == '__main__':
    main()
