"""HTML → Markdown converter with metadata extraction."""

from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup, Comment
from markdownify import markdownify

from crawl0.models import PageMetadata


# Tags/classes/ids to strip before converting
STRIP_TAGS = {"script", "style", "noscript", "iframe", "svg"}
STRIP_ROLES = {"navigation", "banner", "contentinfo", "complementary", "search"}
STRIP_TAGS_SEMANTIC = {"nav", "footer", "header"}
STRIP_CLASS_PATTERNS = {
    "sidebar", "menu", "nav", "footer", "header", "banner", "cookie",
    "popup", "modal", "overlay", "advertisement", "ad-", "social-share",
    "breadcrumb", "pagination",
}


def _should_strip_element(tag: BeautifulSoup) -> bool:
    """Check if an element should be stripped based on tag, role, or class."""
    if tag.name in STRIP_TAGS:
        return True
    if tag.name in STRIP_TAGS_SEMANTIC:
        return True
    role = tag.get("role", "")
    if role in STRIP_ROLES:
        return True
    classes = " ".join(tag.get("class", []))
    tag_id = tag.get("id", "")
    combined = f"{classes} {tag_id}".lower()
    return any(pattern in combined for pattern in STRIP_CLASS_PATTERNS)


def extract_metadata(soup: BeautifulSoup, url: str) -> PageMetadata:
    """Extract page metadata from HTML."""
    def meta_content(name: str | None = None, property: str | None = None) -> str | None:
        attrs = {}
        if name:
            attrs["name"] = name
        if property:
            attrs["property"] = property
        tag = soup.find("meta", attrs=attrs)
        return tag.get("content") if tag else None

    title_tag = soup.find("title")
    link_canonical = soup.find("link", attrs={"rel": "canonical"})
    link_icon = soup.find("link", attrs={"rel": lambda x: x and "icon" in x.lower()}) if soup.find("link") else None
    html_tag = soup.find("html")

    return PageMetadata(
        title=title_tag.get_text(strip=True) if title_tag else None,
        description=meta_content(name="description"),
        author=meta_content(name="author"),
        og_title=meta_content(property="og:title"),
        og_description=meta_content(property="og:description"),
        og_image=meta_content(property="og:image"),
        og_url=meta_content(property="og:url"),
        og_type=meta_content(property="og:type"),
        canonical_url=link_canonical.get("href") if link_canonical else None,
        language=html_tag.get("lang") if html_tag else None,
        favicon=urljoin(url, link_icon.get("href")) if link_icon and link_icon.get("href") else None,
    )


def extract_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Extract all links from page."""
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        links.append(urljoin(base_url, href))
    return list(dict.fromkeys(links))  # deduplicate preserving order


def extract_images(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Extract all image URLs from page."""
    images: list[str] = []
    for img in soup.find_all("img", src=True):
        images.append(urljoin(base_url, img["src"]))
    return list(dict.fromkeys(images))


def clean_html(html: str) -> BeautifulSoup:
    """Parse and clean HTML, stripping non-content elements."""
    soup = BeautifulSoup(html, "lxml")

    # Remove comments
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    # Remove unwanted elements (collect first, then decompose to avoid mutation issues)
    to_remove = [tag for tag in soup.find_all(True) if _should_strip_element(tag)]
    for tag in to_remove:
        tag.decompose()

    return soup


def html_to_markdown(html: str) -> str:
    """Convert HTML to clean markdown."""
    soup = clean_html(html)

    # Find main content area
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(attrs={"role": "main"})
        or soup.find("div", class_=lambda c: c and "content" in " ".join(c).lower())
        or soup.body
        or soup
    )

    md = markdownify(str(main), heading_style="ATX", strip=["img"])

    # Clean up excessive whitespace
    lines = md.split("\n")
    cleaned: list[str] = []
    prev_blank = False
    for line in lines:
        stripped = line.rstrip()
        is_blank = not stripped
        if is_blank and prev_blank:
            continue
        cleaned.append(stripped)
        prev_blank = is_blank

    return "\n".join(cleaned).strip()


def parse_html(html: str, url: str) -> tuple[str, PageMetadata, list[str], list[str]]:
    """Parse HTML and return (markdown, metadata, links, images).

    Args:
        html: Raw HTML string.
        url: The page URL for resolving relative links.

    Returns:
        Tuple of (markdown, metadata, links, images).
    """
    soup = BeautifulSoup(html, "lxml")
    metadata = extract_metadata(soup, url)
    links = extract_links(soup, url)
    images = extract_images(soup, url)
    markdown = html_to_markdown(html)
    return markdown, metadata, links, images
