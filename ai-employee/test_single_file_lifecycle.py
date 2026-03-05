"""
Test Script: Single-File Lifecycle

This script demonstrates the single-file lifecycle where ONE file moves through folders:
Needs_Action/ → Plans/ → Pending_Approval/ → Approved/ → Done/

Usage:
    python test_single_file_lifecycle.py
"""

import sys
from pathlib import Path
from datetime import datetime
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from skills.process_email import process_email
from skills.create_approval_request import create_approval_request
from skills.move_to_done import move_to_done

# Test vault path
VAULT_PATH = Path('D:/Hackathon-0/AI_Employee_Vault')


def create_test_email() -> Path:
    """Create a test email file in Needs_Action/."""
    needs_action_dir = VAULT_PATH / 'Needs_Action'
    needs_action_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    email_file = needs_action_dir / f'TEST_EMAIL_{timestamp}.md'
    
    content = f"""---
type: email
from: "Test Client <client@example.com>"
subject: Test Invoice Request
received: {datetime.now().isoformat()}
priority: high
status: pending
gmail_id: TEST_{timestamp}
---

## Email Content

Hi,

Can you please send me the invoice for January 2026?

Thanks,
Test Client
"""
    
    email_file.write_text(content, encoding='utf-8')
    print(f"✅ Created test email: {email_file.name}")
    return email_file


def test_email_lifecycle():
    """Test the complete email lifecycle."""
    print("\n" + "="*60)
    print("SINGLE-FILE LIFECYCLE TEST: Email Processing")
    print("="*60)
    
    # Step 1: Create test email
    print("\n📥 STEP 1: Email detected")
    email_file = create_test_email()
    print(f"   Location: Needs_Action/{email_file.name}")
    
    # Step 2: Process email (creates plan, moves to Plans/)
    print("\n📋 STEP 2: Processing email (creating plan)")
    result = process_email(
        file_path=str(email_file),
        vault_path=str(VAULT_PATH)
    )
    
    if result['success']:
        print(f"   ✅ Email processed successfully")
        print(f"   Current location: {result.get('current_file', 'Unknown')}")
        print(f"   Previous location: {result.get('previous_location', 'Unknown')}")
        print(f"   Requires approval: {result.get('requires_approval', False)}")
        
        # Show file content
        current_file = Path(result['current_file'])
        if current_file.exists():
            content = current_file.read_text(encoding='utf-8')
            print(f"\n   📄 File content preview:")
            print("   " + "-"*50)
            for i, line in enumerate(content.split('\n')[:30]):
                print(f"   {line}")
            print("   " + "-"*50)
    else:
        print(f"   ❌ Processing failed: {result.get('error')}")
        return
    
    # Step 3: Show final state
    print("\n📊 STEP 3: Final State")
    print("-"*60)
    
    folders = ['Needs_Action', 'Plans', 'Pending_Approval', 'Approved', 'Done']
    for folder in folders:
        folder_path = VAULT_PATH / folder
        if folder_path.exists():
            # Look for files with TEST_EMAIL in name
            test_files = [f for f in folder_path.iterdir() if f.is_file() and 'TEST_EMAIL' in f.name]
            if test_files:
                print(f"   📁 {folder}/:")
                for f in test_files:
                    print(f"      - {f.name}")
            else:
                print(f"   📁 {folder}/: (no test files)")
        else:
            print(f"   📁 {folder}/: (folder doesn't exist)")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    print("\n✅ Expected behavior:")
    print("   - ONE file created in Needs_Action/")
    print("   - SAME file moved to Plans/ (with Action Plan section added)")
    print("   - SAME file moved to Pending_Approval/ (with Approval section added)")
    print("   - NO separate PLAN_*.md or APPROVAL_*.md files created")
    print("\n📝 To approve and complete:")
    print("   1. Move the file from Pending_Approval/ to Approved/")
    print("   2. Orchestrator will execute and move to Done/")


def test_generic_file_lifecycle():
    """Test the generic file lifecycle."""
    print("\n" + "="*60)
    print("SINGLE-FILE LIFECYCLE TEST: Generic File Processing")
    print("="*60)
    
    # Create test file
    needs_action_dir = VAULT_PATH / 'Needs_Action'
    needs_action_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    test_file = needs_action_dir / f'TEST_FILE_{timestamp}.md'
    
    content = f"""---
type: file_drop
original_name: document.pdf
size: 12345
created: {datetime.now().isoformat()}
status: pending
---

## File Drop

A new file was dropped for processing.

Please review and take appropriate action.
"""
    
    test_file.write_text(content, encoding='utf-8')
    print(f"✅ Created test file: {test_file.name}")
    
    # Process using orchestrator's _process_generic_file logic
    from src.orchestration.orchestrator import Orchestrator, OrchestratorConfig
    
    config = OrchestratorConfig(vault_path=str(VAULT_PATH))
    orchestrator = Orchestrator(config)
    
    print("\n📋 Processing file...")
    orchestrator._process_generic_file(test_file)
    
    # Show final state
    print("\n📊 Final State:")
    print("-"*60)
    
    folders = ['Needs_Action', 'Plans', 'Pending_Approval', 'Approved', 'Done']
    for folder in folders:
        folder_path = VAULT_PATH / folder
        if folder_path.exists():
            test_files = [f for f in folder_path.iterdir() if f.is_file() and 'TEST_FILE' in f.name]
            if test_files:
                print(f"   📁 {folder}/:")
                for f in test_files:
                    print(f"      - {f.name}")
            else:
                print(f"   📁 {folder}/: (no test files)")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)


def cleanup_test_files():
    """Remove all test files from vault."""
    print("\n🧹 Cleaning up test files...")
    
    folders = ['Needs_Action', 'Plans', 'Pending_Approval', 'Approved', 'Done']
    for folder in folders:
        folder_path = VAULT_PATH / folder
        if folder_path.exists():
            for f in folder_path.iterdir():
                if f.is_file() and 'TEST_' in f.name:
                    f.unlink()
                    print(f"   Deleted: {folder}/{f.name}")
    
    print("✅ Cleanup complete")


def main():
    """Main test runner."""
    print("\n" + "="*60)
    print("SINGLE-FILE LIFECYCLE TEST SUITE")
    print("="*60)
    
    try:
        # Test 1: Email lifecycle
        test_email_lifecycle()
        
        # Optional: Test 2: Generic file lifecycle
        # test_generic_file_lifecycle()
        
        print("\n✅ All tests completed!")
        print("\n📝 Next steps:")
        print("   - Review the file in Pending_Approval/")
        print("   - Move it to Approved/ to trigger execution")
        print("   - Check Done/ folder after execution")
        print("   - Run cleanup with: python test_single_file_lifecycle.py --cleanup")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    # Ask for cleanup
    print("\n" + "-"*60)
    response = input("\nClean up test files? (y/n): ").strip().lower()
    if response == 'y':
        cleanup_test_files()


if __name__ == '__main__':
    main()
