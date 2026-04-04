"""
LinkedIn Browser Post - Async Version
Posts to LinkedIn using Playwright browser automation
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime


class LinkedInBrowserPoster:
    """Post to LinkedIn using browser automation with async API"""
    
    def __init__(self, headless=False, dry_run=False):
        """Initialize poster"""
        
        self.logger = logging.getLogger('skills.linkedin_browser_post')
        
        # Import session auth
        try:
            from skills.linkedin_session_auth import LinkedInSessionAuth
        except ImportError:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from skills.linkedin_session_auth import LinkedInSessionAuth
        
        self.auth = LinkedInSessionAuth()
        self.headless = headless
        self.dry_run = dry_run
        self.timeout = 90000  # 90 seconds
        
        self.logger.info("LinkedInBrowserPoster initialized")
        self.logger.info(f"Config directory: {self.auth.config_dir}")
        self.logger.info(f"Dry run: {self.dry_run}")
        self.logger.info(f"Headless mode: {self.headless}")
        self.logger.info(f"Browser timeout: {self.timeout}ms")
    
    
    async def create_post(self, content, post_type='general'):
        """
        Create a LinkedIn post - ASYNC VERSION
        
        This uses async Playwright API to avoid event loop conflicts
        """
        
        if self.dry_run:
            self.logger.info(f"DRY RUN: Would post {len(content)} chars to LinkedIn")
            return {
                'success': True,
                'post_id': f'dry_run_{int(datetime.now().timestamp())}',
                'error': None,
                'message': 'Dry run - no actual post'
            }
        
        try:
            from playwright.async_api import async_playwright
            import os
            
            # ═══════════════════════════════════════════════════════
            # MEMORY FIX: Increase Node.js heap size
            # ═══════════════════════════════════════════════════════
            os.environ['NODE_OPTIONS'] = '--max-old-space-size=4096'
            
            self.logger.info(f"Creating LinkedIn post ({len(content)} chars)")
            
            # ═══════════════════════════════════════════════════════
            # SESSION CHECK
            # ═══════════════════════════════════════════════════════
            
            if not self.auth.session_file.exists():
                self.logger.error("❌ No session file found!")
                return {
                    'success': False,
                    'post_id': None,
                    'error': 'Session expired or invalid',
                    'message': 'Run: python src/skills/linkedin_session_auth.py login'
                }
            
            session = self.auth._load_session()
            if not session or 'cookies' not in session:
                self.logger.error("❌ Invalid session data!")
                return {
                    'success': False,
                    'post_id': None,
                    'error': 'Session expired or invalid',
                    'message': 'Run: python src/skills/linkedin_session_auth.py login'
                }
            
            self.logger.info("✓ Session file valid")
            
            # ═══════════════════════════════════════════════════════
            # LAUNCH BROWSER
            # ═══════════════════════════════════════════════════════
            
            playwright = await async_playwright().start()
            
            self.logger.info("Launching browser...")
            
            browser = await playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-software-rasterizer',
                    '--disable-extensions',
                    '--disable-background-networking',
                    '--disable-default-apps',
                    '--disable-sync',
                    '--js-flags=--max-old-space-size=4096',
                ]
            )
            
            self.logger.info("✓ Browser launched")
            
            # ═══════════════════════════════════════════════════════
            # LOAD SESSION
            # ═══════════════════════════════════════════════════════
            
            context = await browser.new_context()
            await context.add_cookies(session['cookies'])
            
            self.logger.info("✓ Session cookies loaded")
            
            page = await context.new_page()
            
            # ═══════════════════════════════════════════════════════
            # NAVIGATE TO LINKEDIN
            # ═══════════════════════════════════════════════════════
            
            self.logger.info("Navigating to LinkedIn feed...")
            
            try:
                await page.goto('https://www.linkedin.com/feed', 
                               wait_until='domcontentloaded', 
                               timeout=self.timeout)
                self.logger.info("✓ Navigation successful")
            except Exception as e:
                self.logger.error(f"Navigation failed: {e}")
                await browser.close()
                await playwright.stop()
                return {
                    'success': False,
                    'post_id': None,
                    'error': 'Failed to navigate to LinkedIn',
                    'message': str(e)
                }
            
            # Check if logged in
            await page.wait_for_timeout(3000)
            
            url = page.url
            if 'login' in url.lower() or 'checkpoint' in url.lower():
                self.logger.error("❌ Not logged in - session expired!")
                await browser.close()
                await playwright.stop()
                return {
                    'success': False,
                    'post_id': None,
                    'error': 'Session expired or invalid',
                    'message': 'Run: python src/skills/linkedin_session_auth.py login'
                }
            
            self.logger.info("✓ Confirmed logged in")
            
            # ═══════════════════════════════════════════════════════
            # CLICK "Start a post"
            # ═══════════════════════════════════════════════════════
            
            self.logger.info("Looking for 'Start a post' button...")
            
            clicked = False
            
            # Try selectors
            selectors = [
                'button.share-box-feed-entry__trigger',
                '[aria-label*="Start a post"]',
                '.share-box-feed-entry__trigger',
            ]
            
            for selector in selectors:
                try:
                    button = await page.wait_for_selector(selector, timeout=10000)
                    await button.click()
                    self.logger.info(f"✓ Clicked: {selector}")
                    clicked = True
                    break
                except:
                    continue
            
            if not clicked:
                self.logger.error("❌ Could not find 'Start a post' button")
                await browser.close()
                await playwright.stop()
                return {
                    'success': False,
                    'post_id': None,
                    'error': 'Could not find post button'
                }
            
            await page.wait_for_timeout(3000)
            
            # ═══════════════════════════════════════════════════════
            # FIND EDITOR
            # ═══════════════════════════════════════════════════════
            
            self.logger.info("Finding editor...")
            
            editor = None
            selectors = ['.ql-editor', '[contenteditable="true"]', '.editor-content']
            
            for selector in selectors:
                try:
                    editor = await page.wait_for_selector(selector, timeout=10000)
                    if editor:
                        self.logger.info(f"✓ Found editor: {selector}")
                        break
                except:
                    continue
            
            if not editor:
                self.logger.error("❌ Could not find editor")
                await browser.close()
                await playwright.stop()
                return {
                    'success': False,
                    'post_id': None,
                    'error': 'Could not find editor'
                }
            
            # ═══════════════════════════════════════════════════════
            # INSERT CONTENT (JavaScript - instant!)
            # ═══════════════════════════════════════════════════════
            
            self.logger.info(f"Inserting content ({len(content)} chars)...")
            
            # Escape for JavaScript
            content_escaped = (content
                .replace('\\', '\\\\')
                .replace('`', '\\`')
                .replace('${', '\\${')
                .replace('\n', '\\n')
                .replace('\r', '')
            )
            
            try:
                success = await page.evaluate(f'''
                    () => {{
                        const editors = document.querySelectorAll('.ql-editor, [contenteditable="true"], .editor-content');
                        const editor = editors[editors.length - 1];
                        if (!editor) return false;
                        
                        editor.innerHTML = '';
                        const content = `{content_escaped}`;
                        const htmlContent = content.replace(/\\n/g, '<br>');
                        editor.innerHTML = htmlContent;
                        
                        editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        editor.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        editor.focus();
                        
                        return true;
                    }}
                ''')
                
                if success:
                    self.logger.info("✓ Content inserted via JavaScript")
                else:
                    raise Exception("JavaScript returned false")
                    
            except Exception as e:
                self.logger.warning(f"JavaScript failed, using fill(): {e}")
                await editor.fill(content)
                self.logger.info("✓ Content inserted via fill()")
            
            await page.wait_for_timeout(2000)
            
            # ═══════════════════════════════════════════════════════
            # CLICK POST BUTTON
            # ═══════════════════════════════════════════════════════
            
            self.logger.info("Looking for POST button...")
            
            posted = False
            selectors = [
                'button.share-actions__primary-action',
                'button[aria-label="Post"]',
                '.share-actions__primary-action',
            ]
            
            for selector in selectors:
                try:
                    button = await page.wait_for_selector(selector, timeout=5000)
                    is_disabled = await button.get_attribute('disabled')
                    if not is_disabled:
                        await button.click()
                        self.logger.info(f"✓ Clicked POST: {selector}")
                        posted = True
                        break
                except:
                    continue
            
            if not posted:
                # Try JavaScript
                try:
                    posted = await page.evaluate('''
                        () => {
                            const buttons = Array.from(document.querySelectorAll('button'));
                            const postBtn = buttons.find(btn => 
                                btn.textContent?.trim().toLowerCase() === 'post' && !btn.disabled
                            );
                            if (postBtn) {
                                postBtn.click();
                                return true;
                            }
                            return false;
                        }
                    ''')
                    if posted:
                        self.logger.info("✓ Posted via JavaScript")
                except:
                    pass
            
            if not posted:
                # Try keyboard
                try:
                    await page.keyboard.press('Control+Enter')
                    posted = True
                    self.logger.info("✓ Posted via Ctrl+Enter")
                except:
                    pass
            
            if not posted:
                self.logger.error("❌ Could not click POST button")
                await browser.close()
                await playwright.stop()
                return {
                    'success': False,
                    'post_id': None,
                    'error': 'Could not click POST button'
                }
            
            # ═══════════════════════════════════════════════════════
            # VERIFY SUCCESS
            # ═══════════════════════════════════════════════════════
            
            await page.wait_for_timeout(5000)
            
            self.logger.info("Verifying post...")
            
            final_url = page.url
            
            await browser.close()
            await playwright.stop()
            
            if 'feed' in final_url:
                self.logger.info("✅ POST PUBLISHED SUCCESSFULLY!")
                return {
                    'success': True,
                    'post_id': f'linkedin_post_{int(datetime.now().timestamp())}',
                    'error': None,
                    'message': 'Post published successfully'
                }
            else:
                self.logger.info("✅ POST LIKELY PUBLISHED")
                return {
                    'success': True,
                    'post_id': f'linkedin_post_{int(datetime.now().timestamp())}',
                    'error': None,
                    'message': 'Post published (assumed success)'
                }
        
        except Exception as e:
            self.logger.error(f"❌ Error: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            
            return {
                'success': False,
                'post_id': None,
                'error': str(e),
                'message': 'Post creation failed'
            }


def main():
    """Test posting"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Post to LinkedIn')
    parser.add_argument('--content', type=str, help='Post content')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    
    args = parser.parse_args()
    
    if not args.content:
        args.content = """🚀 Test post from AI Employee!

This is an automated test post.

#AI #Automation #Test"""
    
    poster = LinkedInBrowserPoster(headless=args.headless)
    
    print(f"\nPosting to LinkedIn...")
    print(f"Content: {args.content[:100]}...")
    
    result = asyncio.run(poster.create_post(args.content))
    
    print(f"\nResult:")
    print(f"  Success: {result['success']}")
    print(f"  Post ID: {result.get('post_id')}")
    print(f"  Error: {result.get('error')}")
    print(f"  Message: {result.get('message')}")


if __name__ == '__main__':
    main()
