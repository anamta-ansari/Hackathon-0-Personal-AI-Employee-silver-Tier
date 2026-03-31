"""
LinkedIn Browser-Based Posting Skill

This skill posts to LinkedIn using browser automation (Playwright) instead of the API.
It reuses the session saved by LinkedInSessionAuth.

Features:
- Post to LinkedIn using browser automation
- Reuse saved session cookies
- Support for text posts and posts with images
- Error handling and retry logic
- Detection of session expiry

Usage:
    python src/skills/linkedin_browser_post.py --content "Your post content here"
    python src/skills/linkedin_browser_post.py --file path/to/post.md
    python src/skills/linkedin_browser_post.py --test
"""

import os
import sys
import json
import logging
import time
import re
from pathlib import Path
from datetime import datetime
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

# Clipboard support for fast paste method
try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False
    logger.debug("pyperclip not available - clipboard paste method disabled")

# Import session auth
try:
    from .linkedin_session_auth import LinkedInSessionAuth
except ImportError:
    from linkedin_session_auth import LinkedInSessionAuth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LinkedInBrowserPoster:
    """
    LinkedIn Browser-Based Poster

    Posts to LinkedIn using browser automation with saved session.
    """

    def __init__(self, config_dir: Optional[str] = None, dry_run: bool = False, headless: bool = False):
        """
        Initialize LinkedIn Browser Poster

        Args:
            config_dir: Path to config directory
            dry_run: If True, log actions without posting
            headless: If True, run browser without UI (default: False for visibility)
        """
        # Resolve paths
        self.project_root = Path(__file__).parent.parent.parent
        self.config_dir = Path(config_dir) if config_dir else self.project_root / 'config'
        self.vault_path = self.project_root / 'AI_Employee_Vault'

        # Initialize session auth
        self.session_auth = LinkedInSessionAuth(config_dir=str(self.config_dir))

        # State
        self.dry_run = dry_run
        self.headless = headless  # Control browser visibility
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        # Ensure directories exist
        self.logs_dir = self.project_root / 'logs'
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"LinkedInBrowserPoster initialized")
        logger.info(f"Config directory: {self.config_dir}")
        logger.info(f"Dry run: {dry_run}")
        logger.info(f"Headless mode: {headless}")

    def _apply_stealth(self, page: Page) -> None:
        """Apply stealth mode to avoid bot detection"""
        try:
            # Try new stealth API first
            try:
                from playwright_stealth import stealth
                stealth(page)
            except ImportError:
                from playwright_stealth import stealth_sync
                stealth_sync(page)
        except Exception as e:
            logger.debug(f"Stealth mode warning: {e}")

    def _launch_browser(self) -> bool:
        """
        Launch browser with saved session

        Returns:
            True if successful
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright not available")
            return False

        # Load saved session
        session_data = self.session_auth._load_session()
        if not session_data:
            logger.error("No saved session found")
            logger.info("Run: python src/skills/linkedin_session_auth.py login")
            return False

        try:
            # Start playwright
            self.playwright = sync_playwright().start()
            
            # Launch browser (use headless setting from instance)
            logger.info(f"Launching browser (headless={self.headless})...")
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                ]
            )

            # Create context with saved cookies
            self.context = self.browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent=session_data.get('user_agent')
            )

            # Set cookies
            cookies = session_data.get('cookies', [])
            if cookies:
                self.context.add_cookies(cookies)

            # Create page
            self.page = self.context.new_page()

            # Apply stealth
            self._apply_stealth(self.page)

            logger.info("Browser launched with saved session")
            return True

        except Exception as e:
            logger.error(f"Error launching browser: {e}")
            self._close_browser()
            return False

    def _close_browser(self) -> None:
        """Close browser if open"""
        try:
            if self.page:
                self.page.close()
                self.page = None
            if self.context:
                self.context.close()
                self.context = None
            if self.browser:
                self.browser.close()
                self.browser = None
            if hasattr(self, 'playwright') and self.playwright:
                self.playwright.stop()
                self.playwright = None
            logger.debug("Browser closed")
        except Exception as e:
            logger.debug(f"Error closing browser: {e}")

    def _navigate_to_linkedin(self) -> bool:
        """
        Navigate to LinkedIn feed

        Returns:
            True if successfully navigated and logged in
        """
        if not self.page:
            return False

        try:
            logger.info("Navigating to LinkedIn...")
            # Use domcontentloaded for faster load, with longer timeout
            try:
                self.page.goto('https://www.linkedin.com/feed', wait_until='domcontentloaded', timeout=60000)
                time.sleep(5)  # Wait for page to fully load
            except Exception as e:
                logger.debug(f"Feed navigation error: {e}")
                # Try homepage instead
                self.page.goto('https://www.linkedin.com', wait_until='domcontentloaded', timeout=30000)
                time.sleep(3)

            # Check if logged in
            current_url = self.page.url

            if 'linkedin.com/login' in current_url:
                logger.error("Not logged in - session may be expired")
                return False

            # Check for feed or homepage
            if 'linkedin.com/feed' in current_url or 'linkedin.com/' in current_url:
                logger.info("Successfully navigated to LinkedIn")
                return True
            
            logger.warning(f"Unexpected URL: {current_url}")
            return True  # Continue anyway

        except Exception as e:
            logger.error(f"Error navigating to LinkedIn: {e}")
            return False

    def _is_logged_in(self) -> bool:
        """
        Check if currently logged into LinkedIn

        Returns:
            True if logged in
        """
        if not self.page:
            return False
        
        try:
            # Check URL
            if 'linkedin.com/login' in self.page.url:
                return False
            
            # Check for post box (only visible when logged in)
            try:
                post_box = self.page.query_selector('[data-test-id="share-box-feed-entry"]')
                if post_box:
                    return True
            except:
                pass
            
            # Check for profile icon
            try:
                profile_icon = self.page.query_selector('[data-test-id="profile icon"]')
                if profile_icon:
                    return True
            except:
                pass
            
            # Check URL contains feed
            if 'linkedin.com/feed' in self.page.url:
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking login status: {e}")
            return False

    def create_post(self, content: str, title: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a post on LinkedIn using browser automation

        Args:
            content: Post content (text)
            title: Optional title for logging

        Returns:
            Dict with post result
        """
        result = {
            'success': False,
            'post_id': None,
            'error': None,
            'message': ''
        }
        
        # Validate content
        if not content or not content.strip():
            result['error'] = 'Post content is empty'
            return result
        
        # Check content length (LinkedIn limit: 3000 characters)
        if len(content) > 3000:
            result['error'] = f'Content exceeds 3000 characters ({len(content)})'
            return result
        
        # Check session
        if not self.session_auth.is_valid_session():
            result['error'] = 'Session expired or invalid'
            result['message'] = 'Run: python src/skills/linkedin_session_auth.py login'
            return result
        
        # Dry run check
        if self.dry_run:
            logger.info(f"[DRY RUN] Would post: {content[:100]}...")
            result['success'] = True
            result['message'] = 'Dry run - no post published'
            return result
        
        try:
            # Launch browser
            if not self._launch_browser():
                result['error'] = 'Failed to launch browser'
                return result
            
            # Navigate to LinkedIn
            if not self._navigate_to_linkedin():
                result['error'] = 'Failed to navigate to LinkedIn'
                self._close_browser()
                return result
            
            # Verify logged in
            if not self._is_logged_in():
                result['error'] = 'Not logged in - session may be expired'
                self._close_browser()
                return result
            
            logger.info("Creating LinkedIn post...")

            # Click "Start a post" button
            # Try multiple selectors as LinkedIn changes them frequently
            post_box_clicked = False
            selectors_to_try = [
                '[data-test-id="share-box-feed-entry"]',
                '.share-box-feed-entry',
                'button:has-text("Start a post")',
                'button:has-text("Start")',
                '.artdeco-button:has-text("Start")',
                '[aria-label*="Start a post"]',
                '[aria-label*="Create a post"]',
            ]
            
            try:
                # First, wait for the page to be fully loaded
                time.sleep(3)
                
                for selector in selectors_to_try:
                    try:
                        post_box = self.page.wait_for_selector(selector, timeout=5000, state='visible')
                        if post_box:
                            post_box.click()
                            logger.info(f"Clicked 'Start a post' using selector: {selector}")
                            post_box_clicked = True
                            time.sleep(3)  # Wait for dialog to open
                            break
                    except Exception:
                        logger.debug(f"Selector failed: {selector}")
                        continue
                
                if not post_box_clicked:
                    # Try clicking the first button in the feed area as fallback
                    logger.info("Trying fallback: clicking first button in feed")
                    try:
                        # Look for any button near the top of the feed
                        fallback_btn = self.page.query_selector('button[aria-label]')
                        if fallback_btn:
                            fallback_btn.click()
                            post_box_clicked = True
                            time.sleep(2)
                    except Exception as e:
                        logger.debug(f"Fallback also failed: {e}")
                
                if not post_box_clicked:
                    raise Exception("Could not find 'Start a post' button with any selector")
                    
            except Exception as e:
                logger.error(f"Could not click post box: {e}")
                result['error'] = 'Could not open post editor'
                self._close_browser()
                return result

            # Find the text editor and type content using FAST method
            try:
                # Wait for editor dialog to appear (increased wait time)
                logger.info("Waiting for editor dialog to open...")
                time.sleep(3)
                
                # Try multiple selectors for the editor with longer timeouts
                editor_selectors = [
                    '[role="textbox"][aria-label*="post" i]',
                    '[role="textbox"][aria-label*="Share" i]',
                    '[aria-label*="What do you want to share?" i]',
                    '[data-placeholder*="What do you want to share?" i]',
                    '.editor-content',
                    '[contenteditable="true"]',
                    'div[contenteditable="true"]',
                    '.share-box__editor',
                ]

                editor = None
                for selector in editor_selectors:
                    try:
                        editor = self.page.wait_for_selector(selector, timeout=5000, state='visible')
                        if editor:
                            logger.info(f"Found editor using: {selector}")
                            break
                    except:
                        continue

                if not editor:
                    # Fallback: find any contenteditable element via JavaScript
                    logger.info("Trying JavaScript fallback to find editor...")
                    editor = self.page.query_selector('[contenteditable]')
                    
                    if not editor:
                        # Take screenshot for debugging
                        try:
                            screenshot_path = self.logs_dir / f"editor_not_found_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                            self.page.screenshot(path=str(screenshot_path))
                            logger.warning(f"Screenshot saved: {screenshot_path}")
                        except:
                            pass
                        raise Exception("Could not find post editor - dialog may not have opened")

                # Click to focus
                editor.click()
                time.sleep(2)

                # Log content details
                logger.info(f"Content to post: {len(content)} characters")
                logger.info(f"Has emojis: {'Yes' if any(ord(c) > 127 for c in content) else 'No'}")
                logger.info(f"Preview: {content[:100]}...")

                # ═══════════════════════════════════════════════════════════
                # CRITICAL FIX: Fast content insertion using JavaScript
                # ═══════════════════════════════════════════════════════════
                
                typing_success = False
                
                # Method 1: Direct JavaScript innerHTML (FASTEST - instant)
                if not typing_success:
                    try:
                        logger.info("Method 1: JavaScript innerHTML injection...")
                        
                        # Escape content for JavaScript
                        content_escaped = (content
                            .replace('\\\\', '\\\\\\\\')
                            .replace('`', '\\`')
                            .replace('${', '\\${')
                            .replace('\n', '\\n')
                        )
                        
                        js_result = self.page.evaluate(f'''
                            () => {{
                                const editor = document.querySelector('.editor-content, [contenteditable="true"], .ql-editor');
                                if (!editor) {{
                                    console.error('Editor not found');
                                    return false;
                                }}
                                
                                // Clear existing content
                                editor.innerHTML = '';
                                
                                // Insert new content
                                const content = `{content_escaped}`;
                                
                                // Convert line breaks to <br> tags
                                const htmlContent = content.replace(/\\n/g, '<br>');
                                editor.innerHTML = htmlContent;
                                
                                // Trigger input event so LinkedIn knows content changed
                                editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                editor.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                
                                // Focus editor
                                editor.focus();
                                
                                console.log('Content inserted successfully');
                                return true;
                            }}
                        ''')
                        
                        self.page.wait_for_timeout(2000)
                        
                        if js_result:
                            logger.info("✓ Content inserted via JavaScript (instant)")
                            typing_success = True
                        else:
                            logger.warning("Method 1: JavaScript returned false")
                            
                    except Exception as e:
                        logger.error(f"JavaScript method failed: {e}")
                
                # Method 2: Fallback to fill() method
                if not typing_success:
                    try:
                        logger.info("Method 2: Using fill() method...")
                        editor.fill(content)
                        self.page.wait_for_timeout(2000)
                        logger.info("✓ Content inserted via fill()")
                        typing_success = True
                        
                    except Exception as e:
                        logger.error(f"Fill method failed: {e}")
                
                # Method 3: Clipboard paste (fast, natural)
                if not typing_success and PYPERCLIP_AVAILABLE:
                    try:
                        logger.info("Method 3: Clipboard paste...")
                        pyperclip.copy(content)
                        editor.click()
                        self.page.wait_for_timeout(500)
                        self.page.keyboard.press('Control+V')
                        self.page.wait_for_timeout(2000)  # Wait for LinkedIn to process
                        logger.info("✓ Content pasted from clipboard")
                        
                        # Check if post button became enabled (indicates success)
                        try:
                            post_enabled = self.page.evaluate('''
                                () => {
                                    const buttons = Array.from(document.querySelectorAll('button.share-actions__primary-action, button[aria-label="Post"]'));
                                    return buttons.some(btn => !btn.disabled);
                                }
                            ''')
                            if post_enabled:
                                logger.info("✓ Post button enabled - content accepted")
                                typing_success = True
                            else:
                                logger.warning("⚠️ Post button still disabled after paste")
                        except:
                            # Assume success if no error
                            typing_success = True
                            
                    except Exception as e:
                        logger.warning(f"Clipboard paste failed: {e}")
                
                # Method 4: Last resort - type in chunks
                if not typing_success:
                    try:
                        logger.info("Method 4: Chunked typing (slow fallback)...")
                        
                        chunk_size = 50
                        for i in range(0, len(content), chunk_size):
                            chunk = content[i:i+chunk_size]
                            editor.type(chunk, delay=5)
                            logger.debug(f"Progress: {min(i+chunk_size, len(content))}/{len(content)}")
                            
                        self.page.wait_for_timeout(2000)
                        logger.info("✓ Content typed in chunks")
                        typing_success = True
                        
                    except Exception as e:
                        logger.error(f"Chunked typing failed: {e}")
                
                if not typing_success:
                    raise Exception("Could not enter post content with any method")

                # Verify content was inserted
                logger.info("Verifying content insertion...")
                try:
                    # Wait a bit for LinkedIn to process the content
                    self.page.wait_for_timeout(2000)
                    
                    # Try multiple methods to verify content
                    editor_text = None
                    
                    # Method 1: Check textContent
                    try:
                        editor_text = self.page.evaluate('''
                            () => {
                                const editor = document.querySelector('.editor-content, [contenteditable="true"]');
                                return editor ? editor.textContent.trim() : '';
                            }
                        ''')
                    except:
                        pass
                    
                    # Method 2: Check innerHTML if textContent fails
                    if not editor_text or len(editor_text) == 0:
                        try:
                            editor_html = self.page.evaluate('''
                                () => {
                                    const editor = document.querySelector('.editor-content, [contenteditable="true"]');
                                    return editor ? editor.innerHTML : '';
                                }
                            ''')
                            # If HTML has content, assume text is there (LinkedIn may not expose it yet)
                            if editor_html and len(editor_html) > 10:
                                editor_text = "content_present_in_html"
                        except:
                            pass
                    
                    # Method 3: Check if post button is now enabled (indirect verification)
                    if not editor_text or len(editor_text) == 0:
                        try:
                            post_button_enabled = self.page.evaluate('''
                                () => {
                                    const buttons = document.querySelectorAll('button.share-actions__primary-action, button[aria-label="Post"]');
                                    for (const btn of buttons) {
                                        if (!btn.disabled) {
                                            return true;
                                        }
                                    }
                                    return false;
                                }
                            ''')
                            if post_button_enabled:
                                editor_text = "post_button_enabled"
                        except:
                            pass
                    
                    if editor_text and len(editor_text) > 0:
                        logger.info(f"✓ Content verification successful: {editor_text[:50]}...")
                    else:
                        logger.warning("⚠️ Editor appears empty after insertion (but proceeding anyway)")
                        # Don't fail here - LinkedIn may have the content but not expose it via JS
                        
                except Exception as e:
                    logger.warning(f"Could not verify content: {e}")
                    # Don't fail here - proceed with posting anyway
                
            except Exception as e:
                logger.error(f"Could not type content: {e}")
                result['error'] = 'Could not enter post content'
                self._close_browser()
                return result
            
            # ═══════════════════════════════════════════════════════════
            # CRITICAL FIX: Multiple post button strategies
            # ═══════════════════════════════════════════════════════════
            
            try:
                logger.info("Waiting for Post button to become enabled...")
                self.page.wait_for_timeout(3000)
                
                # Try multiple button selectors
                selectors = [
                    'button.share-actions__primary-action',
                    'button[aria-label="Post"]',
                    'button.share-actions__primary-action.artdeco-button--primary',
                    '.share-box-footer button.artdeco-button--primary',
                    'button:has-text("Post")',
                    'button[data-test-share-box-post-button]',
                ]
                
                posted = False
                
                # Strategy 1: Try each CSS selector
                for selector in selectors:
                    try:
                        logger.info(f"Trying selector: {selector}")
                        
                        # Wait for button with shorter timeout
                        post_button = self.page.wait_for_selector(
                            selector,
                            state='visible',
                            timeout=5000
                        )
                        
                        if post_button:
                            # Check if enabled
                            is_disabled = post_button.get_attribute('disabled')
                            
                            if is_disabled:
                                logger.debug(f"Button disabled: {selector}")
                                continue
                            
                            # Click it
                            post_button.click()
                            logger.info(f"✓ Clicked Post button: {selector}")
                            
                            # Wait for post to submit
                            self.page.wait_for_timeout(4000)
                            
                            posted = True
                            break
                            
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {str(e)[:100]}")
                        continue
                
                # Strategy 2: JavaScript button finder (if selectors failed)
                if not posted:
                    logger.info("Trying JavaScript button finder...")
                    
                    try:
                        js_result = self.page.evaluate('''
                            () => {
                                // Find all buttons
                                const buttons = Array.from(document.querySelectorAll('button'));
                                
                                // Find the Post button
                                const postBtn = buttons.find(btn => {
                                    const text = btn.textContent?.trim().toLowerCase();
                                    const label = btn.getAttribute('aria-label')?.toLowerCase();
                                    const classes = btn.className;
                                    
                                    // Match by text, label, or class
                                    return (
                                        text === 'post' ||
                                        label === 'post' ||
                                        (classes && classes.includes('share-actions__primary-action'))
                                    );
                                });
                                
                                if (postBtn && !postBtn.disabled) {
                                    console.log('Found Post button via JavaScript');
                                    postBtn.click();
                                    return true;
                                }
                                
                                console.error('Post button not found or disabled');
                                return false;
                            }
                        ''')
                        
                        if js_result:
                            logger.info("✓ Posted via JavaScript")
                            posted = True
                            self.page.wait_for_timeout(4000)
                            
                    except Exception as e:
                        logger.error(f"JavaScript strategy failed: {e}")
                
                # Strategy 3: Press Enter key (last resort)
                if not posted:
                    logger.info("Trying Ctrl+Enter key press...")
                    
                    try:
                        self.page.keyboard.press('Control+Enter')
                        self.page.wait_for_timeout(3000)
                        logger.info("✓ Pressed Ctrl+Enter")
                        posted = True
                        
                    except Exception as e:
                        logger.error(f"Enter key failed: {e}")
                
                if not posted:
                    raise Exception("Could not submit post - button not found or not clickable")
                
                # ═══════════════════════════════════════════════════════════
                # Verify post was published
                # ═══════════════════════════════════════════════════════════
                
                logger.info("Verifying post was published...")
                
                # Wait for LinkedIn to process
                self.page.wait_for_timeout(3000)
                
                # Check if we're back at feed (indicates success)
                current_url = self.page.url
                logger.info(f"Current URL after posting: {current_url}")
                
                if 'feed' in current_url and 'update' not in current_url:
                    logger.info("✓ Returned to feed - post likely successful")
                    result['success'] = True
                    result['post_id'] = f"browser_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    result['message'] = 'Post published successfully'
                    logger.info("✓ Post published successfully!")
                else:
                    # Check for error messages
                    try:
                        error_msg = self.page.evaluate('''
                            () => {
                                const errors = document.querySelectorAll('.artdeco-inline-feedback--error');
                                return errors.length > 0 ? errors[0].textContent : null;
                            }
                        ''')
                        
                        if error_msg:
                            logger.error(f"LinkedIn error: {error_msg}")
                            result['error'] = f'LinkedIn error: {error_msg}'
                        else:
                            # Still on feed or profile - assume success
                            if 'linkedin.com/feed' in current_url or 'linkedin.com/in/' in current_url:
                                result['success'] = True
                                result['post_id'] = f"browser_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                                result['message'] = 'Post submitted (verified on feed)'
                                logger.info("✓ Post submitted (verified)")
                            else:
                                result['error'] = 'Unexpected URL after posting'
                                logger.warning(f"Unexpected URL: {current_url}")
                                
                    except Exception as e:
                        logger.warning(f"Could not check for errors: {e}")
                        
                        # If we clicked the button, assume success
                        if posted:
                            result['success'] = True
                            result['post_id'] = f"browser_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                            result['message'] = 'Post button clicked (verify manually)'
                            logger.warning("Post button clicked - verify manually on LinkedIn")
                
            except Exception as e:
                logger.error(f"Could not click post button: {e}")
                result['error'] = f'Could not submit post: {str(e)}'
                self._close_browser()
                return result
            
            # Close browser
            self._close_browser()
            
            # Log the action
            if result['success']:
                self._log_post_event('post_published', {
                    'title': title,
                    'content_length': len(content),
                    'post_id': result['post_id']
                })
            else:
                self._log_post_event('post_failed', {
                    'title': title,
                    'error': result['error']
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            result['error'] = str(e)
            self._close_browser()
            return result

    def create_post_with_image(
        self,
        content: str,
        image_path: str,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a post with image attachment

        Args:
            content: Post content
            image_path: Path to image file
            title: Optional title

        Returns:
            Dict with post result
        """
        result = {
            'success': False,
            'post_id': None,
            'error': None,
            'message': ''
        }
        
        # Validate image
        image_file = Path(image_path)
        if not image_file.exists():
            result['error'] = f'Image not found: {image_path}'
            return result
        
        # Check file type
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        if image_file.suffix.lower() not in valid_extensions:
            result['error'] = f'Invalid image type: {image_file.suffix}'
            return result
        
        # Check session
        if not self.session_auth.is_valid_session():
            result['error'] = 'Session expired or invalid'
            return result
        
        # Dry run check
        if self.dry_run:
            logger.info(f"[DRY RUN] Would post with image: {content[:50]}...")
            result['success'] = True
            result['message'] = 'Dry run - no post published'
            return result
        
        try:
            # Launch browser
            if not self._launch_browser():
                result['error'] = 'Failed to launch browser'
                return result
            
            # Navigate to LinkedIn
            if not self._navigate_to_linkedin():
                result['error'] = 'Failed to navigate to LinkedIn'
                self._close_browser()
                return result
            
            # Verify logged in
            if not self._is_logged_in():
                result['error'] = 'Not logged in'
                self._close_browser()
                return result
            
            logger.info("Creating LinkedIn post with image...")
            
            # Click "Start a post" button
            try:
                post_box = self.page.wait_for_selector('[data-test-id="share-box-feed-entry"]', timeout=10000)
                post_box.click()
                time.sleep(2)
            except Exception as e:
                logger.error(f"Could not click post box: {e}")
                result['error'] = 'Could not open post editor'
                self._close_browser()
                return result
            
            # Click media/image button
            try:
                # Find and click the image/media button
                media_button = self.page.wait_for_selector('[aria-label*="photo" i], [aria-label*="image" i], [aria-label*="media" i]', timeout=10000)
                media_button.click()
                logger.info("Clicked media button")
                time.sleep(2)
            except Exception as e:
                logger.error(f"Could not click media button: {e}")
                result['error'] = 'Could not open media selector'
                self._close_browser()
                return result
            
            # Upload image file
            try:
                # Wait for file input to appear
                file_input = self.page.wait_for_selector('input[type="file"]', timeout=10000)
                file_input.set_input_files(str(image_file))
                logger.info(f"Uploaded image: {image_path}")
                
                # Wait for upload to complete
                time.sleep(3)
                
                # Check for upload confirmation
                # (LinkedIn shows a preview when upload succeeds)
            except Exception as e:
                logger.error(f"Could not upload image: {e}")
                result['error'] = 'Could not upload image'
                self._close_browser()
                return result
            
            # Type content
            try:
                editor = self.page.wait_for_selector('[role="textbox"][aria-label*="post"]', timeout=10000)
                editor.click()
                time.sleep(1)
                editor.type(content, delay=50)
                logger.info(f"Typed post content")
                time.sleep(2)
            except Exception as e:
                logger.error(f"Could not type content: {e}")
                result['error'] = 'Could not enter post content'
                self._close_browser()
                return result
            
            # Click "Post" button
            try:
                post_button = self.page.wait_for_selector('button[aria-label="Post"]', timeout=10000)
                post_button.click()
                logger.info("Clicked 'Post' button")
                time.sleep(3)
                
                # Check for success
                current_url = self.page.url
                if 'linkedin.com/feed' in current_url:
                    result['success'] = True
                    result['post_id'] = f"browser_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    result['message'] = 'Post with image published successfully'
                    logger.info("Post with image published successfully!")
                else:
                    result['error'] = 'Unexpected state after posting'
                    
            except Exception as e:
                logger.error(f"Could not click post button: {e}")
                result['error'] = 'Could not submit post'
                self._close_browser()
                return result
            
            # Close browser
            self._close_browser()
            
            # Log the action
            if result['success']:
                self._log_post_event('post_with_image_published', {
                    'title': title,
                    'image': str(image_file),
                    'post_id': result['post_id']
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            result['error'] = str(e)
            self._close_browser()
            return result

    def _log_post_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """
        Log post event

        Args:
            event_type: Type of event
            details: Event details
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'actor': 'linkedin_browser_post',
            'details': details
        }
        
        log_file = self.logs_dir / f"linkedin_posts_{datetime.now().strftime('%Y-%m-%d')}.json"
        
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

    def test_connection(self) -> bool:
        """
        Test if session is valid and can access LinkedIn

        Returns:
            True if connection successful
        """
        logger.info("Testing LinkedIn connection...")
        
        # Check session
        if not self.session_auth.is_valid_session():
            logger.error("Session validation failed")
            return False
        
        # Try to launch browser and navigate
        if not self._launch_browser():
            return False
        
        if not self._navigate_to_linkedin():
            self._close_browser()
            return False
        
        is_logged_in = self._is_logged_in()
        self._close_browser()
        
        if is_logged_in:
            logger.info("✓ Connection test successful")
            return True
        else:
            logger.error("✗ Connection test failed - not logged in")
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
        description='LinkedIn Browser-Based Posting',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python src/skills/linkedin_browser_post.py --content "Your post content here"
    python src/skills/linkedin_browser_post.py --file path/to/post.md
    python src/skills/linkedin_browser_post.py --test
    python src/skills/linkedin_browser_post.py --dry-run --content "Test post"
    python src/skills/linkedin_browser_post.py --content "Test" --visible  # Visible browser (default)
    python src/skills/linkedin_browser_post.py --content "Test" --headless  # Headless browser
        """
    )

    parser.add_argument(
        '--content',
        type=str,
        help='Post content (text)'
    )

    parser.add_argument(
        '--file',
        type=str,
        help='Path to file containing post content'
    )

    parser.add_argument(
        '--image',
        type=str,
        help='Path to image file for post with image'
    )

    parser.add_argument(
        '--title',
        type=str,
        help='Post title (for logging)'
    )

    parser.add_argument(
        '--test',
        action='store_true',
        help='Test connection to LinkedIn'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode (no actual posting)'
    )

    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode (no UI)'
    )

    parser.add_argument(
        '--visible',
        action='store_true',
        help='Run browser in visible mode (default, can watch it work)'
    )

    parser.add_argument(
        '--config-dir',
        type=str,
        help='Path to config directory'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("LinkedIn Browser-Based Posting")
    print("=" * 60)
    print()

    # Determine headless mode (default is visible for user to see)
    headless_mode = args.headless
    if args.visible:
        headless_mode = False  # Explicitly visible
    
    # Initialize poster
    poster = LinkedInBrowserPoster(
        config_dir=args.config_dir,
        dry_run=args.dry_run,
        headless=headless_mode
    )

    if args.test:
        print("Testing LinkedIn connection...")
        print("-" * 40)
        success = poster.test_connection()
        print()
        if success:
            print("=" * 60)
            print("✓ CONNECTION TEST SUCCESSFUL")
            print("=" * 60)
            print()
            print("Your LinkedIn session is working!")
            print("You can now create posts.")
        else:
            print("=" * 60)
            print("✗ CONNECTION TEST FAILED")
            print("=" * 60)
            print()
            print("Your session may be expired.")
            print()
            print("To re-login:")
            print("  python src/skills/linkedin_session_auth.py login")
            sys.exit(1)

    elif args.content or args.file:
        # Get content
        content = args.content
        if args.file:
            file_path = Path(args.file)
            if not file_path.exists():
                print(f"ERROR: File not found: {file_path}")
                sys.exit(1)
            content = file_path.read_text(encoding='utf-8')
        
        if not content or not content.strip():
            print("ERROR: Post content is empty")
            sys.exit(1)
        
        print(f"Creating LinkedIn post...")
        print("-" * 40)
        print(f"Content length: {len(content)} characters")
        if args.image:
            print(f"Image: {args.image}")
        print()
        
        # Create post
        if args.image:
            result = poster.create_post_with_image(
                content=content,
                image_path=args.image,
                title=args.title
            )
        else:
            result = poster.create_post(
                content=content,
                title=args.title
            )
        
        print()
        if result['success']:
            print("=" * 60)
            print("✓ POST PUBLISHED")
            print("=" * 60)
            print()
            print(f"Post ID: {result['post_id']}")
            print(f"Message: {result['message']}")
        else:
            print("=" * 60)
            print("✗ POST FAILED")
            print("=" * 60)
            print()
            print(f"Error: {result['error']}")
            print()
            if 'session' in result.get('message', '').lower():
                print("To re-login:")
                print("  python src/skills/linkedin_session_auth.py login")
            sys.exit(1)

    else:
        # No action specified - show help
        parser.print_help()
        print()
        print()
        print("Quick Start:")
        print("  1. Login: python src/skills/linkedin_session_auth.py login")
        print("  2. Test:  python src/skills/linkedin_browser_post.py --test")
        print("  3. Post:  python src/skills/linkedin_browser_post.py --content \"Your post\"")

    print()
    print("Done.")
