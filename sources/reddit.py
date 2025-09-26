"""Minimal Reddit JSON fetcher with lightweight filtering."""
from __future__ import annotations

import logging
from typing import List

SCOOP_KEYWORDS = {
    "breaking",
    "scoop",
    "headline",
    "leak",
    "leaked",
    "leaks",
    "announce",
    "announcement",
    "announced",
    "exclusive",
    "reveals",
    "revealed",
    "new track",
    "new single",
    "new album",
    "tour dates",
    "lineup",
}

VIDEO_HINTS = {"hosted:video", "rich:video", "video"}
VIDEO_DOMAINS = {
    "youtube.com",
    "youtu.be",
    "tiktok.com",
    "instagram.com",
    "facebook.com",
    "fb.watch",
    "streamable.com",
    "v.redd.it",
    "reddit.com",
    "twitter.com",
    "x.com",
}

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
        if not (_looks_like_video(payload, link) or _looks_like_scoop(title)):
            _LOGGER.debug(
                "Skipping subreddit post without scoop/video cues",
                extra={"title": title[:80], "link": link},
            )
            continue
        items.append({
            "title": title,
            "link": link,
            "published": payload.get("created_utc"),
        })
    _LOGGER.info("Fetched %s subreddit items", len(items), extra={"subreddit": subreddit})
    return items


def _looks_like_video(payload: dict, link: str) -> bool:
    link_lower = link.lower()
    post_hint = (payload.get("post_hint") or "").lower()
    domain = (payload.get("domain") or "").lower()

    if payload.get("is_video") or payload.get("media"):
        return True
    if post_hint in VIDEO_HINTS:
        return True
    if link_lower.endswith((".mp4", ".webm", ".mov")):
        return True
    for candidate in VIDEO_DOMAINS:
        if candidate in link_lower or candidate in domain:
            return True
    return False


def _looks_like_scoop(title: str) -> bool:
    normalized = title.lower()
    return any(token in normalized for token in SCOOP_KEYWORDS)


__all__ = ["fetch_subreddit"]
