# EventScout AI — ללא YouTube API
מאתר מקורות חינמיים (Google News RSS, RSS מותאם, Reddit JSON) → מוציא טקסט, מזהה לינקי וידאו/פלטפורמה → מדרג עם כללים או עם LLM מקומי (Ollama) → שולח בטלגרם.

## למה זה חינמי
- ללא YouTube API. 
- Google News RSS ו-RSS פתוח. 
- Reddit JSON ציבורי (עלול להגביל קצב; הכי טוב לשמור על מעט בקשות). 
- אופציונלית: LLM מקומי דרך [Ollama](https://ollama.com) — חינם מקומית.

## התקנה
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # מלא טלגרם, ואופציונלית OLLAMA_*
```
`.env`:
```
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
# אופציונלי:
OLLAMA_MODEL=llama3.1:8b
OLLAMA_ENDPOINT=http://localhost:11434
```

## קונפיגורציה
ערוך `queries.json`:
- `google_news_queries`: מחרוזות חיפוש (נבנה RSS אוטומטי).
- `rss_feeds`: פידים ישירים של אתרי אירועים/הפקות.
- `subreddits`: מקורות EDM/פסטיבלים.
- `keywords_*` + `cities`: מילים לשיקלול ציון.

## ריצה
```bash
python bot.py --limit 6
```
ישלח דוח לטלגרם: כותרת, לינק מקור, ציון, ואם נמצאו — קישורי וידאו ישירים (`.mp4/.webm`) ולינקים לפלטפורמות (TikTok/IG/Reddit).

## איך זה מחליט "כדאי/לא"
- ציון כללים: התאמות למילות מפתח + עיר + "היום/הלילה/השבוע" + איכות טקסט.
- אם אקטיבי OLLAMA_*: משלב ציון LLM (0–10) עם הציון הכללי (60/40).

## איתור וידאו
- מחפש `<video>`/`source`/`og:video` בעמודים.
- אוסף לינקים לפלטפורמות (TikTok/IG/Facebook/Reddit). נועד לריפוסט דרך הפלטפורמה עצמה (כפוף לתנאים).

## הפעלה יומית (cron 09:00)
```cron
0 9 * * * cd /path/to/event_scout_ai && . .venv/bin/activate && python bot.py --limit 6
```

## הרחבות
- הוספת מקורות: Telegram Channels (Telethon), בלוגים, אתרי מועדונים.
- ניקוד לפי גיל יעד (נוער/18+), ז׳אנר, עיר.
- שמירת ארכיון JSON + דשבורד קליקי יציאה.

## הערות משפטיות
- כבד מדיניות ואת תנאי השימוש של אתרים. לריפוסט וידאו מומלץ להשתמש ביכולות Remix/Stitch בפלטפורמה המקורית או לקבל אישור מבעלי הזכויות.


## שימוש ב-OpenRouter (AI חינמי)
מלא ב-`.env`:
```
OPENROUTER_API_KEY=or_...
OPENROUTER_MODEL=google/gemma-2-9b-it:free   # או mistralai/mistral-7b-instruct:free
OPENROUTER_ENDPOINT=https://openrouter.ai/api/v1/chat/completions
OPENROUTER_SITE_URL=https://parties247-website.vercel.app
OPENROUTER_APP_TITLE=EventScout AI
```
כאשר קיים `OPENROUTER_API_KEY`, הבוט ייתן ציון AI דרך OpenRouter במקום Ollama.
