"""Generic RSS fetching helpers."""
from __future__ import annotations

import logging
from typing import List

import feedparser

_LOGGER = logging.getLogger(__name__)


def fetch_rss(url: str, *, limit: int = 10) -> List[dict]:
    """Fetch arbitrary RSS feeds and normalise their entries."""
    _LOGGER.debug("Fetching RSS feed", extra={"url": url})
    feed = feedparser.parse(url)
    if feed.bozo:
        _LOGGER.warning("RSS feed had parsing issues", extra={"url": url, "bozo_exception": str(feed.bozo_exception)})
    items = []
    seen_links: set[str] = set()
    for entry in feed.entries[:limit]:
        title = entry.get("title", "").strip()
        link = entry.get("link", "")
        if not link or link in seen_links:
            continue
        seen_links.add(link)
        published = entry.get("published") or entry.get("updated")
        items.append({"title": title, "link": link, "published": published})
    _LOGGER.info("Fetched %s RSS items", len(items), extra={"url": url})
    return items


__all__ = ["fetch_rss"]
