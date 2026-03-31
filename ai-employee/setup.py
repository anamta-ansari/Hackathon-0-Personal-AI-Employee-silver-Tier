"""
AI Employee - First-Time Setup Script
Helps configure .env file and verify installation
"""

import os
import shutil
from pathlib import Path


def main():
    print("="*70)
    print("AI EMPLOYEE - FIRST-TIME SETUP")
    print("="*70)
    print()
    
    project_root = Path(__file__).parent
    
    # Step 1: Create .env from example
    print("📝 Step 1: Environment Configuration")
    print("-" * 70)
    
    env_file = project_root / '.env'
    env_example = project_root / '.env.example'
    
    if env_file.exists():
        print(f"✓ .env file already exists: {env_file}")
        overwrite = input("\n  Overwrite with template? (y/N): ").lower()
        if overwrite != 'y':
            print("  Skipping .env creation")
        else:
            shutil.copy(env_example, env_file)
            print(f"✓ Created .env from template")
    else:
        shutil.copy(env_example, env_file)
        print(f"✓ Created .env file: {env_file}")
    
    print("\n⚠️  IMPORTANT: Edit .env and add your credentials:")
    print(f"   {env_file}")
    print()
    
    # Step 2: Create vault directories
    print("📁 Step 2: Vault Directory Structure")
    print("-" * 70)
    
    vault_path = project_root.parent / 'AI_Employee_Vault'
    
    folders = [
        'Needs_Action',
        'Plans',
        'Pending_Approval',
        'Approved',
        'Done',
        'Failed',
        'Rejected'
    ]
    
    vault_path.mkdir(exist_ok=True)
    print(f"✓ Created vault: {vault_path}")
    
    for folder in folders:
        folder_path = vault_path / folder
        folder_path.mkdir(exist_ok=True)
        print(f"  ✓ {folder}/")
    
    print()
    
    # Step 3: Create config directory
    print("⚙️  Step 3: Configuration Directory")
    print("-" * 70)
    
    config_dir = project_root / 'config'
    config_dir.mkdir(exist_ok=True)
    print(f"✓ Created config directory: {config_dir}")
    print()
    
    # Step 4: Create logs directory
    print("📋 Step 4: Logs Directory")
    print("-" * 70)
    
    logs_dir = project_root / 'logs'
    logs_dir.mkdir(exist_ok=True)
    print(f"✓ Created logs directory: {logs_dir}")
    print()
    
    # Step 5: Verify installations
    print("🔍 Step 5: Verify Dependencies")
    print("-" * 70)
    
    try:
        import playwright
        print("✓ Playwright installed")
    except ImportError:
        print("❌ Playwright not installed")
        print("   Run: pip install playwright")
    
    try:
        from dotenv import load_dotenv
        print("✓ python-dotenv installed")
    except ImportError:
        print("❌ python-dotenv not installed")
        print("   Run: pip install python-dotenv")
    
    try:
        import yaml
        print("✓ PyYAML installed")
    except ImportError:
        print("❌ PyYAML not installed")
        print("   Run: pip install PyYAML")
    
    try:
        import watchdog
        print("✓ Watchdog installed")
    except ImportError:
        print("❌ Watchdog not installed")
        print("   Run: pip install watchdog")
    
    print()
    
    # Final instructions
    print("="*70)
    print("✅ SETUP COMPLETE!")
    print("="*70)
    print()
    print("NEXT STEPS:")
    print()
    print("1. Edit .env file and add your credentials:")
    print(f"   {env_file}")
    print()
    print("2. Authenticate with LinkedIn:")
    print("   python src/skills/linkedin_session_auth.py login")
    print()
    print("3. Start the orchestrator:")
    print("   python src/orchestration/orchestrator.py")
    print()
    print("For detailed instructions, see README.md")
    print("="*70)


if __name__ == "__main__":
    main()
