import os, json, math, requests, re
from .utils import norm_text

KEYWORDS_CACHE = None

def load_keywords(path="queries.json"):
    global KEYWORDS_CACHE
    if KEYWORDS_CACHE is None:
        with open(path, "r", encoding="utf-8") as f:
            q = json.load(f)
        KEYWORDS_CACHE = {
            "he": set([s.lower() for s in q.get("keywords_he", [])]),
            "en": set([s.lower() for s in q.get("keywords_en", [])]),
            "cities": set([s.lower() for s in q.get("cities", [])])
        }
    return KEYWORDS_CACHE

def score_rule_based(title: str, text: str) -> float:
    K = load_keywords()
    t = f"{title} {text}".lower()
    score = 0.0
    # keyword hits
    for kw in K["he"]:
        if kw in t: score += 2.0
    for kw in K["en"]:
        if kw in t: score += 1.2
    # city hits
    for c in K["cities"]:
        if c in t: score += 1.0
    # freshness heuristic: prefer short posts and explicit dates
    if re.search(r"\b(היום|הלילה|tonight|today|this week|השבוע)\b", t):
        score += 1.5
    # penalties
    if len(text) < 120: score -= 0.5
    return score

def ollama_judge(title: str, text: str, ollama_endpoint: str, model: str) -> float:
    prompt = f"""
Evaluate if this is a high‑value post for Israeli party/festival followers.
Title: {title}
Text: {text[:1200]}
Return a single JSON with fields: score (0-10), reasons (short, Hebrew).
"""
    try:
        r = requests.post(f"{ollama_endpoint}/api/generate", json={
            "model": model,
            "prompt": prompt,
            "stream": False
        }, timeout=25)
        r.raise_for_status()
        out = r.json().get("response", "")
        import json as _json, re as _re
        m = _re.search(r"\{.*\}", out, _re.S)
        if m:
            js = _json.loads(m.group(0))
            return float(js.get("score", 0))
    except Exception:
        return 0.0
    return 0.0

def openrouter_judge(title: str, text: str) -> float:
    from .llm import openrouter_chat
    site_url = os.getenv("OPENROUTER_SITE_URL", "")
    app_title = os.getenv("OPENROUTER_APP_TITLE", "EventScout AI")
    prompt = f"""
הערך בפורמט JSON בלבד. דרג את התאמת התוכן לפוסט ריפוסט למסיבות/פסטיבלים בישראל.
החזר JSON עם: score (0-10), reasons (עברית קצרה), genre (מחרוזת), city (אם מזוהה).
Title: {title}
Text: {text[:1600]}
"""
    msg = [{"role": "system", "content": "אתה שופט קפדן. החזר JSON תקין בלבד."},
           {"role": "user", "content": prompt}]
    try:
        out = openrouter_chat(msg, site_url=site_url, app_title=app_title)
        import json as _json
        js = _json.loads(out.strip())
        s = float(js.get("score", 0))
        # clamp
        if s < 0: s = 0.0
        if s > 10: s = 10.0
        return s
    except Exception:
        return 0.0


def final_score(title: str, text: str, use_llm: bool, ollama_endpoint: str, model: str) -> float:
    rb = score_rule_based(title, text)
    if use_llm:
        llm = ollama_judge(title, text, ollama_endpoint, model)
        # blend
        return 0.6*rb + 0.4*(llm)
    return rb
