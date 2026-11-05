import asyncio
from typing import Optional, Dict, Any

STEALTH_JS = """
// 1. Mask navigator.webdriver tell
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
    configurable: true
});

// 2. Mock chrome runtime object
if (!window.chrome) {
    window.chrome = {
        runtime: {},
        loadTimes: function() {},
        csi: function() {},
        app: {}
    };
}

// 3. Mock realistic plugins array
Object.defineProperty(navigator, 'plugins', {
    get: () => [
        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
        { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' }
    ],
    configurable: true
});

// 4. Mock languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
    configurable: true
});

// 5. Mock permissions query
const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
if (originalQuery) {
    window.navigator.permissions.query = (parameters) => (
        parameters && parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(parameters)
    );
}
"""

DEFAULT_WINDOWS_CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)

def get_stealth_context_options(user_agent: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate realistic desktop browser options and Client Hints to defeat basic
    anti-bot fingerprinting and silent Cloudflare/Turnstile challenges.
    """
    ua = user_agent or DEFAULT_WINDOWS_CHROME_UA
    return {
        "user_agent": ua,
        "viewport": {"width": 1920, "height": 1080},
        "locale": "en-US",
        "timezone_id": "America/Los_Angeles",
        "has_touch": False,
        "is_mobile": False,
        "extra_http_headers": {
            "sec-ch-ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "accept-language": "en-US,en;q=0.9",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
        }
    }

async def create_stealth_context(browser, user_agent: Optional[str] = None):
    """
    Instantiate a new Playwright browser context pre-configured with evasive headers,
    standard desktop viewport, and anti-detection initialization scripts.
    """
    context_options = get_stealth_context_options(user_agent=user_agent)
    context = await browser.new_context(**context_options)
    await context.add_init_script(STEALTH_JS)
    return context

CHALLENGE_TITLE_SIGNATURES = [
    "just a moment...",
    "attention required! | cloudflare",
    "checking your browser",
    "security check",
]

CHALLENGE_BODY_SIGNATURES = [
    "verify you are human",
    "cloudflare turnstile",
    "checking your browser before accessing",
    "cf-turnstile",
    "datadome",
    "perimeterx",
    "please verify you are a human",
]

def is_challenge_active(title: str, body: str) -> bool:
    """Return True if title or body contains active anti-bot challenge signatures."""
    t_lower = (title or "").lower()
    b_lower = (body or "").lower()
    if any(sig in t_lower for sig in CHALLENGE_TITLE_SIGNATURES):
        return True
    if any(sig in b_lower and len(b_lower) < 2500 for sig in CHALLENGE_BODY_SIGNATURES):
        return True
    return False

async def resolve_transient_challenge(page, timeout_seconds: float = 5.0, poll_interval: float = 0.5) -> bool:
    """
    Wait for silent/transient challenges (e.g. Turnstile auto-solve, Cloudflare waiting room)
    to complete and redirect to genuine content before declaring a page blocked.
    Returns True if content is clear, False if still blocked after timeout.
    """
    start_time = asyncio.get_event_loop().time()
    
    while True:
        try:
            title = await page.title()
            body = await page.evaluate("() => document.body ? document.body.innerText.substring(0, 3000) : ''")
        except Exception:
            # Context might be briefly recreating on redirect
            title = ""
            body = ""

        if not is_challenge_active(title, body):
            return True

        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed >= timeout_seconds:
            return False

        await asyncio.sleep(poll_interval)
