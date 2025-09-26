"""Scoring heuristics for EventScout."""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Dict

import requests

LOGGER = logging.getLogger(__name__)
KEYWORDS_CACHE: Dict[str, set[str]] | None = None


def load_keywords(path: str = "queries.json") -> Dict[str, set[str]]:
    global KEYWORDS_CACHE
    if KEYWORDS_CACHE is None:
        with open(path, "r", encoding="utf-8") as handle:
            config = json.load(handle)
        KEYWORDS_CACHE = {
            "he": {s.lower() for s in config.get("keywords_he", [])},
            "en": {s.lower() for s in config.get("keywords_en", [])},
            "artists": {s.lower() for s in config.get("artist_keywords", [])},
            "viral": {s.lower() for s in config.get("viral_cues", [])},
            "cities": {s.lower() for s in config.get("cities", [])},
        }
        LOGGER.debug("Loaded keyword configuration", extra={"counts": {k: len(v) for k, v in KEYWORDS_CACHE.items()}})
    return KEYWORDS_CACHE


def score_rule_based(title: str, text: str) -> float:
    keywords = load_keywords()
    combined = f"{title} {text}".lower()
    score = 0.0

    hits_he = sum(1 for kw in keywords["he"] if kw in combined)
    hits_en = sum(1 for kw in keywords["en"] if kw in combined)
    hits_city = sum(1 for city in keywords["cities"] if city in combined)
    hits_artist = sum(1 for artist in keywords["artists"] if artist in combined)
    hits_viral = sum(1 for clue in keywords["viral"] if clue in combined)

    if hits_he == 0 and hits_en == 0:
        score -= 3.0
    else:
        score += hits_he * 2.0
        score += hits_en * 1.4

    score += hits_city * 1.2
    score += hits_artist * 2.5
    score += hits_viral * 1.5

    if re.search(r"\b(today|tonight|this week|tomorrow|היום|הלילה|השבוע|מחר)\b", combined):
        score += 1.8

    if len(text) < 120:
        score -= 0.8

    if re.search(r"\b(pre\s?sale|tickets? on sale)\b", combined):
        score += 0.8

    if re.search(r"\b(news|politics|finance)\b", combined):
        score -= 1.0

    LOGGER.debug(
        "Rule-based score computed",
        extra={
            "title": title[:80],
            "score": score,
            "hits_he": hits_he,
            "hits_en": hits_en,
            "hits_city": hits_city,
            "hits_artist": hits_artist,
            "hits_viral": hits_viral,
        },
    )
    return score


def ollama_judge(title: str, text: str, ollama_endpoint: str, model: str) -> float:
    prompt = f"""
Evaluate if this announcement is a high-value post for Israeli party/festival followers.
Return a JSON object with: score (0-10) and reasons (short, English).
Title: {title}
Text: {text[:1200]}
"""
    try:
        response = requests.post(
            f"{ollama_endpoint}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=25,
        )
        response.raise_for_status()
        payload = response.json().get("response", "")
        import json as _json
        import re as _re

        match = _re.search(r"\{.*\}", payload, _re.S)
        if match:
            parsed = _json.loads(match.group(0))
            return float(parsed.get("score", 0))
    except Exception:
        LOGGER.exception("Ollama judge failed", extra={"model": model})
        return 0.0
    return 0.0


def openrouter_judge(title: str, text: str) -> float:
    from .llm import openrouter_chat

    site_url = os.getenv("OPENROUTER_SITE_URL", "")
    app_title = os.getenv("OPENROUTER_APP_TITLE", "EventScout AI")
    prompt = f"""
Return a valid JSON object. Evaluate how suitable this content is for a repost about parties or festivals in Israel.
Return JSON with: score (0-10), reasons (concise English), genre (string), city (if detected).
Title: {title}
Text: {text[:1600]}
"""
    message = [
        {"role": "system", "content": "You are a strict judge. Return valid JSON only."},
        {"role": "user", "content": prompt},
    ]
    try:
        output = openrouter_chat(message, site_url=site_url, app_title=app_title)
        import json as _json

        parsed = _json.loads(output.strip())
        score = float(parsed.get("score", 0))
        if score < 0:
            score = 0.0
        if score > 10:
            score = 10.0
        return score
    except Exception:
        LOGGER.exception("OpenRouter judge failed")
        return 0.0


def final_score(title: str, text: str, use_llm: bool, ollama_endpoint: str, model: str) -> float:
    rule_based = score_rule_based(title, text)
    if use_llm:
        llm_score = ollama_judge(title, text, ollama_endpoint, model)
        final = 0.6 * rule_based + 0.4 * llm_score
        LOGGER.debug(
            "Combined score",
            extra={"rule_based": rule_based, "llm": llm_score, "final": final},
        )
        return final
    LOGGER.debug("Rule-based only score", extra={"score": rule_based})
    return rule_based
