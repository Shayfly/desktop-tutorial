# מסמך ארכיטקטורה: Dynamic Multi-Model Product Orchestration

1. חזון ועקרונות

148AI היא Multi-Model Product Orchestrator: מערכת שמקבלת תוצאה סופית שהמשתמש רוצה, מפרקת אותה למשימות, בוחרת לכל משימה את המודל, הספק או הכלי המתאים ביותר, מחברת את התוצרים ומוודאת שהתוצאה הסופית עומדת בדרישות.

המשתמש עשוי לבקש:

* אתר
* SaaS
* אפליקציה
* משחק
* Agent
* Automation
* תמונה
* סרטון
* סרט
* שיר
* Voice/Audio
* 3D
* או שילוב של כמה סוגי תוצרים

מוצר יחיד עשוי להשתמש במודל או ספק אחד, או בשילוב של ספקים רבים. הבחירה אינה נעשית לפי מספר המודלים, אלא לפי איכות התוצאה הסופית, העלות הכוללת, זמן הביצוע ורמת האמינות.

פונקציית המטרה:

Produce the highest-quality verified final result at the lowest total justified cost.

עקרונות מרכזיים:

* Task-level selection:
    Task → Provider/Model selection per task
* אין להשתמש כברירת מחדל במודל יחיד לכל המוצר:
    Request → One model for entire product
* יש להשתמש בדיוק בכמות היכולת הנדרשת להשגת איכות היעד:
    Use exactly as much AI capability as required to reach the target quality — no less and no more.
* Multi-model צריך להיות Selective and economical, ולא Ensemble everywhere.
* כל פעולה משמעותית כפופה לתקציב, Verification ותנאי עצירה.
* בשלב הראשון יש לוודא שהארכיטקטורה מאפשרת תזמור ברמת משימה. הרחבת האופטימיזציה תתבסס בהמשך על נתוני שימוש אמיתיים, ללא צורך בשכתוב מיידי של Golden E2E.

2. מודל ביצוע: Product DAG

2.1 פירוק המוצר

כל בקשת משתמש הופכת ל־Task/Capability DAG — גרף מכוון של משימות, תלויות ותוצרים.

ה־DAG מגדיר:

* משימות נדרשות
* תלויות בין משימות
* משימות שניתן לבצע במקביל
* סוג היכולת הנדרש לכל משימה
* תוצר צפוי ופורמט תוצר
* קריטריוני הצלחה
* שלבי Verification
* תוצר סופי מאוחד
* מדיניות Retry, Repair ו־Escalation
* מגבלות תקציב וזמן

לכל צומת ניתן לבחור Provider, Model או Tool באופן עצמאי. כשל במשימה צריך לאפשר Retry או Repair מקומי, ללא הרצה מחדש של כל המוצר.

2.2 דוגמה: סרטון פרסומת

User Request
→ LLM A: הבנת הבריף
→ LLM B: כתיבת תסריט
→ Image Provider C: יצירת דמויות וסצנות
→ Video Provider D: המרת תמונות לווידאו
→ TTS Provider E: יצירת קריינות
→ Music Provider F: יצירת מוזיקה
→ LLM G: בדיקת רציפות, איכות והתאמה לבריף
→ Video Composer: חיבור כל הרכיבים
→ Verifier: בדיקה סופית

יצירת מוזיקה וקריינות עשויה להתבצע במקביל. חיבור הווידאו תלוי בהשלמת רכיבי המדיה.

2.3 דוגמה: יצירת אפליקציה

User Request
→ Product Architect
→ Requirements
→ Architecture
→ Frontend
→ Backend
→ Database
→ Integrations
→ Assets
→ Tests
→ Debugging
→ Security Review
→ Build
→ Verification

ניתן לבחור מודל שונה ל־Architecture, Frontend, Backend, Tests ו־Debugging, וכן להשתמש בכלים ייעודיים ל־Build ול־Verification.

2.4 חוזה משימה

כל Task צריך להגדיר לפחות:

* task_id
* סוג משימה ומודאליות
* קלט נדרש
* תוצר ופורמט תוצר
* תלויות
* קריטריוני הצלחה
* יכולות וכלים נדרשים
* מגבלת תקציב וזמן
* סף איכות מינימלי
* שלב Verification
* max_retries
* max_repairs
* max_escalations
* מדיניות Escalation ו־Fallback
* תנאי עצירה
* תנאי כשל סופי

3. מנוע תזמור ואופטימיזציה

3.1 מטרת המנוע

ה־Router הוא רכיב בתוך Orchestration + Optimization Engine. הוא אינו בוחר רק את המודל הזול ביותר, אלא את הקומבינציה שממקסמת איכות והסתברות הצלחה וממזערת את העלות הכוללת, הזמן והסיכון.

העלות הכוללת כוללת:

* יצירה ראשונית
* Retries
* Repairs
* Verification
* Escalation
* Fallback
* Composition
* עלויות כלים וספקים נוספים

לדוגמה, מודל בעל עלות קריאה נמוכה עשוי להיות יקר יותר בפועל אם הוא דורש ניסיונות ותיקונים רבים.

3.2 פרמטרים לבחירה

יש להביא בחשבון:

* Final quality
* Probability of success
* Retry ו־Repair צפויים
* עלות כשל
* Latency
* Provider reliability
* Task specialization
* Context size
* Modality
* Tool support
* Historical performance
* Actual previous cost
* User plan
* Available credits
* Build budget
* עלות משימות עתידיות ב־DAG

3.3 בחירת מועמד לכל משימה

function select_candidate(task, context, budget_state, policy):
    candidates = registry.find_capable_providers(
        task_type = task.type,
        modality = task.modality,
        required_tools = task.required_tools,
        required_output_format = task.output_format
    )
    candidates = filter(candidates, candidate ->
        candidate.is_available
        and candidate.supports(task.requirements)
        and candidate.policy_allowed(policy)
        and candidate.estimated_latency <= task.max_latency
    )
    if candidates is empty:
        return NO_CAPABLE_CANDIDATE
    for candidate in candidates:
        p_success = estimate_success(candidate, task, context)
        expected_retries = estimate_retries(candidate, p_success)
        expected_repair_cost = estimate_repair_cost(candidate, task, p_success)
        verification_cost = estimate_verification_cost(task)
        escalation_cost = estimate_expected_escalation_cost(
            candidate, task, p_success
        )
        composition_cost = estimate_composition_cost(task)
        expected_total_cost =
            candidate.initial_cost
            + expected_retries * candidate.retry_cost
            + expected_repair_cost
            + verification_cost
            + escalation_cost
            + composition_cost
        expected_quality = estimate_quality(candidate, task, context)
        expected_latency = estimate_total_latency(candidate, task)
        reliability = candidate.historical_reliability
        candidate.score = optimize(
            quality = expected_quality,
            success_probability = p_success,
            reliability = reliability,
            total_cost = expected_total_cost,
            latency = expected_latency,
            task_priority = task.priority
        )
    ranked = sort_by_score(candidates)
    for candidate in ranked:
        if can_reserve_budget(candidate, task, budget_state):
            return candidate
    return BUDGET_INSUFFICIENT

הבחירה אינה רשאית להתבסס רק על initial_cost.

expected_total_cost =
    initial_cost
    + expected_retry_cost
    + expected_repair_cost
    + expected_verification_cost
    + expected_escalation_cost
    + expected_composition_cost

מועמד תקין חייב לעמוד בתנאים:

candidate.supports_requirements == true
candidate.policy_allowed == true
candidate.available == true
candidate.expected_quality >= task.minimum_expected_quality
candidate.expected_latency <= task.max_latency
reserve(candidate.expected_total_cost) succeeds

כאשר קיימים כמה מועמדים תקינים:

score =
    quality_weight * normalized_quality
    + success_weight * success_probability
    + reliability_weight * reliability
    - cost_weight * normalized_expected_total_cost
    - latency_weight * normalized_latency

משימות קריטיות ייתנו משקל גבוה יותר לאיכות ולאמינות. משימות לא קריטיות ייתנו משקל גבוה יותר לעלות ולמהירות.

3.4 שימוש במספר מודלים

ניתן להפעיל כמה מודלים בכוונה:

Model A → Generate solution
Model B → Independent review
Model C → Repair only the defects

יש להפעיל מודל נוסף רק כאשר התועלת הצפויה מצדיקה את העלות, הזמן והתקציב העתידי:

use_additional_model =
    expected_quality_gain
    + expected_failure_reduction
    > additional_model_cost
    + additional_latency
    + reserved_future_budget_cost

4. תקציב ו־Budget Reservation

4.1 מצבי תקציב

יש להפריד בין:

* available_budget — תקציב שטרם הוקצה
* reserved_budget — תקציב שהוקצה לפעולות מתוכננות
* committed_cost — עלות שאושרה לביצוע
* actual_cost — עלות שנצרכה בפועל
* released_budget — תקציב ששוחרר

Reservation נועדה למנוע ממשימה מוקדמת לצרוך את התקציב הנדרש למשימות קריטיות, Verification או תיקון.

4.2 יצירת Reservation

function reserve_budget(operation, budget_state):
    estimated_cost = estimate_operation_cost(operation)
    safety_margin = calculate_safety_margin(operation)
    reservation_amount = estimated_cost + safety_margin
    protected_future_budget =
        estimate_required_budget_for_remaining_tasks(operation.dag)
    spendable_budget =
        budget_state.total_limit
        - budget_state.actual_cost
        - budget_state.reserved_budget
        - protected_future_budget
    if operation.is_mandatory and spendable_budget < reservation_amount:
        if can_reallocate_noncritical_reservations():
            reallocate_noncritical_reservations()
            spendable_budget = recalculate_spendable_budget()
    if spendable_budget < reservation_amount:
        return RESERVATION_DENIED
    reservation_id = create_reservation(
        operation_id = operation.id,
        amount = reservation_amount,
        expires_at = operation.reservation_deadline
    )
    budget_state.reserved_budget += reservation_amount
    return RESERVATION_APPROVED(reservation_id)

אין להתחיל פעולה ללא Reservation מאושרת, למעט פעולת חירום שהוגדרה מראש במדיניות, עם מגבלת סכום וניסיונות.

4.3 Settlement

function settle_reservation(reservation_id, actual_cost):
    reservation = get_reservation(reservation_id)
    if actual_cost <= reservation.amount:
        release_unused_amount(reservation.amount - actual_cost)
        charge(actual_cost)
        mark_reservation_settled(reservation_id)
        return SETTLED
    if can_extend_reservation(reservation, actual_cost):
        extend_reservation(reservation_id, actual_cost - reservation.amount)
        charge(actual_cost)
        mark_reservation_settled(reservation_id)
        return SETTLED_WITH_EXTENSION
    mark_operation_failed_due_to_budget(reservation.operation_id)
    charge_up_to_authorized_amount(reservation.amount)
    return BUDGET_EXCEEDED

4.4 תנאי עצירה תקציביים

actual_cost >= hard_budget_limit
remaining_budget < minimum_required_cost_for_any_valid_next_step
no_reservation_available_for_required_operation
expected_quality_gain / expected_additional_cost < policy.minimum_roi

כאשר התקציב אינו מספיק, יש להחזיר את התוצר המאושר הטוב ביותר עד כה, או FAILED_BUDGET אם אין תוצר שעומד בדרישות המינימום.

5. Verification וסיווג תוצאות

5.1 שכבות Verification

כל שלב משמעותי צריך לכלול Verification מתאים:

1. Schema Verification — פורמט ו־Schema.
2. Technical Verification — קומפילציה, הרצה או תקינות טכנית.
3. Requirement Verification — התאמה לדרישות.
4. Quality Verification — עמידה בסף איכות.
5. Cross-Task Verification — עקביות עם תוצרים אחרים.
6. Final Product Verification — מוכנות המוצר למסירה.

יש לבדוק, לפי סוג המשימה:

* התאמה לדרישות
* תקינות פורמט
* איכות
* עקביות פנימית
* התאמה לתוצרים קודמים
* תקינות טכנית
* אבטחה
* שלמות המוצר

במשימות קריטיות ניתן לשלב Verifier עצמאי או דטרמיניסטי בנוסף ל־Verifier מבוסס מודל.

5.2 מבנה תוצאת Verification

VerificationResult:
    status: PASS | REPAIRABLE_FAIL | RETRYABLE_FAIL | ESCALATABLE_FAIL | FATAL_FAIL
    score: 0..1
    defects: list
    severity: LOW | MEDIUM | HIGH | CRITICAL
    retryable: boolean
    repairable: boolean
    escalation_recommended: boolean
    reason: string

* PASS — ניתן להמשיך.
* REPAIRABLE_FAIL — ניתן לתקן את התוצר הקיים.
* RETRYABLE_FAIL — ניסיון נוסף עשוי להצליח.
* ESCALATABLE_FAIL — נדרש מודל, ספק או כלי אחר.
* FATAL_FAIL — אין טעם להמשיך באותה אסטרטגיה.

6. Retry, Repair, Escalation ו־Fallback

6.1 החלטה על הפעולה הבאה

function decide_next_action(task, result, state):
    if result.status == PASS:
        return COMPLETE
    if result.status == FATAL_FAIL:
        return FAIL_TASK
    if state.deadline_exceeded:
        return STOP_DEADLINE
    if state.hard_budget_exceeded:
        return STOP_BUDGET
    if result.status == REPAIRABLE_FAIL
       and state.repair_count < task.max_repairs
       and repair_has_positive_expected_value(task, result, state)
       and can_reserve_budget_for_repair(task, result, state):
        return REPAIR
    if result.status == RETRYABLE_FAIL
       and state.retry_count < task.max_retries
       and retry_has_positive_expected_value(task, result, state)
       and can_reserve_budget_for_retry(task, result, state):
        return RETRY
    if result.status == ESCALATABLE_FAIL
       or state.retry_count >= task.retry_before_escalation:
        if escalation_candidate_exists(task, state)
           and can_reserve_budget_for_escalation(task, state):
            return ESCALATE
    if fallback_candidate_exists(task, state)
       and can_reserve_budget_for_fallback(task, state):
        return FALLBACK_PROVIDER
    return FAIL_TASK

ברירת המחדל:

Verify → Repair אם אפשר → Retry אם משתלם → Escalate → Fallback → Fail

6.2 Retry

Retry מתאים לכשל זמני, אקראי או כזה שסביר שייפתר ללא שינוי מהותי ביכולת.

function should_retry(task, result, state):
    if state.retry_count >= task.max_retries:
        return false
    if result.status not in [RETRYABLE_FAIL, TRANSIENT_ERROR]:
        return false
    if result.severity == CRITICAL and not task.allow_critical_retry:
        return false
    p_retry_success = estimate_retry_success(task, result, state)
    retry_cost = estimate_retry_cost(task, state)
    future_cost = estimate_protected_future_cost(task.dag, state)
    if state.remaining_budget < retry_cost + future_cost:
        return false
    if p_retry_success * task.retry_value <= retry_cost:
        return false
    return true

Retry צריך לשנות, כאשר רלוונטי, לפחות אחד מהבאים:

* Random seed
* Prompt normalization
* Context cleanup
* Timeout
* Request parameters
* Input ordering
* Provider connection

אין לבצע Retry זהה לכשל דטרמיניסטי.

6.3 Repair

Repair מתאים כאשר רוב התוצר תקין והכשל מקומי וברור.

function should_repair(task, result, state):
    if state.repair_count >= task.max_repairs:
        return false
    if result.status != REPAIRABLE_FAIL:
        return false
    if result.defects is empty:
        return false
    repair_cost = estimate_repair_cost(task, result)
    regenerate_cost = estimate_regeneration_cost(task)
    repair_success = estimate_repair_success(task, result)
    if repair_success < task.minimum_repair_success_probability:
        return false
    if repair_cost >= regenerate_cost
       and task.repair_quality_gain <= task.regeneration_quality_gain:
        return false
    if not can_reserve_budget_for_repair(task, result, state):
        return false
    return true

דוגמאות:

* תיקון JSON או Schema
* תיקון שגיאת קומפילציה מקומית
* שינוי טקסט או Voice-over
* תיקון צבע, חיתוך או פריים
* תיקון פונקציה בודדת
* השלמת שדה חסר

6.4 Escalation

Escalation מתאים כאשר המודל או הספק הנוכחי אינם עומדים בדרישות, או כאשר נדרשת יכולת שונה או חזקה יותר.

function should_escalate(task, result, state):
    if state.escalation_count >= task.max_escalations:
        return false
    if result.status not in [ESCALATABLE_FAIL, REPAIRABLE_FAIL, RETRYABLE_FAIL]:
        return false
    candidates = find_escalation_candidates(task, state)
    for candidate in candidates:
        p_success = estimate_success(candidate, task, state.context)
        quality_gain = estimate_quality_gain(candidate, task, result)
        escalation_cost = estimate_incremental_cost(candidate, task, state)
        future_cost = estimate_protected_future_cost(task.dag, state)
        if p_success < task.minimum_escalation_success_probability:
            continue
        if state.remaining_budget < escalation_cost + future_cost:
            continue
        if quality_gain / escalation_cost < task.minimum_escalation_roi:
            continue
        return true
    return false

Escalation מותרת כאשר:

* הכשל חוזר לאחר Retry או Repair
* נדרש כלי או יכולת שאינם זמינים
* ההסתברות להצלחה בניסיון נוסף נמוכה
* חלופה צפויה לשפר משמעותית את התוצאה
* קיימת Reservation מתאימה

6.5 Fallback

Fallback הוא מעבר לספק אחר בעל יכולת דומה, ולא בהכרח למודל חזק יותר.

יש להעדיף Fallback כאשר:

* הספק אינו זמין
* קיימת תקלה חוזרת ברמת Provider
* המודל מתאים אך התשתית אינה יציבה
* ספק אחר מציע אותה יכולת בעלות או זמן טובים יותר
* יש להפחית תלות בספק יחיד

6.6 תנאי עצירה

יש לעצור Task כאשר:

* התקבל PASS
* התוצר עומד בסף המינימום והמשך שיפור אינו מצדיק את העלות
* הושגה מגבלת Retry, Repair או Escalation
* התקציב או הדדליין מוצו
* אין מועמד כשיר נוסף
* התקבל FATAL_FAIL
* ה־ROI הצפוי נמוך מהמינימום

function should_stop(task, state, result):
    return (
        result.status == PASS
        or result.score >= task.minimum_acceptable_score
        or state.retry_count >= task.max_retries
        or state.repair_count >= task.max_repairs
        or state.escalation_count >= task.max_escalations
        or state.deadline_exceeded
        or state.hard_budget_exceeded
        or no_valid_candidate_remains(task, state)
        or result.status == FATAL_FAIL
        or expected_next_gain(task, state) < task.minimum_roi
    )

7. תזמור מלא של Task

function execute_task(task, dag_context, budget_state):
    state = initialize_task_state(task, dag_context)
    candidate = select_candidate(
        task,
        dag_context,
        budget_state,
        policy = task.policy
    )
    if candidate in [NO_CAPABLE_CANDIDATE, BUDGET_INSUFFICIENT]:
        return fail_task(task, reason = candidate)
    while true:
        if should_stop_before_execution(task, state, budget_state):
            return finalize_task(task, state)
        operation = build_operation(task, state, candidate)
        reservation = reserve_budget(operation, budget_state)
        if reservation is denied:
            return fail_task(task, reason = BUDGET_INSUFFICIENT)
        output = execute(operation)
        actual_cost = measure_actual_cost(operation, output)
        settle_reservation(reservation.id, actual_cost)
        verification = verify(task, output, dag_context)
        record_attempt(task, candidate, output, verification, actual_cost)
        if verification.status == PASS:
            return complete_task(task, output, verification)
        action = decide_next_action(task, verification, state)
        if action == REPAIR:
            state.repair_count += 1
            candidate = select_repair_candidate(task, verification, state)
            continue
        if action == RETRY:
            state.retry_count += 1
            candidate = adjust_retry_candidate(
                candidate, task, verification, state
            )
            continue
        if action == ESCALATE:
            state.escalation_count += 1
            candidate = select_escalation_candidate(task, state)
            continue
        if action == FALLBACK_PROVIDER:
            state.fallback_count += 1
            candidate = select_fallback_provider(task, state)
            continue
        if action in [STOP_BUDGET, STOP_DEADLINE]:
            return finalize_best_available_or_fail(task, state)
        if action == FAIL_TASK:
            return fail_task(task, reason = verification.reason)

8. KPI ו־SLO

8.1 מטרת המדדים

מדדי ה־KPI וה־SLO צריכים למדוד את התוצאה העסקית והטכנית של המערכת, ולא רק את ביצועי המודל הבודד. המדידה המרכזית היא תוצר סופי מאושר: מוצר או תוצר שעבר את כל בדיקות ה־Verification הנדרשות, עומד בסף האיכות שהוגדר ומוכן למסירה למשתמש.

יש להפריד בין:

* KPI — מדדים לניהול, אופטימיזציה ושיפור המוצר לאורך זמן.
* SLO — יעדי שירות מחייבים עבור אחוז מוגדר מההרצות, עם חלון מדידה ברור.
* SLI — המדידה בפועל שממנה מחושב כל SLO.

כל מדד חייב להיות מפולח לפחות לפי:

* סוג מוצר
* סוג משימה
* מודאליות
* תוכנית משתמש
* Provider ו־Model
* רמת קריטיות
* גודל DAG
* טווח תקציב
* גרסת Policy ו־Prompt

8.2 יעדי KPI ו־SLO ראשוניים

היעדים הבאים הם יעדי Baseline לגרסת Production ראשונה. יש לכייל אותם מחדש לאחר צבירת נתוני אמת במשך 30 יום, אך אין להחליפם ללא יעד מדיד חלופי.

תחום	מדד	הגדרה	יעד KPI	יעד SLO
איכות	שיעור תוצרים סופיים מאושרים	תוצרים שעברו Final Verification ועומדים בסף האיכות	≥ 90%	≥ 85% בכל חלון של 30 יום
איכות	ציון איכות סופי	ציון Verifier מנורמל לתוצר סופי	≥ 0.85 בממוצע	≥ 0.80 ב־P95 של תוצרים מאושרים
איכות	שיעור כשל קריטי לאחר מסירה	תוצרים שנמסרו ולאחר מכן התגלה בהם כשל קריטי	≤ 2%	≤ 3%
עלות	עלות לתוצר מאושר	actual_cost / מספר תוצרים מאושרים	≤ 110% מהעלות המתוכננת	≤ 125% מהעלות המתוכננת ב־P90
עלות	סטיית עלות מתכנון	(actual_cost - estimated_cost) / estimated_cost	≤ 10% בממוצע	≤ 20% ב־P90
זמן	זמן ביצוע לתוצר מאושר	מזמן פתיחת ההרצה עד Final Verification מאושר	שיפור חודשי של ≥ 10% עד התייצבות	≥ 85% מההרצות עומדות ב־deadline שהוגדר
זמן	זמן ביצוע יחסי לתכנון	actual_duration / estimated_duration	≤ 1.15 בממוצע	≤ 1.50 ב־P90
הצלחה	שיעור הצלחת Task	Tasks שהסתיימו ב־PASS ללא כשל סופי	≥ 92%	≥ 88%
הצלחה	שיעור הצלחת Product DAG	DAG שהסתיים בתוצר מאושר	≥ 90%	≥ 85%
תקציב	שיעור חריגות תקציב	הרצות שבהן actual_cost > hard_budget_limit או נדרשה הרחבה לא מאושרת	≤ 0.5%	≤ 1%
תקציב	שיעור עצירות תקציביות תקינות	הרצות שנעצרו לפני חריגה והחזירו FAILED_BUDGET או תוצר מאושר חלקי	≥ 99% מהניסיונות שנחסמו	≥ 99%
תיקונים	שיעור תוצרים הדורשים Repair	תוצרים שעברו Repair אחד או יותר לפני PASS	≤ 35%	≤ 45%
תיקונים	שיעור הצלחת Repair	Repairs שהובילו ל־PASS ללא Escalation נוסף	≥ 70%	≥ 60%
תיקונים	מספר תיקונים לתוצר מאושר	מספר Repairs ממוצע לתוצר שאושר	≤ 0.8	≤ 1.2 ב־P90
ספקים	זמינות ספק	בקשות שהתקבלו והסתיימו ללא כשל תשתיתי של הספק	≥ 99.5%	≥ 99.0%
ספקים	שיעור כשל תשתיתי	Timeout, Rate Limit, 5xx או כשל חיבור שאינו תלוי בתוכן	≤ 1%	≤ 2%
ספקים	שיעור הצלחה לפי ספק	Tasks שהספק השלים ועברו Verification	≥ 90% לספקים קריטיים	≥ 85% לכל ספק פעיל
ספקים	שיעור Fallback	הרצות שעברו לספק חלופי עקב כשל ספק	≤ 8%	≤ 12%
אמינות	דיוק הערכת עלות	פער בין עלות חזויה לעלות בפועל	≥ 90% מהתחזיות בטווח ±20%	≥ 85% בטווח ±30%
אמינות	דיוק הערכת הצלחה	פער בין p_success החזוי לתוצאה בפועל	Brier Score ≤ 0.15	Brier Score ≤ 0.20
תפעול	שלמות Telemetry	הרצות עם עלות, זמן, Provider, Verification וסטטוס מלאים	≥ 99.5%	≥ 99%
תפעול	שיעור הרצות ללא תוצר מאושר או סיבת כשל	כל הרצה מסתיימת ב־PASS, Partial Result או Failure Reason מובנה	≥ 99.9%	≥ 99.5%

היעדים אינם מבטלים ספים ספציפיים למשימה. Task קריטי, כגון Security Review או Final Product Verification, רשאי להגדיר סף איכות גבוה יותר ושיעור הצלחה מחמיר יותר.

8.3 הגדרות מדויקות

תוצר מאושר

תוצר ייחשב מאושר רק אם:

final_verification.status == PASS
and final_verification.score >= product.minimum_quality_score
and all_mandatory_tasks.status == PASS
and no_open_critical_defects
and actual_cost <= hard_budget_limit
and completion_time <= product.deadline

תוצר שעבר את סף האיכות אך חרג מהתקציב או מהדדליין לא ייספר כתוצר מאושר לצורך KPI של עלות או זמן.

עלות לתוצר מאושר

cost_per_approved_product =
    sum(actual_cost for completed_product_runs)
    / count(approved_products)

יש לדווח בנפרד על:

* עלות ממוצעת
* חציון
* P90
* P95
* עלות לפי סוג מוצר
* עלות לפי תוכנית משתמש
* עלות לפי Provider Mix
* עלות כולל ובלי Verification, Repair ו־Escalation

שיעור הצלחה

task_success_rate =
    count(tasks with PASS)
    / count(tasks started)
product_success_rate =
    count(products with approved final result)
    / count(products started)

יש להציג גם:

* הצלחה בניסיון ראשון
* הצלחה לאחר Retry
* הצלחה לאחר Repair
* הצלחה לאחר Escalation
* הצלחה לאחר Fallback
* כשל עקב תוכן
* כשל עקב ספק
* כשל עקב תקציב
* כשל עקב דדליין

חריגת תקציב

חריגת תקציב תוגדר כאשר מתקיים אחד מהבאים:

actual_cost > hard_budget_limit
actual_cost > approved_budget
and no_explicit_extension == true
provider_charge > settled_reservation
and charge_not_authorized == true

כל חריגה חייבת להירשם עם:

* run_id
* task_id
* Provider
* Reservation
* סכום מאושר
* סכום בפועל
* סכום החריגה
* סיבת החריגה
* האם החריגה נחסמה או חויבה
* פעולה מתקנת

שיעור תיקונים

repair_rate =
    count(products_with_at_least_one_repair)
    / count(products_started)

יש למדוד בנפרד:

* Repair לפי סוג כשל
* Repair לפי Provider
* Repair לפי סוג מוצר
* Repair שהצליח
* Repair שהוביל ל־Retry
* Repair שהוביל ל־Escalation
* Repair שהסתיים בכשל

אמינות ספק

אמינות ספק אינה רק זמינות API. היא כוללת:

provider_reliability =
    weighted(
        availability,
        technical_success_rate,
        verified_output_success_rate,
        latency_slo_compliance,
        cost_prediction_accuracy
    )

לכל ספק יש לשמור חלון מתגלגל של 7, 30 ו־90 יום, עם מינימום מדגם לפני שינוי דירוג משמעותי. אין להוריד דירוג ספק על בסיס כשל יחיד או מדגם קטן.

8.4 SLO לפי רמת קריטיות

יש להגדיר יעדים שונים לפי קריטיות:

רמת קריטיות	שיעור תוצרים מאושרים	חריגת תקציב	זמינות ספקים	שיעור כשל קריטי
Critical	≥ 95%	0% ללא אישור מפורש	≥ 99.9%	≤ 0.5%
High	≥ 90%	≤ 0.5%	≥ 99.5%	≤ 1%
Standard	≥ 85%	≤ 1%	≥ 99.0%	≤ 3%
Experimental	≥ 70%	לפי Budget Policy	Best Effort	מתועד בלבד

משימה או מוצר ברמת Critical לא ייחשבו מאושרים על בסיס ציון ממוצע בלבד. כל כשל קריטי, כשל אבטחה או כשל בדרישה חובה מונע PASS.

8.5 מדידת זמן ו־Latency

יש למדוד את הזמן ברמות הבאות:

* זמן המתנה לתור
* זמן עד התחלת Task
* זמן Provider
* זמן Verification
* זמן Repair
* זמן Retry
* זמן Escalation
* זמן Composition
* זמן כולל עד תוצר מאושר

end_to_end_duration =
    final_approval_timestamp
    - product_run_start_timestamp

יש לדווח על:

* Median
* P75
* P90
* P95
* P99
* שיעור עמידה ב־deadline
* זמן לפי סוג מוצר ומספר צמתים ב־DAG

8.6 מדידת איכות

ציון איכות חייב להתבסס על שילוב של:

* Verifier דטרמיניסטי
* בדיקות טכניות
* בדיקות דרישות
* בדיקות Cross-Task
* בדיקה אנושית במדגם
* Feedback משתמש, כאשר זמין

אין להשתמש בציון של מודל יחיד כמדד איכות יחיד עבור מוצר קריטי.

יש לבצע Calibration תקופתי בין ציון ה־Verifier לבין קבלה אנושית:

verifier_precision =
    accepted_outputs_predicted_as_pass
    / all_outputs_predicted_as_pass
verifier_recall =
    accepted_outputs_predicted_as_pass
    / all_human_accepted_outputs

יעד ראשוני:

* verifier_precision ≥ 0.90
* verifier_recall ≥ 0.85

8.7 Error Budget

לכל SLO יש להגדיר Error Budget:

error_budget = 1 - slo_target

לדוגמה, עבור SLO של 85% תוצרים מאושרים, Error Budget הוא 15% מהרצות שאינן עומדות ביעד.

מדיניות שימוש:

* כאשר נוצלו פחות מ־50% מה־Error Budget: ניתן לבצע ניסויים מבוקרים.
* כאשר נוצלו 50%–80%: יש להגביל ניסויים ולהעדיף יציבות.
* כאשר נוצלו יותר מ־80%: יש לעצור שינויים לא חיוניים, להפעיל Root Cause Analysis ולתעדף תיקוני אמינות.
* כאשר ה־Error Budget נוצל במלואו: אין להרחיב Provider או Policy חדשים ללא אישור מפורש.

8.8 התראות ופעולות מתקנות

יש להפעיל התראה כאשר:

* שיעור תוצרים מאושרים יורד מתחת ל־SLO במשך 15 דקות או 100 הרצות, לפי המאוחר מביניהם.
* שיעור כשל תשתיתי של ספק עובר 5% במשך 10 דקות.
* חריגות תקציב עוברות 1% בחלון של 24 שעות.
* עלות לתוצר מאושר עולה ביותר מ־20% לעומת Baseline של 7 ימים.
* P95 זמן ביצוע חורג ב־25% מהיעד במשך שעה.
* שיעור Repair עולה ביותר מ־15 נקודות אחוז לעומת Baseline.
* ספק יורד מתחת ל־SLO שלו בשני חלונות מדידה רצופים.
* Telemetry חסרה ביותר מ־0.5% מההרצות.

פעולות אפשריות:

* הורדת דירוג Provider
* מעבר ל־Fallback Provider
* הקטנת max_retries
* הקטנת max_escalations
* עצירת מודל או ספק
* הגדלת Verification
* הקפאת ניסויים
* שינוי Budget Policy
* פתיחת Incident
* ביצוע Rollback לגרסת Policy או Model

8.9 דוח KPI תקופתי

יש להפיק דוח יומי, שבועי וחודשי הכולל:

* מספר הרצות
* מספר תוצרים מאושרים
* שיעור הצלחה
* עלות לתוצר מאושר
* עלות מתוכננת לעומת בפועל
* זמן ביצוע ו־P50/P90/P95
* שיעור חריגות תקציב
* שיעור Retry, Repair, Escalation ו־Fallback
* איכות ממוצעת והתפלגות ציונים
* אמינות לפי Provider ו־Model
* ניצול Error Budget
* עשרת גורמי הכשל המרכזיים
* שינוי לעומת התקופה הקודמת
* פעולות מתקנות פתוחות
* השפעת שינויים ב־Policy, Prompt או Model Version

9. Feedback Loop ונתוני ביצוע

9.1 נתונים לכל Task

יש לשמור:

* task type
* selected provider
* model
* estimated cost
* actual cost
* latency
* success/failure
* verifier score
* retry count
* repair count
* escalation count
* final acceptance result
* input type וגודל הקונטקסט
* modality
* model version
* Prompt/Policy version
* failure reason
* repair type
* escalation result
* product ו־DAG identifiers
* השפעת המשימה על התוצאה הסופית
* Reservation identifiers
* סכום Reservation
* סכום ששולם
* סכום ששוחרר
* סיבת עצירה
* SLO classification
* KPI dimensions
* האם נוצרה חריגת תקציב
* האם המשימה תרמה לכשל הסופי

יש להפריד בין:

* נתוני ביצוע גולמיים
* הערכות הסתברות
* מדיניות בחירה
* תוצאות Verification
* החלטות שהתקבלו בפועל
* נתוני KPI ו־SLO מחושבים

אין לעדכן מודל ביצועים על בסיס תוצאה שלא עברה Verification או על בסיס עלות שלא נמדדה ואושרה.

9.2 למידה מנתוני שימוש

148AI צריכה לבנות פרופיל ביצועים לפי סוג משימה, מודל וספק. לדוגמה:

* Model X ל־React UI
* Model Y ל־Python Backend
* Model Z ל־Debugging
* Provider A ל־Photorealistic Images
* Provider B ל־Simple Icons
* Provider C ל־Video Animation
* Provider D ל־Music Generation

ביצועים היסטוריים הם גורם בהחלטה, אך אינם מחליפים Verification בפועל.

יש לעדכן את הפרופילים רק לאחר:

* מינימום מדגם מוגדר
* הפרדת גרסאות Model ו־Policy
* סינון ניסויים לא מייצגים
* בדיקת שינויי מחיר
* בדיקת שינויי זמינות
* בדיקת Calibration של התחזיות

9.3 מדדים

יש למדוד:

* שיעור הצלחה לפי סוג משימה
* עלות ממוצעת לתוצר מאושר
* עלות P90 לתוצר מאושר
* מספר Retries ו־Repairs ממוצע
* שיעור Escalation ו־Fallback
* זמן ביצוע
* איכות לפי Verifier
* אמינות ספקים
* עלות לפי סוג מוצר
* שיעור קבלה סופי
* שיעור כשלי תקציב ודדליין
* הצלחה לאחר Repair או Escalation
* עלות צפויה לעומת עלות בפועל
* שיעור חריגות תקציב
* שיעור תוצרים מאושרים
* שיעור כשל קריטי לאחר מסירה
* עמידה ב־SLO
* ניצול Error Budget
* שלמות Telemetry
* דיוק תחזית עלות והצלחה

10. רכיבי המערכת ודרישות מימוש

10.1 רכיבים

יש להפריד בין:

* Task Planner
* DAG Executor
* Model/Provider Selector
* Cost Estimator
* Budget Manager
* Reservation Ledger
* Verification Engine
* Repair Manager
* Retry Manager
* Escalation Manager
* Product Composer
* Usage and Feedback Store
* KPI/SLO Metrics Pipeline
* Error Budget Manager
* Alerting and Incident Manager
* Policy Engine

ה־model_router הוא נקודת כניסה לבחירת מודלים, אך אינו נושא לבדו את אחריות התזמור. מנוע הביצוע צריך להכיר את התלויות, התוצרים, התקציב, ה־Verification וה־SLO הרלוונטיים להרצה.

10.2 דרישות ארכיטקטוניות

המערכת צריכה לתמוך ב:

* פירוק בקשת משתמש ל־Task/Capability DAG
* בחירת Provider/Model לכל Task
* ביצוע סדרתי ומקבילי
* העברת תוצרים בין משימות
* Verification ברמת Task וברמת מוצר
* Retry ו־Repair מקומיים
* Escalation ו־Fallback
* Budget Reservation ו־Settlement
* איסוף עלויות בפועל
* שמירת נתוני ביצוע ו־Feedback
* חיבור תוצרים למוצר סופי
* סיווג כשל מובנה
* שמירת התוצר הטוב ביותר
* תנאי עצירה מפורשים
* מניעת חריגה מתקציב ומ־ROI מינימלי
* חישוב KPI ו־SLO בזמן אמת ובאצווה
* חישוב Error Budget
* התראות על חריגה מ־SLO
* פילוח מדדים לפי Provider, Model, Task ו־Product
* שמירת גרסאות Policy, Prompt ו־Model
* זיהוי והפרדה בין כשל תוכן לכשל תשתיתי
* תמיכה ב־Rollback וב־Provider Disablement

10.3 נתוני הרצה

לכל הרצה יש לשמור:

* מזהה מוצר ו־DAG
* מזהה Task
* קלט ותוצר או הפניה אליהם
* Provider ו־Model
* עלות משוערת ועלות בפועל
* זמני התחלה וסיום
* תוצאת Verification
* מספר Retries, Repairs ו־Escalations
* החלטות Escalation
* מזהי Reservations
* סכומי Reservation, Settlement ושחרור
* סיבת כשל או עצירה
* תוצאת קבלה סופית
* רמת קריטיות
* SLO יעד
* SLO בפועל
* Error Budget שנצרך
* חריגת תקציב, אם הייתה
* גרסת Policy, Prompt ו־Model
* Provider health snapshot בזמן ההרצה

10.4 שלבי מימוש

שלב ראשון

* הפרדת Request מ־Task
* בחירת מודל או ספק לכל Task
* תיעוד עלות ותוצאת ביצוע
* Verification בסיסי
* Retry ו־Repair מוגבלים
* תנאי עצירה בסיסיים
* Reservation פשוטה לכל פעולה
* מדידת שיעור הצלחה, עלות, זמן וחריגות תקציב
* Dashboard בסיסי ל־KPI
* SLO ראשוניים ל־Product Success, Cost ו־Latency

שלב שני

* Escalation ו־Fallback
* Budget Reservation מלאה עם Settlement ושחרור
* בחירה לפי ביצועים היסטוריים
* משימות מקביליות
* Product Composer
* סיווג כשל מובנה
* מדידת Repair ו־Provider Reliability
* Error Budget
* התראות ו־Incident Management
* פילוח KPI לפי סוג מוצר וספק

שלב שלישי

* הרחבת מנוע האופטימיזציה
* שילוב נתוני שימוש אמיתיים
* שיפור הערכת הסתברות הצלחה
* אופטימיזציה משולבת של איכות, עלות וזמן
* מדיניות דינמית לפי משתמש, תוכנית ותקציב
* למידת עלות כשל, Repair ו־Escalation
* סימולציית תקציב לפני ביצוע DAG מלא
* Calibration אוטומטי של Verifier
* SLO דינמיים לפי רמת קריטיות
* אופטימיזציה לפי Error Budget
* ניסויים מבוקרים והשוואת Provider Mix

11. סיכום

148AI צריכה להיבנות כ־Dynamic Multi-Model Product Orchestrator, ולא כ־Router שבוחר מודל יחיד לכל בקשה.

המערכת צריכה:

1. להבין את המוצר שהמשתמש רוצה.
2. לפרק אותו ל־Task/Capability DAG.
3. לבחור מודל, ספק או כלי לכל משימה.
4. להעריך עלות כוללת צפויה, כולל כשל, Verification, Repair ו־Escalation.
5. לבצע Budget Reservation לפני פעולות משמעותיות.
6. לאמת כל תוצר באמצעות Verification מובנה.
7. לבצע Repair כאשר הכשל מקומי.
8. לבצע Retry רק כאשר קיימת הצדקה הסתברותית וכלכלית.
9. לבצע Escalation או Fallback כאשר היכולת או האמינות אינן מספיקות.
10. לעצור לפי PASS, איכות מינימלית, תקציב, דדליין, מגבלות ניסיון, היעדר מועמד או ROI.
11. לחבר את התוצרים למוצר סופי אחד.
12. לשמור נתוני ביצוע וללמוד מהם.
13. למדוד KPI ו־SLO עבור איכות, עלות לתוצר מאושר, זמן ביצוע, שיעור הצלחה, חריגות תקציב, שיעור תיקונים ואמינות ספקים.
14. להפעיל Error Budget, התראות ופעולות מתקנות כאשר היעדים אינם נשמרים.
15. למזער את העלות הכוללת תוך שמירה על איכות התוצאה.

זהו יתרון הליבה של 148AI: לא רק שימוש במודלים קיימים, אלא תזמור דינמי של היכולות המתאימות ביותר מכל מודל וספק כדי ליצור את המוצר הסופי הטוב, המאומת והמשתלם ביותר.