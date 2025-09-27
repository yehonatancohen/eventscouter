"""TikTok hashtag search utilities using the public TikWM API."""
from __future__ import annotations

import datetime as dt
import logging
from typing import Iterable, List

import requests

_LOGGER = logging.getLogger(__name__)
_API_ENDPOINT = "https://www.tikwm.com/api/search"


def _parse_timestamp(value: object) -> dt.datetime | None:
    """Parse TikTok timestamps into aware ``datetime`` objects."""
    if value in (None, "", 0):
        return None
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return None
    try:
        return dt.datetime.fromtimestamp(numeric, tz=dt.timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def _coerce_title(video: dict) -> str | None:
    candidates: Iterable[str | None] = (
        video.get("title"),
        video.get("desc"),
        video.get("description"),
    )
    for candidate in candidates:
        if candidate:
            return str(candidate).strip()
    author = video.get("author") or {}
    username = None
    if isinstance(author, dict):
        username = author.get("unique_id") or author.get("nickname")
    if username:
        return f"TikTok by @{username}"
    return None


def _coerce_share_url(video: dict) -> str | None:
    candidates: Iterable[str | None] = (
        video.get("share_url"),
        video.get("play"),
        video.get("url"),
        video.get("video_url"),
    )
    for candidate in candidates:
        if candidate:
            text = str(candidate).strip()
            if text:
                return text
    return None


def _normalize_video(video: dict) -> dict | None:
    link = _coerce_share_url(video)
    if not link:
        return None
    title = _coerce_title(video)
    if not title:
        title = "TikTok video"
    created_at = _parse_timestamp(video.get("create_time"))
    normalized = {
        "title": f"[TikTok] {title}",
        "link": link,
        "created_at": created_at,
        "play_count": video.get("play_count"),
        "digg_count": video.get("digg_count"),
    }
    return normalized


def fetch_hashtag(
    keyword: str,
    *,
    limit: int = 8,
    days: int = 7,
) -> List[dict]:
    """Fetch recent TikToks for a hashtag or keyword.

    The implementation relies on the free TikWM API which provides search results
    for TikTok without authentication. Results are filtered to roughly match the
    requested timeframe, prioritising higher engagement clips first.
    """

    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    params = {
        "keywords": keyword,
        "count": max(limit * 3, 24),
        "page": 1,
    }
    _LOGGER.debug("Fetching TikTok search", extra={"keyword": keyword, "params": params})
    try:
        response = requests.get(_API_ENDPOINT, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        _LOGGER.exception("Failed to fetch TikTok search", extra={"keyword": keyword})
        return []

    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        _LOGGER.debug("TikTok payload missing data", extra={"keyword": keyword})
        return []

    videos: Iterable[dict] = []
    if isinstance(data.get("videos"), list):
        videos = data["videos"]
    elif isinstance(data.get("list"), list):
        videos = data["list"]

    normalized: List[dict] = []
    for raw in videos:
        if not isinstance(raw, dict):
            continue
        item = _normalize_video(raw)
        if not item:
            continue
        created = item["created_at"]
        if created and created < cutoff:
            continue
        normalized.append(item)

    normalized.sort(
        key=lambda item: (
            item.get("play_count") or 0,
            item.get("digg_count") or 0,
            item.get("created_at") or dt.datetime.min.replace(tzinfo=dt.timezone.utc),
        ),
        reverse=True,
    )

    results: List[dict] = []
    for item in normalized:
        payload = {
            "title": item["title"],
            "link": item["link"],
        }
        created = item.get("created_at")
        if isinstance(created, dt.datetime):
            payload["created_at"] = created.isoformat()
        if item.get("play_count") is not None:
            payload["play_count"] = item["play_count"]
        if item.get("digg_count") is not None:
            payload["digg_count"] = item["digg_count"]
        results.append(payload)
        if len(results) >= limit:
            break

    _LOGGER.info("Fetched %s TikTok items", len(results), extra={"keyword": keyword})
    return results


__all__ = ["fetch_hashtag", "_normalize_video", "_parse_timestamp"]
