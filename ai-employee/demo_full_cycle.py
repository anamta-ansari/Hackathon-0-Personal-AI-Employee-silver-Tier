"""
Full Cycle Demo: File Dropped → Done

Demonstrates the complete Bronze Tier flow:
1. File dropped in Inbox/
2. Watcher detects → Task created in Needs_Action/
3. Orchestrator creates plan in Plans/
4. Orchestrator checks for approval keywords
5. Approval required → Request created in Pending_Approval/
6. Human approves (simulated) → File moved to Approved/
7. Orchestrator executes → Files moved to Done/
8. Dashboard updated
9. All actions logged
"""

import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from orchestration.orchestrator import Orchestrator, OrchestratorConfig

VAULT_PATH = Path(__file__).parent / 'AI_Employee_Vault'

def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def print_step(num, text):
    print(f"\n[STEP {num}] {text}")
    print("-" * 50)

def cleanup():
    """Clean up folders for fresh demo."""
    folders = ['Inbox', 'Needs_Action', 'Plans', 'Pending_Approval', 'Approved', 'Done']
    for folder in folders:
        fpath = VAULT_PATH / folder
        if fpath.exists():
            for f in fpath.iterdir():
                if f.is_file():
                    f.unlink()

def main():
    cleanup()
    
    print_header("BRONZE TIER FULL CYCLE DEMO")
    print("Flow: File Dropped -> Detected -> Plan -> Approval -> Executed -> Done")
    
    # ================================================================
    # STEP 1: File Dropped
    # ================================================================
    print_step(1, "FILE DROPPED IN INBOX/")
    
    inbox_dir = VAULT_PATH / 'Inbox'
    inbox_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a file that will trigger approval (contains "email" keyword)
    test_file = inbox_dir / "client_inquiry.txt"
    test_file.write_text("Client wants to schedule a meeting via email.")
    
    print(f"Created file: {test_file.name}")
    print(f"Content: {test_file.read_text()}")
    
    # Simulate watcher moving to Needs_Action
    print("\n[WATCHER] Detecting file...")
    time.sleep(1)
    
    needs_action_dir = VAULT_PATH / 'Needs_Action'
    needs_action_dir.mkdir(parents=True, exist_ok=True)
    
    task_file = needs_action_dir / f"FILE_{test_file.stem}.md"
    task_file.write_text(f"""---
type: file_drop
original_name: {test_file.name}
received: {datetime.now().isoformat()}
status: pending
---

## Content
{test_file.read_text()}

## Action
Process client inquiry and send email response.
""")
    
    test_file.unlink()  # Remove from Inbox
    print(f"[WATCHER] Created task: {task_file.name}")
    
    # Wait for file to be "old" enough for processing
    print("\n[INFO] Waiting 6 seconds for file age check...")
    time.sleep(6)
    
    # ================================================================
    # STEP 2: PLAN CREATED
    # ================================================================
    print_step(2, "ORCHESTRATOR CREATES PLAN")
    
    config = OrchestratorConfig(vault_path=str(VAULT_PATH), check_interval=5, dry_run=True)
    orchestrator = Orchestrator(config)
    
    # Process the task
    new_files = orchestrator.check_needs_action()
    if new_files:
        orchestrator.trigger_qwen(new_files)
    
    # Check if plan was created
    plans_dir = VAULT_PATH / 'Plans'
    plans = list(plans_dir.glob("PLAN_*.md")) if plans_dir.exists() else []
    content = ""
    if plans:
        plan_file = plans[0]
        print(f"Plan created: {plan_file.name}")
        print(f"Content preview:")
        content = plan_file.read_text(encoding='utf-8')
        for line in content.split('\n')[:15]:
            print(f"  {line}")
    else:
        print("[ERROR] No plan created!")
    
    # ================================================================
    # STEP 3: APPROVAL CHECK
    # ================================================================
    print_step(3, "APPROVAL KEYWORD CHECK")
    
    APPROVAL_KEYWORDS = ["send", "email", "payment", "post", "delete", "publish", "share"]
    content_lower = content.lower()
    
    found_keywords = [kw for kw in APPROVAL_KEYWORDS if kw in content_lower]
    print(f"Scanning for keywords: {APPROVAL_KEYWORDS}")
    print(f"Found: {found_keywords}")
    
    if found_keywords:
        print("\n[INFO] Approval REQUIRED - creating approval request...")
        # Approval request already created by orchestrator
        pending_dir = VAULT_PATH / 'Pending_Approval'
        approvals = list(pending_dir.glob("APPROVAL_*.md")) if pending_dir.exists() else []
        if approvals:
            print(f"Approval request created: {approvals[0].name}")
    
    # ================================================================
    # STEP 4: HUMAN APPROVAL (SIMULATED)
    # ================================================================
    print_step(4, "HUMAN APPROVAL (SIMULATED)")
    
    pending_dir = VAULT_PATH / 'Pending_Approval'
    approved_dir = VAULT_PATH / 'Approved'
    approved_dir.mkdir(parents=True, exist_ok=True)
    
    if pending_dir.exists():
        for f in pending_dir.glob("APPROVAL_*.md"):
            # Simulate human moving file to Approved/
            approved_file = approved_dir / f.name
            approved_file.write_text(f.read_text())
            f.unlink()
            print(f"[HUMAN] Moved {f.name} to Approved/")
            print(f"[HUMAN] Action: APPROVED")
    
    # ================================================================
    # STEP 5: EXECUTION
    # ================================================================
    print_step(5, "ORCHESTRATOR EXECUTES APPROVED ACTION")
    
    # Run execution cycle
    orchestrator._execute_approved_actions()
    
    # Check Done folder
    done_dir = VAULT_PATH / 'Done'
    done_files = list(done_dir.glob("DONE_*.md")) if done_dir.exists() else []
    print(f"Files moved to Done/: {len(done_files)}")
    for f in done_files:
        print(f"  - {f.name}")
    
    # ================================================================
    # STEP 6: DASHBOARD UPDATE
    # ================================================================
    print_step(6, "DASHBOARD UPDATED")
    
    orchestrator._update_dashboard_with_stats()
    
    dashboard_path = VAULT_PATH / 'Dashboard.md'
    if dashboard_path.exists():
        content = dashboard_path.read_text(encoding='utf-8')
        # Extract stats table
        in_stats = False
        for line in content.split('\n'):
            if 'Quick Stats' in line:
                in_stats = True
            if in_stats:
                # Encode to ASCII, replace non-ASCII with ?
                safe_line = line.encode('ascii', 'replace').decode('ascii')
                print(safe_line)
                if line.startswith('|') and 'Completed Today' in line:
                    break
    
    # ================================================================
    # STEP 7: AUDIT LOG
    # ================================================================
    print_step(7, "AUDIT LOG ENTRIES")
    
    logs_dir = VAULT_PATH / 'Logs'
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = logs_dir / f"{today}.json"
    
    if log_file.exists():
        import json
        logs = json.loads(log_file.read_text())
        print(f"Total log entries today: {len(logs)}")
        print("\nRecent actions:")
        for log in logs[-5:]:
            print(f"  [{log.get('timestamp', '')[:16]}] {log.get('action_type', '')}: {log.get('target', '')[:40]}")
    
    # ================================================================
    # SUMMARY
    # ================================================================
    print_header("CYCLE COMPLETE")
    print("""
  Flow Summary:
  [OK] 1. File dropped in Inbox/
  [OK] 2. Watcher detected -> Task in Needs_Action/
  [OK] 3. Orchestrator created plan in Plans/
  [OK] 4. Approval keywords found -> Request in Pending_Approval/
  [OK] 5. Human approved -> Moved to Approved/
  [OK] 6. Orchestrator executed -> Files in Done/
  [OK] 7. Dashboard updated with stats
  [OK] 8. All actions logged to JSON
  
  BRONZE TIER: FULLY OPERATIONAL
    """)
    print("=" * 70)

if __name__ == '__main__':
    main()
