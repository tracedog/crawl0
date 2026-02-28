"""Crawl0 extraction plugins."""

from crawl0.plugins.base import BaseExtractor
from crawl0.plugins.restaurant import RestaurantExtractor
from crawl0.plugins.ecommerce import EcommerceExtractor
from crawl0.plugins.contact import ContactExtractor
from crawl0.plugins.social import SocialExtractor

EXTRACTORS: dict[str, type[BaseExtractor]] = {
    "restaurant": RestaurantExtractor,
    "ecommerce": EcommerceExtractor,
    "contact": ContactExtractor,
    "social": SocialExtractor,
}

__all__ = [
    "BaseExtractor",
    "RestaurantExtractor",
    "EcommerceExtractor",
    "ContactExtractor",
    "SocialExtractor",
    "EXTRACTORS",
]
