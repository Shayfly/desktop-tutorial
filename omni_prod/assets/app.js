'use strict';
/* 148AI creator workspace (M5-UX01).
   Uses only existing V28 endpoints plus the plan step
   (POST /api/v28/projects/{id}/build-contracts). Never shows a preview,
   publish result or cost that the backend did not report. */

const T = {
  he: {
    skip:'דילוג לתוכן', projects:'פרויקטים', manage:'ניהול', logout:'התנתקות',
    hero:'תארו את אפליקציית הווב שלכם.', lead:'148AI מתכננת, בונה, בודקת ומציגה אותה.',
    how1:'כותבים מה האפליקציה צריכה לעשות ולמי.', how2:'מקבלים תוכנית ועלות מקסימלית, ומאשרים.',
    how3:'צופים בבנייה, בודקים בתצוגה מקדימה, משנים ומורידים את הקוד.',
    scope:'כרגע: אפליקציות ווב ו-SaaS. מובייל, משחקים ומדיה עוד לא זמינים.',
    signinTitle:'כניסה לחשבון', email:'אימייל', password:'סיסמה', passwordHint:'לפחות 10 תווים.', showPassword:'הצגת סיסמה', hidePassword:'הסתרת סיסמה',
    login:'כניסה', register:'יצירת חשבון חינם',
    firstProject:'הפרויקט הראשון שלכם', projectName:'שם הפרויקט', createProject:'יצירת פרויקט',
    request:'מה תרצו לבנות?', build:'המשך', planHint:'שום בנייה ושום חיוב לא מתחילים לפני שתאשרו סיכום ועלות.',
    modeLegend:'איך תרצו להמשיך?', modeGuided:'שיחה מודרכת', modeGuidedHint:'נשאל כמה שאלות קצרות — גם על צבעים, גופן וסגנון. אפשר לענות "אין לי העדפה".',
    modeRecommend:'המערכת תמליץ ותבחר', modeRecommendHint:'נבחר עבורכם לפי מה שכתבתם, ותראו הכול בסיכום לפני אישור.',
    discTitle:'בואו נדייק את הבקשה', discProgress:(a, r) => `${a} החלטות · נשארו ${r}`, why:'למה שואלים: ',
    delegate:'אין לי העדפה — בחרו עבורי', delegateWill:v => `(נבחר: ${v})`, suggestedFromRequest:'(לפי מה שכתבתם)',
    next:'המשך', skipGroup:'דלגו על השאלות האלה', pauseNote:'הכול נשמר. אפשר לחזור ולהמשיך גם אחרי רענון או ממכשיר אחר.',
    decided:'מה כבר החלטנו', change:'שינוי', save:'שמירה', cancel:'ביטול', needAnswer:q => `צריך תשובה ל: ${q}`,
    discDone:'סיימנו. זה הסיכום — בדקו אותו לפני אישור.', showSummary:'הצגת הסיכום והעלות',
    src_message:'מהבקשה שלכם', src_answer:'התשובה שלכם', src_delegated:'נבחר עבורכם', src_default:'ברירת מחדל',
    sumGoal:'המטרה', sumIncluded:'כלול', sumExcluded:'לא כלול בשלב זה', semanticTitle:'כך פירשנו את הבקשה', semanticIncluded:'נדרש במוצר', semanticExcluded:'לא התבקש', semanticUncertain:'צריך הבהרה', sumAssumptions:'החלטות שבחרנו עבורכם (אפשר לשנות)',
    updateRequest:'עדכן את הבקשה', approveBuild:'לאשר ולהתחיל לבנות', approvalExpired:'האישור פג. בדקו את הסיכום ואשרו שוב.',
    builtTitle:'מה נבנה עד עכשיו', newBuild:'מוצר חדש בפרויקט חדש', newProjectPlus:'+ פרויקט חדש', newProjectHint:'לכל מוצר פרויקט משלו. תנו לו שם, ואז תתארו מה לבנות.', nameRequired:'צריך לתת לפרויקט שם.', builtVersion:'גרסה נוכחית', files:'קבצים',
    progress:'התקדמות הבנייה', modifyTitle:'מה תרצו לשנות?', modifySend:'שליחת שינוי', versions:'גרסאות',
    evidence:'פרטים טכניים ועדויות', refresh:'רענון', openTab:'פתיחה בלשונית חדשה',
    noPreview:'כאן תופיע האפליקציה אחרי שהבנייה תסתיים.', download:'הורדת קוד המקור (ZIP)', publish:'פרסום',
    publishNotConfigured:'העלאה לאוויר עוד לא זמינה. אפשר להוריד את הקוד ולבדוק בתצוגה המקדימה.',
    manageProject:'ניהול פרויקט', rename:'שינוי שם', saveName:'שמירת השם', archive:'העברה לארכיון',
    newProject:'פרויקט חדש', close:'סגירה',
    promptPlaceholder:'לדוגמה: מערכת לניהול תורים למספרה, עם יומן לספרים, הזמנה עצמית ללקוחות ותזכורות במייל.',
    propTitle:'ההצעה שלכם', propLooks:'ככה זה ייראה', propGeneric:'הצעה כללית', propEstimate:'הערכה', propPrice:'מחיר לבנייה', propIncluded:'כלול', propExcluded:'לא כלול', propFacts:'הפרטים שלכם, כמו שכתבתם', propApprove:'לאשר ולהתחיל לבנות', propChange:'שנה משהו', propEdit:'שנה', propUp:'הזז למעלה', propDown:'הזז למטה', propRemove:'הסר', propSave:'שמור', propUndo:'בטל את השינוי האחרון', propApproving:'מאשרים ומתחילים לבנות…', propNotYet:'ההצעה עוד לא מוכנה: נשלים את הפרטים בשיחה.',
    planTitle:'התוכנית', understood:'מה הבנו', roles:'משתמשים', data:'נתונים', integrations:'חיבורים',
    capabilities:'יכולות שהבנייה צריכה', infrastructure:'מה שהאפליקציה צריכה', cost:'עלות',
    estimated:'הערכה', maximum:'מקסימום מאושר', questions:'שאלות לפני שמתחילים', blockersTitle:'מה חוסם כרגע',
    creditsRequired:'מחיר הבנייה (יורד מהיתרה שלכם)', creditsRemaining:'היתרה שלכם', quoteStatus:'המחיר',
    confirm:'לאשר ולהתחיל לבנות', editRequest:'עריכת הבקשה', costUnknown:'לא ניתן לחשב',
    byPipeline:'בתוך הבנייה', byProvider:'שירות חיצוני', required:'נדרש', optional:'רשות',
    st_LIVE:'פעיל', st_PARTIAL:'מוגדר, לא נבדק', st_NOT_CONFIGURED:'לא מוגדר', st_BLOCKED:'חסום',
    st_SELF_CONTAINED:'מובנה באפליקציה', st_PRICED:'מאושר', st_UNKNOWN:'עוד אין מחיר', st_NOT_AUTHORIZED:'לא מאושר',
    stepPlanning:'תכנון', stepContract:'חוזה בנייה', stepInfra:'בסיס', stepAssets:'נכסים (אייקון ותמונות)',
    stepGenerate:'יצירת קוד, בנייה, בדיקות ותיקונים', stepGates:'בדיקות איכות, אבטחה וזכויות', stepPreview:'תצוגה מקדימה',
    noteGenerate:'הבנייה, הבדיקות והתיקונים רצים בשלב אחד. מספר סבבי התיקון מדווח בסיום.',
    repairs:n=>`סבבי תיקון: ${n}`, queued:'ממתין בתור', queuedNext:'ממתין בתור: הבנייה שלך הבאה בתור', queuedAhead:n=>`ממתין בתור: ${n === 1 ? 'עבודה אחת' : n + ' עבודות'} לפני הבנייה שלך`, started:'הבנייה התחילה', buildReady:'הבנייה הסתיימה בהצלחה.',
    buildFailed:'הבנייה נכשלה',
    openDraftPreview:'פתח את הטיוטה בתצוגה (לא עברה את כל הבדיקות)',
    stopBuild:'עצירת הבנייה', stopChange:'עצירת השינוי', stopChangeConfirm:'לעצור את השינוי? נחויב רק על מה שכבר נוצל.', modCancelled:'השינוי נעצר.', stopConfirm:'לעצור את הבנייה? נחויב רק על מה שכבר נוצל, והגרסה לא תיווצר.',
    stopping:'העצירה תתבצע בסיום הצעד הנוכחי (עד כמה דקות).', buildCancelled:'הבנייה נעצרה. נחויב רק על מה שכבר נוצל.',
    liveLog:'מה קורה עכשיו', logEmpty:'מתכוננים לבנייה…', logNoBuild:'אין בנייה עדיין בפרויקט הזה.',
    checkingApproval:'מאמתים אישור ותקציב — הבנייה עדיין לא התחילה.',
    uiEmpty:'האתר שנבנה יצא ריק', uiMissing:{form:'טופס', input:'שדות קלט', button:'כפתור', table:'טבלה', content:'תוכן'}, uiMissingLead:'חסרים בו', uiEmptyTail:'אז לא מסרנו אותו.',
    errCodes:{preview_no_build_queue:'בגרסת הבדיקה הזו של 148AI אי אפשר לבנות, ולכן הבנייה לא התחילה.', build_not_found:'הבנייה לא התחילה בגלל תקלה אצלנו.', verification_failed:'לא הצלחנו לבנות את האתר הפעם.',
      needs_customer_input:'חסר פרט שרק אתם יכולים לתת, ולכן עצרנו את הבנייה. לא נמציא אותו.',
      release_policy_failed:'בנינו את האתר, אבל הוא לא עבר את הבדיקות שלנו, אז לא מסרנו אותו.',
      quality_gate_failed:'האתר נבנה אבל לא יצא מספיק טוב, אז לא מסרנו אותו.',
      preview_not_ready:'בנינו את האתר, אבל הוא לא נפתח כשניסינו אותו, אז לא מסרנו אותו.',
      security_gate_failed:'מצאנו באתר שנבנה בעיה שעלולה לסכן את המידע של המבקרים בו, אז לא מסרנו אותו.',
      rights_gate_not_clear:'האתר נבנה ונשמר, אבל לא הצלחנו לוודא שמותר להשתמש בכל מה שיש בו (למשל תמונה או שם), ולכן הוא עוד לא מוכן.',
      unsupported_dependency:'האתר שביקשתם צריך משהו שאנחנו עוד לא יודעים לבנות.',
      worker_lost:'הבנייה נתקעה ועצרנו אותה.',
      build_timeout:'הבנייה נמשכה יותר מדי זמן ועצרנו אותה לפני שהסתיימה.',
      provider_liability_unknown:'הבנייה נעצרה באמצע. עוד לא ידוע אם חויבתם על מה שכבר נעשה.',
      worker_exception:'משהו השתבש אצלנו בזמן הבנייה. זה לא בגללכם.',
      model_budget_exhausted:'הבקשה גדולה מדי לבנייה אחת, והבנייה נעצרה לפני שהסתיימה.',
      model_unavailable:'יש עומס אצלנו כרגע, והבנייה לא הושלמה. כדאי לחכות כמה דקות.',
      provider_quota_exhausted:'יש עומס אצלנו כרגע, והבנייה לא הושלמה. כדאי לחכות כמה דקות.',
      model_policy_blocked:'משהו השתבש אצלנו בזמן הבנייה. זה לא בגללכם.',
      capability_gate_failed:'חלק מהאתר (למשל התמונות) לא הצלחנו להכין, אז לא מסרנו אותו.',
      image_mismatch:'התמונה שנוצרה לא מראה את מה שביקשתם, ולכן עצרנו את הבנייה.'},
    // Plain words (owner 2026-11-21): a failed build is said in the customer's terms -- what happened, what happened to their
    // money (only when the record says so), and ONE action that exists. An unknown failure code gets failUnknown, never the
    // raw text. serverSaid: the server's own English sentences (409/422), answered by their code.
    failUnknown:'הבנייה לא הצליחה בגלל תקלה אצלנו.', failNotCharged:'לא חויבתם.',
    failNext:{ retry:l=>`אפשר לנסות שוב: לחצו על "${l}".`, edit:l=>`אפשר לשנות את הבקשה ולנסות שוב: לחצו על "${l}".`, input:l=>`כתבו את הפרט החסר בבקשה: לחצו על "${l}".` },
    failMissing:{ phone:'מספר הטלפון', hours:'שעות הפתיחה' },
    ownerTech:'פרטים טכניים (מוצגים רק לחשבון הבעלים)',
    serverSaid:{ build_contract_invalid:'התוכנית הזו כבר לא בתוקף. טענו את הדף מחדש ואשרו שוב.',
      empty_message:'ההודעה ריקה. כתבו משהו, בחרו תשובה או צרפו תמונה.',
      idempotency_conflict:'הבקשה הזו כבר נשלחה פעם עם פרטים אחרים. טענו את הדף מחדש ונסו שוב.',
      approval_required:'קודם צריך לאשר שהבנתי נכון את הבקשה: לחצו בשיחה על "כן, זה נכון", ואז נסו שוב.' },
    techDetails:'פרטים טכניים', previewStarting:'מפעילים תצוגה מקדימה…', previewRunning:'התצוגה המקדימה פועלת.',
    previewNotPreviewable:'הגרסה הזאת לא ניתנת להצגה מקדימה: ', previewUnavailable:'התצוגה המקדימה לא זמינה כרגע: ',
    previewFailed:'התצוגה המקדימה נכשלה: ', previewExpired:'התצוגה המקדימה פגה. אפשר להפעיל אותה מחדש.',
    startPreview:'הפעלת תצוגה מקדימה',
    duplicateBuild:'התוכנית הזאת כבר נבנית או נבנתה — מוצגת הבנייה הקיימת. כדי לבנות שוב, עדכנו את הבקשה.',
    current:'נוכחית', restore:'שחזור לגרסה הזו', restored:'שוחזר. נוצרה גרסה חדשה.', noVersions:'עדיין אין גרסאות.',
    modQueued:'השינוי נשלח. בונים גרסה מועמדת ובודקים אותה…', modReview:'הגרסה המועמדת עברה את הבדיקות. מה תרצו לעשות?',
    accept:'אישור השינוי', reject:'דחייה', modAccepted:'השינוי אושר ונשמר כגרסה חדשה.', modRejected:'השינוי נדחה.',
    modFailed:'השינוי נכשל: ', classification:'סיווג',
    gateNames:{verification:'אימות', quality:'איכות', security:'אבטחה', rights:'זכויות'},
    checksNotRun:'בדיקות שלא רצו', checksNoneRan:'אף בדיקה לא רצה: הבנייה נעצרה לפני הבדיקות.',
    checkNames:{preview_starts:'הפעלת ניסיון', behavioural_acceptance:'בדיקת התנהגות', browser_flow:'בדיקת דפדפן', visual_layout_desktop_mobile:'מראה הדף במחשב ובטלפון', qa_review:'סקירת איכות', qa_review_blocking_findings:'ממצאי סקירת האיכות', reviewer_independent_of_author:'סוקר שאינו הכותב', sandbox_build_and_tests:'בדיקות הקוד', cross_file_consistency:'עקביות בין הקבצים', dependency_allowlist:'ספריות מאושרות', approved_criteria_covered:'כיסוי הדרישות שאושרו', quality_score:'ציון איכות', static_security_scan:'סריקת אבטחה', rights_clear:'זכויות', acceptance_criteria_defined:'הגדרת דרישות קבלה'},
    repairStopped:'התיקון האוטומטי נעצר',
    repairStops:{time_budget:'התיקון האוטומטי נעצר: הבנייה הגיעה למגבלת הזמן שלה, ולכן לא התחיל סבב תיקון נוסף.', no_progress_repository_unchanged:'התיקון האוטומטי נעצר: סבב התיקון האחרון לא שינה שום קובץ, ולכן סבב נוסף לא היה משנה דבר.', no_progress_repository_cycle:'התיקון האוטומטי נעצר: התיקון חזר לגרסה שכבר נבדקה ונכשלה.', no_progress_empty_patch:'התיקון האוטומטי נעצר: סבב התיקון לא הציע שום שינוי.', no_progress_same_failure:'התיקון האוטומטי נעצר: סבב התיקון נגמר באותו כשל בדיוק כמו הסבב שלפניו.', max_repair_rounds:'התיקון האוטומטי נעצר: נגמרו סבבי התיקון שהוקצו לבנייה הזאת.', needs_customer_input:'התיקון האוטומטי נעצר: חסר פרט שרק אתם יכולים לתת.', test_value_fixed_twice:'התיקון האוטומטי נעצר: אותו ערך צפוי בבדיקה תוקן פעמיים, ולכן הבנייה הועברה לבדיקה ידנית.', repair_model_unavailable:'התיקון האוטומטי נעצר: אף מודל לא החזיר תיקון תקין (תשובה שאינה בפורמט, תשובה שנקטעה, או ספק בלי יתרה). הבנייה הסתיימה על הגרסה הטובה ביותר, עם תוצאות הבדיקות שלמטה. לא חויבתם.'},
    gates:'בדיקות', usage:'שירותים חיצוניים', costActual:'עלות בפועל', costBasis:'בסיס העלות', warnings:'אזהרות',
    requestIds:'מזהי בקשות', tokens:'טוקנים (קלט/פלט)', none:'אין',
    backendMissing:'<b>הבנייה לא זמינה כרגע.</b> זה אצלנו, לא אצלכם. אפשר להירשם, לנהל פרויקטים ולראות תוכנית ועלות.',
    emailUnverified:'האימייל עדיין לא אומת.',
    err401:'פג תוקף ההתחברות. היכנסו שוב.',
 errBadCreds:'האימייל או הסיסמה שגויים. אם אין לך חשבון — לחצו "יצירת חשבון חינם".',
 errAccountExists:'החשבון הזה כבר קיים. עברו ל"כניסה" עם אותה סיסמה.', err402:'אין מספיק יתרה לבנייה הזו: ', tryAgain:'נסו שוב',
    errPlanNotIncluded:'הבנייה הזו גדולה ממה שכלול אצלכם. אפשר לבקש פחות דברים, ואז היא תיכנס.', errAllowanceExhausted:'נגמרה היתרה. אפשר לבנות אתר קטן יותר.',
    err403:'אין הרשאה לפעולה הזו.', err404:'לא נמצא.', err409:'צריך הבהרה לפני שממשיכים.',
    err503:'השירות הזה עוד לא זמין: ', errNet:'אין חיבור אלינו. בדקו את החיבור לאינטרנט ונסו שוב.', errTimeout:'לא קיבלנו תשובה תוך 2 דקות. הפעולה אולי עוד רצה — רעננו בעוד רגע לפני שתנסו שוב.',
    err5xx:'משהו נכשל אצלנו. נסו שוב בעוד רגע; אם זה חוזר, שלחו צילום מסך.', offline:'אין חיבור לאינטרנט. מה שמוצג עשוי להיות לא מעודכן; הפעולות יחזרו לעבוד כשהחיבור יחזור.',
    dataPersistent:'הנתונים שתזינו באפליקציה נשמרים גם אחרי הפעלה מחדש ובגרסה הבאה (אין עדיין גיבוי).',
    shareLabel:'מי יכול לפתוח', sharePRIVATE:'רק אני (פרטי)', shareSHARED:'כל מי שיש לו קישור שיתוף', sharePUBLIC:'כולם (ציבורי)', shareLink:'קישור שיתוף', dataTemporary:'נתונים זמניים: מה שתזינו יימחק כשהתצוגה תיעצר.',
    needPrompt:'כתבו לפחות כמה מילים על האפליקציה.', needEmail:'הזינו אימייל וסיסמה של 10 תווים לפחות.',
    registered:'החשבון נוצר.', created:'הפרויקט נוצר.', renamed:'השם נשמר.', archived:'הפרויקט הועבר לארכיון.',
    downloadReady:'ההורדה התחילה.', untitled:'פרויקט חדש',
    lifecycle:'מחזור בנייה מלא: תכנון, קוד, התקנה, בנייה, בדיקות, תיקונים, תצוגה וייצוא', operatorDetails:'פרטים לצוות שלנו',
    b_durable_backend_not_configured:'הבנייה לא זמינה כרגע. זה אצלנו, לא אצלכם.',
    b_infrastructure:k=>`חלק מהאפליקציה עוד לא מוכן: ${k}`, b_image_provider:'יצירת אייקון ותמונות לא מוגדרת.',
    b_plan_cannot_authorize_cost:'הבנייה הזו גדולה ממה שכלול אצלכם.',
    mediaTitle:'מדיה שתיווצר בבנייה', mediaKinds:{'hero/brand visual':'תמונה ראשית', 'product icon':'אייקון', 'media.image.generate':'תמונה', 'media.video.generate':'וידאו', 'media.audio.tts':'הקראה קולית', 'media.audio.music':'מוזיקה'}, mediaOptional:'אופציונלי',
    planReasons:{'cost class not included in plan':'בנייה בגודל הזה לא כלולה אצלכם.', 'monthly credits exhausted':'נגמר מה שכלול אצלכם החודש.', 'paid-provider budget exhausted':'סכום הבנייה של החודש נגמר.'},
    b_qa_budget_denied:'תקציב אב־הטיפוס אינו מאפשר את הבנייה הזו. בדקו את יתרת בדיקות הפיתוח או נסו בקשה מצומצמת יותר.',
    qaBudgetTitle:'תקציב בדיקות אב־טיפוס — פרטי', qaBudgetRemaining:'יתרה פנימית מוערכת',
    qaBudgetLimit:'מגבלת הרשאה לבנייה אחת', qaBudgetActual:'אלה רישומי העלות של 148AI; לא יתרות אצל ספקי ה־AI.',
    b_cost_quote_unknown:'לחלק ממה שביקשתם עוד אין מחיר, ולכן אי אפשר להתחיל לבנות.',
    b_cost_quote_unavailable:'לא התקבלה הצעת מחיר מאומתת לבנייה.',
    b_spec_not_approved:'לפני שמתחילים לבנות, צריך לאשר שהבנתי נכון את הבקשה: לחצו על "כן, זה נכון".',
    b_plan_not_verified:'התוכנית עוד לא מוכנה. אשרו שהבנתי נכון את הבקשה ואכין אותה: לחצו על "כן, זה נכון".',
    b_approval_state_unavailable:'כרגע אי אפשר לבדוק אם אישרתם את הבקשה, ולכן לא מתחילים לבנות. זה אצלנו, לא אצלכם. נסו שוב בעוד כמה דקות.',
    b_brief_stale:'הבקשה השתנתה מאז שאישרתם אותה. אשרו את הבקשה כמו שהיא עכשיו: לחצו על "כן, זה נכון".',
    readinessBuilt:'הבנייה האחרונה הסתיימה בהצלחה', readinessNextBlocked:'בנייה נוספת לא אפשרית כרגע',     readinessReady:'ניתן לבקש אישור בנייה', readinessBlocked:'לא ניתן להתחיל בבנייה כרגע', readinessUnknown:'מוכנות הפרויקט טרם נבדקה', readinessRunning:'בניית הפרויקט מתבצעת', readinessDetails:'לפרטים',
    readinessBlockedHelp:l=>`עוד אי אפשר להתחיל לבנות, ואין לנו כרגע הסבר מדויק למה. אפשר לשנות את הבקשה ולנסות שוב: לחצו על "${l}".`,
    quoteMissingTitle:'מה שעוד אין לו מחיר:', quoteMissingHelp:l=>`אם אפשר לוותר על זה, הורידו את זה מהבקשה ונבנה בלי זה: לחצו על "${l}".`, quoteUnverified:'לחלק ממה שביקשתם עוד אין לנו מחיר, ולכן אי אפשר להתחיל לבנות.', unknownBlocker:'נדרש בירור נוסף לפני התחלת הבנייה.',
    k_database:'שמירת מידע', k_auth_session:'התחברות וסשנים', k_object_storage:'אחסון קבצים', k_scheduled_http:'משימות מתוזמנות', k_outbound:'מיילים ו-webhooks',
    newChat:'שיחה חדשה · פרויקט חדש', searchProjects:'חיפוש פרויקטים', canBuildTitle:'מה אפשר לבנות היום', noMatches:'לא נמצאו פרויקטים',
    hideSidebar:'הסתרת הסרגל', showSidebar:'הצגת הסרגל', previewToggle:'תצוגה', expandPreview:'הגדלת התצוגה', shrinkPreview:'הקטנת התצוגה',
    hidePreview:'סגירת התצוגה', resizePreview:'גרירה לשינוי רוחב התצוגה', send:'שליחה',
    chatPlaceholder:'כתבו מה תרצו לבנות או לשנות…', you:'אתם', assistant:'148AI', language:'שפה', docTitle:'148AI · סביבת יצירה',
    chatHelloTitle:'מה נבנה היום?', chatHello:'ספרו במילים שלכם מה אתם צריכים — אני אשאל רק מה שחשוב, אציע תוכנית ועלות, ושום דבר לא ייבנה בלי האישור שלכם.',
    tab_req:'דרישות', tab_plan:'תוכנית ועלות', tab_build:'בנייה', tab_change:'שינוי', tab_versions:'גרסאות', tab_details:'פרטים', tab_built:'המוצר',
    actShowPlan:'הצגת הסיכום, התוכנית והעלות', actApprove:'לאשר ולהתחיל לבנות', actApproveSpec:'כן, זה נכון',
    windowsTitle:'חלונות באתר', windowsHint:'סמנו כל חלון שתרצו באתר. חלון שלא מסומן לא ייבנה.',
    canonAck:'אני מאשר/ת בנייה בלי הפרטים החסרים שלמעלה (הם לא יומצאו, והחלק שתלוי בהם יושמט)', actConfirmMod:'שליחת השינוי לביצוע',
    delegateShort:'בחרו עבורי', convNotReady:'השיחה החכמה עוד לא זמינה כאן. השאלות המודרכות עובדות כרגיל.', fallbackNote:'השיחה החכמה עוד לא זמינה כאן, אז עברתי לשאלות המודרכות. הן מופיעות במסך "דרישות" ונשמרות.', archTitle:'תוכנית העבודה (מחלקות ומשימות)', feasibility:'היתכנות', layer:'שלב',
    f_FEASIBLE:'יש היתכנות טכנית', f_FEASIBLE_WITH_CONSTRAINTS:'היתכנות טכנית עם מגבלות', f_BLOCKED:'חסום כרגע', f_UNSUPPORTED:'לא נתמך עדיין', f_UNKNOWN:'לא ידוע',
    constraints:'מגבלות', ifNeeded:'אם צריך', tasksTitle:'פרטים טכניים: מי עושה מה', buildRunning:'הבנייה רצה', interpreterNote:'הפירוש נעשה בכללים קבועים (ללא מודל AI)',
    ts_SUCCEEDED:'הושלם', ts_RUNNING:'רץ', ts_PENDING:'ממתין', ts_READY:'מוכן', ts_FAILED:'נכשל', ts_BLOCKED:'חסום', ts_CANCELLED:'לא בוצע', ts_REPAIRING:'בתיקון', ts_NOT_RECORDED:'לא נרשם',
  },
  en: {
    skip:'Skip to content', projects:'Projects', manage:'Manage', logout:'Sign out',
    hero:'Describe your web app.', lead:'148AI plans, builds, tests and previews it.',
    how1:'Write what the app should do and for whom.', how2:'Get a plan and a maximum cost, then approve it.',
    how3:'Watch the build, try it in a preview, ask for changes and download the code.',
    scope:'Today: web apps and SaaS. Mobile, games and media are not available yet.',
    signinTitle:'Sign in', email:'Email', password:'Password', passwordHint:'At least 10 characters.', showPassword:'Show password', hidePassword:'Hide password',
    login:'Sign in', register:'Create free account',
    firstProject:'Your first project', projectName:'Project name', createProject:'Create project',
    request:'What do you want to build?', build:'Continue', planHint:'Nothing is built or charged before you approve a summary and a cost.',
    modeLegend:'How would you like to continue?', modeGuided:'Guided discovery', modeGuidedHint:'A few short questions — colours, font and style too. "No preference" is always an option.',
    modeRecommend:'Let 148AI recommend and choose', modeRecommendHint:'We choose from what you wrote; you review everything in the summary before approving.',
    discTitle:'Let\'s get the request right', discProgress:(a, r) => `${a} decisions · ${r} left`, why:'Why we ask: ',
    delegate:'No preference — choose for me', delegateWill:v => `(will use: ${v})`, suggestedFromRequest:'(from your request)',
    next:'Continue', skipGroup:'Skip these questions', pauseNote:'Everything is saved. You can continue after a refresh or from another device.',
    decided:'Decided so far', change:'Change', save:'Save', cancel:'Cancel', needAnswer:q => `Please answer: ${q}`,
    discDone:'Discovery is complete. Here is the summary — check it before approving.', showSummary:'Show summary and cost',
    src_message:'from your request', src_answer:'your answer', src_delegated:'chosen for you', src_default:'default',
    sumGoal:'Goal', sumIncluded:'Included', sumExcluded:'Not included for now', semanticTitle:'How we understood your request', semanticIncluded:'Required in the product', semanticExcluded:'Not requested', semanticUncertain:'Needs clarification', sumAssumptions:'Chosen for you (you can change these)',
    updateRequest:'Update the request', approveBuild:'Approve and start building', approvalExpired:'The approval expired. Review the summary and approve again.',
    builtTitle:'What has been built', newBuild:'New product in a new project', newProjectPlus:'+ New project', newProjectHint:'Each product gets its own project. Name it, then describe what to build.', nameRequired:'Give the project a name.', builtVersion:'Current version', files:'files',
    progress:'Build progress', modifyTitle:'What would you like to change?', modifySend:'Send change', versions:'Versions',
    evidence:'Technical details and evidence', refresh:'Refresh', openTab:'Open in new tab',
    noPreview:'Your app appears here once the build finishes.', download:'Download source (ZIP)', publish:'Publish',
    publishNotConfigured:'Publishing is not configured on this server yet. You can download the code and test it in the preview.',
    manageProject:'Manage project', rename:'Rename', saveName:'Save name', archive:'Archive',
    newProject:'New project', close:'Close',
    promptPlaceholder:'For example: an appointment system for a barbershop, with a calendar for barbers, self-booking for customers and email reminders.',
    propTitle:'Your proposal', propLooks:'This is how it will look', propGeneric:'General suggestion', propEstimate:'estimate', propPrice:'Build price', propIncluded:'Included', propExcluded:'Not included', propFacts:'Your details, as you wrote them', propApprove:'Approve and start building', propChange:'Change something', propEdit:'Change', propUp:'Move up', propDown:'Move down', propRemove:'Remove', propSave:'Save', propUndo:'Undo the last change', propApproving:'Approving and starting the build…', propNotYet:'The proposal is not ready yet: we will complete the details in the conversation.',
    planTitle:'The plan', understood:'What we understood', roles:'Users', data:'Data', integrations:'Integrations',
    capabilities:'Capabilities the build needs', infrastructure:'App infrastructure', cost:'Cost',
    estimated:'Estimate', maximum:'Approved maximum', questions:'Questions before we start', blockersTitle:'What is blocking right now',
    creditsRequired:'Price of this build (taken from your balance)', creditsRemaining:'Your balance', quoteStatus:'The price',
    confirm:'Approve and start building', editRequest:'Edit request', costUnknown:'Cannot be calculated',
    byPipeline:'in the build', byProvider:'external provider', required:'required', optional:'optional',
    st_LIVE:'Live', st_PARTIAL:'Configured, not verified', st_NOT_CONFIGURED:'Not configured', st_BLOCKED:'Blocked',
    st_SELF_CONTAINED:'Built into the app', st_PRICED:'Authorized', st_UNKNOWN:'No price yet', st_NOT_AUTHORIZED:'Not authorized',
    stepPlanning:'Planning', stepContract:'Build contract', stepInfra:'Infrastructure', stepAssets:'Assets (icon and images)',
    stepGenerate:'Generating code, building, testing and repairing', stepGates:'Quality, security and rights gates', stepPreview:'Preview',
    noteGenerate:'Build, tests and repairs run as one step. The number of repair rounds is reported at the end.',
    repairs:n=>`Repair rounds: ${n}`, queued:'Waiting in queue', queuedNext:'Waiting in queue: your build is next', queuedAhead:n=>`Waiting in queue: ${n === 1 ? '1 job' : n + ' jobs'} ahead of your build`, started:'Build started', buildReady:'Build finished successfully.',
    buildFailed:'Build failed',
    openDraftPreview:'Open the draft in Preview (did not pass every check)',
    stopBuild:'Stop the build', stopChange:'Stop the change', stopChangeConfirm:'Stop the change? Only what was already used is charged.', modCancelled:'The change was stopped.', stopConfirm:'Stop the build? Only what was already used is charged, and no version is created.',
    stopping:'The build stops when the current step ends (up to a few minutes).', buildCancelled:'The build was stopped. Only what was already used is charged.',
    liveLog:'What is happening now', logEmpty:'Waiting for the build server…', logNoBuild:'No build in this project yet.',
    checkingApproval:'Checking approval and budget — no build has started yet.',
    uiEmpty:'The site that was built came out empty', uiMissing:{form:'a form', input:'input fields', button:'a button', table:'a table', content:'content'}, uiMissingLead:'missing', uiEmptyTail:'so we did not hand it over.',
    errCodes:{preview_no_build_queue:'This test version of 148AI cannot build, so the build did not start.', build_not_found:'The build did not start because of a problem on our side.', verification_failed:'We could not build the site this time.',
      needs_customer_input:'A detail only you can give is missing, so we stopped the build. We will not invent it.',
      release_policy_failed:'We built the site, but it did not pass our checks, so we did not hand it over.',
      quality_gate_failed:'The site was built but did not come out good enough, so we did not hand it over.',
      preview_not_ready:'We built the site, but it did not open when we tried it, so we did not hand it over.',
      security_gate_failed:'We found a problem in the built site that could put its visitors\' information at risk, so we did not hand it over.',
      rights_gate_not_clear:'The site was built and saved, but we could not confirm that everything in it (a picture or a name, for example) may be used, so it is not ready yet.',
      unsupported_dependency:'The site you asked for needs something we cannot build yet.',
      worker_lost:'The build got stuck and we stopped it.',
      build_timeout:'The build took too long and we stopped it before it finished.',
      provider_liability_unknown:'The build stopped part-way. It is not known yet whether you were charged for what was already done.',
      worker_exception:'Something went wrong on our side during the build. It was not caused by you.',
      model_budget_exhausted:'The request is too big for one build, and the build stopped before it finished.',
      model_unavailable:'We are very busy right now, and the build was not finished. It is worth waiting a few minutes.',
      provider_quota_exhausted:'We are very busy right now, and the build was not finished. It is worth waiting a few minutes.',
      model_policy_blocked:'Something went wrong on our side during the build. It was not caused by you.',
      capability_gate_failed:'We could not prepare part of the site (the pictures, for example), so we did not hand it over.',
      image_mismatch:'The generated image does not show what you asked for, so we stopped the build.'},
    failUnknown:'The build did not succeed because of a problem on our side.', failNotCharged:'You were not charged.',
    failNext:{ retry:l=>`You can try again: press "${l}".`, edit:l=>`You can change the request and try again: press "${l}".`, input:l=>`Add the missing detail to the request: press "${l}".` },
    failMissing:{ phone:'the phone number', hours:'the opening hours' },
    ownerTech:'Technical details (shown to the owner account only)',
    serverSaid:{ build_contract_invalid:'This plan can no longer be used. Reload the page and approve again.',
      empty_message:'The message is empty. Write something, choose an answer or attach an image.',
      idempotency_conflict:'This request was already sent once with different details. Reload the page and try again.',
      approval_required:'First confirm that I understood the request: press "Yes, that is right" in the chat, then try again.' },
    techDetails:'Technical details', previewStarting:'Starting preview…', previewRunning:'Preview is running.',
    previewNotPreviewable:'This version cannot be previewed: ', previewUnavailable:'Preview is not available on this server: ',
    previewFailed:'Preview failed: ', previewExpired:'The preview expired. You can start it again.',
    startPreview:'Start preview',
    duplicateBuild:'This plan is already building or built — showing that build. Update the request to build again.',
    current:'Current', restore:'Restore this version', restored:'Restored as a new version.', noVersions:'No versions yet.',
    modQueued:'Change sent. Building and testing a candidate version…', modReview:'The candidate version passed its checks. What would you like to do?',
    accept:'Accept change', reject:'Reject', modAccepted:'Change accepted and saved as a new version.', modRejected:'Change rejected.',
    modFailed:'Change failed: ', classification:'Classification',
    gateNames:{verification:'Verification', quality:'Quality', security:'Security', rights:'Rights'},
    checksNotRun:'Checks that did not run', checksNoneRan:'No check ran: the build stopped before the checks.',
    checkNames:{preview_starts:'trial start-up', behavioural_acceptance:'behaviour check', browser_flow:'browser check', visual_layout_desktop_mobile:'how the page looks on desktop and phone', qa_review:'quality review', qa_review_blocking_findings:'quality review findings', reviewer_independent_of_author:'a reviewer who is not the author', sandbox_build_and_tests:'code tests', cross_file_consistency:'consistency between files', dependency_allowlist:'approved libraries', approved_criteria_covered:'coverage of the approved requirements', quality_score:'quality score', static_security_scan:'security scan', rights_clear:'rights', acceptance_criteria_defined:'acceptance criteria defined'},
    repairStopped:'Automatic repair stopped',
    repairStops:{time_budget:'Automatic repair stopped: the build reached its time limit, so no further repair round was started.', no_progress_repository_unchanged:'Automatic repair stopped: the last repair round changed no file, so another round would have changed nothing.', no_progress_repository_cycle:'Automatic repair stopped: the repair went back to a version that was already checked and failed.', no_progress_empty_patch:'Automatic repair stopped: the repair round proposed no change.', no_progress_same_failure:'Automatic repair stopped: the repair round ended in exactly the same failure as the round before.', max_repair_rounds:'Automatic repair stopped: the repair rounds allotted to this build are used up.', needs_customer_input:'Automatic repair stopped: a detail only you can give is missing.', test_value_fixed_twice:'Automatic repair stopped: the same expected value in a test was fixed twice, so the build was passed on for a human look.', repair_model_unavailable:'Automatic repair stopped: no model returned a valid repair (an answer in the wrong format, an answer cut short, or a provider with no credit). The build ended on its best version, with the check results below. You were not charged.'},
    gates:'Checks', usage:'Provider usage', costActual:'Actual cost', costBasis:'Cost basis', warnings:'Warnings',
    requestIds:'Request IDs', tokens:'Tokens (in/out)', none:'None',
    backendMissing:'<b>Building is not available on this server.</b> It needs PostgreSQL and S3 storage. You can sign up, manage projects and see a plan and cost.',
    emailUnverified:'Your email is not verified yet.',
    err401:'Your session expired. Sign in again.',
 errBadCreds:'Wrong email or password. If you have no account, click "Create free account".',
 errAccountExists:'This account already exists. Switch to "Sign in" with the same password.', err402:'Not enough credits or not allowed on your plan: ', tryAgain:'Try again',
    errPlanNotIncluded:'This build is not included in your plan. Upgrade your plan to continue.', errAllowanceExhausted:'Your budget or credits have run out. Add credits or build a smaller project.',
    err403:'You do not have access to this.', err404:'Not found.', err409:'Clarification is needed before continuing.',
    err503:'This service is not configured on the server yet: ', errNet:'Cannot reach the server. Check your connection and try again.', errTimeout:'The server did not answer within 2 minutes. The action may still be running — refresh in a moment before trying again.',
    err5xx:'Server error. Try again in a moment; if it repeats, send a screenshot.', offline:'You are offline. What you see may be out of date; actions work again when the connection returns.',
    dataPersistent:'Data you enter in the app survives a restart and the next version (no backup yet).',
    shareLabel:'Who can open it', sharePRIVATE:'Only me (private)', shareSHARED:'Anyone with the share link', sharePUBLIC:'Everyone (public)', shareLink:'Share link', dataTemporary:'Temporary data: what you enter is deleted when the preview stops.',
    needPrompt:'Write at least a few words about the app.', needEmail:'Enter an email and a password of at least 10 characters.',
    registered:'Account created.', created:'Project created.', renamed:'Name saved.', archived:'Project archived.',
    downloadReady:'Download started.', untitled:'New project',
    lifecycle:'Full build lifecycle: plan, code, install, build, test, repair, preview and export', operatorDetails:'Details for the server operator',
    b_durable_backend_not_configured:'Building needs a server with PostgreSQL and S3 storage.',
    b_infrastructure:k=>`App infrastructure is not ready: ${k}`, b_image_provider:'Icon and image generation is not configured.',
    b_plan_cannot_authorize_cost:'Your plan does not cover this build.',
    mediaTitle:'Media the build will make', mediaKinds:{'hero/brand visual':'Main image', 'product icon':'Icon', 'media.image.generate':'Image', 'media.video.generate':'Video', 'media.audio.tts':'Voice-over', 'media.audio.music':'Music'}, mediaOptional:'optional',
    planReasons:{'cost class not included in plan':'Your plan does not include a build of this size.', 'monthly credits exhausted':'The monthly credits are used up.', 'paid-provider budget exhausted':"This month's build budget on your plan is used up."},
    b_qa_budget_denied:'The prototype QA budget cannot authorize this build. Check the testing balance or reduce the request.',
    qaBudgetTitle:'Private prototype testing budget', qaBudgetRemaining:'Estimated internal allowance left',
    qaBudgetLimit:'Per-build testing limit', qaBudgetActual:'These are 148AI spend records, not your AI providers’ account balances.',
    b_cost_quote_unknown:'Part of what you asked for has no price yet, so the build cannot start.',
    b_cost_quote_unavailable:'No verified build quote was returned.',
    b_spec_not_approved:'Before the build starts, confirm that I understood the request: press "Yes, that is right".',
    b_plan_not_verified:'The plan is not ready yet. Confirm that I understood the request and I will prepare it: press "Yes, that is right".',
    b_approval_state_unavailable:'We cannot check right now whether you confirmed the request, so no build starts. This is on our side, not yours. Try again in a few minutes.',
    b_brief_stale:'The request changed after you confirmed it. Confirm it as it is now: press "Yes, that is right".',
    readinessBuilt:'The last build finished successfully', readinessNextBlocked:'Another build is not possible right now',     readinessReady:'Build approval can be requested', readinessBlocked:'Build cannot start yet', readinessUnknown:'Project readiness has not been checked', readinessRunning:'Project build in progress', readinessDetails:'Details',
    readinessBlockedHelp:l=>`The build cannot start yet, and we have no exact reason to give you right now. You can change the request and try again: press "${l}".`,
    quoteMissingTitle:'What has no price yet:', quoteMissingHelp:l=>`If you can do without it, take it out of the request and we will build without it: press "${l}".`, quoteUnverified:'Part of what you asked for has no price yet, so the build cannot start.', unknownBlocker:'Further checks are needed before building.',
    k_database:'database', k_auth_session:'sign-in and sessions', k_object_storage:'file storage', k_scheduled_http:'scheduled jobs', k_outbound:'email and webhooks',
    newChat:'New chat · new project', searchProjects:'Search projects', canBuildTitle:'What can be built today', noMatches:'No projects found',
    hideSidebar:'Hide sidebar', showSidebar:'Show sidebar', previewToggle:'Preview', expandPreview:'Enlarge preview', shrinkPreview:'Restore preview size',
    hidePreview:'Close preview', resizePreview:'Drag to resize the preview', send:'Send',
    chatPlaceholder:'Describe what you want to build or change…', you:'You', assistant:'148AI', language:'Language', docTitle:'148AI · Creator workspace',
    aiFallback:'This reply was built from fixed rules, without an AI model.',
    chatHelloTitle:'What shall we build today?', chatHello:'Tell me in your own words what you need. I only ask what matters, propose a plan and a cost, and nothing is built without your approval.',
    tab_req:'Requirements', tab_plan:'Plan & cost', tab_build:'Build', tab_change:'Change', tab_versions:'Versions', tab_details:'Details', tab_built:'Product',
    actShowPlan:'Show summary, plan and cost', actApprove:'Approve and start building', actApproveSpec:'Yes, that is right',
    windowsTitle:'Windows on the site', windowsHint:'Tick each window you want on the site. A window left unticked is not built.',
    canonAck:'I confirm building without the missing details above (they are not invented; the part that needs them is left out)', actConfirmMod:'Send this change',
    delegateShort:'Choose for me', convNotReady:'The conversation is not installed on this server yet (database migration 036 pending). Guided questions still work.', fallbackNote:'The conversation is not installed on this server yet, so I switched to the guided questions. They are in the "Requirements" tab and are saved.', archTitle:'Work plan (departments and tasks)', feasibility:'Feasibility', layer:'Step',
    f_FEASIBLE:'Technically feasible', f_FEASIBLE_WITH_CONSTRAINTS:'Technically feasible with limitations', f_BLOCKED:'Blocked for now', f_UNSUPPORTED:'Not supported yet', f_UNKNOWN:'Unknown',
    constraints:'Limitations', ifNeeded:'if needed', tasksTitle:'Technical details: who does what (from the server records)', buildRunning:'Build running', interpreterNote:'Interpreted with fixed rules (no AI model)',
    ts_SUCCEEDED:'done', ts_RUNNING:'running', ts_PENDING:'waiting', ts_READY:'ready', ts_FAILED:'failed', ts_BLOCKED:'blocked', ts_CANCELLED:'not run', ts_REPAIRING:'repairing', ts_NOT_RECORDED:'not recorded',
  },
  // Arabic (2026-11-22): translated from the Hebrew by three agents, each batch independently reviewed and corrected;
  // customer words, never system words (omni_prod/customer_words.py), second person plural as in Hebrew.
  ar: {
    skip: "الانتقال إلى المحتوى",
    projects: "المشاريع",
    manage: "إدارة",
    logout: "تسجيل الخروج",
    hero: "صِفوا تطبيق الويب الخاص بكم.",
    lead: "148AI تخطّط له وتبنيه وتختبره وتعرضه.",
    how1: "تكتبون ما يجب أن يفعله التطبيق ولمن.",
    how2: "تحصلون على خطة وحدّ أقصى للتكلفة، وتوافقون عليها.",
    how3: "تشاهدون البناء، وتجرّبونه في المعاينة، وتُجرون تغييرات، وتنزّلون الكود.",
    scope: "حاليًا: تطبيقات الويب وSaaS. تطبيقات الجوّال والألعاب والوسائط غير متاحة بعد.",
    signinTitle: "تسجيل الدخول إلى الحساب",
    email: "البريد الإلكتروني",
    password: "كلمة المرور",
    passwordHint: "10 أحرف على الأقل.",
    showPassword: "إظهار كلمة المرور",
    hidePassword: "إخفاء كلمة المرور",
    login: "تسجيل الدخول",
    register: "إنشاء حساب مجاني",
    firstProject: "مشروعكم الأول",
    projectName: "اسم المشروع",
    createProject: "إنشاء مشروع",
    request: "ماذا تريدون أن تبنوا؟",
    build: "متابعة",
    planHint: "لا نبدأ البناء ولا نحصّل أي مبلغ قبل أن توافقوا على الملخّص والتكلفة.",
    modeLegend: "كيف تريدون المتابعة؟",
    modeGuided: "محادثة موجّهة",
    modeGuidedHint: "سنطرح بعض الأسئلة القصيرة — عن الألوان ونوع الخط والأسلوب أيضًا. يمكنكم الإجابة \"لا تفضيل لديّ\".",
    modeRecommend: "148AI توصي وتختار",
    modeRecommendHint: "سنختار لكم بحسب ما كتبتم، وسترون كل شيء في الملخّص قبل الموافقة.",
    discTitle: "لنحدّد الطلب بدقّة",
    discProgress: (a, r) => `${a} قرارات · بقي ${r}`,
    why: "لماذا نسأل: ",
    delegate: "لا تفضيل لديّ — اختاروا عنّي",
    delegateWill: v => `(سنختار: ${v})`,
    suggestedFromRequest: "(بحسب ما كتبتم)",
    next: "متابعة",
    skipGroup: "تخطّوا هذه الأسئلة",
    pauseNote: "كل شيء محفوظ. يمكنكم العودة والمتابعة حتى بعد تحديث الصفحة أو من جهاز آخر.",
    decided: "ما قرّرناه حتى الآن",
    change: "تغيير",
    save: "حفظ",
    cancel: "إلغاء",
    needAnswer: q => `نحتاج إلى إجابة عن: ${q}`,
    discDone: "انتهينا. هذا هو الملخّص — راجعوه قبل الموافقة.",
    showSummary: "عرض الملخّص والتكلفة",
    src_message: "من طلبكم",
    src_answer: "إجابتكم",
    src_delegated: "اخترناه لكم",
    src_default: "الخيار الافتراضي",
    sumGoal: "الهدف",
    sumIncluded: "مشمول",
    sumExcluded: "غير مشمول في هذه المرحلة",
    semanticTitle: "هكذا فهمنا الطلب",
    semanticIncluded: "مطلوب في المنتج",
    semanticExcluded: "لم يُطلب",
    semanticUncertain: "يحتاج إلى توضيح",
    sumAssumptions: "قرارات اخترناها لكم (يمكن تغييرها)",
    updateRequest: "تحديث الطلب",
    approveBuild: "الموافقة وبدء البناء",
    approvalExpired: "انتهت صلاحية الموافقة. راجعوا الملخّص ووافقوا مرة أخرى.",
    builtTitle: "ما تم بناؤه حتى الآن",
    newBuild: "منتج جديد في مشروع جديد",
    newProjectPlus: "+ مشروع جديد",
    newProjectHint: "لكل منتج مشروعه الخاص. أعطوه اسمًا، ثم صِفوا ما تريدون بناءه.",
    nameRequired: "يجب إعطاء المشروع اسمًا.",
    builtVersion: "النسخة الحالية",
    files: "ملفات",
    progress: "تقدّم البناء",
    modifyTitle: "ماذا تريدون أن تغيّروا؟",
    modifySend: "إرسال التغيير",
    versions: "النسخ",
    evidence: "تفاصيل تقنية وأدلة",
    refresh: "تحديث",
    openTab: "فتح في صفحة جديدة",
    noPreview: "سيظهر التطبيق هنا بعد انتهاء البناء.",
    download: "تنزيل الكود المصدري (ZIP)",
    publish: "نشر",
    publishNotConfigured: "النشر على الإنترنت غير متاح بعد. يمكنكم تنزيل الكود وتجربته في المعاينة.",
    manageProject: "إدارة المشروع",
    rename: "تغيير الاسم",
    saveName: "حفظ الاسم",
    archive: "نقل إلى الأرشيف",
    newProject: "مشروع جديد",
    close: "إغلاق",
    promptPlaceholder: "مثلًا: نظام لإدارة المواعيد لصالون حلاقة، مع تقويم للحلّاقين، وحجز ذاتي للزبائن، وتذكيرات عبر البريد الإلكتروني.",
    propTitle: "اقتراحكم",
    propLooks: "هكذا سيبدو",
    propGeneric: "اقتراح عام",
    propEstimate: "تقدير",
    propPrice: "سعر البناء",
    propIncluded: "مشمول",
    propExcluded: "غير مشمول",
    propFacts: "تفاصيلكم، كما كتبتموها",
    propApprove: "الموافقة وبدء البناء",
    propChange: "تغيير شيء ما",
    propEdit: "تغيير",
    propUp: "نقل إلى الأعلى",
    propDown: "نقل إلى الأسفل",
    propRemove: "إزالة",
    propSave: "حفظ",
    propUndo: "التراجع عن التغيير الأخير",
    propApproving: "جارٍ الموافقة وبدء البناء…",
    propNotYet: "الاقتراح غير جاهز بعد: سنستكمل التفاصيل في المحادثة.",
    planTitle: "الخطة",
    understood: "ما فهمناه",
    roles: "المستخدمون",
    data: "البيانات",
    integrations: "الربط",
    capabilities: "القدرات التي يحتاجها البناء",
    infrastructure: "ما يحتاجه التطبيق",
    cost: "التكلفة",
    estimated: "تقدير",
    maximum: "الحد الأقصى الموافق عليه",
    questions: "أسئلة قبل أن نبدأ",
    blockersTitle: "ما العائق الآن",
    creditsRequired: "سعر البناء (يُخصم من رصيدكم)",
    creditsRemaining: "رصيدكم",
    quoteStatus: "السعر",
    confirm: "الموافقة وبدء البناء",
    editRequest: "تعديل الطلب",
    costUnknown: "لا يمكن حسابه",
    byPipeline: "ضمن البناء",
    byProvider: "خدمة خارجية",
    required: "مطلوب",
    optional: "اختياري",
    st_LIVE: "فعّال",
    st_PARTIAL: "مُعدّ، لم يُفحص",
    st_NOT_CONFIGURED: "غير مُعدّ",
    st_BLOCKED: "متوقف",
    st_SELF_CONTAINED: "مدمج في التطبيق",
    st_PRICED: "تمت الموافقة",
    st_UNKNOWN: "لا يوجد سعر بعد",
    st_NOT_AUTHORIZED: "لم تتم الموافقة",
    stepPlanning: "التخطيط",
    stepContract: "عقد البناء",
    stepInfra: "الأساس",
    stepAssets: "المواد (أيقونة وصور)",
    stepGenerate: "إنشاء الكود والبناء والفحوصات والإصلاحات",
    stepGates: "فحوصات الجودة والأمان والحقوق",
    stepPreview: "المعاينة",
    noteGenerate: "البناء والفحوصات والإصلاحات تجري في خطوة واحدة. يُعرض عدد جولات الإصلاح في النهاية.",
    repairs: n=>`جولات الإصلاح: ${n}`,
    queued: "في قائمة الانتظار",
    queuedNext: "في قائمة الانتظار: بناؤكم هو التالي",
    queuedAhead: n=>`في قائمة الانتظار: ${n === 1 ? 'مهمة واحدة' : n === 2 ? 'مهمتان' : n <= 10 ? n + ' مهام' : n + ' مهمة'} قبل بنائكم`,
    started: "بدأ البناء",
    buildReady: "اكتمل البناء بنجاح.",
    buildFailed: "فشل البناء",
    openDraftPreview: "افتحوا المسودة في المعاينة (لم تجتز كل الفحوصات)",
    stopBuild: "إيقاف البناء",
    stopChange: "إيقاف التغيير",
    stopChangeConfirm: "هل تريدون إيقاف التغيير؟ لن يُخصم منكم إلا مقابل ما استُخدم بالفعل.",
    modCancelled: "تم إيقاف التغيير.",
    stopConfirm: "هل تريدون إيقاف البناء؟ لن يُخصم منكم إلا مقابل ما استُخدم بالفعل، ولن تُنشأ النسخة.",
    stopping: "سيتم الإيقاف عند انتهاء الخطوة الحالية (بضع دقائق على الأكثر).",
    buildCancelled: "تم إيقاف البناء. لن يُخصم منكم إلا مقابل ما استُخدم بالفعل.",
    liveLog: "ما يحدث الآن",
    logEmpty: "نستعد للبناء…",
    logNoBuild: "لا يوجد بناء في هذا المشروع بعد.",
    checkingApproval: "نتحقق من الموافقة والميزانية — لم يبدأ البناء بعد.",
    uiEmpty: "جاء الموقع الذي بُني فارغًا",
    uiMissing: {"form":"استمارة","input":"حقول إدخال","button":"زر","table":"جدول","content":"محتوى"},
    uiMissingLead: "ينقصه",
    uiEmptyTail: "لذلك لم نسلّمه.",
    errCodes: {"preview_no_build_queue":"لا يمكن البناء في هذه النسخة التجريبية من 148AI، لذلك لم يبدأ البناء.","build_not_found":"لم يبدأ البناء بسبب عطل لدينا.","verification_failed":"لم ننجح في بناء الموقع هذه المرة.","needs_customer_input":"تنقص معلومة لا يستطيع تقديمها إلا أنتم، لذلك أوقفنا البناء. لن نختلقها.","release_policy_failed":"بنينا الموقع، لكنه لم يجتز فحوصاتنا، لذلك لم نسلّمه.","quality_gate_failed":"بُني الموقع لكنه لم يخرج بجودة كافية، لذلك لم نسلّمه.","preview_not_ready":"بنينا الموقع، لكنه لم يُفتح عندما جرّبناه، لذلك لم نسلّمه.","security_gate_failed":"وجدنا في الموقع الذي بُني مشكلة قد تعرّض معلومات زوّاره للخطر، لذلك لم نسلّمه.","rights_gate_not_clear":"بُني الموقع وحُفظ، لكننا لم نتمكن من التأكد من أنه مسموح استخدام كل ما فيه (مثلًا صورة أو اسم)، لذلك ليس جاهزًا بعد.","unsupported_dependency":"الموقع الذي طلبتموه يحتاج إلى شيء لا نعرف كيف نبنيه بعد.","worker_lost":"علِق البناء فأوقفناه.","build_timeout":"استغرق البناء وقتًا أطول من اللازم، فأوقفناه قبل أن ينتهي.","provider_liability_unknown":"توقف البناء في منتصفه. لا يُعرف بعد إن كان قد خُصم منكم مقابل ما أُنجز حتى الآن.","worker_exception":"حدث خلل لدينا أثناء البناء. هذا ليس بسببكم.","model_budget_exhausted":"الطلب كبير جدًا على بناء واحد، وقد توقف البناء قبل أن ينتهي.","model_unavailable":"هناك ضغط كبير لدينا حاليًا، ولم يكتمل البناء. يُستحسن الانتظار بضع دقائق.","provider_quota_exhausted":"هناك ضغط كبير لدينا حاليًا، ولم يكتمل البناء. يُستحسن الانتظار بضع دقائق.","model_policy_blocked":"حدث خلل لدينا أثناء البناء. هذا ليس بسببكم.","capability_gate_failed":"لم نتمكن من تجهيز جزء من الموقع (مثلًا الصور)، لذلك لم نسلّمه.","image_mismatch":"الصورة التي أُنشئت لا تُظهر ما طلبتموه، لذلك أوقفنا البناء."},
    failUnknown: "لم ينجح البناء بسبب عطل لدينا.",
    failNotCharged: "لم يُخصم منكم أي مبلغ.",
    failNext: { edit: l=>`يمكنكم تغيير الطلب والمحاولة مرة أخرى: اضغطوا على "${l}".`, input: l=>`اكتبوا التفصيل الناقص في الطلب: اضغطوا على "${l}".`, retry: l=>`يمكنكم المحاولة مرة أخرى: اضغطوا على "${l}".` },
    failMissing: {"phone":"رقم الهاتف","hours":"ساعات العمل"},
    ownerTech: "تفاصيل تقنية (تظهر لحساب المالك فقط)",
    serverSaid: {"build_contract_invalid":"هذه الخطة لم تعد سارية. أعيدوا تحميل الصفحة ووافقوا مرة أخرى.","empty_message":"الرسالة فارغة. اكتبوا شيئًا أو اختاروا إجابة أو أرفقوا صورة.","idempotency_conflict":"سبق أن أُرسل هذا الطلب بتفاصيل مختلفة. أعيدوا تحميل الصفحة وحاولوا مرة أخرى.","approval_required":"يجب أولًا تأكيد أنني فهمت الطلب بشكل صحيح: اضغطوا في المحادثة على \"نعم، هذا صحيح\"، ثم حاولوا مرة أخرى."},
    techDetails: "تفاصيل تقنية",
    previewStarting: "نشغّل المعاينة…",
    previewRunning: "المعاينة تعمل.",
    previewNotPreviewable: "لا يمكن معاينة هذه النسخة: ",
    previewUnavailable: "المعاينة غير متاحة حاليًا: ",
    previewFailed: "فشلت المعاينة: ",
    previewExpired: "انتهت صلاحية المعاينة. يمكنكم تشغيلها من جديد.",
    startPreview: "تشغيل المعاينة",
    duplicateBuild: "هذه الخطة قيد البناء أو بُنيت بالفعل — نعرض البناء الموجود. لإعادة البناء، حدّثوا الطلب.",
    current: "الحالية",
    restore: "استعادة هذه النسخة",
    restored: "تمت الاستعادة. أُنشئت نسخة جديدة.",
    noVersions: "لا توجد نسخ بعد.",
    modQueued: "أُرسل التغيير. نبني نسخة مرشّحة ونفحصها…",
    modReview: "اجتازت النسخة المرشّحة الفحوصات. ماذا تريدون أن تفعلوا؟",
    accept: "الموافقة على التغيير",
    reject: "رفض",
    modAccepted: "تمت الموافقة على التغيير وحُفظ كنسخة جديدة.",
    modRejected: "تم رفض التغيير.",
    modFailed: "فشل التغيير: ",
    classification: "التصنيف",
    gateNames: {"verification":"التحقق","quality":"الجودة","security":"الأمان","rights":"الحقوق"},
    checksNotRun: "فحوصات لم تُجرَ",
    checksNoneRan: "لم يُجرَ أي فحص: توقف البناء قبل الفحوصات.",
    checkNames: {"preview_starts":"تشغيل تجريبي","behavioural_acceptance":"فحص السلوك","browser_flow":"فحص في المتصفح","visual_layout_desktop_mobile":"مظهر الصفحة على الحاسوب والهاتف","qa_review":"مراجعة الجودة","qa_review_blocking_findings":"ملاحظات مراجعة الجودة","reviewer_independent_of_author":"مراجِع غير الكاتب","sandbox_build_and_tests":"فحوصات الكود","cross_file_consistency":"الاتساق بين الملفات","dependency_allowlist":"مكتبات معتمدة","approved_criteria_covered":"تغطية المتطلبات التي تمت الموافقة عليها","quality_score":"درجة الجودة","static_security_scan":"فحص الأمان","rights_clear":"الحقوق","acceptance_criteria_defined":"تحديد متطلبات القبول"},
    repairStopped: "توقف الإصلاح التلقائي",
    repairStops: {"time_budget":"توقف الإصلاح التلقائي: وصل البناء إلى الحد الزمني المخصص له، لذلك لم تبدأ جولة إصلاح أخرى.","no_progress_repository_unchanged":"توقف الإصلاح التلقائي: جولة الإصلاح الأخيرة لم تغيّر أي ملف، لذلك لم تكن جولة أخرى لتغيّر شيئًا.","no_progress_repository_cycle":"توقف الإصلاح التلقائي: عاد الإصلاح إلى نسخة سبق فحصها وفشلت.","no_progress_empty_patch":"توقف الإصلاح التلقائي: لم تقترح جولة الإصلاح أي تغيير.","no_progress_same_failure":"توقف الإصلاح التلقائي: انتهت جولة الإصلاح بالفشل نفسه تمامًا كالجولة التي سبقتها.","max_repair_rounds":"توقف الإصلاح التلقائي: نفدت جولات الإصلاح المخصصة لهذا البناء.","needs_customer_input":"توقف الإصلاح التلقائي: تنقص معلومة لا يستطيع تقديمها إلا أنتم.","test_value_fixed_twice":"توقف الإصلاح التلقائي: صُحّحت القيمة المتوقعة نفسها في أحد الفحوصات مرتين، لذلك أُحيل البناء إلى فحص يدوي.","repair_model_unavailable":"توقف الإصلاح التلقائي: لم تُرجِع أيُّ أداة من أدوات الذكاء الاصطناعي إصلاحًا صالحًا (إجابة بصيغة غير صحيحة، أو إجابة مقطوعة، أو خدمة خارجية بلا رصيد). انتهى البناء بأفضل نسخة، مع نتائج الفحوصات أدناه. لم يُخصم منكم أي مبلغ."},
    gates: "الفحوصات",
    usage: "الخدمات الخارجية",
    costActual: "التكلفة الفعلية",
    costBasis: "أساس التكلفة",
    warnings: "تحذيرات",
    requestIds: "معرّفات الطلبات",
    tokens: "التوكنات (إدخال/إخراج)",
    none: "لا يوجد",
    backendMissing: "<b>البناء غير متاح حاليًا.</b> المشكلة لدينا، وليست لديكم. يمكنكم إنشاء حساب وإدارة المشاريع ورؤية خطة وتكلفة.",
    emailUnverified: "لم يتم التحقق من البريد الإلكتروني بعد.",
    err401: "انتهت صلاحية تسجيل الدخول. سجّلوا الدخول مرة أخرى.",
    errBadCreds: "البريد الإلكتروني أو كلمة المرور غير صحيحة. إذا لم يكن لديكم حساب — اضغطوا \"إنشاء حساب مجاني\".",
    errAccountExists: "هذا الحساب موجود بالفعل. انتقلوا إلى \"تسجيل الدخول\" بكلمة المرور نفسها.",
    err402: "لا يوجد رصيد كافٍ لهذا البناء: ",
    tryAgain: "حاولوا مرة أخرى",
    errPlanNotIncluded: "هذا البناء أكبر مما هو مشمول لديكم. يمكنكم طلب أشياء أقل، وعندها سيكون ضمن المشمول.",
    errAllowanceExhausted: "نفد الرصيد. يمكنكم بناء موقع أصغر.",
    err403: "لا توجد صلاحية لهذا الإجراء.",
    err404: "غير موجود.",
    err409: "نحتاج إلى توضيح قبل المتابعة.",
    err503: "هذه الخدمة غير متاحة بعد: ",
    errNet: "لا يوجد اتصال بنا. تحققوا من اتصالكم بالإنترنت وحاولوا مرة أخرى.",
    errTimeout: "لم نتلقَّ ردًا خلال 2 دقيقة. ربما لا تزال العملية جارية — حدّثوا الصفحة بعد لحظة قبل أن تحاولوا مرة أخرى.",
    err5xx: "حدث خلل لدينا. حاولوا مرة أخرى بعد لحظة؛ وإذا تكرر ذلك، أرسلوا لقطة شاشة.",
    offline: "لا يوجد اتصال بالإنترنت. ما يظهر قد لا يكون محدّثًا؛ ستعود الإجراءات للعمل عند عودة الاتصال.",
    dataPersistent: "البيانات التي تُدخلونها في التطبيق تبقى محفوظة حتى بعد إعادة التشغيل وفي النسخة التالية (لا توجد نسخة احتياطية بعد).",
    shareLabel: "من يمكنه فتحه",
    sharePRIVATE: "أنا فقط (خاص)",
    shareSHARED: "كل من لديه رابط المشاركة",
    sharePUBLIC: "الجميع (عام)",
    shareLink: "رابط المشاركة",
    dataTemporary: "بيانات مؤقتة: ما تُدخلونه سيُحذف عند توقف المعاينة.",
    needPrompt: "اكتبوا بضع كلمات على الأقل عن التطبيق.",
    needEmail: "أدخلوا بريدًا إلكترونيًا وكلمة مرور من 10 أحرف على الأقل.",
    registered: "تم إنشاء الحساب.",
    created: "تم إنشاء المشروع.",
    renamed: "تم حفظ الاسم.",
    archived: "نُقل المشروع إلى الأرشيف.",
    downloadReady: "بدأ التنزيل.",
    untitled: "مشروع جديد",
    lifecycle: "دورة بناء كاملة: تخطيط، كود، تثبيت، بناء، فحوصات، إصلاحات، معاينة وتصدير",
    operatorDetails: "تفاصيل لفريقنا",
    b_durable_backend_not_configured: "البناء غير متاح حاليًا. المشكلة عندنا، لا عندكم.",
    b_infrastructure: k=>`جزء من التطبيق ليس جاهزًا بعد: ${k}`,
    b_image_provider: "لم يتم إعداد إنشاء الأيقونة والصور.",
    b_plan_cannot_authorize_cost: "هذا البناء أكبر مما هو مشمول لديكم.",
    mediaTitle: "الوسائط التي ستُنشأ أثناء البناء",
    mediaKinds: {"hero/brand visual":"صورة رئيسية","product icon":"أيقونة","media.image.generate":"صورة","media.video.generate":"فيديو","media.audio.tts":"تعليق صوتي","media.audio.music":"موسيقى"},
    mediaOptional: "اختياري",
    planReasons: {"cost class not included in plan":"بناء بهذا الحجم غير مشمول لديكم.","monthly credits exhausted":"نفد ما هو مشمول لديكم هذا الشهر.","paid-provider budget exhausted":"نفد مبلغ البناء لهذا الشهر."},
    b_qa_budget_denied: "ميزانية التجربة الأولية لا تسمح بهذا البناء. تحققوا من رصيد فحوصات التطوير أو جرّبوا طلبًا أصغر.",
    qaBudgetTitle: "ميزانية فحوصات التجربة الأولية — خاص",
    qaBudgetRemaining: "الرصيد الداخلي المقدَّر",
    qaBudgetLimit: "الحدّ المسموح به لبناء واحد",
    qaBudgetActual: "هذه سجلات التكلفة في 148AI؛ وليست أرصدة لدى شركات الذكاء الاصطناعي.",
    b_cost_quote_unknown: "جزء مما طلبتموه ليس له سعر بعد، ولذلك لا يمكن بدء البناء.",
    b_cost_quote_unavailable: "لم يصل عرض سعر مؤكَّد للبناء.",
    b_spec_not_approved: "قبل أن نبدأ البناء، يجب أن تؤكدوا أنني فهمت الطلب بشكل صحيح: اضغطوا على \"نعم، هذا صحيح\".",
    b_plan_not_verified: "الخطة ليست جاهزة بعد. أكّدوا أنني فهمت الطلب بشكل صحيح وسأُعدّها: اضغطوا على \"نعم، هذا صحيح\".",
    b_approval_state_unavailable: "لا يمكننا الآن التحقق مما إذا كنتم قد أكّدتم الطلب، ولذلك لن يبدأ البناء. المشكلة عندنا، لا عندكم. حاولوا مرة أخرى بعد بضع دقائق.",
    b_brief_stale: "تغيّر الطلب منذ أن أكّدتموه. أكّدوا الطلب كما هو الآن: اضغطوا على \"نعم، هذا صحيح\".",
    readinessBuilt: "انتهى البناء الأخير بنجاح",
    readinessNextBlocked: "بناء إضافي غير ممكن حاليًا",
    readinessReady: "يمكن طلب الموافقة على البناء",
    readinessBlocked: "لا يمكن بدء البناء حاليًا",
    readinessUnknown: "لم يتم فحص جاهزية المشروع بعد",
    readinessRunning: "بناء المشروع جارٍ",
    readinessDetails: "للتفاصيل",
    readinessBlockedHelp: l=>`لا يمكن بدء البناء بعد، وليس لدينا الآن تفسير دقيق للسبب. يمكنكم تغيير الطلب والمحاولة مرة أخرى: اضغطوا على "${l}".`,
    quoteMissingTitle: "ما ليس له سعر بعد:",
    quoteMissingHelp: l=>`إذا كان بإمكانكم الاستغناء عنه، احذفوه من الطلب وسنبني بدونه: اضغطوا على "${l}".`,
    quoteUnverified: "جزء مما طلبتموه ليس لدينا سعر له بعد، ولذلك لا يمكن بدء البناء.",
    unknownBlocker: "يلزم توضيح إضافي قبل بدء البناء.",
    k_database: "حفظ المعلومات",
    k_auth_session: "تسجيل الدخول والجلسات",
    k_object_storage: "تخزين الملفات",
    k_scheduled_http: "مهام مجدولة",
    k_outbound: "البريد الإلكتروني و webhooks",
    newChat: "محادثة جديدة · مشروع جديد",
    searchProjects: "البحث في المشاريع",
    canBuildTitle: "ما الذي يمكن بناؤه اليوم",
    noMatches: "لم يتم العثور على مشاريع",
    hideSidebar: "إخفاء الشريط الجانبي",
    showSidebar: "إظهار الشريط الجانبي",
    previewToggle: "المعاينة",
    expandPreview: "تكبير المعاينة",
    shrinkPreview: "تصغير المعاينة",
    hidePreview: "إغلاق المعاينة",
    resizePreview: "السحب لتغيير عرض المعاينة",
    send: "إرسال",
    chatPlaceholder: "اكتبوا ما تريدون بناءه أو تغييره…",
    you: "أنتم",
    assistant: "148AI",
    language: "اللغة",
    docTitle: "148AI · مساحة الإنشاء",
    aiFallback: "أُعِدّ هذا الرد وفق قواعد ثابتة، بدون ذكاء اصطناعي.",
    chatHelloTitle: "ماذا نبني اليوم؟",
    chatHello: "أخبروني بكلماتكم ما الذي تحتاجونه — سأسأل فقط عمّا هو مهم، وأقترح خطة وتكلفة، ولن يُبنى أي شيء دون موافقتكم.",
    tab_req: "المتطلبات",
    tab_plan: "الخطة والتكلفة",
    tab_build: "البناء",
    tab_change: "تغيير",
    tab_versions: "النسخ",
    tab_details: "التفاصيل",
    tab_built: "المنتج",
    actShowPlan: "عرض الملخص والخطة والتكلفة",
    actApprove: "الموافقة وبدء البناء",
    actApproveSpec: "نعم، هذا صحيح",
    windowsTitle: "النوافذ في الموقع",
    windowsHint: "حدّدوا كل نافذة تريدونها في الموقع. النافذة غير المحدّدة لن تُبنى.",
    canonAck: "أوافق على البناء بدون التفاصيل الناقصة أعلاه (لن يتم اختلاقها، وسيُحذف الجزء الذي يعتمد عليها)",
    actConfirmMod: "إرسال التغيير للتنفيذ",
    delegateShort: "اختاروا لي",
    convNotReady: "المحادثة الذكية غير متاحة هنا بعد. الأسئلة الموجّهة تعمل كالمعتاد.",
    fallbackNote: "المحادثة الذكية غير متاحة هنا بعد، لذلك انتقلت إلى الأسئلة الموجّهة. تظهر في شاشة \"المتطلبات\" ويتم حفظها.",
    archTitle: "خطة العمل (أقسام ومهام)",
    feasibility: "إمكانية التنفيذ",
    layer: "مرحلة",
    f_FEASIBLE: "قابل للتنفيذ تقنيًا",
    f_FEASIBLE_WITH_CONSTRAINTS: "قابل للتنفيذ تقنيًا مع قيود",
    f_BLOCKED: "متعذّر حاليًا",
    f_UNSUPPORTED: "غير مدعوم بعد",
    f_UNKNOWN: "غير معروف",
    constraints: "قيود",
    ifNeeded: "عند الحاجة",
    tasksTitle: "تفاصيل تقنية: من يفعل ماذا",
    buildRunning: "البناء جارٍ",
    interpreterNote: "تم التفسير وفق قواعد ثابتة (بدون ذكاء اصطناعي)",
    ts_SUCCEEDED: "اكتمل",
    ts_RUNNING: "جارٍ",
    ts_PENDING: "قيد الانتظار",
    ts_READY: "جاهز",
    ts_FAILED: "فشل",
    ts_BLOCKED: "متوقف",
    ts_CANCELLED: "لم يُنفَّذ",
    ts_REPAIRING: "قيد الإصلاح",
    ts_NOT_RECORDED: "لم يُسجَّل",
  },
};

// the platform's languages (the owner, 2026-11-22: "תוצאות בהרבה שפות"); each is named in its own script, sets the
// page direction, and formats dates and numbers. Arabic keeps Latin digits (ar-u-nu-latn), as the rest of the platform.
const LANGS = { he: { name: 'עברית', dir: 'rtl', locale: 'he-IL' }, en: { name: 'English', dir: 'ltr', locale: 'en-GB' },
                ar: { name: 'العربية', dir: 'rtl', locale: 'ar-u-nu-latn' } };
const locale = () => (LANGS[S.lang] || LANGS.he).locale;
const S = {
  lang: (l => (l in LANGS ? l : 'he'))(localStorage.getItem('148ai_lang') || 'he'),
  signedIn: false,
  me: null, projects: [], projectId: localStorage.getItem('148ai_project') || '',
  durable: false, plan: null, build: null, versions: [], previewId: null, preview: null,
  mod: null, timers: {},
};
Object.assign(T.he, { actRetryBuild:'לנסות לבנות שוב', stillMissing:'כדי להמשיך חסר עוד', stillMissingNone:'כדי להמשיך חסרה עוד תשובה אחת בשיחה.', actDescribeInstead:'לתאר אתר או אפליקציה במקום', openRequirements:'לבחירה במסך "דרישות"', updateDraft:'עדכן את התוכנית', editAll:'עריכת הבקשה', minimizeContext:'מזעור החלון',
  colourExample:'למשל: ורוד עדין עם שמנת וזהב', fontSample:'כך ייראה הטקסט באתר שלכם', fontUnavailable:'הדוגמה עדיין לא נטענה',
  guidedMode:'מצב שאלון מובנה — שיחת AI אינה פעילה כרגע', aiMode:'מצב שיחת AI מוגדר — הזמינות תלויה בספק ובתקציב', draftNote:'אפשר לשנות כמה פרטים. רק ״עדכן״ יחיל את השינויים.',
  aiFallback:'התשובה הזו נבנתה מכללים קבועים, בלי מודל בינה מלאכותית.',
  attachmentSchema:'צירוף תמונות עוד לא זמין כאן. התמונה והטקסט נשמרו כאן לניסיון חוזר.' });
Object.assign(T.en, { actRetryBuild:'Try building again', stillMissing:'Still missing before we continue', stillMissingNone:'One more answer is needed in the chat before we continue.', actDescribeInstead:'Describe a site or app instead', openRequirements:'Choose in the "Requirements" tab', updateDraft:'Update the plan', editAll:'Edit requirements', minimizeContext:'Minimize panel',
  colourExample:'For example: soft pink with cream and gold', fontSample:'This is how your website text will look', fontUnavailable:'Preview has not loaded yet',
  guidedMode:'Guided questionnaire — AI conversation is not active right now', aiMode:'AI conversation configured — availability depends on provider and budget', draftNote:'Change as many details as you like. Only Update applies the changes.',
  attachmentSchema:'Image attachments need database migration 038 on this deployment. Your image and text remain here for retry.' });

Object.assign(T.he, {
  workspaceHero: 'מה תרצו ליצור היום?',
  workspaceLead: 'אתרים ואפליקציות מתחילים בשיחה. מאשרים את התוכנית, רואים את התוצאה ומשנים מה שצריך.',
  workspaceCards: 'דרישות, תוכנית ובנייה', workspaceEdit: 'עריכה וסימון', workspaceVersion: 'גרסה שמורה',
  workspaceCost: 'מחיר מוערך',
  workspaceWait: 'ממתין לאישור', workspaceDraft: 'טיוטה',
  workspaceExamples: [['אתר לעסק','אני רוצה אתר לעסק עם פירוט שירותים ודרך קלה ליצור קשר.'],
    ['דף נחיתה','אני רוצה דף נחיתה שמציג הצעה ומאפשר להשאיר פרטים.'],
    ['קטלוג','אני רוצה קטלוג מוצרים עם קטגוריות, תמונות ודרך לשאול על מוצר.']],
  workspaceNavigation: 'סביבת העבודה', allProjects: 'כל הפרויקטים', recentProjects: 'אחרונים',
  workspaceTemplates: 'תבניות', workspaceDomains: 'דומיינים', workspaceSettings: 'הגדרות',
  workspaceStatusFilter: 'מצב הפרויקט', workspaceAllStates: 'כל המצבים',
  workspaceStates: { none: 'עוד לא נבנה', unknown: 'מצב לא זמין', building: 'בבנייה', ready: 'נבנה', failed: 'נכשל', cancelled: 'בוטל' },
  workspaceDomainsNote: 'אפשר לפתוח תצוגה פרטית ולהוריד את התוצר. חיבור דומיין ציבורי יופיע כשהאפשרות תהיה זמינה.',
  workspaceTemplateList: [
    ['אתר לעסק', 'אני רוצה אתר לעסק שלי עם תיאור השירותים ודרך נוחה לפנות אליי מהנייד.'],
    ['דף נחיתה', 'אני רוצה דף נחיתה שמציג את ההצעה ומאפשר להשאיר פרטים.'],
    ['קטלוג', 'אני רוצה קטלוג ברור עם קטגוריות, תמונות ודרך לשאול על מוצר.'],
  ],
});
Object.assign(T.en, {
  workspaceHero: 'What will you create today?',
  workspaceLead: 'Start a site or an app in a chat. Approve the plan, preview the result, and refine it.',
  workspaceCards: 'Requirements, plan and build', workspaceEdit: 'Edit & annotate', workspaceVersion: 'Saved version',
  workspaceCost: 'Estimated price',
  workspaceWait: 'Awaiting approval', workspaceDraft: 'Draft',
  workspaceExamples: [['Business site','I want a business site explaining my services with a simple way to contact me.'],
    ['Landing page','I want a landing page that explains an offer and collects enquiries.'],
    ['Catalogue','I want a catalogue of products with categories, photos and a way to ask about an item.']],
  workspaceNavigation: 'Workspace', allProjects: 'All projects', recentProjects: 'Recent projects',
  workspaceTemplates: 'Templates', workspaceDomains: 'Domains', workspaceSettings: 'Settings',
  workspaceStatusFilter: 'Project status', workspaceAllStates: 'All statuses',
  workspaceStates: { none: 'No build yet', unknown: 'Status unavailable', building: 'Building', ready: 'Built', failed: 'Failed', cancelled: 'Cancelled' },
  workspaceDomainsNote: 'Open a private preview or download your work. Custom domains will appear here when available.',
  workspaceTemplateList: [
    ['Business website', 'I want a website for my business that explains my services and makes it easy to reach me from a phone.'],
    ['Landing page', 'I want a landing page that explains the offer and lets visitors leave their contact details.'],
    ['Catalogue', 'I want a catalogue with categories, photos and a way to ask about a product.'],
  ],
});
// Arabic for the workspace blocks above (2026-11-22, translated and independently reviewed)
Object.assign(T.ar, {
  actRetryBuild: "محاولة البناء مرة أخرى",
  stillMissing: "للمتابعة، ما زال ينقص",
  stillMissingNone: "للمتابعة، ما زالت تنقص إجابة واحدة في المحادثة.",
  actDescribeInstead: "صِفوا موقعًا أو تطبيقًا بدلًا من ذلك",
  openRequirements: "للاختيار في شاشة \"المتطلبات\"",
  updateDraft: "تحديث الخطة",
  editAll: "تعديل الطلب",
  minimizeContext: "تصغير النافذة",
  colourExample: "مثلًا: وردي هادئ مع الكريمي والذهبي",
  fontSample: "هكذا سيبدو النص في موقعكم",
  fontUnavailable: "لم يُحمَّل المثال بعد",
  guidedMode: "وضع الاستبيان الموجَّه — محادثة الذكاء الاصطناعي غير مفعّلة حاليًا",
  aiMode: "تم إعداد وضع محادثة الذكاء الاصطناعي — يعتمد التوفر على الخدمة والميزانية",
  draftNote: "يمكنكم تغيير ما تريدون من التفاصيل. «تحديث» وحده يطبّق التغييرات.",
  attachmentSchema: "إرفاق الصور غير متاح هنا بعد. حُفظت الصورة والنص هنا لتعيدوا المحاولة.",
  workspaceHero: "ماذا تريدون أن تُنشئوا اليوم؟",
  workspaceLead: "المواقع والتطبيقات تبدأ بمحادثة. توافقون على الخطة، وترون النتيجة، وتغيّرون ما يلزم.",
  workspaceCards: "المتطلبات والخطة والبناء",
  workspaceEdit: "التعديل ووضع العلامات",
  workspaceVersion: "نسخة محفوظة",
  workspaceCost: "السعر التقديري",
  workspaceWait: "بانتظار الموافقة",
  workspaceDraft: "مسودة",
  workspaceExamples: [["موقع لنشاط تجاري","أريد موقعًا لنشاط تجاري مع تفصيل للخدمات وطريقة سهلة للتواصل."],["صفحة هبوط","أريد صفحة هبوط تقدّم عرضًا وتتيح ترك البيانات."],["كتالوج","أريد كتالوج منتجات مع فئات وصور وطريقة للسؤال عن منتج."]],
  workspaceNavigation: "مساحة العمل",
  allProjects: "كل المشاريع",
  recentProjects: "الأحدث",
  workspaceTemplates: "القوالب",
  workspaceDomains: "أسماء النطاقات",
  workspaceSettings: "الإعدادات",
  workspaceStatusFilter: "حالة المشروع",
  workspaceAllStates: "كل الحالات",
  workspaceStates: {"none":"لم يُبنَ بعد","unknown":"الحالة غير متاحة","building":"قيد البناء","ready":"تم البناء","failed":"فشل","cancelled":"أُلغي"},
  workspaceDomainsNote: "يمكنكم فتح معاينة خاصة وتنزيل عملكم. سيظهر ربط اسم نطاق عام عندما يصبح هذا الخيار متاحًا.",
  workspaceTemplateList: [["موقع لنشاط تجاري","أريد موقعًا لنشاطي التجاري مع وصف للخدمات وطريقة مريحة للتواصل معي من الهاتف."],["صفحة هبوط","أريد صفحة هبوط تقدّم العرض وتتيح ترك البيانات."],["كتالوج","أريد كتالوجًا واضحًا مع فئات وصور وطريقة للسؤال عن منتج."]],
});

// For everyone (the owner, 2026-11-22: "מקטן שיודע לקרוא ועד למבוגר שלא מבין בכלל"; inbox 001 §6: the number of
// technical terms a person must know to start and finish is zero). These words replace the earlier ones on the entry,
// the first screen, the drawer, the preview and the history; tests/platform_for_everyone_browser.cjs counts the
// technical terms on those screens and fails when one comes back.
Object.assign(T.he, {
  hero: 'תארו במילים שלכם מה אתם צריכים.',
  workspaceLead: 'מספרים במילים פשוטות מה צריך. אנחנו מציעים, אתם מאשרים, ורואים את התוצאה.',
  how1: 'כותבים במילים פשוטות מה אתם צריכים.', how2: 'מקבלים הצעה עם מחיר, ומאשרים רק אם מתאים.',
  how3: 'רואים איך זה נראה, מבקשים שינויים במילים, ושומרים.',
  scope: 'כרגע אפשר לבנות אתרים ומערכות שנפתחים מכל מחשב או טלפון. אפליקציה להתקנה בטלפון, משחקים, וידאו ומוזיקה עוד לא.',
  manage: 'אפשרויות', manageProject: 'אפשרויות הפרויקט', versions: 'היסטוריה', tab_versions: 'היסטוריה', noVersions: 'עוד אין שמירות קודמות.',
  download: 'הורדת הקבצים',
  publishNotConfigured: 'העלאה לאוויר עוד לא זמינה. בינתיים אפשר לראות איך זה נראה ולהוריד את הקבצים.',
  workspaceTemplates: 'רעיונות להתחלה', workspaceDomains: 'כתובת לאתר',
  workspaceDomainsNote: 'בינתיים אפשר לראות את האתר ולהוריד אותו. כתובת משלכם, כמו www.העסק-שלי.co.il, תופיע כאן כשהאפשרות תהיה זמינה.',
  chatHelloTitle: 'מה תרצו ליצור?',
  chatHello: 'כתבו במילים שלכם, כמו שהייתם מספרים לחבר, או לחצו על אחת הדוגמאות. שום דבר לא נבנה ושום חיוב לא קורה בלי האישור שלכם.',
  workspaceExamples: [
    ['אתר לעסק שלי', 'אני רוצה אתר לעסק שלי, עם מה שאני מציע, איפה אני נמצא ואיך יוצרים איתי קשר.'],
    ['קביעת תורים', 'אני רוצה מערכת שבה לקוחות קובעים תור לפי שעות פנויות ומשאירים שם וטלפון.'],
    ['הזמנה לאירוע', 'אני רוצה דף לאירוע, עם תאריך, מקום ואפשרות לאשר הגעה.'],
    ['תיק עבודות', 'אני רוצה עמוד שמציג את העבודות שלי עם תמונות ודרך ליצור איתי קשר.'],
    ['קטלוג מוצרים', 'אני רוצה קטלוג מוצרים עם קטגוריות, תמונות ודרך לשאול על מוצר.'],
    ['דף למבצע', 'אני רוצה דף שמציג מבצע או הצעה ומאפשר להשאיר פרטים.'],
  ],
  textSize: 'גודל טקסט', textSizes: { normal: 'רגיל', large: 'גדול', xlarge: 'גדול מאוד' },
});
Object.assign(T.en, {
  hero: 'Describe what you need in your own words.',
  workspaceLead: 'Say in plain words what you need. We suggest, you approve, and you see the result.',
  how1: 'Write in plain words what you need.', how2: 'Get a proposal with a price, and approve it only if it suits you.',
  how3: 'See how it looks, ask for changes in words, and keep it.',
  scope: 'Today you can make websites and tools that open on any computer or phone. Phone apps to install, games, video and music are not available yet.',
  manage: 'Options', manageProject: 'Project options', versions: 'History', tab_versions: 'History', noVersions: 'Nothing saved earlier yet.',
  download: 'Download the files',
  publishNotConfigured: 'Putting it online is not available yet. Meanwhile you can see how it looks and download the files.',
  workspaceTemplates: 'Ideas to start', workspaceDomains: 'Web address',
  workspaceDomainsNote: 'Meanwhile you can see your site and download it. An address of your own, like www.my-business.com, will appear here when it becomes available.',
  chatHelloTitle: 'What would you like to make?',
  chatHello: 'Write it in your own words, as you would tell a friend, or tap one of the examples. Nothing is built and nothing is charged without your approval.',
  workspaceExamples: [
    ['My business website', 'I want a website for my business with what I offer, where I am and how to reach me.'],
    ['Booking appointments', 'I want a system where customers book an appointment in free time slots and leave their name and phone.'],
    ['Event invitation', 'I want a page for an event with the date, the place and a way to reply that you are coming.'],
    ['My portfolio', 'I want a page that shows my work with photos and a way to contact me.'],
    ['Product catalogue', 'I want a product catalogue with categories, photos and a way to ask about a product.'],
    ['A special offer', 'I want a page that shows a special offer and lets people leave their details.'],
  ],
  textSize: 'Text size', textSizes: { normal: 'Normal', large: 'Large', xlarge: 'Extra large' },
});

// Arabic, the same plain words (2026-11-23). Written by Claude, not yet independently reviewed like the 2026-11-22 block.
Object.assign(T.ar, {
  hero: 'صِفوا بكلماتكم ما تحتاجونه.',
  workspaceLead: 'قولوا بكلمات بسيطة ما تحتاجونه. نحن نقترح، وأنتم توافقون، وترون النتيجة.',
  how1: 'تكتبون بكلمات بسيطة ما تحتاجونه.', how2: 'تحصلون على اقتراح مع السعر، وتوافقون فقط إذا ناسبكم.',
  how3: 'ترون كيف يبدو، وتطلبون التغييرات بالكلمات، وتحفظون.',
  scope: 'يمكن الآن بناء مواقع وأنظمة تُفتح من أي حاسوب أو هاتف. تطبيقات للتثبيت على الهاتف والألعاب والفيديو والموسيقى ليست متاحة بعد.',
  manage: 'خيارات', manageProject: 'خيارات المشروع', versions: 'السجلّ', tab_versions: 'السجلّ', noVersions: 'لا توجد حفظات سابقة بعد.',
  download: 'تنزيل الملفات',
  publishNotConfigured: 'النشر على الإنترنت غير متاح بعد. في هذه الأثناء يمكنكم رؤية كيف يبدو وتنزيل الملفات.',
  workspaceTemplates: 'أفكار للبدء', workspaceDomains: 'عنوان للموقع',
  workspaceDomainsNote: 'في هذه الأثناء يمكنكم رؤية موقعكم وتنزيله. عنوان خاص بكم، مثل www.my-business.com، سيظهر هنا عندما يصبح متاحًا.',
  chatHelloTitle: 'ماذا تريدون أن تصنعوا؟',
  chatHello: 'اكتبوا بكلماتكم، كما لو كنتم تحكون لصديق، أو اضغطوا على أحد الأمثلة. لا يُبنى شيء ولا يُخصم شيء من دون موافقتكم.',
  workspaceExamples: [
    ['موقع لعملي', 'أريد موقعًا لعملي، فيه ما أقدّمه، وأين أنا، وكيف يتواصلون معي.'],
    ['حجز المواعيد', 'أريد نظامًا يحجز فيه الزبائن موعدًا في الأوقات المتاحة ويتركون الاسم والهاتف.'],
    ['دعوة إلى مناسبة', 'أريد صفحة لمناسبة فيها التاريخ والمكان وإمكانية تأكيد الحضور.'],
    ['معرض أعمالي', 'أريد صفحة تعرض أعمالي بالصور وطريقة للتواصل معي.'],
    ['كتالوج منتجات', 'أريد كتالوج منتجات بفئات وصور وطريقة للسؤال عن منتج.'],
    ['صفحة لعرض خاص', 'أريد صفحة تعرض عرضًا خاصًا وتتيح ترك التفاصيل.'],
  ],
  textSize: 'حجم النص', textSizes: { normal: 'عادي', large: 'كبير', xlarge: 'كبير جدًا' },
});

const $ = id => document.getElementById(id);
const t = key => (T[S.lang] && T[S.lang][key]) ?? T.en[key] ?? key;

function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? '' : v);
  }
  for (const kid of kids.flat()) if (kid !== null && kid !== undefined && kid !== false) el.append(kid.nodeType ? kid : String(kid));
  return el;
}

/* ---------- API ---------- */
class ApiError extends Error {
  constructor(status, detail) { super(typeof detail === 'string' ? detail : (detail && (detail.error || detail.reason)) || `HTTP ${status}`); this.status = status; this.detail = detail; }
}
async function api(path, { method = 'GET', body, raw = false } = {}) {
  // The session travels in the HttpOnly cookie set by the server; the token is
  // never readable by or stored in this page.
  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  let res;
  // A request that never answers must not freeze the page (2026-10-08: the
  // change panel kept saying "sent" after the candidate was ready).
  const ctl = typeof AbortController === 'function' ? new AbortController() : null;
  const timer = ctl ? setTimeout(() => ctl.abort(), 125000) : null;
  try { res = await fetch(path, { method, headers, credentials: 'same-origin', signal: ctl ? ctl.signal : undefined, body: body === undefined ? undefined : JSON.stringify(body) }); }
  catch (e) { throw new ApiError(0, e && e.name === 'AbortError' ? 'timeout' : t('errNet')); }
  finally { if (timer) clearTimeout(timer); }
  if (raw && res.ok) return res;
  let data = null;
  const text = await res.text();
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!res.ok) {
    const detail = data && typeof data === 'object' && 'detail' in data ? data.detail : data;
    if (res.status === 401 && S.signedIn) signOutLocal();
    throw new ApiError(res.status, detail);
  }
  return data;
}
function explain(err) {
  if (!(err instanceof ApiError)) return String(err && err.message || err);
  const msg = err.message || '';
  if (err.status === 402 && err.detail && err.detail.error === 'plan_cannot_authorize_cost') return t('errPlanNotIncluded');
  if (err.status === 402 && err.detail && err.detail.error === 'build_allowance_exhausted') return t('errAllowanceExhausted');
  // A 401 on the sign-in screen means wrong credentials, not an expired session.
  if (err.status === 401 && !S.signedIn) return t('errBadCreds');
  if ((err.status === 400 || err.status === 409) && /already exists/i.test(msg)) return t('errAccountExists');
  if (err.detail && err.detail.code === 'project_limit_reached') {
    const used = Number(err.detail.active_projects);
    const max = Number(err.detail.max_projects);
    const count = Number.isFinite(used) && Number.isFinite(max) ? ` (${used}/${max})` : '';
    return S.lang === 'he'
      ? 'הגעתם למכסת הפרויקטים הפעילים' + count + '. ניתן לארכב פרויקט קיים או לשנות תוכנית. זו לא בעיה של יתרה.'
      : S.lang === 'ar'
        ? 'وصلتم إلى الحد الأقصى للمشاريع النشطة' + count + '. يمكنكم أرشفة مشروع قائم أو تغيير الخطة. هذه ليست مشكلة في الرصيد.'
        : 'Active project limit reached' + count + '. Archive an existing project or change plan. This is not a balance issue.';
  }
  if (err.detail && err.detail.error === 'attachments_not_ready') return t('attachmentSchema');
  if (err.detail && err.detail.error === 'capability_not_feasible') return capabilityBlockMessage(err.detail);
  if (err.detail && ['spec_not_approved', 'plan_not_verified', 'approval_state_unavailable', 'brief_stale'].includes(err.detail.error))
    return t(`b_${err.detail.error}`);     // a human sentence, never the server's English (the status stays 409)
  const said = err.detail && typeof err.detail.error === 'string' ? (t('serverSaid') || {})[err.detail.error] : null;
  if (said) return said;                    // plain words in the customer's language, never the server's English sentence
  switch (err.status) {
    case 0: return err.detail === 'timeout' ? t('errTimeout') : t('errNet');
    case 401: return t('err401');
    case 402: return t('err402') + msg;
    case 403: return t('err403');
    case 404: return t('err404');
    case 409: return (err.detail && err.detail.message) || t('err409');
    case 422: return (err.detail && err.detail.message) || msg;
    case 503: return (err.detail && err.detail.error === 'conversation_not_ready') ? t('convNotReady')
      : (err.detail && err.detail.message) || (t('err503') + msg);
    default: return err.status >= 500 ? t('err5xx') : msg;
  }
}
const pid = () => encodeURIComponent(S.projectId);

/* ---------- text size (the owner, 2026-11-22: readable for an older person too) ---------- */
// Three sizes, kept on this device. The whole page is sized in rem, so the root size scales every text.
const TEXT_SIZES = ['normal', 'large', 'xlarge'];
let currentTextSize = (() => {
  try { const s = localStorage.getItem('148ai_text'); return TEXT_SIZES.includes(s) ? s : 'normal'; }
  catch { return 'normal'; }          // private mode: the size still changes, it is just not kept after a reload
})();
function applyTextSize() {
  document.documentElement.dataset.text = currentTextSize;
  for (const b of [$('textSizeBtn'), $('textSizeBtn2')]) if (b) b.textContent = `${t('textSize')}: ${t('textSizes')[currentTextSize]}`;
}
function nextTextSize() {
  currentTextSize = TEXT_SIZES[(TEXT_SIZES.indexOf(currentTextSize) + 1) % TEXT_SIZES.length];
  try { localStorage.setItem('148ai_text', currentTextSize); } catch { /* see above */ }
  applyTextSize();
}

/* ---------- language ---------- */
function applyLang() {
  document.documentElement.lang = S.lang;
  document.documentElement.dir = (LANGS[S.lang] || LANGS.he).dir;
  document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll('[data-i18n-label]').forEach(el => { el.setAttribute('aria-label', t(el.dataset.i18nLabel)); el.title = t(el.dataset.i18nLabel); });
  if ($('passwordToggle')) { const label = t($('password').type === 'password' ? 'showPassword' : 'hidePassword'); $('passwordToggle').setAttribute('aria-label', label); $('passwordToggle').title = label; }
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => { el.placeholder = t(el.dataset.i18nPlaceholder); });
  for (const pick of [$('langBtn'), $('langBtn2')]) {
    if (!pick.options.length) pick.append(...Object.entries(LANGS).map(([code, l]) => h('option', { value: code, lang: code, dir: l.dir }, l.name)));
    pick.value = S.lang;
  }
  $('chatInput').placeholder = t('chatPlaceholder');
  applyTextSize();
  $('publishNote').textContent = t('publishNotConfigured');
  document.title = t('docTitle');
  renderBanner(); renderDiscovery(); renderPlan(); renderTrack(); renderVersions(); renderEvidence(); renderPreview(); renderMod();
  renderProjects(); renderWorkspaceBalance(); renderChat(); renderArch(); renderTabs(); syncStageButtons();
  if (window.VE) VE.render();
}

/* ---------- auth ---------- */
function signOutLocal() {
  S.signedIn = false; S.me = null;
  S.projects = []; projectBuildStates.clear(); projectDrafts.clear(); projectStateRequests.clear();
  S.lastShownProject = null;
  $('chatInput').value = ''; $('followup').value = ''; $('sbSearch').value = '';
  if ($('workspaceDialog').open) $('workspaceDialog').close();
  $('sbSettings').open = false;
  closeSidebarMobile();
  renderProjects();
  Object.values(S.timers).forEach(clearTimeout); S.timers = {};
  showView();
}
async function authSubmit(kind) {
  const email = $('email').value.trim(), password = $('password').value;
  const msg = $('authMsg'); msg.className = 'msg'; msg.textContent = '';
  if (!email.includes('@') || password.length < 10) { msg.textContent = t('needEmail'); return; }
  try {
    const path = kind === 'register' ? '/api/v28/auth/register' : '/api/v28/auth/login';
    await api(path, { method: 'POST', body: { email, password } });
    $('password').value = '';
    $('password').type = 'password';
    $('passwordToggle').setAttribute('aria-pressed', 'false');
    $('passwordToggle').setAttribute('aria-label', t('showPassword'));
    await enterWorkspace();
  } catch (e) {
    msg.textContent = explain(e);
    const exists = e instanceof ApiError && [400, 409].includes(e.status)
      && /already exists/i.test(String(e.message || ''));
    if (kind === 'register' && exists) {
      $('authTitle').textContent = t('signinTitle');
      $('email').focus();
    }
  }
}
async function logout() {
  try { await api('/api/v28/auth/logout', { method: 'POST' }); } catch { /* local sign-out still happens */ }
  signOutLocal();
}

/* ---------- views ---------- */
function showView() {
  const signedIn = Boolean(S.signedIn && S.me);
  $('welcomeView').hidden = signedIn;
  $('workspaceView').hidden = !signedIn;
  $('accountBox').hidden = !signedIn;
  document.body.classList.toggle('signed-in', signedIn);
  document.body.classList.toggle('signed-out', !signedIn);
  if (signedIn) {
    const unverified = S.me.email_verified === false ? ` (${t('emailUnverified')})` : '';
    $('accountEmail').textContent = S.me.email + unverified;
    $('sbEmail').textContent = S.me.email + unverified;
    renderWorkspaceBalance();
  }
  renderBanner();
}
function renderBanner() {
  const b = $('backendBanner');
  const show = Boolean(S.me) && !S.durable;
  b.hidden = !show;
  if (show) b.innerHTML = t('backendMissing'); // static copy from T, no user data
}
async function loadStatus() {
  try { const s = await api('/api/v28/m5/status'); S.durable = !(s.blockers || []).includes('durable_postgres_s3_backend_required'); }
  catch { S.durable = false; }
}
async function enterWorkspace() {
  S.me = await api('/api/v28/me');
  S.signedIn = true;
  await loadStatus();
  showView();
  await loadProjects();
}

/* ---------- projects ---------- */
async function loadProjects() {
  const d = await api('/api/v28/projects');
  S.projects = (d.projects || []).filter(p => !p.archived_at && p.status !== 'ARCHIVED');
  if (!S.projects.find(p => p.id === S.projectId)) S.projectId = S.projects[0] ? S.projects[0].id : '';
  renderProjects();
  await selectProject(S.projectId);
}
function renderProjects() {
  const sel = $('projectSelect');
  sel.replaceChildren(...S.projects.map(p => h('option', { value: p.id, selected: p.id === S.projectId }, p.title || t('untitled'))));
  // the owner, 2026-11-22: nobody is asked to name a project before saying what they want. The conversation box is
  // always there; the first message creates the project and names it (submitChat, titleFrom).
  $('projectMenuBtn').disabled = !S.projectId;
  renderSidebarProjects();
  const cur = S.projects.find(p => p.id === S.projectId);
  const title = cur ? (cur.title || t('untitled')) : S.projects.length ? t('newProject') : '148AI';
  $('chatTitle').textContent = title;
  renderWorkspaceHeader();
}
const projectBuildStates = new Map();
const projectDrafts = new Map();
function renderWorkspaceBalance() {
  const credits = S.me?.subscription?.credits_remaining;
  const balance = $('sbBalance');
  balance.hidden = !Number.isFinite(credits);
  balance.textContent = balance.hidden ? '' : `${t('creditsRemaining')} · ${new Intl.NumberFormat(locale()).format(credits)}`;
}
async function refreshWorkspaceBalance() {
  const account = S.me;
  if (!account) return;
  try {
    const subscription = await api('/api/v28/me/subscription');
    if (S.me !== account) return;
    account.subscription = subscription;
    renderWorkspaceBalance();
  } catch { /* Keep the last balance returned for this account. */ }
}
function projectStatus(p) {
  const status = String(projectBuildStates.get(p.id) ?? p.last_build_status ?? '').toLowerCase();
  if (['queued', 'running', 'building'].includes(status)) return 'building';
  return ['none', 'ready', 'failed', 'cancelled'].includes(status) ? status : 'unknown';
}
// review F2 (2026-11-22): GET /api/v28/projects carries no build status, so every project not opened in this session read
// "status unavailable" and the status filter missed it. The latest build of each listed project is read once per
// session -- at most 30 projects, 3 requests at a time; a project whose status cannot be read stays "unavailable".
const projectStateRequests = new Set();
async function loadProjectStates(projects) {
  const queue = projects.filter(p => !projectBuildStates.has(p.id) && !p.last_build_status && !projectStateRequests.has(p.id)).slice(0, 30);
  if (!queue.length || !S.signedIn) return;
  queue.forEach(p => projectStateRequests.add(p.id));
  let changed = false;
  const worker = async () => {
    for (let p = queue.shift(); p; p = queue.shift()) {
      try {
        const d = await api(`/api/v28/projects/${encodeURIComponent(p.id)}/builds/latest`);
        if (d && 'build' in d) { projectBuildStates.set(p.id, d.build ? String(d.build.status || '').toLowerCase() : 'none'); changed = true; }
      } catch { /* stays "status unavailable": said, not guessed */ }
    }
  };
  await Promise.all([worker(), worker(), worker()]);
  if (!changed) return;
  renderSidebarProjects();
  if ($('workspaceDialog').open && $('workspaceProjectList')) renderProjectCatalogue();
}
function rememberBuildState(status) {
  if (!S.projectId || projectBuildStates.get(S.projectId) === status) return;
  projectBuildStates.set(S.projectId, status);
  renderSidebarProjects();
  if ($('workspaceDialog').open && $('workspaceProjectList')) renderProjectCatalogue();
}
function orderedProjects(query) {
  const q = query.trim().toLocaleLowerCase();
  return S.projects.filter(p => (p.title || t('untitled')).toLocaleLowerCase().includes(q))
    .sort((a, b) => String(b.updated_at || b.created_at || '').localeCompare(String(a.updated_at || a.created_at || '')));
}
function showProjectRows(list, projects) {
  const focusedId = list.contains(document.activeElement) ? document.activeElement.dataset.project : null;
  list.replaceChildren(...projects.map(p => {
    const status = projectStatus(p);
    const title = p.title || t('untitled');
    return h('li', {}, h('button', { type: 'button', 'data-project': p.id, title,
      'aria-current': p.id === S.projectId ? 'true' : 'false', onclick: () => {
        if ($('workspaceDialog').open) $('workspaceDialog').close();
        closeSidebarMobile();
        if (p.id !== S.projectId) selectProject(p.id);
      } },
      h('span', { class: 'ttl', dir: 'auto' }, title),
      h('span', { class: 'sbStatus' }, t('workspaceStates')[status])));
  }));
  if (!projects.length) list.append(h('li', { class: 'hint' }, t('noMatches')));
  if (focusedId) Array.from(list.querySelectorAll('button')).find(button => button.dataset.project === focusedId)?.focus();
}
function renderSidebarProjects() {
  const query = $('sbSearch').value;
  const projects = orderedProjects(query);
  const shown = query.trim() ? projects : projects.slice(0, 5);
  showProjectRows($('sbProjects'), shown);
  loadProjectStates(shown);
}
function renderProjectCatalogue() {
  const status = $('workspaceProjectState').value;
  const projects = orderedProjects($('workspaceProjectSearch').value);
  showProjectRows($('workspaceProjectList'), projects.filter(p => !status || projectStatus(p) === status));
  loadProjectStates(projects);
}
function openWorkspaceDialog(view) {
  closeSidebarMobile();
  const body = $('workspaceDialogBody');
  $('workspaceDialogTitle').textContent = t(view);
  if (view === 'allProjects') {
    body.replaceChildren(
      h('input', { id: 'workspaceProjectSearch', type: 'search', 'aria-label': t('searchProjects'),
        placeholder: t('searchProjects'), value: $('sbSearch').value, oninput: renderProjectCatalogue }),
      h('button', { type: 'button', class: 'workspaceNew', onclick: () => {
        $('workspaceDialog').close();
        openNewProject();
      } }, t('newProject')),
      h('label', {}, t('workspaceStatusFilter'), h('select', { id: 'workspaceProjectState', onchange: renderProjectCatalogue },
        h('option', { value: '' }, t('workspaceAllStates')),
        Object.entries(t('workspaceStates')).map(([value, label]) => h('option', { value }, label)))),
      h('ul', { id: 'workspaceProjectList', class: 'sbList' }));
    renderProjectCatalogue();
  } else if (view === 'workspaceTemplates') {
    body.replaceChildren(...t('workspaceTemplateList').map(([name, prompt]) =>
      h('button', { type: 'button', class: 'ghost', onclick: () => {
        $('workspaceDialog').close();
        openNewProject(null, prompt);
      } }, name)));
  } else {
    body.replaceChildren(h('p', {}, t('workspaceDomainsNote')));
  }
  $('workspaceDialog').showModal();
  $('workspaceProjectSearch')?.focus();
}
async function createProject(title) {
  const p = await api('/api/v28/projects', { method: 'POST', body: { title: title || t('untitled') } });
  S.projectId = p.id;
  await loadProjects();
  // A new project starts with an empty conversation (selectProject cleared the
  // box before loading); never clear again here -- the user may already be typing.
  $('chatInput').focus();
}
// A new project is an empty conversation, as in every product of its kind (the owner, 2026-11-22): no name is asked.
// The first message creates the project and names it; the name can be changed later under "Options". An idea from
// "Ideas to start" is written into the box for the customer to read, change and send.
async function openNewProject(_event, prompt = '') {
  closeSidebarMobile();
  if ($('workspaceDialog').open) $('workspaceDialog').close();
  await selectProject('');
  if (typeof prompt === 'string' && prompt) { $('chatInput').value = prompt; autoGrow(); }
  $('chatInput').focus();
}
// The project's name, from the customer's first message: its first phrase without "I want", at most 40 characters.
const TITLE_LEADS = [/^(אני\s+)?(רוצה|צריך|צריכה|מחפש|מחפשת)\s+/, /^(תבנו|בנו|תעשו|עשו)\s+לי\s+/,
  /^i\s+(want|need|would like)\s+(to\s+have\s+)?/i, /^(please\s+)?(build|make|create)\s+(me\s+)?/i];
function titleFrom(text) {
  let one = String(text || '').replace(/\s+/g, ' ').trim();
  for (const lead of TITLE_LEADS) one = one.replace(lead, '');
  one = (one.split(/[,.;:!?\n]/)[0] || '').trim();
  if (!one) return t('untitled');
  if (one.length <= 40) return one;
  const cut = one.slice(0, 40), space = cut.lastIndexOf(' ');
  return `${space > 20 ? cut.slice(0, space) : cut}…`;
}
async function selectProject(id) {
  Object.values(S.timers).forEach(clearTimeout); S.timers = {};
  if (S.lastShownProject && S.lastShownProject !== id) {
    const draft = $('chatInput').value;
    const sending = S.inFlight && S.inFlight.project === S.lastShownProject && S.inFlight.text === draft.trim();
    if (draft && !sending) projectDrafts.set(S.lastShownProject, draft);
    else projectDrafts.delete(S.lastShownProject);
  }
  S.projectId = id || ''; localStorage.setItem('148ai_project', S.projectId);
  S.plan = null; S.build = null; S.buildAdmissionError = ''; S.preview = null; S.previewId = null; S.mod = null; S.versions = []; S.newBuildOpen = false;
  S.disc = null; S.editQ = null; S.editDraft = null; S.chatRetry = null; S.answerRetry = null; S.chat = null; S.arch = null; S.tasks = null; S.tab = null;
  if (S.projectId !== S.lastShownProject) { $('chatInput').value = projectDrafts.get(S.projectId) || ''; autoGrow(); $('followup').value = ''; $('composerMsg').textContent = ''; }
  S.lastShownProject = S.projectId;
  $('planPanel').hidden = true; $('progressPanel').hidden = true;
  Object.assign(S, {proposal:null, proposalUndo:null, proposalOpen:null, proposalWindows:null, proposalLoad:null, planRequest:null});
  $('versionNotice').textContent = '';
  window.VE?.setPane('chat');
  resetBuildPanel();
  S.lastChange = null;
  if (window.VE) VE.reset();
  applyLang();
  if (!S.projectId) return;
  await loadVersions();
  await restoreMod();
  await restoreConversation();
  await restoreBuild();
}
/* Michael 2026-11-13 (production, a new project "מאפייה"): the build tab showed the live log of ANOTHER project's
   run from the night before. The server reads every build by project; the stale lines were the previous project's
   DOM, never cleared on a project switch, and a slow response for the previous project could still land after the
   switch. Every panel is cleared on a switch, and a response for another project is dropped. */
function resetBuildPanel() {
  for (const id of ['track', 'taskBoard', 'liveLogList']) $(id).replaceChildren();
  $('buildMsg').textContent = ''; $('buildMsg').className = 'msg';
  $('buildControls').hidden = true; $('liveLog').hidden = true;
}
const stillOn = project => S.projectId === project;
// A build that is still queued/running survives a reload: its track, live log
// and stop button come back (directive 2026-10-09 §12).
async function restoreBuild() {
  const project = S.projectId;
  try {
    const d = await api(`/api/v28/projects/${pid()}/builds/latest`);
    if (!stillOn(project)) return;
    const b = d && d.build;
    if (!S.build && d && 'build' in d) rememberBuildState(b ? b.status : 'none');
    if (!b || S.build) { renderLog(); return; }
    if (isTerminal(b.status)) {
      // 2026-11-09: a finished build (its result, failure reason and the founder's draft) is shown again after a
      // reload instead of disappearing. Read once; no polling and no automatic preview start.
      const full = await api(`/api/v28/projects/${pid()}/builds/${encodeURIComponent(b.build_id)}`);
      if (S.build || !stillOn(project)) return;
      S.build = { id: b.build_id, ...full };
      await pollEvents();
      renderTrack(); renderEvidence(); renderPlan();
      return;
    }
    S.build = { id: b.build_id, status: b.status, phase: '', evidence: {} };
    renderTrack(); renderPlan(); pollBuild();
  } catch (e) { /* older server: nothing to restore */ }
}

/* ---------- plan + quote ---------- */
/* ---------- discovery conversation (directive 2026-10-09 §4-5) ---------- */
const newKey = () => (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random()).slice(0, 60);
const discPath = () => `/api/v28/projects/${pid()}/discovery`;
/* The old "describe + choose a mode" composer is replaced by the conversation
   (Unified Conversation OS): the supervisor decides how many questions to ask. */
// warehouse 113 (owner 2026-11-16): "update the plan" either moves on (the plan is requested) or says what is still
// missing, by name -- never a silent return to the tab.
function stillMissingLine(disc) {
  if (!disc || disc.complete) return '';
  const names = (disc.questions || []).map(q => q.text).filter(Boolean);
  return names.length ? `${t('stillMissing')}: ${names.join(' · ')}` : t('stillMissingNone');
}
async function sendAnswers(answers, { editing = false } = {}) {
  if(S.updatingAnswers)return;
  const retrySignature=JSON.stringify([S.projectId,S.disc.brief.revision,answers]);
  if(!S.answerRetry || S.answerRetry.signature!==retrySignature)S.answerRetry={signature:retrySignature,key:newKey()};
  const msg = $('discMsg'); if (msg) msg.textContent = '';
  try {
    S.updatingAnswers = true;
    if($('updateBriefBtn'))$('updateBriefBtn').disabled=true;
    // Edits made in the requirements panel go through the same conversation,
    // so the project history records them (the brief stays the source of truth).
    if (S.chat && S.chat.fallback) {
      S.disc = await api(`${discPath()}/answers?lang=${S.lang}`, { method: 'POST',
        body: { revision: S.disc.brief.revision, answers, request_key: S.answerRetry.key } });
      renderChat();
    } else {
      applyConversation(await api(`/api/v28/projects/${pid()}/conversation?lang=${S.lang}`, { method: 'POST',
        body: { answers, brief_revision:S.disc.brief.revision, request_key: S.answerRetry.key } }));
    }
    S.answerRetry=null;
    S.editQ = null; if (editing) S.editDraft = null; S.plan = null; renderPlan();
    renderDiscovery();
    if (S.disc.complete) await requestBriefPlan();
    else { openTab('req'); const m = $('discMsg'); if (m) m.textContent = stillMissingLine(S.disc); }   // warehouse 113
  } catch (e) {
    if (e.status === 409) { try { S.disc = await api(`${discPath()}?lang=${S.lang}`); renderDiscovery(); } catch { /* keep message */ } }
    const m = $('discMsg'); if (m) m.textContent = explain(e);
  } finally { S.updatingAnswers = false; if($('updateBriefBtn'))$('updateBriefBtn').disabled=false; }
}
function beginBriefEdit() {
  if (!S.disc) return;
  S.editDraft = S.editDraft || {};
  S.editQ = null;
  renderDiscovery(); openTab('req');
}
async function requestBriefPlan(open = true) {
  if (!S.disc || !S.disc.complete) return;
  const request = {};
  const briefRevision = S.disc.brief.revision;
  S.planRequest = request;
  const current = () => S.planRequest === request && S.disc?.brief?.revision === briefRevision;
  try {
    const plan = await api(`/api/v28/projects/${pid()}/build-contracts?lang=${S.lang}`, { method: 'POST',
      body: { prompt: S.disc.prompt, brief_revision: briefRevision } });
    if (!current()) return;
    S.plan = plan;
    // 2026-11-09: the background quote fetched while a project opens (open=false) resolved AFTER restoreBuild()
    // and wiped the queued/running build from the screen. Only a plan the user asked for replaces a finished build;
    // a queued or running build always stays.
    if (open === true && (!S.build || isTerminal(S.build.status))) S.build = null;
    await loadProposal();
    if (!current()) return;
    renderDiscovery(); renderPlan(); renderTrack(); if (open === true) openTab('plan');
  } catch (e) {
    const message = $('discMsg');
    if (current() && message) message.textContent = explain(e);
  }
}
function questionCard(q, current) {
  const name = `q_${q.id}`;
  const chosen = current !== undefined ? current : (q.suggested || '');
  const kids = [h('legend', {}, q.text), h('p', { class: 'hint' }, t('why') + q.why)];
  if (q.id === 'font') {
    const fonts = {heebo:'Heebo', assistant:'Assistant', rubik:'Rubik', system:'system-ui'};
    const picker = h('details', {class:'fontPicker'}, h('summary', {}, (q.options.find(o => o.value === chosen) || {}).label || t('delegate')));
    const list = h('div', {class:'fontOptions'});
    for (const o of q.options) {
      const sample = h('span', {class:`fontSample font-${o.value}`}, t('fontSample'));
      const note = h('small', {class:'hint'}, o.value === 'system' ? '' : t('fontUnavailable'));
      const input = h('input', {type:'radio',name,value:o.value,checked:o.value===chosen,
        onchange:()=>{picker.querySelector('summary').textContent=o.label;}});
      list.append(h('label', {class:'opt fontOption'}, input, h('span', {}, o.label, sample, note)));
      if (o.value !== 'system' && document.fonts) document.fonts.load(`16px "${fonts[o.value]}"`).then(loaded=>{
        if(loaded.length){note.textContent='';sample.classList.add('loaded');}
      }).catch(()=>{});
    }
    picker.append(list); kids.push(picker);
  } else if (q.kind === 'choice') {
    for (const o of q.options) {
      kids.push(h('label', { class: 'opt' }, h('input', { type: 'radio', name, value: o.value, checked: o.value === chosen }),
        h('span', {}, o.label, (q.suggested === o.value && current === undefined) ? h('small', {}, ' ' + t('suggestedFromRequest')) : null)));
    }
  } else {
    kids.push(h('textarea', { name, rows: 2, maxlength: 2000, placeholder: q.id === 'color' ? t('colourExample') : q.recommended || '' }, chosen && chosen !== '__delegate__' ? chosen : ''));
  }
  if (q.delegable) {
    const rec = q.kind === 'choice' ? ((q.options.find(o => o.value === q.recommended) || {}).label || '') : (q.recommended || '');
    kids.push(h('label', { class: 'opt delegate' }, h('input', { type: 'radio', name: q.kind === 'choice' ? name : `${name}_d`, value: '__delegate__', checked:chosen==='__delegate__' }),
      h('span', {}, t('delegate'), rec ? h('small', {}, ' ' + t('delegateWill')(rec)) : null)));
  }
  return h('fieldset', { class: 'question', 'data-q': q.id, 'data-kind': q.kind, 'data-delegable': q.delegable ? '1' : '' }, kids);
}
function collectAnswers(root, { skip = false } = {}) {
  const answers = {}; const missing = [];
  for (const fs of root.querySelectorAll('fieldset.question')) {
    const id = fs.dataset.q;
    let v = '';
    if (fs.dataset.kind === 'choice') {
      const c = fs.querySelector('input[type=radio]:checked'); v = c ? c.value : '';
    } else {
      const d = fs.querySelector(`input[name="q_${id}_d"]:checked`);
      v = d ? '__delegate__' : (fs.querySelector('textarea').value || '').trim();
    }
    if (skip && fs.dataset.delegable) v = '';
    if (!v && !fs.dataset.delegable) missing.push(fs.querySelector('legend').textContent);
    answers[id] = v;
  }
  return { answers, missing };
}
function renderDiscovery() {
  const panel = $('discoveryPanel'); const d = S.disc;
  if (!d) { panel.hidden = true; return; }
  panel.hidden = false;
  const kids = [h('h2', {}, t('discTitle')),
    h('p', { class: 'hint' }, t('discProgress')(d.progress.answered, d.progress.remaining))];
  const editing = S.editDraft !== null && S.editDraft !== undefined;
  if (editing) {
    const form = h('form', { class: 'qgroup', onsubmit: e => { e.preventDefault();
      const { answers, missing } = collectAnswers(form);
      if (missing.length) { $('discMsg').textContent = t('needAnswer')(missing[0]); return; }
      const changes=Object.fromEntries(Object.entries(answers).filter(([k,v])=>{
        const old=d.answered.find(a=>a.id===k);return !old || v!==old.value;
      }));
      if(Object.keys(changes).length) sendAnswers(changes,{editing:true});
      else {S.editDraft=null;renderDiscovery();requestBriefPlan(true);} } },
      h('p', {class:'hint'}, t('draftNote')),
      ...d.answered.map(a=>questionCard(a, Object.hasOwn(S.editDraft,a.id)?S.editDraft[a.id]:a.value)),
      h('div', { class: 'row draftActions' }, h('button', { id:'updateBriefBtn',type: 'submit' }, t('updateDraft')),
        h('button', { type: 'button', class: 'ghost', onclick: () => { S.editDraft = null; renderDiscovery(); openTab(S.plan?'plan':'req'); } }, t('cancel'))));
    const remember=()=>{S.editDraft=collectAnswers(form).answers;};
    form.addEventListener('input',remember);form.addEventListener('change',remember);
    kids.push(form);
  } else if (!d.complete && d.questions.length && (!S.chat || S.chat.fallback)) {
    const form = h('form', { class: 'qgroup', onsubmit: e => { e.preventDefault();
      const { answers, missing } = collectAnswers(form);
      if (missing.length) { $('discMsg').textContent = t('needAnswer')(missing[0]); return; }
      sendAnswers(answers); } },
      h('h3', {}, d.group_title), ...d.questions.map(q => questionCard(q)),
      h('div', { class: 'row' }, h('button', { type: 'submit' }, t('next')),
        h('button', { type: 'button', class: 'ghost', onclick: () => {
          const { answers, missing } = collectAnswers(form, { skip: true });
          if (missing.length) { $('discMsg').textContent = t('needAnswer')(missing[0]); return; }
          sendAnswers(answers); } }, t('skipGroup'))),
      h('p', { class: 'hint' }, t('pauseNote')));
    kids.push(form);
  } else if (d.complete) {
    kids.push(h('p', { class: 'msg ok' }, t('discDone')));
    if (!S.plan) kids.push(h('div', { class: 'row' }, h('button', { onclick: () => requestBriefPlan(true) }, t('showSummary'))));
  }
  if (d.answered.length) {
    kids.push(h('details', { class: 'decided', open: d.complete && !S.plan ? true : null }, h('summary', {}, t('decided')),
      h('ul', { class: 'answers' }, d.answered.map(a => h('li', {},
        h('span', { class: 'q' }, a.text), h('b', {}, a.value_label),
        h('span', { class: `pill ${a.source === 'answer' ? 'ok' : 'muted'}` }, t(`src_${a.source}`)),
        h('button', { type: 'button', class: 'ghost', onclick: beginBriefEdit }, t('change')))))));
  }
  kids.push(h('p', { class: 'msg', id: 'discMsg', role: 'alert' }));
  panel.replaceChildren(...kids);
}
function pill(status) {
  const cls = { LIVE: 'ok', SELF_CONTAINED: 'ok', PRICED: 'ok', PARTIAL: 'warn', UNKNOWN: 'warn', NOT_CONFIGURED: 'bad', BLOCKED: 'bad', NOT_AUTHORIZED: 'bad' }[status] || 'muted';
  return h('span', { class: `pill ${cls}` }, t(`st_${status}`) || status || '—');
}
const money = v => (v === null || v === undefined) ? t('costUnknown') : `$${Number(v).toFixed(2)}`;
function renderWorkspaceHeader() {
  const build = S.build?.status?.toLowerCase();
  const code = build === 'ready' ? 'ready' : build === 'failed' ? 'failed' : build && !isTerminal(build) ? 'building' : build === 'cancelled' ? 'cancelled' : null;
  const state = code ? t('workspaceStates')[code] : S.plan?.can_build ? t('workspaceWait') : t('workspaceDraft');
  const estimate = proposalPrice(S.proposal?.price);
  const chip = $('workspaceProjectChip');
  chip.hidden = !S.projectId;
  chip.dataset.state = code || 'draft';
  chip.textContent = estimate ? `${state} · ${t('workspaceCost')} ${estimate.amount}` : state;
}

function renderProjectReadiness() {
  renderWorkspaceHeader();
  const strip = $('projectReadiness');
  if (!strip) return;
  strip.hidden = !S.projectId;
  if (!S.projectId) return;
  const p = S.plan;
  const { mode, label } = readinessView(S.build, p);
  strip.className = 'projectReadiness ' + mode;
  strip.replaceChildren(h('span', { class:'readinessLabel' }, label),
    h('button', { type:'button', onclick: () => openTab(p ? 'plan' : 'req') }, t('readinessDetails')));
}
// Michael 2026-11-14 (butcher): after a successful build the strip said "לא ניתן להתחיל בבנייה כרגע: <reason>" in
// red beside "הבנייה הסתיימה בהצלחה". The refusal is about ANOTHER build: it is said so, and never in the failure colour.
function readinessView(build, p) {
  const busy = build && !isTerminal(build.status);
  const built = !busy && build && String(build.status).toLowerCase() === 'ready';
  // 79: a blocked build names its ONE reason (server-chosen from a closed list), never only the generic line.
  const why = p && !p.can_build && p.blocked_reason ? p.blocked_reason.message : '';
  if (built) {
    return { mode: 'built', label: why ? `${t('readinessBuilt')}. ${t('readinessNextBlocked')}: ${why}` : t('readinessBuilt') };
  }
  const mode = busy ? 'running' : !p ? 'unknown' : p.can_build ? 'ready' : 'blocked';
  const label = busy ? t('readinessRunning') : !p ? t('readinessUnknown') :
    p.can_build ? t('readinessReady') : (why ? `${t('readinessBlocked')}: ${why}` : t('readinessBlocked'));
  return { mode, label };
}
/* ---------- first agent: the proposal card (docs/spec/first-agent.md 1, 7) ---------- */
const proposalPath = () => `/api/v28/projects/${pid()}/proposal`;
async function loadProposal() {
  const load = {};
  S.proposalLoad = load;
  let proposal;
  try { proposal = await api(proposalPath()); } catch { proposal = null; }
  if (S.proposalLoad !== load) return;
  S.proposal = proposal;
  renderWorkspaceHeader();
}
// The price line: always shown, always an estimate (Michael 2026-11-15: the price never blocks).
function proposalPrice(price) {
  if (!price || typeof price.amount_ils !== 'number') return null;
  return { amount: `${price.amount_ils} ₪`, label: t('propEstimate'), basis: price.basis || '' };
}
async function proposalEdit(op, key, value) {
  const pr = S.proposal; if (!pr) return;
  const project = S.projectId;
  try {
    const out = await api(`${proposalPath()}/edit`, { method: 'POST', body: { revision: pr.revision, op, key, value } });
    if (!stillOn(project)) return;
    S.proposal = out.proposal; S.proposalUndo = out.undo; S.proposalOpen = null;
    S.plan = null; await requestBriefPlan(true);            // a new structure is a new fingerprint: a new plan
  } catch (e) { const m = $('propMsg'); if (m) m.textContent = explain(e); }
}
async function proposalUndo() {
  if (!S.proposalUndo) return;
  const project = S.projectId;
  try {
    const out = await api(`${proposalPath()}/undo`, { method: 'POST', body: { undo: S.proposalUndo } });
    if (!stillOn(project)) return;
    S.proposal = out.proposal; S.proposalUndo = null;
    S.plan = null; await requestBriefPlan(true);
  } catch (e) { const m = $('propMsg'); if (m) m.textContent = explain(e); }
}
// One button: approve THIS spec (its fingerprint) and start the build -- not two approvals on the same thing.
async function approveAndBuild() {
  const pr = S.proposal; if (!pr || !pr.ok) return;
  const m = $('propMsg'); if (m) m.textContent = t('propApproving');
  try {
    applyConversation(await api(specApprovalPath(), { method: 'POST',
      body: { brief_fingerprint: pr.brief_fingerprint, canon_ack: true, request_key: newKey(),
              windows: S.proposalWindows ? S.proposalWindows.read() : undefined } }));
    await requestBriefPlan(false);
    if (S.plan && S.plan.can_build) await startBuild();
    else if (m) m.textContent = (S.plan && S.plan.blocked_reason) ? S.plan.blocked_reason.message : t('readinessBlocked');
  } catch (e) { if (m) m.textContent = explain(e); }
}
function proposalCard() {
  const pr = S.proposal;
  if (!pr) return [];
  if (!pr.ok || !pr.cards) return [h('section', { class: 'proposal pending' }, h('p', {}, t('propNotYet')))];
  const price = proposalPrice(pr.price);
  S.proposalWindows = windowsChoice(pr.windows);
  const rowsOf = card => card.rows.map((r, i) => {
    const open = S.proposalOpen === r.key;
    const editor = open ? h('div', { class: 'rowEdit' },
      h('input', { type: 'text', id: 'propRowText', value: r.detail === '—' ? '' : r.detail, 'aria-label': r.title }),
      h('div', { class: 'row' },
        h('button', { type: 'button', onclick: () => proposalEdit('set_detail', r.key, $('propRowText').value) }, t('propSave')),
        h('button', { type: 'button', class: 'ghost', disabled: i === 0, onclick: () => proposalEdit('move_up', r.key) }, t('propUp')),
        h('button', { type: 'button', class: 'ghost', disabled: i === card.rows.length - 1, onclick: () => proposalEdit('move_down', r.key) }, t('propDown')),
        h('button', { type: 'button', class: 'ghost', onclick: () => proposalEdit('remove', r.key) }, t('propRemove')))) : null;
    return h('li', { class: `propRow${open ? ' open' : ''}`, 'data-key': r.key },
      h('button', { type: 'button', class: 'propRowBtn', 'aria-expanded': open ? 'true' : 'false',
                    onclick: () => { S.proposalOpen = open ? null : r.key; renderPlan(); } },
        h('span', { class: 'n' }, String(i + 1)), h('span', { class: 'title' }, r.title),
        h('span', { class: 'detail' }, r.detail), h('span', { class: 'edit' }, t('propEdit'))),
      editor);
  });
  return [h('section', { class: 'proposal', 'aria-labelledby': 'propTitle' },
    h('h2', { id: 'propTitle' }, t('propTitle')),
    ...pr.cards.map(card => h('div', { class: 'structureCard' },
      h('h3', {}, t('propLooks'), card.generic ? h('span', { class: 'pill warn' }, card.generic_reason || t('propGeneric')) : null),
      h('ol', { class: 'propRows' }, rowsOf(card)))),
    price ? h('div', { class: 'propPrice' }, h('span', {}, t('propPrice')), h('b', {}, price.amount),
      h('span', { class: 'pill warn' }, price.label), h('small', {}, price.basis)) : null,
    pr.facts && pr.facts.length ? h('div', {}, h('h3', {}, t('propFacts')),
      h('ul', { class: 'facts' }, pr.facts.map(f => h('li', {}, h('bdi', { dir: 'auto' }, f.source_ref))))) : null,
    h('div', { class: 'propLists' },
      h('div', {}, h('h3', {}, t('propIncluded')), h('ul', {}, pr.included.map(x => h('li', {}, x)))),
      h('div', {}, h('h3', {}, t('propExcluded')), h('ul', {}, pr.excluded.map(x => h('li', {}, x))))),
    S.proposalWindows.node,
    h('div', { class: 'row propActions' },
      h('button', { type: 'button', class: 'primary', id: 'approveAndBuildBtn',
                    disabled: Boolean(S.build && !isTerminal(S.build.status)), onclick: approveAndBuild }, t('propApprove')),
      h('button', { type: 'button', class: 'secondary', onclick: beginBriefEdit }, t('propChange')),
      S.proposalUndo ? h('button', { type: 'button', class: 'ghost', onclick: proposalUndo }, t('propUndo')) : null),
    h('p', { class: 'msg', id: 'propMsg', role: 'alert' }))];
}
function renderPlan() {
  const panel = $('planPanel'); const p = S.plan;
  renderProjectReadiness();
  if (!p) { panel.hidden = true; return; }
  panel.hidden = false;
  const facts = (label, items) => items && items.length ? [h('h3', {}, label), h('ul', { class: 'facts' }, items.map(x => h('li', {}, x)))] : [];
  const required = p.capabilities.filter(c => c.required);
  const lifecycle = required.filter(c => c.key.startsWith('software.'));
  const caps = [];
  if (lifecycle.length) caps.push(h('li', {}, h('span', {}, t('lifecycle')), h('span', { class: 'pill muted' }, t('byPipeline'))));
  for (const c of required.filter(c => !c.key.startsWith('software.'))) {
    caps.push(h('li', {}, h('span', {}, c.purpose || c.key),
      h('span', { class: 'pill muted' }, c.executed_by === 'external provider' ? t('byProvider') : t('byPipeline'))));
  }
  const infra = p.infrastructure.map(i => h('li', {}, h('span', {}, t(`k_${i.kind}`) || i.purpose), pill(i.readiness)));
  const sum = (p.brief_revision && S.disc && S.disc.summary) ? S.disc.summary : null;
  const briefKids = sum ? [
    h('h3', {}, t('sumGoal')), h('p', { class: 'summary' }, sum.goal),
    ...Object.entries(sum.sections).filter(([, items]) => items.length).map(([g, items]) => [
      h('h3', {}, sum.group_titles[g]),
      h('ul', { class: 'answers' }, items.map(x => h('li', {}, h('span', { class: 'q' }, x.question), h('b', {}, x.value),
        h('span', { class: `pill ${x.source === 'answer' ? 'ok' : 'muted'}` }, t(`src_${x.source}`)))))]),
    ...facts(t('sumIncluded'), sum.included), ...facts(t('sumExcluded'), sum.excluded),
    ...(sum.semantic_review?.length ? [h('h3', {}, t('semanticTitle')),
      h('ul', { class: 'answers' }, sum.semantic_review.map(x => h('li', {},
        h('b', {}, x.label), h('span', { class: 'pill' },
        x.uncertain ? t('semanticUncertain') : x.included ? t('semanticIncluded') : t('semanticExcluded')),
        h('span', { class: 'meta' }, x.evidence))))] : []),
  ].flat() : [];
  const kids = [
    ...proposalCard(),
    h('h2', {}, t('planTitle')),
    h('section', { class: `readinessStatus ${readinessView(S.build, p).mode === 'built' ? 'built' : p.can_build ? 'ready' : 'blocked'}`,
                   role: 'status', 'aria-live': 'polite' },
      h('strong', {}, readinessView(S.build, p).mode === 'built' ? `${t('readinessBuilt')}. ${p.can_build ? t('readinessReady') : t('readinessNextBlocked')}`
                       : p.can_build ? t('readinessReady') : t('readinessBlocked')),
      !p.can_build && p.blocked_reason ? h('p', { class: 'blockedReason' }, p.blocked_reason.message) : null,
      !p.can_build ? h('p', {}, p.blocked_reason ? p.blocked_reason.next : t('readinessBlockedHelp')(requestEditLabel(p))) : null),
    ...briefKids,
    ...(mediaLines(p).length ? [h('h3', {}, t('mediaTitle')), h('ul', { class: 'facts media' }, mediaLines(p).map(x => h('li', {}, x)))] : []),
    h('h3', {}, t('understood')),
    h('p', { class: 'summary' }, p.product.summary || p.product.title),
    ...facts(t('roles'), p.product.user_roles), ...facts(t('data'), p.product.data_requirements),
    ...facts(t('integrations'), p.product.required_integrations),
    h('h3', {}, t('capabilities')), h('ul', { class: 'checklist' }, caps),
    h('h3', {}, t('infrastructure')), h('ul', { class: 'checklist' }, infra),
    h('h3', {}, t('cost')),
    h('div', { class: 'cost' },
      h('div', {}, h('span', {}, t('creditsRequired')), h('b', {}, p.credits_required ?? t('costUnknown'))),
      h('div', {}, h('span', {}, t('creditsRemaining')),
        h('b', {}, (p.allowance && p.allowance.credits_remaining != null) ? p.allowance.credits_remaining : '—')),
      h('div', {}, h('span', {}, t('quoteStatus')), pill(p.build_authorization || 'UNKNOWN'))),
  ];
  if (p.prototype_qa_budget) {
    const qa = p.prototype_qa_budget;
    kids.push(h('section', { class: 'prototype-budget', 'aria-label': t('qaBudgetTitle') },
      h('h3', {}, t('qaBudgetTitle')),
      h('div', { class: 'cost' },
        h('div', {}, h('span', {}, t('qaBudgetRemaining')), h('b', {}, money(qa.remaining_usd))),
        h('div', {}, h('span', {}, t('qaBudgetLimit')), h('b', {}, money(qa.per_build_max_usd)))),
      h('p', { class: 'meta' }, t('qaBudgetActual'))));
  }
  if (p.clarification_questions.length) {
    kids.push(h('h3', {}, t('questions')), h('ul', { class: 'checklist' }, p.clarification_questions.map(q => h('li', {}, q.question))));
  }
  if (p.blockers.length) {
    const missingCapabilityNames = {
      'ai.agent.tools': ['סוכן AI המבצע פעולות', 'Agent tool execution', 'وكيل ذكاء اصطناعي ينفّذ إجراءات'],
      'integration.maps': ['מפות אינטראקטיביות', 'Interactive maps', 'خرائط تفاعلية'],
      'media.audio.tts': ['יצירת קול וקריינות', 'Text-to-speech', 'تحويل النص إلى صوت وتعليق صوتي'],
      'outbound': ['שליחת מיילים או התראות', 'Outgoing emails or notifications', 'إرسال رسائل بريد إلكتروني أو إشعارات'],
      'target.agent': ['מוצר מסוג סוכן AI', 'AI agent product', 'منتج من نوع وكيل ذكاء اصطناعي'],
    };
    const nameForMissing = g => {
      const names = missingCapabilityNames[g.key];
      return names ? names[{ he: 0, en: 1, ar: 2 }[S.lang] ?? 1] : String(g.purpose || g.key || t('unknownBlocker'));
    };
    const title = b => blockerTitle(b, p);
    const titles = [...new Set(p.blockers.map(title))];
    // Never imply that editing the request is the only remedy for a missing
    // provider quote. A configured-but-unpriced capability needs operator
    // pricing or an explicit, user-approved scope change.
    if (p.blockers.some(b => b.code === 'cost_quote_unknown' || b.code === 'cost_quote_unavailable')) {
      titles.push(t('quoteUnverified'));
    }
    kids.push(h('h3', {}, t('blockersTitle')), h('ul', { class: 'blockers' }, titles.map(x => h('li', {}, x))),
      ...(Array.isArray(p.unavailable_requirements) && p.unavailable_requirements.length ? [
        h('h4', {}, t('quoteMissingTitle')),
        h('ul', { class: 'quoteMissing' }, p.unavailable_requirements.map(g => h('li', {}, nameForMissing(g)))),
        h('p', { class: 'hint' }, t('quoteMissingHelp')(requestEditLabel(p)))
      ] : []),
      // 409 spec_not_approved / plan_not_verified: the same approval button as in the conversation, right here
      ...(p.brief_fingerprint && p.blockers.some(b => ['spec_not_approved', 'plan_not_verified', 'brief_stale'].includes(b.code)) ? [
        h('button', { type: 'button', class: 'primary', onclick: async () => {
          if (await sendChat({ brief_fingerprint: p.brief_fingerprint }, t('actApproveSpec'), specApprovalPath)) {
            S.plan = null; await requestBriefPlan();
          }
        } }, t('actApproveSpec'))] : []));
  }
  kids.push(h('div', { class: 'row' },
    h('button', { id: 'confirmBtn', disabled: !p.can_build || Boolean(S.build && !isTerminal(S.build.status)), onclick: startBuild },
      p.brief_revision ? t('approveBuild') : t('confirm')),
    h('button', { class: 'secondary', onclick: () => {
      if (S.disc) { beginBriefEdit(); }
      else $('chatInput').focus(); } }, requestEditLabel(p))));
  kids.push(h('p',{id:'planMsg',class:'msg',role:'alert'},S.buildAdmissionError||''));
  panel.replaceChildren(...kids);
}

/* ---------- build ---------- */
const isTerminal = s => ['ready', 'failed', 'cancelled', 'READY', 'FAILED', 'CANCELLED'].includes(s);
let buildStarting = false;
async function startBuild() {
  if (!S.plan || !S.plan.can_build || buildStarting) return;
  const buildProjectId = pid();
  const plan = S.plan;
  const prompt = (S.disc && S.disc.prompt) || 'build';
  const idempotencyStorageKey = `148ai_build_idempotency:${buildProjectId}:${plan.build_contract_id}`;
  // One click = one request; the server also returns the existing build for
  // an already-approved plan instead of starting a second one.
  buildStarting = true;
  S.buildAdmissionError='';
  // Show approval progress immediately, without inventing a build ID or task.
  $('progressPanel').hidden = false;
  resetBuildPanel(); renderLog();
  $('buildMsg').textContent = t('checkingApproval');
  openTab('build');
  try {
    let idempotencyKey = localStorage.getItem(idempotencyStorageKey);
    if (!idempotencyKey) {
      idempotencyKey = newKey();
      localStorage.setItem(idempotencyStorageKey, idempotencyKey);
    }
    // Directive 2026-10-09 §5: the server binds this approval to the user,
    // the brief revision, the plan and the price; the build consumes it once.
    let approvalId = null;
    if (plan.brief_revision) {
      const a = await api(`/api/v28/projects/${buildProjectId}/approvals`, { method: 'POST',
        body: { build_contract_id: plan.build_contract_id, brief_revision: plan.brief_revision } });
      approvalId = a.approval_id;
    }
    const d = await api(`/api/v28/projects/${buildProjectId}/builds`, { method: 'POST',
      body: { prompt, build_contract_id: plan.build_contract_id,
              approval_id: approvalId, idempotency_key: idempotencyKey } });
    localStorage.removeItem(idempotencyStorageKey);
    if (pid() !== buildProjectId) return;
    S.build = { id: d.build_id, status: d.status || 'queued', phase: d.duplicate ? '' : 'QUEUED', evidence: {} };
    renderPlan(); renderTrack(); renderBuilt(); openTab('build'); pollBuild();
    if (d.duplicate) $('buildMsg').textContent = t('duplicateBuild');
  } catch (e) {
    if (e.status >= 400 && e.status < 500) {
      localStorage.removeItem(idempotencyStorageKey);
    }
    if (pid() !== buildProjectId) return;
    if(!S.build){
      S.buildAdmissionError=explain(e);
      if(e.status===409)await requestBriefPlan(false);
      $('progressPanel').hidden = true;
      renderPlan();renderTrack();openTab('plan');
    }else $('buildMsg').textContent=explain(e);
  } finally {
    buildStarting = false;
  }
}
async function pollBuild() {
  // One poll loop at a time (2026-10-30): a second call used to arm a second timer, so the loops stacked.
  clearTimeout(S.timers.build);
  if (!S.build) return;
  const project = S.projectId, buildId = S.build.id;
  try {
    const d = await api(`/api/v28/projects/${pid()}/builds/${encodeURIComponent(S.build.id)}`);
    if (!stillOn(project) || !S.build || S.build.id !== buildId) return;
    S.build = { ...S.build, ...d };
    await pollEvents();
    await loadTasks();
    renderTrack(); renderEvidence(); renderTasks(); renderChat();
    if (isTerminal(d.status)) {
      refreshWorkspaceBalance();
      renderPlan();
      if (String(d.status).toLowerCase() === 'ready' && d.result_version_id) {
        S.newBuildOpen = false;
        await loadVersions();
        startPreview(d.result_version_id);
      } else if (d.result_version_id) { await loadVersions(); }
      else renderBuilt();
      return;
    }
  } catch (e) { $('buildMsg').textContent = explain(e); }
  clearTimeout(S.timers.build);
  S.timers.build = setTimeout(pollBuild, 2500);
}
/* Directive 2026-10-09 §10/§12: live log + stop. */
async function pollEvents() {
  const b = S.build; if (!b || !b.id) return;
  if (b.logFor !== b.id) { b.logFor = b.id; b.log = []; b.logAfter = 0; }
  const project = S.projectId;
  try {
    const d = await api(`/api/v28/projects/${pid()}/builds/${encodeURIComponent(b.id)}/events?after=${b.logAfter || 0}`);
    if (!stillOn(project) || S.build !== b) return;
    for (const e of d.events || []) { b.log.push(e); b.logAfter = Math.max(b.logAfter || 0, e.seq); }
  } catch (e) { /* the log is a convenience; status polling carries on */ }
}
function renderLog() {
  const b = S.build; const box = $('liveLog'); const list = $('liveLogList');
  if (!b) {                    // an explicit empty state, never the lines of a build of another project
    box.hidden = $('progressPanel').hidden;
    list.replaceChildren(h('li', { class: 'ev muted' }, t('logNoBuild')));
    return;
  }
  box.hidden = false;
  const fmt = iso => { try { return new Date(iso).toLocaleTimeString(locale(), { hour: '2-digit', minute: '2-digit', second: '2-digit' }); } catch (e) { return ''; } };
  const rows = (b.log || []).slice(-60).map(e => h('li', { class: `ev ${e.kind}` }, h('time', {}, fmt(e.at)), ' ', e.message));
  const atEnd = list.scrollHeight - list.scrollTop - list.clientHeight < 24;
  list.replaceChildren(...(rows.length ? rows : [h('li', { class: 'ev muted' }, t('logEmpty'))]));
  if (atEnd) list.scrollTop = list.scrollHeight;  // follow the newest line unless the user scrolled up
}
function renderControls() {
  const b = S.build; const row = $('buildControls'); const btn = $('cancelBuildBtn');
  const live = b && !isTerminal(b.status);
  row.hidden = !live;
  if (!live) return;
  btn.disabled = Boolean(b.cancelRequested);
  $('cancelHint').textContent = b.cancelRequested ? t('stopping') : '';
}
async function cancelBuild() {
  const b = S.build; if (!b || isTerminal(b.status) || b.cancelRequested) return;
  if (!window.confirm(t('stopConfirm'))) return;
  b.cancelRequested = true; renderControls();
  try {
    const d = await api(`/api/v28/projects/${pid()}/builds/${encodeURIComponent(b.id)}/cancel`, { method: 'POST' });
    if (d.outcome === 'cancelled') { clearTimeout(S.timers.build); pollBuild(); }
  } catch (e) { b.cancelRequested = false; renderControls(); $('buildMsg').textContent = explain(e); }
}
const PHASE_ORDER = ['PLANNING', 'INFRASTRUCTURE', 'ASSETS', 'GENERATING', 'VERIFYING'];
function renderTrack() {
  if (S.build?.status) rememberBuildState(S.build.status);
  renderProjectReadiness();
  const panel = $('progressPanel');
  if (!S.build) { panel.hidden = true; return; }
  panel.hidden = false;
  const b = S.build; const ev = (b && b.evidence) || {};
  const status = b ? String(b.status).toLowerCase() : null;
  const phase = b ? String(b.phase || '').toUpperCase() : null;
  const reached = PHASE_ORDER.indexOf(phase);
  const failedCode = status === 'failed' ? (b.error_code || '') : '';
  // Step at which a failed build stopped. Steps after it never ran: they are
  // shown as skipped, never as done (a failed build once showed the quality
  // gates as passed although generation had failed before them).
  const FAIL_STEP = { infrastructure_not_configured: 1, capability_not_configured: 2, capability_gate_failed: 2, image_mismatch: 2,
    worker_exception: 3, build_timeout: 3, provider_liability_unknown: 3, worker_lost: 3, preview_not_ready: 3, model_budget_exhausted: 3, model_unavailable: 3, provider_quota_exhausted: 3, model_policy_blocked: 3, verification_failed: 3, release_policy_failed: 4, quality_gate_failed: 4, security_gate_failed: 4, rights_gate_not_clear: 4 };
  const failedIdx = failedCode in FAIL_STEP ? FAIL_STEP[failedCode] : -1;
  const preview = S.preview;
  const steps = [];
  const push = (name, state, note) => steps.push(h('li', { class: `step ${state}` }, h('span', { class: 'dot', 'aria-hidden': 'true' }),
    h('div', {}, h('span', { class: 'name' }, name), note ? h('span', { class: 'note' }, note) : null,
      h('span', { class: 'sr' }, ` (${state})`))));
  // A build exists only for an approved plan (after a reload the plan itself is not reloaded).
  push(t('stepPlanning'), (S.plan || b) ? 'done' : 'active');
  push(t('stepContract'), S.plan ? (S.plan.status === 'READY' ? 'done' : 'failed') : b ? 'done' : 'pending',
    S.plan && S.plan.status !== 'READY' ? t('err409') : null);
  const backendStep = (key, idx, failCodes, note) => {
    if (!b) return push(t(key), 'pending', note);
    if (failCodes.includes(failedCode)) return push(t(key), 'failed', friendlyError(b));
    if (status === 'ready') return push(t(key), 'done', note);
    if (status === 'failed') return push(t(key), (failedIdx >= 0 ? idx < failedIdx : reached > idx) ? 'done' : 'skipped', note);
    if (status === 'queued') return push(t(key), 'pending', idx === 0 ? queuedNote(b) : note);
    if (status === 'cancelled') return push(t(key), 'skipped', null);
    return push(t(key), reached === idx ? 'active' : reached > idx ? 'done' : 'pending', note);
  };
  const infraEv = ev.infrastructure; const capEv = ev.capabilities;
  backendStep('stepInfra', 1, ['infrastructure_not_configured'], infraEv === null && status === 'ready' ? t('none') : null);
  backendStep('stepAssets', 2, ['capability_not_configured', 'capability_gate_failed', 'image_mismatch'], null);
  const repairNote = b && b.repair_rounds !== undefined && b.repair_rounds !== null && isTerminal(b.status) ? t('repairs')(b.repair_rounds) : t('noteGenerate');
  backendStep('stepGenerate', 3, ['worker_exception', 'preview_not_ready', 'model_budget_exhausted', 'model_unavailable', 'provider_quota_exhausted', 'model_policy_blocked', 'verification_failed'], repairNote);
  backendStep('stepGates', 4, ['quality_gate_failed', 'security_gate_failed', 'rights_gate_not_clear'], null);
  let pState = (!preview && (status === 'cancelled' || status === 'failed')) ? 'skipped' : 'pending', pNote = null;
  if (preview) {
    const ps = preview.status;
    if (ps === 'RUNNING') pState = 'done';
    else if (['FAILED', 'NOT_PREVIEWABLE', 'UNAVAILABLE'].includes(ps)) { pState = 'failed'; pNote = preview.error_message; }
    else if (ps === 'EXPIRED' || ps === 'STOPPED') { pState = 'skipped'; pNote = t('previewExpired'); }
    else pState = 'active';
  }
  push(t('stepPreview'), pState, pNote);
  $('track').replaceChildren(...steps);
  if (status === 'failed' && !S.preview) renderPreview();
  renderControls(); renderLog();
  const msg = $('buildMsg'); msg.className = 'msg';
  if (status === 'ready') { msg.className = 'msg ok'; msg.textContent = t('buildReady'); const nr = notRunLine(b); if (nr) msg.append(h('div', { class: 'notrun' }, nr)); }
  else if (status === 'cancelled') { msg.textContent = t('buildCancelled'); }
  else if (status === 'failed') {
    // Plain words (owner 2026-11-21): what happened, what happened to the money, and the one action -- as a button.
    const fv = failureView(b);
    msg.replaceChildren(fv.text);
    msg.append(h('div', {}, failureButton(fv)));
    // The checks that did not run (warehouse 104), why the repair stopped (warehouse 102) and the raw message: owner only.
    const tech = ownerTech(b);
    if (tech) msg.append(h('details', { class: 'tech' }, h('summary', {}, t('ownerTech')),
      ...tech.lines.map(x => h('div', { class: 'notrun' }, x)), h('code', { dir: 'ltr' }, tech.raw)));
    // CEO 2026-11-08: a failed founder build keeps its best candidate as a draft version; open it next to the failures.
    if (b.result_version_id) {
      const btn = h('button', { class: 'btn', type: 'button' }, t('openDraftPreview'));
      btn.addEventListener('click', () => startPreview(b.result_version_id));
      msg.append(h('div', {}, btn));
    }
  }
  else msg.textContent = '';
}

/* ---------- preview ---------- */
async function startPreview(versionId) {
  S.preview = { status: 'STARTING', version_id: versionId }; renderPreview(); renderTrack();
  try {
    const d = await api(`/api/v28/projects/${pid()}/versions/${encodeURIComponent(versionId)}/previews`, { method: 'POST' });
    S.previewId = d.preview_id; pollPreview();
  } catch (e) {
    const notPreviewable = e.status === 422;
    S.preview = { status: notPreviewable ? 'NOT_PREVIEWABLE' : 'UNAVAILABLE', version_id: versionId,
      error_message: notPreviewable ? (e.detail && e.detail.reason) || e.message : explain(e) };
    renderPreview(); renderTrack();
  }
}
async function pollPreview() {
  if (!S.previewId) return;
  try {
    const d = await api(`/api/v28/projects/${pid()}/previews/${encodeURIComponent(S.previewId)}`);
    S.preview = d; renderPreview(); renderTrack();
    if (['RUNNING', 'FAILED', 'NOT_PREVIEWABLE', 'EXPIRED', 'STOPPED'].includes(d.status)) return;
  } catch (e) { S.preview = { status: 'UNAVAILABLE', error_message: explain(e) }; renderPreview(); return; }
  S.timers.preview = setTimeout(pollPreview, 2000);
}
function renderPreview() {
  const p = S.preview; const frame = $('previewFrame'); const empty = $('previewEmpty'); const text = $('previewEmptyText');
  const link = $('openPreviewLink'); const refresh = $('refreshPreviewBtn');
  const running = p && p.status === 'RUNNING' && p.preview_url;
  frame.hidden = !running; empty.hidden = Boolean(running);
  refresh.disabled = !running; link.setAttribute('aria-disabled', running ? 'false' : 'true');
  $('previewUrl').textContent = running ? p.preview_url : '—';
  const note = $('previewDataNote');
  note.hidden = !running;
  if (running) note.textContent = p.data_storage === 'persistent' ? t('dataPersistent') : t('dataTemporary');
  renderSharing(running ? p : null);
  if (running) {
    // Autonomous completion §4: previews are private; open them with the
    // owner's short-lived access link (the router turns it into a cookie).
    const acc = S.previewAccess && S.previewAccess.id === p.id ? S.previewAccess : null;
    if (!acc) { requestPreviewAccess(p); return; }
    if (frame.dataset.access !== acc.url) { frame.dataset.access = acc.url; frame.src = acc.url; }
    link.href = acc.url;
    if (window.VE) VE.onPreview();
    return;
  }
  delete frame.dataset.access;
  link.removeAttribute('href');
  if (frame.src) frame.removeAttribute('src');
  let message = t('noPreview');
  if (p) {
    if (p.status === 'NOT_PREVIEWABLE') message = t('previewNotPreviewable') + (p.error_message || '');
    else if (p.status === 'UNAVAILABLE') message = t('previewUnavailable') + (p.error_message || '');
    else if (p.status === 'FAILED') message = t('previewFailed') + (p.error_message || '');
    else if (p.status === 'EXPIRED' || p.status === 'STOPPED') message = t('previewExpired');
    else message = t('previewStarting');
  }
  text.textContent = message;
  // A project opened later (or a preview that was unavailable) can start one
  // for its current version too, not only right after a build or a change.
  const canRetry = currentVersionId() && (!p || ['EXPIRED', 'STOPPED', 'FAILED', 'UNAVAILABLE'].includes(p.status));
  empty.querySelector('.previewRecovery')?.remove();
  const buildFailed = S.build?.status?.toLowerCase() === 'failed' && !p;
  empty.classList.toggle('previewFailed', buildFailed);
  if (buildFailed) {
    const recovery = failureView(S.build);
    text.textContent = recovery.text;
    const recover = failureButton(recovery);
    recover.addEventListener('click', () => window.VE?.setPane('chat'), {capture:true});
    empty.append(h('div', { class: 'previewRecovery' }, recover));
  }
  const existing = empty.querySelector(':scope > button'); if (existing) existing.remove();
  // review F1 (2026-11-22): a failed rebuild does not hide the preview of the version that already works
  if (canRetry) empty.append(h('button', { class: 'secondary', onclick: () => startPreview(currentVersionId()) }, t('startPreview')));
  if (window.VE) VE.onPreview();
}

let accessPending = null;
async function requestPreviewAccess(p) {
  if (accessPending === p.id) return;
  accessPending = p.id;
  try {
    const d = await api(`/api/v28/projects/${pid()}/previews/${encodeURIComponent(p.id)}/access`, { method: 'POST' });
    S.previewAccess = { id: p.id, url: d.url };
  } catch (e) {
    S.previewAccess = null; $('previewEmptyText').textContent = explain(e);
  } finally { accessPending = null; }
  renderPreview();
}
function renderSharing(p) {
  const box = $('previewSharing'); if (!box) return;
  box.hidden = !p;
  if (!p) return;
  const mode = p.access_mode || 'PRIVATE';
  const sel = h('select', { 'aria-label': t('shareLabel'), onchange: async (ev) => {
    try {
      const d = await api(`/api/v28/projects/${pid()}/previews/${encodeURIComponent(p.id)}/sharing`, { method: 'POST', body: { mode: ev.target.value } });
      S.preview = { ...S.preview, access_mode: d.access_mode }; S.shareUrl = d.share_url || null; renderPreview();
    } catch (e) { $('previewDataNote').textContent = explain(e); }
  } }, ...['PRIVATE', 'SHARED', 'PUBLIC'].map(m => h('option', { value: m, selected: m === mode }, t('share' + m))));
  const kids = [h('span', {}, t('shareLabel') + ': '), sel];
  if (mode === 'SHARED' && S.shareUrl) kids.push(h('input', { readonly: true, value: S.shareUrl, dir: 'ltr', 'aria-label': t('shareLink'), onfocus: (e) => e.target.select() }));
  box.replaceChildren(...kids);
}
// warehouse 104 (owner, 2026-11-15): the checks that did not run are named, never hidden in a count or in "did not pass
// or did not run". The list is the quality report's own (release_policy.QualityReport.not_run); a failed build with no
// report stopped before any check.
// Review 2026-11-15: "no check ran" is said only for the failure codes the worker emits before any check (the engine
// died); a failed build whose report could not be generated, or a report stored before the list existed, says nothing
// rather than guessing.
function notRunLine(b) {
  const NO_REPORT_BEFORE_CHECKS = ['worker_exception', 'model_budget_exhausted', 'model_unavailable', 'provider_quota_exhausted', 'model_policy_blocked', 'attempt_ledger_unavailable', 'plan_violation'];
  const status = b ? String(b.status || '').toLowerCase() : '';
  if (status !== 'failed' && status !== 'ready') return '';
  const qr = b.evidence && b.evidence.quality_report;
  if (!qr) return status === 'failed' && NO_REPORT_BEFORE_CHECKS.includes(b.error_code) ? t('checksNoneRan') : '';
  if (!Array.isArray(qr.not_run)) return '';
  const names = t('checkNames') || {};
  const list = qr.not_run.map(c => names[c.check] || c.check);
  return list.length ? `${t('checksNotRun')}: ${list.join(', ')}.` : '';
}
// warehouse 102 (owner, 2026-11-15, narrow scope): why the automatic repair stopped, in the customer's words. The reason
// is the engine's own (autonomous_core stop_reason, stored by the worker as evidence.repair_stop_reason); a reason the
// table does not know is shown as it is, never hidden.
function stopReasonLine(b) {
  if (!b || String(b.status || '').toLowerCase() !== 'failed') return '';
  const reason = b.evidence && b.evidence.repair_stop_reason;
  if (!reason || reason === 'passed' || reason === 'no_repair_adopted') return '';
  const words = t('repairStops') || {};
  return words[reason] || `${t('repairStopped')}: ${reason}`;
}
function friendlyError(b) {
  const known = (t('errCodes') || {})[b.error_code];
  // #335 (d): which detail is missing, in the customer's words
  if (b.error_code === 'needs_customer_input') {
    const names = t('failMissing') || {};
    const m = String(b.error_message || '').match(/missing from the customer: ([a-z, ]+)/);
    // a detail the table has no words for is not named at all: its internal key is never shown
    const what = m ? m[1].split(',').map(x => names[x.trim()]).filter(Boolean).join(', ') : '';
    return known + (what ? ' (' + what + ')' : '');
  }
  if (b.error_code === 'image_mismatch') {
    // Michael 2026-11-15: judged in seconds -- what was asked, and what the vision model saw
    const m = String(b.error_message || '').match(/asked "([^"]*)"; the image shows "([^"]*)"/);
    if (m) return known + ({ en: ` Asked: "${m[1]}". The image shows: "${m[2]}".`,
                            ar: ` طلبتم: "${m[1]}". في الصورة: "${m[2]}".` }[S.lang] ?? ` ביקשתם: "${m[1]}". בתמונה: "${m[2]}".`);
    return known;
  }
  // 2026-11-08: 'all model routes failed: ... does not fit the remaining budget' is the build budget running out,
  // not the providers being down (bld_e6b94762 showed 'providers unavailable' while every route was over budget).
  if (b.error_code === 'model_unavailable' && /does not fit the remaining budget/.test(String(b.error_message || '')))
    return (t('errCodes') || {}).model_budget_exhausted || known;
  // 78: the app started and served an empty page -- never "the site did not start".
  if (b.error_code === 'preview_not_ready' && /generated interface is empty/.test(String(b.error_message || ''))) {
    const m = String(b.error_message || '').match(/missing: ([a-z,]+)/);
    const names = t('uiMissing') || {};
    const parts = (m ? m[1].split(',') : []).map(k => names[k]).filter(Boolean);
    return t('uiEmpty') + (parts.length ? ': ' + t('uiMissingLead') + ' ' + parts.join(', ') : '') + ', ' + t('uiEmptyTail');
  }
  // No words for this code: one default line. The raw message and the code are the owner's (ownerTech), never the customer's.
  return known || t('failUnknown');
}
// Who sees the technical blocks: only the owner's account. /api/v28/me says is_founder (pricing.m5_founder_account);
// anything else -- false, missing, not loaded, not a boolean -- is a customer.
function ownerView() {
  return Boolean(S.me && S.me.is_founder === true);
}
// "You were not charged" is said only when the build's own record says the reservation was released (the worker's
// evidence.billing; maintenance.reap_build), or for the three codes whose code path releases it without writing
// evidence (maintenance.run_once worker_lost; worker_tasks._fail_build_not_found; investor_app._close_preview_build).
const NOT_CHARGED_BILLING = ['released', 'exposure_checked_release'];
const NOT_CHARGED_CODES = ['worker_lost', 'build_not_found', 'preview_no_build_queue'];
// The charge is not known yet (maintenance: the reservation is held for reconciliation): never "not charged", whatever else is recorded.
const CHARGE_UNKNOWN_CODES = ['provider_liability_unknown'];
// The one action. Trying the same request again cannot help for these; the request itself has to change.
const FAIL_ACTION = { needs_customer_input: 'input', model_budget_exhausted: 'edit', unsupported_dependency: 'edit', rights_gate_not_clear: 'edit' };
function failureView(b) {
  const what = friendlyError(b);
  const billing = b.evidence && b.evidence.billing;
  const notCharged = !CHARGE_UNKNOWN_CODES.includes(b.error_code)
    && (NOT_CHARGED_BILLING.includes(billing) || (!billing && NOT_CHARGED_CODES.includes(b.error_code)));
  const action = Object.prototype.hasOwnProperty.call(FAIL_ACTION, b.error_code) ? FAIL_ACTION[b.error_code] : 'retry';
  const label = action === 'retry' ? t('actRetryBuild') : t('editAll');
  const text = [what, notCharged ? t('failNotCharged') : '', t('failNext')[action](label)].filter(Boolean).join(' ');
  return { what, notCharged, action, label, text };
}
function failureButton(fv) {
  const go = fv.action === 'retry'
    ? async () => { if (!S.plan) await requestBriefPlan(); openTab('plan'); const c = $('confirmBtn'); if (c) c.focus(); }
    : () => { if (S.disc) beginBriefEdit(); else { const i = $('chatInput'); if (i) i.focus(); } };
  return h('button', { class: 'btn primary', type: 'button', onclick: go }, fv.label);
}
function ownerTech(b) {
  if (!ownerView() || !b) return null;
  const lines = [notRunLine(b), stopReasonLine(b)].filter(Boolean);
  return { lines, raw: [b.error_code, b.error_message].filter(Boolean).join(': ') };
}
function requestEditLabel(p) {
  return p && p.brief_revision ? t('updateRequest') : t('editRequest');
}

/* ---------- versions ---------- */
function currentVersionId() { return S.versions.length ? S.versions[0].id : null; }
async function loadVersions() {
  const project = S.projectId;
  try {
    const d = await api(`/api/v28/projects/${pid()}/history`);
    if (!stillOn(project)) return;
    S.versions = (d.versions || []).slice().sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
  } catch { S.versions = []; }
  renderVersions(); renderMod(); renderBuilt(); renderPreview();
  $('downloadBtn').disabled = !currentVersionId();
}
/* Once a project has a product, lead with what it is and how to change it;
   a new build from scratch stays one click away. */
function renderBuilt() {
  const v = S.versions[0];
  const building = (!!S.plan && !S.build) || (!!S.build && !isTerminal(S.build.status));
  $('builtPanel').hidden = !v;
  $('newBuildRow').hidden = !v || S.newBuildOpen || building;
  renderDiscovery();
  if (!v) return;
  $('builtName').textContent = v.title || v.message || t('workspaceVersion');
  $('builtSummary').textContent = v.summary || '';
  $('builtFeatures').replaceChildren(...(v.features || []).map((f) => h('li', {}, f)));
  let when = v.created_at;
  try { when = new Intl.DateTimeFormat(locale(), { dateStyle: 'short', timeStyle: 'short' }).format(new Date(v.created_at)); } catch { /* keep raw */ }
  $('builtMeta').replaceChildren(when,
    v.file_count ? ` · ${v.file_count} ${t('files')}` : '');
}
function renderVersions() {
  const panel = $('versionsPanel');
  panel.hidden = !S.projectId || !S.me;
  const list = $('versionsList');
  if (!S.versions.length) { list.replaceChildren(h('li', { class: 'meta' }, t('noVersions'))); return; }
  const fmt = new Intl.DateTimeFormat(locale(), { dateStyle: 'short', timeStyle: 'short' });
  list.replaceChildren(...S.versions.map((v, i) => {
    let when = v.created_at; try { when = fmt.format(new Date(v.created_at)); } catch { /* keep raw */ }
    return h('li', {},
      h('div', { class:'versionLabel' }, h('strong', {}, v.title || v.message || t('workspaceVersion')), h('div', { class: 'meta' }, when),
        h('details', {}, h('summary', {}, t('tab_details')), h('code', { dir:'ltr' }, v.id))),
      i === 0 ? h('span', { class: 'pill ok' }, t('current')) : h('button', { class: 'ghost', onclick: () => restoreVersion(v.id) }, t('restore')));
  }));
}
const activeVersionRestores = new Set();
async function restoreVersion(versionId) {
  const project = S.projectId;
  const notice = $('versionNotice');
  if (activeVersionRestores.has(project)) return;
  activeVersionRestores.add(project);
  notice.textContent = '';
  try {
    await api(`/api/v28/projects/${pid()}/rollback`, { method: 'POST', body: { target_version_id: versionId, message: 'rollback from workspace' } });
    if (!stillOn(project)) return;
    clearTimeout(S.timers.preview);
    S.preview = null; S.previewId = null; S.previewAccess = null;
    await loadVersions();
    if (stillOn(project)) { notice.className = 'msg ok'; notice.textContent = t('restored'); }
  } catch (e) {
    if (stillOn(project)) { notice.className = 'msg'; notice.textContent = explain(e); }
  } finally {
    activeVersionRestores.delete(project);
  }
}

/* ---------- modification ---------- */
async function sendModification(extra) {
  const followup = $('followup').value.trim(); const vid = currentVersionId();
  if (followup.length < 3 || !vid || modActive()) return null;
  $('modifyBtn').disabled = true;
  try {
    const d = await api(`/api/v28/projects/${pid()}/versions/${encodeURIComponent(vid)}/modifications`,
      { method: 'POST', body: { followup, ...(extra || {}) } });
    S.mod = { id: d.modification_id, status: 'QUEUED', source_version_id: vid, visual_edit: d.visual_edit || null };
    renderMod(); pollMod();
    return d;
  } catch (e) {
    if (e.status === 409 && e.detail && e.detail.error === 'target_ambiguous') throw e;   // the editor asks which element
    S.mod = { status: 'ERROR', error_message: explain(e) }; renderMod(); return null;
  }
  finally { renderMod(); }
}
const MOD_DONE = ['READY_FOR_REVIEW', 'FAILED', 'ACCEPTED', 'REJECTED', 'SUPERSEDED', 'CLARIFICATION_REQUIRED', 'NEEDS_CLARIFICATION', 'CONFLICT', 'ERROR', 'CANCELLED'];
// One change at a time: the send button stays locked while a change is being
// built or waits for review (a double click once created two candidates).
// 2026-11-15: a queued build says how many jobs are ahead of it (the server's count; no number -> the plain line)
function queuedNote(b) {
  const n = b && b.queue_ahead;
  if (typeof n !== 'number' || !Number.isInteger(n) || n < 0) return t('queued');
  return n === 0 ? t('queuedNext') : t('queuedAhead')(n);
}
function modActive() { return !!(S.mod && S.mod.id && ['QUEUED', 'RUNNING', 'READY_FOR_REVIEW'].includes(S.mod.status)); }
async function pollMod() {
  if (!S.mod || !S.mod.id) return;
  try {
    const d = await api(`/api/v28/projects/${pid()}/modifications/${encodeURIComponent(S.mod.id)}`);
    S.mod = { ...S.mod, ...d, misses: 0 };
    try {  // live log of the change (autonomous completion §5)
      const ev = await api(`/api/v28/projects/${pid()}/modifications/${encodeURIComponent(S.mod.id)}/events?after=${S.mod.logAfter || 0}`);
      S.mod.log = (S.mod.log || []).concat(ev.events || []);
      if ((ev.events || []).length) S.mod.logAfter = ev.events[ev.events.length - 1].seq;
    } catch (e) { /* the log is a convenience */ }
    renderMod();
    if (MOD_DONE.includes(d.status)) return;
  } catch (e) {
    // A dropped or slow request is retried; only a real refusal ends polling.
    S.mod.misses = (S.mod.misses || 0) + 1;
    if (e.status && e.status !== 0 || S.mod.misses > 20) { S.mod = { ...S.mod, status: 'ERROR', error_message: explain(e) }; renderMod(); return; }
  }
  S.timers.mod = setTimeout(pollMod, 3000);
}
/* After a reload or project switch, pick up the latest change of this
   version: still running -> keep polling; ready -> show accept / reject. */
async function restoreMod() {
  const vid = currentVersionId();
  if (!vid) return;
  try {
    const d = await api(`/api/v28/projects/${pid()}/modifications/latest`);
    if (!d || !d.modification_id || d.source_version_id !== vid) return;
    if (!['QUEUED', 'RUNNING', 'READY_FOR_REVIEW'].includes(d.status)) return;
    S.mod = { id: d.modification_id, ...d }; renderMod();
    if (d.status !== 'READY_FOR_REVIEW') pollMod();
  } catch { /* the panel simply starts empty */ }
}
async function cancelMod() {
  if (!S.mod || !S.mod.id || !window.confirm(t('stopChangeConfirm'))) return;
  S.mod.cancelRequested = true; renderMod();
  try {
    await api(`/api/v28/projects/${pid()}/modifications/${encodeURIComponent(S.mod.id)}/cancel`, { method: 'POST' });
    clearTimeout(S.timers.mod); pollMod();
  } catch (e) { S.mod.cancelRequested = false; S.mod.error_message = explain(e); renderMod(); }
}
async function decideMod(accept) {
  const before = currentVersionId();
  try {
    const d = await api(`/api/v28/projects/${pid()}/modifications/${encodeURIComponent(S.mod.id)}/${accept ? 'accept' : 'reject'}`,
      { method: 'POST', body: accept ? { message: 'accepted in workspace' } : { reason: 'rejected in workspace' } });
    S.mod = { ...S.mod, status: accept ? 'ACCEPTED' : 'REJECTED', promoted_version_id: d.version_id || d.promoted_version_id };
    renderMod();
    if (accept) {
      await loadVersions();
      S.lastChange = { before: S.mod.source_version_id || before, after: currentVersionId() };
      if (currentVersionId()) startPreview(currentVersionId());
      if (window.VE) VE.onChangeAccepted();
    }
  } catch (e) { S.mod = { ...S.mod, status: 'ERROR', error_message: explain(e) }; renderMod(); }
}
function renderMod() {
  $('modifyPanel').hidden = !currentVersionId();
  $('modifyBtn').disabled = modActive();
  const box = $('modifyState'); const m = S.mod;
  if (!m) { box.replaceChildren(); return; }
  const kids = [];
  if (m.status === 'READY_FOR_REVIEW') {
    kids.push(h('p', {}, t('modReview')),
      m.classification ? h('p', { class: 'hint' }, `${t('classification')}: ${m.classification}`) : null,
      h('div', { class: 'row' }, h('button', { onclick: () => decideMod(true) }, t('accept')),
        h('button', { class: 'secondary', onclick: () => decideMod(false) }, t('reject'))));
  } else if (m.status === 'ACCEPTED') kids.push(h('p', { class: 'msg ok' }, t('modAccepted')));
  else if (m.status === 'REJECTED') kids.push(h('p', { class: 'hint' }, t('modRejected')));
  else if (['FAILED', 'ERROR', 'CLARIFICATION_REQUIRED', 'NEEDS_CLARIFICATION', 'CONFLICT'].includes(m.status)) kids.push(h('p', { class: 'msg' }, t('modFailed') + (m.error_message || m.classification_reason || m.status)));
  else if (m.status === 'CANCELLED') kids.push(h('p', { class: 'hint' }, t('modCancelled')));
  else {
    kids.push(h('p', { class: 'hint' }, m.cancelRequested ? t('stopping') : t('modQueued')));
    if (m.id && ['QUEUED', 'RUNNING'].includes(m.status))
      kids.push(h('div', { class: 'row' }, h('button', { class: 'secondary danger', disabled: Boolean(m.cancelRequested), onclick: cancelMod }, t('stopChange'))));
  }
  if (m.log && m.log.length) kids.push(h('details', { class: 'live-log', open: true }, h('summary', {}, t('liveLog')),
    h('ol', {}, ...m.log.slice(-30).map(e => h('li', { class: `ev ${e.kind}` }, e.message)))));
  box.replaceChildren(...kids);
}

/* ---------- evidence ---------- */
// A check mark only for an explicit pass. A missing gate value, null, or a gate without a boolean verdict is NOT a
// pass (2026-10-30): it renders '—'. The rights gate reports publish_allowed instead of passed.
function gateMark(v) {
  const verdict = v && typeof v.passed === 'boolean' ? v.passed
    : v && typeof v.publish_allowed === 'boolean' ? v.publish_allowed : null;
  return verdict === true ? '✓' : verdict === false ? '✗' : '—';
}
// Gate names are labels like every other one (2026-10-30: the raw keys were printed). An unknown key keeps its
// name, so a new gate is never hidden.
function gateLabel(k) { return ((t('gateNames') || {})[k]) || k; }
function renderEvidence() {
  const panel = $('evidencePanel'); const ev = S.build && S.build.evidence;
  if (!ev || !isTerminal(S.build.status)) { panel.hidden = true; return; }
  panel.hidden = false;
  const gates = ev.gates || {};
  const gateText = Object.entries(gates).map(([k, v]) => `${gateLabel(k)}: ${gateMark(v)}`).join(', ') || t('none');
  const warnings = [];
  if (ev.capabilities && ev.capabilities.status && ev.capabilities.status !== 'VERIFIED') warnings.push(`capabilities: ${ev.capabilities.status}`);
  const row = (k, v) => [h('dt', {}, k), h('dd', {}, v)];
  $('evidenceBody').replaceChildren(
    h('dl', {},
      row(t('gates'), gateText),
      row(t('repairs')(S.build.repair_rounds ?? '—'), ''),
      row('billing', ev.billing || '—'),
      row(t('warnings'), warnings.join(', ') || t('none'))),
    h('pre', {}, JSON.stringify({ build_contract: ev.build_contract, infrastructure: ev.infrastructure, capabilities: ev.capabilities }, null, 2)));
}

/* ---------- download / publish ---------- */
async function downloadZip() {
  const vid = currentVersionId(); if (!vid) return;
  try {
    const res = await api(`/api/v28/projects/${pid()}/export?version_id=${encodeURIComponent(vid)}`, { raw: true });
    const blob = await res.blob();
    const a = h('a', { href: URL.createObjectURL(blob), download: `${S.projectId}-148ai.zip` });
    document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  } catch (e) { $('publishNote').textContent = explain(e); }
}
function publishNotConfigured() { $('publishNote').textContent = t('publishNotConfigured'); $('publishNote').focus?.(); }

/* ---------- project dialog ---------- */
function openProjectDialog() {
  const p = S.projects.find(x => x.id === S.projectId);
  $('renameInput').value = p ? p.title : ''; $('newProjectInput').value = ''; $('projectMsg').textContent = '';
  $('archiveBtn').disabled = !p; $('renameBtn').disabled = !p;
  $('projectDialog').showModal();
}
async function dialogAction(fn, okKey) {
  const msg = $('projectMsg'); msg.className = 'msg'; msg.textContent = '';
  try { await fn(); msg.className = 'msg ok'; msg.textContent = t(okKey); }
  catch (e) { msg.textContent = explain(e); }
}


/* ---------- conversation (Unified Conversation OS) ---------- */
const convPath = () => `/api/v28/projects/${pid()}/conversation`;
// Gate 1 has its own route: approving the spec is not a chat message (an empty message is refused as empty_message).
const specApprovalPath = () => `/api/v28/projects/${pid()}/spec-approval`;
// One source of truth for the approval state (the owner, 2026-11-16; production 11:10-11:11 the same day): the panel's
// plan was fetched while the spec was still waiting for approval, and stayed on screen after the chat approved it --
// the chat said "approve the budget" while the panel still said "the spec is not approved" and offered that button
// again. A plan that waits on an approval is dropped the moment the conversation moves past it, and fetched again.
const APPROVAL_STATE_BLOCKERS = ['spec_not_approved', 'plan_not_verified', 'approval_state_unavailable', 'brief_stale'];
function planWaitsOnApproval(p) {
  return Boolean(p) && (p.blockers || []).some(b => APPROVAL_STATE_BLOCKERS.includes(b.code));
}
function applyConversation(view) {
  if (view.discovery && S.disc && view.discovery.brief.revision !== S.disc.brief.revision) S.plan = null;
  const moved = (view.plan_id || null) !== ((S.chat && S.chat.plan_id) || null)
    || ((view.turn && view.turn.actions) || []).some(a => a.type === 'approve_build');
  if (moved && planWaitsOnApproval(S.plan)) S.plan = null;
  S.chat = view;
  if (view.discovery) S.disc = view.discovery;
  S.arch = view.plan || null;
  renderChat(); renderDiscovery(); renderArch(); renderTabs();
  const acts = (view.turn && view.turn.actions) || [];
  // A complete, buildable brief: fetch the real quote (free; nothing is reserved).
  if (S.disc && S.disc.complete && !S.plan && !S.updatingAnswers) requestBriefPlan(false);
}
// Only a server that does not have the conversation (503 conversation_not_ready: migration pending) switches to
// the guided questionnaire. Anything else -- a network blip, a timeout, a 500 -- is shown with a retry, and the
// conversation stays the mode (2026-10-30: any error used to switch for the whole session).
function conversationNotInstalled(e) {
  return e instanceof ApiError && e.status === 503 && !!e.detail && e.detail.error === 'conversation_not_ready';
}
async function restoreConversation() {
  const project = S.projectId;     // the requirements belong to the project they were read for (Michael 2026-11-13)
  try { const view = await api(`${convPath()}?lang=${S.lang}`); if (stillOn(project)) applyConversation(view); }
  catch (e) {
    if (!stillOn(project)) return;
    if (!conversationNotInstalled(e)) {
      S.chat = { messages: [], unavailable: explain(e), retry: true };
      renderChat(); renderTabs();
      return;
    }
    // Conversation storage missing (migration pending): say so and keep the guided
    // questionnaire (the /discovery flow) working underneath.
    S.chat = { messages: [], unavailable: explain(e), fallback: true };
    try { const disc = await api(`${discPath()}?lang=${S.lang}`); if (!stillOn(project)) return; S.disc = disc; }
    catch { S.disc = null; }
    renderChat(); renderDiscovery(); renderTabs();
  }
}
let chatBusy = false;
function whenVisible() {
  if (document.visibilityState !== 'hidden') return Promise.resolve();
  return new Promise(r => document.addEventListener('visibilitychange', function f() {
    if (document.visibilityState !== 'hidden') { document.removeEventListener('visibilitychange', f); r(); }
  }));
}
async function sendChat(body, shownText, path) {
  if (chatBusy || !S.projectId) return;
  const retrySignature=JSON.stringify([S.projectId,body]);
  if(!S.chatRetry || S.chatRetry.signature!==retrySignature)S.chatRetry={signature:retrySignature,key:newKey()};
  chatBusy = true; $('chatSend').disabled = true; $('composerMsg').textContent = '';
  const project = S.projectId;
  S.inFlight = { project, text: String(body.message || '').trim() };
  const pending = shownText ? { role: 'customer', content: shownText, pending: true } : null;
  if (pending) { S.chat = S.chat || { messages: [] }; S.chat.messages = [...(S.chat.messages || []), pending]; renderChat(); }
  try {
    const url = `${(path || convPath)()}?lang=${S.lang}`, payload = { ...body, request_key: S.chatRetry.key };
    let view;
    // 2026-11-09: iOS Safari drops an open request when the page goes to the background (switching apps to take a
    // screenshot), and the customer saw "no connection" although the server had answered. The send is idempotent
    // per request_key, so a dropped request is re-sent quietly with the SAME key -- after the page is visible
    // again -- and the server returns the answer it already stored instead of asking the model twice.
    for (let attempt = 0; ; attempt++) {
      try { view = await api(url, { method: 'POST', body: payload }); break; }
      catch (err) {
        if (err.status !== 0 || err.detail === 'timeout' || attempt >= 3) throw err;
        await whenVisible();
        await new Promise(r => setTimeout(r, 1500 * (attempt + 1)));
      }
    }
    S.chatRetry=null;
    // review F5 (2026-11-22): the customer moved to another project while this was in flight -- the reply is that
    // project's, shown when it is opened again; this composer and this view are not touched
    if (S.projectId !== project) { if ((projectDrafts.get(project) || '').trim() === S.inFlight.text) projectDrafts.delete(project); return true; }
    S.forceScroll = true;
    applyConversation(view);
    if (body.message) $('chatInput').value = '';
    autoGrow();
    return true;
  } catch (e) {
    if (pending) { S.chat.messages = S.chat.messages.filter(m => m !== pending); renderChat(); }
    $('composerMsg').textContent = explain(e);
    return false;
  } finally { chatBusy = false; S.inFlight = null; $('chatSend').disabled = false; }
}
async function submitChat(e) {
  if (e) e.preventDefault();
  const text = $('chatInput').value.trim();
  const images = window.VE ? VE.pendingCount() : 0;
  if (!text && !images) return;
  if (!S.projectId) {
    // the first message of a new conversation creates its project, named from the message (the owner, 2026-11-22);
    // the attached images stay attached through the switch to the new project (VE.reset)
    if (S.creatingProject) return;
    S.creatingProject = true; S.keepAttachments = true;
    try { await createProject(titleFrom(text)); }
    catch (err) { $('chatInput').value = text; autoGrow(); $('composerMsg').textContent = explain(err); return; }
    finally { S.creatingProject = false; S.keepAttachments = false; }
  }
  if (S.chat && S.chat.fallback && !images) { startGuidedFallback(text); return; }
  let ids = [];
  if (images) {
    try { ids = await VE.uploadPending(); }
    catch (err) { $('composerMsg').textContent = explain(err); return; }
  }
  const sent=await sendChat({ message: text, ...(ids.length ? { attachment_ids: ids } : {}) }, text || `📎 ${ids.length}`);
  if (sent && ids.length && window.VE) VE.clearPending();
  // a send that failed gives the words back to the box (the project switch above had emptied it)
  if (!sent && text && !$('chatInput').value) { $('chatInput').value = text; autoGrow(); }
}
async function startGuidedFallback(text) {
  // Only when the conversation API is not installed here: the existing guided
  // discovery (brief revisions, approval, plan) takes the request instead.
  $('composerMsg').textContent = '';
  try {
    S.disc = await api(`${discPath()}?lang=${S.lang}`, { method: 'POST', body: { prompt: text, mode: 'guided', request_key: newKey() } });
    S.chat.messages = [...S.chat.messages, { role: 'customer', content: text },
      { role: 'assistant', content: t('fallbackNote') }];
    $('chatInput').value = '';
    renderChat(); renderDiscovery(); openTab('req');
    if (S.disc.complete) await requestBriefPlan(true);
  } catch (e) { $('composerMsg').textContent = explain(e); }
}
function answerQuick(q, value, label) {
  if (S.chat && S.chat.fallback) { sendAnswers({ [q.id]: value }); return; }   // guided flow (no conversation API here)
  sendChat({ answers: { [q.id]: value } }, label);
}
function quickReplies(questions, said) {
  // the message already asks the question in words (supervisor._label_carries_its_question): the card adds the buttons only
  return h('div', { class: 'quick' }, questions.map(q => h('div', {},
    q.text && !String(said || '').includes(q.text) ? h('div', { class: 'qq' }, q.text) : null,
    h('div', { class: 'opts' },
      ...(q.kind === 'choice' ? q.options.map(o => h('button', { type: 'button', onclick: () => answerQuick(q, o.value, o.label) },
        o.label, q.suggested === o.value ? ' ✓' : '')) : []),
      q.delegable ? h('button', { type: 'button', class: 'del', onclick: () => answerQuick(q, '__delegate__', t('delegateShort')) }, t('delegateShort')) : null))));
}
// owner 2026-11-16: the approval screen offers each window with its one-sentence benefit; the customer approves (ticks)
// or rejects (leaves unticked) each one. read() is what the approval sends: every offered window, true or false.
function windowsChoice(offer) {
  if (!offer || !offer.length) return { node: null, read: () => undefined };
  const boxes = offer.map(w => h('input', { type: 'checkbox', checked: w.state === 'approved', 'data-window': w.id }));
  const node = h('fieldset', { class: 'windowsChoice' }, h('legend', {}, t('windowsTitle')),
    h('p', { class: 'hint' }, t('windowsHint')),
    ...offer.map((w, i) => h('label', { class: 'windowOpt', 'data-window': w.id }, boxes[i],
      h('span', { class: 'wtext' }, h('b', {}, w.label), h('span', { class: 'benefit' }, w.benefit)))));
  return { node, read: () => Object.fromEntries(offer.map((w, i) => [w.id, Boolean(boxes[i].checked)])) };
}
function actionButtons(actions) {
  const out = [];
  for (const a of actions || []) {
    if (a.type === 'edit_requirements') out.push(h('button',{type:'button',class:'secondary',onclick:beginBriefEdit},t('editAll')));
    // #339 (Michael 2026-11-13): a blocked customer decision links straight to the Requirements tab
    if (a.type === 'open_requirements') out.push(h('button',{type:'button',class:'primary',onclick:beginBriefEdit},t('openRequirements')));
    if (a.type === 'approve_spec') {
      // Michael 2026-11-10 condition 3: an incomplete fact canon needs an explicit tick before the spec is approved.
      const incomplete = a.canon && a.canon.status === 'CANON_INCOMPLETE';
      const wins = windowsChoice(a.windows);
      if (wins.node) out.push(wins.node);
      const btn = h('button', { type: 'button', disabled: incomplete, onclick: () => sendChat(
        { brief_fingerprint: a.brief_fingerprint, canon_ack: incomplete ? Boolean(box && box.checked) : false,
          windows: wins.read() },
        t('actApproveSpec'), specApprovalPath) }, t('actApproveSpec'));
      const box = incomplete ? h('input', { type: 'checkbox', id: 'canonAck', onchange: (e) => { btn.disabled = !e.target.checked; } }) : null;
      if (incomplete) out.push(h('label', { class: 'canonAck', for: 'canonAck' }, box, ' ', t('canonAck')));
      out.push(btn);
    }
    if (a.type === 'show_plan') out.push(h('button', { type: 'button', class: 'secondary', onclick: () => { if (S.plan) openTab('plan'); else requestBriefPlan(true); } }, t('actShowPlan')));
    // warehouse 69 (A0): a type without an output profile was refused; the one action is to describe a site or app instead
    if (a.type === 'describe_web_instead') out.push(h('button', { type: 'button', class: 'primary', onclick: () => { const i = $('chatInput'); if (i) i.focus(); } }, t('actDescribeInstead')));
    // warehouse 77c: a failed build's one action in the conversation -- back to the approval screen to try again
    if (a.type === 'retry_build') out.push(h('button', { type: 'button', class: 'primary', onclick: async () => { if (!S.plan) await requestBriefPlan(); openTab('plan'); const b = $('confirmBtn'); if (b) b.focus(); } }, t('actRetryBuild')));
    if (a.type === 'approve_build') out.push(h('button', { type: 'button', onclick: async () => { if (!S.plan) await requestBriefPlan(); openTab('plan'); const b = $('confirmBtn'); if (b) b.focus(); } }, t('actApprove')));
    if (a.type === 'confirm_modification') out.push(h('button', { type: 'button', disabled: modActive() || !currentVersionId(),
      onclick: () => { $('followup').value = a.request; openTab('change'); sendModification(a.attachment_ids && a.attachment_ids.length ? { attachment_ids: a.attachment_ids } : null); } }, t('actConfirmMod')));
  }
  return out.length ? h('div', { class: 'acts' }, out) : null;
}
function renderChat() {
  const box = $('thread'); if (!box) return;
  const msgs = (S.projectId && S.chat && S.chat.messages) || [];   // a new conversation (no project yet) opens on the welcome
  const kids = [];
  if(S.chat && S.chat.interpreter) kids.push(h('p',{class:'chatMode hint'},
    S.chat.interpreter==='model-via-worker'?t('aiMode'):t('guidedMode')));
  if (!msgs.length) kids.push(h('div', { class: 'welcomeChat' }, h('h2', {}, t('chatHelloTitle')), h('p', {}, t('chatHello')),
    S.chat && S.chat.unavailable ? h('p', { class: 'msg' }, S.chat.unavailable) : null,
    S.chat && S.chat.retry ? h('button', { type: 'button', class: 'secondary', onclick: restoreConversation }, t('tryAgain')) : null,
    h('div', { class:'workspaceExamples' }, t('workspaceExamples').map(([label, prompt]) =>
      h('button', { type:'button', class:'secondary', onclick:() => {
        $('chatInput').value = prompt; autoGrow(); $('chatInput').focus();
      } }, label)))));
  else if (S.chat && S.chat.unavailable) kids.push(h('p', { class: 'msg' }, S.chat.unavailable));
  const lastAssistant = msgs.map(m => m.role).lastIndexOf('assistant');
  msgs.forEach((m, i) => {
    // review F3 (2026-11-22): the speaker, said to screen readers; an aria-label on a plain div is not read
    const bubble = h('div', { class: `bubble ${m.role}`, dir: 'auto' }, h('span', { class: 'sr' }, `${m.role === 'customer' ? t('you') : t('assistant')}: `), m.content);
    if (m.role === 'assistant' && m.ai_status === 'fallback')
      bubble.append(h('p', { class: 'hint aiFallback' }, t('aiFallback')));
    if (m.attachments && m.attachments.length) bubble.append(h('div', { class: 'thumbs' }, m.attachments.map(a =>
      h('img', { src: `/api/v28/projects/${pid()}/attachments/${encodeURIComponent(a.id)}`, alt: t('attachedImage'), loading: 'lazy', width: 72, height: 72 }))));
    if (i === lastAssistant) {
      // CEO 2026-11-08: no questionnaire. Only the buttons the server sent with this turn; never the detector's
      // pending questions as a fallback (Venice asks in words; the server sends none while she leads).
      const qs = (S.chat.turn && S.chat.turn.questions) || [];
      if (qs.length) bubble.append(quickReplies(qs, m.content));
      const acts = actionButtons(m.actions && m.actions.length ? m.actions : ((S.chat.turn && S.chat.turn.actions) || []));
      if (acts) bubble.append(acts);
    }
    kids.push(bubble);
  });
  // Build/change state lines come from the server records (no invented progress).
  if (S.build && S.build.status) {
    const st = String(S.build.status).toLowerCase();
    const counts = (S.tasks && S.tasks.tasks || []).reduce((a, x) => { a[x.state] = (a[x.state] || 0) + 1; return a; }, {});
    const label = st === 'ready' ? t('buildReady') : st === 'failed' ? friendlyError(S.build) :
      st === 'cancelled' ? t('buildCancelled') : `${t('buildRunning')}${S.build.phase ? ` · ${S.build.phase}` : ''}`;
    kids.push(h('button', { type: 'button', class: `statusline ghost${st === 'failed' ? ' bad' : ''}`, onclick: () => openTab('build') }, label,
      counts.SUCCEEDED ? ` · ${counts.SUCCEEDED} ${t('ts_SUCCEEDED')}` : ''));
  }
  if (S.mod && S.mod.status) kids.push(h('button', { type: 'button', class: 'statusline ghost', onclick: () => openTab('change') },
    S.mod.status === 'READY_FOR_REVIEW' ? t('modReview') : S.mod.status === 'ACCEPTED' ? t('modAccepted') : t('modQueued')));
  const atEnd = box.scrollHeight - box.scrollTop - box.clientHeight < 60;
  box.replaceChildren(...kids);
  if (atEnd || msgs.length < 3 || S.forceScroll) { box.scrollTop = box.scrollHeight; S.forceScroll = false; }
}
function renderArch() {
  const panel = $('archPanel'); const a = S.arch;
  if (!a) { panel.hidden = true; return; }
  panel.hidden = false;
  const f = a.feasibility || {};
  const byId = Object.fromEntries((a.tasks || []).map(x => [x.task_id, x]));
  const layers = (a.layers || []).map((ids, i) => h('div', { class: 'layer' }, h('b', {}, `${t('layer')} ${i + 1}`),
    ids.map(id => { const x = byId[id] || {}; return h('span', { class: `tk ${x.executable === false ? 'gap' : ''}`, title: `${x.department} · ${x.agent}` },
      `${x.department} · ${ttLabel(x.task_type || id)}${x.conditional ? ` (${t('ifNeeded')})` : ''}`); })));
  const limits = (f.findings || []).filter(x => x.outcome !== 'FEASIBLE');
  const blockedByBuildGate = Boolean(S.plan && !S.plan.can_build);
  panel.replaceChildren(h('h2', {}, t('archTitle')),
    h('p', {}, h('b', {}, `${t('feasibility')}: `), h('span', { class: `feas ${blockedByBuildGate ? 'bad' : f.outcome === 'FEASIBLE' ? 'ok' : f.outcome === 'FEASIBLE_WITH_CONSTRAINTS' ? 'warn' : 'bad'}` }, blockedByBuildGate ? t('readinessBlocked') : (t(`f_${f.outcome}`) || f.outcome))),
    limits.length ? h('details', {}, h('summary', {}, `${t('constraints')} (${limits.length})`),
      h('ul', {}, limits.map(x => h('li', {}, findingLabel(x),
        h('details', {}, h('summary', {}, S.lang==='he'?'פרטים טכניים':'Technical details'),
          `${x.item}: ${x.reason}`, x.alternative ? ` — ${x.alternative}` : ''))))) : null,
    h('div', { class: 'layers' }, layers),
    (S.chat && S.chat.interpreter === 'deterministic') ? h('p', { class: 'hint' }, t('interpreterNote')) : null);
}
// 2026-11-14 (Michael b2): the plan refusal names the subscription's own reason (b.detail, the closed list of
// build_readiness.PLAN_REASONS), never a generic line that contradicts it ('does not authorize variable cost').
// Michael 2026-11-14 (b3): what media the build makes, one line each, from the contract (p.media) -- never from the
// goal sentence, which is the intake model's free text and dropped the butcher's hero image.
function mediaLines(p) {
  const kinds = T[S.lang].mediaKinds || T.en.mediaKinds;
  return ((p && p.media) || []).map(m => {
    const kind = kinds[m.purpose] || kinds[m.key] || T.en.mediaKinds[m.key] || m.key;
    const line = m.subject ? `${kind}: ${m.subject}` : kind;
    return m.required ? line : `${line} (${t('mediaOptional')})`;
  });
}
// One line per blocker in the plan tab (top level so the test runs this exact function).
function blockerTitle(b, p) {
  if(b.code==='capability_not_feasible')return capabilityBlockMessage(b);
  if(b.code==='requirements_invalid')return S.lang==='he'?'יש להשלים או לתקן פרטים בבקשה.':'Complete or correct the request.';
  if (b.code.startsWith('infrastructure_')) {
    const kind = ((p.infrastructure || []).find(i => b.code.startsWith(`infrastructure_${i.kind}_`)) || {}).kind;
    return t('b_infrastructure')(kind ? t(`k_${kind}`) : b.code);
  }
  if (b.code.startsWith('image_provider_')) return t('b_image_provider');
  if (b.code === 'plan_cannot_authorize_cost') return planReason(b);
  return T[S.lang][`b_${b.code}`] || T.en[`b_${b.code}`] || t('unknownBlocker');
}
function planReason(b) {
  const reason = String((b && b.detail) || '');
  return (T[S.lang].planReasons || {})[reason] || T.en.planReasons[reason] || t('b_plan_cannot_authorize_cost');
}
function capabilityBlockMessage(detail) {
  const action = S.lang==='he' ? 'ערכו את הדרישה או פנו לתמיכה להשלמת היכולת.' : 'Edit the requirement or contact support to enable this capability.';
  const rows = (Array.isArray(detail.findings) ? detail.findings : []).map(x => {
    if(!x || typeof x!=='object' || typeof x.item!=='string' || !x.item.trim())return '';
    // The existing Hebrew sign-in label already names the capability and offers an action.
    if(S.lang==='he' && x.item.startsWith('sign-in'))return findingLabel(x);
    return `${findingLabel(x)} ${x.alternative || action}`;
  }).filter(Boolean);
  const intro = S.lang==='he' ? 'הבנייה לא התחילה: ' : 'The build did not start: ';
  return intro + (rows.length ? rows.join(' ') : (detail.message || action));
}
function findingLabel(x) {
  if(S.lang!=='he')return `${x.item}: ${x.reason || 'not supported yet'}`;
  if(x.item.startsWith('sign-in'))return 'התחברות והרשאות באתר שייבנה עדיין אינן זמינות. אפשר לערוך את הדרישה או להשאיר אותה להמשך.';
  if(x.item==='publishing')return 'פרסום בכתובת קבועה עדיין אינו זמין. קיימות תצוגה פרטית והורדת קוד.';
  if(x.item==='independent model review')return 'מודל הביקורת עשוי להיות מאותו ספק של מודל הכתיבה. בדיקות הקוד עדיין נדרשות לפני שחרור.';
  const names={'code generation':'יצירת קוד','behavioural acceptance':'בדיקות התנהגות','release policy':'מדיניות שחרור'};
  if(names[x.item])return `${names[x.item]}: ${x.outcome==='FEASIBLE_WITH_CONSTRAINTS'?'קיימות מגבלות שיש לבדוק':'דרושה בדיקה נוספת'}`;
  return `${x.item}: ${x.reason || 'עדיין אינה נתמכת'}`;
}
const TT = {
  he: { requirements:'דרישות', plan_and_quote:'תוכנית והצעת מחיר', architecture:'ארכיטקטורה', implementation:'כתיבת הקוד',
    unit_tests:'בדיקות בסביבה מבודדת', repair:'תיקונים', preview_smoke:'הפעלת תצוגה', behavioural_acceptance:'בדיקות התנהגות',
    browser_flow:'בדיקת דפדפן', visual_qa:'בדיקה חזותית', security_scan:'סריקת אבטחה', code_review:'סקירת קוד',
    release_gate:'שער שחרור', version_release:'שמירת גרסה', cost_settlement:'חישוב עלות' },
  ar: { requirements:'المتطلبات', plan_and_quote:'الخطة وعرض السعر', architecture:'تصميم البنية', implementation:'كتابة الكود',
    unit_tests:'فحوصات في بيئة معزولة', repair:'إصلاحات', preview_smoke:'تشغيل المعاينة', behavioural_acceptance:'فحوصات السلوك',
    browser_flow:'فحص في المتصفح', visual_qa:'فحص بصري', security_scan:'فحص الأمان', code_review:'مراجعة الكود',
    release_gate:'بوابة الإطلاق', version_release:'حفظ النسخة', cost_settlement:'حساب التكلفة' },
};
const ttLabel = k => (TT[S.lang] && TT[S.lang][k]) || String(k).replace(/_/g, ' ');
async function loadTasks() {
  if (!S.build || !S.build.id) return;
  const project = S.projectId;
  try { const tasks = await api(`/api/v28/projects/${pid()}/builds/${encodeURIComponent(S.build.id)}/plan`);
    if (stillOn(project)) S.tasks = tasks; }
  catch { S.tasks = null; }
}
function renderTasks() {
  const box = $('taskBoard'); if (!box) return;
  const tasks = (S.tasks && S.tasks.bound && S.tasks.tasks) || [];
  if (!tasks.length) { box.replaceChildren(); return; }
  const cls = st => ({ SUCCEEDED: 'ok', RUNNING: 'warn', REPAIRING: 'warn', FAILED: 'bad', BLOCKED: 'bad' })[st] || 'muted';
  // Founder 2026-10-11: customers see "build progress"; who-does-what stays one click away.
  const done = tasks.filter(x => x.state === 'SUCCEEDED').length;
  box.replaceChildren(h('details', { class: 'tech' }, h('summary', {}, `${t('tasksTitle')} · ${done}/${tasks.length}`),
    h('ul', { class: 'taskboard' }, tasks.map(x => h('li', {},
      h('span', { class: 'dept' }, x.department), h('span', {}, ttLabel(x.task_type)),
      h('span', { class: `pill ${cls(x.state)}` }, t(`ts_${x.state}`) || x.state))))));
}

/* ---------- context tabs (requirements / plan / build / change / versions / details) ---------- */
const TABS = [['built', ['builtPanel', 'newBuildRow']], ['req', ['discoveryPanel']], ['plan', ['archPanel', 'planPanel']],
  ['build', ['progressPanel']], ['change', ['modifyPanel']], ['versions', ['versionsPanel']], ['details', ['evidencePanel']]];
function renderTabs() {
  const nav = $('ctxTabs'); if (!nav) return;
  $('ctxTitle').textContent=S.tab==='req'?t('editAll'):S.tab?t(`tab_${S.tab}`):t('editAll');
  const avail = TABS.filter(([, ids]) => ids.some(id => $(id) && !$(id).hidden));
  if (S.tab && !avail.find(([k]) => k === S.tab)) S.tab = null;
  const cards = avail.filter(([key]) => key !== 'versions');
  $('projectCards').hidden = !cards.length;
  nav.replaceChildren(...cards.map(([k]) => h('button', { type: 'button', 'aria-pressed': S.tab === k ? 'true' : 'false',
    'aria-controls': 'ctx', onclick: () => { $('projectCards').open = false; openTab(S.tab === k ? null : k); } }, t(`tab_${k}`))));
  for (const [k, ids] of TABS) for (const id of ids) { const el = $(id); if (el) el.classList.toggle('active', S.tab === k); }
  $('ctx').classList.toggle('open', Boolean(S.tab));
  document.querySelector('.composerHint').hidden = Boolean(S.build || S.versions.length);
}
function openTab(k) {
  S.tab = k;
  if (k === 'versions') window.VE?.setPane('versions');
  else if ($('workspaceView').dataset.pane === 'versions') window.VE?.setPane('chat');
  renderTabs();
}
const tabObserver = new MutationObserver(() => renderTabs());

/* ---------- workspace shell: sidebar, splitter, preview size ---------- */
let sidebarOpener=null;
function syncSidebar() {
  const mobile=matchMedia('(max-width:900px)').matches,ws=$('workspaceView');
  const open=mobile?ws.classList.contains('sb-open'):!ws.classList.contains('sb-collapsed');
  $('sbScrim').hidden=!(mobile&&open);$('sidebar').inert=!open;
  $('sidebar').setAttribute('aria-hidden',String(!open));
  for(const id of ['sbOpen','mobileMenuBtn','sbCollapse'])$(id).setAttribute('aria-expanded',String(open));
  if(mobile&&open){$('sidebar').setAttribute('role','dialog');$('sidebar').setAttribute('aria-modal','true');}
  else{$('sidebar').removeAttribute('role');$('sidebar').removeAttribute('aria-modal');}
}
function openSidebar(e) {
  sidebarOpener=e?.currentTarget||$('sbOpen');const ws=$('workspaceView');
  if(matchMedia('(max-width:900px)').matches)ws.classList.add('sb-open');
  else{ws.classList.remove('sb-collapsed');try{localStorage.removeItem('148ai_sb');}catch{}}
  syncSidebar();$('sbCollapse').focus();
  refreshWorkspaceBalance();
}
function closeSidebarMobile() {
  const wasOpen=$('workspaceView').classList.contains('sb-open');
  $('workspaceView').classList.remove('sb-open');syncSidebar();
  if(wasOpen&&sidebarOpener)sidebarOpener.focus();
}
function syncStageButtons() {
  const ws = $('workspaceView'); if (!ws) return;
  const hidden = ws.classList.contains('stage-hidden') && !matchMedia('(max-width:900px)').matches;
  $('togglePreviewBtn').setAttribute('aria-expanded', hidden ? 'false' : 'true');
  const max = ws.classList.contains('stage-max');
  $('expandPreviewBtn').setAttribute('aria-pressed', max ? 'true' : 'false');
  $('expandPreviewBtn').textContent = max ? '⤡' : '⤢';
  $('expandPreviewBtn').setAttribute('aria-label', t(max ? 'shrinkPreview' : 'expandPreview'));
  $('expandPreviewBtn').title = t(max ? 'shrinkPreview' : 'expandPreview');
}
function setStageWidth(pct) {
  const v = Math.max(24, Math.min(60, pct));  // the conversation always keeps a usable width
  document.documentElement.style.setProperty('--stage-w', `${v}%`);
  try { localStorage.setItem('148ai_stage_w', String(v)); } catch { /* convenience only */ }
}
function autoGrow() { const el = $('chatInput'); el.style.height = 'auto'; el.style.height = `${Math.min(el.scrollHeight, 192)}px`; }
function wireWorkspace() {
  const ws = $('workspaceView');
  try { const w = Number(localStorage.getItem('148ai_stage_w')); if (w) setStageWidth(w); } catch { /* default width */ }
  try { if (localStorage.getItem('148ai_sb') === 'collapsed') ws.classList.add('sb-collapsed'); } catch { /* default */ }
  $('chatForm').addEventListener('submit', submitChat);
  $('chatInput').addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) submitChat(e); });
  $('chatInput').addEventListener('input', autoGrow);
  $('sbSearch').addEventListener('input', renderSidebarProjects);
  $('sbAll').addEventListener('click', () => openWorkspaceDialog('allProjects'));
  $('sbTemplates').addEventListener('click', () => openWorkspaceDialog('workspaceTemplates'));
  $('sbDomains').addEventListener('click', () => openWorkspaceDialog('workspaceDomains'));
  $('sbCollapse').addEventListener('click', () => {
    if(matchMedia('(max-width:900px)').matches){closeSidebarMobile();return;}
    ws.classList.add('sb-collapsed');try{localStorage.setItem('148ai_sb','collapsed');}catch{}
    syncSidebar();$('sbOpen').focus();
  });
  $('sbOpen').addEventListener('click',openSidebar);
  $('mobileMenuBtn').addEventListener('click',openSidebar);
  matchMedia('(max-width:900px)').addEventListener('change',()=>{closeSidebarMobile();syncSidebar();});
  document.addEventListener('keydown',e=>{
    if(!ws.classList.contains('sb-open')||!matchMedia('(max-width:900px)').matches)return;
    if(e.key==='Escape'){e.preventDefault();closeSidebarMobile();}
    if(e.key==='Tab'){
      const items=[...$('sidebar').querySelectorAll('button,input,a[href],summary')].filter(el=>!el.disabled&&el.getClientRects().length);
      const first=items[0],last=items[items.length-1];
      if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
      else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
    }
  });
  syncSidebar();
  $('sbScrim').addEventListener('click', closeSidebarMobile);
  $('langBtn2').addEventListener('change', e => { $('langBtn').value = e.target.value; $('langBtn').dispatchEvent(new Event('change')); });
  $('logoutBtn2').addEventListener('click', logout);
  $('togglePreviewBtn').addEventListener('click', () => {
    if (matchMedia('(max-width:900px)').matches) ws.classList.toggle('stage-mobile');
    else { ws.classList.toggle('stage-hidden'); ws.classList.remove('stage-max'); }
    syncStageButtons();
  });
  $('closePreviewBtn').addEventListener('click', () => { ws.classList.remove('stage-max', 'stage-mobile'); if (!matchMedia('(max-width:900px)').matches) ws.classList.add('stage-hidden'); syncStageButtons(); });
  $('expandPreviewBtn').addEventListener('click', () => { ws.classList.toggle('stage-max'); syncStageButtons(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && ws.classList.contains('stage-max')) { ws.classList.remove('stage-max'); syncStageButtons(); } });
  // Drag the separator: the preview width follows the pointer (keyboard: arrows).
  const sp = $('splitter');
  const rtl = () => document.documentElement.dir === 'rtl';
  sp.addEventListener('pointerdown', e => {
    sp.setPointerCapture(e.pointerId); sp.classList.add('drag');
    const frame = $('previewFrame'); frame.style.pointerEvents = 'none';
    const move = ev => {
      const r = ws.getBoundingClientRect();
      const fromEdge = rtl() ? ev.clientX - r.left : r.right - ev.clientX;
      setStageWidth(fromEdge / r.width * 100);
    };
    const up = () => { sp.classList.remove('drag'); frame.style.pointerEvents = ''; sp.removeEventListener('pointermove', move); sp.removeEventListener('pointerup', up); };
    sp.addEventListener('pointermove', move); sp.addEventListener('pointerup', up);
  });
  sp.addEventListener('keydown', e => {
    const cur = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--stage-w')) || 42;
    const grow = (e.key === 'ArrowLeft') !== rtl() ? 1 : -1;
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') { e.preventDefault(); setStageWidth(cur + 3 * grow); }
  });
  for (const [, ids] of TABS) for (const id of ids) if ($(id)) tabObserver.observe($(id), { attributes: true, attributeFilter: ['hidden'] });
  syncStageButtons();
}

/* ---------- wiring ---------- */
function wire() {
  $('ctxMinimize').addEventListener('click',()=>openTab(null));
  $('authForm').addEventListener('submit', e => { e.preventDefault(); authSubmit('login'); });
  $('passwordToggle').addEventListener('click', () => {
    const input = $('password'), toggle = $('passwordToggle');
    const showing = input.type === 'password';
    input.type = showing ? 'text' : 'password';
    toggle.setAttribute('aria-pressed', String(showing));
    const label = t(showing ? 'hidePassword' : 'showPassword');
    toggle.setAttribute('aria-label', label); toggle.title = label;
    input.focus({ preventScroll: true });
  });
  $('registerBtn').addEventListener('click', () => authSubmit('register'));
  $('logoutBtn').addEventListener('click', logout);
  $('langBtn').addEventListener('change', e => { if (!(e.target.value in LANGS)) return; S.lang = e.target.value; localStorage.setItem('148ai_lang', S.lang); applyLang(); });
  $('projectSelect').addEventListener('change', e => selectProject(e.target.value));
  $('projectMenuBtn').addEventListener('click', openProjectDialog);
  for (const b of [$('textSizeBtn'), $('textSizeBtn2')]) b.addEventListener('click', nextTextSize);
  wireWorkspace();
  $('renameBtn').addEventListener('click', () => dialogAction(async () => {
    await api(`/api/v28/projects/${pid()}`, { method: 'PATCH', body: { title: $('renameInput').value.trim() } });
    await loadProjects();
  }, 'renamed'));
  $('archiveBtn').addEventListener('click', () => dialogAction(async () => {
    await api(`/api/v28/projects/${pid()}/archive`, { method: 'POST' });
    await loadProjects();
  }, 'archived'));
  $('newProjectBtn').addEventListener('click', () => dialogAction(async () => {
    await createProject($('newProjectInput').value.trim());
  }, 'created'));
  // Founder 2026-10-08: a new product never reuses the open project; it gets
  // its own named project and an empty request box.
  $('newBuildBtn').addEventListener('click', openNewProject);
  $('newProjectTopBtn').addEventListener('click', openNewProject);
  $('cancelBuildBtn').addEventListener('click', cancelBuild);
  // Directive 2026-10-09 §11: an offline state, not a frozen page.
  const syncOnline = () => { $('offlineBanner').hidden = navigator.onLine !== false; };
  window.addEventListener('online', syncOnline); window.addEventListener('offline', syncOnline); syncOnline();
  $('modifyBtn').addEventListener('click', sendModification);
  // A fresh owner link on every refresh (links expire; the cookie may be blocked in an iframe).
  $('refreshPreviewBtn').addEventListener('click', () => { S.previewAccess = null; delete $('previewFrame').dataset.access; renderPreview(); });
  $('downloadBtn').addEventListener('click', downloadZip);
  $('publishBtn').addEventListener('click', publishNotConfigured);
}

async function boot() {
  wire(); applyLang();
  localStorage.removeItem('148ai_token'); // tokens from older versions are never kept in page storage
  try { await enterWorkspace(); return; } catch { /* no valid session cookie */ }
  showView();
}
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});
document.addEventListener('DOMContentLoaded', boot);
