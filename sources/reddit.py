"""Minimal Reddit JSON fetcher with lightweight filtering."""
from __future__ import annotations

import logging
from typing import List

import requests

_LOGGER = logging.getLogger(__name__)
_USER_AGENT = "Mozilla/5.0 (compatible; EventScout/1.0; +https://github.com/)"


def fetch_subreddit(subreddit: str, *, limit: int = 10, t: str = "day") -> List[dict]:
    """Fetch top submissions from a subreddit using the public JSON endpoint."""
    url = f"https://www.reddit.com/r/{subreddit}/top.json"
    params = {"limit": limit, "t": t}
    headers = {"User-Agent": _USER_AGENT}
    _LOGGER.debug("Fetching subreddit", extra={"subreddit": subreddit, "url": url, "params": params})
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        _LOGGER.warning("Failed to fetch subreddit", extra={"subreddit": subreddit, "error": str(exc)})
        return []

    data = response.json()
    children = data.get("data", {}).get("children", [])
    items: List[dict] = []
    for child in children:
        payload = child.get("data", {})
        if payload.get("stickied") or payload.get("over_18"):
            continue
        title = payload.get("title", "").strip()
        link = payload.get("url_overridden_by_dest") or payload.get("url")
        if not link:
            continue
        score = payload.get("score", 0)
        num_comments = payload.get("num_comments", 0)
        if score < 20 and num_comments < 3:
            # Filter low-signal posts to reduce noise.
            continue
        items.append({
            "title": title,
            "link": link,
            "published": payload.get("created_utc"),
        })
    _LOGGER.info("Fetched %s subreddit items", len(items), extra={"subreddit": subreddit})
    return items


__all__ = ["fetch_subreddit"]
