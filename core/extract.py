import requests, re
from bs4 import BeautifulSoup
from readability import Document

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; EventScout/1.0)"}

def fetch_html(url: str, timeout: int = 15) -> str:
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text

def extract_text_and_videos(url: str):
    html = fetch_html(url)
    doc = Document(html)
    content_html = doc.summary()
    soup = BeautifulSoup(content_html, "lxml")
    text = soup.get_text(" ", strip=True)

    video_links = set()
    # direct video tags
    for v in soup.select("video source, video"):
        src = v.get("src") or v.get("data-src")
        if src and any(src.lower().endswith(ext) for ext in [".mp4", ".m3u8", ".webm"]):
            video_links.add(src)

    # og:video
    for meta in soup.select('meta[property="og:video"], meta[property="og:video:url"], meta[property="og:video:secure_url"]'):
        c = meta.get("content")
        if c: video_links.add(c)

    # common platforms — keep page links for in‑app repost (no scraping)
    platform_links = set()
    for a in soup.select("a[href]"):
        href = a["href"]
        if any(p in href for p in ["tiktok.com", "instagram.com", "facebook.com/reel", "fb.watch", "v.redd.it"]):
            platform_links.add(href)

    return text, sorted(video_links), sorted(platform_links)
