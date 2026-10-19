# PROVIDERS_INVENTORY — ספקי AI שהקוד פונה אליהם

נסרק מול `main` @ `1f744ae`, 2026-10-19. המסמך מצליב ארבעה מקורות:
1. `infra/worker-host/model-catalog.json`: מה שה-worker מנתב אליו בפועל.
2. `omni_prod/intelligence/inventory.py`: המלאי המנוהל של מודלים, כולל מצב חיבור ואימות.
3. `omni_prod/intelligence/prices.py`: לוח המחירים המרכזי (`price_at` / `require_price`).
4. חיפוש בקוד אחר משתני env ו-endpoints.

## מקרא

- **פעיל:** המודל מופיע ב-`model-catalog.json` ובמלאי הוא מסומן `CONNECTION_TESTED`.
  - ⚠ המצב `CREDENTIAL_PRESENT` הוא טענה סטטית שכתובה במלאי. היא לא נבדקה כאן מול ה-secrets.
- **רשומת מחיר:** `price_at(model)` מחזיר שורה.
- **המחיר מאומת:** `prices.py` מציין שכל שורה נקראה מעמוד התמחור הרשמי ב-`verified_at` (2026-10-11). **בסשן הזה המחירים של Google, ‏OpenAI ו-Anthropic לא נבדקו מחדש.**
- 🔴 **חור בתמחור:** אין רשומה בלוח המרכזי. `require_price` יחזיר `PriceMissing`, או שהעלות מחושבת ממקור אחר שלא מתעד היסטוריה.

## ספקים

| שם | משתנה סביבה | endpoint | האם פעיל | רשומת מחיר | המחיר מאומת |
|---|---|---|---|---|---|
| **Gemini** (Google) | `GEMINI_API_KEY` | `https://generativelanguage.googleapis.com/v1beta/openai` | **כן, 3 מודלים:** `gemini-3.8-flash`, ‏`gemini-3.1-flash-lite`, ‏`gemini-3.5-flash-lite` (`REAL_EXECUTION_VERIFIED`). 6 מודלים נוספים במלאי: `NOT_CONNECTED` | כן, לכל 9 | לפי הקוד, 2026-10-11. לא נבדק מחדש כאן |
| **OpenAI** | `OPENAI_API_KEY` | `https://api.openai.com/v1` | **מחובר, לא מאומת:** `gpt-6-luna`, ‏`gpt-6.1-sol` (`CONNECTION_TESTED`, ‏`UNVERIFIED`) | כן | לפי הקוד, 2026-10-11. לא נבדק מחדש כאן |
| **Anthropic** | `ANTHROPIC_API_KEY` | `https://api.anthropic.com/v1` | **מחובר, לא מאומת:** `claude-sonnet-5-5`. ‏`claude-haiku-5-5`: ‏`NOT_CONNECTED` | כן | לפי הקוד, 2026-10-11. לא נבדק מחדש כאן |
| 🔴 **Replicate** (תמונה) | `REPLICATE_API_TOKEN` | `https://api.replicate.com/v1` | **מחובר, לא מאומת:** `black-forest-labs/flux-schnell` (`CONNECTION_TESTED`) | 🔴 **אין בלוח המרכזי.** המחיר מגיע מ-env (`OMNI_IMAGE_PROVIDER_*_USD_PER_IMAGE`), עם ברירת מחדל של $0.003 לתמונה ב-`providers/replicate_connection.py:33-35` | מקור לפי הקוד: `replicate.com/pricing`, 2026-10-06. לא נבדק כאן |
| 🔴 **Groq** | `GROQ_API_KEY` (רק ב-`infra/worker-host/.env.example:30`) | אין | **לא.** אין ב-catalog, אין adapter ואין רשומה במלאי | 🔴 **אין** | — |
| **Venice** | `VENICE_API_KEY`: **לא קיים בקוד** | אין (`docs.venice.ai` כמקור מחיר בלבד) | **לא.** אין adapter | רק ב-PR #60, שעדיין לא מוזג: 8 מודלי Gemini דרך Venice, מסומנים "not connected" | נבדק ידנית 2026-10-19. צילום טקסט ב-#57, לא byte-exact |
| 🔴 **מודל מקומי** | `OMNI_LOCAL_MODEL_URL`, ‏`OMNI_LOCAL_MODEL_API_KEY`, ‏`OMNI_LOCAL_MODEL_ID` | ברירת מחדל `http://127.0.0.1:8001/v1` (`model_runtime_config.py:31`) | **לא.** במלאי: `NOT_CONNECTED`, ‏DEV_ONLY, ‏"unset on the worker" (`inventory.py:212`) | 🔴 **אין** | — |
| 🔴 **רשימת fallback ישנה** | `OMNI_EXTERNAL_MODELS_JSON` | כל endpoint שנכתב ב-JSON | **לא.** במלאי: `NOT_CONNECTED`, ‏deprecated (`inventory.py:214`) | 🔴 **אין.** ספקים שרירותיים, ומפתח גולמי בתוך ה-JSON | — |

## חורים בתמחור (🔴)

1. **Replicate: הוא מחובר, ואין לו רשומה בלוח המרכזי.** זה החור המשמעותי היחיד בין הספקים שמחוברים בפועל. העלות מחושבת דרך env, ולכן:
   - אין לה היסטוריה מתוארכת.
   - `price_at('black-forest-labs/flux-schnell')` מחזיר `None`.
   - ערך שגוי ב-env יעבור בשקט.
2. **Groq:** יש מפתח ב-`.env.example`, ואין שום דבר אחר. אם מישהו יחבר אותו, הוא יפעל בלי מחיר. **זה פער פוטנציאלי, לא פעיל.**
3. **מודל מקומי ו-`OMNI_EXTERNAL_MODELS_JSON`:** שני הנתיבים מסומנים כמנותקים. אם יופעלו, הם יפעלו בלי רשומת מחיר. הרשימה הישנה מקבלת כל ספק.

## הערות נוספות

- **המחירים ב-catalog תואמים ללוח המרכזי** בכל 6 המודלים (input ו-output). ל-catalog אין שדה מחיר cache, ולכן הערכות העלות של ה-worker גבוהות מהעלות בפועל. זו טעות לכיוון השמרני.
- **Claude דרך Venice לא ניתן לתמחור בלוח הנוכחי.** `price_at` מחפש לפי מזהה מודל בלבד, והמזהים של Claude ב-Venice זהים למזהים של `anthropic` (ראו #60).
- **מודלי media של Gemini** (תמונה, וידאו, TTS, ‏Lyria): יש להם רשומת מחיר, אבל אין adapter (`NOT_CONNECTED`).
