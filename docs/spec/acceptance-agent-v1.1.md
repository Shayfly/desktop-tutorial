# מפרט סוכן הקבלה — v1.1

## 0. שני ערוצים — החוק שמאחד הכל
- **תוכן** (עובדות: טלפון, כתובת, שעות, ביקורות, שירותים, שם) → **טקסט חופשי.** ככה לקוחות כותבים.
- **החלטות** (סוג מוצר, שמירת נתונים, התחברות, פרטים אישיים) → **כפתורים בלבד.**

**אסור כפתור לעובדה. אסור טקסט חופשי להחלטה.** זו התקלה של זרוע 1: ארבע פעמים המודל ניחש החלטה בביטחון גבוה, ואיש לא שאל בכפתור.

## 1. אובייקט ההחלטות
```ts
type Conf = "stated" | "inferred" | "missing";
interface Field<T> { v: T | null; conf: Conf; src: "customer" | "rawBrief" | "library" }

type ArtifactKind = "site" | "landing" | "app" | "saas" | "game" | "song" | "video" | "agent" | "combo";

interface ArtifactIntent {
  id: ArtifactId;
  kind: Field<ArtifactKind>;              // כפתור בלבד
  purpose: Field<string>;                 // חופשי
  audience: Field<string>;                // חופשי
  mustInclude: Field<string[]>;           // חופשי
  persistence: Field<"none" | "records">; // כפתור בלבד
  game?: { genre: Field<GameGenre>; players: Field<1|2|4|"online"> };
  song?: { style: Field<string>; seconds: Field<number>; use: Field<"bg"|"intro"|"ad"> };
  saas?: { payer: Field<string>; billing: Field<"subscription"|"oneoff"> };
  agent?: { skills: Field<SkillId[]>; runtime: Field<string> };
}

interface IntakeDecision {
  v: 1; locale: "he-IL";
  rawBrief: string;                        // IMMUTABLE. הערוץ שהלקוח לא יכול לזייף
  artifacts: ArtifactIntent[];             // ≥1
  shared: { tone: Field<string>; brandName: Field<string>; businessFacts: Fact[] };
  gaps: Gap[]; turns: number; mode: "menu" | "free";
}
```

**`rawBrief` חסום לשינוי** וכל הרמזים, השלילות והקנון נקראים ממנו — לא מהבריף שהמערכת כתבה.

## 2. ערוץ התוכן
פסקה חופשית נכנסת כ-`rawBrief`, וממנה נגזרים עובדות וקנון. הסוג מוסק ממנה ונכתב `inferred` עד לאישור בכפתור.

## 3. ערוץ ההחלטות — הכרטיס
תפריט בשתי מדרגות: **זמין עכשיו** (אתר, דף נחיתה) / **בקרוב** (השאר). בחירה לא-זמינה: הודעה, לכידת מייל, הצעת הקרוב הזמין.

הכרטיס מציג כל החלטה כשורות כפתורים, כשהמומלץ **מסומן מראש**. אין תוויות ביטחון — הסימון הוא הביטחון.

## 4. התכנסות
שני הערוצים מייצרים את אותו `IntakeDecision`. ארכיטקט לא מבחין במקור.

## 5. תקציב שאלות — נמדד, לא מומצא
אין תקרת תורות. `askedCount` פר פער, ו-`systemAskedDecisions` בדוח. **הסף נקבע אחרי ריצה אחת עם R1 ו-R2**, לא לפני.

## 6. פער
```ts
interface Gap {
  field: string;
  blocks: "build" | "approval" | "nothing";
  resolver: "customer" | "system";
  options: string[];
  askedCount: number;
  trigger: "missing" | "stale" | "conflict";
}
```
חומרה נגזרת מ-`blocks`. `askedCount ≥ 2` = תקלה.

## 7. הצעה
מופעל ב"לא יודע" או `missing`. 3 דוגמאות קונקרטיות מהספרייה. אין התאמה → 3 הקרובות עם הסבר. אין מופשט.

## 8. ריבוי פריטים
אחרי כרטיס ראשון: "להוסיף עוד?". `shared` נגזר פעם אחת. כאן מתחיל "עולם ולא דף".

## 9. שינוי סוג
שדות בלתי-תלויים נשמרים. תלויי-סוג נמחקים ומסומנים `missing`. אין איפוס.

## 10. מסירה
רק כשאין `Gap` עם `blocks: build`.

## 11. כשל
`SCHEMA` עצור · `EXTRACT_BAD` ניסיון אחד ואז כפתור · `MODEL_HICCUP` retry ×2 · `AMBIGUOUS_KIND` תפריט · `OUT_OF_SCOPE` סירוב + רשימת המתנה + חלופה (למחזר את הקיים).

## 12. אסור
להסיק סוג בלי אישור · להסתיר חוסר זמינות · לשאול מה שב-`rawBrief` · לכתוב פרוזה להחלטה · כפתור לעובדה · להתחיל בנייה · להבטיח תאריך · ז'רגון באנגלית · יותר מ-3 הצעות.

## 13. קבלה
```
T1 פסקה על פרחים → kind inferred, ≤2 gaps
T2 בחירת אתר → kind stated, כרטיס בתור אחד
T3 בחירת משחק → הודעה + מייל + הצעה
T4 "לא יודע" → 3 קונקרטיות
T5 שינוי site→app → purpose נשמר, persistence missing
T6 "אתר עם שיר" → 2 פריטים, shared אחד
T7 כל שדה נושא conf
T8 אין שאלת החלטה בטקסט חופשי
T9 אין כפתור לעובדה
T10 סירוב נקי על iOS נייטיב
```

## 14. סדר
1. סכמה + ולידטור (סקיצה, חתימה, קוד)
2. תפריט + זמינות + רשימת המתנה
3. ענף site
4. חילוץ תוכן
5. מנוע הצעה
6. ריבוי פריטים
7. שאר הענפים

## 15. 409
`retryable: true`, תיעוד, וחיבור לכרטיס ב-PR של §3. `database` ב-PR נפרד.
