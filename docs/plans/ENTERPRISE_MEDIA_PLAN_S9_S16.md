# Enterprise plan, continued: world-class sites, apps, software, games, songs and videos (stages S9 to S16)

Author: Claude Code (chief architect), 2026-11-27. No production code was written, nothing was committed, pushed,
merged or deployed, and no paid service was called.

**Order executed.** The owner's message of 2026-11-27, as the launching agent passed it on, word for word:
"תוספים או שתבנה קוד אצלנו כדי שהלקוח יוכל לייצר לנו משחקים שירים סרטונים אתרים מערכות תוכנות שנראים ויזואלית ברמה הכי
גבוהה בעולם כיום, תתכנן ותוסיף את זה גם להמשך תוכנית אנטרפריז ברמת מערכת אנטרפייז". The highest file in `inbox/` on
main is `inbox/003-2026-11-27-owner-decisions.md`; it does not record this order yet. Recording it there is the
coordinator's task.

**Code read.** `origin/main` at `e29015c` (exported to
`/tmp/claude-0/-home-user-desktop-tutorial/ef722132-a1de-581a-aa3a-c4e5105bcddd/scratchpad/em_main_e29015c`). Main moved
to `bc7077e` while I worked; of the paths this document cites, only `inbox/` changed (003 was added;
`git diff --stat e29015c origin/main -- <cited paths>`). Line numbers are those of `e29015c`.

**Built on, not repeated.** The site diagnosis and its slices are the other architect's document,
`/tmp/claude-0/-home-user-desktop-tutorial/ef722132-a1de-581a-aa3a-c4e5105bcddd/scratchpad/visual_design.md`
(called VD below). Stage S10 adopts its slices unchanged and adds only what it left open.

**Limits of the research, said first.**
- This session could not open provider pages: `WebFetch` fails with `getaddrinfo ENOTFOUND` for `ai.google.dev` and
  `docs.cloud.google.com` (hosts outside the session's allowed network domains). Every price and licence below was
  read through web search summaries on 2026-11-27, with the page's URL beside it. None was read on the page itself.
  **Every price here is an estimate** until an implementer reads it on the official page and records it in
  `provider_pricing` with its source and date.
- The search connector Tavily was not used: its credits are the owner's money.
- No lawyer read any provider's terms. The repository says the same of its own records
  (`omni_prod/rights_sources.json`, `rule`: "no lawyer reviewed any of them").

---

## 0. סיכום בעברית פשוטה

1. **ההחלטה:** קונים מספקים חיצוניים רק את חומר הגלם (תמונה, שניות וידאו, מוזיקה, קול, מודל תלת-ממד). את כל מה
   שקובע את הרמה בונים אצלנו: הכיוון האמנותי, ההרכבה, הבדיקות והמסירה. לכל סוג פלט יש "ערכה" בדוקה שלנו, והמודל
   ממלא אותה ולא ממציא מאפס. כך זה כבר עובד באתרים (ספריית הסקשנים) ובמשחקים (ערכת המשחקים).
2. **הסדר:** אתרים, אחריהם אפליקציות ומשחקי 2D ביחד, אחריהם תשתית המדיה, שיר, ובסוף סרטון. משחקי 3D רק בהחלטה שלך.
3. **מספור:** בתוכנית v3 שלבים 7 ו-8 כבר תפוסים (בדיקות מקצה לקצה, חבילת מסירה). לכן השלבים החדשים הם S9 עד S16.
4. **מה במחסן:** שיר וסרטון הם פריט 137, ותמחור הוא פריט 136. תכננתי אותם כי ביקשת, ולא נבנה מהם דבר עד שתשחרר.
5. **כסף:** אתר, אפליקציה, משחק 2D ושיר נכנסים מתחת ל-2$ לבנייה (הערכה). סרטון של 30 שניות באיכות 1080p לא נכנס:
   3.7 עד 5.5$ (הערכה). סרטון של 15 שניות ב-720p נכנס בקושי: 1.3 עד 1.9$ (הערכה).
6. **הסיכון הגדול ביותר אינו ספק.** מתוך 62 בניות בייצור רק 16 הסתיימו בהצלחה (VD סעיף 1.2). רמה עולמית מתחילה
   בבנייה שמסתיימת, ולכן כל סוג חדש נכנס דרך ערכה בדוקה ולא דרך קוד חופשי של המודל.
7. **17 החלטות שלך** מחכות בסעיף 9, כל אחת כשאלה אחת עם אפשרויות. חמש השאלות של מסמך האתרים נספרות שם כשאלה אחת (שאלה 5).

---

## 1. The decision

**Recommended: one pipeline and one profile per output type; buy generation, build direction, composition,
verification and delivery.**

- **Buy** (through the capability and provider layer that already exists): pixels, video seconds, music, speech and
  3D meshes. These are the things a small team cannot make better than the model vendors, and their price falls every
  quarter.
- **Build** (as tested kits the model fills in, never free-form output): the art direction per trade, the composition
  engine per type, the gates that measure the result, the rights record, the storage and the delivery. This is where
  the visual level is decided and where a customer's product becomes theirs (iron laws 20, 22, 25).
- **Add-ons** in the owner's sense are open-source libraries with a permissive licence, vendored into the build with
  their licence recorded. The generated product never loads code from another host: the sandbox has no network and no
  install step (`omni_prod/dependency_policy.py:1-14`), and a product must run without us (iron law 20).

The pattern is already in the repository twice: `omni_prod/section_library` for sites and `omni_prod/game_kit` for
games. The measured difference on sites is the argument: the designed route cost $0.108 for a build against $0.53 to
$0.95 on the path where the model writes the page (VD 1.3), and it is the only route on which composition can be
checked deterministically.

### Alternatives rejected

| Alternative | Why not |
|---|---|
| **Buy finished products** (a white-label site builder, an app builder, a consumer music or video app) | The best-known music apps have no official public API (Suno, Udio: search 2026-11-27, third-party sources). A product built inside someone else's builder is not the customer's to take away (iron laws 20, 25). It would be a second system beside ours (AGENTS.md law 9). |
| **Host open models ourselves** | No GPU exists: the worker is one Oracle Always Free ARM machine with 2 cores and 12 GB (`infra/worker-host/README_HE.md:18-22`), and `CURRENT_TRUTH_V28_HE.md` lists GPU generation as not verified. Open licences carry traps: Hunyuan3D's licence excludes the EU, the UK and South Korea; Stability's community licence ends above $1M of annual revenue. |
| **Let the frontier model write everything, with better prompts** | That is today's legacy path: 5 to 9 times the cost, design scores of 57 to 87, a different page every run (VD 1.2, 2.1), and nothing deterministic to gate. All-time, 16 of 62 production builds ended READY. |
| **One aggregator for every modality** (only Replicate, or only Venice) | One point of failure, and the licence still differs per model. Venice's terms grant its service "solely for your personal, non-commercial use" (section 7.1, as search read it) and take a licence over outputs (10.6; WAREHOUSE.md item 137). Replicate stays as one of two providers because its adapter exists. |
| **Media first, because it demos best** | The owner's order is sites first (OWNERS.md rule 10). Songs and videos are in the warehouse (137), and they need storage, rights records and a render queue that do not exist. |
| **A new vision reviewer that scores "premium"** | VD already rejected it, rightly: taste scored by a model is not a gate one can calibrate. This plan keeps VD's deterministic measures as the gate and adds only a calibration test for the critic that exists (S9.4); if the critic fails calibration it stays advisory and nothing depends on it. |

### Risks

1. **Builds that do not finish.** 16 READY of 62 (VD 1.2); repair rounds were 68% of model cost in 14 days of
   production (STATUS.md, 2026-11-26 owner-costs entry). A new type built free-form would inherit this. Mitigation:
   every type enters through a kit with a schema and a probe; the route to the kit is measured per week.
2. **Rights in music and video.** Terms are unclear exactly where it matters: Google's API terms waive ownership but
   developers' questions about distributing Lyria output are unanswered on Google's forum; ElevenLabs forbids
   reselling API access to its music service without reseller status. No lawyer has read anything. Mitigation: S13.3
   blocks on an unknown right; question 12 asks for a legal reading before anything is sold.
3. **Video does not fit the $2 line.** See section 4. The cap stays; the owner decides a tier (question 9; warehouse 136).
4. **Hebrew singing is untested.** No provider's Hebrew vocals were heard. A song whose words cannot be understood is
   a failed product whatever its loudness. Mitigation: the bake-off of S14.0 before any build.
5. **Provider churn.** In this repository's own record: the Sora API closed (WAREHOUSE 137); OpenAI's GPT Image 1 was
   shut down on 2026-10-23 (search, developers.openai.com). Mitigation: the matrix's lifecycle fields, two providers
   per modality, and a weekly re-read of prices and terms (S13.3).
6. **One worker.** One ARM host runs builds and would run renders. Mitigation: a separate queue with its own time
   budget (S13.4); a second host is the owner's money (question 16).
7. **Thin calibration.** 16 READY builds exist. Every threshold below is a first estimate that enters at warn and
   blocks only after three builds (the owner's rule for gates, `omni_prod/skill_units/gate.py:58-83`).
8. **Privacy is the product (iron law 1).** Every media provider here is a direct provider, not a private model. The
   stage tag must say so (iron law 24). `PROVIDER_MATRIX.json` writes "customer screenshots never sent to third-party
   AI" on every model row, while `omni_prod/design_review.py:15-16` says screenshots are sent to the routed provider.
   Before a customer's photo goes to an image-to-video model (S15), that sentence must be made true or corrected.
9. **Scope.** Eight stages for one working agent. The order below is strict so that each stage closes before the next
   spends money.

---

## 2. Facts that shape the plan

### 2.1 Discrepancies found, reported and not settled in silence

| # | Finding | Evidence |
|---|---|---|
| D1 | **Stage ids S7 and S8 are taken.** Plan v3 already has "שלב 7" (end-to-end, review, controlled rollout) with tasks S7.1 to S7.6 and "שלב 8" (delivery pack) with S8.1 and S8.2. The task named the new stages "S7, S8 and so on"; they are numbered **S9 to S16** here. | `inbox/002-2026-11-25-owner-plan-v3.md:285-334` |
| D2 | **The "$2 per build" line is not what the engine enforces today.** `m5_founder_build_budget` ($2) applies only when `OMNI_FOUNDER_NO_BUILD_LIMIT=0`; by the owner's word of 2026-11-26 his account builds with no money limit and two safety bounds ($25, 400 calls). Every other account is bound by its plan's class cap, which is a soft cap: LIGHT $0.60, STANDARD $1.60, ADVANCED $3.00, HEAVY $5.50, EXTREME $18. CLAUDE.md section 6 still says the $2 cap stays. This plan compares every cost with $2, as instructed, and with the class caps. | `omni_prod/pricing.py:225-228, 326-333, 344-369`; STATUS.md 2026-11-26 ("Contradictions, the owner's newer word governs") |
| D3 | **An owner's plan for five output types already exists**: `docs/OUTPUT_PLATFORM_PLAN_HE.md` (2026-11-15), with one pipeline and a profile per type, gates G1 to G10 (G7 media fidelity, G8 runtime), phases P0 to P5 and a ceiling per type (site $0.60, web app $0.90, game $1.50, song $0.80, clip $4.50). This document extends it and builds no second plan: S10 = P1, S11 = P2, S12 = P3, S14 = P4, S15 = P5. Its section 13 puts full-length songs, advanced video editing, native apps and game networking out of scope; today's order may reopen the first two (question 14). | `docs/OUTPUT_PLATFORM_PLAN_HE.md` sections 7, 9, 12, 13 |
| D4 | **"A7" means two things.** In plan v3, A7 is design and A8 is media. In the output plan, A7 is rights and A4 is assets. Below, "the rights gate" always means G5 of the output plan. | `inbox/002...:455-464`; `docs/OUTPUT_PLATFORM_PLAN_HE.md` section 4 |
| D5 | **The provider matrix is stale on images.** `PROVIDER_MATRIX.json` (`as_of` 2026-11-18) lists `replicate-flux-schnell` as UNVERIFIED and NOT_ROUTED, while the five latest READY builds each carry a Replicate usage row of $0.003 (VD 1.3). AGENTS.md rule 3 says status is derived. | `PROVIDER_MATRIX.json`; VD 1.3 |
| D6 | **The 2D game kit is merged and tested but nothing in the product imports it.** `game` is still refused. This is correct under law 2 (it is not marked active), and it is the first job of S12. | `grep -rn game_kit omni_prod` finds only the kit itself; `omni_prod/output_profile/__init__.py:102`; `omni_prod/intake/families.py:15` |
| D7 | **`game_pipeline.py` and `mobile_pipeline.py` are plans, not capabilities.** They return Godot, Unity, Unreal, Gradle and Xcode command lines and test only `shutil.which`. `investor_app.py:29,33` imports them. Whether their routes are refused in production was not checked. | `omni_prod/game_pipeline.py:16-27`; `omni_prod/mobile_pipeline.py:16-25` |
| D8 | **`media_branding.py` needs ffmpeg and no image has it.** | `omni_prod/media_branding.py:61-63`; `grep -n ffmpeg Dockerfile infra/sandbox/Dockerfile` returns nothing |
| D9 | **The hash-chained audit module has no caller in the product** (inferred from grep; `agent_os/audit.py` is a different module). | `grep -rn "create_event(" omni_prod` finds only `omni_prod/audit.py` |
| D10 | **`feature_flags.py` says it is the only place a flag is read**, and holds one flag. Rollout switches are read elsewhere: `OMNI_DESIGN_REVIEW` and `OMNI_GATE_<gate>`. | `omni_prod/feature_flags.py:1,17`; `omni_prod/design_review.py:106`; `omni_prod/skill_units/gate.py:93` |
| D11 | **Image providers do not fail over.** `build_image_provider` returns exactly one provider, chosen by an environment variable. | `omni_prod/providers/image_provider.py:582-606` |
| D12 | **Model names differ between records.** WAREHOUSE 137 names "Gemini Omni 1.2 Flash"; the matrix lists `gemini-omni-1-1-flash`; `model_discovery.DIRECT_MEDIA_MODELS` lists both. | `omni_prod/model_discovery.py:22-27` |

### 2.2 Warehouse collisions, said in advance (CLAUDE.md section 7.2)

Only the owner takes an item out. Each line says what the plan needs.

| Item | State in WAREHOUSE.md | What collides | Needs |
|---|---|---|---|
| **137** music and video | **in the warehouse** (the owner, 2026-11-26: "לחכות בינתיים"). "לא נבנים שיר, סרטון או חיבור לספק מדיה, ולא מוצאת הוצאה על בדיקה" | S13.1, S13.4 to S13.7 and S13.9 (media infrastructure), all of S14 (song) and S15 (video), generated music in games (S12.5), a video loop in a site's hero (S15.4). Planning them here follows today's order, which is later and explicit; CLAUDE.md 7.1 ("not planned") is the earlier rule, and the contradiction is reported, not settled. | **requires the owner to release item 137** (question 8) |
| **136** cost limits and pricing | **in the warehouse** ("לא נבנית הגבלת עלות חדשה ולא נקבע מחיר") | Any tier for video, any ceiling per type, the cost class a game or an app build belongs to. Costs below are reported, not enforced. | **requires the owner to release item 136** for the part he chooses (question 9) |
| **134** 2D browser games | released 2026-11-23, "בתכנון"; stage 1 (the kit) merged in #516 | S12.1 and S12.2 are 134 as written. S12.3 and S12.4 widen its wording: 134 says the model writes "rules, levels, characters and texts" and the kit draws them; generated sprites and backgrounds are not in it. | the owner widens 134 or opens a new item (question 6) |
| **135** installed web app (PWA) | released 2026-11-23, "בתכנון" | S11.4 is 135. | none |
| **130** separate apps pipeline | released 2026-11-22, queued | S11.1 to S11.3 are 130. | none |
| **125** design contract per category | released; widened by the owner on 2026-11-27 (inbox/003: a dark and a light variant per palette) | S10.5 is 125 (VD S4). VD question 4 asks to widen it further. | VD question 4 |
| **122, 123** mandatory fields, page typology | released, "בתכנון" | The recorded order is 122, 123, 125. VD question 1 asks to do visuals first. S11's screen schema is to apps what 123 is to pages: reported. | VD question 1 |
| **126, 127, 129** fonts, domains, scripts | built or released | No new font, no change to the domain files' schema, logical properties only. Captions in S15 use the font pairs of 126. | none |
| **118** image as a file | "בבנייה"; not verified on a production build | S13.1 extends the same module (`repository_assets.py`) and the same single decode point. S10.4 depends on 118 (VD risk 2). | none; reported |
| **131** publish to a real address | released, queued | S13.2's delivery of media files and S15's video on a published site share its files. | none; reported |
| **128** image and voice intake | released, queued | Speech-to-text is a media provider; if it goes to Google or ElevenLabs it shares the adapter of S13.6. | none; reported |
| **120, 116** frozen corpus | released, blocked on a migration and decisions | A benchmark of other people's sites (S9.4) would need the corpus and its rights. S9.4 uses our own renders instead. | none |
| **124** see, screenshot, fix | released; the sketch card is built now (inbox/003) | The player card of S14 and S15 lives in the same conversation card. One card mechanism, not two. | none; reported |
| **121** worker-down alert | built | S13.4 adds the media queue to the same check. | none |
| **65** platformer run | out of the warehouse; it is 134's acceptance 7 | S12.2. One paid production build "only on explicit instruction". | the owner's go for the build |
| 3D games | **in no item**. `3d_experience` is refused (`output_profile/__init__.py:120`); the owner chose "משחקי דפדפן (HTML5 canvas)" on 2026-11-23 | S16. | **a new warehouse item, by the owner** (question 17) |

---

## 3. The six output types

Legend: **verified** = a run or a production row exists and is cited; **unverified** = code or a contract exists and no
run was found; **absent** = no code.

### 3.1 Web site

**Current truth.**
- Verified: `website` is executable (`omni_prod/intake/families.py:15`). Two routes: the designed library
  (`omni_prod/section_library`, `site_content.decide`) and the legacy path. Production: 16 READY builds all-time; of
  the last five, scores 57 to 87, three with no picture (VD 1.2). FLUX schnell on Replicate made pictures at $0.003
  each (VD 1.3).
- Unverified: warehouse 118 and the default-hero fix #541 on a production build (VD 2.2); the Google image adapter
  (`omni_prod/providers/google_image.py:36-46` never reports more than PARTIAL, "not live verified"); any performance
  number of a customer's page in a real browser under throttling.
- Absent: a gate that blocks a generic page (VD 2.1, "Gates"); publishing to a real address (131).

**The world-class bar** (every number a first estimate, at warn until three builds confirm it).

| Dimension | Criterion | Where it is measured |
|---|---|---|
| First screen | hero picture covers >= 40% of a desktop screen and >= 35% of a phone screen; headline and main action inside the first screen | VD S1, S2 |
| Imagery | >= 1 real picture; on a page with 3 or more, no run longer than 2.5 phone screens without one; every picture passes `image_match` on the customer's own words | VD S2, S3; `omni_prod/image_match.py` |
| Composition | >= 4 distinct section compositions; markup-skeleton similarity between two trades: mean <= 0.80, no pair above 0.90 (today 0.899 and 0.993) | VD S5 |
| Text on pictures | contrast >= 4.5 (3 for large text) against the sampled pixels | VD S2 |
| Performance (lab, in the browser run that exists) | LCP <= 2.5 s, CLS <= 0.1, total blocking time <= 200 ms, under 4x CPU slow-down and a mobile network profile; page weight <= 1.8 MB, pictures <= 1.5 MB (`a4.PAGE_IMAGE_BUDGET_BYTES`) | S10.9. Thresholds: web.dev, Core Web Vitals (LCP 2.5 s, INP 200 ms, CLS 0.1 at the 75th percentile). TBT stands in for INP in a lab. |
| Accessibility | WCAG 2.2 AA automated checks: 0 serious findings; the existing G3 units | `omni_prod/skill_units/a11y_*` |
| Critic | the existing design critic, on a fixed rubric, by a model other than the builder, **only if** it passes calibration (S9.4): score >= the calibrated minimum | S10.10 |
| Truth | every fact from the brief; no placeholder; the existing G2 and copy units | existing |

**Build or buy.**
- Buy: pictures. Two tiers: the hero from a strong model, item pictures from the cheap one.

  | Candidate | Price (estimate; read 2026-11-27 through search) | Rights as read | Source |
  |---|---|---|---|
  | FLUX schnell on Replicate (today) | $0.003 per image (measured in production, VD 1.3) | Apache 2.0, commercial use allowed | huggingface.co/black-forest-labs/FLUX.1-schnell |
  | Google Nano Banana 2.1 | about $0.034 per 1K image; batch about half | Google "won't claim ownership"; paid tier not used to improve products; the matrix already records Gemini paid tier as COMMERCIAL_APPROVED | ai.google.dev/gemini-api/docs/pricing; ai.google.dev/gemini-api/terms |
  | Google Nano Banana 2 (3.1 Flash Image) | $0.045 (0.5K), $0.067 (1K), $0.101 (2K), $0.151 (4K) | same | same |
  | Google Nano Banana Pro (3 Pro Image) | $0.134 (1K to 2K), $0.24 (4K) | same | same |
  | FLUX 1.1 pro (Replicate or BFL) | $0.04 per image; Ultra $0.06 | BFL's developer terms: the user owns outputs and may use them commercially | replicate.com/pricing; bfl.ai/pricing; bfl.ai/legal/developer-terms-of-service |
  | FLUX.2 pro | from $0.03 for the first megapixel, $0.015 for each more | same | bfl.ai/pricing; replicate.com/blog/run-flux-2-on-replicate |
  | OpenAI gpt-image (current) | $30 per million output tokens; a worked example of $0.025 for one image | not read | developers.openai.com/api/docs/pricing |
  | Recraft vector (SVG) | $0.08 per image; Pro $0.30 | developer terms not read | recraft.ai/docs/api-reference/pricing.md |

  Recommended: keep schnell for item pictures; the hero from **Nano Banana 2.1** (the adapter exists, the key exists,
  plan v3 names Nano Banana for A8 and asks for exactly this evidence in S2.4), chosen by the owner's eye in a
  one-time comparison (VD question 3). No stock photos and no template kit (VD section 4).
- Build: everything in VD (photo-led hero, measures, pictures inside sections, art direction per trade, more
  compositions, motion), the two-tier routing with failover, the lab performance gate, the calibrated critic.
- Add-ons: none needed. Motion is CSS only (VD S6).

**Verification.** VD's per-slice acceptance and mutations; S10.8 to S10.11 below. Law 2: "sites at a high visual
level" is marked VERIFIED only by S10.11, eight real builds whose stored measures pass.

**Cost per build (estimate).** $0.25 to $0.45: the library route measured $0.108 (VD 1.3), plus six item pictures
($0.05 to $0.10, VD S3), a stronger hero ($0.03 to $0.13) and one critic call (about $0.014, VD 1.3). Under $2 and
under the LIGHT cap of $0.60. The legacy path measured $0.53 to $0.95.

### 3.2 Web app or system

**Current truth.**
- Verified: `web_app` is executable and goes to the legacy path (`omni_prod/site_content/__init__.py:168`,
  `not_content_only`); its checks are `behavior_acceptance`, `browser_probe` and `visual_qa`
  (`output_profile/__init__.py:88`). The costliest build recorded spent $1.76 in 57 model calls
  (`omni_prod/pricing.py:341`).
- Unverified: **no production app build was examined for this plan**; the output plan itself says "אפליקציית ווב: לא
  נבדק". G8 (runtime and load) is at warn (`omni_prod/runtime_load.py:16-18`). Hardened sign-in is behind
  `OMNI_SITE_AUTH_V2`, off by default (`omni_prod/feature_flags.py:3-7`). `providers/managed_web_saas.py` and
  `providers/qstash_scheduler.py` have no production run that I found.
- Absent: the separate apps pipeline (130), the installable app (135: no `pwa_install.json` control exists), any
  design system for apps: the model writes every screen's markup and style from nothing.

**The world-class bar.**

| Dimension | Criterion |
|---|---|
| States | every screen that shows data has an empty, a loading and an error state, each shown in a real browser (130's acceptance 1): coverage = 100% |
| Design system | every spacing value, font size and colour on the page comes from the contract's tokens: 0 values outside the scale; at most 6 font sizes; touch targets >= 44 px; a light and a dark variant (inbox/003, decision 4) |
| Behaviour | 100% of the contract's acceptance ids pass (`web_saas_acceptance`: auth, role, create, read, update, delete, integration, responsive, API smoke); data survives a restart of the preview |
| Runtime | G8 passes and blocks: every request answered, p95 within its limit, the server alive afterwards |
| Accessibility | keyboard reaches every control, focus is visible, 0 serious automated findings |
| Installable | manifest valid, service worker active, home screen opens offline (135) |
| Security | sign-in hardening on; the existing G6 and `web_security` checks |
| Critic | as for sites, on an apps benchmark, only after calibration |

**Build or buy.**
- Build: `omni_prod/app_kit`, the third kit of the same shape as the section library and the game kit. The model
  writes screen definitions (schema `148ai.app/1`: navigation shell, table, form, detail, dashboard cards, chart) and
  the handlers; the kit supplies the tested components, the three states and the tokens from `g_apple.contract`.
- Add-on (decided here so the implementer need not): the kit's components are a vendored, pinned open-source
  web-components library, **Shoelace 2.x (MIT)**, themed from our tokens through CSS custom properties, registered in
  the add-on registry of S9.6. Reasons: custom elements need no build step and no Node (the sandbox has neither);
  the page opens from a file; the library documents right-to-left support. **To confirm in the PR, because this
  session could not open the project's pages:** the LICENSE file at the pinned version says MIT, and three components
  (dialog, select, table navigation) pass our own RTL browser test. If either check fails, the fallback is fixed: the
  kit ships its own twelve components and no add-on. Charts: uPlot (MIT), same registry, same check.
- Rejected: React with a component library (needs Node and a bundler in the sandbox; a larger failure surface while
  26% of builds finish); Bootstrap-style CSS kits (no components with states, a generic look).
- Buy: nothing new. Pictures, when an app has them, use the site's image tiers.

**Verification.** `app_probe` (S11.2) plays every state in Chromium; the state screenshot matrix is stored as
evidence. Acceptance of the stage is four of plan v3's S7.1 scenarios built for real (store, CRM, permissions,
automation).

**Cost per build (estimate).** $0.80 to $1.80. Under $2 with a thin margin; above the LIGHT cap of $0.60, at or above
STANDARD's $1.60. The kit should lower it by cutting repair rounds, which is a hypothesis until measured.

### 3.3 Software or tool

**Current truth.** Absent as a type. The families `automation`, `api_integration`, `ai_agent` and `mobile_app` are
refused (`output_profile/__init__.py:108-119`). An internal tool with screens is a `web_app`.

**What this plan means by it.** Three things, in order: (1) a tool with screens = `web_app` on the app kit; (2) an
automation: a trigger (schedule or webhook), steps, and a run log; it is scenario 5 of plan v3's S7.1; (3) a
command-line tool: possible later, and "visual level" does not apply to it. Desktop and store apps stay refused: the
output plan's section 13 puts them out of scope, and they need signing toolchains that do not exist (D7).

**The bar for an automation.** A trigger fires and the step's effect is recorded; a retry does not repeat the effect
(idempotency key); a failed step is visible in the run log with a sentence and an action; credentials are never taken
in chat (the Integration Center returns names only, `CURRENT_TRUTH_V28_HE.md`); the exported project runs alone with
one documented command (iron law 20).

**Build or buy.** Build the step runner and the run-log screen (app kit). Reuse `providers/qstash_scheduler.py` for
the hosted schedule, with a plain cron line in the export so the product does not depend on us. No new provider.

**Verification.** `automation_probe` (S11.8). **Cost per build (estimate):** as an app, $0.80 to $1.80.

### 3.4 Game, 2D and 3D

**Current truth.**
- Verified: the kit, stage 1 of warehouse 134 (#516 `e388915`): `omni_prod/game_kit` (a 496-line runtime, a schema
  for four kinds, an assembler, a probe that plays the page in Chromium), `tests/test_game_kit.py`,
  `tests/negative_controls/game_kit.json`, run in `browser-python.yml`. The gate `GAME` for free-form canvas games
  exists at warn (`omni_prod/game_runtime.py:22,34`).
- Unverified: a game built from a customer's request; acceptance 7 of 134 (the platformer run, former item 65).
- Absent: the `game` profile and its builder (D6); any art. The runtime draws rectangles and circles in six palette
  colours (`runtime.js`: only `fillRect` and `arc`; `schema.py` `PALETTE_KEYS`) and plays one oscillator
  (`runtime.js:53-54`). That is a working prototype's look, not a product's. 3D: nothing (D7, S16).

**The world-class bar (2D, in the browser).**

| Dimension | Criterion |
|---|---|
| Plays | the existing `game_probe`: canvas not blank, input changes the state, the score rises, the game ends, the end screen shows, touch controls >= 44 px on a phone |
| Frame rate | under 4x CPU slow-down: >= 30 frames a second at phone size (today's `MIN_FPS`, `probe.py:27`) and >= 55 at desktop size |
| Response | a key or a touch changes the game state within 100 ms |
| Weight | the page <= 5 MB; first frame within 2 s |
| Art | every entity is a sprite, not a flat shape (>= 16 colours inside its box); >= 2 animation frames per moving entity within one second; >= 2 background layers that move at different speeds |
| Feedback | a visible burst within 200 ms of a scoring event; a sound node starts on jump, hit, score, win and lose |
| Critic | three screenshots (title, play, end) on a games benchmark, only after calibration |

**Build or buy.**
- Build: keep our runtime (the owner's rule in 134: "המודל לא כותב מנוע"). Add an art layer to it (runtime v2,
  schema `148ai.game/2`): sprite atlas, animation, parallax, particles, screen shake, a skinned interface. Stay on
  Canvas 2D: the four kinds need no shaders, and the probe runs Chromium with the GPU off (`probe.py`, `_launch`).
  Sound effects are synthesized in the runtime (no provider, no rights question).
- Buy: the pixels. One image holds the whole cast on a 4x4 grid over a flat key colour; our code cuts, keys, trims and
  packs it (Pillow, already pinned). One or two images for the background layers. Same image tiers as sites.
  Generated music waits for 137 and S14.
- Rejected: Phaser or PixiJS as an engine (a second runtime beside the tested one, law 9; WebGL in a headless test
  without a GPU makes the frame-rate check flaky); Godot or Unity export (toolchains that do not exist, D7).
- 3D (S16, not released): three.js (MIT) vendored, and meshes from a 3D provider:

  | Candidate | Price (estimate) | Rights as read | Source |
  |---|---|---|---|
  | Meshy API | 20 credits for the mesh plus 10 for texture on the latest model; the price of a credit was not read | paid plans: "you own the output"; free plan CC BY 4.0 | docs.meshy.ai/en/api/pricing |
  | Tripo API | $0.01 a credit, about 40 to 50 credits a model: $0.40 to $0.50 (third-party sources) | commercial use said to be included for API output (third-party) | tripo3d.ai/blog/announcement-tripo-openapi-platform-payment-system |
  | Hunyuan3D (open weights) | about $0.38 a model on Tencent Cloud (third-party) | **licence excludes the EU, the UK and South Korea**: rejected | huggingface.co/tencent/Hunyuan3D-2/blob/main/LICENSE |

**Verification.** The extended probe (S12.6) and its mutations; the acceptance is one real build of each kind plus the
platformer of 134.

**Cost per build (estimate).** 2D: $0.60 to $1.50 (the output plan's own estimate for the builder, two repair rounds,
two to four pictures at $0.03 to $0.07, two critic calls). Under $2; above the LIGHT cap. 3D: $1.50 to $3.50 with
five to ten meshes: at or over $2.

### 3.5 Song or music

**Current truth.**
- Absent as a product: `media` is refused (`output_profile/__init__.py:105-107`: "no media fidelity gate (G7), no
  audio/video rights check").
- Contracts only, unverified: the asset kinds (`omni_prod/media_pipeline.py:8-9`), the capability keys
  (`omni_prod/capability_registry.py:55-61`), `OPTIONAL_MEDIA_KEYS` reported NOT_CONFIGURED
  (`providers/image_provider.py:59, 577`), matrix rows `lyria-3-5` (music, UNVERIFIED, NOT_ROUTED, commercial status
  CONDITIONAL) and `gemini-3-8-flash-lite-tts`. `HTTPMediaCapabilityProvider` refuses any paid provider
  (`providers/http_media_provider.py:43-47`).
- The rights gate blocks all audio today, on purpose: "The platform supplies no audio or video yet"
  (`omni_prod/skill_units/rights_media_source/manifest.json`).
- **In the warehouse: item 137.**

**The world-class bar (gate G7, audio).** Deterministic, measured with ffmpeg on the delivered file.

| Measure | Criterion | Failure code |
|---|---|---|
| Loudness | integrated -14 LUFS, within 1 LU (ITU-R BS.1770 measurement) | `LOUDNESS_OUT` |
| True peak | <= -1.0 dBTP | `PEAK_OVER` |
| Clipping | no run of 3 or more samples at full scale | `CLIPPED` |
| Bandwidth | 95% of the energy reaches at least 12 kHz, and there is content above 15 kHz (catches an up-sampled or low-bitrate file) | `COVERAGE_LOW` |
| Format | stereo, >= 44.1 kHz; a WAV master and an MP3 at 320 kbps | `FORMAT_OUT` |
| Length | within 5% of the approved length | `DURATION_OUT` |
| Silence | starts within 0.5 s; no digital silence longer than 2 s inside; ends on a tail, not a cut | `SILENCE` |
| Words (a song with lyrics) | the transcript of the vocal matches the approved lyrics: word error rate <= 25% (first estimate; Hebrew must be tested before this number means anything) | `LYRICS_LOST` |
| Rights | a rights record exists for the file's sha256 with commercial use allowed (S13.3); the prompt names no artist | `RIGHTS_UNKNOWN` |

The -14 LUFS and -1 dBTP targets are Spotify's published recommendation (support.spotify.com, "Loudness
normalization"); Apple's commonly cited target is -16 (secondary sources).

**Build or buy.**

| Candidate | Price (estimate) | Rights as read | Verdict |
|---|---|---|---|
| Google Lyria 3.5 (Gemini API) | $0.08 a full song; Lyria 3 Clip $0.04 for 30 s (third-party readings of Google's page; the model page exists) | Google won't claim ownership; the terms say the API is for "professional or business purposes, not for consumer use"; developers' questions on distributing Lyria output are unanswered on Google's forum; output carries SynthID. The matrix already says CONDITIONAL. | candidate for songs with vocals |
| ElevenLabs Eleven Music API | $0.15 a minute on pay-as-you-go, up to $0.33 on low tiers; 5-minute limit | "broad commercial use on all paid plans"; film, TV and large studio games need Enterprise. **ElevenAPI terms: no reselling, repackaging or redistributing API access to the Music Service unless an Authorized Reseller**, which is what a platform that sells songs does | candidate, only with reseller status (question 11) |
| Stability Stable Audio 2.5 / 3.0 API | 8 credits = $0.08 a generation, up to six minutes on 3.0; failed generations are not charged | commercial use permitted under the terms of service (Stability's own explainer; the terms themselves not read) | recommended for instrumental music: backgrounds, game loops, video scores |
| Suno, Udio | no official public API (third-party sources, mid-2026) | n/a | rejected: an unofficial wrapper breaks their terms |
| MiniMax music, Venice-hosted music | price and terms not found | Venice: see section 1 | not now |
| Speech (for voice-over, not singing) | ElevenLabs $0.08 per 1,000 characters on its main models (a newer page shows $0.022); Google Gemini 3.8 Flash TTS $9 per million audio tokens at 25 tokens a second, about $0.0002 a second, doubling on 2027-01-01 | as above per vendor | Google first (the key exists), ElevenLabs as the quality option |

Sources: ai.google.dev/gemini-api/docs/models/lyria-3.5; ai.google.dev/gemini-api/terms;
discuss.ai.google.dev (thread 197753); elevenlabs.io/pricing/api; elevenlabs.io/elevenapi-terms;
elevenlabs.io/eleven-music-api; docs.stability.ai/pricing;
stability.ai/explainers/can-ai-generated-music-be-used-commercially.

- Build: the lyric writer and its checks; the customer's approval of the lyrics inside the one summary (iron laws 3
  and 12: the lyrics are part of the fingerprint); two takes at most; mastering to the loudness target with ffmpeg,
  declared in the delivery notes (no hidden transformation, output plan principle 1); G7; the choice of the better
  take by its gate numbers; cover art from the image provider; a release page from the section library (cover, player,
  lyrics), so that a song is also a visual product; the rights file.

**Verification.** G7's probes run on synthetic fixtures made by ffmpeg, so they are built and mutated at no provider
cost (S13.5). The type is VERIFIED only by S14.5: six songs built in production, the owner's ear recorded beside the
numbers.

**Cost per build (estimate).** Lyria path: $0.25 to $0.45 (lyrics $0.03 to $0.06, two takes $0.16, transcript and
checks $0.02 to $0.05, cover $0.03 to $0.07). ElevenLabs path, three minutes, two takes: $1.00 to $2.10 depending on
the plan tier. Instrumental minute on Stable Audio: $0.10 to $0.20. All under $2 except ElevenLabs on its low tiers.

### 3.6 Video or clip

**Current truth.**
- Absent as a product; refused with songs (`output_profile/__init__.py:105`).
- Contracts only, unverified: `media.video.*` and `media.film.*` keys (`capability_registry.py:63-70`); the matrix row
  `gemini-omni-1-1-flash`; a watermark path that needs ffmpeg (D8).
- **In the warehouse: item 137.** The owner asked on 2026-11-25 what Venice offers for video (inbox/002, 22:20).

**The world-class bar (gate G7, video).** Deterministic, with ffprobe and ffmpeg filters.

| Measure | Criterion | Failure code |
|---|---|---|
| Container | MP4, H.264 High with AAC, `faststart`; constant frame rate of 24 or 30 | `FORMAT_OUT` |
| Resolution | >= 1080 on the short side for the standard tier (>= 720 for the economy tier), in the approved aspect (16:9, 9:16 or 1:1) | `RESOLUTION_LOW` |
| Length | within 0.25 s of the shot plan | `DURATION_OUT` |
| Sound | the audio bar of 3.5 (-14 LUFS, -1 dBTP) | `LOUDNESS_OUT` |
| Sync | audio and video start within 40 ms of each other and end within 100 ms | `SYNC_DRIFT` |
| Dead picture | no black longer than 0.5 s and no frozen picture longer than 1 s that the shot plan does not declare | `BLACK`, `FROZEN` |
| Cuts | the number of detected cuts equals the plan's, give or take one | `CUTS_OUT` |
| Text | every caption and title lies inside the 90% title-safe area (we render them, so this is exact); captions exist when there is speech | `TEXT_UNSAFE`, `CAPTIONS_MISSING` |
| Coherence | per shot, a vision check on sampled frames against the shot's description (advisory until calibrated) | advisory |
| Rights and disclosure | a rights record per generated shot, voice and music; the provider's watermark metadata kept; the file marked as AI-generated | `RIGHTS_UNKNOWN` |

The disclosure line is not optional for European customers: the Commission states that the transparency obligations
of Article 50(2) and (4) of the AI Act apply from 2 August 2026, and its code of practice on marking and labelling was
published on 10 June 2026 (digital-strategy.ec.europa.eu, FAQ "Transparency obligations under Article 50").

**Build or buy.**

| Candidate | Price per second of output (estimate) | Rights as read | Source |
|---|---|---|---|
| Google Veo 3.1 Lite, with audio | $0.05 (720p), $0.08 (1080p) | as Gemini API above | ai.google.dev/gemini-api/docs/pricing; blog.google (Veo 3.1 Lite) |
| Google Veo 3.1 Fast, with audio | $0.10 (720p), $0.12 (1080p), $0.30 (4K) | same | same |
| Google Veo 3.1 Standard, with audio | $0.40 (720p and 1080p), $0.60 (4K) (a third-party listing citing Google's page of 2026-10-18) | same | developersdigest.tech |
| Google Gemini Omni Flash | $0.10 | same | blog.google (Gemini Omni Flash) |
| Runway API | Gen-4 Turbo $0.05; Gen-4.5 $0.12 (a credit is $0.01) | commercial terms not retrieved | docs.dev.runwayml.com/guides/pricing |
| MiniMax direct | Hailuo 2.3: $0.28 for 6 s at 768p, $0.49 for 6 s at 1080p; H3: $0.08 at 768p | terms not retrieved | platform.minimax.io/docs/guides/pricing-paygo |
| Kling 4.0 on Replicate | $0.157 (720p), $0.235 (1080p) | Replicate says every video model it lists is available for commercial use; its terms pass output rights to the customer subject to the model's own terms | replicate.com/kwaivgi/kling-v4.0; replicate.com/terms |
| MiniMax H3 on Replicate | $0.08 (768p), $0.13 (2K) | same | replicate.com/minimax/h3 |
| Seedance 2.0 | $0.07 (480p) to about $0.15 (720p); sources conflict | not read | byteplus.com |
| Venice-hosted video | Kling V3 Pro $0.12 to $0.18; others per clip | Venice's own terms: section 1; each model's licence applies too | docs.venice.ai/pricing; venice.ai/legal/tos |
| OpenAI Sora | closed (WAREHOUSE 137; not re-verified: the search returned nothing) | n/a | n/a |

Recommended: **Google Veo 3.1 (Lite and Fast) as the first provider**, because the key, the billing and the commercial
status are already recorded in the matrix and it is the cheapest 1080p with sound; **a Replicate-hosted model as the
second**, because the prediction-job adapter with its submission journal exists
(`providers/image_provider.py:8-31`). Venice is not recommended for media until its terms are confirmed in writing.

- Build: the clip composer. A clip is not one generation: script, then a shot plan (schema `148ai.clip/1`), a still
  per shot from the image provider under one style clause, image-to-video per shot, or motion on the customer's own
  photos; titles and end cards rendered by our code from the site's tokens and font pairs; voice; music from S14;
  assembly, captions (libass, which shapes Hebrew and Arabic), loudness and aspect variants with ffmpeg; G7; one
  repair round that regenerates only the failed shot.
- Rejected: Remotion (its licence is not a permissive open-source one for a company; a Node render farm); Cloudflare
  Stream (its price was not retrieved, and a clip of a minute needs no adaptive streaming).

**Verification.** G7 video on synthetic fixtures first (S13.5). VERIFIED only by S15.5: three clips built in
production.

**Cost per build (estimate), with 1.3 takes per shot, stills, voice, music, planning and review:**

| Clip | Estimate | Against $2 |
|---|---|---|
| 15 s, 720p, Veo 3.1 Lite | $1.30 to $1.90 | under, barely |
| 15 s, 720p, Veo 3.1 Fast | $2.30 to $2.80 | over |
| 30 s, 1080p, Veo 3.1 Lite | $3.70 to $4.30 | **over** |
| 30 s, 1080p, Veo 3.1 Fast | $5.00 to $5.50 | **over** |
| 30 s, 1080p, a premium model (Veo Standard, Kling) | $9 to $16 | far over |
| a 5 s silent loop for a site's hero, 720p Lite | $0.35 to $0.50 | under |

The owner's own ceiling for a clip in the output plan is $4.50 with one repair round. A 30-second clip does not fit
under $2 with any provider read here. The cap stays; question 9 offers the tiers.

---

## 4. Cost per build, in one table (all estimates unless marked)

| Type | Estimate | $2 line | Plan class caps (D2) | Basis |
|---|---|---|---|---|
| Site, library route with pictures | $0.25 to $0.45 | under | under LIGHT $0.60 | $0.108 measured (VD 1.3) plus the additions of 3.1 |
| Site, legacy path | $0.53 to $0.95, **measured** | under | at or above LIGHT | VD 1.2 |
| App, system, automation | $0.80 to $1.80 | under, thin | above LIGHT; near STANDARD $1.60 | the costliest build recorded: $1.76 (`pricing.py:341`) |
| Game 2D | $0.60 to $1.50 | under | above LIGHT | output plan section 8 |
| Song, Lyria path | $0.25 to $0.45 | under | under LIGHT | 3.5 |
| Song, ElevenLabs path | $1.00 to $2.10 | at the line | above LIGHT | 3.5 |
| Clip 15 s 720p economy | $1.30 to $1.90 | under, barely | above STANDARD | 3.6 |
| Clip 30 s 1080p | $3.70 to $5.50 | **over** | ADVANCED $3.00 to HEAVY $5.50 | 3.6 |
| Game 3D | $1.50 to $3.50 | at or over | above STANDARD | 3.4 |

Production's real average for comparison: 32 builds in 14 days cost $19.04 in models, about $0.60 a build, and failed
builds lost $9.11 (STATUS.md, 2026-11-26). The number that matters is plan v3's: the cost of a product delivered
right, failures included.

**One-time spend of the plan itself (estimate):** S9.4 calibration $1 to $2; S10.8 image comparison $1 to $1.50;
S10.11 eight site builds $2 to $3.50; S11.9 four app builds with retries $8 to $14; S12.2 and S12.8 five game builds
$3 to $7.50; S13.6 provider probes $2 to $4; S14.0 and S14.5 song comparison and six songs $5 to $12; S15.0 and S15.5
probes and three clips $7 to $15. **Total: about $30 to $60.** Monthly: error monitoring $0 to $29 (S9.3); storage at
$0.015 a GB-month with no egress charge on R2 (developers.cloudflare.com/r2/pricing), about $0.45 a month for a
thousand 30 MB clips.

---

## 5. The enterprise layer

Each line names the module that exists and is upgraded. Nothing here is a second system (AGENTS.md law 9).

| Concern | Today (evidence) | Decision | Slice |
|---|---|---|---|
| **Tenant isolation of generated assets** | Capability artifacts are keyed by project, not account: `projects/<project>/builds/<build>/capabilities/...` (`omni_prod/artifact_keys.py:15-18`). Build screenshots are keyed by build only (`omni_prod/worker_tasks.py:381`). Attachments are `attachments/<account>/<project>/`; repository zips are content-addressed and shared (STATUS.md, S4.5 entry). 210 routes are classified and probed with two accounts (`tests/tenant_isolation_routes.json`, `tests/test_tenant_isolation_pg.py`). | New media keys are `tenants/<account>/projects/<project>/media/<sha256>.<ext>`: private, never shared between accounts (no existence oracle). One route serves them after an ownership check. The route joins the registry and the two-account matrix. Existing objects are not moved: that is a storage migration, the owner's (STATUS.md says so already). | S13.2 |
| **Asset storage and CDN** | `S3ArtifactStore` on Cloudflare R2 (`omni_prod/storage.py:16-56`), scoped temporary credentials (`providers/r2_credentials.py`). A file travels inside the repository as a base64 envelope, images only, up to 3 MB (`omni_prod/repository_assets.py:37-40`; `attachments.MAX_BYTES`, `omni_prod/attachments.py:35`). | Large media travels **by reference**: a second envelope, `148ai-binary-ref:v1;mime=...;sha256=...;bytes=...;key=...`, decoded at the same single point, `repository_assets.file_bytes`, which streams the object and checks its sha256. The export zip still holds the real file (iron laws 20, 25). Delivery is a short-lived signed URL of our own bucket under our own domain, never a function proxying megabytes and never a provider's URL. Whether that satisfies iron law 22 ("from our server") is question 13. | S13.1, S13.2 |
| **Rights and licensing records** | Six known sources, all for fonts, images and embeds (`omni_prod/rights_sources.json`); the gate blocks every unknown source and all audio and video (`rights_media_source/manifest.json`); `provider_router` rejects a provider without commercial use by default (`omni_prod/provider_router.py:40, 105`); `ImageProviderConfig` carries `license` and `commercial_use` (`image_provider.py:102-103`); a customer's upload has no declaration of right ("an approval-flow change, the owner's decision", `rights_sources.json`; question 15). | One row per generated asset in a new table `asset_rights`: sha256, account, project, build, kind, provider, model, provider task id, terms URL, the date the terms were read, the clause relied on, commercial use, restrictions, prompt sha256, input assets, provenance marks. Written when the asset is collected. The gate passes a media file only with such a row; unknown blocks. Terms older than 90 days turn the freshness check red. The export's `docs/CREATIVE_RIGHTS.md` is generated from the rows and says plainly: what was generated, by which model, on what basis, and that material generated from prompts alone may not be protected by copyright (US Copyright Office, Part 2, 2025-01-29: "prompts alone do not provide sufficient human control"). | S13.3 |
| **Provider failover and the matrix** | A router with quality, price, latency, health and a Redis circuit breaker exists (`omni_prod/provider_router.py`, `omni_prod/redis_circuit_breaker.py`); the registry exists (`omni_prod/provider_registry.py`); image providers are not registered together (D11); the matrix is generated (`python -m omni_prod.intelligence.matrix --write`) and stale on images (D5). | Two providers per modality, both in the registry, chosen by the router. Failover happens only before a submission is recorded; after the INTENT row, never to another provider (`AmbiguousSubmission`, `image_provider.py:70-71`), so nothing is paid twice. For a clip, failover is at the level of the whole job, not the shot: two models in one clip do not look alike. Matrix rows for video, music, speech and 3D enter as UNVERIFIED and change only on a run id that resolves green. | S9.5, S10.8, S13.6 |
| **Observability and error monitoring** | Missing, confirmed: no error-reporting library is imported or pinned (`grep -rn sentry_sdk`; `requirements-production.txt`). `omni_prod/observability.py` is 32 lines: a request counter and a Prometheus text endpoint. What exists around it: the worker-down alert (`worker-alert.yml`), `critical-path-freshness.yml`, `structured_event.py`. | Wire the Sentry SDK (its protocol is also spoken by the self-hosted GlitchTip, so the destination can change with one variable) into the API and both workers. Every event passes through the one redaction layer (`omni_prod/secret_redaction.py`) and carries no request body: iron law 1. Unset destination reads NOT_CONFIGURED out loud, never OK. The destination is the owner's (question 2). Media adds stage timings (queue, provider, assembly, gate) through `structured_event` and targets in `omni_prod/slo.py`. | S9.3, S13.7 |
| **Job queue and SLAs for long renders** | RQ on Redis; queues `omni-builds` and `omni-previews`; a build stops itself at 1,020 s and the queue kills at 1,200 s (`omni_prod/queueing.py:3-6, 48-52`); the capability executor polls at most 60 times (`omni_prod/capability_executor.py:71, 304-317`); one host. Vercel functions only enqueue and report, which stays. | A media build is a build: same `build_jobs` row, same state machine, same checkpoints (S4.2). It runs on a new queue `omni-media` with its own ordered time budgets, in its own worker process, one at a time. Each generation is a capability requirement with its own idempotency key, so a killed worker resumes without paying again. Poll budgets become per capability. Targets (first estimates, p95): site 5 min, app 15, game 8, song 6, 30-second clip 20. **An SLA is a promise to customers and is not set here**: it needs measured data, and it is the owner's. | S13.4 |
| **Audit trail** | A hash-chained event type exists with no caller (D9); `provenance.py`, `attestation.py` and the build events table exist. | Persist the chain: one append-only table `audit_events`, written for generation submitted and collected, gate result, rights recorded, asset delivered, published, deleted. `evidence_export` verifies the chain. | S13.8 |
| **Staged rollout behind flags** | One flag in `feature_flags.py`; gate modes per gate (`OMNI_GATE_<gate>`); the critic's `founder`, `all`, `0`; `canary.py` and `canary_controller.py`. | One function, `output_rollout(type, account)`, in `feature_flags.py`, reading `OMNI_OUTPUT_<TYPE>` = `off`, `owner`, `allowlist`, `all`; any other value raises. The A0 router asks it: a type whose profile exists but whose rollout excludes the account gets today's "not yet" sentence. Sites and web apps stay `all`, byte for byte. Gates enter at warn and move to block per the existing rule. Who is on an allowlist is the owner's (question 7). | S9.2 |

---

## 6. The stages

Common to every slice, as in VD section 5: one PR per slice from current main (iron law 26); the whole suite before a
push; browser tests never in parallel; mutations in `tests/negative_controls/<name>.json`, run by
`scripts/run_negative_controls.py`, with `"envs": ["pg"]` where a database is needed; every new gate enters at warn;
every threshold is global data read from the platform (CLAUDE.md section 4); a migration ships with its rollback file.
Test and control file names below are the names the implementer creates, except where marked "exists".

### S9. Shared foundations (in parallel with S10; no provider spend except S9.4)

**Depends on:** nothing. **Warehouse:** none. Nothing in S10.1 to S10.3 waits for S9.

| Slice | What | Where | Acceptance (test or workflow id) | Mutations |
|---|---|---|---|---|
| **S9.1** stage file | A machine-readable file of stages S1 to S16: id, acceptance ids, dependencies, warehouse items; status derived from runs, never typed. It is the "Missing" of AGENTS.md law 10. | new `omni_prod/plan_stages.py` with `--write` producing `PLAN_STAGES.json`; `scripts/check_pr_report.py` (exists) compares a PR's stage with the open stages, read from main | `tests/test_plan_stages.py`; the `PR report` check (`pr-report.yml`, exists) | a stage with an unmet dependency reads open; an acceptance id that names no existing test passes; the file is edited by hand and the generator check passes |
| **S9.2** rollout per type | section 5, last row | `omni_prod/feature_flags.py`; `omni_prod/output_profile/__init__.py` (`route`) | `tests/test_output_rollout.py`; `tests/test_output_profile_router.py` (exists) unchanged; the flag-off identity digest of `pipeline_identity` unchanged | an unknown value reads as `all`; `owner` admits another account; rollout `off` still returns the profile; the default for `website` changes |
| **S9.3** error monitoring | section 5 | `omni_prod/observability.py`; the worker entry points; `requirements-production.txt` | `tests/test_error_reporting.py`, on the real SDK client with a recording transport (seam rule); a new path "error-monitoring" in `critical-path-freshness.yml` | a secret reaches the transport; a worker exception is swallowed without a report; an unset destination reads OK; a request body is attached |
| **S9.4** benchmark and critic calibration | A frozen set of our own renders per type (sites first: VD's eight picture-less pages as known-bad, the S10 pages as known-good), and the owner's choice on 20 pairs ("which is better"). The existing critic's instruction becomes a fixed rubric of ten criteria scored 0 to 2; the reviewing model must not be the building model (`independent_of` already exists in the matrix's task classes). A script scores the set and reports agreement with the owner. **The score may gate only if agreement is >= 0.80 and every known-bad page scores below every known-good page.** Otherwise it stays advisory, and that is a valid end. | `omni_prod/design_review.py`; `tests/fixtures/visual_benchmark/`; new `scripts/calibrate_design_rubric.py`; result in `docs/evidence/` | `tests/test_design_review.py` (exists) plus `tests/test_design_rubric.py`; the calibration run's stored result | the reviewer equals the builder and passes; a known-bad page above a known-good one still enables the gate; agreement computed on fewer than 20 pairs passes |
| **S9.5** matrix truth | Rows for video, music, speech and 3D enter as UNVERIFIED; the image rows are re-derived from usage (D5); every evidence run id is resolved | `omni_prod/intelligence/inventory.py`, `matrix.py`; `scripts/resolve_evidence_runs.py` (exists) | `tests/test_intelligence_plane.py` (exists); `evidence-runs.yml` (exists) | a media row marked AVAILABLE with no evidence passes; a red run id counts as evidence |
| **S9.6** add-on registry | One file, `omni_prod/addons.json`: name, version, sha256 of every vendored file, SPDX licence, source, date read, which profiles use it. Allowed: MIT, Apache-2.0, BSD, ISC, CC0. Vendored files are platform files: the model does not see or edit them and they are restored after every repair, as image files are (118). The export carries `THIRD_PARTY_LICENSES.md`, generated. | `omni_prod/dependency_policy.py`; the transform that already restores platform assets | `tests/test_addons_registry.py`; `tests/test_dependency_policy.py` (exists) | a file whose sha256 differs passes; a GPL entry passes; an add-on loaded from another host passes; a model's edit to a vendored file survives |

**Stage acceptance:** all six slices merged; `PLAN_STAGES.json` shows S9 closed from its own runs.
**From the owner:** questions 1, 2, 4 (the 20 pairs), and about $1 to $2 for S9.4.

### S10. Sites at a world-class level (the output plan's P1; the owner's first priority)

**Depends on:** VD's questions 1 to 5. **Warehouse:** 118 (verify), 122 and 123 (order, VD question 1), 125 (S10.5),
126, 127, 129 (respected). VD's slices are adopted with their own acceptance and mutations; they are not rewritten
here.

| Slice | What | Source |
|---|---|---|
| **S10.1** | repair the hero overlay and the gate's definition of a visual; one verification build | VD S0 |
| **S10.2** | a photo-led first screen | VD S1 |
| **S10.3** | visual measures in the browser run that exists | VD S2 |
| **S10.4** | pictures inside the designed sections; builds with pictures stay on the library route | VD S3 |
| **S10.5** | one art direction per trade (warehouse 125, with the dark and light variants of inbox/003) | VD S4 |
| **S10.6** | more compositions (with or after 123) | VD S5 |
| **S10.7** | motion and texture, CSS only | VD S6 |

Added by this plan:

| Slice | What | Where | Acceptance | Mutations |
|---|---|---|---|---|
| **S10.8** two image tiers and failover | The hero asks for the strong tier, item pictures for the cheap one. Both adapters are registered and the router chooses (D11). A one-time comparison of ten subjects on three models, chosen by the owner's eye (VD question 3). This also gives plan v3's S2.4 its A8 evidence: one Nano Banana picture installed in a customer's site. | `omni_prod/capability_planner.py` (the constraint per place); `omni_prod/providers/image_provider.py:582-606`; `omni_prod/provider_router.py` | `tests/test_image_tier_routing.py`, with the real provider classes and a recording `urlopen` (seam rule); `provider-probe.yml` (exists) for the live proof | the hero goes to the cheap tier; a failover submits again after an INTENT row; a provider without commercial use is chosen; the breaker never opens |
| **S10.9** performance in the same run | LCP, CLS, long-task time, bytes by type, under CPU slow-down and a mobile network profile, added to Visual QA's report; thresholds in one table read from the platform. It is G4's measurement in a browser, not a second gate. | `omni_prod/visual_qa.py` (`SCRIPT`, `AUDIT`); `section_library/directions.json` (`perf_thresholds`) | `tests/test_visual_qa_perf.py` on the real audit text; a stored table of the eight reference pages' numbers | the slow-down removed and the stored table still matches; a 3 MB hero passes; a missing threshold key falls back to a default |
| **S10.10** the calibrated critic gates | Only if S9.4 passed: a build whose rubric score is under the calibrated minimum gets one repair round, and after it is said, not shipped as READY in silence (a 57 shipped: VD 2.1). Enters at warn. | `omni_prod/design_review.py:91-110` | `tests/test_design_review.py` | a score under the minimum ships READY with no finding; the reviewer equals the builder |
| **S10.11** the proof | Eight trades built for real on the library route. Evidence per build: every measure of S10.3 and S10.9 passes, the picture checks pass, the contact sheet is attached, the cost is recorded. And the share of content-site builds that reach the library route is reported weekly from `site_route.reason`, with a target of 80% over the last twenty. | `golden-rehearsal.yml` (exists, dispatch) or the owner's own builds; read-only SQL on `build_jobs.evidence_json` | the eight rows; `first-pass-yield.yml` (exists) for the share | n/a (evidence, not code) |

**Stage acceptance:** S10.1 to S10.4 and S10.8 to S10.11 closed (S10.5 to S10.7 follow their own warehouse order);
`PLAN_STAGES.json` derives it. **Cost per build:** section 4.
**From the owner:** VD's five questions; about $3 to $5 for the comparison and the eight builds.

### S11. Apps, systems and software (the output plan's P2; together with S12, after sites: OWNERS.md rule 10)

**Depends on:** S9.2, S9.6, S10.3 (the measures' machinery). **Warehouse:** 130, 135 (released); 131 (delivery);
**136 for the cost class of an app build** (reported: the Free and Amateur plans allow only LIGHT, $0.60).

| Slice | What | Where | Acceptance | Mutations |
|---|---|---|---|---|
| **S11.0** the baseline | Read-only: the last web app builds in production, their gates, costs and failure reasons, in a table. Until then "apps" is unverified (3.2). | read-only SQL; STATUS.md | the table, with the query and its fingerprint | n/a |
| **S11.1** the app kit and its route | `omni_prod/app_kit`: schema `148ai.app/1`, the vendored components (3.2), an assembler, tokens from the contract. A `decide()` for apps like the sites' one: a request that fits the schema goes to the kit, anything else to the legacy path with its reason recorded. An invalid definition is refused whole, nothing defaulted. | new `omni_prod/app_kit/` (`schema.py`, `assemble.py`, `probe.py`, as in `game_kit`); `omni_prod/app_states.py:842`; `omni_prod/output_profile/__init__.py` (a second builder id, `app_kit_v1`) | `tests/test_app_kit.py` in `browser-python.yml`; `tests/negative_controls/app_kit.json` | an unknown key is accepted; a data region without its three states is accepted; an app request enters the site engine (130's own mutation); the route falls to legacy with no reason |
| **S11.2** the three states, proven | `app_probe` forces empty, loading and error on every data region in Chromium and stores the screenshot matrix (130's acceptance 1). A server error reaches the customer as a sentence with an action (acceptance 2). | `omni_prod/app_kit/probe.py`; `omni_prod/customer_words.py` | `tests/test_app_probe.py` | 130's four: empty state missing, loading state missing, a stack trace reaches the customer, an app sent to the site engine |
| **S11.3** the installable app | warehouse 135 as written | per 135 | `tests/negative_controls/pwa_install.json` (named in 135) | 135's four |
| **S11.4** runtime, load and sign-in | G8 calibrated on three builds and moved to block; `site_auth_v2` turned on after the gates its own docstring names | `omni_prod/runtime_load.py`; `omni_prod/feature_flags.py` | `gate-freeze.yml` and `gate-regression.yml` (exist) | the existing G8 and auth controls |
| **S11.5** the design-system measures | Added to Visual QA for pages built by the kit: values outside the token scale, count of font sizes, touch targets, keyboard reach, state coverage, both colour variants | `omni_prod/visual_qa.py` | `tests/test_visual_qa_app.py` | a value outside the scale passes; a state missing from the matrix passes; the measures judge a content site |
| **S11.6** persistence | Data written through the app survives a restart of its preview: the CRM scenario | `omni_prod/web_saas_acceptance.py` (exists) | `tests/test_app_persistence.py`, on the real preview provider | a write kept only in memory passes |
| **S11.7** the automation profile | The family `automation` becomes executable with its own profile: trigger, steps, run log, idempotent retry, a cron line in the export | `omni_prod/intake/families.py:15`; `output_profile`; `omni_prod/providers/qstash_scheduler.py`; the app kit's run-log screen | `tests/test_automation_probe.py`; `tests/negative_controls/automation_profile.json` | a retry repeats the effect; a failed step shows as done; a credential asked in chat; the export needs our scheduler to run |
| **S11.8** the critic for apps | the benchmark of S9.4, type app | S9.4's files | S9.4's test | S9.4's |
| **S11.9** the proof | Four of plan v3's S7.1 scenarios built for real: store with a test payment, CRM, permissions, automation. Evidence: every gate, the state matrix, the cost per delivered app. | the rehearsal or the owner's builds | the four rows | n/a |

**Stage acceptance:** S11.1 to S11.6 and S11.9 closed; S11.7 may close after. **Cost per build:** section 4.
**From the owner:** question 3 (add-ons in principle); about $8 to $14.

### S12. 2D games (the output plan's P3; together with S11)

**Depends on:** S9.2, S10.8 (image tiers) for S12.4. **Warehouse:** 134 (released; S12.3 and S12.4 need it widened,
question 6); 65 (the paid acceptance build needs the owner's go); **137 for generated music**; 136 for the cost
class.

| Slice | What | Where | Acceptance | Mutations |
|---|---|---|---|---|
| **S12.1** the profile | 134 as written: the `game` profile with builder `canvas_game_v1`, `game` executable, the worker assembles and probes with the kit, the conversation asks a game's questions, a failed probe never shows as ready. Behind `OMNI_OUTPUT_GAME=owner`. | `omni_prod/output_profile/__init__.py:102`; `omni_prod/intake/families.py:15`; `omni_prod/worker_tasks.py`; `omni_prod/game_kit` | `tests/test_output_profile_router.py` (exists); `tests/negative_controls/game_profile.json` (named in 134); `tests/negative_controls/output_profile_router.json` NC2 (exists) stays | 134's six |
| **S12.2** the platformer | 134's acceptance 7: one Hebrew request, one production build, the result recorded with a screenshot | production, by the owner's instruction | the build row and its probe report | n/a |
| **S12.3** runtime v2, the art layer | Sprites, animation, parallax, particles, shake, a skinned interface; schema `148ai.game/2`; a version 1 definition still plays, with the version 1 look, said and not silent. The state window the probe reads does not change. | `omni_prod/game_kit/runtime.js`, `schema.py`, `assemble.py` | `tests/test_game_kit.py` (exists) plus `tests/test_game_kit_art.py` | a sprite missing from the atlas draws nothing and passes; a version 2 key in a version 1 file is accepted; the state window changes shape |
| **S12.4** the sprite pipeline | The cast sheet, the cutting, keying and packing, the checks (every cell filled, no key-colour fringe above 2%, cells distinct, one vision call naming the cast). Art that fails its checks is dropped and said; the game plays in the flat look. It never fails the build. | new `omni_prod/game_kit/art.py`; `omni_prod/image_prompt.py`; `omni_prod/repository_assets.py` (the atlas is a file under 3 MB) | `tests/test_game_art_pipeline.py`, with a real image file as fixture | an empty cell passes; a fringe passes; failed art fails the build; the atlas is embedded as base64 in the page |
| **S12.5** sound without a provider | Synthesized effects for jump, hit, score, win, lose; an optional synthesized loop | `runtime.js` | `tests/test_game_kit.py` | a scoring event starts no sound node and passes |
| **S12.6** the quality measures | 3.4's table added to `game_probe`, at warn | `omni_prod/game_kit/probe.py` | `tests/test_game_probe_quality.py` | the slow-down removed; a flat rectangle counts as a sprite; a 12 MB page passes; a late response passes |
| **S12.7** the critic for games | S9.4, type game | S9.4's | S9.4's | S9.4's |
| **S12.8** the proof | One real build of each of the four kinds, with art | production | four rows: probe report, frame-rate table, screenshots, cost | n/a |

**Stage acceptance:** S12.1, S12.2 close 134; S12.3 to S12.8 close "games at a high visual level".
**From the owner:** question 6; the go for the paid builds; about $3 to $7.50.

### S13. The enterprise layer for media (before any song or clip)

**Depends on:** S9.2, S9.3, S9.5; plan v3's S4.2 (checkpoints) and S4.5 (tenant isolation) merged.
**Warehouse:** **137** for S13.1 and S13.4 to S13.7 and S13.9; S13.2, S13.3 and S13.8 serve images too and need no
release. 118 and 131 are touched: reported.

| Slice | Needs 137 | What | Where | Acceptance | Mutations |
|---|---|---|---|---|---|
| **S13.1** carriage by reference | yes | section 5, storage | `omni_prod/repository_assets.py`; the five write points warehouse 118 lists | `tests/test_images_as_files.py` (exists) unchanged; `tests/test_assets_by_reference.py`; `tests/negative_controls/assets_by_reference.json` | a reference whose bytes differ from its sha256 is written; a reference outside `assets/` is decoded; the export zip holds the envelope text; the model sees the reference |
| **S13.2** tenant keys and delivery | no | section 5, isolation | `omni_prod/artifact_keys.py`; `omni_prod/investor_app.py` (one route); `tests/tenant_isolation_routes.json` | `tests/test_tenant_isolation_registry.py` and `tests/test_tenant_isolation_pg.py` (exist) with the new route; `intake-budget-pg.yml` | a key built without the account; another account's asset id answers anything but the unknown-id answer; a signed link lives longer than five minutes |
| **S13.3** the rights record | no | section 5, rights. Migration and rollback file. | new migration; `omni_prod/capability_executor.py` (at collect); `omni_prod/rights_sources.json`, `rights_sources.py`; `omni_prod/skill_units/rights_media_source`; `omni_prod/media_pipeline.py` (`repository_files`) | `tests/test_asset_rights_pg.py` (`pg`); `tests/test_skill_gate_rights.py` (exists); a path "provider terms" in `critical-path-freshness.yml` | an asset is delivered with no row; a row without commercial use passes; a restriction is ignored; terms a year old pass in silence; a prompt naming an artist reaches the provider |
| **S13.4** the media queue | yes | section 5, queue | `omni_prod/queueing.py`; `omni_prod/capability_executor.py:71`; the worker's compose file; `worker-alert.yml` | `tests/test_media_queue.py`; `tests/test_crash_resume_pg.py` (exists) with a media job killed between two generations; `postdeploy-checks.yml` stage `crash` | a resumed job submits a paid generation twice; the time budgets out of order load without error; the queue's kill ends a job with no final state; a media job takes the build queue's worker |
| **S13.5** ffmpeg and gate G7 | yes | ffmpeg and ffprobe in the worker image; ten probes as skill units (manifest, probe, an ok and a broken fixture, failure codes), fixtures synthesized by ffmpeg itself; G7 enters at warn, in media profiles only; a missing tool is NOT_RUN out loud | `Dockerfile` (the frozen step of `deploy-worker.yml` is not touched); new `omni_prod/skill_units/media_*`; `omni_prod/skill_units/gate.py:64` | `tests/test_g7_media_probes.py`; `tests/negative_controls/g7_media.json` | one per probe: the threshold removed; and: a probe error reads as pass; ffprobe missing reads as pass |
| **S13.6** provider adapters | yes, and questions 10, 11 | `PredictionImageProvider` becomes the media provider for every kind (same journal, same idempotency, same safe fetch; type sniffing for MP4, WebM, MP3, WAV, GLB; a size limit per kind; output stored by reference). A Google adapter for Veo, Lyria and speech beside `google_image.py`, on the same journal. Prices enter `provider_pricing` with source and date. One live probe per provider. | `omni_prod/providers/image_provider.py`, `google_image.py`; `omni_prod/provider_pricing.py`; `infra/provider_probe.py` | `tests/test_m5_media_provider_adapters.py` (exists) extended, real adapter against a recording HTTP server; `provider-probe.yml` for the live run id | the INTENT row is written after the paid call; a wrong file type is stored; an oversize file is stored; the kill switch (`model_policy.external_spend_enabled`) is ignored |
| **S13.7** timings and targets | yes | section 5, observability | `omni_prod/structured_event.py`, `metrics.py`, `slo.py` | `tests/test_media_timings.py`; plan v3's S5.2 report | a stage with no timing passes; queue time counted as provider time |
| **S13.8** the audit chain | no | section 5, audit. Migration and rollback file. | `omni_prod/audit.py`; new migration; `omni_prod/evidence_export.py` | `tests/test_audit_chain_pg.py` (`pg`) | an event dropped; a broken chain verifies; an event with no actor |
| **S13.9** marks on the file | yes | Provider metadata kept through every re-encode; our own tag (generated by AI, the asset's sha256, the model); a `provenance.json` beside the file. Cryptographic signing (C2PA) needs a certificate: the owner's, later. | the assembly step; `omni_prod/provenance.py` | `tests/test_media_marks.py` | a re-encode strips the metadata and passes |

**Stage acceptance:** every slice closed; a synthetic media job (fixtures, no provider) runs the whole path on the real
worker: queue, kill, resume, G7, rights row, audit chain, delivery to its owner and refusal to another account.
**From the owner:** questions 8, 10, 11, 12, 13, 16; about $2 to $4 for the probes.

### S14. Song and music (the output plan's P4)

**Depends on:** S13 closed. **Warehouse:** **137**; **136** for a price.

| Slice | What | Where | Acceptance | Mutations |
|---|---|---|---|---|
| **S14.0** the comparison | Six songs, three Hebrew and three English, on each candidate. The owner listens; G7's numbers and the word error rate are tabled beside his choice. | the probe of S13.6 | the table in `docs/evidence/` | n/a |
| **S14.1** the profiles | Families `song` and `clip` beside `media` (which stays refused for everything else: podcasts and the like). A song's brief: what it is for, language, style and mood in the customer's words, vocals or none, length, lyrics given or to be written. No field of a site. | `omni_prod/intake/families.py`; `omni_prod/output_profile/__init__.py:105`; `omni_prod/intake/artifact_fields.py` | `tests/test_output_profile_router.py`; `tests/negative_controls/song_profile.json` | a song profile pointing at the web builder; "אתר לאולפן מוזיקה" classified as a song (69's rule 8); a site field in a song's brief |
| **S14.2** the song composer | 3.5, "Build" | new `omni_prod/song_kit/` (lyrics, plan, mastering, choice of take, release page data) | `tests/test_song_kit.py`, the whole path on a recorded provider answer | lyrics changed after approval without a new fingerprint; a third take is paid; the louder take wins over the one that passes G7; mastering is applied and not declared |
| **S14.3** the gates | G7 audio, G2 on the lyrics' facts, the rights gate, the artist-name filter | S13.3, S13.5 | S13's tests on a song | S13's |
| **S14.4** the card | A player in the conversation card, with the build id; one approval | the shell files (Claude Code's since 2026-11-22) | a browser test in `browser-python.yml` | a song that failed G7 shows a play button |
| **S14.5** the proof | Three Hebrew and three English songs built in production by the owner. All pass G7; the words are understood in at least five; six rights rows; the cost is measured. `OMNI_OUTPUT_SONG=owner` until then. | production | six rows and the owner's verdict | n/a |

**Cost per build:** section 4. **From the owner:** questions 11, 12, 14; about $5 to $12.

### S15. Video and clip (the output plan's P5)

**Depends on:** S13 and S14 (music for the score). **Warehouse:** **137**; **136** for the tier.

| Slice | What | Where | Acceptance | Mutations |
|---|---|---|---|---|
| **S15.0** the probes | One five-second shot per candidate provider | S13.6 | run ids in the matrix | n/a |
| **S15.1** the profile | A clip's brief: purpose, audience, aspect, length tier, the messages (the customer's facts only), the customer's own logo and photos, voice or none, music or none, caption language | as S14.1 | `tests/negative_controls/clip_profile.json` | a clip longer than its tier is accepted; a fact not in the brief reaches a title |
| **S15.2** the clip composer | 3.6, "Build" | new `omni_prod/clip_kit/` (`schema.py`, `plan.py`, `assemble.py`, `cards.py`) | `tests/test_clip_kit.py`: the whole path with synthetic shots made by ffmpeg, no provider | a shot plan with an unknown key is accepted; a failed shot regenerates the whole clip; a second repair round runs; a title outside the safe area renders; Hebrew captions render left to right |
| **S15.3** the gates | G7 video, the rights gate, captions, disclosure | S13 | S13's tests on a clip | S13's |
| **S15.4** video in a site | A five-second silent loop in the hero's cover layout: poster first, no motion under `prefers-reduced-motion`, at most 2.5 MB, LCP still within its limit | `omni_prod/section_library`; S10.2, S10.9 | `tests/test_section_library.py`; `tests/test_visual_qa_perf.py` | the loop delays the first paint and passes; the loop plays under reduced motion |
| **S15.5** the proof | Three clips built in production: 15 seconds upright from the customer's photos; 30 seconds wide, generated; one hero loop | production | three rows, the G7 report of each, the cost against the tier | n/a |

**Cost per build:** section 4; a 30-second clip is over $2. **From the owner:** questions 9, 10, 12, 14; about $7 to $15.

### S16. 3D games (not released; a decision first)

**Depends on:** S12 closed with three accepted builds; S13.1 (GLB files travel by reference); S9.6 (three.js).
**Warehouse:** **a new item, which only the owner can open** (question 17). Outline only, so that the decision is
informed: a second kit with two or three fixed templates (a runner, an arena, a product viewer for sites); meshes from
a 3D provider, optimized on the worker; a gate on draw calls, triangles, texture memory and 30 frames a second at
phone size. Estimated cost per build $1.50 to $3.50. No slice is planned until the item exists.

---

## 7. Order and dependencies

```
now, in parallel:   S9 (foundations)        S10.1 -> S10.2 -> S10.3   (no spend, VD's first three)
then:               S10.4 -> S10.8 -> S10.9 -> S10.10 -> S10.11       (sites proven)
                    S10.5 (125), S10.6 (with 123), S10.7              (their own warehouse order)
after sites:        S11 (apps, systems, software)  ||  S12 (2D games) (together: OWNERS.md rule 10)
after 137 is out:   S13 (media layer) -> S14 (song) -> S15 (video)
on a new item:      S16 (3D)
```

- **Against plan v3's own stages.** Plan v3 forbids starting a stage before the previous one closes, except what is
  marked parallel. S9 to S12 raise the quality of exactly what S7.1 will judge (a business site, a store, a CRM,
  permissions, an automation), so they belong before S7's acceptance run, in parallel with S2 to S6. S13 to S15 belong
  after S7. That marking is the owner's (question 1).
- **S7.1's five scenarios** name no game, song or clip. When a type goes to `all`, its acceptance run should join
  them: a change to the owner's list, asked in question 1.
- **S8's delivery pack** needs nothing new: the matrix, the stage file and the rights records are sources it already
  derives from.

---

## 8. Not verified, said openly

- No provider page was opened (see the limits at the top). Prices, model names and licence wording are search
  readings of 2026-11-27. Several sources disagreed and are marked.
- No generated picture, song or video was seen or heard. Nothing here says any provider is good in Hebrew.
- No production app build was read (S11.0 does that first). The app and game cost estimates rest on the output plan's
  own estimates and one recorded maximum.
- Shoelace's licence and right-to-left behaviour were not read on its pages; the plan fixes the check and the
  fallback (3.2).
- Whether the routes behind `game_pipeline.py` and `mobile_pipeline.py` are refused in production (D7).
- The current limit on a Vercel function's response body. The design does not rely on it: no media passes through a
  function.
- The second host's price (question 16) is from memory, not checked.
- VD's own list of what it did not test stands (its section 6).
- The whole test suite was not run: nothing was changed.

---

## 9. שאלות לבעלים (החלטה אחת בכל שאלה)

**עכשיו**

1. **מספור וסדר מול תוכנית v3.** שלבים 7 ו-8 תפוסים, ולכן השלבים החדשים הם S9 עד S16. תוכנית v3 אוסרת להתחיל שלב לפני
   שהקודם נסגר.
   - (א) S9 עד S12 (יסודות, אתרים, אפליקציות, משחקים) רצים במקביל לשלבים 2 עד 6, ולפני בדיקת הקבלה של שלב 7. המדיה
     (S13 עד S15) אחרי שלב 7. כשסוג חדש נפתח לכולם, מוסיפים לו תרחיש לבדיקת הקבלה. **מומלץ.**
   - (ב) הכול מחכה לסגירת שלב 8.
   - (ג) הכול במקביל, גם המדיה.

2. **ניטור שגיאות (היום אין).**
   - (א) Sentry בענן, אזור אירופה. בערך 26 עד 29 דולר לחודש (הערכה). **מומלץ.**
   - (ב) GlitchTip בקוד פתוח על השרת שלנו. בלי תשלום, יותר תחזוקה, והשרת קטן.
   - (ג) בלי ניטור בינתיים.

3. **"תוספים" הם ספריות קוד פתוח שמוטמעות בתוך המוצר.** רישיון מתיר בלבד (MIT וכדומה), הרישיון
   נרשם ונמסר ללקוח, והמוצר לא טוען שום דבר משרת אחר.
   - (א) מאשר את העיקרון, ואת ערכת הרכיבים לאפליקציות כתוסף הראשון. **מומלץ.**
   - (ב) רק קוד שלנו, בלי ספריות חיצוניות.

4. **20 זוגות תמונות.** כדי לדעת אם המבקר האוטומטי רואה כמוך, אני צריך שתבחר "מה יותר יפה" ב-20
   זוגות של אתרים שבנינו. בערך עשר דקות.
   - (א) שולח לך את הזוגות. **מומלץ.**
   - (ב) בלי כיול: המבקר נשאר ייעוץ בלבד ולא חוסם.

5. **חמש השאלות של מסמך האתרים** (סדר העבודה, תמונות כברירת מחדל, מודל התמונות, הרחבת פריט 125, בנייה אחת לאימות)
   נשארות כמו שהן שם, והן חוסמות את S10.

**לפני אפליקציות ומשחקים**

6. **גרפיקה למשחקים.** פריט 134 אומר שהמודל כותב חוקים ושלבים והערכה מציירת. היום היא מציירת
   מלבנים ועיגולים. כדי שמשחק ייראה כמו מוצר צריך דמויות ורקעים שנוצרים במודל תמונות.
   - (א) מרחיבים את 134 לכלול גרפיקה שנוצרת. **מומלץ.**
   - (ב) 134 נשאר, והגרפיקה מקבלת מספר מחסן חדש.

7. **מי מקבל סוג חדש ראשון.** כל סוג נפתח בשלבים: כבוי, רק אתה, רשימת חשבונות, כולם.
   - (א) אחרי "רק אתה" עוברים ישר ל"כולם", אחרי שלוש בניות טובות. **מומלץ.**
   - (ב) שלב ביניים: אתה נותן רשימת חשבונות.

**לפני מדיה**

8. **פריט 137, שיר וסרטון.**
   - (א) נשאר במחסן. בונים רק יסודות, אתרים, אפליקציות ומשחקים.
   - (ב) משחררים עכשיו רק את התשתית (S13): תור, אחסון, בדיקות איכות ורישום זכויות. החיבור לספקים (S13.6) נשאר במחסן,
     ואין הוצאה. **מומלץ**, כי זו העבודה הארוכה, והיא לא עולה כסף.
   - (ג) משחררים הכול.

9. **סרטון מול תקרת 2 דולר.** (נוגע בפריט 136) סרטון של 30 שניות ב-1080p עולה 3.7 עד 5.5 דולר
   (הערכה). בתוכנית הפלטים שלך כתובה לקליפ תקרה של 4.50.
   - (א) שני מסלולים: "קצר" עד 15 שניות ב-720p בתוך 2 דולר, ו"מלא" עד 30 שניות ב-1080p עם תקרה של 5.50. **מומלץ.**
   - (ב) רק המסלול הקצר, עד שיהיו נתוני עלות אמיתיים.
   - (ג) מחכים עם המחיר, ובינתיים רק אתה בונה סרטונים, בספירה בלבד.

10. **ספק הווידאו.**
    - (א) Google Veo ראשי, ומודל דרך Replicate כגיבוי. **מומלץ**: המפתח והחיוב כבר קיימים.
    - (ב) רק דרך Replicate (MiniMax או Kling).
    - (ג) Venice. לא מומלץ: בתנאים שלו כתוב "שימוש אישי, לא מסחרי".

11. **ספק השירים.**
    - (א) בדיקת השוואה בעברית ובאנגלית, Google Lyria מול ElevenLabs, שישה שירים לכל אחד, 3 עד 5 דולר (הערכה), ואתה
      בוחר באוזן. **מומלץ.**
    - (ב) רק Lyria.
    - (ג) רק ElevenLabs. דורש מהם הסכם מפיץ: התנאים שלהם אוסרים למכור הלאה גישה לשירות המוזיקה.

    מוזיקת רקע בלי שירה (לאתר, למשחק, לסרטון): Stable Audio, 8 סנט ליצירה (הערכה).

12. **זכויות.** אף עורך דין לא קרא את תנאי הספקים, והתנאים במוזיקה לא חד-משמעיים.
    - (א) עורך דין קורא את התנאים של הספקים שנבחרו לפני שמוכרים שיר או סרטון ללקוח. **מומלץ.**
    - (ב) ממשיכים עם רישום זכויות וגילוי ללקוח בלבד.

13. **מאיפה הלקוח מוריד קובץ גדול.** חוק ברזל 22 אומר "מהשרת שלנו". סרטון של עשרות מגה לא עובר
    דרך השרת של האתר.
    - (א) מהאחסון שלנו, בכתובת שלנו, בקישור שתקף כמה דקות ורק לבעל הקובץ. **מומלץ.**
    - (ב) רק דרך השרת שלנו, גם אם זה מגביל את גודל הקובץ.

14. **שיר מלא ועריכת וידאו.** בתוכנית הפלטים שלך מ-15.11 הם מחוץ לתחום.
    - (א) שיר עד שלוש דקות וסרטון עד 30 שניות נכנסים. עריכה ידנית של הלקוח לא. **מומלץ.**
    - (ב) נשארים עם קטעים קצרים בלבד.

15. **הצהרת הלקוח על קבצים שהוא מעלה.** היום הלקוח לא מצהיר שהתמונה או הלוגו שלו. לסרטון מתמונות הלקוח זה נדרש,
    וזה שינוי בזרימת האישור.
    - (א) שורה אחת בסיכום שלפני האישור: "הקבצים שהעליתי שלי או שיש לי רשות להשתמש בהם". **מומלץ.**
    - (ב) בלי הצהרה.

**מאוחר יותר**

16. **שרת שני לעיבוד מדיה.** היום שרת אחד קטן מריץ הכול. אפשר להתחיל עליו, עבודה אחת בכל פעם.
    - (א) מתחילים על השרת הקיים, מודדים, ומחליטים לפי המדידה. **מומלץ.**
    - (ב) שרת שני מההתחלה. בערך 5 עד 10 דולר לחודש (הערכה מזיכרון, לא נבדקה).

17. **משחקי 3D.** אין להם פריט במחסן, ועלות בנייה מוערכת 1.5 עד 3.5 דולר.
    - (א) אחרי ששלושה משחקי 2D עברו קבלה. **מומלץ.**
    - (ב) עכשיו, במקביל ל-2D.
    - (ג) לא בתוכנית.

**תקציב חד-פעמי לכל הבדיקות והבניות של התוכנית:** בערך 30 עד 60 דולר (הערכה, סעיף 4).

---

## 10. Sources (all read through web search on 2026-11-27; none opened directly)

Images: https://ai.google.dev/gemini-api/docs/pricing · https://ai.google.dev/gemini-api/terms ·
https://replicate.com/pricing · https://replicate.com/blog/run-flux-2-on-replicate · https://replicate.com/terms ·
https://bfl.ai/pricing · https://bfl.ai/legal/developer-terms-of-service ·
https://huggingface.co/black-forest-labs/FLUX.1-schnell · https://developers.openai.com/api/docs/pricing ·
https://www.recraft.ai/docs/api-reference/pricing.md

Video: https://blog.google/innovation-and-ai/technology/ai/veo-3-1-lite/ ·
https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-omni-flash-nano-banana-2-lite/ ·
https://www.developersdigest.tech/models/video-generation/google-gemini-api (third party) ·
https://docs.dev.runwayml.com/guides/pricing/ · https://platform.minimax.io/docs/guides/pricing-paygo ·
https://replicate.com/kwaivgi/kling-v4.0 · https://replicate.com/minimax/h3 ·
https://replicate.com/docs/topics/models/official-models · https://www.byteplus.com/product/seedance ·
https://docs.venice.ai/pricing · https://venice.ai/legal/tos

Music and speech: https://ai.google.dev/gemini-api/docs/models/lyria-3.5 ·
https://discuss.ai.google.dev/t/clarification-required-commercial-saas-application-using-lyria-api-generated-music-distribution-rights/197753 ·
https://elevenlabs.io/pricing/api · https://elevenlabs.io/elevenapi-terms · https://elevenlabs.io/eleven-music-api ·
https://docs.stability.ai/pricing · https://stability.ai/explainers/can-ai-generated-music-be-used-commercially ·
https://sonilo.com/blog/guides/official-suno-api-saas-builders-2026 (third party, on Suno) ·
https://support.spotify.com/ca-en/artists/article/loudness-normalization/

3D: https://docs.meshy.ai/en/api/pricing ·
https://www.tripo3d.ai/blog/announcement-tripo-openapi-platform-payment-system ·
https://huggingface.co/tencent/Hunyuan3D-2/blob/main/LICENSE

Platform, law and standards: https://sentry.io/pricing/ · https://docs.sentry.io/pricing/ ·
https://developers.cloudflare.com/r2/pricing/ ·
https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act ·
https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content ·
https://www.copyright.gov/ai/Copyright-and-Artificial-Intelligence-Part-2-Copyrightability-Report.pdf ·
https://web.dev/articles/vitals · https://web.dev/articles/defining-core-web-vitals-thresholds
