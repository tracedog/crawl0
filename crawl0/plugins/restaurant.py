"""Restaurant data extractor — menu items, hours, location, phone, cuisine."""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, Field

from crawl0.plugins.base import BaseExtractor

# Price pattern: $12, $12.99, 12.99, etc.
PRICE_RE = re.compile(r"\$?\d{1,4}(?:\.\d{2})?")
PHONE_RE = re.compile(
    r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
)
HOURS_RE = re.compile(
    r"(?:mon|tue|wed|thu|fri|sat|sun|monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
    r"[^:\n]{0,30}?\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)",
    re.IGNORECASE,
)
CUISINE_KEYWORDS = [
    "mexican", "italian", "chinese", "japanese", "thai", "indian", "french",
    "american", "mediterranean", "korean", "vietnamese", "greek", "sushi",
    "pizza", "burgers", "seafood", "steakhouse", "bbq", "barbecue", "vegan",
    "vegetarian", "tapas", "ramen", "pho", "tacos", "dim sum", "cajun",
]


class MenuItem(BaseModel):
    """A single menu item."""
    name: str
    price: float | None = None
    description: str = ""


class RestaurantData(BaseModel):
    """Structured restaurant data."""
    name: str | None = None
    cuisine_type: list[str] = Field(default_factory=list)
    menu_items: list[MenuItem] = Field(default_factory=list)
    phone: str | None = None
    address: str | None = None
    hours: list[str] = Field(default_factory=list)
    url: str = ""


class RestaurantExtractor(BaseExtractor):
    """Extract restaurant information from HTML."""

    def extract(self, soup: BeautifulSoup, url: str) -> RestaurantData:
        text = soup.get_text(" ", strip=True)

        return RestaurantData(
            name=self._extract_name(soup),
            cuisine_type=self._extract_cuisine(text),
            menu_items=self._extract_menu_items(soup),
            phone=self._extract_phone(text),
            address=self._extract_address(soup),
            hours=self._extract_hours(text),
            url=url,
        )

    def _extract_name(self, soup: BeautifulSoup) -> str | None:
        # Try og:site_name, og:title, then <title>
        og = soup.find("meta", attrs={"property": "og:site_name"})
        if og and og.get("content"):
            return og["content"]
        title = soup.find("title")
        if title:
            name = title.get_text(strip=True)
            # Strip common suffixes
            for sep in [" |", " -", " –", " —"]:
                if sep in name:
                    name = name.split(sep)[0].strip()
            return name
        return None

    def _extract_cuisine(self, text: str) -> list[str]:
        text_lower = text.lower()
        return [c for c in CUISINE_KEYWORDS if c in text_lower]

    def _extract_menu_items(self, soup: BeautifulSoup) -> list[MenuItem]:
        items: list[MenuItem] = []

        # Strategy 1: Look for elements with price patterns nearby
        # Common patterns: <div class="menu-item">, <li> with name + price
        menu_containers = soup.find_all(
            class_=lambda c: c and any(
                k in c.lower() for k in ["menu", "item", "dish", "food", "product"]
            )
        )

        for container in menu_containers[:100]:  # limit
            text = container.get_text(" ", strip=True)
            prices = PRICE_RE.findall(text)
            if not prices:
                continue

            # Try to split name from price
            price_str = prices[0]
            price_val = float(price_str.replace("$", ""))
            # Name is text before the price
            idx = text.find(price_str)
            name = text[:idx].strip().rstrip("–—-·.").strip()
            desc = text[idx + len(price_str):].strip().lstrip("–—-·.").strip()

            if name and 2 < len(name) < 100:
                items.append(MenuItem(name=name, price=price_val, description=desc[:200]))

        # Strategy 2: Look in headings followed by price
        if not items:
            for heading in soup.find_all(["h2", "h3", "h4", "h5"]):
                sibling_text = ""
                sib = heading.find_next_sibling()
                if sib:
                    sibling_text = sib.get_text(" ", strip=True)
                combined = f"{heading.get_text(strip=True)} {sibling_text}"
                prices = PRICE_RE.findall(combined)
                if prices:
                    price_val = float(prices[0].replace("$", ""))
                    name = heading.get_text(strip=True)
                    if name and 2 < len(name) < 100:
                        items.append(MenuItem(name=name, price=price_val, description=sibling_text[:200]))

        # Deduplicate by name
        seen: set[str] = set()
        unique: list[MenuItem] = []
        for item in items:
            key = item.name.lower()
            if key not in seen:
                seen.add(key)
                unique.append(item)

        return unique

    def _extract_phone(self, text: str) -> str | None:
        match = PHONE_RE.search(text)
        return match.group(0) if match else None

    def _extract_address(self, soup: BeautifulSoup) -> str | None:
        # Look for address tag, schema.org, or common patterns
        addr = soup.find("address")
        if addr:
            return addr.get_text(" ", strip=True)[:200]

        # Schema.org streetAddress
        for prop in ["streetAddress", "address"]:
            el = soup.find(attrs={"itemprop": prop})
            if el:
                return el.get_text(" ", strip=True)[:200]

        return None

    def _extract_hours(self, text: str) -> list[str]:
        matches = HOURS_RE.findall(text)
        # Clean and deduplicate
        seen: set[str] = set()
        result: list[str] = []
        for m in matches[:14]:  # max 2 weeks
            clean = m.strip()
            if clean.lower() not in seen:
                seen.add(clean.lower())
                result.append(clean)
        return result
