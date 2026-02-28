"""Social media profile extractor — profile info, follower counts, posts."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from crawl0.plugins.base import BaseExtractor

FOLLOWER_RE = re.compile(
    r"(\d[\d,\.]*[KkMmBb]?)\s*(?:followers?|following|subscribers?|fans?|connections?)",
    re.IGNORECASE,
)
COUNT_SUFFIXES = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}


def _parse_count(text: str) -> int | None:
    """Parse follower-style count like '1.2K', '5M', '12,345'."""
    text = text.strip().replace(",", "")
    suffix = text[-1].lower() if text and text[-1].lower() in COUNT_SUFFIXES else None
    try:
        if suffix:
            return int(float(text[:-1]) * COUNT_SUFFIXES[suffix])
        return int(float(text))
    except (ValueError, IndexError):
        return None


class PostSummary(BaseModel):
    """Summary of a social media post."""
    text: str = ""
    timestamp: str = ""
    likes: int | None = None
    comments: int | None = None


class SocialData(BaseModel):
    """Structured social media profile data."""
    platform: str = ""
    username: str = ""
    display_name: str = ""
    bio: str = ""
    followers: int | None = None
    following: int | None = None
    posts_count: int | None = None
    avatar_url: str = ""
    recent_posts: list[PostSummary] = Field(default_factory=list)
    url: str = ""


class SocialExtractor(BaseExtractor):
    """Extract social media profile information from HTML."""

    def extract(self, soup: BeautifulSoup, url: str) -> SocialData:
        text = soup.get_text(" ", strip=True)

        # Detect platform from URL
        platform = ""
        url_lower = url.lower()
        for p in ["twitter", "x.com", "instagram", "facebook", "linkedin",
                   "tiktok", "youtube", "github", "threads", "mastodon", "bluesky"]:
            if p in url_lower:
                platform = "twitter" if p == "x.com" else p
                break

        return SocialData(
            platform=platform,
            username=self._extract_username(soup, url),
            display_name=self._extract_display_name(soup),
            bio=self._extract_bio(soup),
            followers=self._extract_follower_count(text, "follower"),
            following=self._extract_follower_count(text, "following"),
            avatar_url=self._extract_avatar(soup),
            recent_posts=self._extract_posts(soup),
            url=url,
        )

    def _extract_username(self, soup: BeautifulSoup, url: str) -> str:
        # Try meta tags
        for attr in [{"name": "twitter:creator"}, {"property": "profile:username"}]:
            tag = soup.find("meta", attrs=attr)
            if tag and tag.get("content"):
                return tag["content"].lstrip("@")

        # Extract from URL path
        from urllib.parse import urlparse
        path = urlparse(url).path.strip("/")
        parts = path.split("/")
        if parts and parts[0] and not parts[0].startswith(("p", "status", "post", "reel")):
            return parts[0]

        return ""

    def _extract_display_name(self, soup: BeautifulSoup) -> str:
        og = soup.find("meta", attrs={"property": "og:title"})
        if og and og.get("content"):
            return og["content"]
        title = soup.find("title")
        if title:
            return title.get_text(strip=True)
        return ""

    def _extract_bio(self, soup: BeautifulSoup) -> str:
        og = soup.find("meta", attrs={"property": "og:description"})
        if og and og.get("content"):
            return og["content"][:500]
        desc = soup.find("meta", attrs={"name": "description"})
        if desc and desc.get("content"):
            return desc["content"][:500]
        return ""

    def _extract_follower_count(self, text: str, kind: str) -> int | None:
        pattern = re.compile(
            rf"(\d[\d,\.]*[KkMmBb]?)\s*{kind}s?",
            re.IGNORECASE,
        )
        match = pattern.search(text)
        if match:
            return _parse_count(match.group(1))
        return None

    def _extract_avatar(self, soup: BeautifulSoup) -> str:
        og = soup.find("meta", attrs={"property": "og:image"})
        if og and og.get("content"):
            return og["content"]
        return ""

    def _extract_posts(self, soup: BeautifulSoup) -> list[PostSummary]:
        posts: list[PostSummary] = []

        # Look for common post/tweet/status containers
        containers = soup.find_all(
            class_=lambda c: c and any(
                k in c.lower()
                for k in ["post", "tweet", "status", "entry", "feed-item", "timeline"]
            )
        )

        for container in containers[:10]:
            text = container.get_text(" ", strip=True)[:500]
            if len(text) < 10:
                continue

            time_el = container.find("time")
            timestamp = ""
            if time_el:
                timestamp = time_el.get("datetime") or time_el.get_text(strip=True)

            posts.append(PostSummary(text=text, timestamp=timestamp))

        return posts[:5]
