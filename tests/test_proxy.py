"""Tests for proxy rotation."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from crawl0.utils.proxy import (
    ProxyEntry,
    ProxyProtocol,
    ProxyRotator,
    RotationStrategy,
    _parse_proxy,
    load_proxies_from_file,
)


class TestParseProxy:
    def test_http_proxy(self):
        e = _parse_proxy("http://proxy.example.com:8080")
        assert e.protocol == ProxyProtocol.HTTP
        assert e.url == "http://proxy.example.com:8080"

    def test_https_proxy(self):
        e = _parse_proxy("https://proxy.example.com:8443")
        assert e.protocol == ProxyProtocol.HTTPS

    def test_socks5_proxy(self):
        e = _parse_proxy("socks5://proxy.example.com:1080")
        assert e.protocol == ProxyProtocol.SOCKS5

    def test_no_scheme_defaults_http(self):
        e = _parse_proxy("proxy.example.com:8080")
        assert e.protocol == ProxyProtocol.HTTP
        assert e.url == "http://proxy.example.com:8080"

    def test_with_auth(self):
        e = _parse_proxy("http://user:pass@proxy.example.com:8080")
        assert "user:pass" in e.url

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            _parse_proxy("")


class TestProxyRotator:
    def test_round_robin(self):
        proxies = ["http://p1:8080", "http://p2:8080", "http://p3:8080"]
        r = ProxyRotator(proxies, strategy=RotationStrategy.ROUND_ROBIN)
        assert r.size == 3
        urls = [r.get_next().url for _ in range(6)]
        assert urls == [
            "http://p1:8080", "http://p2:8080", "http://p3:8080",
            "http://p1:8080", "http://p2:8080", "http://p3:8080",
        ]

    def test_random(self):
        proxies = ["http://p1:8080", "http://p2:8080", "http://p3:8080"]
        r = ProxyRotator(proxies, strategy=RotationStrategy.RANDOM)
        entries = [r.get_next() for _ in range(10)]
        assert all(e is not None for e in entries)

    def test_empty_returns_none(self):
        r = ProxyRotator()
        assert r.get_next() is None

    def test_failure_detection(self):
        r = ProxyRotator(["http://p1:8080", "http://p2:8080"], max_failures=2)
        p1 = r.get_next()
        r.report_failure(p1)
        r.report_failure(p1)
        # p1 should be skipped now
        assert r.available_count == 1
        next_proxy = r.get_next()
        assert next_proxy.url == "http://p2:8080"

    def test_success_resets_failures(self):
        r = ProxyRotator(["http://p1:8080"], max_failures=3)
        p1 = r.get_next()
        r.report_failure(p1)
        r.report_failure(p1)
        r.report_success(p1)
        assert p1.fail_count == 0
        assert r.available_count == 1

    def test_all_failed_returns_none(self):
        r = ProxyRotator(["http://p1:8080"], max_failures=1, recovery_time=9999)
        p1 = r.get_next()
        r.report_failure(p1)
        assert r.get_next() is None


class TestLoadProxiesFromFile:
    def test_load(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("http://p1:8080\n# comment\nhttp://p2:8080\n\nsocks5://p3:1080\n")
            f.flush()
            proxies = load_proxies_from_file(f.name)
        assert proxies == ["http://p1:8080", "http://p2:8080", "socks5://p3:1080"]
        Path(f.name).unlink()

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_proxies_from_file("/nonexistent/proxies.txt")
