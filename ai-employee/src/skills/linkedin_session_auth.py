"""
LinkedIn Session Authentication - Browser-Based Authentication

This skill handles browser-based LinkedIn authentication using Playwright.
Instead of OAuth, it saves session cookies from a manual browser login.

How it works:
1. Browser opens (Chromium)
2. User logs into LinkedIn manually (email/password/2FA)
3. Session cookies are saved to config/linkedin_session.json
4. Future automation reuses the saved session

Advantages:
- No LinkedIn Developer App needed
- No CLIENT_ID/SECRET needed
- No approval waiting
- Works immediately

Usage:
    python src/skills/linkedin_session_auth.py login   # Login and save session
    python src/skills/linkedin_session_auth.py test    # Test if session valid
    python src/skills/linkedin_session_auth.py logout  # Clear saved session
    python src/skills/linkedin_session_auth.py status  # Check session status
"""

import os
import sys
import json
import logging
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# Playwright imports
try:
    from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
    # Try new stealth API first, fall back to old
    try:
        from playwright_stealth import stealth_sync
        stealth_sync  # Reference to avoid unused import warning
    except ImportError:
        from playwright_stealth import stealth as stealth_sync
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Playwright not installed. Run: pip install playwright playwright-stealth")

# Import config loader for environment variables
try:
    from ..config_loader import Config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Config loader not available - using file-based config")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LinkedInSessionAuth:
    """
    LinkedIn Session Authentication Manager

    Handles browser-based authentication with LinkedIn using session cookies.
    Supports both file-based and environment variable-based configuration.
    """

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize LinkedIn Session Authentication

        Args:
            config_dir: Path to config directory (default: project_root/config)
        """
        # Resolve paths
        self.project_root = Path(__file__).parent.parent.parent
        self.config_dir = Path(config_dir) if config_dir else self.project_root / 'config'
        
        # Try to load session from .env first (for security)
        if CONFIG_AVAILABLE and Config.LINKEDIN_SESSION_TOKEN:
            logger.info("✓ Found LinkedIn session in .env")
            # Save to file for compatibility with existing code
            self._save_session_from_env()
        
        # Session files
        self.session_file = self.config_dir / 'linkedin_session.json'
        self.storage_file = self.config_dir / 'linkedin_storage.json'
        self.profile_file = self.config_dir / 'linkedin_profile.json'
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Auth state
        self.is_authenticated: bool = False
        self.profile_data: Optional[Dict[str, Any]] = None
        
        # Browser state
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Ensure logging directory exists
        self.logs_dir = self.project_root / 'logs'
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"LinkedInSessionAuth initialized")
        logger.info(f"Config directory: {self.config_dir}")
        logger.info(f"Session file: {self.session_file}")

    def _save_session_from_env(self) -> bool:
        """
        Save session from .env environment variable to file
        
        Returns:
            True if saved successfully
        """
        if not CONFIG_AVAILABLE or not Config.LINKEDIN_SESSION_TOKEN:
            return False
        
        try:
            # Create session data from .env
            session_data = {
                'cookies': [
                    {
                        'name': 'li_at',
                        'value': Config.LINKEDIN_SESSION_TOKEN,
                        'domain': Config.LINKEDIN_COOKIE_DOMAIN,
                        'path': '/',
                        'httpOnly': True,
                        'secure': True
                    }
                ],
                'saved_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=30)).isoformat(),
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'source': '.env'
            }
            
            # Ensure config directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # Save session file
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2)
            
            # Create empty storage file if it doesn't exist
            if not self.storage_file.exists():
                with open(self.storage_file, 'w', encoding='utf-8') as f:
                    json.dump({}, f, indent=2)
            
            logger.info(f"✓ Saved LinkedIn session from .env to {self.session_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving session from .env: {e}")
            return False

    def _session_exists(self) -> bool:
        """Check if session files exist"""
        return self.session_file.exists() and self.storage_file.exists()

    def _load_session(self) -> Optional[Dict[str, Any]]:
        """
        Load saved session from disk

        Returns:
            Session data dict or None if not found
        """
        if not self.session_file.exists():
            return None
        
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # Validate session data
            if 'cookies' not in session_data:
                return None
            
            # Check if session has expired
            expires_at = session_data.get('expires_at')
            if expires_at:
                expires_dt = datetime.fromisoformat(expires_at)
                if datetime.now() > expires_dt:
                    logger.info("Session has expired")
                    return None
            
            logger.info(f"Loaded session from {self.session_file}")
            return session_data
            
        except Exception as e:
            logger.error(f"Error loading session: {e}")
            return None

    def _save_session(self, cookies: List[Dict[str, Any]], local_storage: Dict[str, Any]) -> bool:
        """
        Save session cookies and local storage to disk

        Args:
            cookies: Browser cookies
            local_storage: Local storage data

        Returns:
            True if saved successfully
        """
        try:
            # Get user agent from page navigator
            user_agent = None
            if self.page:
                try:
                    user_agent = self.page.evaluate('() => navigator.userAgent')
                except:
                    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

            # Create session data
            session_data = {
                'cookies': cookies,
                'saved_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=90)).isoformat(),  # 90 day expiry (was 30)
                'user_agent': user_agent,
            }

            # Save session file
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2)

            # Save storage file
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(local_storage, f, indent=2)

            logger.info(f"Session saved to {self.session_file}")
            logger.info(f"Storage saved to {self.storage_file}")

            # Log the event
            self._log_auth_event('session_saved', {'cookies_count': len(cookies)})

            return True

        except Exception as e:
            logger.error(f"Error saving session: {e}")
            self._log_auth_event('session_save_failed', {'error': str(e)})
            return False

    def _clear_session(self) -> bool:
        """
        Delete saved session files

        Returns:
            True if cleared successfully
        """
        try:
            if self.session_file.exists():
                self.session_file.unlink()
                logger.info(f"Deleted: {self.session_file}")
            
            if self.storage_file.exists():
                self.storage_file.unlink()
                logger.info(f"Deleted: {self.storage_file}")
            
            if self.profile_file.exists():
                self.profile_file.unlink()
                logger.info(f"Deleted: {self.profile_file}")
            
            self.is_authenticated = False
            self.profile_data = None
            
            logger.info("Session cleared successfully")
            self._log_auth_event('session_cleared', {})
            
            return True
            
        except Exception as e:
            logger.error(f"Error clearing session: {e}")
            return False

    def _apply_stealth(self, page: Page) -> None:
        """
        Apply stealth mode to avoid bot detection

        Args:
            page: Playwright page
        """
        try:
            # Use stealth context manager for new API
            from playwright_stealth import stealth
            stealth(page)
        except ImportError:
            try:
                from playwright_stealth import stealth_sync
                stealth_sync(page)
            except Exception as e:
                logger.debug(f"Stealth mode not available: {e}")
        except Exception as e:
            logger.debug(f"Stealth mode warning: {e}")

    def _wait_for_login(self, page: Page, timeout: int = 300) -> bool:
        """
        Wait for user to complete LinkedIn login

        Args:
            page: Playwright page
            timeout: Maximum wait time in seconds

        Returns:
            True if login detected
        """
        logger.info("Waiting for you to log into LinkedIn...")
        logger.info("(Browser window should be visible)")
        logger.info("Complete the login, then wait for automatic detection...")
        
        start_time = time.time()
        last_url = page.url
        
        while time.time() - start_time < timeout:
            try:
                current_url = page.url
                
                # Check if we're on the feed page (logged in)
                if 'linkedin.com/feed' in current_url:
                    logger.info("LinkedIn feed detected - login successful!")
                    return True
                
                # Check if we're on the homepage (logged in)
                if current_url == 'https://www.linkedin.com/' and last_url != current_url:
                    # Check for profile icon (indicates logged in)
                    try:
                        profile_icon = page.query_selector('[data-test-id="profile icon"]')
                        if profile_icon:
                            logger.info("Profile icon detected - logged in!")
                            return True
                    except:
                        pass
                
                # Check for "Start a post" box (only visible when logged in)
                try:
                    post_box = page.query_selector('[data-test-id="share-box-feed-entry"]')
                    if post_box:
                        logger.info("Post box detected - logged in!")
                        return True
                except:
                    pass
                
                last_url = current_url
                time.sleep(2)
                
            except Exception as e:
                logger.debug(f"Checking login status: {e}")
                time.sleep(2)
        
        logger.warning("Login timeout reached")
        return False

    def authenticate(self, headless: bool = False) -> bool:
        """
        Launch browser for manual LinkedIn login and save session

        Args:
            headless: If True, run browser without UI (not recommended for login)

        Returns:
            True if authentication successful
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright not installed")
            logger.error("Install with: pip install playwright playwright-stealth")
            logger.error("Then run: python -m playwright install chromium")
            return False
        
        logger.info("=" * 60)
        logger.info("LinkedIn Session Authentication")
        logger.info("=" * 60)
        logger.info("")
        
        try:
            with sync_playwright() as p:
                # Launch browser
                logger.info("Launching Chromium browser...")
                self.browser = p.chromium.launch(
                    headless=headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                    ]
                )
                
                # Create browser context
                self.context = self.browser.new_context(
                    viewport={'width': 1280, 'height': 800},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                # Create page
                self.page = self.context.new_page()
                
                # Apply stealth mode
                self._apply_stealth(self.page)
                
                # Navigate to LinkedIn
                logger.info("Navigating to LinkedIn.com...")
                self.page.goto('https://www.linkedin.com/login', wait_until='networkidle')
                
                # Wait for login
                if not headless:
                    login_success = self._wait_for_login(self.page, timeout=300)
                else:
                    logger.warning("Headless mode - cannot wait for manual login")
                    login_success = False
                
                if login_success:
                    # Get cookies
                    cookies = self.page.context.cookies()
                    
                    # Get local storage
                    local_storage = {}
                    try:
                        storage = self.page.evaluate('() => localStorage')
                        local_storage = {str(k): str(v) for k, v in storage.items()}
                    except Exception as e:
                        logger.debug(f"Could not get local storage: {e}")
                    
                    # Save session
                    if self._save_session(cookies, local_storage):
                        # Try to get profile info
                        self._capture_profile_info()
                        
                        logger.info("")
                        logger.info("=" * 60)
                        logger.info("✓ SESSION SAVED SUCCESSFULLY")
                        logger.info("=" * 60)
                        logger.info("")
                        logger.info(f"Session file: {self.session_file}")
                        logger.info(f"Storage file: {self.storage_file}")
                        logger.info("")
                        logger.info("Next steps:")
                        logger.info("  1. Test session: python src/skills/linkedin_session_auth.py test")
                        logger.info("  2. Start automation: python src/orchestration/orchestrator.py")
                        logger.info("")
                        
                        self.is_authenticated = True
                        return True
                
                # Cleanup
                self.browser.close()
                self.browser = None
                self.context = None
                self.page = None
                
                logger.info("")
                logger.warning("Session not saved - login not completed or cancelled")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            self._log_auth_event('authentication_failed', {'error': str(e)})
            
            # Cleanup on error
            if self.browser:
                try:
                    self.browser.close()
                except:
                    pass
            
            return False

    def _capture_profile_info(self) -> bool:
        """
        Capture profile information from logged-in session

        Returns:
            True if profile captured successfully
        """
        try:
            if not self.page:
                return False
            
            # Navigate to profile page
            self.page.goto('https://www.linkedin.com/m/feed/', wait_until='networkidle')
            time.sleep(2)
            
            # Try to get profile name
            profile_name = None
            try:
                name_element = self.page.query_selector('.share-box-feed-entry__dropdown button span')
                if name_element:
                    profile_name = name_element.inner_text()
            except:
                pass
            
            # Try to get profile URL
            profile_url = None
            try:
                profile_link = self.page.query_selector('a[href*="/in/"]')
                if profile_link:
                    profile_url = profile_link.get_attribute('href')
            except:
                pass
            
            # Save profile info
            profile_data = {
                'name': profile_name,
                'profile_url': profile_url,
                'captured_at': datetime.now().isoformat()
            }
            
            with open(self.profile_file, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, indent=2)
            
            logger.info(f"Profile captured: {profile_name}")
            self.profile_data = profile_data
            
            return True
            
        except Exception as e:
            logger.debug(f"Could not capture profile: {e}")
            return False

    def is_valid_session(self) -> bool:
        """
        Check if saved session is valid and working (QUICK TEST - <20 seconds)

        Returns:
            True if session is valid
        """
        if not PLAYWRIGHT_AVAILABLE:
            return False

        # Check if session files exist
        if not self._session_exists():
            logger.debug("No saved session found")
            return False

        # Load session
        session_data = self._load_session()
        if not session_data:
            return False

        try:
            # Set NODE_OPTIONS to increase memory limit
            import os
            os.environ['NODE_OPTIONS'] = '--max-old-space-size=1024'  # 1GB memory limit
            
            # Quick test with sync_playwright (NOT context manager to avoid issues)
            playwright = sync_playwright().start()
            
            # Launch browser (headless for testing)
            browser = playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--js-flags="--max-old-space-size=512"',
                ],
                env={**os.environ, 'NODE_OPTIONS': '--max-old-space-size=1024'}
            )

            # Create context with saved cookies
            context = browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent=session_data.get('user_agent')
            )

            # Set cookies
            context.add_cookies(session_data.get('cookies', []))

            # Create page
            page = context.new_page()

            # Quick navigation test (15 second timeout)
            try:
                page.goto('https://www.linkedin.com', wait_until='domcontentloaded', timeout=15000)
                page.wait_for_timeout(3000)  # Wait for any redirects
            except Exception as e:
                logger.debug(f"Navigation error: {e}")
                browser.close()
                playwright.stop()
                return False

            # Quick URL check
            current_url = page.url
            is_logged_in = False
                
            # Check 1: URL contains feed or profile
            if 'linkedin.com/feed' in current_url or 'linkedin.com/in/' in current_url:
                is_logged_in = True
                logger.debug(f"✓ Logged in - URL: {current_url}")
                
            # Check 2: URL is NOT login page
            elif 'linkedin.com/login' not in current_url and 'linkedin.com/checkpoint' not in current_url:
                # Check 3: Look for logged-in indicators
                try:
                    # Check for "Start a post" button (only visible when logged in)
                    post_box = page.query_selector('[data-test-id="share-box-feed-entry"]')
                    if post_box:
                        is_logged_in = True
                        logger.debug("✓ Post box detected - logged in")
                except:
                    pass
                    
                # Check for profile menu
                if not is_logged_in:
                    try:
                        profile_menu = page.query_selector('[data-test-id="profile icon"]')
                        if profile_menu:
                            is_logged_in = True
                            logger.debug("✓ Profile icon detected - logged in")
                    except:
                        pass
                    
                # Check for navigation bar (only visible when logged in)
                if not is_logged_in:
                    try:
                        nav_bar = page.query_selector('[data-test-id="topbar"]')
                        if nav_bar:
                            is_logged_in = True
                            logger.debug("✓ Navigation bar detected - logged in")
                    except:
                        pass
                    
                # Fallback: If URL is linkedin.com homepage and no login prompt, assume logged in
                if not is_logged_in and (current_url == 'https://www.linkedin.com/' or current_url == 'https://www.linkedin.com'):
                    is_logged_in = True
                    logger.debug("✓ Homepage reached - assuming logged in")

            # Close immediately
            browser.close()
            playwright.stop()

            if is_logged_in:
                logger.debug("✓ Session is valid (quick check)")
                return True
            else:
                logger.debug(f"✗ Session invalid - URL: {current_url}")
                return False

        except Exception as e:
            logger.debug(f"Session validation error: {e}")
            return False

    def _close_browser(self) -> None:
        """Close browser if open"""
        try:
            if self.browser:
                self.browser.close()
                self.browser = None
                self.context = None
                self.page = None
                logger.debug("Browser closed")
        except Exception as e:
            logger.debug(f"Error closing browser: {e}")

    def get_cookies(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get saved session cookies

        Returns:
            List of cookies or None if no session
        """
        session_data = self._load_session()
        if session_data:
            return session_data.get('cookies')
        return None

    def get_storage(self) -> Optional[Dict[str, Any]]:
        """
        Get saved local storage data

        Returns:
            Storage dict or None if no session
        """
        if not self.storage_file.exists():
            return None
        
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None

    def get_profile(self) -> Optional[Dict[str, Any]]:
        """
        Get cached profile information

        Returns:
            Profile data or None if not available
        """
        if not self.profile_file.exists():
            return None
        
        try:
            with open(self.profile_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None

    def check_status(self) -> Dict[str, Any]:
        """
        Check current session status

        Returns:
            Status dictionary
        """
        status = {
            'playwright_available': PLAYWRIGHT_AVAILABLE,
            'session_exists': self._session_exists(),
            'session_valid': False,
            'session_age_days': None,
            'expires_in_days': None,
            'profile_name': None,
            'config_dir': str(self.config_dir)
        }
        
        if self._session_exists():
            session_data = self._load_session()
            if session_data:
                # Calculate session age
                saved_at = session_data.get('saved_at')
                if saved_at:
                    saved_dt = datetime.fromisoformat(saved_at)
                    age = datetime.now() - saved_dt
                    status['session_age_days'] = age.days
                
                # Calculate expiry
                expires_at = session_data.get('expires_at')
                if expires_at:
                    expires_dt = datetime.fromisoformat(expires_at)
                    delta = expires_dt - datetime.now()
                    status['expires_in_days'] = max(0, delta.days)
        
        # Get profile name
        profile = self.get_profile()
        if profile:
            status['profile_name'] = profile.get('name', 'Unknown')
        
        # Check if session is valid
        if status['session_exists']:
            status['session_valid'] = self.is_valid_session()
        
        return status

    def _log_auth_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """
        Log authentication event

        Args:
            event_type: Type of event
            details: Event details
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'actor': 'linkedin_session_auth',
            'details': details
        }
        
        log_file = self.logs_dir / f"linkedin_session_{datetime.now().strftime('%Y-%m-%d')}.json"
        
        logs = []
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except:
                logs = []
        
        logs.append(log_entry)
        
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=2)
        except Exception as e:
            logger.debug(f"Could not write log: {e}")


    def login_interactive(self):
        """
        Browser-based login with Chromium
        Opens browser, user logs in manually, session is saved
        """
        
        print("\n" + "="*70)
        print("LINKEDIN BROWSER LOGIN")
        print("="*70)
        print()
        print("This will open a Chromium browser for you to login to LinkedIn.")
        print("After you login, the session will be saved automatically.")
        print()
        input("Press ENTER to open browser...")
        
        try:
            from playwright.sync_api import sync_playwright
            
            print("\n🌐 Launching Chromium browser...")
            
            with sync_playwright() as p:
                # Launch browser (NOT headless - user needs to see it)
                browser = p.chromium.launch(
                    headless=False,
                    args=[
                        '--start-maximized',
                    ]
                )
                
                print("✓ Browser launched")
                
                # Create context
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080}
                )
                
                # Create page
                page = context.new_page()
                
                print("\n🔗 Navigating to LinkedIn login...")
                
                # Navigate to LinkedIn
                page.goto('https://www.linkedin.com/login')
                
                print("\n" + "="*70)
                print("📝 PLEASE LOGIN TO LINKEDIN IN THE BROWSER")
                print("="*70)
                print()
                print("1. Enter your LinkedIn email/username")
                print("2. Enter your password")
                print("3. Complete any 2FA/verification if prompted")
                print("4. Wait until you see the LinkedIn FEED")
                print("5. Then come back here and press ENTER")
                print()
                
                # Wait for user to login
                input("⏳ After you're logged in and see your feed, press ENTER...")
                
                print("\n💾 Saving session...")
                
                # Get cookies
                cookies = context.cookies()
                
                # Find li_at cookie (LinkedIn session cookie)
                li_at_cookie = None
                for cookie in cookies:
                    if cookie['name'] == 'li_at':
                        li_at_cookie = cookie
                        break
                
                if not li_at_cookie:
                    print("\n❌ ERROR: LinkedIn session cookie not found!")
                    print("This means you might not be logged in properly.")
                    print()
                    print("Please try again and make sure you:")
                    print("1. Successfully login to LinkedIn")
                    print("2. See your LinkedIn feed before pressing ENTER")
                    
                    browser.close()
                    return False
                
                # Create session data
                session_data = {
                    'cookies': cookies,
                    'created_at': datetime.now().isoformat()
                }
                
                # Save to file
                self.config_dir.mkdir(parents=True, exist_ok=True)
                
                with open(self.session_file, 'w') as f:
                    json.dump(session_data, f, indent=2)
                
                print(f"✓ Session saved to: {self.session_file}")
                
                # Close browser
                browser.close()
                
                print("\n" + "="*70)
                print("✅ LOGIN SUCCESSFUL!")
                print("="*70)
                print()
                print(f"Session saved with {len(cookies)} cookies")
                print(f"li_at cookie: {li_at_cookie['value'][:20]}...")
                print()
                print("You can now use the orchestrator to post to LinkedIn!")
                print()
                
                return True
                
        except Exception as e:
            print(f"\n❌ Error during login: {e}")
            import traceback
            traceback.print_exc()
            return False


# CLI interface
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
        description='LinkedIn Session Authentication',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python src/skills/linkedin_session_auth.py login   # Login and save session
    python src/skills/linkedin_session_auth.py test    # Test session validity
    python src/skills/linkedin_session_auth.py logout  # Clear saved session
    python src/skills/linkedin_session_auth.py status  # Check session status
        """
    )

    parser.add_argument(
        'command',
        nargs='?',
        default='status',
        choices=['login', 'test', 'logout', 'status'],
        help='Command to run'
    )

    parser.add_argument(
        '--config-dir',
        type=str,
        help='Path to config directory (default: project_root/config)'
    )

    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode (not recommended for login)'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("LinkedIn Session Authentication")
    print("=" * 60)
    print()

    # Initialize auth manager
    auth = LinkedInSessionAuth(config_dir=args.config_dir)

    if args.command == 'login':
        print("LinkedIn Browser Login")
        print("-" * 40)
        print()

        # Check dependencies
        if not PLAYWRIGHT_AVAILABLE:
            print("ERROR: Playwright not installed")
            print()
            print("Install with:")
            print("  pip install playwright playwright-stealth")
            print("  python -m playwright install chromium")
            print()
            sys.exit(1)

        # Check if session already exists
        if auth._session_exists():
            print("Existing session found!")
            response = input("Overwrite existing session? (y/N): ").strip().lower()
            if response != 'y':
                print("Login cancelled")
                sys.exit(0)

        # Use the new interactive login method
        success = auth.login_interactive()

        if not success:
            print()
            print("=" * 60)
            print("✗ LOGIN FAILED")
            print("=" * 60)
            print()
            print("Possible reasons:")
            print("  • Login not completed in browser")
            print("  • Browser was closed manually")
            print("  • Network error")
            print()
            print("Try again:")
            print("  python src/skills/linkedin_session_auth.py login")
            sys.exit(1)

    elif args.command == 'test':
        print("Testing LinkedIn Session")
        print("-" * 40)
        print()
        
        if not PLAYWRIGHT_AVAILABLE:
            print("ERROR: Playwright not installed")
            sys.exit(1)
        
        if not auth._session_exists():
            print("No saved session found!")
            print()
            print("To create a session:")
            print("  python src/skills/linkedin_session_auth.py login")
            sys.exit(1)
        
        print("Loading saved session...")
        is_valid = auth.is_valid_session()
        
        print()
        if is_valid:
            print("=" * 60)
            print("✓ SESSION VALID")
            print("=" * 60)
            print()
            print("Your LinkedIn session is working correctly!")
            print("You can now use LinkedIn posting features.")
        else:
            print("=" * 60)
            print("✗ SESSION INVALID")
            print("=" * 60)
            print()
            print("Your session has expired or is invalid.")
            print()
            print("To re-login:")
            print("  python src/skills/linkedin_session_auth.py login")
            sys.exit(1)

    elif args.command == 'logout':
        print("Clearing LinkedIn Session")
        print("-" * 40)
        print()
        
        if not auth._session_exists():
            print("No saved session found!")
            print("Nothing to clear.")
            sys.exit(0)
        
        profile = auth.get_profile()
        if profile and profile.get('name'):
            print(f"Session for: {profile.get('name')}")
            print()
        
        response = input("Clear saved session? (y/N): ").strip().lower()
        
        if response == 'y':
            success = auth._clear_session()
            print()
            if success:
                print("=" * 60)
                print("✓ SESSION CLEARED")
                print("=" * 60)
                print()
                print("LinkedIn session has been removed.")
                print("You will need to login again to use LinkedIn features.")
            else:
                print("=" * 60)
                print("✗ CLEAR FAILED")
                print("=" * 60)
                print()
                print("Error clearing session")
                sys.exit(1)
        else:
            print("Clear cancelled")

    elif args.command == 'status':
        print("Session Status")
        print("-" * 40)
        print()
        
        status = auth.check_status()
        
        print(f"  Playwright installed: {'Yes' if status['playwright_available'] else 'No'}")
        print(f"  Session exists: {'Yes' if status['session_exists'] else 'No'}")
        print(f"  Session valid: {'Yes' if status['session_valid'] else 'No'}")
        
        if status['session_age_days'] is not None:
            print(f"  Session age: {status['session_age_days']} days")
        
        if status['expires_in_days'] is not None:
            print(f"  Expires in: {status['expires_in_days']} days")
        
        if status['profile_name']:
            print(f"  Profile: {status['profile_name']}")
        
        print(f"  Config dir: {status['config_dir']}")
        
        print()
        if status['session_valid']:
            print("Status: ✓ AUTHENTICATED")
        elif status['session_exists'] and not status['session_valid']:
            print("Status: ⚠ Session exists but may be expired")
            print("        Run 'test' command to verify")
        else:
            print("Status: ✗ NOT AUTHENTICATED")
            print("        Run 'login' command to create session")
        
        # Next steps
        print()
        print("Next Steps:")
        if not status['session_exists']:
            print("  1. Run: python src/skills/linkedin_session_auth.py login")
            print("  2. Log into LinkedIn in the browser")
            print("  3. Session will be saved automatically")
        elif not status['session_valid']:
            print("  1. Run: python src/skills/linkedin_session_auth.py test")
            print("  2. Verify session status")
            print("  3. Re-login if needed")
        else:
            print("  ✓ Session ready!")
            print("  ✓ You can now use LinkedIn posting features")

    print()
    print("Done.")
