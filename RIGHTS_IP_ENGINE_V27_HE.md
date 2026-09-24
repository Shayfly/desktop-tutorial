# Omni Creator V27 — Rights & IP Engine

## מטרה
המנוע נועד למנוע מצב שבו Omni מייצרת ומפרסמת מוצר עם שימוש לא פתור בזכויות של צד שלישי.
הוא אינו תחליף לייעוץ משפטי או לחיפוש clearance רשמי. הוא שכבת triage, provenance ו-publish gate.

## מה נסרק
- זכויות יוצרים
- סימני מסחר / trade dress
- שם, דמות, likeness וזהות של אדם
- קול / digital replica
- זכויות מבצעים
- יצירה מוזיקלית / מילים / לחן
- master / sound recording
- עיצוב
- רישיונות דאטה ונכסים

## התנהגות
1. כל Build מקבל `rights/rights-manifest.json`.
2. בקשה מפורשת לשימוש מסוכן בצד שלישי מסומנת `LEGAL_REVIEW_REQUIRED`.
3. אפשר להמשיך לעבוד על הפרויקט, אבל Promote/Publish נחסם כברירת מחדל.
4. המשתמש יכול לצרף evidence: רישיון, הסכמה, מקור ו-scope. העלאה עצמית אינה מסומנת אוטומטית כמאומתת.
5. רק Legal/IP Reviewer מורשה של הפלטפורמה יכול להעביר evidence ל-verified; רק evidence מאומת שמתאים לסוג הזכות ול-subject יכול לפתור finding.
6. לחלופין ניתן להפעיל `Original Alternative`: Omni מסירה identifiers של צד שלישי ומשאירה רק mechanics / genre / requirements כלליים ליצירה מקורית חדשה.
7. Original Alternative אינו "שינוי באחוזים" ואינו safe-harbor משפטי.

## Jurisdiction profiles ראשוניים
- US — copyright, trademark, digital replica / likeness risk baseline.
- EU — כולל transparency analysis ל-AI-generated/manipulated deepfake content לפי Article 50 כאשר רלוונטי.
- IL — copyright, trademarks, performers/broadcasters rights, privacy/personality risk baseline.

הפרופילים הם baseline מתוחזק. אין טענה שהם מכסים כל חוק, חריג, פסיקה או מדינה בעולם.

## מקורות רשמיים שנשמרים בפרופילים
- USPTO — Likelihood of Confusion
- U.S. Copyright Office — Copyright and Artificial Intelligence / Digital Replicas
- EUR-Lex — Regulation (EU) 2024/1689 Article 50
- WIPO Lex — Israel Copyright Act 2007
- WIPO Lex — Israel Performers' and Broadcasters' Rights Law 5744-1984
- WIPO Lex — Israel Protection of Privacy Law 5741-1981

## עקרון מוצר
Omni לא מנסה "לעקוף זכויות" על ידי שינוי קטן. היא עושה אחת משלוש פעולות:
- Original — יצירה מקורית.
- Licensed/Consented — evidence מתועד ומאומת.
- Review Required — עצירת publish עד בדיקה.
