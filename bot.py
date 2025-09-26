import os, json, argparse, requests
from dotenv import load_dotenv
from sources.google_news import fetch_search
from sources.rss import fetch_rss
from sources.reddit import fetch_subreddit
from core.extract import extract_text_and_videos
from core.rank import final_score
from core.utils import load_seen, save_seen, hash_id, norm_text

def send_telegram(token: str, chat_id: str, text: str, preview: bool = True):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": not preview,
        "parse_mode": "HTML"
    }
    r = requests.post(url, json=payload, timeout=20)
    r.raise_for_status()

def collect_candidates(qconf: dict, max_per_source: int = 10):
    items = []
    # Google News keyword searches
    for q in qconf.get("google_news_queries", []):
        try:
            items += fetch_search(q, limit=max_per_source)
        except Exception:
            pass
    # RSS feeds
    for url in qconf.get("rss_feeds", []):
        try:
            items += fetch_rss(url, limit=max_per_source)
        except Exception:
            pass
    # Reddit
    for sub in qconf.get("subreddits", []):
        try:
            items += fetch_subreddit(sub, limit=8, t="day")
        except Exception:
            pass
    return items

def main(limit: int = 6):
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    ollama_model = os.getenv("OLLAMA_MODEL") or ""
    ollama_ep = os.getenv("OLLAMA_ENDPOINT") or ""

    if not all([token, chat_id]):
        raise SystemExit("Missing TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID")

    with open("queries.json", "r", encoding="utf-8") as f:
        Q = json.load(f)

    seen = load_seen()
    raw = collect_candidates(Q, max_per_source=8)

    # Enrich: extract text+videos, score
    cand = []
    for it in raw:
        uid = hash_id(it["link"])
        if uid in seen: 
            continue
        title = norm_text(it.get("title",""))
        try:
            text, direct_videos, platform_links = extract_text_and_videos(it["link"])
        except Exception:
            text, direct_videos, platform_links = "", [], []
        use_llm = bool(ollama_model and ollama_ep)
        score = final_score(title, text, use_llm, ollama_ep, ollama_model)
        cand.append({
            "uid": uid,
            "title": title,
            "link": it["link"],
            "score": round(score, 2),
            "videos": direct_videos,
            "platform_links": platform_links
        })

    cand.sort(key=lambda x: x["score"], reverse=True)
    pick = cand[:limit]
    for p in pick:
        seen.add(p["uid"])

    save_seen(seen)

    if not pick:
        send_telegram(token, chat_id, "לא נמצאו מועמדים טובים היום.")
        return

    # Send digest
    header = f"🎛️ EventScout — מועמדים לריפוסט ({len(pick)})"
    send_telegram(token, chat_id, header, preview=False)

    for i, p in enumerate(pick, 1):
        vids = "\n".join(p["videos"][:3]) if p["videos"] else "—"
        plats = "\n".join(p["platform_links"][:3]) if p["platform_links"] else "—"
        msg = (
            f"<b>{i}. {p['title']}</b>\n"
            f"ציון: {p['score']}\n"
            f"🔗 מקור: {p['link']}\n\n"
            f"🎬 וידאו ישיר: \n{vids}\n\n"
            f"📱 לינקים לפלטפורמות: \n{plats}"
        )
        send_telegram(token, chat_id, msg, preview=True)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=6)
    args = ap.parse_args()
    main(limit=args.limit)
