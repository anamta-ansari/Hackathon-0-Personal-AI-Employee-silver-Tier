"""
Configuration Loader - Load settings from environment variables

This module provides a centralized way to load configuration from .env files
using python-dotenv. All sensitive credentials are loaded from environment
variables instead of being hardcoded.

Usage:
    from src.config_loader import Config
    
    # Access configuration
    vault_path = Config.VAULT_PATH
    linkedin_token = Config.LINKEDIN_SESSION_TOKEN
    
    # Validate configuration
    errors = Config.validate()
    if errors:
        print("Configuration errors:", errors)
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
project_root = Path(__file__).parent.parent
env_path = project_root / '.env'

if env_path.exists():
    load_dotenv(env_path)
    print(f"✓ Loaded environment from: {env_path}")
else:
    print(f"⚠️  No .env file found at: {env_path}")
    print("   Using environment variables or defaults")


class Config:
    """Configuration loaded from environment variables"""
    
    # Project
    PROJECT_NAME = os.getenv('PROJECT_NAME', 'ai-employee')
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Paths
    PROJECT_ROOT = project_root
    VAULT_PATH = Path(os.getenv('VAULT_PATH', project_root.parent / 'AI_Employee_Vault'))
    CONFIG_DIR = project_root / 'config'
    LOGS_DIR = project_root / 'logs'
    
    # LinkedIn
    LINKEDIN_SESSION_TOKEN = os.getenv('LINKEDIN_SESSION_TOKEN', '')
    LINKEDIN_COOKIE_DOMAIN = os.getenv('LINKEDIN_COOKIE_DOMAIN', '.linkedin.com')
    
    # Gmail OAuth
    GMAIL_CLIENT_ID = os.getenv('GMAIL_CLIENT_ID', '')
    GMAIL_CLIENT_SECRET = os.getenv('GMAIL_CLIENT_SECRET', '')
    GMAIL_PROJECT_ID = os.getenv('GMAIL_PROJECT_ID', '')
    GMAIL_ACCESS_TOKEN = os.getenv('GMAIL_ACCESS_TOKEN', '')
    GMAIL_REFRESH_TOKEN = os.getenv('GMAIL_REFRESH_TOKEN', '')
    
    # Browser
    BROWSER_HEADLESS = os.getenv('BROWSER_HEADLESS', 'False').lower() == 'true'
    BROWSER_TIMEOUT = int(os.getenv('BROWSER_TIMEOUT', '90000'))
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/orchestrator.log')
    
    # Orchestration
    CYCLE_INTERVAL = int(os.getenv('CYCLE_INTERVAL', '30'))
    AUTO_EXECUTE = os.getenv('AUTO_EXECUTE', 'True').lower() == 'true'
    
    
    @classmethod
    def get_linkedin_session_json(cls):
        """Generate LinkedIn session JSON from environment"""
        if not cls.LINKEDIN_SESSION_TOKEN:
            return None
            
        return {
            "cookies": [
                {
                    "name": "li_at",
                    "value": cls.LINKEDIN_SESSION_TOKEN,
                    "domain": cls.LINKEDIN_COOKIE_DOMAIN,
                    "path": "/",
                    "httpOnly": True,
                    "secure": True
                }
            ]
        }
    
    
    @classmethod
    def get_gmail_credentials_json(cls):
        """Generate Gmail credentials JSON from environment"""
        if not cls.GMAIL_CLIENT_ID or not cls.GMAIL_CLIENT_SECRET:
            return None
            
        return {
            "installed": {
                "client_id": cls.GMAIL_CLIENT_ID,
                "project_id": cls.GMAIL_PROJECT_ID,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": cls.GMAIL_CLIENT_SECRET,
                "redirect_uris": ["http://localhost"]
            }
        }
    
    
    @classmethod
    def save_credentials_to_files(cls):
        """Save credentials from .env to config files (for compatibility)"""
        
        cls.CONFIG_DIR.mkdir(exist_ok=True)
        
        # LinkedIn session
        linkedin_session = cls.get_linkedin_session_json()
        if linkedin_session:
            session_file = cls.CONFIG_DIR / 'linkedin_session.json'
            with open(session_file, 'w') as f:
                json.dump(linkedin_session, f, indent=2)
            print(f"✓ Saved LinkedIn session to: {session_file}")
        
        # Gmail credentials
        gmail_creds = cls.get_gmail_credentials_json()
        if gmail_creds:
            creds_file = cls.CONFIG_DIR / 'gmail_credentials.json'
            with open(creds_file, 'w') as f:
                json.dump(gmail_creds, f, indent=2)
            print(f"✓ Saved Gmail credentials to: {creds_file}")
    
    
    @classmethod
    def validate(cls):
        """Validate critical configuration"""
        errors = []
        
        if not cls.LINKEDIN_SESSION_TOKEN:
            errors.append("❌ LINKEDIN_SESSION_TOKEN not set in .env")
        
        if not cls.GMAIL_CLIENT_ID or not cls.GMAIL_CLIENT_SECRET:
            errors.append("❌ Gmail OAuth credentials not set in .env")
        
        if not cls.VAULT_PATH.exists():
            errors.append(f"❌ Vault path does not exist: {cls.VAULT_PATH}")
        
        return errors


# Auto-validate on import
if __name__ == "__main__":
    print("\n" + "="*60)
    print("CONFIGURATION VALIDATION")
    print("="*60 + "\n")
    
    errors = Config.validate()
    
    if errors:
        print("Configuration errors found:\n")
        for error in errors:
            print(error)
        print("\nPlease update your .env file")
    else:
        print("✅ All configuration valid!")
        print(f"\n📁 Vault path: {Config.VAULT_PATH}")
        print(f"🔧 Debug mode: {Config.DEBUG}")
        print(f"⏱️  Cycle interval: {Config.CYCLE_INTERVAL}s")
    
    print("\n" + "="*60)
