"""Tests for extraction plugins."""

from __future__ import annotations


from crawl0.plugins.restaurant import RestaurantExtractor, RestaurantData
from crawl0.plugins.ecommerce import EcommerceExtractor, EcommerceData
from crawl0.plugins.contact import ContactExtractor, ContactData
from crawl0.plugins.social import SocialExtractor, SocialData, _parse_count
from crawl0.plugins import EXTRACTORS


class TestRestaurantExtractor:
    def test_extract_phone(self):
        html = "<html><body>Call us at (702) 555-1234</body></html>"
        ext = RestaurantExtractor()
        result = ext.extract_from_html(html, "https://example.com")
        assert isinstance(result, RestaurantData)
        assert result.phone == "(702) 555-1234"

    def test_extract_cuisine(self):
        html = "<html><body>Authentic Mexican food and tacos</body></html>"
        ext = RestaurantExtractor()
        result = ext.extract_from_html(html, "https://example.com")
        assert "mexican" in result.cuisine_type
        assert "tacos" in result.cuisine_type

    def test_extract_name_from_og(self):
        html = '<html><head><meta property="og:site_name" content="Don Sazon"></head><body></body></html>'
        ext = RestaurantExtractor()
        result = ext.extract_from_html(html, "https://example.com")
        assert result.name == "Don Sazon"

    def test_extract_address(self):
        html = "<html><body><address>123 Main St, Las Vegas, NV 89101</address></body></html>"
        ext = RestaurantExtractor()
        result = ext.extract_from_html(html, "https://example.com")
        assert result.address is not None
        assert "123 Main St" in result.address

    def test_extract_menu_items(self):
        html = """<html><body>
        <div class="menu-item">Tacos $12.99 Corn tortillas with carne asada</div>
        <div class="menu-item">Burrito $10.50 Large flour tortilla</div>
        </body></html>"""
        ext = RestaurantExtractor()
        result = ext.extract_from_html(html, "https://example.com")
        assert len(result.menu_items) >= 1


class TestEcommerceExtractor:
    def test_schema_org_product(self):
        html = """<html><body>
        <div itemscope itemtype="http://schema.org/Product">
            <span itemprop="name">Cool Widget</span>
            <span itemprop="price" content="29.99">$29.99</span>
            <span itemprop="description">A very cool widget</span>
        </div>
        </body></html>"""
        ext = EcommerceExtractor()
        result = ext.extract_from_html(html, "https://example.com")
        assert isinstance(result, EcommerceData)
        assert len(result.products) == 1
        assert result.products[0].name == "Cool Widget"
        assert result.products[0].price == 29.99

    def test_css_class_products(self):
        html = """<html><body>
        <div class="product-card"><h3>Widget A</h3><span>$19.99</span></div>
        <div class="product-card"><h3>Widget B</h3><span>$24.99</span></div>
        </body></html>"""
        ext = EcommerceExtractor()
        result = ext.extract_from_html(html, "https://example.com")
        assert len(result.products) == 2


class TestContactExtractor:
    def test_extract_email(self):
        html = "<html><body>Contact us at info@example.com</body></html>"
        ext = ContactExtractor()
        result = ext.extract_from_html(html, "https://example.com")
        assert isinstance(result, ContactData)
        assert "info@example.com" in result.emails

    def test_extract_phone(self):
        html = "<html><body>Call 702-555-1234 now</body></html>"
        ext = ContactExtractor()
        result = ext.extract_from_html(html, "https://example.com")
        assert len(result.phones) > 0

    def test_extract_social_links(self):
        html = """<html><body>
        <a href="https://twitter.com/example">Twitter</a>
        <a href="https://www.instagram.com/example">Instagram</a>
        <a href="https://www.facebook.com/example">Facebook</a>
        </body></html>"""
        ext = ContactExtractor()
        result = ext.extract_from_html(html, "https://example.com")
        assert "twitter" in result.social_links
        assert "instagram" in result.social_links
        assert "facebook" in result.social_links

    def test_extract_address_tag(self):
        html = "<html><body><address>456 Oak Ave, Henderson, NV</address></body></html>"
        ext = ContactExtractor()
        result = ext.extract_from_html(html, "https://example.com")
        assert len(result.addresses) > 0


class TestSocialExtractor:
    def test_parse_count(self):
        assert _parse_count("1.2K") == 1200
        assert _parse_count("5M") == 5_000_000
        assert _parse_count("12,345") == 12345
        assert _parse_count("100") == 100

    def test_extract_username_from_url(self):
        html = "<html><body>Profile</body></html>"
        ext = SocialExtractor()
        result = ext.extract_from_html(html, "https://twitter.com/elonmusk")
        assert isinstance(result, SocialData)
        assert result.username == "elonmusk"
        assert result.platform == "twitter"

    def test_extract_display_name(self):
        html = (
            '<html><head><meta property="og:title" content="Elon Musk"></head><body></body></html>'
        )
        ext = SocialExtractor()
        result = ext.extract_from_html(html, "https://x.com/elonmusk")
        assert result.display_name == "Elon Musk"

    def test_extract_followers(self):
        html = "<html><body>12.5K followers 500 following</body></html>"
        ext = SocialExtractor()
        result = ext.extract_from_html(html, "https://instagram.com/test")
        assert result.followers == 12500
        assert result.following == 500


class TestExtractorRegistry:
    def test_all_schemas_registered(self):
        assert "restaurant" in EXTRACTORS
        assert "ecommerce" in EXTRACTORS
        assert "contact" in EXTRACTORS
        assert "social" in EXTRACTORS
