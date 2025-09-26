"""EventScout bot entrypoint with improved filtering and scheduling."""
from __future__ import annotations

import argparse
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

import requests
from dotenv import load_dotenv

from core.rank import final_score, load_keywords
from core.utils import hash_id, load_seen, norm_text, save_seen
from sources.google_news import fetch_search
from sources.reddit import fetch_subreddit
from sources.rss import fetch_rss

LOGGER = logging.getLogger("eventscout")


@dataclass
class Candidate:
    uid: str
    title: str
    link: str
    score: float
    videos: List[str]
    platform_links: List[str]


def configure_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def send_telegram(token: str, chat_id: str, text: str, *, preview: bool = True) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": not preview,
        "parse_mode": "HTML",
    }
    LOGGER.debug("Sending Telegram message", extra={"length": len(text)})
    response = requests.post(url, json=payload, timeout=20)
    response.raise_for_status()
    LOGGER.info("Telegram message delivered", extra={"bytes": len(response.content)})


def collect_candidates(qconf: Dict, *, max_per_source: int = 10) -> List[dict]:
    items: List[dict] = []
    seen_links: set[str] = set()

    for query in qconf.get("google_news_queries", []):
        try:
            results = fetch_search(query, limit=max_per_source)
            LOGGER.debug("Google News results", extra={"query": query, "count": len(results)})
            for result in results:
                if result["link"] not in seen_links:
                    items.append(result)
                    seen_links.add(result["link"])
        except Exception:
            LOGGER.exception("Failed to fetch Google News", extra={"query": query})

    for query in qconf.get("social_video_queries", []):
        try:
            results = fetch_search(query, limit=max_per_source, language="iw")
            LOGGER.debug(
                "Social video query results",
                extra={"query": query, "count": len(results)},
            )
            for result in results:
                if result["link"] not in seen_links:
                    items.append(result)
                    seen_links.add(result["link"])
        except Exception:
            LOGGER.exception("Failed to fetch social video query", extra={"query": query})

    for url in qconf.get("rss_feeds", []):
        try:
            results = fetch_rss(url, limit=max_per_source)
            LOGGER.debug("RSS results", extra={"url": url, "count": len(results)})
            for result in results:
                if result["link"] not in seen_links:
                    items.append(result)
                    seen_links.add(result["link"])
        except Exception:
            LOGGER.exception("Failed to fetch RSS feed", extra={"url": url})

    for subreddit in qconf.get("subreddits", []):
        try:
            results = fetch_subreddit(subreddit, limit=8, t="day")
            LOGGER.debug("Reddit results", extra={"subreddit": subreddit, "count": len(results)})
            for result in results:
                if result["link"] not in seen_links:
                    items.append(result)
                    seen_links.add(result["link"])
        except Exception:
            LOGGER.exception("Failed to fetch subreddit", extra={"subreddit": subreddit})

    LOGGER.info("Collected %s unique raw candidates", len(items))
    return items


def enrich_candidates(
    raw_items: Sequence[dict],
    seen_ids: set[str],
    *,
    use_llm: bool,
    ollama_endpoint: str,
    ollama_model: str,
) -> List[Candidate]:
    from core.extract import extract_text_and_videos

    enriched: List[Candidate] = []
    for item in raw_items:
        uid = hash_id(item["link"])
        if uid in seen_ids:
            LOGGER.debug("Skipping already seen candidate", extra={"link": item["link"]})
            continue
        title = norm_text(item.get("title", ""))
        try:
            text, direct_videos, platform_links = extract_text_and_videos(item["link"])
        except Exception:
            LOGGER.exception("Failed to extract content", extra={"link": item["link"]})
            text, direct_videos, platform_links = "", [], []
        score = round(
            final_score(title, text, use_llm, ollama_endpoint, ollama_model),
            2,
        )
        if direct_videos or platform_links:
            score = round(score + 1.2, 2)
        LOGGER.debug(
            "Candidate scored",
            extra={"link": item["link"], "score": score, "title": title[:80]},
        )
        enriched.append(
            Candidate(
                uid=uid,
                title=title,
                link=item["link"],
                score=score,
                videos=direct_videos,
                platform_links=platform_links,
            )
        )
    return enriched


def select_top_candidates(
    candidates: Iterable[Candidate],
    *,
    limit: int,
    min_score: float,
) -> List[Candidate]:
    filtered = [c for c in candidates if c.score >= min_score]
    LOGGER.info(
        "Filtered candidates by score",
        extra={"kept": len(filtered), "min_score": min_score},
    )
    filtered.sort(key=lambda c: c.score, reverse=True)
    return filtered[:limit]


def format_digest(candidates: Sequence[Candidate]) -> str:
    lines: List[str] = []
    lines.append(f"🎛️ EventScout — {len(candidates)} high-quality leads")
    lines.append("")
    for idx, candidate in enumerate(candidates, start=1):
        lines.append(f"<b>{idx}. {candidate.title}</b>")
        lines.append(f"Score: {candidate.score} · Source: {candidate.link}")
        if candidate.videos:
            video_lines = "\n".join(candidate.videos[:3])
            lines.append(f"🎬 Direct video links:\n{video_lines}")
        if candidate.platform_links:
            platform_lines = "\n".join(candidate.platform_links[:3])
            lines.append(f"📱 Platform references:\n{platform_lines}")
        lines.append("")
    return "\n".join(lines).strip()


def _detect_city(title: str) -> str | None:
    lowered = title.lower()
    for city in load_keywords()["cities"]:
        if city in lowered:
            return city.title()
    return None


def _generate_social_titles(candidate: Candidate, city: str | None) -> List[str]:
    base = candidate.title
    if len(base) > 90:
        base = base[:87] + "..."
    titles: List[str] = []
    if city:
        titles.append(f"{city} Nightlife Scoop: {base}")
        titles.append(f"{city} Party Cam: {base}")
    else:
        titles.append(f"Festival FOMO Alert: {base}")
        titles.append(f"Aftermovie Drop: {base}")
    return titles


def build_social_video_suggestion(candidates: Sequence[Candidate]) -> str:
    if not candidates:
        return ""

    prioritized = sorted(
        candidates,
        key=lambda c: (
            bool(c.videos or c.platform_links),
            len(c.videos),
            len(c.platform_links),
            c.score,
        ),
        reverse=True,
    )

    for candidate in prioritized:
        media_link = None
        if candidate.videos:
            media_link = candidate.videos[0]
        elif candidate.platform_links:
            media_link = candidate.platform_links[0]
        if not media_link:
            continue

        city = _detect_city(candidate.title)
        titles = _generate_social_titles(candidate, city)
        lines = [
            "🔥 Suggested social upload",
            f"Inspiration: {candidate.title}",
            f"Clip to feature: {media_link}",
            "Catchy titles:",
        ]
        lines.extend(f"• {title}" for title in titles)
        lines.append(f"Context source: {candidate.link}")
        suggestion = "\n".join(lines)
        LOGGER.info(
            "Prepared social upload suggestion",
            extra={"title": candidate.title[:80], "media_link": media_link},
        )
        return suggestion

    return ""


def compose_message(candidates: Sequence[Candidate]) -> str:
    body = format_digest(candidates)
    suggestion = build_social_video_suggestion(candidates)
    if suggestion:
        return f"{body}\n\n{suggestion}"
    return body


def run_cycle(
    *,
    token: str,
    chat_id: str,
    qconf: Dict,
    seen_ids: set[str],
    max_per_source: int,
    limit: int,
    min_score: float,
    use_llm: bool,
    ollama_endpoint: str,
    ollama_model: str,
) -> None:
    LOGGER.info("Starting collection cycle")
    raw_items = collect_candidates(qconf, max_per_source=max_per_source)
    candidates = enrich_candidates(
        raw_items,
        seen_ids,
        use_llm=use_llm,
        ollama_endpoint=ollama_endpoint,
        ollama_model=ollama_model,
    )
    top_candidates = select_top_candidates(candidates, limit=limit, min_score=min_score)
    for candidate in top_candidates:
        seen_ids.add(candidate.uid)
    save_seen(seen_ids)

    if not top_candidates:
        LOGGER.info("No candidates exceeded threshold", extra={"min_score": min_score})
        return

    message = compose_message(top_candidates)
    send_telegram(token, chat_id, message, preview=True)


def load_config(path: str = "queries.json") -> Dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run EventScout collector")
    parser.add_argument("--limit", type=int, default=6, help="Maximum number of events to send per cycle")
    parser.add_argument("--max-per-source", type=int, default=8, help="Maximum raw items per source")
    parser.add_argument("--min-score", type=float, default=5.5, help="Minimum score required to send an event")
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=15,
        help="Interval (in minutes) between cycles when running continuously",
    )
    parser.add_argument("--once", action="store_true", help="Run a single cycle and exit")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_logging(verbose=args.verbose)
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    ollama_model = os.getenv("OLLAMA_MODEL") or ""
    ollama_endpoint = os.getenv("OLLAMA_ENDPOINT") or ""

    if not all([token, chat_id]):
        raise SystemExit("Missing TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID")

    qconf = load_config()
    seen_ids = load_seen()
    LOGGER.info("Loaded %s seen ids", len(seen_ids))

    use_llm = bool(ollama_model and ollama_endpoint)
    LOGGER.info("LLM scoring enabled: %s", use_llm)

    cycles_run = 0
    while True:
        run_cycle(
            token=token,
            chat_id=chat_id,
            qconf=qconf,
            seen_ids=seen_ids,
            max_per_source=args.max_per_source,
            limit=args.limit,
            min_score=args.min_score,
            use_llm=use_llm,
            ollama_endpoint=ollama_endpoint,
            ollama_model=ollama_model,
        )
        cycles_run += 1
        if args.once:
            LOGGER.info("Single-cycle mode complete", extra={"cycles": cycles_run})
            break
        LOGGER.info(
            "Sleeping before next cycle",
            extra={"minutes": args.interval_minutes},
        )
        time.sleep(max(args.interval_minutes, 1) * 60)


if __name__ == "__main__":
    main()
