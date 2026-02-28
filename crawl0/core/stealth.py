"""Stealth mode — browser fingerprint randomization, anti-bot evasion, CAPTCHA/WAF detection."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Any

# --- User-Agent pools (real, current browsers) ---

_CHROME_VERSIONS = [
    "120.0.0.0", "121.0.0.0", "122.0.0.0", "123.0.0.0", "124.0.0.0",
    "125.0.0.0", "126.0.0.0", "127.0.0.0", "128.0.0.0", "129.0.0.0",
]

_FIREFOX_VERSIONS = [
    "121.0", "122.0", "123.0", "124.0", "125.0",
    "126.0", "127.0", "128.0", "129.0", "130.0",
]

_SAFARI_VERSIONS = [
    "17.2", "17.3", "17.4", "17.5", "17.6",
]

_PLATFORMS = [
    # (os_string_chrome, os_string_firefox, platform_nav, os_label)
    ("Windows NT 10.0; Win64; x64", "Windows NT 10.0; Win64; x64", "Win32", "windows"),
    ("Macintosh; Intel Mac OS X 10_15_7", "Macintosh; Intel Mac OS X 10.15", "MacIntel", "mac"),
    ("X11; Linux x86_64", "X11; Linux x86_64", "Linux x86_64", "linux"),
]

_VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 720},
    {"width": 2560, "height": 1440},
    {"width": 1680, "height": 1050},
    {"width": 1600, "height": 900},
]

_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-US,en;q=0.9,es;q=0.8",
    "en-GB,en;q=0.9",
    "en-US,en;q=0.9,fr;q=0.8",
    "en-US,en;q=0.9,de;q=0.8",
    "en-US,en;q=0.9,ja;q=0.8",
    "en-US,en;q=0.9,pt;q=0.8",
]

_TIMEZONES = [
    "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles",
    "America/Phoenix", "America/Anchorage", "Pacific/Honolulu",
    "Europe/London", "Europe/Berlin", "Europe/Paris",
    "Asia/Tokyo", "Asia/Shanghai", "Asia/Kolkata",
    "Australia/Sydney",
]

_HARDWARE_CONCURRENCY = [2, 4, 6, 8, 10, 12, 16]


def _build_chrome_ua(os_str: str, version: str) -> str:
    return (
        f"Mozilla/5.0 ({os_str}) AppleWebKit/537.36 "
        f"(KHTML, like Gecko) Chrome/{version} Safari/537.36"
    )


def _build_firefox_ua(os_str: str, version: str) -> str:
    return f"Mozilla/5.0 ({os_str}; rv:{version}) Gecko/20100101 Firefox/{version}"


def _build_safari_ua(version: str) -> str:
    wk_build = "605.1.15"
    return (
        f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        f"AppleWebKit/{wk_build} (KHTML, like Gecko) Version/{version} Safari/{wk_build}"
    )


@dataclass
class BrowserFingerprint:
    """A complete browser fingerprint for a session."""

    user_agent: str
    viewport: dict[str, int]
    accept_language: str
    timezone: str
    platform: str
    hardware_concurrency: int
    languages: list[str]
    headers: dict[str, str] = field(default_factory=dict)
    browser_type: str = "chromium"  # chromium or firefox

    @property
    def playwright_launch_args(self) -> list[str]:
        """Chromium launch args for stealth."""
        return [
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-web-security",
            "--disable-setuid-sandbox",
            "--no-sandbox",
            "--disable-infobars",
            "--window-size={},{}".format(self.viewport["width"], self.viewport["height"]),
            "--disable-accelerated-2d-canvas",
            "--disable-gpu",
            "--use-gl=swiftshader",  # WebGL fingerprint masking
            "--disable-reading-from-canvas",  # Canvas fingerprint masking
        ]

    @property
    def navigator_overrides_js(self) -> str:
        """JavaScript to inject for navigator property overrides."""
        langs_js = ", ".join(f'"{lang}"' for lang in self.languages)
        return f"""
        Object.defineProperty(navigator, 'webdriver', {{get: () => undefined}});
        Object.defineProperty(navigator, 'platform', {{get: () => '{self.platform}'}});
        Object.defineProperty(navigator, 'hardwareConcurrency', {{get: () => {self.hardware_concurrency}}});
        Object.defineProperty(navigator, 'languages', {{get: () => [{langs_js}]}});
        // Mask chrome automation indicators
        if (window.chrome) {{
            window.chrome.runtime = undefined;
        }}
        // Override permissions query
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) =>
            parameters.name === 'notifications'
                ? Promise.resolve({{state: Notification.permission}})
                : originalQuery(parameters);
        // WebGL vendor/renderer masking
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {{
            if (parameter === 37445) return 'Intel Inc.';
            if (parameter === 37446) return 'Intel Iris OpenGL Engine';
            return getParameter.call(this, parameter);
        }};
        """


def generate_fingerprint(full_stealth: bool = False) -> BrowserFingerprint:
    """Generate a randomized browser fingerprint.

    Args:
        full_stealth: If True, randomize everything. If False, just UA + basic headers.

    Returns:
        A BrowserFingerprint with consistent, realistic values.
    """
    # Pick a platform
    os_chrome, os_firefox, platform_nav, os_label = random.choice(_PLATFORMS)

    # Pick browser type (weighted toward Chrome)
    browser_roll = random.random()
    if os_label == "mac" and browser_roll > 0.85:
        # Safari only on Mac
        ua = _build_safari_ua(random.choice(_SAFARI_VERSIONS))
        browser_type = "chromium"  # Playwright uses chromium for Safari-like
    elif browser_roll > 0.75:
        ua = _build_firefox_ua(os_firefox, random.choice(_FIREFOX_VERSIONS))
        browser_type = "firefox"
    else:
        ua = _build_chrome_ua(os_chrome, random.choice(_CHROME_VERSIONS))
        browser_type = "chromium"

    accept_lang = random.choice(_LANGUAGES)
    lang_primary = accept_lang.split(",")[0].strip()
    languages = [lang_primary]
    if ";" in accept_lang.split(",")[-1]:
        secondary = accept_lang.split(",")[1].split(";")[0].strip()
        languages.append(secondary)

    viewport = random.choice(_VIEWPORTS) if full_stealth else {"width": 1920, "height": 1080}
    timezone = random.choice(_TIMEZONES) if full_stealth else "America/Los_Angeles"
    hw_concurrency = random.choice(_HARDWARE_CONCURRENCY) if full_stealth else 8

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": accept_lang,
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": ua,
    }

    if full_stealth:
        # Add more realistic headers
        headers["Sec-Fetch-Dest"] = "document"
        headers["Sec-Fetch-Mode"] = "navigate"
        headers["Sec-Fetch-Site"] = "none"
        headers["Sec-Fetch-User"] = "?1"
        headers["Cache-Control"] = random.choice(["max-age=0", "no-cache"])
        headers["Sec-Ch-Ua-Platform"] = f'"{_platform_to_sec_ch(os_label)}"'

    return BrowserFingerprint(
        user_agent=ua,
        viewport=viewport,
        accept_language=accept_lang,
        timezone=timezone,
        platform=platform_nav,
        hardware_concurrency=hw_concurrency,
        languages=languages,
        headers=headers,
        browser_type=browser_type,
    )


def _platform_to_sec_ch(os_label: str) -> str:
    return {"windows": "Windows", "mac": "macOS", "linux": "Linux"}.get(os_label, "Unknown")


# --- Human-like behavior simulation ---

def gaussian_delay(mean: float = 1.0, std: float = 0.3, minimum: float = 0.2) -> float:
    """Generate a gaussian-distributed delay in seconds."""
    delay = random.gauss(mean, std)
    return max(minimum, delay)


async def simulate_human_behavior(page: Any, full_stealth: bool = False) -> None:
    """Simulate human-like behavior on a Playwright page.

    Args:
        page: Playwright page object.
        full_stealth: If True, do more elaborate simulation.
    """
    import asyncio

    if not full_stealth:
        # Basic: just a small random wait
        await asyncio.sleep(gaussian_delay(0.5, 0.2, 0.1))
        return

    # Random initial wait (human reading the page)
    await asyncio.sleep(gaussian_delay(1.0, 0.4, 0.3))

    # Random mouse movement
    viewport = page.viewport_size or {"width": 1920, "height": 1080}
    for _ in range(random.randint(2, 5)):
        x = random.randint(100, viewport["width"] - 100)
        y = random.randint(100, viewport["height"] - 100)
        await page.mouse.move(x, y, steps=random.randint(5, 15))
        await asyncio.sleep(gaussian_delay(0.3, 0.1, 0.05))

    # Random scroll pattern
    scroll_count = random.randint(1, 4)
    for _ in range(scroll_count):
        scroll_y = random.randint(100, 500)
        await page.evaluate(f"window.scrollBy(0, {scroll_y})")
        await asyncio.sleep(gaussian_delay(0.8, 0.3, 0.2))

    # Sometimes scroll back up a bit
    if random.random() > 0.6:
        await page.evaluate(f"window.scrollBy(0, -{random.randint(50, 200)})")
        await asyncio.sleep(gaussian_delay(0.5, 0.2, 0.1))


# --- CAPTCHA Detection ---

_CAPTCHA_PATTERNS = [
    # reCAPTCHA
    (r"google\.com/recaptcha", "reCAPTCHA"),
    (r"grecaptcha", "reCAPTCHA"),
    (r"g-recaptcha", "reCAPTCHA"),
    (r"recaptcha/api", "reCAPTCHA"),
    # hCaptcha
    (r"hcaptcha\.com", "hCaptcha"),
    (r"h-captcha", "hCaptcha"),
    # Cloudflare Turnstile
    (r"challenges\.cloudflare\.com/turnstile", "Cloudflare Turnstile"),
    (r"cf-turnstile", "Cloudflare Turnstile"),
    # Generic
    (r"captcha", "Unknown CAPTCHA"),
]


def detect_captcha(html: str) -> bool:
    """Check if HTML contains CAPTCHA elements.

    Args:
        html: Page HTML content.

    Returns:
        True if a CAPTCHA is detected.
    """
    html_lower = html.lower()
    for pattern, _name in _CAPTCHA_PATTERNS:
        if re.search(pattern, html_lower):
            return True
    return False


def identify_captcha(html: str) -> str | None:
    """Identify the specific CAPTCHA provider.

    Args:
        html: Page HTML content.

    Returns:
        Name of the CAPTCHA provider, or None.
    """
    html_lower = html.lower()
    for pattern, name in _CAPTCHA_PATTERNS:
        if re.search(pattern, html_lower):
            return name
    return None


# --- WAF / Cloudflare Detection ---

_WAF_PATTERNS: list[tuple[str, str]] = [
    # Cloudflare
    (r"checking your browser", "Cloudflare"),
    (r"cloudflare ray id", "Cloudflare"),
    (r"cf-browser-verification", "Cloudflare"),
    (r"__cf_chl_managed_tk__", "Cloudflare"),
    (r"cdn-cgi/challenge-platform", "Cloudflare"),
    (r"just a moment\.\.\.", "Cloudflare"),
    # AWS WAF
    (r"awswaf", "AWS WAF"),
    (r"request blocked.*aws", "AWS WAF"),
    # Akamai
    (r"akamai.*access denied", "Akamai"),
    (r"reference.*akamai", "Akamai"),
    # Sucuri
    (r"sucuri\.net", "Sucuri"),
    (r"access denied.*sucuri", "Sucuri"),
    # Generic
    (r"access denied", "Generic WAF"),
    (r"403 forbidden.*security", "Generic WAF"),
]


def detect_waf(html: str, status_code: int = 200) -> str | None:
    """Detect WAF/Cloudflare challenge pages.

    Args:
        html: Page HTML content.
        status_code: HTTP response status code.

    Returns:
        WAF provider name if detected, None otherwise.
    """
    html_lower = html.lower()

    # Cloudflare challenge is typically 403 or 503 with specific markers
    if status_code in (403, 503):
        for pattern, name in _WAF_PATTERNS:
            if re.search(pattern, html_lower):
                return name

    # Some WAFs return 200 with challenge content
    for pattern, name in _WAF_PATTERNS[:6]:  # Only check strong Cloudflare indicators for 200s
        if re.search(pattern, html_lower):
            return name

    return None
