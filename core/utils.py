import os, json, re, hashlib, time, datetime, unicodedata

def norm_text(t: str) -> str:
    if not t: return ""
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def hash_id(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]

def load_seen(path="seen.json"):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_seen(ids, path="seen.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sorted(list(ids)), f, ensure_ascii=False)

def now_iso():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat("T")+"Z"
