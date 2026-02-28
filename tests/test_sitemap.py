"""Tests for sitemap discovery and parsing."""

from __future__ import annotations

from crawl0.utils.sitemap import _parse_sitemap_xml


class TestSitemapParsing:
    def test_parse_urlset(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/page1</loc></url>
            <url><loc>https://example.com/page2</loc></url>
        </urlset>"""
        pages, subs = _parse_sitemap_xml(xml)
        assert len(pages) == 2
        assert "https://example.com/page1" in pages
        assert len(subs) == 0

    def test_parse_sitemap_index(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <sitemap><loc>https://example.com/sitemap1.xml</loc></sitemap>
            <sitemap><loc>https://example.com/sitemap2.xml</loc></sitemap>
        </sitemapindex>"""
        pages, subs = _parse_sitemap_xml(xml)
        assert len(pages) == 0
        assert len(subs) == 2
        assert "https://example.com/sitemap1.xml" in subs

    def test_parse_invalid_xml(self):
        pages, subs = _parse_sitemap_xml("not xml at all")
        assert pages == []
        assert subs == []

    def test_parse_empty_urlset(self):
        xml = """<?xml version="1.0"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        </urlset>"""
        pages, subs = _parse_sitemap_xml(xml)
        assert pages == []
        assert subs == []
