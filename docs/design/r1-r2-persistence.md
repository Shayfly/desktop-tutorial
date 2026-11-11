# R1 + R2 design — the persistence decision (run 10b triage, for Michael's sign-off)

Status: SIGNED by Michael 2026-11-11 12:04 with six conditions (section 8). Sections 8.1-8.6 override anything
earlier in this document that disagrees with them. Fixtures: tests/test_run10b_fixtures.py (PR #297, merged).

## 0. Where "content only: yes" fell in arm 1 — traced to the line

The customer answered the model's content question twice ("מידע", "מידע"); the model proposed
`content_only=yes, confidence high` four times (intake_messages 1567, 1579, 1581, 1583). The approved brief
(project_briefs, prj_F1VB5RGuECqXHg rev 8) has **no `content_only` field at all**; only `login` and `personal_data`
are there as confirmed answers. The answer never had a slot to land in:

1. `omni_prod/discovery.py:111` — the `content_only` question has
   `ask_if=lambda v: ... and v.get('_family') == 'website'`.
2. `omni_prod/intake/artifact_fields.py:56-77` — `ARTIFACT_FIELDS["web_app"]` (`_COMMON + _APP`) has no `content_only` field
   (only `'website'` does), and `gaps.detect()` (`gaps.py:176`) builds its candidates from that set plus pending
   discovery questions — which, by (1), never include `content_only` for a web_app.
3. `_family` comes from `classify_family(prompt)`: "תבנה דף לעסק שלי" -> `web_app` (only "דף נחיתה" -> website).

So the field is unreachable for every brief the classifier calls web_app; the model's proposal is discarded because
there is no confirmable field to attach it to; `requirements_text` (`discovery.py:528`) never writes
`CONTENT_ONLY_LINE`; `compile()` (`product_architect.py:223`) sees `content_only=False`; the keyword path
(`_infer_data_requirements`, `product_architect.py:488`) and the brain's modules decide alone. Arm 1 passed only
because its model-written behaviour plan covered data_create with a refusal (POST -> 405); arms 2-3 did not.

**R1 therefore lands in two places, not one:** the decision slot must exist independent of the family (intake), and
the contract must obey it in one place (compile). The classifier (R3) stops being load-bearing.

A second keyword flaw on the same path: `_RECORDS` (`artifact_fields.py:22`) contains `טלפון|מייל|הזמנ`, so a page
that SHOWS a phone or says "להזמין זר" is cued as saving records. Showing contact details is not storing them.

## 1. Where the decision is stored — typed fields

Brief field (intake, `project_briefs.brief_json.fields`):
`persistence: {"value": "none" | "records", "source": "answer" | "message", "confidence": "confirmed"}`
(`content_only=yes` is kept as a read-only alias of `persistence=none` for old briefs; no migration).

Approved brief block (written by `requirements_text`, the only trusted channel into `compile`, parsed from the LAST
generated marker exactly like `read_approved`):
`Product decisions v1: {"version":1,"artifact_class":"page"|"app","persistence":"none"|"records","source":"customer"}`

BuildContract (typed, `build_contract.py`): two new fields
`artifact_class: "page" | "app"` and `persistence: "none" | "records"`, plus
`persistence_source: "customer" | "keyword"` so every later gate knows whether a human decided.

## 2. Where precedence is enforced — one function

`product_architect.py`, a single resolver called once from `compile()`; nothing else derives data needs:

```python
def resolve_persistence(decisions, intent, modules) -> tuple[str, str, tuple[str, ...]]:
    """(persistence, source, data_requirements). An explicit customer decision always wins."""
    if decisions.persistence == 'none':
        return 'none', 'customer', ()                       # keywords are not consulted at all
    if decisions.persistence == 'records':
        reqs = _infer_data_requirements(intent, modules) or ('records',)
        return 'records', 'customer', reqs                   # keywords only NAME the records
    reqs = _infer_data_requirements(intent, modules)          # no decision: then and only then, keywords
    return ('records' if reqs else 'none'), 'keyword', reqs
```

`persistence='none'` also selects the existing content-only floor (`_content_only_spec`) and the
`static_content_site` default, so `acceptance_scope` waives data_create/update/delete through the path that already
exists (`web_saas_acceptance.py:104`). The leftover today — the keyword list staying in a content-only contract — is
removed by construction.

## 3. Intake: the slot exists for every family

- `content_only` becomes `persistence`, declared in `_COMMON` (not `_SITE`), `confirm=True`, non-delegable, never
  defaulted (the existing rule). Asked when login is none and no storing feature was named; otherwise implied:
  sign-in, a saved form, sign-ups, bookings ON the site -> `records` (still shown in the summary).
- Cues are split: `_STORES` = collection verbs (טופס נשמר, נרשמים, השארת פרטים, קביעת תור באתר, sign up, saved form);
  phone/e-mail/WhatsApp shown on the page and "להזמין" inside a message template are NOT storage cues.
- What the customer already said pre-selects the chip ("דף סטטי", "רק טלפון ווואטסאפ", "בלי הזמנה באתר" -> none);
  the chip is still pressed once. One question, never repeated once answered (it is a confirmed field).

## 4. R2 — a realizability check that resolves

Runs at gate 1 (before a plan exists), next to `planning/feasibility.assess`:

```
needs_decision  iff  contract.persistence_source == 'keyword'
                and  contract.data_requirements                       # the contract would demand records
                and  not stores_feature(brief)                        # no sign-in, no saved form, personal_data != yes
```

New finding outcome `NEEDS_DECISION` (not BLOCKED/UNSUPPORTED). The customer sees one question with two buttons,
in Hebrew, no internal names:

> ביקשתם דף, אבל לא ברור אם הוא שומר מידע. מה נכון?
> [ דף לקריאה בלבד — לא נשמר כלום ]   [ אתר ששומר מידע (טפסים, הזמנות, רשימות) ]

Each button writes `persistence` (source answer, confirmed) -> new brief revision -> spec re-rendered -> gate 1 again.

If the customer ignores it: no plan and no build; gate 1 stays closed and every turn that tries to approve gets the
same one-line answer naming the ONE missing decision (this also fixes run-10b finding 5, the silent wait). It is
never defaulted, because the two wrong guesses fail differently: "none" on a site that must save loses customer
data; "records" on a page burns repair rounds (run 10b).

Inverse check, same place: `persistence == 'records'` (customer) with no data requirement at all -> the contract
names a generic `records` module instead of passing a store-nothing contract.

## 5. R2 is silent when a decision exists

`persistence_source == 'customer'` -> the check returns nothing, whatever the keywords say. Fixture: florist with
`persistence=none` written -> no question, contract has no data requirement, no data acceptance.

## 6. Fixtures (added in the R1/R2 PRs; the locked ones flip)

| fixture | today | after R1+R2 |
|---|---|---|
| locksmith / florist-details / florist-nodetails, decision `none` | data reqs from keywords | `()`, content-only floor (3 locked failures flip) |
| same three, NO decision | build proceeds, fails after 5 rounds | `NEEDS_DECISION` before any build |
| positive: "אתר עם הרשמה" | data kept | data kept; R2 silent (sign-in is a storing feature) |
| positive: "טופס ששולח מייל ונשמר" | data kept | data kept; R2 silent (saved form) |
| explicit `none` + keyword "הזמנה" | n/a | R2 silent, no data (point 5) |
| phone shown on page | cued as records | NOT a storage cue |

## 7. Out of scope here

R3 (classifier) becomes a tie-breaker only: it may pre-select the chip, never decide. R4 (warning keyed to
"business page") is the next PR. Pricing untouched.

## 8. Conditions of the signature (Michael 2026-11-11 12:04) — binding

### 8.1 Strong and weak cues
`_infer_data_requirements` and the intake cue list are split into two typed sets:

- **strong** (alone enough for `records`): sign-up / registration, sign-in, cart, payment, a list of orders or
  bookings kept on the site, a personal area, a form that is SAVED ("נרשמים", "התחברות", "סל", "תשלום", "רשימת
  הזמנות", "אזור אישי", "טופס שנשמר", "השארת פרטים").
- **weak** (never enough alone): phone, e-mail, WhatsApp, "להזמין", "הזמנה" (an order by phone is not a record),
  "לקוחות" (a page about customers stores nothing).

Rule: with no customer decision, `persistence = records` only if at least one STRONG cue is present. Weak cues alone
give `persistence = none` with `source = keyword` -- they may NAME records once a strong cue exists, never create
the requirement. This is what keeps R2 from asking in almost every business brief.

### 8.2 Where NEEDS_DECISION fires — discovery, first turn
Not in `compile()`. The persistence question is a discovery question (like `content_only` today, minus the family
condition), raised in the FIRST interpretation turn when it is open: login none, no strong cue, no customer answer.
It is asked once, pre-selected from what the customer said, and answered by chip. The check at gate 1 (section 4)
stays only as a backstop assertion: if a contract reaches gate 1 with `source = keyword` and data requirements,
discovery failed to ask -- the same two buttons are shown AND the event is logged as a defect
(`persistence_backstop_fired`), never silently.

### 8.3 `artifact_class` is derived, never classified
`artifact_class` is written by the resolver only: `page` iff `persistence == none` and the contract has no storing
capability (8.5); otherwise `app`. The classifier (`classify_family`) never writes it and is not read by the
resolver; at most it pre-selects the persistence chip.

### 8.4 A stale decision is re-asked
On every brief edit, the resolver re-reads the edited text. If `persistence == none` with `source == customer` and
the edit adds a STRONG cue or a storing capability ("עם הרשמה"), the field is moved to `stale` and the persistence
question is asked again, quoting the new words. A stale decision never reaches a contract: compile refuses a brief
whose persistence is `stale`. Fixture: approve `none`, edit in "עם הרשמה" -> question asked again, no contract.

### 8.5 R2 reads the contract's typed capabilities, not the brief text
New typed contract field `storing_capabilities: tuple[str, ...]`, computed by the resolver from typed facts only:
`auth_session` in infrastructure, roles beyond `user`, required integrations `payments` / `email` with a saved form,
and the strong cues of 8.1 as resolved by the brain. R2's "no storing capability" is `not
contract.storing_capabilities`. `database` infrastructure is NOT a signal: it is itself derived from persistence
(`none` -> no database), so it cannot vote for itself.

### 8.6 Every NEEDS_DECISION is counted
Each time the persistence question is shown it is recorded in the turn interpretation
(`decision_asked: persistence`, with `trigger: discovery | backstop | stale`), and the frozen-run report counts it in
`humanDecisions` with a separate `systemAskedDecisions` breakdown, so a mechanism that adds questions is measured.

### Fixtures added for the conditions
| condition | fixture |
|---|---|
| 8.1 | the three run-10b briefs with NO decision -> `persistence=none, source=keyword`, no question, no data requirement |
| 8.1 | "דף לעסק עם טלפון ומייל" -> no question; "דף עם טופס שנשמר" -> `records` |
| 8.2 | first interpretation turn of an ambiguous brief carries `decision_asked: persistence` |
| 8.3 | `artifact_class` identical with `classify_family` monkeypatched to return anything |
| 8.4 | `none` approved, then "עם הרשמה" -> stale, re-asked, compile refuses |
| 8.5 | positive fixtures: `storing_capabilities` non-empty; florist: empty |
| 8.6 | the turn interpretation and the report field |
