"""JSON output formatting for scrape results."""

from __future__ import annotations

import json
from typing import Any

from crawl0.models import ScrapeResult


def to_json(result: ScrapeResult, indent: int = 2, include_html: bool = False) -> str:
    """Convert a ScrapeResult to formatted JSON string.

    Args:
        result: The scrape result to serialize.
        indent: JSON indentation level.
        include_html: Whether to include raw HTML in output.

    Returns:
        JSON string.
    """
    data = result.to_dict()
    if not include_html:
        data.pop("html", None)
    return json.dumps(data, indent=indent, ensure_ascii=False, default=str)


def to_dict(result: ScrapeResult, include_html: bool = False) -> dict[str, Any]:
    """Convert a ScrapeResult to a dictionary.

    Args:
        result: The scrape result to convert.
        include_html: Whether to include raw HTML.

    Returns:
        Dictionary representation.
    """
    data = result.to_dict()
    if not include_html:
        data.pop("html", None)
    return data
