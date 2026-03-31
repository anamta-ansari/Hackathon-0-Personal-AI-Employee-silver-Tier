#!/usr/bin/env python3
"""
LinkedIn MCP Server - Model Context Protocol for LinkedIn posting

This MCP server handles LinkedIn posting through browser automation.
It provides a reliable interface for the orchestrator to post to LinkedIn.

Usage:
    python -m src.skills.linkedin_mcp_server
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available")


class LinkedInMCPHandler:
    """Handle LinkedIn posting via MCP protocol"""
    
    def __init__(self):
        self.config_dir = Path(__file__).parent.parent.parent / 'config'
        self.session_file = self.config_dir / 'linkedin_session.json'
        self.logs_dir = Path(__file__).parent.parent.parent / 'logs'
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
    def load_session(self):
        """Load saved LinkedIn session"""
        if not self.session_file.exists():
            return None
        
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    
    def post_to_linkedin(self, content: str) -> dict:
        """
        Post content to LinkedIn using browser automation
        
        Args:
            content: Post content (text)
            
        Returns:
            dict: Result with success status and post_id
        """
        result = {
            'success': False,
            'post_id': None,
            'error': None
        }
        
        # Validate content
        if not content or len(content.strip()) == 0:
            result['error'] = 'Empty content'
            return result
        
        if len(content) > 3000:
            result['error'] = 'Content exceeds 3000 characters'
            return result
        
        # Load session
        session = self.load_session()
        if not session:
            result['error'] = 'No LinkedIn session found'
            return result
        
        try:
            with sync_playwright() as p:
                # Launch browser (visible for debugging)
                browser = p.chromium.launch(
                    headless=False,
                    args=['--disable-blink-features=AutomationControlled']
                )
                
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 800},
                    user_agent=session.get('user_agent')
                )
                
                # Load cookies
                cookies = session.get('cookies', [])
                if cookies:
                    context.add_cookies(cookies)
                
                page = context.new_page()
                
                # Navigate to LinkedIn
                logger.info("Navigating to LinkedIn...")
                page.goto('https://www.linkedin.com/feed', wait_until='networkidle', timeout=60000)
                self._wait_random(3, 5)
                
                # Check if logged in
                if 'login' in page.url:
                    result['error'] = 'Not logged in'
                    browser.close()
                    return result
                
                logger.info("Creating post...")
                
                # Find and click "Start a post" button
                post_button = None
                selectors = [
                    'button:has-text("Start a post")',
                    'button:has-text("Start")',
                    '[aria-label*="Start a post"]',
                    '[data-test-id="share-box-feed-entry"]',
                ]
                
                for selector in selectors:
                    try:
                        post_button = page.wait_for_selector(selector, timeout=3000, state='visible')
                        if post_button:
                            post_button.scroll_into_view_if_needed()
                            self._wait_random(1, 2)
                            post_button.click(force=True)
                            logger.info(f"Clicked post button with: {selector}")
                            self._wait_random(2, 3)
                            break
                    except:
                        continue
                
                if not post_button:
                    # Try JavaScript fallback
                    try:
                        page.evaluate('''() => {
                            const btn = Array.from(document.querySelectorAll('button'))
                                .find(b => b.textContent.includes('Start'));
                            if (btn) btn.click();
                        }''')
                        self._wait_random(2, 3)
                    except Exception as e:
                        result['error'] = f'Could not open post editor: {e}'
                        browser.close()
                        return result
                
                # Find editor and type content
                editor_selectors = [
                    '[role="textbox"][aria-label*="post"]',
                    '[contenteditable="true"]',
                ]
                
                editor = None
                for selector in editor_selectors:
                    try:
                        editor = page.wait_for_selector(selector, timeout=3000, state='visible')
                        if editor:
                            break
                    except:
                        continue
                
                if not editor:
                    result['error'] = 'Could not find text editor'
                    browser.close()
                    return result
                
                # Type content
                editor.click()
                self._wait_random(1, 2)
                editor.type(content, delay=30)
                logger.info(f"Typed {len(content)} characters")
                self._wait_random(2, 3)
                
                # Click Post button
                post_submit_selectors = [
                    'button[aria-label="Post"]',
                    'button:has-text("Post")',
                    '.share-box-footer button:first-child',
                ]
                
                submitted = False
                for selector in post_submit_selectors:
                    try:
                        submit_btn = page.wait_for_selector(selector, timeout=3000, state='visible')
                        if submit_btn:
                            # Check if disabled
                            disabled = submit_btn.get_attribute('disabled')
                            if disabled:
                                continue
                            submit_btn.scroll_into_view_if_needed()
                            self._wait_random(1, 2)
                            submit_btn.click(force=True)
                            logger.info(f"Clicked submit with: {selector}")
                            submitted = True
                            break
                    except:
                        continue
                
                if not submitted:
                    # JavaScript fallback
                    try:
                        page.evaluate('''() => {
                            const btn = Array.from(document.querySelectorAll('button'))
                                .find(b => b.textContent.trim() === 'Post' && !b.disabled);
                            if (btn) btn.click();
                        }''')
                    except:
                        pass
                
                # Wait for post to submit
                self._wait_random(3, 5)
                
                # Check if successful (URL should still be feed)
                if 'feed' in page.url:
                    result['success'] = True
                    result['post_id'] = f"mcp_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    logger.info("Post published successfully!")
                else:
                    result['error'] = 'Post may not have published'
                
                browser.close()
                
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Posting error: {e}")
        
        return result
    
    def _wait_random(self, min_sec: float, max_sec: float):
        """Wait random time to appear more human"""
        import time
        import random
        time.sleep(random.uniform(min_sec, max_sec))


def handle_request(request: dict) -> dict:
    """Handle MCP request"""
    handler = LinkedInMCPHandler()
    
    method = request.get('method')
    params = request.get('params', {})
    
    if method == 'linkedin.post':
        content = params.get('content', '')
        return handler.post_to_linkedin(content)
    elif method == 'linkedin.test_session':
        session = handler.load_session()
        return {'success': session is not None}
    else:
        return {'error': f'Unknown method: {method}'}


def main():
    """Main MCP server loop"""
    logger.info("LinkedIn MCP Server starting...")
    
    if not PLAYWRIGHT_AVAILABLE:
        logger.error("Playwright not available")
        sys.exit(1)
    
    # Read requests from stdin
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            response = handle_request(request)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError:
            print(json.dumps({'error': 'Invalid JSON'}), flush=True)
        except Exception as e:
            print(json.dumps({'error': str(e)}), flush=True)


if __name__ == '__main__':
    main()
