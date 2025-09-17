# LinkedIn Cookies Configuration

This guide explains how to configure LinkedIn cookies for the LinkedIn scraper.

## Overview

The LinkedIn scraper uses browser cookies to authenticate with LinkedIn. These cookies are now configurable via the `.env` file instead of being hardcoded in the source code.

## Setting Up Cookies

### 1. Export Cookies from Your Browser

1. **Log into LinkedIn** in your browser
2. **Install a cookie export extension** (e.g., "Cookie Editor" for Chrome/Firefox)
3. **Export all LinkedIn cookies** as JSON
4. **Copy the JSON array** of cookie objects

### 2. Add Cookies to .env File

Add the `LINKEDIN_COOKIES` variable to your `.env` file:

```bash
# LinkedIn Cookies Configuration
# To update: Export cookies from your browser after logging into LinkedIn
# Format: JSON array of cookie objects
LINKEDIN_COOKIES=[{"domain": ".linkedin.com", "name": "bcookie", "value": "...", ...}, {...}]
```

### 3. Required Cookie Format

The cookies must be in JSON array format with the following structure:

```json
[
  {
    "domain": ".linkedin.com",
    "name": "cookie_name",
    "value": "cookie_value",
    "path": "/",
    "secure": true,
    "httpOnly": false,
    "sameSite": "no_restriction",
    "expirationDate": 1234567890
  }
]
```

## Important Notes

### Security
- **Never commit** the `.env` file with real cookies to version control
- **Keep cookies secure** - they provide access to your LinkedIn account
- **Regenerate cookies regularly** for security

### Cookie Expiration
- **Monitor cookie expiration** - cookies will expire over time
- **Update cookies when scraper fails** with authentication errors
- **Check browser for fresh cookies** if getting login redirects

### Testing Configuration

Test your cookie configuration:

```bash
python3 -c "
from mcp_servers.playwright.server import load_linkedin_cookies
from dotenv import load_dotenv

load_dotenv()
try:
    cookies = load_linkedin_cookies()
    print(f'✅ Successfully loaded {len(cookies)} LinkedIn cookies')
except Exception as e:
    print(f'❌ Error: {str(e)}')
"
```

## Troubleshooting

### Error: "LINKEDIN_COOKIES environment variable is required"
- Ensure the `LINKEDIN_COOKIES` variable is set in your `.env` file
- Check that the `.env` file is in the project root directory

### Error: "Invalid JSON in LINKEDIN_COOKIES"
- Verify the JSON format is valid (use a JSON validator)
- Ensure quotes are properly escaped
- Check for trailing commas or syntax errors

### Error: "LINKEDIN_COOKIES must be a JSON array"
- Ensure the value starts with `[` and ends with `]`
- Verify it's an array of cookie objects, not a single object

### Scraper gets redirected to LinkedIn login page
- Cookies may have expired - export fresh cookies from your browser
- Check that all required cookies are present (especially `li_at`, `li_rm`)
- Verify you're logged into LinkedIn in the same browser session

## Cookie Export Tools

### Browser Extensions
- **Cookie Editor** (Chrome/Firefox) - Easy export to JSON
- **EditThisCookie** (Chrome) - Export cookies in various formats
- **Advanced Cookie Manager** (Firefox) - Detailed cookie management

### Manual Export (Developer Tools)
1. Open **Developer Tools** (F12)
2. Go to **Application/Storage** tab
3. Select **Cookies** → `linkedin.com`
4. **Copy all cookie data** manually

## Example .env Configuration

```bash
# LinkedIn Cookies Configuration
LINKEDIN_COOKIES=[{"domain": ".linkedin.com", "expirationDate": 1781728252.04868, "hostOnly": false, "httpOnly": false, "name": "bcookie", "path": "/", "sameSite": "no_restriction", "secure": true, "session": false, "storeId": "0", "value": "\"v=2&09c343a7-5ea8-41b1-8ba2-53c8f0055dda\""}, {"domain": ".linkedin.com", "name": "li_at", "value": "YOUR_LI_AT_TOKEN_HERE", "path": "/", "secure": true, "httpOnly": true}]
```

## Security Best Practices

1. **Use environment variables** - Never hardcode cookies in source code
2. **Limit access** - Only share cookie data with authorized team members  
3. **Regular rotation** - Update cookies periodically for security
4. **Monitor usage** - Check LinkedIn account for unusual activity
5. **Backup configuration** - Keep a secure backup of working cookie configuration