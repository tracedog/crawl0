"""Tests for HTML parser and markdown converter."""

from crawl0.core.parser import parse_html, extract_metadata, html_to_markdown, clean_html
from bs4 import BeautifulSoup


SAMPLE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Test Page</title>
    <meta name="description" content="A test page for crawl0">
    <meta property="og:title" content="OG Test Page">
    <meta property="og:image" content="https://example.com/image.jpg">
    <link rel="canonical" href="https://example.com/test">
</head>
<body>
    <nav><a href="/home">Home</a><a href="/about">About</a></nav>
    <main>
        <h1>Hello World</h1>
        <p>This is a test paragraph with <a href="/link1">a link</a>.</p>
        <p>Another paragraph with an <img src="/image.png" alt="test"> image.</p>
    </main>
    <footer>Copyright 2026</footer>
    <script>console.log("hi")</script>
</body>
</html>
"""


def test_parse_html_returns_tuple():
    md, metadata, links, images = parse_html(SAMPLE_HTML, "https://example.com")
    assert isinstance(md, str)
    assert isinstance(links, list)
    assert isinstance(images, list)


def test_metadata_extraction():
    soup = BeautifulSoup(SAMPLE_HTML, "lxml")
    meta = extract_metadata(soup, "https://example.com")
    assert meta.title == "Test Page"
    assert meta.description == "A test page for crawl0"
    assert meta.og_title == "OG Test Page"
    assert meta.og_image == "https://example.com/image.jpg"
    assert meta.canonical_url == "https://example.com/test"
    assert meta.language == "en"


def test_markdown_contains_content():
    md = html_to_markdown(SAMPLE_HTML)
    assert "Hello World" in md
    assert "test paragraph" in md


def test_strips_nav_footer_script():
    md = html_to_markdown(SAMPLE_HTML)
    assert "Copyright 2026" not in md
    assert "console.log" not in md


def test_links_extraction():
    _, _, links, _ = parse_html(SAMPLE_HTML, "https://example.com")
    assert "https://example.com/link1" in links
    assert "https://example.com/home" in links


def test_images_extraction():
    _, _, _, images = parse_html(SAMPLE_HTML, "https://example.com")
    assert "https://example.com/image.png" in images


def test_clean_html_removes_scripts():
    soup = clean_html(SAMPLE_HTML)
    assert soup.find("script") is None
    assert soup.find("nav") is None
    assert soup.find("footer") is None
