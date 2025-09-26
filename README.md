# EventScout AI — No YouTube API Needed

EventScout monitors free data sources (Google News RSS, curated RSS feeds, Reddit JSON) → extracts article text and videos → ranks candidates with heuristics or an optional LLM → sends the best leads to Telegram.

## Why it is free
- No YouTube API.
- Google News RSS and open RSS feeds.
- Public Reddit JSON (mind the rate limits).
- Optional: local LLM via [Ollama](https://ollama.com).

## Installation
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Fill in Telegram and optional OLLAMA_* values
```
`.env`:
```bash
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
# Optional local LLM:
OLLAMA_MODEL=llama3.1:8b
OLLAMA_ENDPOINT=http://localhost:11434
```

## Configuration
Edit `queries.json`:
- `google_news_queries`: search strings (the tool builds RSS URLs automatically).
- `social_video_queries`: Google News RSS searches that focus on TikTok/Instagram/Facebook clips.
- `rss_feeds`: direct feeds for event or production sites.
- `subreddits`: EDM/festival sources.
- `keywords_*` + `cities`: keywords for scoring.

## Run the bot
```bash
python bot.py --limit 6
```
By default the bot loops forever, waking up every 15 minutes. Use `--interval-minutes` to change the cadence or `--once` to run a single cycle. The Telegram message now includes a curated digest plus a "Suggested social upload" block with a highlighted clip and two catchy headline ideas.
The default minimum score is 5.5—raise or lower it via `--min-score` depending on how picky you want the feed to be.

## How it decides what is "good"
- Rule-based score: matches for keywords, city mentions, date/time hints, ticket information, and text length, plus boosts for viral video terms and celebrity party context.
- Optional LLM score through Ollama. Final score is a 60/40 blend of rule-based and AI judging.
- Events below the minimum score are dropped.

## Video detection
- Scans `<video>`/`source`/`og:video` tags.
- Captures platform links (TikTok/IG/Facebook/Reddit) for native reposting.

## Run on a schedule (every 4 hours)
```cron
0 */4 * * * cd /path/to/eventscout && . .venv/bin/activate && python bot.py --limit 6 --interval-minutes 240
```
Because the bot already loops continuously, cron is optional—useful only if you prefer process supervision outside the script.

## Optional OpenRouter (free tier)
Add to `.env`:
```bash
OPENROUTER_API_KEY=or_...
OPENROUTER_MODEL=google/gemma-2-9b-it:free
OPENROUTER_ENDPOINT=https://openrouter.ai/api/v1/chat/completions
OPENROUTER_SITE_URL=https://parties247-website.vercel.app
OPENROUTER_APP_TITLE=EventScout AI
```
When `OPENROUTER_API_KEY` is set, the bot uses OpenRouter for the AI score instead of Ollama.
