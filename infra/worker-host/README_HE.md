# שרת הבנייה של 148AI (worker host)

השרת מריץ שני רכיבים:
- **worker**: מושך משימות בנייה מהתור ב־Redis ומבצע אותן.
- **sandbox-runner**: מריץ את הקוד שנוצר בתוך Docker מבודד, בלי גישה לרשת.

כל המידע נשמר בשירותים המנוהלים (Neon, Upstash, R2). השרת עצמו לא מחזיק שום מידע ייחודי, ואפשר למחוק אותו ולהקים מחדש בכל רגע.

אין חיבור נכנס חוץ מ־SSH. הפריסה נעשית דרך GitHub Actions שרץ על השרת עצמו (self-hosted runner, תווית `omni-worker`).

## הקמה חד־פעמית

1. **אסימון רישום ל־runner (בתוקף שעה אחת).** ב־GitHub: Settings ← Actions ← Runners ← New self-hosted runner ← Linux. מהשורה `./config.sh --url ... --token XXXX` מעתיקים רק את הערך של `--token`. לא שולחים אותו בצ'אט.
2. **יצירת השרת — Oracle Cloud Always Free (ההחלטה).**
   - Home region: **Germany Central (Frankfurt)**, קרוב ל־Neon, Upstash ו־R2. אי אפשר לשנות אותו אחרי ההרשמה.
   - Compute ← Instances ← Create instance:
     - Image: **Ubuntu 24.04**.
     - Shape: **VM.Standard.A1.Flex** (Ampere/arm64), עם 2 OCPU ו־12GB RAM. זה בתוך המכסה החינמית.
   - בעמוד היצירה, תחת Show advanced options ← Management ← **Cloud-init script**, מדביקים:
     ```
     #!/bin/bash
     export RUNNER_TOKEN=<האסימון מסעיף 1>
     ```
     ומיד אחר כך את כל התוכן של `bootstrap.sh`. הסקריפט תומך ב־arm64.
   - אם אין קיבולת A1 באזור (קורה לפעמים), החלופה היא Hetzner Cloud CX22 עם Ubuntu 24.04 ואותו cloud-init.
3. **מפתח Gemini.** ב־aistudio.google.com ← Get API key. המפתח נכנס **רק** לסוד `WORKER_ENV` בסעיף הבא, בשורה `GEMINI_API_KEY=`. לא שולחים אותו בצ'אט ולא שומרים אותו ב־Git.
4. **הסוד `WORKER_ENV` ב־GitHub.** ב־Settings ← Secrets and variables ← Actions ← New repository secret יוצרים סוד בשם `WORKER_ENV`.
   - התוכן הוא הקובץ `.env.example` אחרי מילוי הערכים.
   - הערכים זהים לאלה שמוגדרים ב־Vercel Preview, ובנוסף מפתח ספק ה־AI.
   - ערכי R2 (`OMNI_S3_*`) חייבים להיות אותם ערכים שעובדים ב־Preview. כדאי לבדוק אותם קודם ב־`/r2-diagnostics` (התחברות ב־Preview נדרשת).
5. **הפעלה.** ב־GitHub: Actions ← "Deploy build worker" ← Run workflow. הריצה:
   - בונה את ה־images.
   - מריצה את מיגרציות מסד הנתונים באופן אוטומטי (`python -m omni_prod.migrate`).
   - מפעילה את ה־worker.

   בסוף הלוג מופיע `Listening on omni-builds`.
6. **הרשאת QA לבדיקות (פעם אחת, אחרי סעיף 5).** ב־GitHub: Actions ← "Internal entitlement" ← Run workflow:
   - action = `grant`
   - email = כתובת החשבון ב־148AI
   - reason = `Golden E2E #1`

   ההרשאה נקשרת לחשבון, מתועדת, ואפשר לבטל אותה עם `revoke`. היא פעילה רק ב־staging.

## ניתוב בין מודלים

הקובץ `model-catalog.json` מכיל את רשימת המודלים, המחירים והאיכות של כל אחד.

לכל בקשה נבחר המודל **הזול ביותר** שעומד ברף האיכות `OMNI_MODEL_MIN_QUALITY`. אם הוא נכשל, הבקשה עוברת למודל הזול הבא.

מודל שהמפתח שלו לא מוגדר לא נבחר בכלל.

תקציב המודלים לבנייה נקבע ונשמר מראש ב־Vercel, לפני שהבנייה נכנסת לתור. ה־worker מוגבל אוטומטית לסכום שנשמר, גם אם ההגדרה בשרת גבוהה יותר.
