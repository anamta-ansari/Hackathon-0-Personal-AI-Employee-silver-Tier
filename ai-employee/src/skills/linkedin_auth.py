"""
LinkedIn Authentication Management for AI Employee - Silver Tier

This skill handles authentication with LinkedIn using the linkedin-api library.
It manages credential storage, validation, and provides authenticated LinkedIn instances.

Silver Tier Requirement: LinkedIn auto-posting authentication

Usage:
    python src/skills/linkedin_auth.py auth     # Set up credentials
    python src/skills/linkedin_auth.py test     # Test credentials
    python src/skills/linkedin_auth.py status   # Check status
    python src/skills/linkedin_auth.py revoke   # Remove credentials
"""

import os
import sys
import json
import logging
import getpass
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Environment variable for vault path
DEFAULT_VAULT_PATH = os.getenv('VAULT_PATH', 'D:/Hackathon-0/AI_Employee_Vault')

# LinkedIn API dependency
try:
    from linkedin_api import Linkedin
    LINKEDIN_API_AVAILABLE = True
except ImportError:
    LINKEDIN_API_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("linkedin-api not installed. Run: pip install linkedin-api")

# python-dotenv for .env file management
try:
    from dotenv import load_dotenv, set_key, find_dotenv, unset_key
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("python-dotenv not installed. Run: pip install python-dotenv")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LinkedInAuthManager:
    """
    LinkedIn Authentication Manager

    Handles credential storage, validation, and authentication with LinkedIn.
    Uses .env file for secure credential storage.
    """

    def __init__(self, vault_path: Optional[str] = None):
        """
        Initialize LinkedIn Authentication Manager

        Args:
            vault_path: Path to Obsidian vault (for logging)
        """
        # Resolve paths
        self.vault_path = Path(vault_path) if vault_path else Path(DEFAULT_VAULT_PATH)
        self.project_root = Path(__file__).parent.parent.parent
        
        # .env file location (in project root)
        self.env_file = self.project_root / '.env'
        
        # Ensure .env file exists
        if not self.env_file.exists():
            self._create_env_file()
        
        # Load environment variables
        if DOTENV_AVAILABLE:
            load_dotenv(self.env_file)
        
        # Auth state
        self.api: Optional[Linkedin] = None
        self.is_authenticated = False
        self.email: Optional[str] = None
        
        # Ensure logging directory exists
        self.logs_dir = self.vault_path / 'Logs'
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"LinkedInAuthManager initialized")
        logger.info(f"Vault path: {self.vault_path}")
        logger.info(f"Env file: {self.env_file}")

    def _create_env_file(self) -> None:
        """Create empty .env file if it doesn't exist"""
        try:
            self.env_file.parent.mkdir(parents=True, exist_ok=True)
            self.env_file.touch(exist_ok=True)
            logger.info(f"Created empty .env file: {self.env_file}")
        except Exception as e:
            logger.error(f"Error creating .env file: {e}")

    def _env_file_exists(self) -> bool:
        """Check if .env file exists"""
        return self.env_file.exists()

    def _credentials_in_env(self) -> bool:
        """Check if LinkedIn credentials exist in .env file"""
        email = os.getenv('LINKEDIN_EMAIL')
        password = os.getenv('LINKEDIN_PASSWORD')
        return bool(email and password)

    def _get_credentials_from_env(self) -> tuple:
        """
        Get credentials from environment variables
        
        Returns:
            tuple: (email, password) or (None, None) if not found
        """
        email = os.getenv('LINKEDIN_EMAIL')
        password = os.getenv('LINKEDIN_PASSWORD')
        return email, password

    def authenticate(self, email: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        Authenticate with LinkedIn
        
        Args:
            email: LinkedIn email (optional, will prompt if not provided)
            password: LinkedIn password (optional, will prompt if not provided)
            
        Returns:
            bool: True if authentication successful
        """
        if not LINKEDIN_API_AVAILABLE:
            logger.error("linkedin-api library not installed")
            logger.error("Install with: pip install linkedin-api")
            return False
        
        # Get credentials
        if not email or not password:
            # Try to load from .env first
            env_email, env_password = self._get_credentials_from_env()
            if env_email and env_password:
                email = env_email
                password = env_password
                logger.info("Using credentials from .env file")
            else:
                # Prompt user for credentials
                logger.info("LinkedIn credentials not found in .env file")
                email = input("Enter LinkedIn email: ").strip()
                password = getpass.getpass("Enter LinkedIn password: ")
        
        if not email or not password:
            logger.error("Email and password are required")
            return False
        
        try:
            # Attempt authentication
            logger.info(f"Authenticating with LinkedIn: {email}")
            self.api = Linkedin(email, password)
            
            # Test connection by getting profile
            profile = self.api.get_profile()
            
            if profile:
                self.is_authenticated = True
                self.email = email
                
                # Save credentials to .env if not already saved
                if not self._credentials_in_env():
                    self.save_credentials(email, password)
                
                logger.info("LinkedIn authentication successful!")
                logger.info(f"Logged in as: {email}")
                
                # Log success
                self.log_auth_event('authentication_success', {'email': email})
                
                return True
            else:
                logger.error("Authentication failed - no profile returned")
                return False
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"LinkedIn authentication failed: {error_msg}")
            
            # Provide helpful error messages
            if "401" in error_msg or "Unauthorized" in error_msg:
                logger.error("Invalid email or password")
            elif "403" in error_msg:
                logger.error("Access forbidden - account may be restricted")
            elif "429" in error_msg:
                logger.error("Rate limit exceeded - try again later")
            elif "Could not authenticate" in error_msg:
                logger.error("Could not authenticate with LinkedIn")
                logger.error("This may be due to LinkedIn's security measures")
                logger.error("Try again later or check if your account is in good standing")
            
            # Log failure
            self.log_auth_event('authentication_failed', {'email': email, 'error': error_msg})
            
            self.is_authenticated = False
            self.api = None
            return False

    def test_credentials(self) -> Dict[str, Any]:
        """
        Test existing credentials in .env file
        
        Returns:
            dict: Test results
        """
        result = {
            'success': False,
            'authenticated': False,
            'email': None,
            'credentials_exist': False,
            'error': None
        }
        
        # Check if .env file exists
        if not self._env_file_exists():
            result['error'] = '.env file not found'
            return result
        
        # Check if credentials exist in .env
        email, password = self._get_credentials_from_env()
        if not email or not password:
            result['error'] = 'LinkedIn credentials not found in .env file'
            result['credentials_exist'] = False
            return result
        
        result['credentials_exist'] = True
        result['email'] = email
        
        # Try to authenticate
        if not LINKEDIN_API_AVAILABLE:
            result['error'] = 'linkedin-api library not installed'
            return result
        
        try:
            api = Linkedin(email, password)
            profile = api.get_profile()
            
            if profile:
                result['success'] = True
                result['authenticated'] = True
                logger.info(f"Credentials test successful: {email}")
            else:
                result['error'] = 'Authentication returned no profile'
                
        except Exception as e:
            result['error'] = f'Authentication failed: {str(e)}'
            logger.error(result['error'])
        
        return result

    def check_status(self) -> Dict[str, Any]:
        """
        Check current authentication status
        
        Returns:
            dict: Status information
        """
        status = {
            'authenticated': self.is_authenticated,
            'env_file_exists': self._env_file_exists(),
            'credentials_in_env': self._credentials_in_env(),
            'email': self.email,
            'api_available': LINKEDIN_API_AVAILABLE,
            'dotenv_available': DOTENV_AVAILABLE
        }
        
        # Get masked email if credentials exist
        if status['credentials_in_env']:
            email, _ = self._get_credentials_from_env()
            if email:
                # Mask email for security (e.g., j***@example.com)
                parts = email.split('@')
                if len(parts) == 2:
                    masked = f"{parts[0][0]}***@{parts[1]}"
                    status['email'] = masked
        
        return status

    def save_credentials(self, email: str, password: str) -> bool:
        """
        Save credentials to .env file
        
        Args:
            email: LinkedIn email
            password: LinkedIn password
            
        Returns:
            bool: True if saved successfully
        """
        if not DOTENV_AVAILABLE:
            logger.error("python-dotenv not available")
            return False
        
        try:
            # Ensure .env file exists
            if not self._env_file_exists():
                self._create_env_file()
            
            # Set credentials in .env file
            set_key(str(self.env_file), 'LINKEDIN_EMAIL', email)
            set_key(str(self.env_file), 'LINKEDIN_PASSWORD', password)
            
            # Reload environment to pick up changes
            load_dotenv(self.env_file)
            
            logger.info(f"Credentials saved to: {self.env_file}")
            logger.info("⚠️  SECURITY NOTE: Credentials are stored in plain text in .env file")
            logger.info("   Keep this file secure and never commit it to version control")
            
            # Log the event
            self.log_auth_event('credentials_saved', {'email': email})
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving credentials: {e}")
            self.log_auth_event('credentials_save_failed', {'email': email, 'error': str(e)})
            return False

    def revoke_credentials(self) -> bool:
        """
        Remove credentials from .env file
        
        Returns:
            bool: True if revoked successfully
        """
        if not DOTENV_AVAILABLE:
            logger.error("python-dotenv not available")
            return False
        
        try:
            # Remove credentials from .env
            unset_key(str(self.env_file), 'LINKEDIN_EMAIL')
            unset_key(str(self.env_file), 'LINKEDIN_PASSWORD')
            
            # Reload environment
            load_dotenv(self.env_file)
            
            # Reset auth state
            self.api = None
            self.is_authenticated = False
            self.email = None
            
            logger.info("LinkedIn credentials removed from .env file")
            
            # Log the event
            self.log_auth_event('credentials_revoked', {})
            
            return True
            
        except Exception as e:
            logger.error(f"Error revoking credentials: {e}")
            return False

    def get_api(self) -> Optional[Linkedin]:
        """
        Get authenticated LinkedIn API instance
        
        Returns:
            Linkedin API instance or None if not authenticated
        """
        if not self.is_authenticated or not self.api:
            if not self.authenticate():
                return None
        return self.api

    def log_auth_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """
        Log authentication event to vault logs
        
        Args:
            event_type: Type of auth event
            details: Event details
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'actor': 'linkedin_auth',
            'details': details
        }
        
        log_file = self.logs_dir / f"linkedin_auth_{datetime.now().strftime('%Y-%m-%d')}.json"
        
        # Append to log file
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


# CLI interface for testing
if __name__ == '__main__':
    import argparse

    # Handle Windows console encoding
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

    parser = argparse.ArgumentParser(
        description='LinkedIn Authentication Management',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python src/skills/linkedin_auth.py auth     # Set up credentials
    python src/skills/linkedin_auth.py test     # Test existing credentials
    python src/skills/linkedin_auth.py status   # Check authentication status
    python src/skills/linkedin_auth.py revoke   # Remove credentials
        """
    )
    
    parser.add_argument(
        'command',
        nargs='?',
        default='status',
        choices=['auth', 'test', 'status', 'revoke'],
        help='Command to run'
    )
    
    parser.add_argument(
        '--vault',
        type=str,
        default=DEFAULT_VAULT_PATH,
        help='Path to Obsidian vault'
    )
    
    parser.add_argument(
        '--email',
        type=str,
        help='LinkedIn email (for auth command)'
    )
    
    parser.add_argument(
        '--password',
        type=str,
        help='LinkedIn password (for auth command, not recommended - use interactive prompt)'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("LinkedIn Authentication Management")
    print("=" * 60)
    print()

    # Initialize auth manager
    auth = LinkedInAuthManager(vault_path=args.vault)

    if args.command == 'status':
        print("Authentication Status:")
        print("-" * 40)
        status = auth.check_status()
        
        for key, value in status.items():
            key_display = key.replace('_', ' ').title()
            if value is True:
                print(f"  ✓ {key_display}: Yes")
            elif value is False:
                print(f"  ✗ {key_display}: No")
            else:
                print(f"  • {key_display}: {value}")
        
        print()
        if status['authenticated']:
            print("Status: ✓ AUTHENTICATED")
        elif status['credentials_in_env']:
            print("Status: ⚠ Credentials saved but not authenticated")
            print("        Run 'test' command to verify credentials")
        else:
            print("Status: ✗ NOT AUTHENTICATED")
            print("        Run 'auth' command to set up credentials")
        
        # Show next steps
        print()
        print("Next Steps:")
        if not status['credentials_in_env']:
            print("  1. Run: python src/skills/linkedin_auth.py auth")
            print("  2. Enter your LinkedIn email and password")
            print("  3. Credentials will be saved to .env file")
        elif not status['authenticated']:
            print("  1. Run: python src/skills/linkedin_auth.py test")
            print("  2. Verify credentials work")
        else:
            print("  ✓ Authentication complete!")
            print("  ✓ You can now use LinkedIn posting features")

    elif args.command == 'auth':
        print("LinkedIn Authentication Setup")
        print("-" * 40)
        
        # Check if already authenticated
        if auth._credentials_in_env():
            email, _ = auth._get_credentials_from_env()
            print(f"Found existing credentials for: {email}")
            response = input("Overwrite existing credentials? (y/N): ").strip().lower()
            if response != 'y':
                print("Authentication cancelled")
                sys.exit(0)
        
        # Check dependencies
        if not LINKEDIN_API_AVAILABLE:
            print()
            print("ERROR: linkedin-api library not installed")
            print()
            print("Install with:")
            print("  pip install linkedin-api")
            print()
            sys.exit(1)
        
        if not DOTENV_AVAILABLE:
            print()
            print("ERROR: python-dotenv library not installed")
            print()
            print("Install with:")
            print("  pip install python-dotenv")
            print()
            sys.exit(1)
        
        # Perform authentication
        print()
        print("Enter your LinkedIn credentials:")
        print("(Credentials will be saved to .env file)")
        print()
        
        success = auth.authenticate(
            email=args.email,
            password=args.password
        )
        
        print()
        if success:
            print("=" * 60)
            print("✓ AUTHENTICATION SUCCESSFUL")
            print("=" * 60)
            print()
            print(f"Logged in as: {auth.email}")
            print("Credentials saved to: " + str(auth.env_file))
            print()
            print("You can now use LinkedIn posting features:")
            print("  python src/skills/linkedin_post.py --generate weekly_update")
        else:
            print("=" * 60)
            print("✗ AUTHENTICATION FAILED")
            print("=" * 60)
            print()
            print("Possible reasons:")
            print("  • Incorrect email or password")
            print("  • LinkedIn security measures (try again later)")
            print("  • Network connectivity issues")
            print("  • Account restrictions")
            print()
            print("Troubleshooting:")
            print("  1. Verify your credentials are correct")
            print("  2. Try logging into LinkedIn.com in a browser")
            print("  3. Wait a few minutes and try again")
            print("  4. Check if your account is in good standing")
            sys.exit(1)

    elif args.command == 'test':
        print("Testing LinkedIn Credentials")
        print("-" * 40)
        
        result = auth.test_credentials()
        
        print(f"  .env file exists: {'Yes' if result['env_file_exists'] else 'No'}")
        print(f"  Credentials saved: {'Yes' if result['credentials_exist'] else 'No'}")
        
        if result['credentials_exist']:
            print(f"  Email: {result['email']}")
            print()
            print("Testing authentication...")
            
            if result['success']:
                print()
                print("=" * 60)
                print("✓ CREDENTIALS TEST SUCCESSFUL")
                print("=" * 60)
                print()
                print("Your LinkedIn credentials are working correctly!")
                print("You can now use LinkedIn posting features.")
            else:
                print()
                print("=" * 60)
                print("✗ CREDENTIALS TEST FAILED")
                print("=" * 60)
                print()
                print(f"Error: {result['error']}")
                print()
                print("To fix this:")
                print("  1. Run: python src/skills/linkedin_auth.py auth")
                print("  2. Re-enter your credentials")
                sys.exit(1)
        else:
            print()
            print("=" * 60)
            print("✗ NO CREDENTIALS FOUND")
            print("=" * 60)
            print()
            print("To set up credentials:")
            print("  1. Run: python src/skills/linkedin_auth.py auth")
            print("  2. Enter your LinkedIn email and password")
            sys.exit(1)

    elif args.command == 'revoke':
        print("Revoking LinkedIn Credentials")
        print("-" * 40)
        
        if auth._credentials_in_env():
            email, _ = auth._get_credentials_from_env()
            print(f"Found credentials for: {email}")
            print()
            response = input("Remove these credentials? (y/N): ").strip().lower()
            
            if response == 'y':
                success = auth.revoke_credentials()
                print()
                if success:
                    print("=" * 60)
                    print("✓ CREDENTIALS REMOVED")
                    print("=" * 60)
                    print()
                    print("LinkedIn credentials have been removed from .env file")
                    print("You will need to re-authenticate to use LinkedIn features")
                else:
                    print("=" * 60)
                    print("✗ REVOCATION FAILED")
                    print("=" * 60)
                    print()
                    print("Error removing credentials")
                    sys.exit(1)
            else:
                print("Revocation cancelled")
        else:
            print("No LinkedIn credentials found in .env file")
            print("Nothing to revoke")

    print()
    print("Done.")
