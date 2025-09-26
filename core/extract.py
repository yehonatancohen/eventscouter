"""HTML extraction helpers for EventScout."""
from __future__ import annotations

import logging

import requests
from bs4 import BeautifulSoup
from readability import Document

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; EventScout/1.0)"}
LOGGER = logging.getLogger(__name__)


def fetch_html(url: str, timeout: int = 15) -> str:
    LOGGER.debug("Fetching HTML", extra={"url": url, "timeout": timeout})
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    LOGGER.info("Fetched HTML", extra={"url": url, "bytes": len(response.content)})
    return response.text


def extract_text_and_videos(url: str):
    """Return (text, direct_videos, platform_links) from a web page."""
    html = fetch_html(url)
    doc = Document(html)
    content_html = doc.summary()
    soup = BeautifulSoup(content_html, "lxml")
    text = soup.get_text(" ", strip=True)

    video_links = set()
    for video in soup.select("video source, video"):
        src = video.get("src") or video.get("data-src")
        if src and any(src.lower().endswith(ext) for ext in [".mp4", ".m3u8", ".webm"]):
            video_links.add(src)

    for meta in soup.select(
        'meta[property="og:video"], meta[property="og:video:url"], meta[property="og:video:secure_url"]'
    ):
        content = meta.get("content")
        if content:
            video_links.add(content)

    platform_links = set()
    for anchor in soup.select("a[href]"):
        href = anchor["href"]
        if any(
            platform in href
            for platform in ["tiktok.com", "instagram.com", "facebook.com/reel", "fb.watch", "v.redd.it"]
        ):
            platform_links.add(href)

    LOGGER.debug(
        "Extracted media references",
        extra={
            "url": url,
            "videos": len(video_links),
            "platform_links": len(platform_links),
            "text_length": len(text),
        },
    )

    return text, sorted(video_links), sorted(platform_links)
