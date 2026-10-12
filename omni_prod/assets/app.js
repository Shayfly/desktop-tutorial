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
    signinTitle:'כניסה לחשבון', email:'אימייל', password:'סיסמה', passwordHint:'לפחות 10 תווים.',
    login:'כניסה', register:'יצירת חשבון חינם',
    firstProject:'הפרויקט הראשון שלכם', projectName:'שם הפרויקט', createProject:'יצירת פרויקט',
    request:'מה תרצו לבנות?', build:'המשך', planHint:'שום בנייה ושום חיוב לא מתחילים לפני שתאשרו סיכום ועלות.',
    modeLegend:'איך תרצו להמשיך?', modeGuided:'שיחת אפיון מודרכת', modeGuidedHint:'נשאל כמה שאלות קצרות — גם על צבעים, גופן וסגנון. אפשר לענות "אין לי העדפה".',
    modeRecommend:'המערכת תמליץ ותבחר', modeRecommendHint:'נבחר עבורכם לפי מה שכתבתם, ותראו הכול בסיכום לפני אישור.',
    discTitle:'בואו נדייק את הבקשה', discProgress:(a, r) => `${a} החלטות · נשארו ${r}`, why:'למה שואלים: ',
    delegate:'אין לי העדפה — בחרו עבורי', delegateWill:v => `(נבחר: ${v})`, suggestedFromRequest:'(לפי מה שכתבתם)',
    next:'המשך', skipGroup:'דלגו על השאלות האלה', pauseNote:'הכול נשמר. אפשר לחזור ולהמשיך גם אחרי רענון או ממכשיר אחר.',
    decided:'מה כבר החלטנו', change:'שינוי', save:'שמירה', cancel:'ביטול', needAnswer:q => `צריך תשובה ל: ${q}`,
    discDone:'האפיון הושלם. זה הסיכום — בדקו אותו לפני אישור.', showSummary:'הצגת הסיכום והעלות',
    src_message:'מהבקשה שלכם', src_answer:'התשובה שלכם', src_delegated:'נבחר עבורכם', src_default:'ברירת מחדל',
    sumGoal:'המטרה', sumIncluded:'כלול', sumExcluded:'לא כלול בשלב זה', sumAssumptions:'החלטות שבחרנו עבורכם (אפשר לשנות)',
    updateRequest:'עדכן את הבקשה', approveBuild:'אשר והתחל בנייה', approvalExpired:'האישור פג. בדקו את הסיכום ואשרו שוב.',
    builtTitle:'מה נבנה עד עכשיו', newBuild:'מוצר חדש בפרויקט חדש', newProjectPlus:'+ פרויקט חדש', newProjectHint:'לכל מוצר פרויקט משלו. תנו לו שם, ואז תתארו מה לבנות.', nameRequired:'צריך לתת לפרויקט שם.', builtVersion:'גרסה נוכחית', files:'קבצים',
    progress:'התקדמות הבנייה', modifyTitle:'מה תרצו לשנות?', modifySend:'שליחת שינוי', versions:'גרסאות',
    evidence:'פרטים טכניים ועדויות', refresh:'רענון', openTab:'פתיחה בלשונית חדשה',
    noPreview:'כאן תופיע האפליקציה אחרי שהבנייה תסתיים.', download:'הורדת קוד המקור (ZIP)', publish:'פרסום',
    publishNotConfigured:'הפרסום לאוויר עוד לא מוגדר בשרת הזה. אפשר להוריד את הקוד ולבדוק בתצוגה המקדימה.',
    manageProject:'ניהול פרויקט', rename:'שינוי שם', saveName:'שמירת השם', archive:'העברה לארכיון',
    newProject:'פרויקט חדש', close:'סגירה',
    promptPlaceholder:'לדוגמה: מערכת לניהול תורים למספרה, עם יומן לספרים, הזמנה עצמית ללקוחות ותזכורות במייל.',
    planTitle:'התוכנית', understood:'מה הבנו', roles:'משתמשים', data:'נתונים', integrations:'חיבורים',
    capabilities:'יכולות שהבנייה צריכה', infrastructure:'תשתית לאפליקציה', cost:'עלות',
    estimated:'הערכה', maximum:'מקסימום מאושר', questions:'שאלות לפני שמתחילים', blockersTitle:'מה חוסם כרגע',
    creditsRequired:'קרדיטים לבנייה', creditsRemaining:'קרדיטים שנותרו', quoteStatus:'תמחור',
    confirm:'אשרו והתחילו בנייה', editRequest:'עריכת הבקשה', costUnknown:'לא ניתן לחשב',
    byPipeline:'בתוך הבנייה', byProvider:'ספק חיצוני', required:'נדרש', optional:'רשות',
    st_LIVE:'פעיל', st_PARTIAL:'מוגדר, לא נבדק', st_NOT_CONFIGURED:'לא מוגדר', st_BLOCKED:'חסום',
    st_SELF_CONTAINED:'מובנה באפליקציה', st_PRICED:'מאושר', st_UNKNOWN:'לא ניתן לתמחר', st_NOT_AUTHORIZED:'לא מאושר',
    stepPlanning:'תכנון', stepContract:'חוזה בנייה', stepInfra:'תשתית', stepAssets:'נכסים (אייקון ותמונות)',
    stepGenerate:'יצירת קוד, בנייה, בדיקות ותיקונים', stepGates:'בדיקות איכות, אבטחה וזכויות', stepPreview:'תצוגה מקדימה',
    noteGenerate:'הבנייה, הבדיקות והתיקונים רצים בשלב אחד. מספר סבבי התיקון מדווח בסיום.',
    repairs:n=>`סבבי תיקון: ${n}`, queued:'ממתין בתור', started:'הבנייה התחילה', buildReady:'הבנייה הסתיימה בהצלחה.',
    buildFailed:'הבנייה נכשלה',
    stopBuild:'עצירת הבנייה', stopChange:'עצירת השינוי', stopChangeConfirm:'לעצור את השינוי? נחויב רק על מה שכבר נוצל.', modCancelled:'השינוי נעצר.', stopConfirm:'לעצור את הבנייה? נחויב רק על מה שכבר נוצל, והגרסה לא תיווצר.',
    stopping:'העצירה תתבצע בסיום הצעד הנוכחי (עד כמה דקות).', buildCancelled:'הבנייה נעצרה. נחויב רק על מה שכבר נוצל.',
    liveLog:'מה קורה עכשיו', logEmpty:'ממתין לשרת הבנייה…',
    checkingApproval:'מאמתים אישור ותקציב — הבנייה עדיין לא התחילה.',
    errCodes:{verification_failed:'הקוד שנוצר לא עבר את הבדיקות האוטומטיות גם אחרי סבבי תיקון.',
      release_policy_failed:'המוצר לא סומן כמוכן: אחת הבדיקות המחייבות (הפעלה, בדיקת התנהגות, בדיקת דפדפן או סקירת איכות) לא עברה או לא רצה. הפירוט בפרטים הטכניים.',
      quality_gate_failed:'הקוד עבד, אבל לא עמד ברף האיכות הנדרש גם אחרי סבבי תיקון.',
      preview_not_ready:'הקוד עבר את הבדיקות, אבל האתר לא עלה בהפעלת ניסיון ולכן לא אושר.',
      security_gate_failed:'נמצאה בעיית אבטחה בקוד שנוצר, ולכן הוא לא אושר.',
      rights_gate_not_clear:'הגרסה נשמרה, אבל חסר אישור זכויות לפני פרסום.',
      unsupported_dependency:'הקוד ביקש ספרייה חיצונית שעדיין לא נתמכת בפלטפורמה.',
      worker_lost:'הבנייה הפסיקה להגיב ושוחררה. לא חויבו קרדיטים. אפשר לנסות שוב.',
      worker_exception:'אירעה תקלה פנימית במהלך הבנייה. הצוות קיבל את הפרטים.',
      model_budget_exhausted:'הבנייה הגיעה לתקרת העלות שנקבעה לה ונעצרה לפני שהושלמה. אפשר לנסות שוב.',
      model_unavailable:'ספקי ה־AI לא היו זמינים כרגע (עומס או מכסה). אפשר לנסות שוב בעוד כמה דקות.',
      provider_quota_exhausted:'לפחות ספק AI אחד דיווח שנגמרה המכסה או יתרת הקרדיטים. אין כרגע ספק חלופי שהשלים את הבקשה. בדקו את הספק שמופיע בהמשך.',
      model_policy_blocked:'מדיניות השימוש במודלים לא אפשרה את הבנייה בסביבה הזו.',
      capability_gate_failed:'יכולת נדרשת (למשל יצירת תמונות) לא אומתה, ולכן הבנייה לא אושרה.'},
    techDetails:'פרטים טכניים', previewStarting:'מפעילים תצוגה מקדימה…', previewRunning:'התצוגה המקדימה פועלת.',
    previewNotPreviewable:'הגרסה הזאת לא ניתנת להצגה מקדימה: ', previewUnavailable:'תצוגה מקדימה לא זמינה בשרת הזה: ',
    previewFailed:'התצוגה המקדימה נכשלה: ', previewExpired:'התצוגה המקדימה פגה. אפשר להפעיל אותה מחדש.',
    startPreview:'הפעלת תצוגה מקדימה',
    duplicateBuild:'התוכנית הזאת כבר נבנית או נבנתה — מוצגת הבנייה הקיימת. כדי לבנות שוב, עדכנו את הבקשה.',
    current:'נוכחית', restore:'שחזור לגרסה הזו', restored:'שוחזר. נוצרה גרסה חדשה.', noVersions:'עדיין אין גרסאות.',
    modQueued:'השינוי נשלח. בונים גרסה מועמדת ובודקים אותה…', modReview:'הגרסה המועמדת עברה את הבדיקות. מה תרצו לעשות?',
    accept:'אישור השינוי', reject:'דחייה', modAccepted:'השינוי אושר ונשמר כגרסה חדשה.', modRejected:'השינוי נדחה.',
    modFailed:'השינוי נכשל: ', classification:'סיווג',
    gates:'בדיקות', usage:'שימוש בספקים', costActual:'עלות בפועל', costBasis:'בסיס העלות', warnings:'אזהרות',
    requestIds:'מזהי בקשות', tokens:'טוקנים (קלט/פלט)', none:'אין',
    backendMissing:'<b>בנייה לא זמינה בשרת הזה.</b> נדרשים PostgreSQL ואחסון S3. אפשר להירשם, לנהל פרויקטים ולראות תוכנית ועלות.',
    emailUnverified:'האימייל עדיין לא אומת.',
    err401:'פג תוקף ההתחברות. היכנסו שוב.', err402:'אין מספיק קרדיטים או שהמסלול לא מאפשר זאת: ',
    err403:'אין הרשאה לפעולה הזו.', err404:'לא נמצא.', err409:'צריך הבהרה לפני שממשיכים.',
    err503:'השירות הזה עוד לא מוגדר בשרת: ', errNet:'אין חיבור לשרת. בדקו את החיבור ונסו שוב.', errTimeout:'השרת לא ענה תוך 30 שניות. הפעולה אולי עוד רצה — רעננו בעוד רגע לפני שתנסו שוב.',
    err5xx:'שגיאה בשרת. נסו שוב בעוד רגע; אם זה חוזר, שלחו צילום מסך.', offline:'אין חיבור לאינטרנט. מה שמוצג עשוי להיות לא מעודכן; הפעולות יחזרו לעבוד כשהחיבור יחזור.',
    dataPersistent:'הנתונים שתזינו באפליקציה נשמרים גם אחרי הפעלה מחדש ובגרסה הבאה (אין עדיין גיבוי).',
    shareLabel:'מי יכול לפתוח', sharePRIVATE:'רק אני (פרטי)', shareSHARED:'כל מי שיש לו קישור שיתוף', sharePUBLIC:'כולם (ציבורי)', shareLink:'קישור שיתוף', dataTemporary:'נתונים זמניים: מה שתזינו יימחק כשהתצוגה תיעצר.',
    needPrompt:'כתבו לפחות כמה מילים על האפליקציה.', needEmail:'הזינו אימייל וסיסמה של 10 תווים לפחות.',
    registered:'החשבון נוצר.', created:'הפרויקט נוצר.', renamed:'השם נשמר.', archived:'הפרויקט הועבר לארכיון.',
    downloadReady:'ההורדה התחילה.', untitled:'פרויקט חדש',
    lifecycle:'מחזור בנייה מלא: תכנון, קוד, התקנה, בנייה, בדיקות, תיקונים, תצוגה וייצוא', operatorDetails:'פרטים למפעיל השרת',
    b_durable_backend_not_configured:'הבנייה דורשת שרת עם PostgreSQL ואחסון S3.',
    b_infrastructure:k=>`התשתית של האפליקציה לא מוכנה: ${k}`, b_image_provider:'יצירת אייקון ותמונות לא מוגדרת.',
    b_plan_cannot_authorize_cost:'המסלול הנוכחי לא מאשר עלות משתנה בתשלום.',
    b_qa_budget_denied:'תקציב אב־הטיפוס אינו מאפשר את הבנייה הזו. בדקו את יתרת בדיקות הפיתוח או נסו בקשה מצומצמת יותר.',
    qaBudgetTitle:'תקציב בדיקות אב־טיפוס — פרטי', qaBudgetRemaining:'יתרה פנימית מוערכת',
    qaBudgetLimit:'מגבלת הרשאה לבנייה אחת', qaBudgetActual:'אלה רישומי העלות של 148AI; לא יתרות אצל ספקי ה־AI.',
    b_cost_quote_unknown:'חלק מהעלויות של הבנייה לא ידועות, ולכן אי אפשר לאשר אותה.',
    k_database:'מסד נתונים', k_auth_session:'התחברות וסשנים', k_object_storage:'אחסון קבצים', k_scheduled_http:'משימות מתוזמנות', k_outbound:'מיילים ו-webhooks',
    newChat:'שיחה חדשה · פרויקט חדש', searchProjects:'חיפוש פרויקטים', canBuildTitle:'מה אפשר לבנות היום', noMatches:'לא נמצאו פרויקטים',
    hideSidebar:'הסתרת הסרגל', showSidebar:'הצגת הסרגל', previewToggle:'תצוגה', expandPreview:'הגדלת התצוגה', shrinkPreview:'הקטנת התצוגה',
    hidePreview:'סגירת התצוגה', resizePreview:'גרירה לשינוי רוחב התצוגה', send:'שליחה',
    chatPlaceholder:'כתבו מה תרצו לבנות או לשנות…', you:'אתם', assistant:'148AI',
    chatHelloTitle:'מה נבנה היום?', chatHello:'ספרו במילים שלכם מה אתם צריכים — אני אשאל רק מה שחשוב, אציע תוכנית ועלות, ושום דבר לא ייבנה בלי האישור שלכם.',
    tab_req:'דרישות', tab_plan:'תוכנית ועלות', tab_build:'בנייה', tab_change:'שינוי', tab_versions:'גרסאות', tab_details:'פרטים', tab_built:'המוצר',
    actShowPlan:'הצגת הסיכום, התוכנית והעלות', actApprove:'לאישור והתחלת בנייה', actConfirmMod:'שליחת השינוי לביצוע',
    delegateShort:'בחרו עבורי', convNotReady:'השיחה החכמה עוד לא מותקנת בשרת הזה (חסר עדכון מסד נתונים 036). השאלות המודרכות עובדות כרגיל.', fallbackNote:'השיחה החכמה עוד לא מותקנת בשרת הזה, אז עברתי לשאלות המודרכות. הן מופיעות בלשונית "דרישות" ונשמרות.', archTitle:'תוכנית העבודה (מחלקות ומשימות)', feasibility:'היתכנות', layer:'שלב',
    f_FEASIBLE:'אפשר לבנות', f_FEASIBLE_WITH_CONSTRAINTS:'אפשר לבנות, עם מגבלות', f_BLOCKED:'חסום כרגע', f_UNSUPPORTED:'לא נתמך עדיין', f_UNKNOWN:'לא ידוע',
    constraints:'מגבלות', ifNeeded:'אם צריך', tasksTitle:'פרטים טכניים: מי עושה מה (מהרישום בשרת)', buildRunning:'הבנייה רצה', interpreterNote:'הפירוש נעשה בכללים קבועים (ללא מודל AI)',
    ts_SUCCEEDED:'הושלם', ts_RUNNING:'רץ', ts_PENDING:'ממתין', ts_READY:'מוכן', ts_FAILED:'נכשל', ts_BLOCKED:'חסום', ts_CANCELLED:'לא בוצע', ts_REPAIRING:'בתיקון', ts_NOT_RECORDED:'לא נרשם',
  },
  en: {
    skip:'Skip to content', projects:'Projects', manage:'Manage', logout:'Sign out',
    hero:'Describe your web app.', lead:'148AI plans, builds, tests and previews it.',
    how1:'Write what the app should do and for whom.', how2:'Get a plan and a maximum cost, then approve it.',
    how3:'Watch the build, try it in a preview, ask for changes and download the code.',
    scope:'Today: web apps and SaaS. Mobile, games and media are not available yet.',
    signinTitle:'Sign in', email:'Email', password:'Password', passwordHint:'At least 10 characters.',
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
    sumGoal:'Goal', sumIncluded:'Included', sumExcluded:'Not included for now', sumAssumptions:'Chosen for you (you can change these)',
    updateRequest:'Update the request', approveBuild:'Approve and start building', approvalExpired:'The approval expired. Review the summary and approve again.',
    builtTitle:'What has been built', newBuild:'New product in a new project', newProjectPlus:'+ New project', newProjectHint:'Each product gets its own project. Name it, then describe what to build.', nameRequired:'Give the project a name.', builtVersion:'Current version', files:'files',
    progress:'Build progress', modifyTitle:'What would you like to change?', modifySend:'Send change', versions:'Versions',
    evidence:'Technical details and evidence', refresh:'Refresh', openTab:'Open in new tab',
    noPreview:'Your app appears here once the build finishes.', download:'Download source (ZIP)', publish:'Publish',
    publishNotConfigured:'Publishing is not configured on this server yet. You can download the code and test it in the preview.',
    manageProject:'Manage project', rename:'Rename', saveName:'Save name', archive:'Archive',
    newProject:'New project', close:'Close',
    promptPlaceholder:'For example: an appointment system for a barbershop, with a calendar for barbers, self-booking for customers and email reminders.',
    planTitle:'The plan', understood:'What we understood', roles:'Users', data:'Data', integrations:'Integrations',
    capabilities:'Capabilities the build needs', infrastructure:'App infrastructure', cost:'Cost',
    estimated:'Estimate', maximum:'Approved maximum', questions:'Questions before we start', blockersTitle:'What is blocking right now',
    creditsRequired:'Credits for this build', creditsRemaining:'Credits remaining', quoteStatus:'Pricing',
    confirm:'Approve and start build', editRequest:'Edit request', costUnknown:'Cannot be calculated',
    byPipeline:'in the build', byProvider:'external provider', required:'required', optional:'optional',
    st_LIVE:'Live', st_PARTIAL:'Configured, not verified', st_NOT_CONFIGURED:'Not configured', st_BLOCKED:'Blocked',
    st_SELF_CONTAINED:'Built into the app', st_PRICED:'Authorized', st_UNKNOWN:'Cannot be priced', st_NOT_AUTHORIZED:'Not authorized',
    stepPlanning:'Planning', stepContract:'Build contract', stepInfra:'Infrastructure', stepAssets:'Assets (icon and images)',
    stepGenerate:'Generating code, building, testing and repairing', stepGates:'Quality, security and rights gates', stepPreview:'Preview',
    noteGenerate:'Build, tests and repairs run as one step. The number of repair rounds is reported at the end.',
    repairs:n=>`Repair rounds: ${n}`, queued:'Waiting in queue', started:'Build started', buildReady:'Build finished successfully.',
    buildFailed:'Build failed',
    stopBuild:'Stop the build', stopChange:'Stop the change', stopChangeConfirm:'Stop the change? Only what was already used is charged.', modCancelled:'The change was stopped.', stopConfirm:'Stop the build? Only what was already used is charged, and no version is created.',
    stopping:'The build stops when the current step ends (up to a few minutes).', buildCancelled:'The build was stopped. Only what was already used is charged.',
    liveLog:'What is happening now', logEmpty:'Waiting for the build server…',
    checkingApproval:'Checking approval and budget — no build has started yet.',
    errCodes:{verification_failed:'The generated code did not pass its automated checks, even after repair rounds.',
      release_policy_failed:'The product was not marked ready: a mandatory check (start-up, behaviour, browser or quality review) did not pass or did not run. See the technical details.',
      quality_gate_failed:'The code works but did not meet the quality bar, even after repair rounds.',
      preview_not_ready:'The code passed its checks but the site did not start in a trial run, so it was not accepted.',
      security_gate_failed:'A security problem was found in the generated code, so it was not accepted.',
      rights_gate_not_clear:'The version was saved but needs rights clearance before publishing.',
      unsupported_dependency:'The code asked for an external library the platform does not support yet.',
      worker_lost:'The build stopped responding and was released. No credits were charged. You can try again.',
      worker_exception:'An internal error occurred during the build. The details were recorded.',
      model_budget_exhausted:'The build reached its cost ceiling and stopped before it was finished. You can try again.',
      model_unavailable:'The AI providers were not available right now (load or quota). Try again in a few minutes.',
      provider_quota_exhausted:'An AI provider reported exhausted quota/credits, and no fallback completed. Check the named provider below.',
      model_policy_blocked:'The model usage policy did not allow this build in this environment.',
      capability_gate_failed:'A required capability (such as image generation) was not verified, so the build was not accepted.'},
    techDetails:'Technical details', previewStarting:'Starting preview…', previewRunning:'Preview is running.',
    previewNotPreviewable:'This version cannot be previewed: ', previewUnavailable:'Preview is not available on this server: ',
    previewFailed:'Preview failed: ', previewExpired:'The preview expired. You can start it again.',
    startPreview:'Start preview',
    duplicateBuild:'This plan is already building or built — showing that build. Update the request to build again.',
    current:'Current', restore:'Restore this version', restored:'Restored as a new version.', noVersions:'No versions yet.',
    modQueued:'Change sent. Building and testing a candidate version…', modReview:'The candidate version passed its checks. What would you like to do?',
    accept:'Accept change', reject:'Reject', modAccepted:'Change accepted and saved as a new version.', modRejected:'Change rejected.',
    modFailed:'Change failed: ', classification:'Classification',
    gates:'Checks', usage:'Provider usage', costActual:'Actual cost', costBasis:'Cost basis', warnings:'Warnings',
    requestIds:'Request IDs', tokens:'Tokens (in/out)', none:'None',
    backendMissing:'<b>Building is not available on this server.</b> It needs PostgreSQL and S3 storage. You can sign up, manage projects and see a plan and cost.',
    emailUnverified:'Your email is not verified yet.',
    err401:'Your session expired. Sign in again.', err402:'Not enough credits or not allowed on your plan: ',
    err403:'You do not have access to this.', err404:'Not found.', err409:'Clarification is needed before continuing.',
    err503:'This service is not configured on the server yet: ', errNet:'Cannot reach the server. Check your connection and try again.', errTimeout:'The server did not answer within 30 seconds. The action may still be running — refresh in a moment before trying again.',
    err5xx:'Server error. Try again in a moment; if it repeats, send a screenshot.', offline:'You are offline. What you see may be out of date; actions work again when the connection returns.',
    dataPersistent:'Data you enter in the app survives a restart and the next version (no backup yet).',
    shareLabel:'Who can open it', sharePRIVATE:'Only me (private)', shareSHARED:'Anyone with the share link', sharePUBLIC:'Everyone (public)', shareLink:'Share link', dataTemporary:'Temporary data: what you enter is deleted when the preview stops.',
    needPrompt:'Write at least a few words about the app.', needEmail:'Enter an email and a password of at least 10 characters.',
    registered:'Account created.', created:'Project created.', renamed:'Name saved.', archived:'Project archived.',
    downloadReady:'Download started.', untitled:'New project',
    lifecycle:'Full build lifecycle: plan, code, install, build, test, repair, preview and export', operatorDetails:'Details for the server operator',
    b_durable_backend_not_configured:'Building needs a server with PostgreSQL and S3 storage.',
    b_infrastructure:k=>`App infrastructure is not ready: ${k}`, b_image_provider:'Icon and image generation is not configured.',
    b_plan_cannot_authorize_cost:'Your current plan does not authorize paid variable cost.',
    b_qa_budget_denied:'The prototype QA budget cannot authorize this build. Check the testing balance or reduce the request.',
    qaBudgetTitle:'Private prototype testing budget', qaBudgetRemaining:'Estimated internal allowance left',
    qaBudgetLimit:'Per-build testing limit', qaBudgetActual:'These are 148AI spend records, not your AI providers’ account balances.',
    b_cost_quote_unknown:'Some build costs are unknown, so the build cannot be authorized.',
    k_database:'database', k_auth_session:'sign-in and sessions', k_object_storage:'file storage', k_scheduled_http:'scheduled jobs', k_outbound:'email and webhooks',
    newChat:'New chat · new project', searchProjects:'Search projects', canBuildTitle:'What can be built today', noMatches:'No projects found',
    hideSidebar:'Hide sidebar', showSidebar:'Show sidebar', previewToggle:'Preview', expandPreview:'Enlarge preview', shrinkPreview:'Restore preview size',
    hidePreview:'Close preview', resizePreview:'Drag to resize the preview', send:'Send',
    chatPlaceholder:'Describe what you want to build or change…', you:'You', assistant:'148AI',
    chatHelloTitle:'What shall we build today?', chatHello:'Tell me in your own words what you need. I only ask what matters, propose a plan and a cost, and nothing is built without your approval.',
    tab_req:'Requirements', tab_plan:'Plan & cost', tab_build:'Build', tab_change:'Change', tab_versions:'Versions', tab_details:'Details', tab_built:'Product',
    actShowPlan:'Show summary, plan and cost', actApprove:'Go to approval', actConfirmMod:'Send this change',
    delegateShort:'Choose for me', convNotReady:'The conversation is not installed on this server yet (database migration 036 pending). Guided questions still work.', fallbackNote:'The conversation is not installed on this server yet, so I switched to the guided questions. They are in the "Requirements" tab and are saved.', archTitle:'Work plan (departments and tasks)', feasibility:'Feasibility', layer:'Step',
    f_FEASIBLE:'Buildable', f_FEASIBLE_WITH_CONSTRAINTS:'Buildable with limitations', f_BLOCKED:'Blocked for now', f_UNSUPPORTED:'Not supported yet', f_UNKNOWN:'Unknown',
    constraints:'Limitations', ifNeeded:'if needed', tasksTitle:'Technical details: who does what (from the server records)', buildRunning:'Build running', interpreterNote:'Interpreted with fixed rules (no AI model)',
    ts_SUCCEEDED:'done', ts_RUNNING:'running', ts_PENDING:'waiting', ts_READY:'ready', ts_FAILED:'failed', ts_BLOCKED:'blocked', ts_CANCELLED:'not run', ts_REPAIRING:'repairing', ts_NOT_RECORDED:'not recorded',
  },
};

const S = {
  lang: localStorage.getItem('148ai_lang') || 'he',
  signedIn: false,
  me: null, projects: [], projectId: localStorage.getItem('148ai_project') || '',
  durable: false, plan: null, build: null, versions: [], previewId: null, preview: null,
  mod: null, timers: {},
};
Object.assign(T.he, { updateDraft:'עדכן את התוכנית', editAll:'עריכת הבקשה', minimizeContext:'מזעור החלון',
  colourExample:'למשל: ורוד עדין עם שמנת וזהב', fontSample:'כך ייראה הטקסט באתר שלכם', fontUnavailable:'הדוגמה עדיין לא נטענה',
  guidedMode:'מצב שאלון מובנה — שיחת AI אינה פעילה כרגע', aiMode:'מצב שיחת AI מוגדר — הזמינות תלויה בספק ובתקציב', draftNote:'אפשר לשנות כמה פרטים. רק ״עדכן״ יחיל את השינויים.',
  attachmentSchema:'צירוף תמונות אינו זמין בפריסה הזאת: נדרש עדכון מסד הנתונים (038). התמונה והטקסט נשמרו כאן לניסיון חוזר.' });
Object.assign(T.en, { updateDraft:'Update the plan', editAll:'Edit requirements', minimizeContext:'Minimize panel',
  colourExample:'For example: soft pink with cream and gold', fontSample:'This is how your website text will look', fontUnavailable:'Preview has not loaded yet',
  guidedMode:'Guided questionnaire — AI conversation is not active right now', aiMode:'AI conversation configured — availability depends on provider and budget', draftNote:'Change as many details as you like. Only Update applies the changes.',
  attachmentSchema:'Image attachments need database migration 038 on this deployment. Your image and text remain here for retry.' });

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
  const timer = ctl ? setTimeout(() => ctl.abort(), 30000) : null;
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
  if (err.detail && err.detail.error === 'attachments_not_ready') return t('attachmentSchema');
  if (err.detail && err.detail.error === 'capability_not_feasible') return S.lang==='he'
    ? 'הבנייה לא התחילה: אחת הדרישות עדיין אינה נתמכת. בדקו את החסימות בתוכנית או ערכו את הבקשה.'
    : 'The build did not start: a requirement is not supported yet. Review the plan blockers or edit the request.';
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

/* ---------- language ---------- */
function applyLang() {
  document.documentElement.lang = S.lang;
  document.documentElement.dir = S.lang === 'he' ? 'rtl' : 'ltr';
  document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll('[data-i18n-label]').forEach(el => { el.setAttribute('aria-label', t(el.dataset.i18nLabel)); el.title = t(el.dataset.i18nLabel); });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => { el.placeholder = t(el.dataset.i18nPlaceholder); });
  for (const b of [$('langBtn'), $('langBtn2')]) { b.textContent = S.lang === 'he' ? 'English' : 'עברית'; b.lang = S.lang === 'he' ? 'en' : 'he'; }
  $('chatInput').placeholder = t('chatPlaceholder');
  $('publishNote').textContent = t('publishNotConfigured');
  document.title = S.lang === 'he' ? '148AI · סביבת יצירה' : '148AI · Creator workspace';
  renderBanner(); renderDiscovery(); renderPlan(); renderTrack(); renderVersions(); renderEvidence(); renderPreview(); renderMod();
  renderProjects(); renderChat(); renderArch(); renderTabs(); syncStageButtons();
  if (window.VE) VE.render();
}

/* ---------- auth ---------- */
function signOutLocal() {
  S.signedIn = false; S.me = null;
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
    await enterWorkspace();
  } catch (e) { msg.textContent = explain(e); }
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
  $('emptyProjects').hidden = S.projects.length > 0;
  $('chatForm').hidden = S.projects.length === 0;
  $('chatCol').classList.toggle('no-project', S.projects.length === 0);
  $('projectMenuBtn').disabled = !S.projectId;
  // Sidebar: the real project list (one persistent conversation per project), filtered locally.
  const q = ($('sbSearch').value || '').trim().toLowerCase();
  const items = S.projects.filter(p => !q || String(p.title || '').toLowerCase().includes(q));
  $('sbProjects').replaceChildren(...(items.length ? items.map(p => h('li', {},
    h('button', { type: 'button', 'aria-current': p.id === S.projectId ? 'true' : 'false', title: p.title || t('untitled'),
      onclick: () => { closeSidebarMobile(); if (p.id !== S.projectId) selectProject(p.id); } },
      h('span', { class: `st ${String(p.last_build_status || p.status || '').toLowerCase()}`, 'aria-hidden': 'true' }),
      h('span', { class: 'ttl' }, p.title || t('untitled'))))) : [h('li', { class: 'hint' }, t('noMatches'))]));
  const cur = S.projects.find(p => p.id === S.projectId);
  $('chatTitle').textContent = cur ? (cur.title || t('untitled')) : '148AI';
}
async function createProject(title) {
  const p = await api('/api/v28/projects', { method: 'POST', body: { title: title || t('untitled') } });
  S.projectId = p.id;
  await loadProjects();
  // A new project starts with an empty conversation (selectProject cleared the
  // box before loading); never clear again here -- the user may already be typing.
  $('chatInput').focus();
}
function openNewProject() {
  closeSidebarMobile();
  $('newProjectName').value = ''; $('newProjectMsg').textContent = '';
  $('newProjectDialog').showModal(); $('newProjectName').focus();
}
async function submitNewProject(e) {
  e.preventDefault();
  const name = $('newProjectName').value.trim();
  if (!name) { $('newProjectMsg').textContent = t('nameRequired'); return; }
  $('newProjectCreate').disabled = true;
  try { await createProject(name); $('newProjectDialog').close(); }
  catch (err) { $('newProjectMsg').textContent = explain(err); }
  finally { $('newProjectCreate').disabled = false; }
}
async function selectProject(id) {
  Object.values(S.timers).forEach(clearTimeout); S.timers = {};
  S.projectId = id || ''; localStorage.setItem('148ai_project', S.projectId);
  S.plan = null; S.build = null; S.buildAdmissionError = ''; S.preview = null; S.previewId = null; S.mod = null; S.versions = []; S.newBuildOpen = false;
  S.disc = null; S.editQ = null; S.editDraft = null; S.chatRetry = null; S.answerRetry = null; S.chat = null; S.arch = null; S.tasks = null; S.tab = null;
  if (S.projectId !== S.lastShownProject) { $('chatInput').value = ''; $('followup').value = ''; $('composerMsg').textContent = ''; }
  S.lastShownProject = S.projectId;
  $('planPanel').hidden = true; $('progressPanel').hidden = true;
  S.lastChange = null;
  if (window.VE) VE.reset();
  applyLang();
  if (!S.projectId) return;
  await loadVersions();
  await restoreMod();
  await restoreConversation();
  await restoreBuild();
}
// A build that is still queued/running survives a reload: its track, live log
// and stop button come back (directive 2026-10-09 §12).
async function restoreBuild() {
  try {
    const d = await api(`/api/v28/projects/${pid()}/builds/latest`);
    const b = d && d.build;
    if (!b || isTerminal(b.status) || S.build) return;
    S.build = { id: b.build_id, status: b.status, phase: '', evidence: {} };
    renderTrack(); pollBuild();
  } catch (e) { /* older server: nothing to restore */ }
}

/* ---------- plan + quote ---------- */
/* ---------- discovery conversation (directive 2026-10-09 §4-5) ---------- */
const newKey = () => (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random()).slice(0, 60);
const discPath = () => `/api/v28/projects/${pid()}/discovery`;
/* The old "describe + choose a mode" composer is replaced by the conversation
   (Unified Conversation OS): the supervisor decides how many questions to ask. */
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
    else openTab('req');
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
  try {
    S.plan = await api(`/api/v28/projects/${pid()}/build-contracts`, { method: 'POST',
      body: { prompt: S.disc.prompt, brief_revision: S.disc.brief.revision } });
    S.build = null; renderDiscovery(); renderPlan(); renderTrack(); if (open === true) openTab('plan');
  } catch (e) { const m = $('discMsg'); if (m) m.textContent = explain(e); }
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
function renderPlan() {
  const panel = $('planPanel'); const p = S.plan;
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
  ].flat() : [];
  const kids = [
    h('h2', {}, t('planTitle')),
    ...briefKids,
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
    const title = b => {
      if(b.code==='capability_not_feasible')return S.lang==='he'?'אחת הדרישות עדיין אינה נתמכת. יש לערוך אותה או להמתין להשלמת היכולת.':'A requirement is not supported yet. Edit it or wait for support.';
      if(b.code==='requirements_invalid')return S.lang==='he'?'יש להשלים או לתקן פרטים בבקשה.':'Complete or correct the request.';
      if (b.code.startsWith('infrastructure_')) {
        const kind = (p.infrastructure.find(i => b.code.startsWith(`infrastructure_${i.kind}_`)) || {}).kind;
        return t('b_infrastructure')(kind ? t(`k_${kind}`) : b.code);
      }
      if (b.code.startsWith('image_provider_')) return t('b_image_provider');
      return T[S.lang][`b_${b.code}`] || T.en[`b_${b.code}`] || b.message;
    };
    const titles = [...new Set(p.blockers.map(title))];
    kids.push(h('h3', {}, t('blockersTitle')), h('ul', { class: 'blockers' }, titles.map(x => h('li', {}, x))),
      ...p.blockers.flatMap(b=>(b.findings||[]).filter(f=>f&&typeof f.item==='string').map(f=>h('p',{},findingLabel(f)))),
      h('details', { class: 'tech' }, h('summary', {}, t('operatorDetails')),
        h('ul', { dir: 'ltr' }, p.blockers.map(b => h('li', {}, h('code', {}, b.code), ': ', b.message)))));
  }
  kids.push(h('div', { class: 'row' },
    h('button', { id: 'confirmBtn', disabled: !p.can_build || Boolean(S.build && !isTerminal(S.build.status)), onclick: startBuild },
      p.brief_revision ? t('approveBuild') : t('confirm')),
    h('button', { class: 'secondary', onclick: () => {
      if (S.disc) { beginBriefEdit(); }
      else $('chatInput').focus(); } }, p.brief_revision ? t('updateRequest') : t('editRequest'))));
  kids.push(h('p',{id:'planMsg',class:'msg',role:'alert'},S.buildAdmissionError||''));
  panel.replaceChildren(...kids);
}

/* ---------- build ---------- */
const isTerminal = s => ['ready', 'failed', 'cancelled', 'READY', 'FAILED', 'CANCELLED'].includes(s);
let buildStarting = false;
async function startBuild() {
  if (!S.plan || !S.plan.can_build || buildStarting) return;
  // One click = one request; the server also returns the existing build for
  // an already-approved plan instead of starting a second one.
  buildStarting = true;
  S.buildAdmissionError='';
  // Show approval progress immediately, without inventing a build ID or task.
  $('progressPanel').hidden = false;
  $('track').replaceChildren();
  $('buildMsg').textContent = t('checkingApproval');
  openTab('build');
  try {
    // Directive 2026-10-09 §5: the server binds this approval to the user,
    // the brief revision, the plan and the price; the build consumes it once.
    let approvalId = null;
    if (S.plan.brief_revision) {
      const a = await api(`/api/v28/projects/${pid()}/approvals`, { method: 'POST',
        body: { build_contract_id: S.plan.build_contract_id, brief_revision: S.plan.brief_revision } });
      approvalId = a.approval_id;
    }
    const d = await api(`/api/v28/projects/${pid()}/builds`, { method: 'POST',
      body: { prompt: (S.disc && S.disc.prompt) || 'build', build_contract_id: S.plan.build_contract_id,
              approval_id: approvalId } });
    S.build = { id: d.build_id, status: d.status || 'queued', phase: d.duplicate ? '' : 'QUEUED', evidence: {} };
    renderPlan(); renderTrack(); renderBuilt(); openTab('build'); pollBuild();
    if (d.duplicate) $('buildMsg').textContent = t('duplicateBuild');
  } catch (e) {
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
  if (!S.build) return;
  try {
    const d = await api(`/api/v28/projects/${pid()}/builds/${encodeURIComponent(S.build.id)}`);
    S.build = { ...S.build, ...d };
    await pollEvents();
    await loadTasks();
    renderTrack(); renderEvidence(); renderTasks(); renderChat();
    if (isTerminal(d.status)) {
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
  S.timers.build = setTimeout(pollBuild, 2500);
}
/* Directive 2026-10-09 §10/§12: live log + stop. */
async function pollEvents() {
  const b = S.build; if (!b || !b.id) return;
  if (b.logFor !== b.id) { b.logFor = b.id; b.log = []; b.logAfter = 0; }
  try {
    const d = await api(`/api/v28/projects/${pid()}/builds/${encodeURIComponent(b.id)}/events?after=${b.logAfter || 0}`);
    for (const e of d.events || []) { b.log.push(e); b.logAfter = Math.max(b.logAfter || 0, e.seq); }
  } catch (e) { /* the log is a convenience; status polling carries on */ }
}
function renderLog() {
  const b = S.build; const box = $('liveLog'); const list = $('liveLogList');
  if (!b) { box.hidden = true; return; }
  box.hidden = false;
  const fmt = iso => { try { return new Date(iso).toLocaleTimeString(S.lang === 'he' ? 'he-IL' : 'en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' }); } catch (e) { return ''; } };
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
  const FAIL_STEP = { infrastructure_not_configured: 1, capability_not_configured: 2, capability_gate_failed: 2,
    worker_exception: 3, preview_not_ready: 3, model_budget_exhausted: 3, model_unavailable: 3, provider_quota_exhausted: 3, model_policy_blocked: 3, verification_failed: 3, release_policy_failed: 4, quality_gate_failed: 4, security_gate_failed: 4, rights_gate_not_clear: 4 };
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
    if (status === 'queued') return push(t(key), 'pending', idx === 0 ? t('queued') : note);
    if (status === 'cancelled') return push(t(key), 'skipped', null);
    return push(t(key), reached === idx ? 'active' : reached > idx ? 'done' : 'pending', note);
  };
  const infraEv = ev.infrastructure; const capEv = ev.capabilities;
  backendStep('stepInfra', 1, ['infrastructure_not_configured'], infraEv === null && status === 'ready' ? t('none') : null);
  backendStep('stepAssets', 2, ['capability_not_configured', 'capability_gate_failed'], null);
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
  renderControls(); renderLog();
  const msg = $('buildMsg'); msg.className = 'msg';
  if (status === 'ready') { msg.className = 'msg ok'; msg.textContent = t('buildReady'); }
  else if (status === 'cancelled') { msg.textContent = t('buildCancelled'); }
  else if (status === 'failed') {
    // Customer-facing reason; the raw technical message stays one click away.
    msg.replaceChildren(`${t('buildFailed')}: ${friendlyError(b)}`);
    if (b.error_message) msg.append(h('details', { class: 'tech' }, h('summary', {}, t('techDetails')), h('code', { dir: 'ltr' }, b.error_message)));
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
  const existing = empty.querySelector('button'); if (existing) existing.remove();
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
function friendlyError(b) {
  const known = (t('errCodes') || {})[b.error_code];
  if (b.error_code === 'provider_quota_exhausted') {
    // Show the named route only when the server reported a quota response.
    // This is NOT a provider billing balance; it can also be a rate/usage quota.
    const match = String(b.error_message || '').match(/AI provider quota\/credits unavailable:\s*([^;]+)/);
    return known + (match && match[1] ? ' — ' + match[1] : '');
  }
  return known || b.error_message || b.error_code || '';
}

/* ---------- versions ---------- */
function currentVersionId() { return S.versions.length ? S.versions[0].id : null; }
async function loadVersions() {
  try {
    const d = await api(`/api/v28/projects/${pid()}/history`);
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
  $('builtName').textContent = v.title || v.message || v.id;
  $('builtSummary').textContent = v.summary || '';
  $('builtFeatures').replaceChildren(...(v.features || []).map((f) => h('li', {}, f)));
  let when = v.created_at;
  try { when = new Intl.DateTimeFormat(S.lang === 'he' ? 'he-IL' : 'en-GB', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(v.created_at)); } catch { /* keep raw */ }
  $('builtMeta').replaceChildren(t('builtVersion'), ': ', h('code', { dir: 'ltr' }, String(v.id).slice(0, 12)), ` · ${when}`,
    v.file_count ? ` · ${v.file_count} ${t('files')}` : '');
}
function renderVersions() {
  const panel = $('versionsPanel');
  panel.hidden = !S.projectId || !S.me;
  const list = $('versionsList');
  if (!S.versions.length) { list.replaceChildren(h('li', { class: 'meta' }, t('noVersions'))); return; }
  const fmt = new Intl.DateTimeFormat(S.lang === 'he' ? 'he-IL' : 'en-GB', { dateStyle: 'short', timeStyle: 'short' });
  list.replaceChildren(...S.versions.map((v, i) => {
    let when = v.created_at; try { when = fmt.format(new Date(v.created_at)); } catch { /* keep raw */ }
    return h('li', {},
      h('div', {}, h('div', {}, v.title || v.message || v.id), h('div', { class: 'meta' }, when, ' ', h('code', { dir: 'ltr' }, String(v.id).slice(0, 12)))),
      i === 0 ? h('span', { class: 'pill ok' }, t('current')) : h('button', { class: 'ghost', onclick: () => restoreVersion(v.id) }, t('restore')));
  }));
}
async function restoreVersion(versionId) {
  try {
    await api(`/api/v28/projects/${pid()}/rollback`, { method: 'POST', body: { target_version_id: versionId, message: 'rollback from workspace' } });
    await loadVersions();
    $('buildMsg').className = 'msg ok'; $('buildMsg').textContent = t('restored'); $('progressPanel').hidden = false;
  } catch (e) { $('progressPanel').hidden = false; $('buildMsg').className = 'msg'; $('buildMsg').textContent = explain(e); }
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
function renderEvidence() {
  const panel = $('evidencePanel'); const ev = S.build && S.build.evidence;
  if (!ev || !isTerminal(S.build.status)) { panel.hidden = true; return; }
  panel.hidden = false;
  const gates = ev.gates || {};
  const gateText = Object.entries(gates).map(([k, v]) => `${k}: ${v && v.passed === false ? '✗' : '✓'}`).join(', ') || t('none');
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
function applyConversation(view) {
  if (view.discovery && S.disc && view.discovery.brief.revision !== S.disc.brief.revision) S.plan = null;
  S.chat = view;
  if (view.discovery) S.disc = view.discovery;
  S.arch = view.plan || null;
  renderChat(); renderDiscovery(); renderArch(); renderTabs();
  const acts = (view.turn && view.turn.actions) || [];
  // A complete, buildable brief: fetch the real quote (free; nothing is reserved).
  if (S.disc && S.disc.complete && !S.plan && !S.updatingAnswers) requestBriefPlan(false);
}
async function restoreConversation() {
  try { applyConversation(await api(`${convPath()}?lang=${S.lang}`)); }
  catch (e) {
    // Conversation storage missing (migration pending) or unreachable: say so and
    // keep the guided questionnaire (the /discovery flow) working underneath.
    S.chat = { messages: [], unavailable: explain(e), fallback: true };
    try { S.disc = await api(`${discPath()}?lang=${S.lang}`); } catch { S.disc = null; }
    renderChat(); renderDiscovery(); renderTabs();
  }
}
let chatBusy = false;
async function sendChat(body, shownText) {
  if (chatBusy || !S.projectId) return;
  const retrySignature=JSON.stringify([S.projectId,body]);
  if(!S.chatRetry || S.chatRetry.signature!==retrySignature)S.chatRetry={signature:retrySignature,key:newKey()};
  chatBusy = true; $('chatSend').disabled = true; $('composerMsg').textContent = '';
  const pending = shownText ? { role: 'customer', content: shownText, pending: true } : null;
  if (pending) { S.chat = S.chat || { messages: [] }; S.chat.messages = [...(S.chat.messages || []), pending]; renderChat(); }
  try {
    const view = await api(`${convPath()}?lang=${S.lang}`, { method: 'POST', body: { ...body, request_key: S.chatRetry.key } });
    S.chatRetry=null;
    S.forceScroll = true;
    applyConversation(view);
    if (body.message) $('chatInput').value = '';
    autoGrow();
    return true;
  } catch (e) {
    if (pending) { S.chat.messages = S.chat.messages.filter(m => m !== pending); renderChat(); }
    $('composerMsg').textContent = explain(e);
    return false;
  } finally { chatBusy = false; $('chatSend').disabled = false; }
}
async function submitChat(e) {
  if (e) e.preventDefault();
  const text = $('chatInput').value.trim();
  const images = window.VE ? VE.pendingCount() : 0;
  if (!text && !images) return;
  if (!S.projectId) { openNewProject(); return; }
  if (S.chat && S.chat.fallback && !images) { startGuidedFallback(text); return; }
  let ids = [];
  if (images) {
    try { ids = await VE.uploadPending(); }
    catch (err) { $('composerMsg').textContent = explain(err); return; }
  }
  const sent=await sendChat({ message: text, ...(ids.length ? { attachment_ids: ids } : {}) }, text || `📎 ${ids.length}`);
  if (sent && ids.length && window.VE) VE.clearPending();
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
function quickReplies(questions) {
  return h('div', { class: 'quick' }, questions.map(q => h('div', {},
    h('div', { class: 'qq' }, q.text),
    h('div', { class: 'opts' },
      ...(q.kind === 'choice' ? q.options.map(o => h('button', { type: 'button', onclick: () => answerQuick(q, o.value, o.label) },
        o.label, q.suggested === o.value ? ' ✓' : '')) : []),
      q.delegable ? h('button', { type: 'button', class: 'del', onclick: () => answerQuick(q, '__delegate__', t('delegateShort')) }, t('delegateShort')) : null))));
}
function actionButtons(actions) {
  const out = [];
  for (const a of actions || []) {
    if (a.type === 'edit_requirements') out.push(h('button',{type:'button',class:'secondary',onclick:beginBriefEdit},t('editAll')));
    if (a.type === 'show_plan') out.push(h('button', { type: 'button', class: 'secondary', onclick: () => { if (S.plan) openTab('plan'); else requestBriefPlan(true); } }, t('actShowPlan')));
    if (a.type === 'approve_build') out.push(h('button', { type: 'button', onclick: async () => { if (!S.plan) await requestBriefPlan(); openTab('plan'); const b = $('confirmBtn'); if (b) b.focus(); } }, t('actApprove')));
    if (a.type === 'confirm_modification') out.push(h('button', { type: 'button', disabled: modActive() || !currentVersionId(),
      onclick: () => { $('followup').value = a.request; openTab('change'); sendModification(a.attachment_ids && a.attachment_ids.length ? { attachment_ids: a.attachment_ids } : null); } }, t('actConfirmMod')));
  }
  return out.length ? h('div', { class: 'acts' }, out) : null;
}
function renderChat() {
  const box = $('thread'); if (!box) return;
  if (!S.projectId) { box.replaceChildren(); return; }
  const msgs = (S.chat && S.chat.messages) || [];
  const kids = [];
  if(S.chat && S.chat.interpreter) kids.push(h('p',{class:'chatMode hint'},
    S.chat.interpreter==='model-via-worker'?t('aiMode'):t('guidedMode')));
  if (!msgs.length) kids.push(h('div', { class: 'welcomeChat' }, h('h2', {}, t('chatHelloTitle')), h('p', {}, t('chatHello')),
    S.chat && S.chat.unavailable ? h('p', { class: 'msg' }, S.chat.unavailable) : null));
  else if (S.chat && S.chat.unavailable) kids.push(h('p', { class: 'msg' }, S.chat.unavailable));
  const lastAssistant = msgs.map(m => m.role).lastIndexOf('assistant');
  msgs.forEach((m, i) => {
    const bubble = h('div', { class: `bubble ${m.role}`, dir: 'auto' }, h('span', { class: 'who' }, m.role === 'customer' ? t('you') : t('assistant')), m.content);
    if (m.attachments && m.attachments.length) bubble.append(h('div', { class: 'thumbs' }, m.attachments.map(a =>
      h('img', { src: `/api/v28/projects/${pid()}/attachments/${encodeURIComponent(a.id)}`, alt: t('attachedImage'), loading: 'lazy', width: 72, height: 72 }))));
    if (i === lastAssistant) {
      const turnQs = (S.chat.turn && S.chat.turn.questions) || [];
      const qs = turnQs.length ? turnQs : (S.disc && !S.disc.complete ? (S.disc.questions || []).slice(0, 2) : []);
      if (qs.length) bubble.append(quickReplies(qs));
      const acts = actionButtons(m.actions && m.actions.length ? m.actions : ((S.chat.turn && S.chat.turn.actions) || []));
      if (acts) bubble.append(acts);
    }
    kids.push(bubble);
  });
  // Build/change state lines come from the server records (no invented progress).
  if (S.build && S.build.status) {
    const st = String(S.build.status).toLowerCase();
    const counts = (S.tasks && S.tasks.tasks || []).reduce((a, x) => { a[x.state] = (a[x.state] || 0) + 1; return a; }, {});
    const label = st === 'ready' ? t('buildReady') : st === 'failed' ? `${t('buildFailed')}: ${friendlyError(S.build)}` :
      st === 'cancelled' ? t('buildCancelled') : `${t('buildRunning')}${S.build.phase ? ` · ${S.build.phase}` : ''}`;
    kids.push(h('button', { type: 'button', class: 'statusline ghost', onclick: () => openTab('build') }, label,
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
  panel.replaceChildren(h('h2', {}, t('archTitle')),
    h('p', {}, h('b', {}, `${t('feasibility')}: `), h('span', { class: `feas ${f.outcome === 'FEASIBLE' ? 'ok' : f.outcome === 'FEASIBLE_WITH_CONSTRAINTS' ? 'warn' : 'bad'}` }, t(`f_${f.outcome}`) || f.outcome)),
    limits.length ? h('details', {}, h('summary', {}, `${t('constraints')} (${limits.length})`),
      h('ul', {}, limits.map(x => h('li', {}, findingLabel(x),
        h('details', {}, h('summary', {}, S.lang==='he'?'פרטים טכניים':'Technical details'),
          `${x.item}: ${x.reason}`, x.alternative ? ` — ${x.alternative}` : ''))))) : null,
    h('div', { class: 'layers' }, layers),
    (S.chat && S.chat.interpreter === 'deterministic') ? h('p', { class: 'hint' }, t('interpreterNote')) : null);
}
function findingLabel(x) {
  if(S.lang!=='he')return `${x.item}: ${x.reason}`;
  if(x.item.startsWith('sign-in'))return 'התחברות והרשאות באתר שייבנה עדיין אינן זמינות. אפשר לערוך את הדרישה או להשאיר אותה להמשך.';
  if(x.item==='publishing')return 'פרסום בכתובת קבועה עדיין אינו זמין. קיימות תצוגה פרטית והורדת קוד.';
  if(x.item==='independent model review')return 'מודל הביקורת עשוי להיות מאותו ספק של מודל הכתיבה. בדיקות הקוד עדיין נדרשות לפני שחרור.';
  const names={'code generation':'יצירת קוד','behavioural acceptance':'בדיקות התנהגות','release policy':'מדיניות שחרור'};
  if(names[x.item])return `${names[x.item]}: ${x.outcome==='FEASIBLE_WITH_CONSTRAINTS'?'קיימות מגבלות שיש לבדוק':'דרושה בדיקה נוספת'}`;
  return `${x.item}: ${x.reason}`;
}
const TT = {
  he: { requirements:'דרישות', plan_and_quote:'תוכנית והצעת מחיר', architecture:'ארכיטקטורה', implementation:'כתיבת הקוד',
    unit_tests:'בדיקות בסביבה מבודדת', repair:'תיקונים', preview_smoke:'הפעלת תצוגה', behavioural_acceptance:'בדיקות התנהגות',
    browser_flow:'בדיקת דפדפן', visual_qa:'בדיקה חזותית', security_scan:'סריקת אבטחה', code_review:'סקירת קוד',
    release_gate:'שער שחרור', version_release:'שמירת גרסה', cost_settlement:'חישוב עלות' },
};
const ttLabel = k => (TT[S.lang] && TT[S.lang][k]) || String(k).replace(/_/g, ' ');
async function loadTasks() {
  if (!S.build || !S.build.id) return;
  try { S.tasks = await api(`/api/v28/projects/${pid()}/builds/${encodeURIComponent(S.build.id)}/plan`); }
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
  nav.replaceChildren(...avail.map(([k]) => h('button', { type: 'button', 'aria-selected': S.tab === k ? 'true' : 'false',
    'aria-controls': 'ctx', onclick: () => openTab(S.tab === k ? null : k) }, t(`tab_${k}`))));
  for (const [k, ids] of TABS) for (const id of ids) { const el = $(id); if (el) el.classList.toggle('active', S.tab === k); }
  $('ctx').classList.toggle('open', Boolean(S.tab));
}
function openTab(k) { S.tab = k; renderTabs(); }
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
  $('sbSearch').addEventListener('input', renderProjects);
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
      const items=[...$('sidebar').querySelectorAll('button,input,a[href]')].filter(el=>!el.disabled&&el.getClientRects().length);
      const first=items[0],last=items[items.length-1];
      if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
      else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
    }
  });
  syncSidebar();
  $('sbScrim').addEventListener('click', closeSidebarMobile);
  $('langBtn2').addEventListener('click', () => $('langBtn').click());
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
  $('registerBtn').addEventListener('click', () => authSubmit('register'));
  $('logoutBtn').addEventListener('click', logout);
  $('langBtn').addEventListener('click', () => { S.lang = S.lang === 'he' ? 'en' : 'he'; localStorage.setItem('148ai_lang', S.lang); applyLang(); });
  $('projectSelect').addEventListener('change', e => selectProject(e.target.value));
  $('projectMenuBtn').addEventListener('click', openProjectDialog);
  $('firstProjectForm').addEventListener('submit', async e => {
    e.preventDefault();
    try { await createProject($('firstProjectName').value.trim()); } catch (err) { $('composerMsg').textContent = explain(err); }
  });
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
  $('newProjectForm').addEventListener('submit', submitNewProject);
  $('newProjectCancel').addEventListener('click', () => $('newProjectDialog').close());
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
