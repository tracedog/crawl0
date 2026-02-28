"""Contact info extractor — email, phone, address, social links."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from crawl0.plugins.base import BaseExtractor

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(
    r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
)

SOCIAL_DOMAINS = {
    "facebook.com": "facebook",
    "fb.com": "facebook",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "instagram.com": "instagram",
    "linkedin.com": "linkedin",
    "youtube.com": "youtube",
    "tiktok.com": "tiktok",
    "pinterest.com": "pinterest",
    "github.com": "github",
    "threads.net": "threads",
    "mastodon.social": "mastodon",
    "bsky.app": "bluesky",
}


class ContactData(BaseModel):
    """Structured contact information."""
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    addresses: list[str] = Field(default_factory=list)
    social_links: dict[str, str] = Field(default_factory=dict)
    url: str = ""


class ContactExtractor(BaseExtractor):
    """Extract contact information from HTML."""

    def extract(self, soup: BeautifulSoup, url: str) -> ContactData:
        text = soup.get_text(" ", strip=True)

        return ContactData(
            emails=self._extract_emails(text),
            phones=self._extract_phones(text),
            addresses=self._extract_addresses(soup),
            social_links=self._extract_social_links(soup),
            url=url,
        )

    def _extract_emails(self, text: str) -> list[str]:
        emails = EMAIL_RE.findall(text)
        # Filter out common false positives
        filtered = [
            e for e in emails
            if not e.endswith((".png", ".jpg", ".gif", ".svg", ".css", ".js"))
        ]
        return list(dict.fromkeys(filtered))[:10]

    def _extract_phones(self, text: str) -> list[str]:
        phones = PHONE_RE.findall(text)
        return list(dict.fromkeys(phones))[:10]

    def _extract_addresses(self, soup: BeautifulSoup) -> list[str]:
        addresses: list[str] = []

        # <address> tag
        for addr in soup.find_all("address"):
            text = addr.get_text(" ", strip=True)
            if text and len(text) > 5:
                addresses.append(text[:300])

        # Schema.org
        for prop in ["streetAddress", "address"]:
            for el in soup.find_all(attrs={"itemprop": prop}):
                text = el.get_text(" ", strip=True)
                if text and text not in addresses:
                    addresses.append(text[:300])

        return addresses[:5]

    def _extract_social_links(self, soup: BeautifulSoup) -> dict[str, str]:
        social: dict[str, str] = {}

        for a in soup.find_all("a", href=True):
            href = a["href"]
            try:
                domain = urlparse(href).netloc.lower().lstrip("www.")
            except Exception:
                continue
            for sd, platform in SOCIAL_DOMAINS.items():
                if sd in domain and platform not in social:
                    social[platform] = href
                    break

        return social
