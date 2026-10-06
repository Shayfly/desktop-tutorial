# החלטות מייסד — 2026-10-07 (אחרי ה־Architecture Review)

מקור: הודעת המייסד מ־2026-10-07 01:35. מחייב יחד עם `OPERATING_CONTRACT_HE.md`.

1. **Product Orchestrator** — Owner לוגי יחיד לכל Build (לא בהכרח LLM, לא בהכרח process יחיד). כל שינוי מהותי: Orchestrator → Decision Layer → Economics Gate → Updated Plan → Execution.
2. **Decision Layer** מאושר: deterministic, versioned, auditable, replayable, explainable. כל החלטה משאירה Evidence: נבחר, חלופות, מחירים, Policy, Budget, איכות נדרשת, סיבה, החלופה הבאה.
3. בחירה **ברמת Task**; אין חובה למודל אחד או לכמה.
4. **Free Provider Lane**: FREE_CAPABLE → ECONOMY → QUALITY → PREMIUM. Free הוא Provider Metadata (quota, rate limits, privacy/data-use, availability, version, reliability, capabilities, metered cost) — הזדמנות, לא תלות. מועמדים לבדיקה: Groq, Cloudflare Workers AI, OpenRouter free pool, Gemini Free Tier.
5. המדד: **Cost per Verified Successful Outcome**.
6. **Cost Truth**: `metered_cost` (usage × catalog price בגרסה), `provider_reported_cost`, `reconciled_cost` (מקור אמת פיננסי). metered אינו Final Actual.
7. **Profitability**: שני תנאים. Target Contribution ≈70% על Expected, Hard Minimum Contribution ≈10–15% על Maximum — **Policy Parameters לפי Product Family/Budget Profile, לא קבועים**. לבחון בהמשך Expected/P95/P99/Hard Max.
8. **Golden E2E רץ על Internal QA / Staging Budget** עם Hard Cap מפורש — לא על Customer Free Tier. Free Tier ללקוחות ייקבע אחר כך (העדפה: one-time taste / micro-build, לא סבסוד חודשי).
9. **Telemetry עכשיו** — רשימת השדות לכל Attempt (מומש ב־migration 027).
10. Provider Intelligence — סטטי עכשיו; למידה אחרי מדגם. ספים (30 תצפיות, 5% exploration) הם Policy Parameters.
11. **Style & Identity System** במקום Creative Director Agent; LLM/Vision Judge רק לטעם/שיפוט.
12. Verification: Deterministic First; Acceptance מה־IR/Build Contract; Generator ≠ Reviewer כשנדרש.
13. Reuse של Verified Primitives למה שאינו מבדל; יצירה מחדש למה שמבדל. לא Template Builder.
14. **Failure Signature → Proven Fix** כנכס רשמי: קודם תיקון דטרמיניסטי מוכח, ורק אז AI Repair.
15. Caching content-addressed **עם Revocation** (מחיקת משתמש/פרויקט, revoke, legal takedown). Cache key כולל scope, input hash, model, prompt, policy, DNA ו־primitive versions.
16–18. **Golden E2E #1 הוא Priority #1.** מותר במקביל רק Instrumentation: Attempt Ledger, task tagging, cost truth, verification taxonomy, basic stop-loss, versions, routing evidence, traceability, Internal QA Budget.
19. החזון נשאר אוניברסלי; אסור לנעול ל־Request → One Model → Website.
22. החלטה ארכיטקטונית שמתגלה כשגויה — מציגים בעיה, Evidence, חלופה והשפעה, ומחליטים יחד. לא עוקפים בשקט.
