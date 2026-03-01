"""E-commerce data extractor — products, prices, availability."""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from crawl0.plugins.base import BaseExtractor

PRICE_RE = re.compile(r"\$\s?\d{1,6}(?:,\d{3})*(?:\.\d{2})?")


class Product(BaseModel):
    """A single product."""

    name: str
    price: float | None = None
    description: str = ""
    images: list[str] = Field(default_factory=list)
    availability: str = ""
    url: str = ""


class EcommerceData(BaseModel):
    """Structured e-commerce data."""

    products: list[Product] = Field(default_factory=list)
    currency: str = "USD"
    url: str = ""


class EcommerceExtractor(BaseExtractor):
    """Extract product information from e-commerce pages."""

    def extract(self, soup: BeautifulSoup, url: str) -> EcommerceData:
        products = self._extract_products(soup, url)
        return EcommerceData(products=products, url=url)

    def _extract_products(self, soup: BeautifulSoup, base_url: str) -> list[Product]:
        products: list[Product] = []

        # Strategy 1: Schema.org Product markup
        for el in soup.find_all(attrs={"itemtype": re.compile(r"schema\.org/Product", re.I)}):
            name_el = el.find(attrs={"itemprop": "name"})
            price_el = el.find(attrs={"itemprop": "price"})
            desc_el = el.find(attrs={"itemprop": "description"})
            img_el = el.find("img")
            avail_el = el.find(attrs={"itemprop": "availability"})

            name = name_el.get_text(strip=True) if name_el else ""
            if not name:
                continue

            price = None
            if price_el:
                content = price_el.get("content") or price_el.get_text(strip=True)
                try:
                    price = float(re.sub(r"[^\d.]", "", content))
                except (ValueError, TypeError):
                    pass

            images = []
            if img_el and img_el.get("src"):
                images.append(urljoin(base_url, img_el["src"]))

            products.append(
                Product(
                    name=name,
                    price=price,
                    description=(desc_el.get_text(" ", strip=True)[:300] if desc_el else ""),
                    images=images,
                    availability=(avail_el.get_text(strip=True) if avail_el else ""),
                )
            )

        if products:
            return products

        # Strategy 2: Common CSS class patterns for product cards
        product_containers = soup.find_all(
            class_=lambda c: (
                c and any(k in c.lower() for k in ["product", "item", "card", "listing"])
            )
        )

        for container in product_containers[:100]:
            # Find name (heading inside container)
            name_el = container.find(["h1", "h2", "h3", "h4", "h5", "a"])
            if not name_el:
                continue
            name = name_el.get_text(strip=True)
            if not name or len(name) < 2 or len(name) > 200:
                continue

            # Find price
            text = container.get_text(" ", strip=True)
            price_matches = PRICE_RE.findall(text)
            price = None
            if price_matches:
                try:
                    price = float(price_matches[0].replace("$", "").replace(",", "").strip())
                except ValueError:
                    pass

            # Find image
            images = []
            img = container.find("img")
            if img and img.get("src"):
                images.append(urljoin(base_url, img["src"]))

            # Find link
            link = ""
            a_tag = container.find("a", href=True)
            if a_tag:
                link = urljoin(base_url, a_tag["href"])

            # Availability
            avail = ""
            avail_el = container.find(
                class_=lambda c: c and any(k in c.lower() for k in ["stock", "avail", "inventory"])
            )
            if avail_el:
                avail = avail_el.get_text(strip=True)

            products.append(
                Product(
                    name=name,
                    price=price,
                    images=images,
                    availability=avail,
                    url=link,
                )
            )

        # Deduplicate by name
        seen: set[str] = set()
        unique: list[Product] = []
        for p in products:
            key = p.name.lower()
            if key not in seen:
                seen.add(key)
                unique.append(p)

        return unique
