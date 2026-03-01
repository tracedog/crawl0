"""PDF generation from markdown content."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import markdown


def markdown_to_pdf(
    md_content: str,
    output_path: str = "output.pdf",
    title: str = "",
) -> str:
    """Convert markdown to PDF via HTML intermediate.

    Uses weasyprint if available, falls back to writing HTML.

    Args:
        md_content: Markdown string to convert.
        output_path: Path for the output PDF.
        title: Optional document title.

    Returns:
        Path to the generated PDF file.
    """
    # Convert markdown to HTML
    html_body = markdown.markdown(
        md_content,
        extensions=["tables", "fenced_code", "codehilite", "toc"],
    )

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 40px auto;
            padding: 0 20px;
            line-height: 1.6;
            color: #333;
            font-size: 14px;
        }}
        h1, h2, h3, h4 {{ color: #1a1a1a; margin-top: 1.5em; }}
        h1 {{ font-size: 2em; border-bottom: 2px solid #eee; padding-bottom: 0.3em; }}
        h2 {{ font-size: 1.5em; border-bottom: 1px solid #eee; padding-bottom: 0.2em; }}
        pre {{ background: #f5f5f5; padding: 12px; border-radius: 4px; overflow-x: auto; }}
        code {{ background: #f5f5f5; padding: 2px 4px; border-radius: 3px; font-size: 0.9em; }}
        pre code {{ background: none; padding: 0; }}
        table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #f5f5f5; }}
        blockquote {{ border-left: 4px solid #ddd; margin: 0; padding: 0 1em; color: #666; }}
        a {{ color: #0366d6; text-decoration: none; }}
        img {{ max-width: 100%; }}
    </style>
</head>
<body>
{html_body}
</body>
</html>"""

    try:
        from weasyprint import HTML

        HTML(string=html).write_pdf(output_path)
    except ImportError:
        # Fallback: save as HTML (user can print to PDF)
        html_path = output_path.rsplit(".", 1)[0] + ".html"
        Path(html_path).write_text(html, encoding="utf-8")
        return html_path

    return output_path
