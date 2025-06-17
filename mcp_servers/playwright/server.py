"""
Custom Playwright MCP Server with LinkedIn cookies pre-configured.

This server extends the basic Playwright functionality to automatically
include LinkedIn authentication cookies for seamless LinkedIn automation.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

from mcp.server import Server
from mcp.types import Tool, TextContent
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# LinkedIn cookies for authentication
LINKEDIN_COOKIES = [
    {"domain": ".linkedin.com", "expirationDate": 1781728252.04868, "hostOnly": False, "httpOnly": False, "name": "bcookie", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "\"v=2&09c343a7-5ea8-41b1-8ba2-53c8f0055dda\""},
    {"domain": ".linkedin.com", "expirationDate": 1764485137.459191, "hostOnly": False, "httpOnly": False, "name": "li_gc", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "MTswOzE3NDg5MzMxMzY7MjswMjHlv/s4qfh28Ka4j+xiOZrMxst9tUXVu9IBqvDB1818zQ=="},
    {"domain": ".www.linkedin.com", "expirationDate": 1781728252.048789, "hostOnly": False, "httpOnly": True, "name": "bscookie", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "\"v=1&20250603064537b205a416-432a-410c-89f6-f2c635f30a3eAQF70u1jfZyLe6tYUD9Rqa-QHJzQsa-B\""},
    {"domain": "www.linkedin.com", "expirationDate": 1781726921, "hostOnly": True, "httpOnly": False, "name": "li_alerts", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "e30="},
    {"domain": "www.linkedin.com", "expirationDate": 1764485227, "hostOnly": True, "httpOnly": False, "name": "g_state", "path": "/", "sameSite": "unspecified", "secure": False, "session": False, "storeId": "0", "value": "{\"i_l\":0}"},
    {"domain": ".www.linkedin.com", "expirationDate": 1751401852, "hostOnly": False, "httpOnly": False, "name": "timezone", "path": "/", "sameSite": "unspecified", "secure": True, "session": False, "storeId": "0", "value": "Europe/Berlin"},
    {"domain": ".www.linkedin.com", "expirationDate": 1765747852, "hostOnly": False, "httpOnly": False, "name": "li_theme", "path": "/", "sameSite": "unspecified", "secure": True, "session": False, "storeId": "0", "value": "light"},
    {"domain": ".www.linkedin.com", "expirationDate": 1765747852, "hostOnly": False, "httpOnly": False, "name": "li_theme_set", "path": "/", "sameSite": "unspecified", "secure": True, "session": False, "storeId": "0", "value": "app"},
    {"domain": ".linkedin.com", "expirationDate": 1780469231.894047, "hostOnly": False, "httpOnly": True, "name": "dfpfpt", "path": "/", "sameSite": "unspecified", "secure": True, "session": False, "storeId": "0", "value": "c732bad30cf744549900eaeafb6f06ff"},
    {"domain": ".linkedin.com", "hostOnly": False, "httpOnly": True, "name": "fptctx2", "path": "/", "sameSite": "unspecified", "secure": True, "session": True, "storeId": "0", "value": "taBcrIH61PuCVH7eNCyH0FC0izOzUpX5wN2Z%252b5egc%252f5DUzJHCEe5tD6MVX95Q25smbO4Cnw70HdVp7DWLtin93YJeF6lzAsnB8BmItl%252bHcIt2p%252buE3f%252f1oh0BRRlKIcHbUk5cH0AJedLyQGtMa08LySMedfi%252bbmJbUM9MWzYOjII91iLgY%252bFolXo3n05kU6%252bTHdPQq%252fcRHOj%252fdGFepJAecRrVUh2xiUHjxpnrpHvwirZCke5Fz2DdvGPGnt3WFcLq%252b9QGbb1%252fn3Ur68KOZdgu4x%252ftM%252bPoWLpXXdYCXPu%252f3yG%252fxnQZISdJr8ZEndgYrye5IllY9EYIgJK57MRD87CVz%252f42qoNbxRH3Yf1a3boUnM%253d"},
    {"domain": ".www.linkedin.com", "expirationDate": 1781726953.676794, "hostOnly": False, "httpOnly": True, "name": "li_rm", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "AQHoeHwRq8C30gAAAZd_ghE_Pf1aYjTT-r2JKmE04W7rucOb3tVQJpZkbwg73hOH6IXB5Fc5eyAfXUG2ceaNrg2gSICE8iosLbGqosZTyNGjNaiMUG_wPhVFqp32e8FzTsDR_tFOZZrINjsJRex5ffnKw3hs0GKcX9OgeDjBPuNdeNqtu4vs0J0eYF3bLcBy8CeWts4kiAMb_IhlymR9YOF6-GecQCN80RstpU0dXXdntQ4nZut3z38DlPQ21fLhnYhDGvdi20N-PfQ4RkjRZoh08GBo3xjOfcJYTSGS1vO6-M79dM1e1II8CJgVTgaty5LIVMB6tPtDNBYiqmbS1w"},
    {"domain": "www.linkedin.com", "expirationDate": 1750194520.184038, "hostOnly": True, "httpOnly": False, "name": "li_g_recent_logout", "path": "/", "sameSite": "unspecified", "secure": False, "session": False, "storeId": "0", "value": "v=1&true"},
    {"domain": ".linkedin.com", "expirationDate": 1784750920.184463, "hostOnly": False, "httpOnly": False, "name": "visit", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "v=1&M"},
    {"domain": ".www.linkedin.com", "expirationDate": 1757966953.677251, "hostOnly": False, "httpOnly": False, "name": "JSESSIONID", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "\"ajax:5746800555694694412\""},
    {"domain": ".www.linkedin.com", "expirationDate": 1781726953.677146, "hostOnly": False, "httpOnly": True, "name": "li_at", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "AQEDAR3oGXYBc8GCAAABl3-ClRoAAAGXo48ZGk4AL3IqMQpmwg2R5Exj5x0BNRMdqMcJTKqN86geVul8xE8ZRrRHEKbaaIXKEWTcW8mbDyyStoeO86WgZUlgbUczR0umLSnCVOZ0-xCiwxhRVunjnZd8"},
    {"domain": ".linkedin.com", "expirationDate": 1757966953.677202, "hostOnly": False, "httpOnly": False, "name": "liap", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "true"},
    {"domain": ".linkedin.com", "expirationDate": 1750249630.992858, "hostOnly": False, "httpOnly": False, "name": "lidc", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "\"b=TB34:s=T:r=T:a=T:p=T:g=4465:u=501:x=1:i=1750190954:t=1750249631:v=2:sig=AQH_q0Fyyj_ugqKS2filk1mLofZn4sxe\""},
    {"domain": ".linkedin.com", "expirationDate": 1750193956.135587, "hostOnly": False, "httpOnly": True, "name": "__cf_bm", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "T11XAZgoJ1kTJyywIbYmilOH2_VprX_RZwN1tNgRd5g-1750192156-1.0.1.1-fOtOp3vzkbD.d7kxuOHmKjq2AIv_BlzL4l4WvZOIg9_iHJDOJwLyQ7iV.e5WslDttz7B0XcrTZH8NEbTzd1w_MvVrZLPutC6iVmISqQDE9E"},
    {"domain": ".linkedin.com", "expirationDate": 1765744216.104882, "hostOnly": False, "httpOnly": False, "name": "li_mc", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "MTsyMTsxNzUwMTkyMjE2OzI7MDIxW/xgxaeFs0wlu29xDv9Gc+sx3kAK+052IMHCGjgI91Y="},
    {"domain": ".linkedin.com", "hostOnly": False, "httpOnly": False, "name": "lang", "path": "/", "sameSite": "no_restriction", "secure": True, "session": True, "storeId": "0", "value": "v=2&lang=de-de"},
    {"domain": ".linkedin.com", "expirationDate": 1752784256, "hostOnly": False, "httpOnly": False, "name": "UserMatchHistory", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "AQKWInDv6-71MwAAAZd_lnLSaJ7lmtjBw1lBmOTmMxVrJ80vf0qugL-9avXQEcrhqaMz6KnjoHCyfODpUC3kcmlXzMNsYpWi3HsAfvmvnJ-O3czk9wFht84jLxV-ZpP7mvGMW2n2gzCVGa7RorCavYV9EOw7GarIQmiVWwjQ4_ovlnQeEJIIkPQEJTbVDwgOi73BE2jZZiyOgTw2y_mPa66-Y14_0wkRPOrYuYaIeSkm7pPF74KCxKfoNE8EFOOg0cFfG0SOsbaJbOPwhgLgI-r5fipV1zKw_i7AAdy0T-3VEGOMYA"}
]


class PlaywrightMCPServer:
    """Playwright MCP Server with LinkedIn cookie support."""
    
    def __init__(self):
        self.server = Server("playwright-linkedin")
        self.logger = logging.getLogger(__name__)
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.contexts: Dict[str, BrowserContext] = {}
        self.pages: Dict[str, Page] = {}
        self._context_counter = 0
        self._page_counter = 0
        
        # Register tools
        self._register_tools()
    
    def _register_tools(self):
        """Register all available tools."""
        
        @self.server.call_tool()
        async def launch_browser(browser_type: str = "chromium", headless: bool = True, **options) -> List[TextContent]:
            """Launch a new browser instance."""
            try:
                if self.playwright is None:
                    self.playwright = await async_playwright().start()
                
                browser_launcher = getattr(self.playwright, browser_type)
                self.browser = await browser_launcher.launch(headless=headless, **options)
                
                self.logger.info(f"Browser {browser_type} launched successfully")
                return [TextContent(type="text", text=f"Browser {browser_type} launched")]
                
            except Exception as e:
                self.logger.error(f"Failed to launch browser: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        @self.server.call_tool()
        async def create_context(linkedin_auth: bool = True, **options) -> List[TextContent]:
            """Create a new browser context, optionally with LinkedIn authentication."""
            try:
                if not self.browser:
                    return [TextContent(type="text", text="Error: No browser launched")]
                
                # Default context options
                context_options = {
                    "viewport": {"width": 1920, "height": 1080},
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    **options
                }
                
                context = await self.browser.new_context(**context_options)
                
                # Add LinkedIn cookies if requested
                if linkedin_auth:
                    await self._add_linkedin_cookies(context)
                    self.logger.info("LinkedIn authentication cookies added")
                
                context_id = f"context_{self._context_counter}"
                self.contexts[context_id] = context
                self._context_counter += 1
                
                return [TextContent(type="text", text=f"Context created: {context_id}")]
                
            except Exception as e:
                self.logger.error(f"Failed to create context: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        @self.server.call_tool()
        async def create_page(context_id: str) -> List[TextContent]:
            """Create a new page in the specified context."""
            try:
                if context_id not in self.contexts:
                    return [TextContent(type="text", text=f"Error: Context {context_id} not found")]
                
                context = self.contexts[context_id]
                page = await context.new_page()
                
                page_id = f"page_{self._page_counter}"
                self.pages[page_id] = page
                self._page_counter += 1
                
                return [TextContent(type="text", text=f"Page created: {page_id}")]
                
            except Exception as e:
                self.logger.error(f"Failed to create page: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        @self.server.call_tool()
        async def navigate(page_id: str, url: str, wait_until: str = "networkidle") -> List[TextContent]:
            """Navigate to a URL."""
            try:
                if page_id not in self.pages:
                    return [TextContent(type="text", text=f"Error: Page {page_id} not found")]
                
                page = self.pages[page_id]
                await page.goto(url, wait_until=wait_until)
                
                title = await page.title()
                return [TextContent(type="text", text=f"Navigated to {url} - Title: {title}")]
                
            except Exception as e:
                self.logger.error(f"Failed to navigate: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        @self.server.call_tool()
        async def get_page_content(page_id: str) -> List[TextContent]:
            """Get the HTML content of a page."""
            try:
                if page_id not in self.pages:
                    return [TextContent(type="text", text=f"Error: Page {page_id} not found")]
                
                page = self.pages[page_id]
                content = await page.content()
                
                return [TextContent(type="text", text=content)]
                
            except Exception as e:
                self.logger.error(f"Failed to get content: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        @self.server.call_tool()
        async def click_element(page_id: str, selector: str, timeout: int = 30000) -> List[TextContent]:
            """Click an element on the page."""
            try:
                if page_id not in self.pages:
                    return [TextContent(type="text", text=f"Error: Page {page_id} not found")]
                
                page = self.pages[page_id]
                await page.click(selector, timeout=timeout)
                
                return [TextContent(type="text", text=f"Clicked element: {selector}")]
                
            except Exception as e:
                self.logger.error(f"Failed to click element: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        @self.server.call_tool()
        async def type_text(page_id: str, selector: str, text: str, timeout: int = 30000) -> List[TextContent]:
            """Type text into an element."""
            try:
                if page_id not in self.pages:
                    return [TextContent(type="text", text=f"Error: Page {page_id} not found")]
                
                page = self.pages[page_id]
                await page.fill(selector, text, timeout=timeout)
                
                return [TextContent(type="text", text=f"Typed text into {selector}")]
                
            except Exception as e:
                self.logger.error(f"Failed to type text: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        @self.server.call_tool()
        async def wait_for_selector(page_id: str, selector: str, timeout: int = 30000) -> List[TextContent]:
            """Wait for an element to appear."""
            try:
                if page_id not in self.pages:
                    return [TextContent(type="text", text=f"Error: Page {page_id} not found")]
                
                page = self.pages[page_id]
                await page.wait_for_selector(selector, timeout=timeout)
                
                return [TextContent(type="text", text=f"Element found: {selector}")]
                
            except Exception as e:
                self.logger.error(f"Failed to wait for selector: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        @self.server.call_tool()
        async def get_element_text(page_id: str, selector: str) -> List[TextContent]:
            """Get text content of an element."""
            try:
                if page_id not in self.pages:
                    return [TextContent(type="text", text=f"Error: Page {page_id} not found")]
                
                page = self.pages[page_id]
                text = await page.inner_text(selector)
                
                return [TextContent(type="text", text=text)]
                
            except Exception as e:
                self.logger.error(f"Failed to get element text: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        @self.server.call_tool()
        async def screenshot(page_id: str, path: Optional[str] = None, full_page: bool = False) -> List[TextContent]:
            """Take a screenshot of the page."""
            try:
                if page_id not in self.pages:
                    return [TextContent(type="text", text=f"Error: Page {page_id} not found")]
                
                page = self.pages[page_id]
                screenshot_path = path or f"/app/data/screenshot_{page_id}.png"
                
                await page.screenshot(path=screenshot_path, full_page=full_page)
                
                return [TextContent(type="text", text=f"Screenshot saved: {screenshot_path}")]
                
            except Exception as e:
                self.logger.error(f"Failed to take screenshot: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        @self.server.call_tool()
        async def extract_linkedin_profiles(page_id: str) -> List[TextContent]:
            """Extract LinkedIn profile information from the current page."""
            try:
                if page_id not in self.pages:
                    return [TextContent(type="text", text=f"Error: Page {page_id} not found")]
                
                page = self.pages[page_id]
                
                # Extract profile data using JavaScript
                profile_data = await page.evaluate("""
                    () => {
                        const profiles = [];
                        
                        // Extract from search results
                        const profileCards = document.querySelectorAll('[data-view-name="search-entity-result"]');
                        
                        profileCards.forEach(card => {
                            const nameElement = card.querySelector('a[data-test-app-aware-link] span[aria-hidden="true"]');
                            const titleElement = card.querySelector('.entity-result__primary-subtitle');
                            const locationElement = card.querySelector('.entity-result__secondary-subtitle');
                            const linkElement = card.querySelector('a[data-test-app-aware-link]');
                            
                            if (nameElement && linkElement) {
                                profiles.push({
                                    name: nameElement.textContent.trim(),
                                    title: titleElement ? titleElement.textContent.trim() : '',
                                    location: locationElement ? locationElement.textContent.trim() : '',
                                    profile_url: linkElement.href,
                                    extracted_at: new Date().toISOString()
                                });
                            }
                        });
                        
                        return profiles;
                    }
                """)
                
                return [TextContent(type="text", text=json.dumps(profile_data, indent=2))]
                
            except Exception as e:
                self.logger.error(f"Failed to extract profiles: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        @self.server.call_tool()
        async def close_page(page_id: str) -> List[TextContent]:
            """Close a page."""
            try:
                if page_id not in self.pages:
                    return [TextContent(type="text", text=f"Error: Page {page_id} not found")]
                
                page = self.pages[page_id]
                await page.close()
                del self.pages[page_id]
                
                return [TextContent(type="text", text=f"Page {page_id} closed")]
                
            except Exception as e:
                self.logger.error(f"Failed to close page: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        @self.server.call_tool()
        async def close_context(context_id: str) -> List[TextContent]:
            """Close a browser context."""
            try:
                if context_id not in self.contexts:
                    return [TextContent(type="text", text=f"Error: Context {context_id} not found")]
                
                context = self.contexts[context_id]
                await context.close()
                del self.contexts[context_id]
                
                # Clean up pages in this context
                pages_to_remove = [pid for pid, page in self.pages.items() 
                                 if page.context == context]
                for pid in pages_to_remove:
                    del self.pages[pid]
                
                return [TextContent(type="text", text=f"Context {context_id} closed")]
                
            except Exception as e:
                self.logger.error(f"Failed to close context: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        @self.server.call_tool()
        async def close_browser() -> List[TextContent]:
            """Close the browser."""
            try:
                if self.browser:
                    await self.browser.close()
                    self.browser = None
                    self.contexts.clear()
                    self.pages.clear()
                
                if self.playwright:
                    await self.playwright.stop()
                    self.playwright = None
                
                return [TextContent(type="text", text="Browser closed")]
                
            except Exception as e:
                self.logger.error(f"Failed to close browser: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def _add_linkedin_cookies(self, context: BrowserContext):
        """Add LinkedIn authentication cookies to a context."""
        try:
            # Convert our cookie format to Playwright format
            playwright_cookies = []
            
            for cookie in LINKEDIN_COOKIES:
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
            
            # Add cookies to the context
            await context.add_cookies(playwright_cookies)
            self.logger.info(f"Added {len(playwright_cookies)} LinkedIn cookies")
            
        except Exception as e:
            self.logger.error(f"Failed to add LinkedIn cookies: {str(e)}")
            raise
    
    def get_available_tools(self) -> List[Tool]:
        """Get list of available tools."""
        return [
            Tool(
                name="launch_browser",
                description="Launch a new browser instance",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "browser_type": {
                            "type": "string",
                            "enum": ["chromium", "firefox", "webkit"],
                            "default": "chromium"
                        },
                        "headless": {"type": "boolean", "default": True}
                    }
                }
            ),
            Tool(
                name="create_context",
                description="Create a new browser context with optional LinkedIn authentication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "linkedin_auth": {
                            "type": "boolean",
                            "default": True,
                            "description": "Automatically add LinkedIn authentication cookies"
                        }
                    }
                }
            ),
            Tool(
                name="create_page",
                description="Create a new page in a context",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "context_id": {"type": "string"}
                    },
                    "required": ["context_id"]
                }
            ),
            Tool(
                name="navigate",
                description="Navigate to a URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {"type": "string"},
                        "url": {"type": "string"},
                        "wait_until": {
                            "type": "string",
                            "enum": ["load", "domcontentloaded", "networkidle"],
                            "default": "networkidle"
                        }
                    },
                    "required": ["page_id", "url"]
                }
            ),
            Tool(
                name="extract_linkedin_profiles",
                description="Extract LinkedIn profile information from search results",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {"type": "string"}
                    },
                    "required": ["page_id"]
                }
            ),
            Tool(
                name="screenshot",
                description="Take a screenshot of the page",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {"type": "string"},
                        "path": {"type": "string"},
                        "full_page": {"type": "boolean", "default": False}
                    },
                    "required": ["page_id"]
                }
            ),
            Tool(
                name="close_browser",
                description="Close the browser and clean up resources",
                inputSchema={"type": "object", "properties": {}}
            )
        ]
    
    async def run(self):
        """Run the MCP server."""
        # Register the list_tools handler
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return self.get_available_tools()
        
        # Start the server
        async with self.server.stdio() as streams:
            await self.server.run(
                streams[0], streams[1], 
                self.server.create_initialization_options()
            )