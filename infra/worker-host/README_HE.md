# שרת הבנייה של 148AI (worker host)

השרת מריץ שני רכיבים:
- **worker**: מושך משימות בנייה מהתור ב־Redis ומבצע אותן.
- **sandbox-runner**: מריץ את הקוד שנוצר בתוך Docker מבודד, בלי גישה לרשת.

כל המידע נשמר בשירותים המנוהלים (Neon, Upstash, R2). השרת עצמו לא מחזיק שום מידע ייחודי, ואפשר למחוק אותו ולהקים מחדש בכל רגע.

אין חיבור נכנס חוץ מ־SSH. הפריסה נעשית דרך GitHub Actions שרץ על השרת עצמו (self-hosted runner, תווית `omni-worker`).

## הקמה חד־פעמית

1. **אסימון רישום ל־runner (בתוקף שעה אחת).** ב־GitHub: Settings ← Actions ← Runners ← New self-hosted runner ← Linux. מהשורה `./config.sh --url ... --token XXXX` מעתיקים רק את הערך של `--token`.
2. **יצירת השרת ב־Hetzner Cloud.**
   - Ubuntu 24.04
   - CX22 (2 vCPU, 4GB) או הדגם הזול הקרוב
   - מיקום: Falkenstein או Nuremberg, קרוב לפרנקפורט, איפה שנמצאים Neon, Upstash ו־R2
   - בשדה **Cloud config** מדביקים:
     ```
     #!/bin/bash
     export RUNNER_TOKEN=<האסימון מסעיף 1>
     ```
     ומיד אחר כך את כל התוכן של `bootstrap.sh`.
3. **הסוד `WORKER_ENV` ב־GitHub.** ב־Settings ← Secrets and variables ← Actions ← New repository secret יוצרים סוד בשם `WORKER_ENV`. התוכן שלו הוא הקובץ `.env.example` אחרי מילוי הערכים. הערכים זהים לאלה שמוגדרים ב־Vercel Preview, ובנוסף מפתח ספק ה־AI.
4. **הפעלה.** ב־GitHub: Actions ← "Deploy build worker" ← Run workflow. בסוף הריצה הלוג מציג `Listening on omni-builds`.

## ניתוב בין מודלים

הקובץ `model-catalog.json` מכיל את רשימת המודלים, המחירים והאיכות של כל אחד.

לכל בקשה נבחר המודל **הזול ביותר** שעומד ברף האיכות `OMNI_MODEL_MIN_QUALITY`. אם הוא נכשל, הבקשה עוברת למודל הזול הבא.

מודל שהמפתח שלו לא מוגדר לא נבחר בכלל.

התקציב לבנייה אחת (`OMNI_EXTERNAL_BUDGET_USD`) נשמר מראש, לפני שהבנייה נכנסת לתור, ושום קריאה לא חורגת ממנו.
