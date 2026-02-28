"""Tests for stealth module — fingerprint generation, CAPTCHA detection, WAF detection."""

from __future__ import annotations


from crawl0.core.stealth import (
    BrowserFingerprint,
    detect_captcha,
    detect_waf,
    gaussian_delay,
    generate_fingerprint,
    identify_captcha,
)


class TestFingerprintGeneration:
    def test_basic_fingerprint(self):
        fp = generate_fingerprint(full_stealth=False)
        assert isinstance(fp, BrowserFingerprint)
        assert fp.user_agent
        assert fp.viewport
        assert fp.accept_language
        assert fp.headers
        assert "User-Agent" in fp.headers

    def test_full_stealth_fingerprint(self):
        fp = generate_fingerprint(full_stealth=True)
        assert "Sec-Fetch-Dest" in fp.headers
        assert "Sec-Fetch-Mode" in fp.headers
        assert fp.timezone in [
            "America/New_York", "America/Chicago", "America/Denver",
            "America/Los_Angeles", "America/Phoenix", "America/Anchorage",
            "Pacific/Honolulu", "Europe/London", "Europe/Berlin",
            "Europe/Paris", "Asia/Tokyo", "Asia/Shanghai", "Asia/Kolkata",
            "Australia/Sydney",
        ]

    def test_fingerprints_vary(self):
        fps = [generate_fingerprint(full_stealth=True) for _ in range(20)]
        uas = {fp.user_agent for fp in fps}
        # With 20 samples, should have at least 2 different UAs
        assert len(uas) >= 2

    def test_playwright_launch_args(self):
        fp = generate_fingerprint(full_stealth=True)
        args = fp.playwright_launch_args
        assert isinstance(args, list)
        assert any("AutomationControlled" in a for a in args)
        assert any("swiftshader" in a for a in args)

    def test_navigator_overrides_js(self):
        fp = generate_fingerprint(full_stealth=True)
        js = fp.navigator_overrides_js
        assert "webdriver" in js
        assert "platform" in js
        assert "hardwareConcurrency" in js

    def test_browser_type_is_valid(self):
        for _ in range(50):
            fp = generate_fingerprint(full_stealth=True)
            assert fp.browser_type in ("chromium", "firefox")


class TestGaussianDelay:
    def test_returns_positive(self):
        for _ in range(100):
            d = gaussian_delay(1.0, 0.3, 0.2)
            assert d >= 0.2

    def test_respects_minimum(self):
        for _ in range(100):
            d = gaussian_delay(0.01, 0.001, 0.5)
            assert d >= 0.5


class TestCAPTCHADetection:
    def test_recaptcha(self):
        html = '<script src="https://www.google.com/recaptcha/api.js"></script>'
        assert detect_captcha(html) is True
        assert identify_captcha(html) == "reCAPTCHA"

    def test_hcaptcha(self):
        html = '<div class="h-captcha" data-sitekey="abc"></div>'
        assert detect_captcha(html) is True
        assert identify_captcha(html) == "hCaptcha"

    def test_turnstile(self):
        html = '<script src="https://challenges.cloudflare.com/turnstile/v0/api.js"></script>'
        assert detect_captcha(html) is True
        assert identify_captcha(html) == "Cloudflare Turnstile"

    def test_no_captcha(self):
        html = "<html><body><h1>Hello World</h1></body></html>"
        assert detect_captcha(html) is False
        assert identify_captcha(html) is None

    def test_g_recaptcha_div(self):
        html = '<div class="g-recaptcha" data-sitekey="xyz"></div>'
        assert detect_captcha(html) is True
        assert identify_captcha(html) == "reCAPTCHA"


class TestWAFDetection:
    def test_cloudflare_challenge(self):
        html = "<html><body><h1>Just a moment...</h1><p>Checking your browser</p></body></html>"
        assert detect_waf(html, 403) == "Cloudflare"

    def test_cloudflare_ray_id(self):
        html = "<html><body>Cloudflare Ray ID: abc123</body></html>"
        assert detect_waf(html, 403) == "Cloudflare"

    def test_cloudflare_200_challenge(self):
        html = "<html><body>Just a moment... Checking your browser before accessing</body></html>"
        assert detect_waf(html, 200) == "Cloudflare"

    def test_aws_waf(self):
        html = "<html><body>Request blocked by AWSWAF</body></html>"
        assert detect_waf(html, 403) == "AWS WAF"

    def test_no_waf(self):
        html = "<html><body><h1>Hello World</h1></body></html>"
        assert detect_waf(html, 200) is None

    def test_no_waf_on_normal_403(self):
        html = "<html><body><h1>Not Found</h1></body></html>"
        assert detect_waf(html, 403) is None
