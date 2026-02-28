"""Base extractor abstract class."""

from __future__ import annotations

from abc import ABC, abstractmethod

from bs4 import BeautifulSoup
from pydantic import BaseModel


class BaseExtractor(ABC):
    """Abstract base class for extraction plugins.

    Subclasses implement `extract()` to pull structured data from HTML
    using BeautifulSoup + heuristics. No LLMs, no paid APIs.
    """

    @abstractmethod
    def extract(self, soup: BeautifulSoup, url: str) -> BaseModel:
        """Extract structured data from parsed HTML.

        Args:
            soup: BeautifulSoup-parsed HTML.
            url: The source URL.

        Returns:
            A Pydantic model with the extracted data.
        """
        ...

    def extract_from_html(self, html: str, url: str) -> BaseModel:
        """Convenience: extract from raw HTML string.

        Args:
            html: Raw HTML string.
            url: The source URL.

        Returns:
            A Pydantic model with the extracted data.
        """
        soup = BeautifulSoup(html, "lxml")
        return self.extract(soup, url)
