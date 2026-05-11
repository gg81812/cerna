"""
source_urls.py — Map internal filenames to the original public source URLs.

Every file under data/<module>/*.txt|.md has a header like:
    # SOURCE: Cerner eMAR Electronic Medication Administration Record
    # URL: https://wiki.cerner.com/...
    # MODULE: Clinical Workflows
    # RETRIEVED: 2026-04-01

This module parses those headers once at first call and exposes:
  - get_url(filename) -> str | None         (just the URL)
  - get_title(filename) -> str | None       (the SOURCE: line)
  - enrich_recommendations(text, chunks)    (append markdown links)
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path

_DATA_DIR = Path(__file__).parent / "data"

# Match headers in any of the formats actually used in data/:
#   `# URL: https://...`         (commented header)
#   `URL: https://...`           (uncommented)
#   `# SOURCE: Cerner eMAR ...`  (title with prefix)
#   `Source: https://...`        (older format — URL inline after Source:)
_URL_LINE_RE = re.compile(r"^\s*#?\s*URL\s*:\s*(https?\S+)", re.IGNORECASE)
_SOURCE_URL_RE = re.compile(r"^\s*#?\s*Source\s*:\s*(https?\S+)", re.IGNORECASE)
_SOURCE_TITLE_RE = re.compile(r"^\s*#?\s*SOURCE\s*:\s*(.+?)\s*$", re.IGNORECASE)

# Heuristic boundary keywords — lines starting with these aren't titles.
_HEADER_KEYWORDS = ("source:", "url:", "scraped:", "retrieved:", "module:", "title:", "---")


def _parse_headers(path: Path) -> tuple[str | None, str | None]:
    """Return (title, url) from the file header; both may be None."""
    title: str | None = None
    url: str | None = None
    fallback_title: str | None = None
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()[:10]
    except (OSError, UnicodeDecodeError):
        return None, None

    for raw in lines:
        line = raw.rstrip()
        stripped = line.lstrip("# ").strip()
        if not stripped:
            continue

        # URL detection (priority: explicit URL: header, then inline Source: URL)
        if url is None:
            m = _URL_LINE_RE.match(line) or _SOURCE_URL_RE.match(line)
            if m:
                url = m.group(1).strip().rstrip(").,;")
                continue

        # Title detection: explicit SOURCE: <text> header (not a URL line)
        if title is None:
            m = _SOURCE_TITLE_RE.match(line)
            if m and not m.group(1).lower().startswith(("http://", "https://")):
                title = m.group(1).strip()
                continue

        # First plain content line becomes fallback title (skip header rows)
        lower = stripped.lower()
        if (
            fallback_title is None
            and not any(lower.startswith(k) for k in _HEADER_KEYWORDS)
            and len(stripped) > 4
        ):
            fallback_title = stripped.lstrip("#").strip()

        if title and url:
            break

    return (title or fallback_title), url


@lru_cache(maxsize=1)
def _url_map() -> dict[str, tuple[str | None, str | None]]:
    """Scan data/ once and cache the {filename: (title, url)} map."""
    mp: dict[str, tuple[str | None, str | None]] = {}
    if not _DATA_DIR.exists():
        return mp
    for path in _DATA_DIR.rglob("*"):
        if path.suffix.lower() in (".txt", ".md"):
            title, url = _parse_headers(path)
            if title or url:
                mp[path.name] = (title, url)
    return mp


def get_url(filename: str) -> str | None:
    """Look up the source URL for a data filename. Returns None if unknown."""
    if not filename:
        return None
    name = os.path.basename(filename)
    entry = _url_map().get(name)
    return entry[1] if entry else None


def get_title(filename: str) -> str | None:
    """Look up the source title for a data filename. Returns None if unknown."""
    if not filename:
        return None
    name = os.path.basename(filename)
    entry = _url_map().get(name)
    return entry[0] if entry else None


def enrich_recommendations(recommendations: str, chunks, max_links: int = 3) -> str:
    """
    Append a 'Reference sources' section with up to `max_links` clickable URLs
    drawn from the top retrieved chunks. Deduplicates by URL.

    `chunks` may be a list of RetrievedChunk objects or chunk dicts — anything
    with a `source` attribute or "source" key.
    """
    if not chunks:
        return recommendations or ""

    seen: list[tuple[str, str]] = []  # (title, url)
    for c in chunks[: max_links * 3]:  # over-sample then dedupe
        if hasattr(c, "source"):
            fname = c.source
        elif isinstance(c, dict):
            fname = c.get("source", "")
        else:
            continue
        title = get_title(fname) or fname
        url = get_url(fname)
        if not url:
            continue
        if any(u == url for _, u in seen):
            continue
        # Trim the 'SOURCE:' prefix some files start with
        clean_title = re.sub(r"^SOURCE\s*[:\-]\s*", "", title, flags=re.IGNORECASE).strip()
        seen.append((clean_title or "Source", url))
        if len(seen) >= max_links:
            break

    if not seen:
        return recommendations or ""

    base = (recommendations or "").rstrip()
    links_md = "\n\n**Reference sources:**\n" + "\n".join(
        f"- [{title}]({url})" for title, url in seen
    )
    return base + links_md
