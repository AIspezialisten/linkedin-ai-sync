"""
Simplified Playwright automation server with LinkedIn cookies.

This provides a simple JSON-based API for LinkedIn profile scraping
with automatic cookie injection.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# Load environment variables
load_dotenv()

def load_linkedin_cookies() -> List[Dict[str, Any]]:
    """Load LinkedIn cookies from environment variable."""
    cookies_env = os.getenv('LINKEDIN_COOKIES')
    if not cookies_env:
        raise ValueError(
            "LINKEDIN_COOKIES environment variable is required. "
            "Please export your LinkedIn cookies from your browser and add them to the .env file."
        )
    
    try:
        cookies = json.loads(cookies_env)
        if not isinstance(cookies, list):
            raise ValueError("LINKEDIN_COOKIES must be a JSON array of cookie objects")
        
        logging.getLogger(__name__).info(f"✅ Loaded {len(cookies)} LinkedIn cookies from environment")
        return cookies
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in LINKEDIN_COOKIES: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error loading LinkedIn cookies: {str(e)}")


# Cookies are now loaded dynamically from environment variables
# See load_linkedin_cookies() function above


class PlaywrightLinkedInServer:
    """Simplified Playwright server for LinkedIn scraping with automatic authentication."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    async def initialize(self):
        """Initialize Playwright with LinkedIn authentication."""
        try:
            self.playwright = await async_playwright().start()
            
            # Launch browser with no persistent state
            self.browser = await self.playwright.chromium.launch(
                headless=True,  # Set to False for debugging
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    '--incognito',  # Force incognito mode
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            # Create context with LinkedIn cookies (fresh context with no persistence)
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                locale='en-US',
                timezone_id='Europe/Berlin',
                no_viewport=False,
                ignore_https_errors=True
            )
            
            # Add LinkedIn cookies
            await self._add_linkedin_cookies()
            
            # Create page
            self.page = await self.context.new_page()
            
            self.logger.info("✅ Playwright initialized with LinkedIn authentication")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Playwright: {str(e)}")
            return False
    
    async def _add_linkedin_cookies(self):
        """Add LinkedIn cookies to the browser context."""
        playwright_cookies = []
        
        # Load cookies from environment variable
        linkedin_cookies = load_linkedin_cookies()
        
        # Debug: Log which li_at token we're using
        for cookie in linkedin_cookies:
            if cookie['name'] == 'li_at':
                token_preview = cookie['value'][:20] + '...' if len(cookie['value']) > 20 else cookie['value']
                self.logger.info(f"🔑 Using li_at token: {token_preview}")
                break
        
        for cookie in linkedin_cookies:
            playwright_cookie = {
                "name": cookie["name"],
                "value": cookie["value"],
                "domain": cookie["domain"],
                "path": cookie["path"],
                "secure": cookie["secure"],
                "httpOnly": cookie["httpOnly"]
            }
            
            # Add expiration if present
            if "expirationDate" in cookie and cookie["expirationDate"]:
                playwright_cookie["expires"] = cookie["expirationDate"]
            
            # Add sameSite if present
            if "sameSite" in cookie and cookie["sameSite"] != "unspecified":
                if cookie["sameSite"] == "no_restriction":
                    playwright_cookie["sameSite"] = "None"
                else:
                    playwright_cookie["sameSite"] = cookie["sameSite"].title()
            
            playwright_cookies.append(playwright_cookie)
        
        await self.context.add_cookies(playwright_cookies)
        self.logger.info(f"Added {len(playwright_cookies)} LinkedIn cookies")
    
    async def _extract_contact_info(self) -> Dict[str, Any]:
        """Extract contact information by clicking on 'Kontaktinfo' button."""
        try:
            self.logger.info("Attempting to extract contact info...")
            
            # Look for "Kontaktinfo" button with multiple selectors
            contact_info_selectors = [
                'a[data-control-name="contact_see_more"]',
                'button[aria-label*="ontakt"]',  # Partial match for "Kontakt"
                'a[href*="overlay/contact-info"]',
                '.pv-contact-info__contact-type',
                'a:has-text("Kontaktinfo")',
                'button:has-text("Kontaktinfo")',
                '[data-control-name*="contact"]',
                '.pv-top-card-v2-ctas a:first-child',
                '.pv-s-profile-actions a:first-child'
            ]
            
            contact_button = None
            for selector in contact_info_selectors:
                try:
                    # Try to find the element
                    elements = await self.page.query_selector_all(selector)
                    for element in elements:
                        text = await element.inner_text()
                        if 'kontakt' in text.lower():
                            contact_button = element
                            self.logger.info(f"Found contact button with selector: {selector}, text: {text}")
                            break
                    if contact_button:
                        break
                except:
                    continue
            
            # Fallback: look for any link/button containing "kontakt"
            if not contact_button:
                self.logger.info("Trying fallback approach to find contact info...")
                contact_button = await self.page.evaluate("""
                    () => {
                        // Look for any element containing "kontakt" text
                        const elements = document.querySelectorAll('a, button');
                        for (const el of elements) {
                            if (el.textContent && el.textContent.toLowerCase().includes('kontakt')) {
                                return el;
                            }
                        }
                        return null;
                    }
                """)
            
            if contact_button:
                self.logger.info("Clicking on contact info button...")
                
                # Click the button
                await contact_button.click()
                
                # Wait for the overlay to appear
                await asyncio.sleep(2)
                
                # Wait for contact info modal/overlay
                try:
                    await self.page.wait_for_selector('.pv-contact-info__contact-type', timeout=5000)
                except:
                    # Try alternative selectors for the modal
                    modal_selectors = [
                        '[role="dialog"]',
                        '.artdeco-modal',
                        '.pv-contact-info',
                        '.contact-info',
                        '.overlay-content'
                    ]
                    for modal_selector in modal_selectors:
                        try:
                            await self.page.wait_for_selector(modal_selector, timeout=2000)
                            break
                        except:
                            continue
                
                # Extract contact information from the overlay
                contact_data = await self.page.evaluate("""
                    () => {
                        const contactInfo = {
                            email: '',
                            phone: '',
                            website: '',
                            other: []
                        };
                        
                        // Look for contact info in modal/overlay
                        const contactSelectors = [
                            '.pv-contact-info__contact-type',
                            '.contact-info-item',
                            '.pv-contact-info__ci-container',
                            '[role="dialog"] .contact-info',
                            '.artdeco-modal .contact-info'
                        ];
                        
                        for (const selector of contactSelectors) {
                            const contactElements = document.querySelectorAll(selector);
                            
                            contactElements.forEach(element => {
                                const text = element.textContent || '';
                                const href = element.querySelector('a')?.href || '';
                                
                                // Extract email
                                if (text.includes('@') || href.includes('mailto:')) {
                                    const emailMatch = text.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/);
                                    if (emailMatch) {
                                        contactInfo.email = emailMatch[0];
                                    } else if (href.includes('mailto:')) {
                                        contactInfo.email = href.replace('mailto:', '');
                                    }
                                }
                                
                                // Extract phone number (more restrictive validation)
                                // Skip if this text contains linkedin.com (avoid extracting from URLs)
                                if (!text.toLowerCase().includes('linkedin.com')) {
                                    // Include en-dash (–), em-dash (—), and other phone characters
                                    const phoneMatch = text.match(/[\+]?[0-9][\d\s\-–—\(\)\.]{8,}/);
                                    if (phoneMatch && !contactInfo.phone) {
                                        let cleanPhone = phoneMatch[0].replace(/\s+/g, ' ').trim();
                                        cleanPhone = cleanPhone.replace(/\(\s*$/, '').trim();
                                        
                                        // Remove all non-digit characters for validation
                                        const digitsOnly = cleanPhone.replace(/\D/g, '');
                                        
                                        // Validate: should be 9-15 digits and not look like a year/date
                                        if (digitsOnly.length >= 9 && digitsOnly.length <= 15 && 
                                            !digitsOnly.match(/^(19|20)\d{2}$/) &&  // Not a 4-digit year
                                            !digitsOnly.match(/^(19|20)\d{6}$/) &&  // Not a date like 20250618
                                            !digitsOnly.match(/^\d{4}$/) &&         // Not a 4-digit number
                                            !digitsOnly.match(/^\d{2}$/) &&         // Not a 2-digit number
                                            digitsOnly.indexOf('0') !== 0 || digitsOnly.length > 4) { // If starts with 0, must be longer than 4 digits
                                            contactInfo.phone = cleanPhone;
                                        }
                                    }
                                }
                                
                                // Extract website
                                if (href && (href.includes('http') || href.includes('www')) && 
                                    !href.includes('linkedin.com') && !href.includes('mailto:')) {
                                    contactInfo.website = href;
                                }
                                
                                // Store other contact info (clean up whitespace)
                                if (text.trim() && !text.includes('Kontaktinfo')) {
                                    const cleanText = text.replace(/\s+/g, ' ').trim();
                                    if (cleanText && !contactInfo.other.includes(cleanText)) {
                                        contactInfo.other.push(cleanText);
                                    }
                                }
                            });
                        }
                        
                        // Additional extraction from any visible links/text in modal
                        const modal = document.querySelector('[role="dialog"], .artdeco-modal, .pv-contact-info');
                        if (modal) {
                            const allLinks = modal.querySelectorAll('a');
                            allLinks.forEach(link => {
                                const href = link.href;
                                const text = link.textContent;
                                
                                if (href.includes('mailto:') && !contactInfo.email) {
                                    contactInfo.email = href.replace('mailto:', '');
                                } else if (href.includes('tel:') && !contactInfo.phone) {
                                    contactInfo.phone = href.replace('tel:', '');
                                } else if (text && text.includes('@') && !contactInfo.email) {
                                    const emailMatch = text.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/);
                                    if (emailMatch) {
                                        contactInfo.email = emailMatch[0];
                                    }
                                }
                            });
                        }
                        
                        return contactInfo;
                    }
                """)
                
                # Close the modal by pressing Escape or clicking close button
                try:
                    await self.page.keyboard.press('Escape')
                    await asyncio.sleep(1)
                except:
                    pass
                
                self.logger.info(f"Extracted contact info: {contact_data}")
                return contact_data
                
            else:
                self.logger.info("Contact info button not found")
                return {}
                
        except Exception as e:
            self.logger.error(f"Error extracting contact info: {str(e)}")
            return {}
    
    async def navigate_to_profile(self, profile_url: str) -> Dict[str, Any]:
        """Navigate to a LinkedIn profile and extract data."""
        try:
            self.logger.info(f"🌐 Navigating to: {profile_url}")
            
            # Check if we're already logged in
            self.logger.info("📋 Checking current page and cookies...")
            current_url = self.page.url
            self.logger.info(f"Current URL: {current_url}")
            
            # Get current cookies for debugging
            cookies = await self.context.cookies()
            linkedin_cookies = [c for c in cookies if 'linkedin' in c['domain']]
            self.logger.info(f"LinkedIn cookies found: {len(linkedin_cookies)}")
            
            # Try to navigate with more detailed logging
            self.logger.info(f"🚀 Starting navigation to {profile_url}...")
            
            try:
                # First try with a shorter timeout and domcontentloaded
                self.logger.info(f"🌐 Attempting to navigate to: {profile_url}")
                await self.page.goto(profile_url, wait_until='domcontentloaded', timeout=15000)
                self.logger.info("✅ Page loaded (domcontentloaded)")
                
                # Wait a bit more for dynamic content
                await asyncio.sleep(2)
                
                # Check if we hit a login/challenge page
                current_url = self.page.url
                page_title = await self.page.title()
                self.logger.info(f"📄 Current URL after navigation: {current_url}")
                self.logger.info(f"📄 Page title: {page_title}")
                
                # Take an early screenshot to see what we got
                early_screenshot = f"data/screenshots/linkedin_early_{hash(profile_url)}.png"
                await self.page.screenshot(path=early_screenshot)
                self.logger.info(f"📸 Early screenshot saved: {early_screenshot}")
                
                # Check for LinkedIn login/challenge indicators (more specific)
                page_content = await self.page.content()
                
                # Check if we can see key profile elements (more reliable than text patterns)
                has_profile_elements = await self.page.evaluate("""
                    () => {
                        // Look for key LinkedIn profile page elements
                        const profileIndicators = [
                            'h1.text-heading-xlarge',           // Profile name
                            '.pv-text-details__left-panel',    // Profile details panel
                            '.pv-top-card',                     // Profile top card
                            '[data-field="headline"]',         // Headline field
                            '.pv-top-card-v2-ctas',           // Profile action buttons
                            '.pv-contact-info',                 // Contact info
                            'button[aria-label*="Nachricht"]', // German "Message" button
                            'button[aria-label*="Kontakt"]'     // German "Contact" button
                        ];
                        
                        // If we find any of these, we're on a profile page
                        for (const selector of profileIndicators) {
                            if (document.querySelector(selector)) {
                                return true;
                            }
                        }
                        
                        // Also check for common profile text patterns
                        const bodyText = document.body.textContent || '';
                        if (bodyText.includes('Follower') || bodyText.includes('Kontakte') || 
                            bodyText.includes('Nachricht') || bodyText.includes('Kontaktinfo')) {
                            return true;
                        }
                        
                        return false;
                    }
                """)
                
                # Only flag as login page if we have explicit login indicators AND no profile elements
                login_indicators = [
                    'sign in to linkedin', 'join linkedin', 'sign up', 'challenge', 
                    'security verification', 'please sign in', 'anmelden', 'registrieren'
                ]
                has_login_indicators = any(indicator in page_content.lower() for indicator in login_indicators)
                
                if has_login_indicators and not has_profile_elements:
                    self.logger.warning("⚠️  Detected login/challenge page!")
                    return {
                        "success": False,
                        "error": "LinkedIn login/challenge page detected",
                        "html_content": page_content,
                        "screenshot_path": early_screenshot,
                        "current_url": current_url,
                        "page_title": page_title
                    }
                else:
                    self.logger.info(f"✅ Profile page detected (has_profile_elements: {has_profile_elements})")
                
                # Wait for network to settle (with fallback)
                self.logger.info("⏳ Waiting for network to settle...")
                try:
                    await self.page.wait_for_load_state('networkidle', timeout=5000)
                    self.logger.info("✅ Network settled")
                except:
                    self.logger.info("⚠️  Network still active, but proceeding anyway")
                
            except Exception as nav_error:
                self.logger.error(f"❌ Navigation failed: {str(nav_error)}")
                
                # Try to get some diagnostic info anyway
                try:
                    current_url = self.page.url
                    page_title = await self.page.title()
                    emergency_screenshot = f"data/screenshots/linkedin_error_{hash(profile_url)}.png"
                    await self.page.screenshot(path=emergency_screenshot)
                    
                    return {
                        "success": False,
                        "error": f"Navigation timeout: {str(nav_error)}",
                        "html_content": await self.page.content() if self.page else "",
                        "screenshot_path": emergency_screenshot,
                        "current_url": current_url,
                        "page_title": page_title,
                        "navigation_error": str(nav_error)
                    }
                except:
                    return {
                        "success": False,
                        "error": f"Navigation failed completely: {str(nav_error)}"
                    }
            
            # Wait for page to stabilize
            await asyncio.sleep(3)
            
            # Take initial screenshot for debugging
            screenshot_path = f"data/screenshots/linkedin_profile_{hash(profile_url)}.png"
            await self.page.screenshot(path=screenshot_path)
            
            # Try to click on "Kontaktinfo" to get contact details
            contact_info_data = await self._extract_contact_info()
            
            # Take screenshot after contact info extraction
            contact_screenshot_path = f"data/screenshots/linkedin_contact_info_{hash(profile_url)}.png"
            await self.page.screenshot(path=contact_screenshot_path)
            
            # Extract profile data
            profile_data = await self.page.evaluate("""
                () => {
                    const data = {};
                    
                    // Debug: Log available h1 elements
                    const allH1s = document.querySelectorAll('h1');
                    console.log('Found H1 elements:', Array.from(allH1s).map(h1 => ({
                        text: h1.textContent.trim(),
                        classes: h1.className,
                        id: h1.id
                    })));
                    
                    // Extract name - LinkedIn current structure
                    const nameSelectors = [
                        'h1.text-heading-xlarge',
                        '.pv-text-details__left-panel h1', 
                        '.text-heading-xlarge',
                        '.pv-top-card h1',
                        'h1[class*="heading"]',
                        'h1[class*="text-heading"]',
                        '.pv-text-details__left-panel .text-heading-xlarge',
                        '.pv-top-card .pv-text-details__left-panel h1',
                        '.pv-top-card .text-heading-xlarge',
                        '.artdeco-entity-lockup__title a',
                        '.pv-entity__summary-info h1',
                        'main h1',
                        '[data-field="name"] h1',
                        '.pv-top-card--list li:first-child'
                    ];
                    
                    for (const selector of nameSelectors) {
                        const element = document.querySelector(selector);
                        if (element && element.textContent.trim()) {
                            data.full_name = element.textContent.trim();
                            break;
                        }
                    }
                    
                    // Additional fallback - look for any h1 in the main profile area
                    if (!data.full_name) {
                        const allH1s = document.querySelectorAll('h1');
                        for (const h1 of allH1s) {
                            const text = h1.textContent.trim();
                            // Skip if it looks like a section header or contains emoji/symbols
                            if (text && !text.includes('•') && !text.includes('→') && 
                                text.split(' ').length >= 2 && text.split(' ').length <= 5) {
                                data.full_name = text;
                                break;
                            }
                        }
                    }
                    
                    // Extract headline
                    const headlineSelectors = [
                        '.text-body-medium.break-words',
                        '.pv-text-details__left-panel .text-body-medium',
                        '[data-field="headline"]',
                        '.pv-top-card--list li:nth-child(2)'
                    ];
                    
                    for (const selector of headlineSelectors) {
                        const element = document.querySelector(selector);
                        if (element && element.textContent.trim()) {
                            data.headline = element.textContent.trim();
                            break;
                        }
                    }
                    
                    // Extract location
                    const locationSelectors = [
                        '.text-body-small.inline.t-black--light.break-words',
                        '.pv-text-details__left-panel .text-body-small',
                        '[data-field="location"]'
                    ];
                    
                    for (const selector of locationSelectors) {
                        const element = document.querySelector(selector);
                        if (element && element.textContent.trim()) {
                            data.location = element.textContent.trim();
                            break;
                        }
                    }
                    
                    // Extract about section
                    const aboutSelectors = [
                        '.pv-about-section .inline-show-more-text',
                        '[data-field="summary"]',
                        '.pv-about__summary-text'
                    ];
                    
                    for (const selector of aboutSelectors) {
                        const element = document.querySelector(selector);
                        if (element && element.textContent.trim()) {
                            data.about = element.textContent.trim();
                            break;
                        }
                    }
                    
                    // Extract experience
                    data.experience = [];
                    const experienceElements = document.querySelectorAll('#experience ~ .pvs-list .pvs-entity, .experience-section .pv-entity__summary-info');
                    experienceElements.forEach((elem, index) => {
                        if (index < 5) { // Limit to 5 entries
                            const text = elem.textContent.trim();
                            if (text) data.experience.push(text);
                        }
                    });
                    
                    // Extract education
                    data.education = [];
                    const educationElements = document.querySelectorAll('#education ~ .pvs-list .pvs-entity, .education-section .pv-entity__summary-info');
                    educationElements.forEach((elem, index) => {
                        if (index < 3) { // Limit to 3 entries
                            const text = elem.textContent.trim();
                            if (text) data.education.push(text);
                        }
                    });
                    
                    // Extract skills
                    data.skills = [];
                    const skillElements = document.querySelectorAll('#skills ~ .pvs-list .pvs-entity__path, .skills-section .pv-skill-category-entity__name span');
                    skillElements.forEach((elem, index) => {
                        if (index < 10) { // Limit to 10 skills
                            const text = elem.textContent.trim();
                            if (text) data.skills.push(text);
                        }
                    });
                    
                    // Extract connections count
                    const connectionsSelectors = [
                        '.t-black--light.t-normal',
                        '.pv-top-card--list-bullet li',
                        '[data-field="connections"]'
                    ];
                    
                    for (const selector of connectionsSelectors) {
                        const element = document.querySelector(selector);
                        if (element && element.textContent.includes('connection')) {
                            data.connections_count = element.textContent.trim();
                            break;
                        }
                    }
                    
                    // Current position (try to extract from headline or experience)
                    if (data.headline) {
                        data.current_position = data.headline;
                    } else if (data.experience && data.experience.length > 0) {
                        data.current_position = data.experience[0];
                    }
                    
                    // Get page title for verification
                    data.page_title = document.title;
                    
                    return data;
                }
            """)
            
            # Merge contact info into profile data
            if contact_info_data:
                profile_data['contact_email'] = contact_info_data.get('email', '')
                profile_data['contact_phone'] = contact_info_data.get('phone', '')
                profile_data['contact_website'] = contact_info_data.get('website', '')
                profile_data['contact_other'] = contact_info_data.get('other', [])
            
            # Get page content as backup
            html_content = await self.page.content()
            
            return {
                "success": True,
                "extracted_data": profile_data,
                "html_content": html_content,
                "screenshot_path": screenshot_path,
                "contact_screenshot_path": contact_screenshot_path,
                "contact_info": contact_info_data,
                "page_title": await self.page.title()
            }
            
        except Exception as e:
            self.logger.error(f"Error navigating to profile {profile_url}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "html_content": await self.page.content() if self.page else "",
                "screenshot_path": None
            }
    
    async def cleanup(self):
        """Clean up browser resources."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            
            self.logger.info("✅ Playwright cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")


async def handle_command(command: Dict[str, Any]) -> Dict[str, Any]:
    """Handle a single command."""
    action = command.get("action")
    args = command.get("args", {})
    
    if action == "scrape_profile":
        profile_url = args.get("profile_url")
        if not profile_url:
            return {"error": "profile_url is required"}
        
        server = PlaywrightLinkedInServer()
        try:
            # Add server-level timeout (80 seconds total)
            async def scrape_with_timeout():
                if await server.initialize():
                    return await server.navigate_to_profile(profile_url)
                else:
                    return {"error": "Failed to initialize Playwright"}
            
            result = await asyncio.wait_for(scrape_with_timeout(), timeout=80.0)
            return result
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Server-level timeout after 80 seconds",
                "profile_url": profile_url
            }
        finally:
            await server.cleanup()
    
    elif action == "health_check":
        return {"success": True, "status": "Playwright LinkedIn server is running"}
    
    else:
        return {"error": f"Unknown action: {action}"}


async def main():
    """Main server loop - reads JSON commands from stdin."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stderr)]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("🎭 Starting Playwright LinkedIn Server...")
    
    try:
        while True:
            # Read command from stdin
            line = sys.stdin.readline()
            if not line:
                break
            
            try:
                command = json.loads(line.strip())
                result = await handle_command(command)
                
                # Write result to stdout
                print(json.dumps(result))
                sys.stdout.flush()
                
            except json.JSONDecodeError as e:
                error_result = {"error": f"Invalid JSON: {str(e)}"}
                print(json.dumps(error_result))
                sys.stdout.flush()
            except Exception as e:
                error_result = {"error": f"Command error: {str(e)}"}
                print(json.dumps(error_result))
                sys.stdout.flush()
                
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
    
    logger.info("🎭 Playwright LinkedIn Server stopped")


if __name__ == "__main__":
    asyncio.run(main())