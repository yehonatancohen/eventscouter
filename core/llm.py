import os, json, requests

def openrouter_chat(messages, model=None, endpoint=None, api_key=None, site_url=None, app_title=None, timeout=30):
    model = model or os.getenv("OPENROUTER_MODEL", "google/gemma-2-9b-it:free")
    endpoint = endpoint or os.getenv("OPENROUTER_ENDPOINT", "https://openrouter.ai/api/v1/chat/completions")
    api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY missing")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    if site_url:
        headers["HTTP-Referer"] = site_url
    if app_title:
        headers["X-Title"] = app_title

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 300
    }
    r = requests.post(endpoint, headers=headers, json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        return ""
