# R1 + R2 design — the persistence decision (run 10b triage, for Michael's sign-off)

Status: DESIGN. No code until signed. Fixtures: tests/test_run10b_fixtures.py (PR #297).

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
