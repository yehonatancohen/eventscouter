"""Google News search utilities with better article extraction."""
from __future__ import annotations

import logging
import urllib.parse
from dataclasses import dataclass
from typing import Iterable, List

import feedparser

_LOGGER = logging.getLogger(__name__)


@dataclass
class NewsItem:
    """Normalized representation of a Google News entry."""

    title: str
    link: str
    published: str | None = None


def _build_search_url(query: str, language: str = "en", country: str = "IL") -> str:
    q = urllib.parse.quote_plus(query)
    return (
        f"https://news.google.com/rss/search?q={q}&hl={language}-{country}&gl={country}&ceid={country}:{language}"
    )


def _extract_direct_link(entry_link: str) -> str:
    """Return the destination article, stripping Google redirect parameters."""
    if not entry_link:
        return entry_link
    parsed = urllib.parse.urlparse(entry_link)
    if parsed.netloc.endswith("news.google.com"):
        qs = urllib.parse.parse_qs(parsed.query)
        if "url" in qs and qs["url"]:
            return qs["url"][0]
        if "url=" in entry_link:
            try:
                fragment = entry_link.split("url=", 1)[1]
                fragment = fragment.split("&", 1)[0]
                return urllib.parse.unquote(fragment)
            except Exception:
                _LOGGER.debug("Failed to parse inline url parameter", extra={"link": entry_link})
        if parsed.path.startswith("/rss/articles/"):
            # Some links use `url` in the fragment portion.
            fragment_qs = urllib.parse.parse_qs(parsed.fragment)
            if "url" in fragment_qs and fragment_qs["url"]:
                return fragment_qs["url"][0]
    return entry_link


def _coerce_items(entries: Iterable[feedparser.FeedParserDict]) -> List[NewsItem]:
    items: List[NewsItem] = []
    seen_links: set[str] = set()
    for entry in entries:
        title = entry.get("title", "").strip()
        raw_link = entry.get("link", "")
        link = _extract_direct_link(raw_link)
        if not link or link in seen_links:
            continue
        seen_links.add(link)
        published = entry.get("published") or entry.get("updated")
        items.append(NewsItem(title=title, link=link, published=published))
    return items


def fetch_search(query: str, *, limit: int = 10, language: str = "en", country: str = "IL") -> List[dict]:
    """Fetch Google News search results and return normalized dictionaries."""
    url = _build_search_url(query, language=language, country=country)
    _LOGGER.debug("Fetching Google News feed", extra={"query": query, "url": url})
    feed = feedparser.parse(url)
    if feed.bozo:
        _LOGGER.warning("Google News feed had parsing issues", extra={"query": query, "bozo_exception": str(feed.bozo_exception)})
    items = _coerce_items(feed.entries[:limit])
    _LOGGER.info("Fetched %s Google News items", len(items), extra={"query": query})
    return [item.__dict__ for item in items]


__all__ = ["fetch_search", "NewsItem", "_extract_direct_link"]
