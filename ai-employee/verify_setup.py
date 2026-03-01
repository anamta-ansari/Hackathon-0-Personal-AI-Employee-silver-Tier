"""
Setup Verification Script

Run this script to verify that your AI Employee system is properly configured.

Usage:
    python verify_setup.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime


def check_python_version():
    """Check Python version."""
    print("=" * 50)
    print("Checking Python Version...")
    print("=" * 50)
    
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print("[FAIL] Python 3.10+ required (3.13+ recommended)")
        return False
    else:
        print("[PASS] Python version is compatible")
        return True


def check_dependencies():
    """Check required dependencies."""
    print("\n" + "=" * 50)
    print("Checking Dependencies...")
    print("=" * 50)
    
    required = {
        'google.oauth2.credentials': 'google-auth-oauthlib',
        'googleapiclient.discovery': 'google-api-python-client',
        'watchdog.observers': 'watchdog',
        'pytest': 'pytest',
    }
    
    all_installed = True
    
    for module, package in required.items():
        try:
            __import__(module)
            print(f"[OK] {package}")
        except ImportError:
            print(f"[MISSING] {package}")
            all_installed = False
    
    if not all_installed:
        print("\nRun: pip install -r requirements.txt")
    
    return all_installed


def check_vault_structure():
    """Check Obsidian vault structure."""
    print("\n" + "=" * 50)
    print("Checking Vault Structure...")
    print("=" * 50)
    
    vault_path = Path(os.getenv('OBSIDIAN_VAULT_PATH', 'D:\\Hackathon-0\\AI_Employee_Vault'))
    
    if not vault_path.exists():
        print(f"[FAIL] Vault not found at: {vault_path}")
        return False
    
    print(f"Vault location: {vault_path}")
    
    required_folders = [
        'Inbox',
        'Needs_Action',
        'Plans',
        'Done',
        'Pending_Approval',
        'Approved',
        'Rejected',
        'Logs',
        'Briefings',
        'Accounting'
    ]
    
    required_files = [
        'Dashboard.md',
        'Company_Handbook.md',
        'Business_Goals.md'
    ]
    
    all_exist = True
    
    print("\nFolders:")
    for folder in required_folders:
        folder_path = vault_path / folder
        if folder_path.exists():
            print(f"  [OK] /{folder}")
        else:
            print(f"  [MISSING] /{folder}")
            all_exist = False
    
    print("\nCore Files:")
    for file in required_files:
        file_path = vault_path / file
        if file_path.exists():
            print(f"  [OK] {file}")
        else:
            print(f"  [MISSING] {file}")
            all_exist = False
    
    return all_exist


def check_source_files():
    """Check source file structure."""
    print("\n" + "=" * 50)
    print("Checking Source Files...")
    print("=" * 50)
    
    base = Path(__file__).parent
    
    required_files = [
        'src/watchers/base_watcher.py',
        'src/watchers/gmail_watcher.py',
        'src/watchers/filesystem_watcher.py',
        'src/skills/process_email.py',
        'src/skills/update_dashboard.py',
        'src/skills/log_action.py',
        'src/skills/create_approval_request.py',
        'src/skills/move_to_done.py',
        'src/orchestration/orchestrator.py',
        'tests/test_ai_employee.py',
        'SPECIFICATIONS.md',
        'README.md',
        'requirements.txt',
        '.env.example',
    ]
    
    all_exist = True
    
    for file in required_files:
        file_path = base / file
        if file_path.exists():
            print(f"  [OK] {file}")
        else:
            print(f"  [MISSING] {file}")
            all_exist = False
    
    return all_exist


def check_env_file():
    """Check environment file."""
    print("\n" + "=" * 50)
    print("Checking Environment Configuration...")
    print("=" * 50)
    
    env_file = Path(__file__).parent / '.env'
    
    if not env_file.exists():
        print("[FAIL] .env file not found")
        print("   Run: copy .env.example .env (Windows)")
        print("   Or:  cp .env.example .env (Linux/Mac)")
        return False
    
    print("[OK] .env file exists")
    
    # Check for required variables
    content = env_file.read_text()
    
    required_vars = [
        'OBSIDIAN_VAULT_PATH',
        'ENABLE_FILESYSTEM_WATCHER',
        'ORCHESTRATOR_CHECK_INTERVAL'
    ]
    
    print("\nEnvironment Variables:")
    for var in required_vars:
        if var in content:
            print(f"  [OK] {var}")
        else:
            print(f"  [MISSING] {var}")
    
    return True


def check_imports():
    """Test that all modules can be imported."""
    print("\n" + "=" * 50)
    print("Testing Module Imports...")
    print("=" * 50)
    
    import sys
    sys.path.insert(0, str(Path(__file__).parent / 'src'))
    
    modules = [
        ('watchers.base_watcher', 'BaseWatcher'),
        ('watchers.filesystem_watcher', 'FilesystemWatcher'),
        ('skills.process_email', 'process_email'),
        ('skills.update_dashboard', 'update_dashboard'),
        ('skills.log_action', 'log_action'),
        ('orchestration.orchestrator', 'Orchestrator'),
    ]
    
    all_import = True
    
    for module, name in modules:
        try:
            mod = __import__(module, fromlist=[name])
            getattr(mod, name)
            print(f"  [OK] {module}.{name}")
        except Exception as e:
            print(f"  [FAIL] {module}.{name} - {e}")
            all_import = False
    
    return all_import


def run_quick_test():
    """Run a quick functional test."""
    print("\n" + "=" * 50)
    print("Running Quick Functional Test...")
    print("=" * 50)
    
    import sys
    sys.path.insert(0, str(Path(__file__).parent / 'src'))
    
    try:
        from skills.update_dashboard import update_dashboard
        from skills.log_action import log_action
        
        vault_path = os.getenv('OBSIDIAN_VAULT_PATH', 'D:\\Hackathon-0\\AI_Employee_Vault')
        
        # Test dashboard update
        print("Testing dashboard update...")
        result = update_dashboard(vault_path)
        if result['success']:
            print("  [OK] Dashboard update works")
        else:
            print(f"  [FAIL] Dashboard update failed: {result.get('error')}")
            return False
        
        # Test logging
        print("Testing audit logging...")
        entry = log_action(
            vault_path=vault_path,
            action_type='verification_test',
            actor='verify_setup',
            target='system',
            result='success'
        )
        print(f"  [OK] Audit logging works (entry: {entry.timestamp})")
        
        return True
        
    except Exception as e:
        print(f"  [FAIL] Functional test failed: {e}")
        return False


def main():
    """Run all verification checks."""
    print("\n")
    print("+" + "=" * 48 + "+")
    print("|" + " " * 10 + "AI Employee Setup Verification" + " " * 10 + "|")
    print("+" + "=" * 48 + "+")
    print()
    
    results = []
    
    # Run checks
    results.append(("Python Version", check_python_version()))
    results.append(("Dependencies", check_dependencies()))
    results.append(("Vault Structure", check_vault_structure()))
    results.append(("Source Files", check_source_files()))
    results.append(("Environment", check_env_file()))
    results.append(("Module Imports", check_imports()))
    results.append(("Functional Test", run_quick_test()))
    
    # Summary
    print("\n" + "=" * 50)
    print("VERIFICATION SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {name}")
    
    print()
    print(f"Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("\nSUCCESS! Your AI Employee system is ready to run!")
        print("\nStart the orchestrator with:")
        print("  python src/orchestration/orchestrator.py --dry-run")
    else:
        print("\nSome checks failed. Please fix the issues above before running.")
        print("\nQuick fix commands:")
        print("  pip install -r requirements.txt")
        print("  copy .env.example .env")
        print("  python src/orchestration/orchestrator.py --dry-run")
    
    print()
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
