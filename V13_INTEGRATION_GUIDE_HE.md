# V13 — Resilience + Cost Control

## מה נוסף

### Idempotency
כל Build submission מקבל `Idempotency-Key`.
אותו key + אותו payload מחזיר את אותו resource.
אותו key + payload שונה נדחה.

### Worker Heartbeat
כל worker מעדכן heartbeat.
scheduler יכול לזהות worker מת ולסמן jobs לבדיקה/requeue לפי policy.

### Rollback
Deployment נשאר immutable.
Rollback בוחר deployment קודם ומבצע promotion חדש אליו.
אין overwrite של היסטוריה.

### Usage Caps
לפני משימה יקרה:
1. קוראים usage period.
2. מחשבים projected usage.
3. חוסמים אם עובר hard cap.
4. soft cap יכול רק להתריע.

### AI Model Router
לכל משימה אפשר להגדיר:
- minimum quality
- maximum latency
- prefer cost

כך לא משתמשים במודל הכי יקר לכל פעולה.
Architect/complex repair יכולים לקבל model חזק.
Classification/metadata/simple patch יכולים לקבל model זול ומהיר.

## יתרון עסקי
עלות AI הופכת למשתנה נשלט ולא ל"חור שחור".
המערכת יכולה לשמור margin פר משתמש/plan.
