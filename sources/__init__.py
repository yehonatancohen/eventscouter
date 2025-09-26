"""Data source fetchers for EventScout."""

from .google_news import fetch_search as fetch_google_news
from .rss import fetch_rss
from .reddit import fetch_subreddit

__all__ = [
    "fetch_google_news",
    "fetch_rss",
    "fetch_subreddit",
]
