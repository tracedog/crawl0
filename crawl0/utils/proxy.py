"""Proxy rotation support — HTTP, HTTPS, SOCKS5."""

from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ProxyProtocol(str, Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


@dataclass
class ProxyEntry:
    """A single proxy configuration."""

    url: str
    protocol: ProxyProtocol = ProxyProtocol.HTTP
    failed: bool = False
    fail_count: int = 0
    last_used: float = 0.0
    last_failed: float = 0.0

    @property
    def server_url(self) -> str:
        """Return the full proxy URL for Playwright/httpx."""
        return self.url


class RotationStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"


class ProxyRotator:
    """Manages a pool of proxies with rotation and failure detection.

    Args:
        proxies: List of proxy URLs or ProxyEntry objects.
        strategy: Rotation strategy (round_robin or random).
        max_failures: Max consecutive failures before skipping a proxy.
        recovery_time: Seconds before a failed proxy is retried.
    """

    def __init__(
        self,
        proxies: list[str | ProxyEntry] | None = None,
        strategy: RotationStrategy = RotationStrategy.ROUND_ROBIN,
        max_failures: int = 3,
        recovery_time: float = 300.0,
    ) -> None:
        self._entries: list[ProxyEntry] = []
        self._strategy = strategy
        self._max_failures = max_failures
        self._recovery_time = recovery_time
        self._index = 0

        if proxies:
            for p in proxies:
                if isinstance(p, ProxyEntry):
                    self._entries.append(p)
                else:
                    self._entries.append(_parse_proxy(p))

    @property
    def size(self) -> int:
        return len(self._entries)

    @property
    def available_count(self) -> int:
        return sum(1 for e in self._entries if self._is_available(e))

    def _is_available(self, entry: ProxyEntry) -> bool:
        if entry.fail_count < self._max_failures:
            return True
        # Check if recovery time has passed
        if time.monotonic() - entry.last_failed > self._recovery_time:
            entry.fail_count = 0
            entry.failed = False
            return True
        return False

    def get_next(self) -> ProxyEntry | None:
        """Get the next available proxy.

        Returns:
            ProxyEntry or None if no proxies available.
        """
        if not self._entries:
            return None

        available = [e for e in self._entries if self._is_available(e)]
        if not available:
            return None

        if self._strategy == RotationStrategy.RANDOM:
            entry = random.choice(available)
        else:
            # Round robin over available proxies
            self._index = self._index % len(available)
            entry = available[self._index]
            self._index += 1

        entry.last_used = time.monotonic()
        return entry

    def report_failure(self, proxy: ProxyEntry) -> None:
        """Report a proxy failure for auto-skip logic."""
        proxy.fail_count += 1
        proxy.last_failed = time.monotonic()
        if proxy.fail_count >= self._max_failures:
            proxy.failed = True

    def report_success(self, proxy: ProxyEntry) -> None:
        """Report a proxy success — resets failure count."""
        proxy.fail_count = 0
        proxy.failed = False

    def add_proxy(self, proxy_url: str) -> None:
        """Add a proxy to the pool."""
        self._entries.append(_parse_proxy(proxy_url))


def _parse_proxy(url: str) -> ProxyEntry:
    """Parse a proxy URL string into a ProxyEntry.

    Supports formats:
        - http://host:port
        - https://host:port
        - socks5://host:port
        - http://user:pass@host:port
        - host:port (defaults to http)
    """
    url = url.strip()
    if not url:
        raise ValueError("Empty proxy URL")

    # Determine protocol
    if url.startswith("socks5://"):
        protocol = ProxyProtocol.SOCKS5
    elif url.startswith("https://"):
        protocol = ProxyProtocol.HTTPS
    elif url.startswith("http://"):
        protocol = ProxyProtocol.HTTP
    else:
        # No scheme — default to http
        url = f"http://{url}"
        protocol = ProxyProtocol.HTTP

    return ProxyEntry(url=url, protocol=protocol)


def load_proxies_from_file(file_path: str) -> list[str]:
    """Load proxy URLs from a file (one per line).

    Args:
        file_path: Path to the proxy list file.

    Returns:
        List of proxy URL strings.

    Raises:
        FileNotFoundError: If the file doesn't exist.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Proxy file not found: {file_path}")

    proxies = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            proxies.append(line)
    return proxies
