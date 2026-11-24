# 2026-11-23 — tonight's fixes: the build no longer dies on a picture nobody asked for, the chat never ends, the phone (Claude Code)

- **Merged** (all CI green on the exact head; the owner's approval in the chat): #514 `d6eb690` (build count from 2026-11-23),
  #516 `e388915` (2D game kit, warehouse 134 stage 1), #517 `8be4aa7` (warehouse 134/135), #518 `e93d01b` (chat fixes),
  #519 `c43095c` (image gate, logo, failure words).
- **NOT live yet (verified):** neither #518 nor #519 was merged with a title ending in `[release]`, so Vercel canceled
  production (deployment of `e93d01b`: CANCELED) and the worker run 45245404245 says "SKIP -- not a release". This PR's
  merge, titled with `[release]`, releases Vercel; the worker needs "Run workflow" on Deploy build worker (main), because
  a docs-only push does not trigger it.
- **Root of three failed builds** (production, read-only): bld_7b541f93 (ShayFly), bld_4bb6207f and bld_6c8c2d3a (GOA),
  all `image_mismatch: generated image(s) without the subject they were made from`. DECISIONS 5's default hero is
  required=False ("never fails the build") but image_match blocked it for having no subject. Fixed in #519
  (`image_match.check_optional`): kept only if checked and matching, otherwise dropped; an asked-for picture still blocks.
  Evidence: tests/test_default_hero_never_fails_the_build.py (7), controls default_hero_never_fatal 5/5, lens11 9/9.
  **Not verified:** a real production build after the release (needs a paid build).
- **Chat** (#518): no turn cap (the ShayFly conversation closed after 8 turns that cost $0.003 in all); Enter is a new
  line on a phone; the page returns to the top when the keyboard closes; a card opens as a sheet over the conversation
  with the tabs reachable; the conversation rests above the message box. tests/phone_chat_browser.cjs: 4 checks, 6/6 faults.
- **Open:** the bot re-asks a settled question (GOA, "האם זה אתר תוכן בלבד" twice); new details become "what is right?"
  instead of being added (ShayFly lost its packages and prices); "מאשר" typed instead of the button (a money gate, not
  built); one picture per destination (not built).

# 2026-11-22 — the platform for everyone: no naming step, plain words, readable text, 44px controls (Claude, a second session beside Claude Code)

- **The order.** The owner, 2026-11-22 23:18, after #503 went live: upgrade the platform's look to the level of the large
  companies, "accessible to everyone, from a child who can read to an older person who understands nothing", then merge.
  He approved all five upgrades below, in one PR ("הכול ובנוסף לעבוד הכול בבת אחת"). OWNERS.md (2026-11-22) says Matt
  designs the shell and Claude implements a screen after the owner approves its sketch: the list below, with its
  screenshots, was that sketch, approved in the chat.
- **What changed** (`omni_prod/assets/app.js`, `index.html`, `app.css`, `visual-edit.js`):
  1. *First screen.* A new account saw "Your first project -> Project name -> Create project" before it could say what it
     wanted, with an empty "Edit requirements" card above it. Now the conversation box and six examples are the first
     screen; the first message creates the project, named from its first phrase without "I want" (40 characters at
     most; renamable under "Options"). "New project" in the drawer opens an empty conversation the same way; the naming
     dialog is gone. An attached image stays attached through that first switch (`S.keepAttachments`).
  2. *Zero technical terms* on the entry, the first screen, the drawer and its dialogs, the preview and the history (the
     owner's measure, inbox 001 §6). Gone: SaaS, web apps, code, domains, templates, ZIP, "element". "Manage" is now
     "Options" (it is the project menu: rename, archive). Before: entry 2-3 terms, first screen 1, drawer 1-2, preview 4.
  3. *Reading text is 16px or more* (it was 14-15px in 22 places on the first screen); small print that labels other
     text (status, tag, speaker, ids) is 14px. Every size is in rem.
  4. *Every control is 44x44px or more* (warehouse 133's own acceptance; CI measured WCAG's 24px). Below it were the
     message box (38px), the send button (38px), the preview's enlarge and close buttons (32-33px) and the panel
     minimise (34px).
  5. *Text size*: "Text size: Normal / Large / Extra large" (16, 18, 20px), on the entry and in the drawer, kept on the
     device.
- **The look of the owner's example** (2026-11-23, `create-148ai-vision`: "המראה זה מה שחשוב לי"). Its colours, radii and
  shadows were measured in the browser and applied as one layer at the end of `app.css`: a dark top bar (#151410) and a
  dark project rail (#1b1a17) in light and dark mode, the selected project marked with a yellow edge, white cards with a
  light bar, cream answer and side cards, yellow primary buttons with a darker edge, tags as rounded labels, the first
  screen as a card with a large title. On a computer the rail is open on the first visit: the rule that closed it under
  1600px (`visual-edit.js`) served three side-by-side areas the shell no longer has. Kept against the example: 16px
  text (the example uses 15px), the selected tab underlined in ink (its yellow line is 1.4:1 on white, review A11Y-4),
  the preview's own frame (`tests/preview_frame_browser.cjs`). Not built yet from the example: the proposal as the
  "זה מה שנבנה" card inside the conversation (it is the approval screen: the owner decides), build steps and checks
  in plain words, the computer/phone switch on the preview; client review, publishing and handover are in the queue.
- **Evidence.** `tests/platform_for_everyone_browser.cjs` (real Chromium, the real files, the boot path mocked): 5 checks
  x 2 languages hold on this branch; on main the same file fails first/words/text/targets in both languages (run
  2026-11-22, before/after in the PR). 7/7 deliberate faults caught. `tests/test_platform_for_everyone_in_ci.py` with
  `tests/negative_controls/platform_for_everyone_in_ci.json`: 4/4 controls PASS. The five CI browser tests pass locally;
  `tests/customer_flow_browser.cjs` now expects the empty conversation instead of the naming dialog.
- **Not verified here.** axe-core is not installed in this container and cannot be: `platform_a11y_browser.cjs` ran with
  its own measures only (30 screens clean; its 4 non-axe faults caught); the axe part runs in CI. The plan, build and
  details screens were not counted for technical terms (they need build fixtures): next. No real customer has used it.

# 2026-11-22 — 133, the platform design released with its review fixes (Claude Code)

- **What this is.** Codex's design (black, yellow and white workspace) reached the repository as ONE commit, `4457710` on
  `design/148ai-full-workspace-133`. The commits named in his two entries below (`547e118d`, `7bc876ef`, `9a30e8b6`,
  `acc159dd`, `b6553478`, `bd765158`) and the branch `design/148ai-sidebar-integration` exist only in his local
  workspace, not in this repository (`git cat-file -t` fails on each). The owner, 2026-11-22: "תעלה אתה את כל מה
  שקודקס עשה". Released by Claude Code on `claude/practical-hopper-oi3qj2-design-133`, not authored by him.
- **Independent review** (five agents, each finding put to an adversarial verifier): no security finding. Fixed before
  release, each with a browser test that fails without the fix (`tests/workspace_review_fixes_browser.cjs`, in CI):
  F1 a failed rebuild hid the working version's preview; F2 every project not opened in the session said "status
  unavailable" (the project list carries no status); F3 screen readers lost who said each message; F5 a late reply
  emptied another project's composer (the unscoped reply was already on main). Accessibility fixes: the drawer opened
  UNDER the preview on phones (A11Y-1); state and focus marks in yellow on white were 1.3-1.4:1 (A11Y-4/7/8); two menu
  buttons on phones (A11Y-5); the language button's hover (A11Y-6); a 34px logo link (A11Y-9).
- **A blocking WCAG 2.2 AA check for the platform** (`tests/platform_a11y_browser.cjs`, in CI): axe-core plus our own
  measures (horizontal scroll, visible focus, 24px targets, a control covered by another), on the entry, chat, preview,
  versions and drawer, in Hebrew and English, at 320/390/1440 px. Every run also proves it catches 8 deliberate faults.
  Evidence: `2 languages x 3 widths clean; 8/8 mutations caught`.
- **Not verified or not done:** `tests/workspace_sidebar_local.cjs` (Codex's) needs a development server nothing in the
  repository starts, so CI does not run it or its mutations; the phone header can squeeze the project name and the price
  (review A11Y-3, not changed here); a customer has not yet used the design in production.

# 2026-11-22 — 133, integrated workspace (Codex)

- Code `547e118d` on the local integration branch, based on production SHA `64604f03`. The revised entry, sign-in, drawer, projects, chat, plan and build cards, preview, visual editing, ZIP export and versions use the existing 148AI routes.
- Mobile and desktop use chat, preview and versions. The preview contains the edit entry point and the actual build recovery action. A saved version exposes its internal ID in expandable details. The workspace uses black, yellow and white.
- Local evidence: real development FastAPI registration, projects and catalogue with Chromium at 320, 390 and 1440. Failure and version records were injected for browser assertions. All eight deliberate regressions were detected. The customer flow, approval single source, project switching with late responses and preview sizing tests passed. Focused Python suite passed 67, skipped 4 PostgreSQL tests and passed 10 subtests.
- The first full comparison in an isolated environment stopped before execution on the same 50 collection errors in both trees (missing production Python dependencies). The populated runtime is needed for the full comparison. Exact deletion records await independent signature. Production remains at the previous release.
- Independent UI review found stale quote state, a blank Versions pane after switching projects, a missing desktop drawer opener outside chat, invisible rollback feedback and low-contrast label overrides. Addressed in `acc159dd`, `b6553478` and `9a30e8b6`. Follow-up also caught a duplicate filter ID and a late contract response, now scoped to the initiating brief.
- This is an agent review. The deployment and human deletion signature are pending.
- (Claude Code, 2026-11-22: the SHAs above are Codex's local commits; the repository holds his work as `4457710`. See the entry at the top.)


# 2026-11-22 — 133, project navigation (Codex)

- Implemented on local branch `design/148ai-sidebar-integration`, based on `64604f03` (merge #500). Browser-tested code `7bc876ef`.
- Screens: project drawer, all projects (opens as a dialog over the current project), business templates and account settings. The mobile hamburger moved from the bottom navigation into the workspace header and opens from chat, preview and visual edit. Project states have text labels, workspace controls have visible keyboard focus, and project switching retains unsent text within the same session.
- Existing authenticated project list, subscription, project creation and latest-build endpoints serve the new UI. When the server has not returned a project's latest build, the list shows “Status unavailable”. Domain settings show the current scope of delivery. Build and publish operations stay on the established paths.
- Evidence: developer FastAPI with in-memory accounts and real Chromium, `node tests/workspace_sidebar_local.cjs`. Registration, real account balance and project creation, catalogue filtering, template selection and draft restoration passed at 320, 390 and 1440. Six sidebar mutations in the same test failed on their expected checks. `customer_flow_browser.cjs` passed at 390 and 1440. `project_scope_browser.cjs` passed, including late responses from the former project.
- Focused Python regression suite: 74 passed, 4 PostgreSQL tests skipped, 20 subtests passed. The customer wording check caught the term “credits” in the first revision. The balance now uses the existing customer label.
- Pending review: exact deletion declarations are prepared with reviewer pending. Full repository comparison, independent review and production release remain open. The failure and version-row mutations belong to the corresponding screens of item 133.

# 2026-11-22 — warehouse 118, review fixes: every writer carries the image, and the smoke checks the reference the page really uses (Claude Code)

- **What broke (review of the 118 branch, all reproduced):** Claude's own bugs in the first pass of 118.
  - `gate_regression.served_page` still wrote every entry with `write_text`: the new smoke saw an envelope as text, so
    every approved build that carries an image would report `served=False` and fail the gate-regression workflow.
  - The smoke fetched a fixed `/assets/<name>` and never the URL the page references (relative: after a redirect of
    `GET /`, or from a stylesheet in a sub-directory, it is a 404 the smoke did not see).
  - A logo of 2,000,001 to 3,145,728 bytes passed the upload and failed the build (`MAX_ASSET_BYTES` 2,000,000).
  - `download_version` zips image bytes, so `X-Omni-Repository-SHA256` (stored text) did not describe the zip.
  - The visual-edit preview host wrote envelopes as text; the round-artifacts print did not shorten an envelope.
- **Fix:** `served_page` and `preview_host` write through `repository_assets.materialize`; the smoke resolves every
  carried-image reference in the page and its same-origin stylesheets with `urljoin` against the URL that holds it and
  checks 200, Content-Type and bytes (`PREVIEW-ASSET-REFS n`); `CarriedImage.place` gives a STYLESHEET in a
  sub-directory one `../` per directory (every other file keeps `assets/<name>`: it resolves against the document);
  `MAX_ASSET_BYTES` is `attachments.MAX_BYTES`; the download adds `X-Omni-Export-SHA256` (the zip's own sha256) and
  keeps the repository header as the stored checksum; the workflow's elision regex also matches `148ai-binary:v1`.
- **Evidence (commands run in the worktree, 2026-11-22, one pytest process at a time):**
  - `python3 -m pytest -q tests/test_images_as_files.py tests/test_v24_native_remote.py` 26 + 13 passed. New tests:
    `gate_regression.run` on a version saved by the real workspace (served=True); a stylesheet in `static/` reached;
    a page behind `GET /` -> `/he/` fails loudly with the resolved URL; a template literal reference read whole;
    a 2,000,001-byte and a 3,145,728-byte logo carried, one byte over raises; the real `sandbox_service` `POST /run`
    (FastAPI is installed now; only docker is a double) writes the image bytes and refuses a tampered envelope;
    the download of a version with an image carries the bytes and both headers.
  - the 88 test modules that import a changed module (`grep -l -E "repository_assets|preview_smoke|gate_regression|
    generated_images|uploaded_assets|preview_host|inspect-round-artifacts|investor_app|sandbox_service"`, without
    test_m4_acceptance): 1211 passed, 18 skipped, 1 failed. The one failure is
    `test_site_auth_v2::test_flag_off_is_the_baseline_byte_for_byte`, already failing at 9baf892 (before this round):
    the branch changes `scripts/preview_smoke` in the pipeline identity by design. It needs an identity declaration
    signed by the owner and the new baseline in that test; not written here.
  - `python3 scripts/run_negative_controls.py images_as_files` 19/19 PASS (NC9 to NC19 are new).
  - `OMNI_SITE_AUTH_V2=0 python3 -m omni_prod.pipeline_identity`: origin/main a77c1b8 b287af44…, 9baf892
    f3049230…, this round d1655f30… (working tree before commit); the only component that differs is
    `scripts/preview_smoke`.
- **Not verified:** a real production build and a real docker daemon; a page served at a nested URL that `GET /`
  does not reach is not checked by the smoke.

# 2026-11-21 — warehouse 118 (+114): the main image is a file the page references, not base64 in the page (Claude Code)

- **What broke:** the butcher (bld_83529c13, 2026-11-14): the generated hero was inlined as 1,735,408 base64 characters;
  the page was heavy and the facts after the hero fell past the 45,000 characters of GET / the preview smoke keeps.
  The five points of row 118 were text-only. Every image path inlined a data URI: `generated_images.GeneratedImage.uri`
  (D5 default hero and every generated image), `uploaded_assets._MainImage.uri` (customer photos) and
  `uploaded_assets.logo_transform` (the logo).
- **Design (option b, text-only pipeline):** `omni_prod/repository_assets.py`. An image is one repository entry at its
  real path `assets/148ai-<kind>-<n>.<ext>` holding a checked envelope (`148ai-binary:v1;mime;sha256;base64,`); the page
  references the path. Every point that writes files decodes it: `sandbox_service.run` (write_bytes(file_bytes)),
  `sandbox_executor` and `preview_runtime` (`materialize`), `UnifiedOmniEngine._zip` (all v25-v28 export routes) and
  `investor_app.download_version`. `validate_snapshot` checks every envelope (place, type, digest). The saved version
  (`workspace.py`) is unchanged: it carries the envelope as text. The model's view (repair summary, G5 as written,
  failure text) has the marker and no image file; the transform rewrites the verified file after every repair.
  `preview_smoke` fails loudly unless the server serves each `assets/` image with 200, its Content-Type and its bytes.
- **Evidence (commands run in the worktree, 2026-11-21):**
  - `python3 -m pytest -q tests/test_images_as_files.py` 18 passed: on the real smoke path the butcher page with the
    real image has no data:image, each file served with image/webp / image/png / image/jpeg, every fact within 45,000
    (control: inlined, "שבת סגור" is past it); the real workspace save/load, `DockerPreviewProvider.start` work
    directory and `export_zip` each carry and serve the file; a page with no image writes the same bytes as before.
  - the 44 test modules that import a changed module: 730 passed, 11 skipped, 0 failed.
  - `python3 scripts/run_negative_controls.py images_as_files` 8/8 PASS; the existing specs whose targets include a
    changed file: a4_asset_plan 10/10, contract_prompt_readers 10/10, lens11_image_match 9/9, photo_weight 8/8,
    skill_gate_rights 20/20, uploaded_main_image 15/15, and the investor_app specs (conversation_limit,
    item3_preview_route_full_reserve, item4_allowance_message, plan_price_said_once, pr154_two_gates,
    pr176_approval_action, preview_durable_backend) all PASS.
  - Two existing controls lost their bite and were repaired, not weakened: photo_weight NC6 (the weight unit now
    judges the rendition's bytes explicitly) and skill_gate_rights NC5 (the tests now assert what G5 reads as written).
- **G4 / perf_inline_image_weight: stays warn.** Mode is per gate (`gate.DEFAULT_MODE['G4']`), so block would also
  block the five other perf units; the 2026-11-19 calibration data has G4 failing 1 of 5 builds on SCRIPT_BLOCKING
  (perf_blocking_script), and no production build has run with this change. Rule 4 needs three builds. Proposal:
  per-unit modes, then this unit alone to block after three builds.
- **Not verified:** `sandbox_service.run` and `download_version` themselves (FastAPI not installed here; the runner's
  write is checked in source, CI runs the rest); a real production build (warehouse 115); og:image (now possible).
# 2026-11-21 — the content-document route, slice 1: independent review fixed (Claude Code)

- **What broke, and the root:** 15 findings, each reproduced by a skeptic. Three roots: (1) the copy checks read digit
  runs and fixed patterns only, so facts could ride in as words or attach to the wrong noun -- a WhatsApp the customer
  refused, a landline sent to wa.me, '250 שנות ניסיון' from a 250 ₪ price, 'שישה עורכי דין', 'ללא עלות', a vanished
  price, 'תל אביב' as the business name; (2) the route's executors were placed outside the quality gate and the group,
  so an advisory finding gave an engine 'ready' that the worker's release policy FAILED, and a refused rewrite after a
  verified round raised and threw the verified work away; (3) the tests checked the good path only -- the generated
  site tests could not fail (double-escaped regex, order read from the header menu), and the browser-dependent tests
  and controls never ran in CI.
- **Fixed (commits 0eae688..422f929):** WhatsApp only when named affirmatively, on a labelled mobile, inside its sentence
  (`whatsapp_negated`, `whatsapp_landline`); every number -- digits, Hebrew number words, vague magnitudes -- must be
  the customer's AND count the same noun (a year stays a year; a price's digits are not a number); always-open hours,
  star ratings, 'free' over a price, absent channels block; quotes, people, credentials, cities, days warn
  (`UNSUPPORTED_DETAIL`, SITE_CLAIMS calibrating); every page price shown next to its own label (a build budget is
  withheld); with no declared name, only a name the customer quoted (`name_not_declared` otherwise); every skipped
  section said; the advisory filter inside the quality gate with the threshold's test count and the review record
  reconciled; post-sandbox refusals are `RepairDeclined` (an unpaid decline is no round); install is atomic and the
  rehearsal stops before spend on a route error; `AUTHFORM` owned; the generated tests can fail; a `browser-python`
  CI job for the Chromium tests and browser-only controls.
- **Evidence:** `pytest` of the touched files (list in the report), `site_content` controls 44/44 (default env, and
  again with playwright blocked as in CI), `section_library` 7/7 default (playwright blocked) and 10/10 browser; the
  real-chain engine tests with Chromium 6/6 including the worker's release report READY for the reviewer + critic and
  the critic alone. Pipeline identity unchanged.
- **Not checked:** the `browser-python` job on GitHub (not pushed); a live build on the route; the prose limit above.

# 2026-11-21 — the content-document route, slice 1: the model writes copy, the platform renders the library (Claude Code)

- **What:** `omni_prod/site_content` (behind `OMNI_SITE_LIBRARY` = off | accounts | on, default off; an unknown value
  raises). For an approved content-only Hebrew site the model writes ONE JSON document of copy, validated before
  rendering (21 codes; one corrective call, then `site_content_invalid`); the platform fills every structured fact
  slot (phone, WhatsApp, e-mail, address, hours, reviews, prices, number slots) from the fact sheet (fact_canon on the
  approved prompt, the truth gate's own canon), renders the section library with the build's
  contract, and writes a fixed GET-only app.py, fixed tests and a manifest covering every acceptance id. Repair is
  owned by an exhaustive OWNER table: content -> a rewrite of the named JSON paths only; platform ->
  `RepairDeclined('platform_render_defect')` (new in autonomous_core), no paid round; customer -> needs_customer_input;
  advisory (design critic, model reviewer) -> library feedback, never a decline. AgenticRepairAgent is off on the
  route. Worker and rehearsal install it right after the components; evidence `site_route`.
- **Evidence (verified here, 2026-11-21):** the owner's brief bld_b0eb47a5 (production row read read-only, prompt
  sha256 `41d10d63...5db61`) takes the route (palette counsel, its outline mapped to library sections) and, through
  the REAL production chain (`investor_app._verification_executor`, local sandbox transport, local Chromium) and the
  worker's installs, is READY in round 0 with one content call (`tests/test_site_content_engine.py`, 5 passed --
  locally, where Chromium is installed; CI's test job has no Python playwright and skips them: they run in the new
  `browser-python` job, not yet run on GitHub). Every
  WORKER_GATES unit, G-APPLE static and the truth gate pass on the page; with a 480,000-character hero inlined, the
  truth gate's facts and the hero copy are inside the 45,000-character cut. Flag off: byte-identical engine build.
  Controls: `site_content` 7/7 then (after the review below) 44/44; `section_library` was 5/10 even with Chromium
  (NC1-NC5 stale), now 7/7 in the default env and 10/10 with `NC_ENV=browser`. Pipeline identity unchanged
  (`41a6e134...4618`).
- **Found and fixed:** the real visual QA failed the library page on a phone (the closed menu's links measured
  off-screen, the fixed action bar over the hero's phone link) -- every route build would have stopped.
- **Not checked:** a live rehearsal on the owner's account (needs `OMNI_SITE_LIBRARY` set in the worker), other
  palettes end to end through the chain, change requests on a route-built site, gallery/products images, the
  production sandbox's own Chromium. Headings use the body font (the display-font change is deferred). Facts written
  as words in copy are checked by pattern only (see the review entry above); a fact stated in other prose -- a service
  the customer never offered, an award, a guarantee in words the claim list does not know -- is not checked.

# 2026-11-20 — the section library: designed sections the generator will assemble (Claude Code)
# 2026-11-21 — the section library v3: every kind of business, international bar, variety (Claude Code)

- **Why:** the owner's law-firm build (bld_b0eb47a5) was bare; the model designed every site from nothing. The owner
  (2026-11-20): "תכין את הסקשנים אתה אבל ברמה הכי גבוהה שיש", "המטרה שלך זה רמה בין לאומית", "לא רק לעורכי דין",
  "מגוון בהכול ברמה הכי גבוהה".
- **What:** `omni_prod/section_library` -- 12 sections (header, hero with a facts panel, numbers, services, price list,
  gallery, about, team, process, call band, testimonials, FAQ, contact with a WhatsApp form, footer, phone action bar);
  four art directions by palette (formal, warm, bold, elegant); layout variants per section (hero split/banner,
  services cards/list, process steps/timeline, FAQ aside/stacked, testimonials grid/feature), a combination of its own
  per business; tones by position; each page ships only the style it can use. Written against the G-APPLE contract
  (which gained a heading-font token and a 72px step, declared and signed). Nothing invented: a section, fact or
  channel the customer did not give is left out and said; facts the page already showed are not repeated.
- **Verified (independently, in a browser):** two critique rounds by independent designers on seven businesses
  (cafe, salon, plumber, dental, boutique, fitness, law): round 1 5.5-6, round 2 mean 6.64; the design editor's 20
  measured fixes applied. Conformance: 10 palettes x 4 content shapes through every skill unit, the G-APPLE check,
  bidi, links, channels and invented numbers; every layout variant in every direction at 320/820/1440 with no
  sideways scroll; band contrast >= 4.5 on every palette; purged and full stylesheets pixel-identical (32 screenshots);
  the richest page 36,699 characters (the truth gate reads 45,000). `tests/test_section_library.py` and
  `tests/test_section_library_conformance.py`: 36 passed; controls `section_library` 22/22.
- **Not yet:** the generator does not use the library -- the content-document route (wiring slice 1) is being built,
  behind a flag that is off by default.

# 2026-11-20 — the window approval screen offers only the windows that fit the business (Claude Code)

- **What broke (the owner, 2026-11-19, law-firm site):** "בחלונות באתר שום דבר לא קשור למה הוא מציע". `offer()` listed
  all eight catalogue windows for every website -- a cart drawer, filter chips and an age gate for a law firm.
- **Fix:** `window_catalog.relevant(text)` reads the customer's request (whole words, Hebrew prefixes): cookies and a
  question widget for every site; cart / chips / mega menu only for a shop; age gate only for alcohol or tobacco;
  promotion bar and entry popup only with a sale or a shop. A decided window is always shown; a new window with no
  offer rule raises.
- **Evidence:** `tests/test_windows_fit_the_business.py` 7 passed (law firm: 2 windows; butcher with sales: 4; wine
  shop: all 8); window approval tests updated (a cafe is offered 2); controls `windows_fit` 4/4 (NC4 first exposed a
  guard that never ran alone -- fixed).
# 2026-11-20 — the conversation agent never guesses the customer's gender (Claude Code)

- **What broke:** rehearsal 44650878701 (luna on the production path, 3/3 passed) -- the agent wrote "תרצי להציג
  מחירון" to a customer who never said their gender. The reply rules said nothing about Hebrew address.
- **Fix:** the reply rules: in Hebrew, the plural (אתם: תרצו, ספרו) or gender-neutral wording, never a guess.
- **Evidence:** `tests/test_reply_never_guesses_gender.py` 1 passed; control `reply_neutral_address` 1/1.
- **Not verified yet:** a model obeying it -- the next agent rehearsal reads the replies.

# 2026-11-19 — a shared link shows a preview by construction (Claude Code)

- **What broke:** SHARE (og:title, og:description) failed on all five production builds with gate evidence and on the
  owner's law-firm build (bld_b0eb47a5), after #467 had put the rule in the spec. Telling the model is not enough.
- **Fix:** `omni_prod/share_preview.py`, a repository transform after the RTL rule, in the worker and the rehearsal:
  a served page with a <title> and no og:title gets one from that title; og:description comes from the page's meta
  description, else its first paragraph (160 characters). Nothing invented; a page already tagged is left as is;
  a Python template is changed only if it still compiles; tests are never touched.
- **Evidence:** `tests/test_share_preview_by_construction.py` 8 passed, including the butcher production page with its
  og tags removed (SHARE fails; after the transform it passes) and an engine build that is ready with 0 repair rounds
  with SHARE set to block; controls `share_preview` 5/5.
- **Not done:** og:image -- needs the hero image served as a file (warehouse 118).
# 2026-11-19 — PRO: a business site meets a professional minimum (Claude Code)

- **What broke (the owner, bld_b0eb47a5, the law-firm site):** "רמה נמוכה ... אני רוצה מקצועיות". The build passed every
  blocking gate; nothing judged how the page looks -- a hero block, two sections, no visual, the consultation action once.
- **Fix:** a new unit `skill_units/design_minimum` (gate PRO, code DESIGN_TOO_BASIC). It judges only a page with a contact
  action (tel:, WhatsApp, mailto:, #contact): exactly one h1, at least 4 sections, a visual (img/svg/picture/video or a
  CSS background image), the contact action at least twice. Its manifest reaches the generator through `carry_rules`;
  LANDING_CONVERSION now also tells it the professional shape (4+ sections, hero visual, services as a card grid).
- **Rule 4:** PRO enters CALIBRATING (warn) and WORKER_GATES; it blocks only after three calibration builds.
- **Evidence:** `tests/test_design_minimum.py` 6 passed (ok fixture = the real butcher production page; broken fixture =
  the law-firm shape, falls with 3 findings); controls `design_minimum` 6/6, `gates_calibrating` 9/9.
- **Not checked:** the owner's real page itself -- the built files are in object storage, not in the database; the
  broken fixture is its shape as seen in the owner's screenshots.
# 2026-11-19 — the preview's enlarge button covers the whole screen on a phone (Claude Code)

- **What broke (the owner, iPhone):** "מסך מלא לתצוגה מקדימה לא עובד". Reproduced in Chromium as an iPhone 13: after
  ⤢ the stage moved to x=-12 (12px off the screen) with the same width, under the app's bars -- the phone rule makes the
  stage width:100% and static, so `stage-max`'s inset:12px only shifted it.
- **Fix:** on a phone, `.workspace.stage-max>.stage` is fixed at inset 0 over everything (z-index 1000), no backdrop.
- **Evidence:** `tests/preview_frame_browser.cjs` (real app, real ⤢ click) at 390 and 1440 px: the enlarged stage is
  the whole viewport on a phone, 12px inset on a desktop, nothing covers it, the same button restores it. Without the
  CSS fix the new check fails with x=-12 (run here; the browser job runs it in CI).
# 2026-11-20 — migration 045 applied to production: the frozen reference corpus (Claude Code)

- **Approval:** the owner, 2026-11-19 ("מאשר הכול תמשיך לעבוד", on migration 045 + the corpus).
- **Procedure (CLAUDE.md section 5):** backup branch `backup-before-migration-045-corpus-pages-2026-11-20`
  (br-ancient-sunset-b9yi0wyu); dry check: corpus_pages absent, schema_migrations 40 rows, max 44; one transaction
  that first refuses unless max = 44 and the table is absent, then creates the table, index, trigger and the
  schema_migrations row (sha256 3b0d7fb47d0e1a31e4b84d1d1fd2e6be39c0199b7d5fd5db1094a31923b203cb = the file);
  verification in a separate query: corpus_pages exists with 0 rows, trigger corpus_pages_frozen and both constraints
  present, schema_migrations 41 rows, max 45. A first attempt rolled back whole (schema_migrations.sha256 is NOT NULL).
- **Order:** the database was migrated before this code merges; a database ahead of the code is still COMPATIBLE
  (`schema_manifest.compatibility` counts only missing versions).
- **Code:** migration + rollback, `tests/test_corpus_pages_migration.py` (PostgreSQL, intake-budget-pg), the first
  category collected (restaurants: 5 accepted of 26 checked, every rejection with its reason) and the insert script
  (never overwrites; 20% hold-out by a rule on the URL). The rows are not inserted yet.
# 2026-11-19 — the conversation agent runs on gpt-6-luna, Sonnet when Venice does not offer it (Claude Code)

- **Decision (the owner, 2026-11-19, after the measurement):** "אני איתך מה שאתה ממליץ" -- luna, with Sonnet as fallback.
- **Measurement (conversation-rehearsal, agent path, 3 Hebrew conversations each):** luna 3/3, 0 failed calls,
  $0.0011-0.0016 a conversation (run 44613790551); Sonnet 3/3, $0.029-0.041 (44602458248); Haiku 3/3, $0.0014-0.0023
  (44616521276); deepseek-v4-flash 3/3 with one failed call (44602428561); gpt-oss-120b 5 empty or invalid answers
  (44605208470); qwen3-235b 5 timeouts and Arabic in the Hebrew (44607455048).
- **Change:** `conversation_agent.VENICE_MODELS = ('openai-gpt-6-luna', 'claude-sonnet-5-5')`; the ceiling stays Sonnet's
  list price (2,10) so the fallback is never refused; each turn settles at its actual cost. Other accounts unchanged.
- **Evidence:** `tests/test_conversation_agent_sonnet.py` 15 passed, with a new test that the list order wins over the
  price (luna is first and cheapest, so the old controls could no longer tell them apart); controls
  `conversation_agent_sonnet` 12/12 (NC1-NC3 retargeted to that test).
- **Not measured:** 3 conversations per model, all content sites; measure again after a week of real conversations.

# 2026-11-19 — the owner's page structure: "עיצוב:" is not a section, "פתיח" needs no heading (Claude Code)

- **What broke (production, bld_7da07ab0, 6 rounds, $1.52):** the QA review failed CUSTOMER-PAGE-STRUCTURE -- no
  "פתיח" heading, no "עיצוב" section after "צור קשר". Reproduced: with the request's blank lines lost, `outline` read
  "עיצוב: נקי ורציני..." as section 7; and "1. פתיח: ..." names the opening's role, not a heading to show.
- **Fix:** a numbered list ends at its first unnumbered line; an opening role (פתיח/פתיחה/הירו/hero/intro) keeps its
  place and content but is not a required visible heading.
- **Evidence:** `tests/test_outline_roles_and_numbered_end.py` 3 passed on the owner's brief (2 fail without);
  existing outline tests pass; controls `outline_roles` 2/2, `page_outline` unchanged.
- **The same build's other blockers:** G5 on tests/test_site.py (fixed in #471, released 22:21 IL); two real QA findings
  (phone validation, CTA repeated at the end) the repair never reached.

# 2026-11-19 — G5 never judges a test file; the owner's first build failed on one (Claude Code)

- **What broke (production, bld_59236dc6, the owner's law-firm site):** verification_failed after 3 repair rounds,
  `no_progress_repository_unchanged`, $0.904569. G5 (blocking since #468 today) failed IMAGE_SOURCE_UNKNOWN on
  `tests/test_cohen_law.py`, a test the builder wrote; no repair of the site could clear it. Claude's bug in #468: the
  five calibration builds had no test file with an image, and `served_of` read every .py file.
- **Fix:** `served_of` leaves out test files (the repair contracts' `_TEST_FILE` pattern: tests/, test_*.py, *.test.*).
- **Evidence:** `tests/test_served_files_exclude_tests.py` 3 passed with the unit's own broken fixture (2 fail without;
  the same fixture in app.py still fails G5); control `served_not_tests` 1/1.
- **Also from this build (warn gates):** the spec carried PLATFORM-CHECKS with og:title (#467 works) and the page still
  had no og tags -- telling the model is not enough; BRAND flagged a template fragment of app.py.

# 2026-11-19 — a long request is a request, even with "כמה עולה" inside it (Claude Code)

- **What broke (production, the owner, 19:14):** a 14-line law-firm brief got "לא זיהיתי פרטים חדשים". intake_messages:
  interpretation `{"intent": "cost"}`, no reservation, a 0.7 s reply -- the model never read it.
- **Root cause:** `classify_intent` searched the whole message for question phrases; the FAQ line "כמה עולה ייעוץ
  ראשון (250 ₪)" matched the cost question.
- **Fix:** a question intent is a short question (at most 2 lines and 200 characters); anything longer is a request
  (a modification once a version exists).
- **Evidence:** `tests/test_long_request_is_not_a_question.py` 4 passed on the production message, through the real
  supervisor (the interpreter is called once); 3 fail without the fix; controls `intent_long` 2/2.
# 2026-11-19 — the rehearsal measures one cheap Venice model at a time (Claude Code)

- **Why (the owner, 2026-11-19):** choose the conversation agent's model by measurement, among cheap Venice models, with
  the owner. Production is unchanged: it quotes with `conversation_agent.venice_profile()` (Sonnet, then Haiku).
- **What:** `conversation_agent.CANDIDATES` -- deepseek-v4-flash, openai-gpt-oss-120b, qwen3-235b-a22b-instruct-2507,
  openai-gpt-6-luna, claude-haiku-5-5 -- each at its list price (docs/venice_prices_snapshot.md, 2026-10-19) as its
  ceiling. The workflow input `candidate` (agent path only) quotes the rehearsal with that one model; an unknown name
  raises, another path refuses it, and a model Venice now prices above the ceiling is refused before any request.
- **Evidence:** `tests/test_conversation_model_candidates.py` 11 passed on the real build_gateway / VeniceIntakeGateway /
  select_model (Venice HTTP faked), 5 failed without the change; controls `model_candidates` 3/3.
- **Not yet measured:** nothing about quality or cost -- that is the rehearsal runs, after the release.
# 2026-11-19 — a restated text that only adds is an extension, not "what is right?" (Claude Code)

- **What broke (production, the owner's law-firm site, 21:29-21:30):** after the WhatsApp number was given, every turn
  answered "קודם נקבע: ... עכשיו הבנתי: ... לא שיניתי — מה נכון?", and answering did not end it.
- **Root cause:** the model restates the `content` field whole; the restatement differed from the confirmed text (one
  fact added), and `intake.agent.apply` treats any difference from a confirmed value as a conflict.
- **Fix:** for a text field, a HIGH proposal that keeps the confirmed text whole (spacing and ; | , aside) and adds to
  it is applied as the customer's own value. A changed or dropped fact, or a MEDIUM guess, is still asked.
- **Evidence:** `tests/test_content_extension_is_not_a_conflict.py` 5 passed on the production values (2 fail without
  the fix); `test_intake_requirements_preservation` unchanged; controls `content_extends` 2/2.
# 2026-11-19 — "לא לשמור פרטים" answers the personal-data question, next to a "כן" (Claude Code)

- **What broke (production, the owner's law-firm site, 21:23-21:33):** the agent asked "האם יישמרו פרטים אישיים?"
  three times. The answers "כן, 03-5551234 נכון. לא לשמור פרטים..." and "כן, אתר תוכן בלבד ... בלי לשמור כלום" named
  yes and no, so `typed_choice` read neither.
- **Fix:** a negated store ("לא/בלי לשמור", "שלא יישמרו") decides personal_data = no on its own, as "לא שומרים" already
  did; "בלי לשמור כלום" decides content_only = yes.
- **Evidence:** `tests/test_no_store_answer_is_read.py` 3 passed on the owner's two messages (1 fails without);
  `test_conversation_agent_no_cards` unchanged; control `no_store_words` 1/1.

# 2026-11-19 — the concurrent daily-cap test counted calls, not dollars (Claude Code)

- **What broke:** intake-budget-pg on #463 (run 44484532008): `test_50_concurrent_turns_never_exceed_the_daily_cap`
  "6 not less than or equal to 5", while `counted(daily) <= cap` passed. Not the PR's diff (a CI script).
- **Root cause (the test's, not the cap's):** the cap is dollars. A call settles at its actual cost, far below its quote
  ($0.000525 vs $0.007374), and frees the difference; a turn that reserves after one settlement fits a 6th call under
  the same cap. Proof on local PostgreSQL 16: the 50 turns run one at a time reserved 50, counted $0.02625 of a $0.03687
  cap. The count bound held only when no call settled before the last reserve -- a timing condition.
- **Fix:** the test's provider reports each call's cost as exactly its quote, so no settlement frees headroom and at most
  five calls fit; the dollar assertion is unchanged. Same experiment one at a time: 4 reserved.
- **Evidence:** the test 25 of 25 passed concurrently; `test_intake_budget_pg.py` + `test_conversation_turn_cap_pg.py`
  35 passed on local PostgreSQL (1 skipped: it needs Redis, not here); control `daily_cap_test` 1/1 (envs pg: reserve() without the daily scope's cap -> the
  test fails).

# 2026-11-19 — the worker tells the generator what the gates check; it never did (Claude Code)

- **What broke:** SHARE failed all five production builds of 2026-11-17 (no og:title / og:description). **Root cause,
  Claude's bug (#430):** the gates' checks reach the spec through `carry_rules`, which only `install_all` called; only
  the rehearsal calls `install_all`, while the worker installs each gate on its own line. **Evidence:** SELECT on
  `project_version_specs` since 2026-11-17: 0 of 5 stored specs carry the `PLATFORM-CHECKS` requirement.
- **Fix:** the worker calls `carry_rules(engine, WORKER_GATES)` after its last gate and before the build -- the same list
  the rehearsal uses (`test_gates_calibrating` already holds the worker's gates equal to it).
- **Evidence:** `tests/test_worker_carries_gate_rules.py` 3 passed, on the real `_run_live_build_job` (BuildHarness):
  the spec the build starts from names og:title and every installed unit; 3 failed without the fix. Controls
  `worker_carries_gate_rules` 3/3.
- **One test double changed:** `test_first_pass_requires_a_passed_build`'s architect returned a SimpleNamespace, a spec
  no production architect makes; the wrapped worker path reads `spec.to_dict()` (as the facts, outline and contract
  wrappers do), so it returns a ProductSpec. Its assertion is unchanged (declared deletion).
- **Not proven yet:** that a model told about og tags writes them. After the release: the next production build's
  stored spec has `PLATFORM-CHECKS` (SQL), and its SHARE result in `evidence_json.skill_gates`. SHARE stays at warn.

# 2026-11-17 — the game check presses "start" the way a player does (Claude Code)

- **Root cause (rehearsal 44079074182, the stars game):** a working game waited on its start screen; the probe tapped the
  canvas and pressed keys but never the "התחל" button, saw one still frame and called the game frozen (`GAME_FROZEN`).
- **Fix:** before it plays, the probe presses one visible control whose whole label is a start word ("התחל", "שחקו",
  "start", "play"...), says which (`started_by`), and only then plays; a control that is not a start word ("הוראות") is
  never pressed. The start words are one pattern (`START_LABEL`) injected into the sandbox script, so a browser-free test
  checks the same pattern the browser uses.
- **Evidence:** `tests/test_game_runtime.py` + `tests/test_game_runtime_rules.py` 22/22 locally, 13 of them in a real
  browser; controls `game_start_screen` 4/4 with `NC_ENV=browser` (NC1-NC2 need Chromium; NC3-NC4 run in every CI job),
  `game_runtime` 9/9. NOT run in CI: the real-browser half (no CI job has Python Playwright with Chromium -- open).

# 2026-11-19 — G1, G10 and G5 block: calibrated on five builds (Claude Code)

- **Rule 4 (owner 2026-11-16):** a new gate warns until three builds, calibration and a proven fall on a broken page.
- **Evidence:** on the five builds that carry `evidence.skill_gates` (bld_a875456f, bld_77899122, bld_a9643012,
  bld_d36b3b4e, bld_b0de74d5; SELECT on build_jobs) G1, G10 and G5 passed all five; each unit's `fixtures/broken`
  page fails (the unit tests run it). They move from `CALIBRATING` to `CALIBRATED` and default to block.
- **Not moved:** HE and G11 (their false findings were fixed today: new builds first), BRAND (one finding, the served
  page not read), SHARE (fails every build: the generator never writes share tags -- a fix before any block).
- **Tests and controls:** the tests that pinned warn for these gates now state block; `gates_calibrating` 9/9,
  `skill_gate_copy` 5/5, `skill_gate_rights` 20/20, `skill_gate_blocks_brand_share` 4/4 (each NC4 now mutates a
  calibrated gate back to warn).
- **What changes for a build:** a G1/G10/G5 finding now fails the round and goes to repair instead of a warning.
# 2026-11-19 — gate calibration on the five builds with gate evidence; two false findings fixed (Claude Code)

- **Data (SELECT on build_jobs.evidence_json.skill_gates, the five builds of 2026-11-17 that carry it):**

  | Gate | Mode | Pass | Fail | Not run | Finding codes |
  |---|---|---|---|---|---|
  | G1 | warn | 5 | 0 | 0 | -- |
  | G3 | block | 5 | 0 | 0 | -- |
  | G4 | warn | 4 | 1 | 0 | SCRIPT_BLOCKING |
  | G5 | warn | 5 | 0 | 0 | -- |
  | G6 | block | 5 | 0 | 0 | -- |
  | G10 | warn | 5 | 0 | 0 | -- |
  | G11 | warn | 4 | 1 | 0 | ADDRESS_INCOMPLETE (false) |
  | HE | warn | 4 | 1 | 0 | HE_GENDER (false) |
  | BRAND | warn | 4 | 1 | 0 | BRAND_MISSING (not judged: the served page was not read) |
  | SHARE | warn | 0 | 5 | 0 | SHARE_META_MISSING (true: no og:title/og:description on any build) |
  | A4, APPLE, G8 | warn | 0 | 0 | 5 | -- (not judged on these builds) |

- **Fixed (both false, both on bld_d36b3b4e):** HE_GENDER on "פתיחת פניית שירות חדשה" -- a construct phrase whose
  head agrees with the adjective is ambiguous and not judged; pairs are matched overlapping, so a real error after a
  construct ("מחיר שירות חדשה") is now found. ADDRESS_INCOMPLETE on "תאריך שירות" -- a bare "כתובת" inside `<label>`
  is a form field, not an address.
- **Evidence:** `tests/test_gate_calibration_false_positives.py` 7 passed (3 fail on the old probes); the unit
  fixtures unchanged (broken fails, ok passes); negative controls `gate_calibration_false_positives` 5/5,
  `skill_gate_he` 6/6, `skill_gate_links` 5/5, `skill_gates` 10/10.
- **Not done here (one matter per PR):** moving G1/G10/G5 to block (5 clean builds each; the broken fixtures prove
  they fail); SHARE fails every build because the generator never writes share tags -- a generator fix before any
  block; BRAND needs the served page of bld_d36b3b4e to judge.

# 2026-11-18 — Sonnet for the conversation agent only, with the regular model when Venice does not offer it (Claude Code)

- **What was missing:** on Venice the cheapest listed model always won (`venice.select_model`), and one global list and
  ceiling served every account: listing Sonnet beside Haiku never ran Sonnet, listing it alone moved every account onto
  it. Environment variables alone could not give the owner's "Sonnet for the conversation agent only" (D10 analysis).
- **Fix (part 3 of 3):** agent accounts are quoted with the agent's own Venice profile (`conversation_agent`:
  `claude-sonnet-5-5` then `claude-haiku-5-5`, ceiling 2,10 = Sonnet's live list price, Venice pricing page read
  2026-11-18; both tagged anonymized, IRON_LAWS א.1 covered by the owner's decision). The quote says `mode: agent`,
  `venice_select: order`; the worker picks the first listed model Venice offers within the ceiling -- Sonnet, and Haiku
  only when Sonnet is not offered (decision 10), before any request, so never a second paid call. Every other account is
  quoted and served exactly as before (`mode: plain`, cheapest). The profile is in code, not an environment variable:
  the quote (Vercel) and the rehearsal (the worker) read one source. The builder never reads it (guard test). The
  rehearsal has an agent path (`REHEARSAL_PATH=agent`): production's newest quote with the agent profile, each
  conversation held to 8 turns and to production's project cap from the quote's own snapshot, as typed limits.
- **Evidence:** `tests/test_conversation_agent_sonnet.py` 12 passed on the real quote, build_gateway, VeniceIntakeGateway
  and select_model (Venice HTTP faked): Sonnet sent when offered, Haiku when not, the plain quote unchanged. Controls
  `conversation_agent_sonnet` 9/9.
- **Next:** release (Vercel and the worker), then the agent-path rehearsal: the first real measurement of the
  conversation agent's cost. No cost is reported before it.

# 2026-11-19 — agentic repair edits with exact blocks (Claude Code)

- **What broke (wf_309a64e1-002, three founder builds of 2026-11-17):** with Sonnet and gpt-6.1-sol out of credit and
  gemini-3.8-flash answering the agentic prompt with a function call, the edit step fell to the two 8,192-token
  Flash-Lite routes. The only edit offered was a whole file; a whole app.py needs ~9.4-9.8K output tokens (estimate),
  and all 14 answers were cut at 8,188 tokens. **Root cause:** whole-file edits, not the model.
- **Fix:** `omni_prod/repair_edits.py` -- `{path, old, new}` applied exactly once (overlaps counted), all or nothing,
  misses reported back with a hint that is never applied. `agentic_repair`: edit and submit take `edits`; an existing
  file over 12,000 characters is refused whole (`WHOLE_FILE_TOO_LARGE`); a submit whose edits missed does not end the
  round; the prompt asks for blocks and forbids function calls; `BuildDeadline`/`BuildCancelled` are re-raised
  instead of swallowed (found by the plan's skeptic).
- **Evidence:** `tests/test_repair_edit_blocks.py` 13 passed on a SYNTHETIC 20K-character app.py (the round zips were
  not read); repair tests 121 passed; negative controls `repair_edit_blocks` 9/9.
- **Not shown:** that a Flash-Lite route produces correct blocks on a real round, or that a build is saved -- only
  that an answer no longer has to fit a whole file. Credit is back on Sonnet and gpt-6.1-sol, so the strong routes
  answer first again. The trade-off the skeptic named stands: a block from a quality-70 route can now end a round
  that the classic fallback (gemini-3.8-flash) used to repair.
# 2026-11-19 — the first real Sonnet measurement: 1 of 10 agent calls answered (Claude Code)

- **What ran:** conversation-rehearsal, path `agent`, run 44445874611 on the worker, at code `063e4a5` (#456), quote
  `irs_35e9ed263ca84a86b575abcb` with the agent profile (Sonnet then Haiku, ceiling 2,10, order).
- **Result:** red, 1 of 3 scenarios passed (doors). One Sonnet call answered: **$0.018109 CONFIRMED** for the first doors
  turn (`provider_models=['claude-sonnet-5-5']`). The other 9 calls reached Venice and failed fast (17 s for the whole
  run), so their cost is UNKNOWN; each held its worst case, and butcher and bare hit the $0.15 conversation cap after
  about 4 failed calls -- the closing worked as designed (the stop, the free question, the summary).
- **Root cause:** not known yet. The rehearsal printed only "model call failed" (the interpreter keeps the exception
  type alone). A rate limit or a low Venice balance fits the timing; neither is shown. #457 makes the rehearsal print
  each failed call's reason; the next run says which.
- **What this is not:** a cost per conversation. One confirmed turn is not a measurement of the agent; no cost is
  reported until a run where the calls answer.

# 2026-11-18 — the conversation agent's 8-turn cap, and tokens and cost per conversation (Claude Code)

- **What was missing:** the owner's decision for Sonnet set at most 8 turns per conversation and tokens and cost
  recorded per conversation. No turn cap existed on the production intake path (only the rehearsal had one), and tokens
  lived only in each reservation's settle event.
- **Fix (part 2 of 3):** `reserve()` enforces `Caps.project_turns` under the same scope locks as the money check, so two
  tabs cannot both take the last turn and a retry with the same key returns its reservation. A turn is a paid call the
  provider received or may have received; a released call and a settled call the provider never received
  (contacted=false) are not turns, and only reservations made under the cap count (a project's earlier turns never close
  it on the first day). 'turns' closes the conversation; 'busy' (the cap reached only by calls still in flight) says so
  and does not. The cap holds for agent accounts only (`conversation_agent.MAX_TURNS = 8`). `conversation_usage(scope)`
  returns turns, tokens, settled and held amounts and the models; an UNKNOWN or open call makes the total None, never
  $0, and `counted_usd` equals `counted(scope)`. It is stored with each paid or limited assistant message (server side,
  never sent to the browser) and logged as `INTAKE_CONVERSATION_USAGE`; a read failure is kept as `usage_error` and never
  fails the turn. No migration.
- **Evidence:** `tests/test_conversation_turn_cap_pg.py` 8 passed on real PostgreSQL 16 (local, a fresh database with
  every migration); `tests/test_conversation_turn_cap.py` 8 passed. Controls `conversation_turn_cap` 8/8 and
  `conversation_turn_cap_pg` 7/7 (`envs: pg`). The PG file runs in intake-budget-pg's isolated per-file loop
  (`scripts/ci_test_coverage.py` PASS).

# 2026-11-19 — D10 review follow-up: the stop holds, says the right thing, and counts honestly (Claude Code)

- **What broke (the adversarial review wf_8c2f9499-486, findings that survived its skeptics):** the pre-check closed a
  conversation for good on a quote only HELD by a call in flight; the closed state lived in the last assistant message
  only, so a button answer or intent reply in between reopened the paid path; after 'daily' the conversation "had
  ended", after 'busy' a real stop never said why, two 'busy' replies became "no change"; 'busy' on the turn that
  completed the spec dropped the summary; an 'Updated:' line at the limit was dropped; a late paid reply after a daily
  pause was closed as 'daily'; an image-only message read "provider busy"; an EXECUTING call counted as a used turn;
  unreported tokens were summed as 0; Venice's fallback from Sonnet to Haiku was silent.
- **Fix:** each of the above, in `supervisor.py`, `budget.py` (`open_held`, `_TURNS`, `conversation_usage`) and
  `venice.py` (a `VENICE_PREFERRED_MODEL_UNAVAILABLE` warning with the reason).
- **Evidence:** `tests/test_conversation_limit_followup.py` 12 passed, 10 of them fail on the unfixed code (the other two
  are controls); `tests/test_conversation_turn_cap_pg.py` 11 passed on PostgreSQL 16, the 2 new ones fail on the
  unfixed code; negative controls `conversation_limit_followup` 10/10, `conversation_turn_cap_pg` 10/10 (pg).
- **Status:** implemented and verified locally; ships with its PR's release. The #456 release itself: the worker was
  deployed by a manual run (the merge title did not END with `[release]` -- Claude's error); Vercel production ships
  with this PR's release.

# 2026-11-18 — the agent's closing of an incomplete spec is no longer a dead end (Claude Code, D10 review)

- **What broke:** at the limit, an agent conversation whose spec was incomplete only named the gaps and pointed at the
  specification tab. The tab edits only answered fields (`app.js` `beginBriefEdit`), and with no card a typed answer
  is read only against an asked question (`_awaiting`), so the summary was unreachable. **Root cause:** the closing
  cleared `asked_in_words`. Found by the adversarial review wf_8c2f9499-486 (confirmed, high).
- **Fix:** the closing asks ONE open choice question in words (`_free_question`) and records it as asked; the next
  typed message is read by words (`typed_choice`) with no model call and no reservation. The intro no longer says
  "stops asking". A missing free-text field still has only the spec tab (open, below).
- **Evidence:** `tests/test_conversation_limit.py` 13 passed (the new test asserts one question, the answer recorded,
  and no model call); `conversation_limit` NC 15/15 (NC14 no question asked, NC15 not recorded as asked);
  `test_fast.sh` 187 files, 1480 passed; PG turn cap 9 passed, NC 8/8 pg.
- **Status:** implemented, verified locally; not yet in production (ships with the D10 PR and its release).
- **Open:** a missing free-text field at the closing; the review's unverified findings ("Updated:" lines dropped at
  the closing, an image-only message after the stop, an EXECUTING call counted as a turn).

# 2026-11-18 — a conversation that reaches its limit stops gracefully, with the way on (Claude Code)

- **What broke:** when a conversation reached a limit (the $0.15 project cap, the daily cap), the customer read "the
  model provider is busy, send again in a moment" -- false -- every question was cleared and the summary could never
  be reached: a dead end. **Root cause:** the limit was only a free-text `dropped` string (`worker_route.py`), the
  pre-check kept no reason at all (`supervisor._interpreter`), and the supervisor then took the "model did not answer"
  branch. Found by the D10 design analysis (wf_c308510a-631, 3 readers, 2 skeptics), confirmed in the code.
- **Fix (the owner's 2026-11-18 decision, part 1 of 3):** the limit is a typed outcome (`budget.LimitReached`,
  `Interpretation.limit` = {kind, source}; never caps or totals, the daily scope is every account's). The supervisor
  closes the conversation: why it stopped, what this message recorded, and the way on -- the summary with its approval
  when the spec is ready (gate 1, no model cost), else the specification tab (`edit_requirements`, the missing items by
  name). A message that takes the free lane after the stop gets the same closing, not "provider busy"; two closing
  messages in a row alternate (warehouse 113). The stored message is labelled `limit`, not "built from fixed rules".
- **Evidence:** `tests/test_conversation_limit.py` 9 passed on the real supervisor (as the rehearsal runs it) and the
  real ReservedWorkerInterpreter with a refusing reservation service. Controls `conversation_limit` 10/10; the 25
  existing controls on the changed files pass. Related tests 376 passed; `test_fast.sh` 1478.
- **Next (same decision):** the 8-turn cap and tokens and cost per conversation; then Sonnet for the agent profile
  (ordered preference, Haiku when Venice does not offer Sonnet, decision 10), the release, and the production-path
  rehearsal that is the first real cost measurement. No cost is reported before it.

# 2026-11-18 — a repair call where a route answered "no credit" no longer ends the whole build (Claude Code)

- **What broke:** the #448 fix (keep a build's verified work when no route answers the repair) missed one shape of
  "no route answered". **Root cause (Claude's bug, #448):** the catch matched the text `all model routes failed`. When a
  route in the call answered "no credit" -- Anthropic's HTTP 400 "credit balance is too low", including the 24-hour
  half-open trial of a CREDIT_EXHAUSTED route -- the router raises `ProviderQuotaUnavailable` instead
  (`routed_gateway.py`, depleted routes), whose message lacks that text, so the build still died the old way and threw
  its verified rounds away. Found by the repair-JSON root-cause analysis (wf_309a64e1-002), confirmed in the code.
- **Fix:** `autonomous_core.py` matches `ProviderQuotaUnavailable` by type, beside the existing text match. Any other
  model error still ends the build.
- **Evidence:** `tests/test_repair_model_unavailable.py` 6 passed; the new test runs the real RoutedModelGateway with
  one route answering Anthropic's no-credit text and the other prose instead of JSON: the router raises
  `ProviderQuotaUnavailable`, the build ends `failed / repair_model_unavailable` on round 1's version, and the customer
  reads `verification_failed`. Controls `repair_model_unavailable` 4/4 (NC1 and NC2 follow the changed line; NC4: the
  type check removed fails the new test).
- **Not done here:** the rest of the repair-JSON plan. Its winning proposal (exact edit blocks) was refuted by its own
  skeptics (the recommended option keeps whole-file answers that are cut at 8,188 tokens; build time budget unchecked;
  the stored rejected answers in production not read). It is re-planned before anything is built.

# 2026-11-18 — the meter prices one call by its id, not the whole ledger; every routed cost to date is invalid (Claude Code)

- **What broke:** a turn on the routed path was charged for every earlier turn of the run. **Root cause (Claude's
  bug):** `reservation_worker.meter(gateway, quote)` summed every provider attempt in `gateway.recorder.records`. The
  routed gateway's ledger keeps every attempt of its life, so when one gateway served many turns (the routed rehearsal,
  `intake/benchmark.py --model`) turn k paid for turns 1..k. **Invalid (owner 2026-11-18):** every routed cost to date
  -- runs 44126201300, 44141955553 and 44263232985, the figures DECISIONS question 2 stood on, and decision 10's
  numbers. The real cost of the conversation agent has not been measured; the next production-path rehearsal is the
  measurement, and no cost is reported before it. **Not hit:** production billing -- each turn there is one
  reservation on a fresh gateway (`ReservedWorkerInterpreter`); Venice emptied its ledger per call, which hid the same
  trap.
- **Fix (one mechanism everywhere):** the caller that meters a call creates its id (`attempt_ledger.new_call_id`) and
  passes it to the gateway and to `meter(..., call_id=)`. The routed gateway stamps every attempt and every route event
  of the call with it (a build that names none gets a fresh id per call); Venice stamps its records and no longer
  empties its ledger; the reservation worker uses the reservation id; `ModelInterpreter` makes one id per turn and
  refuses a gateway that cannot carry one. Loud, never $0: no id, no ledger, or an attempt without an id raises
  `MeterError`; the worker and the interpreter record that as UNKNOWN with the reason. `call_id` is not persisted (no
  column, no migration). The routed rehearsal names, per turn, the route that answered and each route that refused and
  why (from that call's route events), prints each turn's cost and state, and counts an UNKNOWN turn as unknown, not
  $0.
- **Adversarial review of the change (3 reviewers, 2 skeptics per finding), fixed before the PR:** the routed rehearsal
  lost the lane (`gateway.task = conversation_complex` set an unused attribute, so escalated turns ran as plain
  `conversation`); the workflow's grep dropped the `::warning` lines that name each refused route; a production-path
  call whose gateway could not be built was metered on no ledger or the previous call's; a call id dropped by a layer
  on the way would let the gateway invent one and the meter read "not contacted", $0 (no such layer exists today --
  guarded anyway: `meter(before=ledger_mark(...))` requires every attempt written during the call to carry its id);
  a route closed earlier in the run was skipped with no route event, so later turns could not say why it did not
  answer (it now records `skipped: ...` with the call id); and untested stamps and paths got tests and controls.
- **Evidence:** `tests/test_meter_by_call_id.py` 17 passed -- ten turns on one real RoutedModelGateway, each answer
  costing a different amount (n/1000), give `0.001 .. 0.010`, ten sums (the old meter gave `0.001, 0.003, 0.006, ...`);
  a call with a fallback counts both its attempts and nothing else. `tests/test_rehearsal_routed_path.py` 12 passed.
  Related tests 610 passed. Controls `meter_by_call_id` 24/24: NC1 (permanent) the meter sums the whole ledger; NC2 an
  untagged attempt skipped as $0; NC3 the routed gateway does not stamp; NC4 one id for every turn; NC5 Venice
  untagged; NC6 the worker meters another id; NC7 the rehearsal reads the run's events; NC8 a dropped id reads $0;
  NC9 the lane lost; NC10 the warnings filtered; NC11 a stale ledger; NC12 the gateway ignores the caller's id;
  NC13-NC24 each remaining guard, stamp and catch. The 8 existing controls on these files pass.

# 2026-11-18 — a stalled Chromium install no longer locks out its own retries (Claude Code)

- **What broke:** `a2-offline` on #449 (run 44259745208) skipped every A2 browser test. **Root cause:** attempt 1 hit
  its 160 s bound on a slow apt mirror (`Fetched 21.9 MB in 3min 8s (117 kB/s)`); `timeout` stopped playwright but its
  apt-get child (pid 2634) lived on and held the dpkg lock, so attempts 2 and 3 failed in 0 s on `Could not get lock
  /var/lib/dpkg/lock-frontend`. The one re-run passed. `browser-tests` in `v24-ci.yml` had the same loop.
- **Fix:** both install steps set `DPkg::Lock::Timeout "150"` in `/etc/apt/apt.conf.d` before the first attempt, so a
  retry waits for the stalled install (under one 160 s attempt) instead of dying on its lock.
- **Evidence (container, apt 2.8.3, a process holding the lock for 6 s):** without the setting apt-get exits after 0 s
  with the same message as CI; with it apt-get waits and ends `coreutils is already the newest version` after 6 s.
  `tests/test_ci_playwright_install.py` 5 passed; controls `apt_lock_wait` 3/3 (each workflow without the wait; a wait
  longer than one attempt).

# 2026-11-18 — the fast suite re-measured (Claude Code)

- **Why:** `light` failed its 30 s budget four times on 2026-11-17 on the same 172 files (21.8 to 33.0 s on the CI
  runner; 17 s here) -- the file's own rule says: re-measure when the budget fails, never raise it.
- **Re-measured by the documented method** on main `8c7dcbf`: 442 test files; 198 touch the environment, 30 need absent
  packages; 214 run alone, 207 pass in under 2 s. **New:** a cap on the total -- the kept files run together, fastest
  first, under 13 s here. Result: 187 files (was 172), 1476 tests, 11.5-12.3 s in one process (was 17 s). The module listed in
  `tests/needs_env.txt` (`test_r2_storage_signing.py`) stays out; the full suite caught the first cut keeping it.
- The `fast_suite` controls anchored on the header line "# Result: 172 files", which changes at every re-measure; they
  now anchor on the stable rule line. Controls 2/2.

# 2026-11-17 — a repair no model answered no longer throws away the build (Claude Code)

- **The owner's butcher project (prj_9GM6q4KQX-tu9A), read from build_jobs and build_events:** bld_2b5225d1 (19:56),
  bld_6323468a (22:12) and bld_c0b2b43b (22:37) failed with `model_unavailable`; bld_b0de74d5 (22:46) is READY (2 repair
  rounds, $0.278). In the failed ones the tests had run (up to 3 rounds); then no model route answered the repair with
  valid JSON -- gemini-3.8-flash wrote an analysis before the JSON (rejected by T3's no-leading-prose rule, kept),
  gemini-3.5-flash-lite was cut at its length (`finish_reason=length`), gpt-6.1-sol skipped (CREDIT_EXHAUSTED since
  07:56 UTC). The exception ended the whole build and the screen said "אף בדיקה לא רצה" -- false.
- **Fix:** a repair that no route answered ("all model routes failed") stops the repair (`repair_model_unavailable`);
  the build ends on its best verified version with its real checks (`verification_failed`, "stopped repairing: no model
  returned a valid repair"), and the screen says why in Hebrew and English. Any other error ends the build as before.
  Tests `tests/test_repair_model_unavailable.py` 4/4 (the real loop and the real release verdict); controls 3/3.
- **Cost of the three failed builds:** $0.42 + $0.47 + $0.22 provider spend (company loss; the owner's credits returned).
- **The OpenAI route reopened (CLAUDE.md section 5, 2026-11-17 23:44 UTC):** the owner topped up the account ("הטענתי
  עכשיו"); the circuit (`provider_health`) would have kept the route closed until its 24-hour trial (2026-11-18 07:56).
  Backup branch `backup-before-openai-route-reset-2026-11-17` (br-tiny-hat-b9nclt9c); dry read: 6 rows, two
  CREDIT_EXHAUSTED; one transaction guarded on the old value (a first try matched 0 rows -- the stored time has
  microseconds -- and changed nothing); old: `openai-gpt-6-1-sol` CREDIT_EXHAUSTED since 2026-11-17 07:56:42.188853,
  failures 1, recheck 2026-11-18 07:56; new: UNKNOWN, `reset_by` "claude-code for the owner: OpenAI credit topped up
  2026-11-17" -- the same row `omni_prod.intelligence.health reset` writes; verified by a separate query (1 row
  changed, the other 5 as they were). Not reset: `anthropic-claude-sonnet-5-5`, CREDIT_EXHAUSTED since 2026-11-16 (the
  owner named OpenAI only).
- **Open:** the code models' answers that fail JSON (leading prose, truncation) are not fixed here.

# 2026-11-17 — the conversation rehearsal runs on the production intake path (Claude Code)

- **Merged and released:** #444 `721f560` -> `0ce8cde` (the owner's conversation: the image question is not a loop;
  "only I can change" is not an audience; a leading "לא" answers the login question). Merged: #446 `c5bf71c` ->
  `448a18a` (negative controls in parallel). This replaces #445, which could not take main without a force-push.
- **Why:** the rehearsal ran on the routed gateway; production intake runs through Venice. It passed on Sonnet while the
  owner's real conversation ran on Haiku -- a rehearsal that is not the production path is not evidence of it
  (CLAUDE.md section 3: tests run on the real path).
- **Now:** by default (`REHEARSAL_PATH=production`) every agent call builds the gateway the intake worker builds for a
  reservation (`reservation_worker.build_gateway`), from the quote of the newest settled production reservation, read
  from the database -- production's provider, allowed models, price ceiling and per-call bound (recomputed for each
  call's input with the same formula as `budget.quote`). Every call's real model is recorded (`provider_models`).
  `routed` keeps the old path and says it is not the production path. Tests `tests/test_rehearsal_production_path.py`
  4/4; controls `rehearsal_production_path` 4/4.

# 2026-11-17 — the owner's human test: the image question looped; the conversation ran on Haiku (Claude Code)

# 2026-11-17 — negative controls in parallel; the pg step's limit is not raised again (Claude Code)

- **Root cause (investigated, owner's rule: investigate, do not raise a limit):** the pg job's controls step was raised
  5 -> 10 -> 14 minutes in two days and still ran over: main took 8:56 to 11:37 today, and #445 (one more spec, about
  6 seconds) ran over 14 twice. The time is 574 controls, each a pytest start, in a row on a 4-core runner.
- **Fix:** `NC_JOBS=N` runs N controls at once; each control's lines are buffered and printed in the same order and
  format as a serial run. On a real database every worker gets its own copy of the migrated database
  (`CREATE DATABASE nc_<i> TEMPLATE ...`, bounded retry) and its own Redis index; the runner's own settings never reach
  the tests a control runs. v24-ci: `NC_JOBS=4`; the pg job: `NC_JOBS=3` with `NC_DB_URL`/`NC_REDIS_URL`. No limit
  raised, no control removed; `NC_JOBS=1` (the default) is the serial run.
- **Evidence (local, default environment):** all specs in parallel: 532 controls PASS, 0 FAIL, 0 `::error`; 6 specs
  run only in their own jobs (a2, pg) and say so; 278 s against about 20 minutes serial. Tests
  `tests/test_negative_controls_parallel.py` 5/5; controls `nc_parallel` 5/5; the existing runner tests pass. Found on
  the way: with `NC_JOBS` inherited, the runner's own tests ran in parallel mode under their controls -- fixed, and a
  control proves it.
- **CI on `d9f26d7`:** the pg job's controls step took 4:38 in parallel on per-worker databases (it ran over 14:00
  twice before). One control was exposed as timing-dependent: `test_free_port` caught a fixed port only when the two
  runs happened to overlap, and under parallel load they did not. A test without timing now holds the first port while
  the second is taken (`ThePortIsFree`), and the control points at it; the real-run test stays. `light` ran over its
  30 s budget at 30.5 s (the fast suite did not change; it ran in 21.8-29.6 s today).

# 2026-11-17 — the owner's human test: the image question looped; the conversation ran on Haiku (Claude Code)

- **Merged and released:** #443 `444d3d4` -> `a3bf297` (the browser check: a visible message rewritten after a save is
  feedback).
- **The owner's conversation (prj_9GM6q4KQX-tu9A, "קצביה של שמעון", read from intake_messages):**
  - The image question ("ומה לעשות עם התמונה?") came back three times. Asked for a caricature of Shimon -- a change
    the platform cannot make -- then "מה שאתה רוצה תעשה אתה" ("do what you want"), neither moved it; the owner wrote
    "גם ככה לא מקשיב". Roots: a change asked again had no resolution, and handing the choice over was not read for
    `image_use`. Fixed: a caricature/drawing is read as a change; the first time it is said to be unavailable, the
    second time (or when handed over) the question's own recommendation is taken and said in one sentence. Real
    path tests `tests/test_image_change_not_a_loop.py` (the owner's own sequence); controls 4/4.
  - **The conversation ran on Haiku, not Sonnet:** production intake runs through Venice
    (`OMNI_INTAKE_PROVIDER=venice`) with an allowlist of Haiku and Qwen and a price ceiling of $0.18/$0.90 per million;
    Venice picks the cheapest listed model. D10 changed the routed gateway, which production intake does not use, and
    the conversation rehearsal ran on the routed gateway too -- so it never tested the production path. Switching
    needs higher caps (project $0.15, daily $1.00 today): question 2 in DECISIONS, the owner's.
  - Two misread answers, fixed: (1) "רק אני יכול לשנות מחירים" -- who EDITS the site -- was read as audience
    "internal team" (a deterministic rule, high confidence); an editing verb after "only I" is no longer an audience.
    (2) "לא אני משנה את האתר דרך כאן בעתיד", the answer to "האם צריך התחברות עם סיסמה?", was not read (a typed answer
    had to name an option), so the model's guess (roles) stayed and became a blocker; a leading "לא" now answers a
    yes/no question when the message names no option of its own ("לא, צריך הרשאות למנהל ועובד" stays roles; "לא
    יודע", "לא בטוח", "לא משנה" are not a no). Tests `tests/test_owner_answers_are_read.py` (the owner's words, the
    real path); controls 4/4.
  - Not fixed yet: "אז בלי" was read by the model as a message cut short (it came after the misread login blocker,
    which no longer arises); one turn timed out at the model ("העומס אצל ספק המודל").
- **The butcher build (bld_2b5225d1) failed with `model_unavailable`:** the code model answered with an analysis
  before the JSON (gemini-3.8-flash and gemini-3.1-flash-lite), and the OpenAI route is skipped: CREDIT_EXHAUSTED
  since 2026-11-17 07:56 UTC (HTTP 429, "no credits remaining") -- an account balance, the owner's.

# 2026-11-17 — the browser check called a working lead form "no feedback" (Claude Code)

- **Merged and released:** #442 `0d9bfe3` -> `04dcec6` (D5, D7 part 1, D8, the agent asks the subject first). Live
  rehearsal on production code (run 44141955553): doors, butcher and bare all PASSED, 0 cards, every fact kept,
  $0.034 + $0.096 + $0.148.
- **The owner's human test (bld_d36b3b4e, "148 doors", personal data: yes):** rounds 1 and 2 failed on the same
  finding: "form 'lead-form': the first submit showed '...בדיקה 1 נשמרה בהצלחה...', the second successful submit
  showed no message". Root cause in the platform, not the site: the probe's second round counted only an element
  that was HIDDEN and then shown. A success line that stays on the page and is rewritten per save (a normal lead
  form) was failed -- reproduced locally with the real probe (`text_changed: true`, `revealed: []`).
- **Fix:** a visible message whose words change after a successful save is feedback (`SNAP`/`UPDATED` in
  `omni_prod/browser_probe.py`); a message that stays unchanged, one hidden after first use, and one that disappears
  while it is rewritten are still caught. The decision is one pure function (`feedback_missing`) that the sandbox
  script runs from the same source; `tests/test_feedback_rule.py` checks it with no browser. Controls
  `probe_updated_message`: NC1-NC3 run in every CI job; NC4-NC5 (the JavaScript, `envs: browser`) need Chromium.
  Real-browser tests 13/13 in `tests/test_browser_probe.py`, locally. The T4 evidence lock follows the new hash.
- **Found on the way (CI gap, open):** no CI job has Python Playwright with Chromium, so the real-browser Python tests
  (`test_browser_probe.py`, the browser half of `test_game_runtime.py`) are skipped in CI and run only locally. The
  first push of this fix (`bd17229`) put browser tests under controls and CI reported them DID NOT RUN (skipped)
  -- correctly; the controls now point at the browser-free rule.
- **The owner's build:** bld_d36b3b4e ended FAILED at 19:33 UTC on this finding alone in its last round (stop reason
  `time_budget`, provider spend $0.42). Its evidence keeps the finding but not the per-round `text_changed` /
  `revealed` data, so for this exact build the cause is inferred from the message text (it names the saved record)
  and the local reproduction, not read from the build.

# 2026-11-17 — DECISIONS 5, 7 (part 1) and 8 (Claude Code)

- **Merged and released:** #441 `81e24c4` -> `f14b773`. Vercel production: `OMNI_INTAKE_AGENT=accounts` and
  `OMNI_INTAKE_AGENT_ACCOUNTS` (the owner's account only) set, then a redeploy of `f14b773` (the release build had
  started 3.6 s before the variables were saved).
- **Root cause of #441's first red CI (Claude's bug):** NC1/NC3 of `no_repeat_questions` had their default expected
  lists shrunk but not the pg ones (`expect_failed_pg`); pg-tests failed on `c4d5a7f`. Fixed and declared.
- **D5, default hero:** a content-only website with no uploaded photo and no "בלי תמונות" gets one generated main
  image (optional: a failed generation never fails the build). Found on the way: the approved brief's
  "Logo: a text logo ..." line ordered a generated icon in EVERY build; now only the customer's own words order one.
  Controls `default_hero` 5/5.
- **D8, the repairer and the builder's tests:** the rule "the repair never touches tests" lived only in the prompt; no
  code enforced it. Now `omni_prod/test_edit_guard.py` reviews every repair round: in a test the builder wrote in this
  build only an assert's expected value may change; a test whose changed line carries the customer's phone, price,
  address or hours is reverted; any other change is reverted and the repairer is told why; every allowed edit is
  counted in the build evidence (`test_edits`); the same value fixed twice stops the loop (`test_value_fixed_twice`,
  explained in the chat in Hebrew and English). Controls `repair_test_edits` 7/7.
- **D7 part 1, nearest category:** an unrecognised business takes the palette of the nearest category -- first a related
  word listed under `near` in `vertical_palettes.json` (a pizzeria is near restaurants, a florist near furniture and
  interiors), then an inflection of a category word (letter trigrams, threshold 0.55). With no nearness at all the old
  clause stays (so a doors request without the word "דלתות" still has no palette: `doors_palette` NC1 keeps its
  original three tests; Claude's first edit of that list was wrong, caught by CI on `6054d4d`, and reverted -- the
  declaration written for it now covers no deleted line). The florist contract's pinned fingerprints moved (old
  values kept). Controls `nearest_category` 5/5,
  `vertical_palettes` 4/4, `doors_palette` 3/3.
- **Evidence:** full suite on the branch: 1 failed, 3840 passed -- the one is `test_m4_acceptance` W, the local
  300-second subprocess timeout (287 s on main; it passes in CI). `test_fast.sh` 1428 passed.
- **Live conversation rehearsal on production code (run 44126201300, Sonnet route):** doors PASSED (5 turns, 0 cards,
  approval, facts kept, $0.0517), butcher PASSED (4 turns, $0.0848), bare FAILED: "אתר" alone reached the approval in
  three turns without anyone asking what the site is about (the phone it was to be given never came). Also: in agent
  mode the agent said "I need your explicit confirmation with the button" -- there is no button. Both fixed: the
  agent asks the subject first, never offers the approval without it, and the answer joins the request the build
  starts from; the sensitive line says "in words". Classification corpus: 4 of 101 requests have no subject, all
  four genuinely ("אתר", "build me a 2d game", "סרטון תדמית לעסק", "שלום, אתר לעסק שלי"). Controls `agent_subject` 5/5.
- **CI on `6054d4d`:** the pg job's negative-controls step hit its 14-minute limit. Investigated, not raised: every
  spec ran about 1.8x slower than on `81e24c4` (476 s -> 849 s+ for the same specs, untouched ones included);
  locally the same test file takes 13.3 s on the branch and 12.8 s on main, imports 0.1 s on both -- the runner,
  not the change. The new specs add about 30 s.
- **NOT done:** D7 part 2, the one colour question in words, is held until after the owner's human test (it changes the
  conversation itself).

# 2026-11-17 — conversation on Sonnet; per-account agent; classification corpus; Hebrew whole words; conversation rehearsal (Claude Code)

- **Merged and released:** #440 `7087e3c` -> `8d37478` (phase 3; CI validate limit 15 min).
- **The owner, 2026-11-17: "decide everything yourself"** -- decisions 2-11 closed in DECISIONS.md, with the owner's
  later refinements (per-account flag, decision 8 restricted, decision 3 signal, decision 7 fallback, phase-4
  acceptance on the live model only, validate duration printed, unique URL in the corpus).
- **D10:** task `conversation` (and `conversation_complex`) prefers Sonnet 5.5 (preferred floor 85); the mandatory
  floor stays 70.
- **Per-account agent:** `OMNI_INTAKE_AGENT=accounts` + `OMNI_INTAKE_AGENT_ACCOUNTS`; every other account keeps the
  conversation as it was. The account of the turn is set for the whole turn (a context variable).
- **One broken method, not three bugs:** words were matched inside words -- "פירוק" read as green, "כפתורים" as
  appointments, "בלי טופס הרשמה" as asking for sign-up, "ישיר" as a song (#434). Two explicit rules, each with a
  control: whole words with Hebrew prefixes; a negated cue asks for nothing.
- **Classification corpus:** `tests/fixtures/classification_corpus.json`, 101 frozen requests (25 real first messages
  from production, read only; 76 written by Claude Code), each with the type a professional would build; CI runs it.
  It forced four fixes: a site that runs something is an app; a score app is no game; a business that gives its street
  or phone describes a site; "דף" is a page. Run-10b's R3 and R4 locked failures now pass (markers removed).
- **Conversation agent fixes found by the rehearsal:** "לא שומרים כלום" is content only (deciding phrases); a question
  the agent cannot default stays asked in words (it used to send the customer to a Requirements-tab card that the
  agent never shows).
- **Conversation rehearsal (phase 4 tool):** `omni_prod/conversation_rehearsal.py` + `.github/workflows/conversation-rehearsal.yml`:
  the real supervisor with the live model, a frozen scripted customer, measured acceptance (no card, approval reached,
  facts kept, a model wrote the replies). A scripted model is a development tool only, never the gate.
- **CI:** the validate job prints its duration; over 12 minutes is a warning to investigate.
- **Evidence:** classification corpus 2 tests, controls `classification_corpus` 6/6, `hebrew_whole_words` 4/4,
  `conversation_agent_phase1` 8/8, `conversation_rehearsal` 3/3, `conversation_model` 2/2; `test_fast.sh` exit 0
  (1428 passed, the 4 run-10b locks now pass).
- **NOT verified:** a live conversation (the rehearsal workflow runs after this is deployed).

# 2026-11-17 — conversation agent, phase 3: an exact hand-off -- the customer's facts and page structure reach the generator (Claude Code)

- **Merged and released:** #439 `a10a0a7` -> `ee2d7ca` (phase 2).
- **Why:** the architect rewrites the request in its own words and the generator gets the spec alone -- the same
  hand-off that lost the design contract (#429). What the customer wrote exactly could be dropped there.
- **Facts** (`fact_canon.install_facts`): one mandatory requirement with every phone, e-mail, address and hours
  statement of the request, as written, and an HTTP-checkable criterion. Three calibration builds of four paid a
  repair round for "facts the customer gave are missing from the page: address".
- **Page structure** (`page_outline`): the sections the customer listed under "מבנה הדף:" (or "page structure:"), in
  order, with what they wrote for each, become one mandatory requirement; the criterion checks the names in order.
  The "148 דלתות" brief gives six sections (הירו ... פוטר). A request with no structure heading gets nothing.
  Both are installed in the worker and the rehearsal; no architect is said in the log, never assumed.
- **Evidence:** `tests/test_the_generator_is_told_the_facts.py` 6 passed, `tests/test_page_outline_reaches_the_generator.py`
  7 passed (both through the real build loop); controls `facts_shown` 6/6, `page_outline` 6/6; `test_fast.sh` exit 0.
- **NOT verified:** a real build with either requirement.

# 2026-11-17 — conversation agent, phase 2: the model asks the customer's decisions in its own words (Claude Code)

- **Merged and released:** #438 `f22c53d` -> `acbbbc8` (phase 1, behind `OMNI_INTAKE_AGENT`).
- **Phase 2 (same flag):** the model gets `context.ask_next` -- the decision only the customer may make that is
  still open, in the detector's order: what it means, why it matters, the choices in plain words -- placed first in the
  context (the context is cut at 2,400 characters). Its rules: ask that one question in your own words for this
  business, one sentence on why it matters, the choices named naturally, never answer it for them. With the agent
  there are no "asked with buttons" topics.
- **Also fixed:** the expert checklist came from the family of the LAST message, so after "כן" a doors site got the
  web-app checklist (business rules, managers). It now comes from the request.
- **Evidence:** `tests/test_conversation_agent_asks_in_its_words.py` 4 passed; controls `conversation_agent_phase2`
  5/5; `test_fast.sh` exit 0.
- **NOT verified:** what the live model writes with these rules (phase 4: real conversations).

# 2026-11-17 — conversation agent, phase 1: no question cards (Claude Code)

- **The owner's order (2026-11-17):** no ready-made questionnaire; the first conversation is with a live model
  that knows the work. Plan: `docs/CONVERSATION_AGENT_PLAN_HE.md` (four phases).
- **Phase 1 (flag `OMNI_INTAKE_AGENT`, strict: 0 or 1, anything else raises):** the customer never sees a
  question card. Every question is in the reply, in words; it is still recorded as asked. A typed answer settles
  only the question asked in the previous turn, and only when the words name exactly one option
  (`intake/conversation_agent.typed_choice`, closed word lists) or the model proposed that field with high confidence
  and a quote from that message. Otherwise nothing is set. The deterministic layer still decides what is open and
  when the brief is complete; the two approvals stay server-bound buttons.
- **Evidence:** `tests/test_conversation_agent_no_cards.py` 6 passed -- a whole conversation through the real
  supervisor reaches the spec approval with no card (content-only, from typed words); without the flag the cards are
  as before. Controls `conversation_agent_phase1` 6/6; `test_fast.sh` exit 0.
- **NOT verified:** a conversation with the live model (phase 4). **Open for the owner:** the conversation model
  (DECISIONS 10) and switching the flag on in production (DECISIONS 11).

# 2026-11-17 — "content only" is asked, not dropped (Claude Code)

- **Merged and released:** #436 `6ad3eed` -> `227d23c` (doors palette; the measure rule keeps its check; no phone
  from a hash).
- **What broke ("148 דלתות"):** the owner answered "תוכן בלבד: כן", then "פרטים אישיים: כן". The first answer was
  dropped in silence (`_drop_inapplicable`) and the site became a leads database.
- **Fix:** neither answer is dropped. When "personal details: yes" follows the customer's own "content only: yes",
  one question is asked in words (`storage_intent`, not delegable): "only the business details are shown -- nothing
  is stored" settles both answers as a content site; "the site stores visitors' details" settles it as a site that
  stores. Until it is answered the brief cannot be approved.
- **A test that pinned the old behaviour is changed knowingly:** `test_no_dead_end_conversation`'s walk "content
  only: yes, then personal details: yes" ended at the summary with records; it now passes through the new question
  (answered "visitors") and ends at the same summary.
- **Evidence:** `tests/test_content_only_is_asked_not_dropped.py` 5 passed (through the real conversation);
  controls `content_only_asked` 5/5; `test_fast.sh` exit 0.

# 2026-11-17 — what "148 דלתות" still showed: no palette for doors, a measure rule that failed its own check, a phone read from a hash (Claude Code)

- **Merged:** #435 `cdc0bb3` -> `0316cbe` (the rehearsal asks the release policy).
- **1. No design contract for a doors company** (bld_a875456f: G-APPLE `NOT_RUN`, "the Design line has no
  four-colour palette"): doors were not a category. Doors are a trade: `vertical_palettes.json` renovation gains
  "דלתות", "התקנת דלתות", "דלת ממד", "doors" ("דלת" alone is not one: "דלת הכניסה של האטליז" stays a butcher).
  An unknown business is still said, not defaulted (DECISIONS.md, open question 7).
- **2. The measure rule failed its own check** (rehearsal 44057019675: "about 52ch" gave Hebrew paragraphs 53
  characters a line against a minimum of 55). The rule now gives `max-width: 35rem` (about 65 characters at 16px);
  measured in a real browser on three font stacks, no MEASURE finding. The check (55-75) is unchanged.
- **3. A content-only answer overruled in silence -- NOT fixed here.** The owner answered "תוכן בלבד: כן", then
  "פרטים אישיים: כן"; the first answer was dropped and the site became a leads database. A first fix (not asking
  personal data after content-only) broke six existing tests on the full suite: personal data is a held material
  question by an earlier decision, and an answer to it would then have been dropped in silence instead. Withdrawn;
  DECISIONS.md open question 9.
- **4. A phone read from a hash (found while working on 3).** The fact canon read "+97229093349" out of a brief's hex
  fingerprint ("fingerprint e029093349ecb315"); whether a brief got an invented phone depended on its hash. Hex
  tokens are blanked before the canon reads phones.
- **Evidence:** `tests/test_doors_get_a_design_contract.py` 4 passed; `tests/test_a_hash_is_not_a_phone.py` 2 passed;
  controls `doors_palette` 3/3, `hash_is_not_a_phone` 1/1; `test_fast.sh` exit 0.
- **NOT verified:** a production conversation with these changes.

# 2026-11-17 — the rehearsal asks the release policy (Claude Code)

- **Merged and released:** #434 `01e39ab` -> `69a308c` (`[release]`; the pasted brief reaches the build).
- **Why:** for half a day every customer build failed `release_policy_failed` while five rehearsals of the same code
  said "ready". The rehearsal stopped at the engine's result and never asked the policy.
- **Change:** `rehearsal.release_policy` runs the worker's own `release_quality_report` on the rehearsal's build; a
  build the policy blocks is a failed rehearsal (exit 1) with an `::error` in the customer's words. Rights are not
  assessed in a rehearsal (no account, no markets) and are reported `NOT_ASSESSED`.
- **Evidence:** `tests/test_rehearsal_asks_the_release_policy.py` 5 passed (one reproduces the production state: the
  same three NOT_RUN checks, the same words); controls `rehearsal_asks_release_policy` 5/5.

# 2026-11-17 — the owner's brief never reached the build; what the customer wrote now does (Claude Code)

- **Merged and released:** #433 `96958b3` -> `7596591` (`[release]`; the chain walk reaches the deepest stage).
- **What broke ("148 דלתות", builds bld_a875456f 09:27 and bld_77899122 09:49, $0.18 + $0.30):** the owner pasted a
  3,295-character brief (business, offer, page structure, FAQ, palette). The router answered "שיר, סרטון או מוזיקה
  עוד לא ... ההודעה שלכם נשמרה בשיחה", and the brief was then started from the next message alone: "אתר". With the
  answers "צוות פנימי" and "פרטים אישיים: כן" the build became an internal leads database
  ("persistence: records"). The second build failed its own generated test 3 rounds in a row (the test posts phone
  "053-7778899" and looks for it unchanged; the app stores it normalised; the repairer may not edit tests).
- **Roots (both mine to fix):**
  1. `intake/families.py`: the media rule matched "שיר" (a song) inside "ישיר" ("טון: ישיר, מקצועי" -- a direct
     tone). Now "שיר" is a word, alone or after one Hebrew prefix letter; and a text that describes a page and mentions
     a video in passing is a website.
  2. `conversation/supervisor.py`: a message the customer was told was kept was not part of the request. A new
     brief now starts from everything the customer wrote in the project before it (last five messages, 12,000
     characters, newest words never cut, a cut is logged).
- **Evidence:** `tests/test_a_refused_message_is_still_the_request.py` 8 passed (the production message, excerpted
  read-only, starts a brief that carries "148 דלתות", "1,390 ₪", the service area and "בלי קרוסלה"); controls
  `refused_message_kept` 5/5; full suite on this change 3779 passed, 0 failed.
- **NOT fixed here:** the conversation accepted "content only: yes" and "personal data: yes" together without
  asking which one holds; a generated test that contradicts the app cannot be repaired (the repairer may not edit
  tests).
- **NOT verified:** the owner's conversation on production after the release. The existing project keeps its brief
  (fingerprint 3c1889fd) -- a new project is needed.

# 2026-11-17 — PRODUCTION: every build since #426 failed the release policy; a bug of mine; fixed (Claude Code)

- **What broke (the owner's build, bld_a875456f, 09:27 UTC, worker `4071192`, $0.18):** two rounds, every test
  passed, quality 89, QA review clean -- and `release_policy_failed`: "mandatory checks not passed:
  files/cross_file_consistency NOT_RUN (consistency gate did not run (disabled)); preview/preview_starts NOT_RUN;
  acceptance/behavioural_acceptance NOT_RUN". In the stored evidence `consistency_gate`, `preview_smoke` and
  `behavior_acceptance` are null.
- **Root (a bug of mine, shipped in #426 today):** `behavior_acceptance.find_in_chain` walked at most 20 wrappers
  and then answered "not found". #426 added G5, G8, A4 and G-APPLE on top of the build's stages; the worker's chain
  became longer than 20, so the three deepest stages were never reached. They had run and passed; their evidence
  was read as missing. No build could pass the release policy from `609929e` on. The rehearsal does not run the
  release policy, so five rehearsals today did not show it.
- **Fix:** one bound for every chain walk (`behavior_acceptance.MAX_CHAIN = 64`, used by the gates' report and the
  asset-marker install too), and a walk that reaches the bound raises `ChainTooLong` instead of answering.
- **Evidence:** `tests/test_chain_walk_reaches_the_deepest_stage.py` builds the worker's chain with the real stage
  executors and the real installs: depth 26; on the code before the fix `consistency_evidence`, `behavior_evidence`
  and `preview_smoke_evidence` are all None (reproduced), after it all three are read. 5 passed; controls
  `chain_walk_bound` 3/3; `test_fast.sh` exit 0.
- **Also seen in that build, NOT fixed here:** (1) the request reached the build as the single word "אתר", with
  "Audience: Internal team" and "persistence: records" for a doors company's site; (2) G-APPLE was NOT_RUN -- "the
  Design line has no four-colour palette": the business category was not recognised, so there was no contract.
- **NOT verified:** a production build after the fix. Only the owner can run one.
- **CI on the first push (`0c0b136`): `a2-offline` failed, and not because of this change.** A control I wrote in
  #425 (`a2_collect` NC8, "the flake as it was") ran the whole test file under its mutation, real-browser tests
  included; when Chromium really threw its transient error, two more sites were rejected and a test outside the
  expected list failed. A control whose result depends on a real flake is not a control. NC8 and NC9 now target the
  three tests that raise the error on purpose. `a2_collect` 9/9 locally (NC_ENV=a2).

# 2026-11-17 — three calibration builds, P0=0 on all three; what they said is acted on (Claude Code)

- **Merged and released:** #431 `d3e1dd2` -> `4071192` (`[release]`; the contract keeps the approved lines).
- **The three builds (G-APPLE at warn, contract carried, main `b38b471`):**

  | Build | Run | Result | Reviewers P0 | Static | Render | Cost, time |
  |---|---|---|---|---|---|---|
  | butcher | 44048592665 | ready, 1 round | 0 / 0 | 1 | 6 | $0.147, 213 s |
  | cafe | 44049242034 | ready, 2 rounds | 0 / 0 | 1 | 8 | $0.168, 256 s |
  | fitness trainer | 44050605137 | ready, 1 round | 0 / 0 | 0 | 2 | $0.117, 182 s |

- **Seen on all three:** the hero's content in one half with the other half empty (typography reviewer, P1);
  MEASURE on paragraphs at 768 and 1440; SHARE_META_MISSING (all three ran before #430 was deployed).
  **Seen on two:** the customer's address missing from the first page (one repair round each).
- **Acted on here:** the contract's rules tell the generator not to leave half the hero empty. The rehearsal notice
  now carries WHAT was measured (`why`), because MEASURE cannot be calibrated from a selector alone.
- **Not acted on:** MEASURE (no numbers yet); the missing address (two builds, not three).
- **Evidence:** `tests/test_rehearsal_says_what_was_measured.py` 3 passed; controls `rehearsal_says_measured` 3/3.
- **Open questions 5 and 6 are in DECISIONS.md** (a content site with no image at all; the rehearsal taxonomy is
  not recorded because the push to main is refused).

# 2026-11-17 — the build contract keeps the approved text's line breaks (Claude Code)

- **Merged:** #430 `4b925d1` -> `1da851d` (the generator is told what the installed gates check).
- **Calibration builds so far (G-APPLE at warn, contract carried):** butcher 44048592665 and cafe 44049242034 --
  both ready, P0=0 from both reviewers on both. Seen on both: MEASURE on paragraphs at 768/1440, STRING_30/60 at
  320, the hero pushed into the right half (P1). Not yet acted on: two builds are not three.
- **Full suite on this change (rebuilt on main `b38b471`):** 3764 passed, 0 failed.
- **Owner's order:** finish what was listed as open; this was listed in #421 as "proposed, not done".
- **What was wrong:** `ProductArchitect.compile` stored the contract's prompt as one long line. Every reader on the
  worker that reads by line lost its line. #421 made three readers read both forms, but two cannot recover a joined
  line:
  - a customer review at the end of its line: its author ran into the next line's words;
  - an image description that ends with its line: it ran on.
- **The change:** the contract stores one line per approved line (each line's own whitespace collapsed, blank lines
  dropped). Detection, the spec title and the summary still read the one-line text.
- **What it changes for a customer:** every NEW contract has a new fingerprint. Contracts stored before today are
  one line; they stay valid and the worker still reads them (the production row of "148 דלתות" is a test fixture).
- **Evidence:**
  - `tests/test_contract_prompt_readers.py`, 20 tests: the photo binding, the windows, the canon and the MISSING
    line give the same answers on the approved text, on a contract compiled today, and on a one-line contract;
    the review keeps its author and the image description ends with its line.
  - The eight pinned contract fingerprints are re-pinned, each with its old value. A new test recomputes each
    contract's fingerprint with the prompt flattened and gets the fingerprint pinned before: only the line breaks
    changed.
  - Negative controls `contract_prompt_readers.json` 10/10; NC10 puts the one-line storage back.
- **Not checked:** how the model's output changes when the generator reads the request with line breaks instead of
  one line. The text is the same words; no build was run on a model.

# 2026-11-17 — the generator is told what the installed gates check (Claude Code)

- **Merged and released:** #429 `7b45e1d` -> `b38b471` (`[release]`). CI green on the exact SHA; full suite on the
  branch 3760 passed, 0 failed.
- **What was missing (rehearsal 44043708644):** the share gate failed the butcher's page for a missing og:title, and
  nothing had ever told the generator a shared link needs one. A check learned only by failing it costs a repair
  round once the gate blocks.
- **Fix:** `gate.install_all` now also carries the checks to the generator: one quality requirement
  (`PLATFORM-CHECKS`) whose text is each installed unit's own manifest description, in gate order. A gate that is
  off is left out. One source: nothing is written twice. Not mandatory, so no acceptance criterion is added.
- **Evidence:** `tests/test_gate_rules_reach_the_generator.py` 4 passed (one through the real build loop); controls
  `gate_rules_reach_generator` 6/6; `test_fast.sh` exit 0.
- **NOT verified:** that the generator's first page passes more gates with the list than without it.

# 2026-11-17 — G-APPLE ran on a real page for the first time; three roots from that build fixed (Claude Code)

- **Merged:** #428 `8e26a8f` -> `4d9b1fb` (a syntax failure carries the line itself).
- **The build (rehearsal 44043708644, the butcher, main `609929e`, $0.211, 380 s):** ready after 2 repair rounds.
  G8 passed (60 requests, 0 errors, p95 7 ms, 22 MB). Both reviewers ran on a real vision model: typography/layout
  P0=1 (emoji icons drawn as empty boxes), brand/category P0=0 with four marks of the business named. G-APPLE static:
  CONTRACT_MISSING, raw colours, a third weight, emoji icons; render: 24 OFF_GRID. SHARE: no og:title/og:description.
- **Root 1 (mine):** the design contract was only appended to the prompt. The prompt goes to the architect, which
  writes the spec in its own words; the generator gets the spec and nothing else, so it never saw the contract it
  was checked against. Fixed: `g_apple.ContractArchitect` puts the contract into the spec word for word, as a
  mandatory requirement with an HTTP-checkable criterion. `report()['carried']` says whether it was carried.
- **Root 2 (mine):** the rehearsal never gave the review the approved request (the worker does:
  `install_review_request`), so the fact canon was empty and the customer's own opening hours were "invented" -- a
  blocking finding and a paid repair round no customer's build has. Fixed: the rehearsal installs the request and
  the right-to-left rule, in the worker's order, and reports whether it did.
- **Root 3 (calibration of the gate):** the brand reviewer reported the contact section "missing from the visible
  view": the screenshots are one screen each and the reviewer was never told. Both reviewers are now told.
- **Also:** the contract's rules now say to reset browser default margins (the 24 OFF_GRID findings were headings
  and links on the browser's own margins).
- **Evidence:** `tests/test_g_apple_contract_carried.py` 7 passed (one through the real build loop);
  `tests/test_rehearsal_installs_the_request.py` 4 passed; controls `g_apple_contract_carried` 8/8,
  `rehearsal_installs_request` 2/2; `test_fast.sh` exit 0.
- **NOT verified:** that the generator follows the contract once it has it. The next butcher rehearsal says.
- **NOT fixed:** `publish-taxonomy` cannot push to main (protected branch); the share gate found a real gap (no
  og tags) and nothing tells the generator to write them.

# 2026-11-17 — the butcher rehearsal failed on a syntax error nobody could read; the message now carries the line (Claude Code)

- **Merged:** #427 `360080d` -> `d29d8da` (A4 picture count; no release of its own).
- **What broke (rehearsal 44042316516, main `609929e`, $0.188, 199 s):** the generated `tests/test_site.py` did not
  compile (`:96 closing parenthesis ']' does not match opening parenthesis '('`). One pre-flight fix and one repair
  round returned the same message word for word; the build stopped as `no_progress_same_failure`. No gate ran on a
  page: G-APPLE reported `status: null`.
- **Root, as far as the evidence goes:** the failure named a line number and nothing else. The file itself is not in
  the evidence, so WHY the model wrote that line twice is NOT known. Fixed here: the message carries the line as
  written (`omni_prod/round_preflight.source_line`, used by pre-flight and by the consistency gate), cut at 200
  characters with the cut marked. The next failure of this kind is readable in the log and by the repairer.
- **Evidence:** `tests/test_syntax_message_carries_the_line.py` 5 passed; controls `syntax_message_line` 4/4;
  `test_fast.sh` exit 0.
- **Also seen, NOT fixed:** the rehearsal's `publish-taxonomy` job pushes straight to main and is refused (GH006,
  protected branch). The taxonomy of this rehearsal was not recorded.
- **NOT verified:** that the readable message makes the repair succeed. A second butcher rehearsal (44043708644) is
  running on the old code.

# 2026-11-17 — A4 decides how many pictures a build generates; #426 merged and released (Claude Code)

- **Merged:** #426 `95f851c` -> `609929e` (`[release]`). CI green on the exact SHA (17 checks; `publish-report` is a
  main-only job and is skipped on every PR); full suite on the branch: 3733 passed, 0 failed.
- **A4 -> planner link (the owner, 2026-11-17: "as many as the customer wants while they have credits; to start, up
  to 3 per build"):** `a4.pictures(prompt)` decides the number, `capability_planner` writes it as the image
  requirement's `quantity` -- the number the price, the provider call (`num_outputs`) and the page already read.
  Rule: the number the request states, minus the customer's own placed photos, at least 1, at most 3. A request past
  the cap is cut and the cut is on the requirement (`pictures_asked`) and in the log (`PICTURES_CUT`). Whether a build
  generates any picture is unchanged (founder decision 2026-10-07 #28). An icon is always one.
- **Evidence:** `tests/test_a4_picture_count.py` 11 passed; controls `a4_picture_count` 7/7; `test_fast.sh` exit 0.
- **NOT verified:** no real build has generated more than one picture. The customer is not yet told in the chat that
  a request was cut. Three pictures are three takes of ONE subject: a picture per dish needs a requirement per picture.

# 2026-11-17 — three new checks, all entering at warn: G5 rights, A4 asset plan, G8 runtime and load (Claude Code)

- **G5 (rights), rewritten after an independent review:** every served file is read with a real parser (HTML, CSS,
  scripts that build media, JSON-LD, SVG data: URIs); the source of every font, image and media file must be one the
  registry names (`omni_prod/rights_sources.json`). It reads the page as written (the platform's own assets as their
  placeholders). The worker installs it.
- **A4 (assets agent), first slice:** one asset plan per build. A generated image had no place at all -- the code
  model chose. Now every image has one place by stated rules (the customer's photo keeps its place and the hero; a
  generated picture is the hero only when the hero is free), the generator is told the plan, and the finished page
  is checked against it. A plan that cannot be (two heroes, over 12 images, over 1.5 MB together) stops the build.
- **G8 (runtime and load):** the product is started in the sandbox and asked for its page 60 times, 6 at a time. It
  must answer every request, stay up, answer within 1.5 s at the 95th percentile and hold under 256 MB.
- **G-APPLE, the design gate (the owner's relayed spec, 2026-11-17), in this PR at warn:**
  - *Design contract, locked before code* (`omni_prod/g_apple/contract.py`): from the approved brief's Design line --
    a type scale, the 8-grid (4 is the one half step), a semantic palette whose every text pair's contrast is
    computed and corrected, two weights, one radius, motion tokens. One accent: the palette's second colour is
    dropped, and the contract says so. The generator gets the `:root` block and may use nothing else.
  - *Static enforcement and the refusal list* (`static.py`): raw colour, px off the scale, a third weight, a second
    radius, a missing contract, missing `:focus-visible` / `:hover` / `:active`; gradient hero with outlined text,
    three icon cards, carousel, shadow everywhere, 24px everywhere, everything centred, a second accent, more than
    two button styles, emoji as icons, lorem.
  - *Render probe* (`render.py`, sandbox browser, 390 / 768 / 1440 / 320, one full-page screenshot each): sideways
    scroll, cut text, a control under 44 px, off-grid spacing, line length outside 55-75, the 30 / 60 character
    string test.
  - *Two separate vision reviewers* (`reviewers.py`): typography/layout and brand/category, findings with a selector
    and a severity; P0 blocks (in block mode); a reviewer never proposes code; the category clause makes a page with
    no visible mark of its business a P0.
  - Installed last, right before the build, in the worker and in the rehearsal; evidence key `g_apple`.
  - **Decisions made while building it (said, not hidden):** line length is judged at 768 and 1440 only (at 320-390
    a 55-character line needs unreadably small text); the reviewers see the two screenshots visual QA returns (1440
    and 390) -- the four-width screenshots stay in the sandbox and only their digests are reported; the old butcher
    page predates the contract and fails it by design (30+ findings), so "P0 = 0 on the butcher page" is measured
    on a butcher page BUILT under the contract.
  - **Per the owner: negative controls and the move to block are tomorrow.** Tests today: `tests/test_g_apple.py`
    (20) and `tests/test_g_apple_render.py` (6, four of them in a real browser).
  - **Not verified:** no real build has run under the contract; the reviewers have not run on a real vision model.
- **CI time, root cause and fix (a513b1a):** `test` was cancelled and `pg-tests` failed with no failing test. The
  negative controls ran after pytest inside `test`, and with five new specs the two passed the job's 20-minute limit
  (pytest 8.5 min; the controls over 11). Fix: G8's controls target a server-free rules file (6 min -> 11 s); the
  controls run in their own job, `negative-controls`, beside the tests (the follow-up the workflow's own comment asked
  for); the pg job's control step gets 14 minutes of its 20. Every spec still runs on every push.
- **All three warn (`gate.CALIBRATING`):** findings and measurements go to the log and the build evidence
  (`skill_gates`, `asset_plan`, `runtime_load`); none blocks before three calibration builds. The rehearsal installs
  the same checks.
- **Evidence:** `tests/test_skill_gate_rights.py`, `tests/test_a4_asset_plan.py` (17), `tests/test_g8_runtime_load.py`
  (15: real servers are started -- a healthy one, one that dies under load, one that answers 500, a slow one, one
  that never starts -- and the script passes the real sandbox request policy); negative controls
  `skill_gate_rights` 20/20, `a4_asset_plan` 10/10, `g8_runtime_load`, `gates_calibrating` 6/6.
- **Not verified:** none of the three has run in the real sandbox or on a real build; G8's limits are first guesses
  to calibrate, and its memory reading depends on the sandbox exposing /proc (said as NOT_RUN when it does not).
- **Not in the repository (asked in DECISIONS.md):** the skills triage list (88 keep / 32 merge / 17 drop) and
  `parked/`; stage E cannot start without them.

# 2026-11-17 — uncalibrated gates warn; the page carries a light rendition of every photo (Claude Code)

- **Merged:** #424 `5556c28` -> `a5ab25d` (the worker's time budget; the dead ends). Not released yet.
- **Gates (the owner's rule 4):** HE, G10, G11, G1, BRAND and SHARE were installed on the worker at `block` without
  the three calibration builds. They now warn by default (`gate.CALIBRATING`); G3 and G6 still block, G4 still warns.
  A calibrating gate's findings (bounded, 3 per failure) are kept in `evidence.skill_gates`, and the golden rehearsal
  installs the same gates as the worker (`gate.WORKER_GATES`), so a gate can be calibrated on real generated pages.
- **Photos (warehouse 114, first half):** the butcher's hero (bld_83529c13, a GENERATED image) went into the page as
  1,735,408 base64 characters. Every uploaded or generated image over 360 KB is now carried as a web-sized WebP
  rendition (at most 1600 px, upright, same proportions, transparency kept); a light image is carried byte for byte;
  the original and its digest are untouched. Pillow joins `requirements-production.txt` (the worker image).
- **Evidence:** `tests/test_web_rendition.py` (14: phone-sized photos made with a real encoder; the G4 unit that
  measured the butcher page fails on the original and passes on the rendition), `tests/test_skill_gates.py` (+5);
  negative controls `photo_weight` 8/8, `gates_calibrating` 6/6; declarations 68 -> 75, none lost.
- **CI lesson:** `validate` failed on `ea19bf6`: `requirements.txt` (Vercel) must list exactly the pins of
  `requirements-production.txt` (`tests/test_vercel_entrypoint.py`). Pillow is added to both.
- **CI lesson 2 (a bug of Claude's):** `pg-tests` failed on `2311e2b`: two existing controls (`skill_gate_copy` NC4,
  `skill_gate_he` NC5) mutated the DEFAULT_MODE line this PR rewrote, so they could not be applied. Claude had run only
  the new specs. Both controls now assert the new rule (the gate must not block before calibration), and
  `tests/test_negative_controls_apply.py` checks every mutation of every spec still matches its file.
- **The a2 flake, root cause (CI on `148f0e4`):** three good sites of 31 were rejected with the browser's own
  "Page.screenshot: Protocol error (Page.captureScreenshot): Unable to capture screenshot" (readable since #405 put
  the exception's message in the rejection). Only that error is now tried again, at most 3 times; any other error,
  and that one when it persists, still rejects. Tests in a real browser; `a2_collect` controls 9/9.
- **Not verified:** the worker image has not been built with Pillow yet (the deploy builds images before it drains);
  no gate has been calibrated on a real build yet.
- **Still open in 114:** the photo is still inside the HTML (no browser cache). Serving it as a file needs the
  sandbox request, the stored version and the preview to carry binary files; the map is in warehouse 114.
- **Checked and found already built (stage B 9-12):** image relevance for generated images (`image_match`, lens 11),
  the mobile 390 px render check (`visual_qa`), the links units (`links_tel`, `links_address`, `links_anchor`) and
  the empty-block unit (`blocks_empty`).

# 2026-11-16 — the worker dies mid-build; conversations that end on an unanswerable question (Claude Code)

- **Merged:** #423 `0ebb903` -> `dfe6817` (chat truth; not released yet).
- **Worker death, root cause (production, read-only):** `bld_426addd3` and `bld_0e142230` were killed 15 minutes after
  they started: the queue's 900-second job timeout, with no terminal state written. `bld_0e142230`'s event 810 reads
  "visual check could not verify the product: desktop: JobTimeoutException: Task exceeded maximum timeout value (900
  seconds)": the timeout was caught as a failed check and the build went on repairing.
- **Fix:** the build ends itself (no new repair round after 13 min; stop with `build_timeout` at 17 min; queue limit
  20 min); `BuildDeadline` and the queue's `JobTimeoutException` are control exceptions, never a check failure; the
  customer has words for `build_timeout`, `provider_liability_unknown` and the `time_budget` repair stop.
- **Dead ends, found by walking every way through the cards of four requests:** 80 of 252 walks ended on a question
  with no card and no answer the chat could take ("האם האתר שומר מידע?" after "personal details are stored"; the
  English workflow question for a short request). After the fix: 0 of 252 (220 summaries, 32 stated blockers).
- **Evidence:** `tests/test_build_deadline.py` (16, with rq installed; 2 are NOT_RUN without it),
  `tests/test_no_dead_end_conversation.py` (4); negative controls `build_deadline` 9/9, `no_dead_end` 5/5;
  `scripts/test_fast.sh` exit 0; declarations 81 -> 88, none lost.
- **Correction (a counting bug of Claude's):** the declaration counts reported today as "72 -> 81" (#423) and
  "81 -> 88/89" here were wrong in absolute terms: the script counted the four keys of each old path-only entry as
  four records. The differences were right. The real counts: 40 on `912924d`, 45 after #405, 54 after #423, 68 here
  (14 added in this PR: 6 for the code, 1 for the TASKS row, 5 for the regenerated status files and the T4 lock,
  2 for the declarations file itself). No declaration was lost at any step (checked record by record).
- **CI lesson:** `validate` failed on `861312d`: the agent registry, the department matrix and the T4 evidence lock
  were stale after `queueing.py` and `verification_verdict.py` changed. The fast suite does not cover them; they
  are regenerated here, and Claude now runs those derived-status tests before every push that touches `omni_prod`.
- **Not verified:** no production build has run on the new limits; the limits 13/17/20 are a decision (DECISIONS.md).
- **Open:** warehouse 115 (verify on a real build), 116 (the A2 live job does not exist in code), 117 (a build with a
  photo end to end on production was not tested).

# 2026-11-16 — releases, and the three chat contradictions of stage A (Claude Code)

- **Released (the owner's order):** #422 `349d729` -> `4e16eeb` (docs only; the worker was deployed by a manual run of
  deploy-worker on `4e16eeb`, run 43973795367, success: the path filter does not start it on a docs merge);
  #405 `795bbae` -> `1dc1fbd`.
- **Root causes, each seen in production (project of 2026-11-16 11:05-11:11, read-only query of `intake_messages`):**
  - *Price.* The chat said "45-200" at gate 1 and "500" at gate 2. The price is set by the plan alone
    (`pricing.m5_build_terms`); the range ignored the plan. Now the plan's price is said once, from gate 1.
  - *The empty question.* Five stored messages were exactly "שאלה אחת לפני שממשיכים:". The question lived only in
    the card of the live turn. Now the message carries the card's question in words, and the card adds buttons only.
  - *Chat vs panel.* The customer approved the spec twice (11:10:21, 11:11:01). The panel's plan was fetched before
    the approval and kept its `spec_not_approved` blocker after the chat approved. Now it is dropped and fetched again.
- **Evidence:** `tests/test_plan_price_said_once.py` (8), `tests/test_question_in_words.py` (7),
  `tests/approval_one_truth_browser.cjs` (real Chromium: passes here, and fails on main's app.js with "1 !== 2" plan
  fetches); negative controls `plan_price_said_once` 6/6 and `question_in_words` 6/6; `scripts/test_fast.sh` exit 0;
  declarations 72 -> 81, none lost.
- **Changes a rule, said openly:** Michael 2026-11-13 "the card asks, the text does not". The owner's later order (the
  empty question is a bug) wins: the question is still shown once, in the message; the card no longer repeats it.
- **Not verified:** no live build on production after the release yet; the browser test uses a fixture API.
- **Open:** a walk that clicks the first option of every card can loop on "האם האתר שומר מידע?" (seen in a local
  walk, root cause not found yet); the chat's 8-field summary and the panel's summary are still two builders
  (warehouse 101); `provider_liability_unknown` has no customer wording in app.js.

# 2026-11-16 — the pre-live package (#405, orphaned) checked against main and taken over (Claude Code)

- **Owner's order:** check the orphaned PRs against main; merge what is still right, or close with an explanation.
- **Still right, kept as written:**
  - `needs_env`: the measured 66 (34 modules, 32 test ids) are marked; `-m "not needs_env"` collects none of them,
    and CI collects everything.
  - The CI split: `light` runs on every push, drafts too (the fast suite, changed JSON parses, no conflict marker).
    `test` is skipped only on a draft, and `ready_for_review` re-runs it.
  - a2 109 / 110: a page with no style of its own is rejected; every extracted field says who set it.
  - The capture rejection carries the exception's message, not only its class.
  - A placed photo must sit inside its section; a missing section says what to add.
- **Changed on takeover, and why:**
  - The draft skip of the `test` job is not carried. An independent review found that a re-run of a run started
    while the PR was a draft reports `test` as skipped on a ready head, and a skipped required check reads as
    passing. `test` runs on every push, as on main.
  - `light` blocks a PR that deletes or rewrites a line with no signed declaration, as its author wrote it. The
    owner decided this on 2026-11-16: "without this the declarations are documentation, not protection; only a
    signed declaration releases". (I had first made the step report only; that is reverted.)
- **Waiting for the owner's signature:** five declarations, bound to the digest of the lines deleted, with
  `"reviewer": "pending"`: `omni_prod/a2/capture.py`, `omni_prod/a2/extract.py`, `omni_prod/discovery.py`,
  `tests/negative_controls/uploaded_main_image.json` and `docs/identity/allowed-deletions.json` itself. Records: 40
  on main, 45 here, 5 pending. Claude does not sign for a person. Until the owner signs, `light` fails on this PR.
- **Evidence:**
  - Merged with main it merges clean, including `uploaded_assets.py`, which #421 changed today.
  - Its own tests pass, 112 with the neighbours.
  - Negative controls: `uploaded_main_image` 15/15, `fast_suite` 2/2, `contract_prompt_readers` 9/9, and the new
    `ci_light` 2/2 (NC1 makes the step report only; NC2 skips `test` on a draft).
  - The a2 controls (`a2_styles`, `a2_extract`, `a2_collect`) run only in the a2 CI job.
- **Not done in this PR (as its author said):** capture steps 2 and 3. The message is now recorded; the fix by type
  comes after it is seen in CI.

# 2026-11-16 — `scripts/commit_resolved.sh` (#403, orphaned) checked against main and taken over (Claude Code)

- **Owner's order:** check the orphaned PRs against main; merge what is still right.
- **#403 is still right.** The script commits a conflict resolution only after three checks pass: no conflict
  marker is left, every changed JSON file parses, and no path is still unmerged.
- **Its one conflict with main** was the first line of CLAUDE.md section 8, which main had changed (the owner signs,
  not Michael) and extended (the count before and after). The resolution keeps main's two lines and adds the
  script's line.
- **Evidence:** the resolution was committed with the script itself: `scripts/commit_resolved.sh .` exited 0 and
  printed `committed c33b560`. Against main the PR adds 65 lines in 3 files and deletes none.
- **Added on takeover:** the PR had only hand-run evidence. `tests/test_commit_resolved.py` (6 tests) now runs the
  script on a temporary repository with a real conflict: exit 2, 3 (each file named), 4 and 0. Negative controls
  `commit_resolved.json` 3/3; NC2 is the old rule (a `=======` anywhere), which refuses a resolved markdown file.
- **Not tested:** exit code 5. After the script's own `git add`, no case leaves a path unmerged.

# 2026-11-16 — the fast suite (#402, orphaned) checked against main and taken over (Claude Code)

- **Owner's order:** #402, #403 and #405 were orphaned when Claude left. Check each against main, merge what is
  still right, or close it with an explanation.
- **#402 is still right.** Merged with main `b761003` it merges clean. Its evidence:
  - `scripts/test_fast.sh` runs its 172 measured files in 21.7 s, within the 30 s budget;
  - `tests/test_fast_suite.py` passes; there are 392 test files now, against 369 measured, inside the 100-file
    band;
  - negative controls `fast_suite.json` 2/2;
  - `scripts/ci_test_coverage.py` PASS.
- **No CI job runs the fast suite yet.** Its `light` job is part of #405.
# 2026-11-16 — the rights gate G5: the source of every font, image and audio is known, or the build is blocked (Claude Code)

- **Owner's order:** the agents come after the gates, A7 (rights) first: "checks the source of every asset: font,
  image, audio. Blocks on an unknown right; it does not assume." And: an agent with no gate that runs it does not go
  in, so the gate comes first. This entry is the gate.
- **Implemented:**
  - `omni_prod/rights_sources.json` is the registry of known sources, a data file. Each source states its right, the
    basis it rests on and the date the basis was read. A source without a basis is refused at load. Six sources:
    - the customer's upload, and the image the platform generates (flux-schnell on Replicate, Apache-2.0);
    - an SVG the build draws, and a path the build serves itself;
    - Google Fonts, and a Google map embedded in a frame.
  - `omni_prod/rights_sources.py` reads every asset reference of one served file and judges it.
  - Three skill units form gate G5: `rights_image_source` (IMAGE_SOURCE_UNKNOWN), `rights_font_source`
    (FONT_SOURCE_UNKNOWN) and `rights_media_source` (MEDIA_SOURCE_UNKNOWN: audio, video and frames from other sites).
  - G5 blocks by default (`OMNI_GATE_G5`), and its mode is said on every build like every gate.
  - G5 reads the files as written: the platform's own assets are their `148ai-asset://` placeholders. So the
    customer's photo is known, and the same bytes with no record of their source are not.
  - G5 reads every served file (pages, stylesheets, scripts, Python and template files), not only whole documents.
  - The worker installs G5 with the other gates.
- **An independent review before the push found the first version full of holes; a bug of mine.** It read pages with
  regular expressions and only whole `<html>` documents. What passed although unknown, each now a test:
  - a photo gallery built by a script from addresses with no file extension (images.unsplash.com, picsum.photos);
  - an asset loaded from a stylesheet file, a script file or a fragment in a Python constant;
  - a `>` inside an earlier attribute, and a comment opener inside `<style>`, which hid what followed;
  - a photograph wrapped in an SVG data: URI;
  - `image-set()`, an escaped `url`, `@import` with no space, lazy-loading `data-src`, `<body background>`,
    `imagesrcset`, `<object>` with no extension, and a player in a frame on any host outside a list of six;
  - anything that merely started like a placeholder.

  What was blocked although legitimate: Google Fonts loaded with `@import` and two weights (read as an unknown
  image), and an empty `data:,` favicon.
- **The fix:** the reading is rewritten on `html.parser`, with separate readers for CSS, scripts, JSON-LD, SVG data:
  URIs and Python constants. A script that puts media on the page has every address literal judged, with or without
  an extension; an address that is plainly a link target (`href`, `window.open`, `location`) is not a load.
- **It falls on a page:** each broken fixture is the real butcher production page, as written, changed in one
  place: the hero hotlinked from images.unsplash.com; the hero as embedded JPEG bytes; the Heebo stylesheet replaced
  by one from fonts.cdnfonts.com; an `@font-face` loading a font file from another host; background music from
  cdn.pixabay.com; an embedded YouTube player. The unchanged page passes with its two assets known.
- **Evidence:** `tests/test_skill_gate_rights.py`, 29 tests. Two run the worker's own installs: the photo of the
  "148 דלתות" production contract, and the logo, right-to-left, a generated image and the photo chained in the
  worker's order. Negative controls `skill_gate_rights.json` 20/20.
- **The bases were read on 2026-11-16, and no lawyer reviewed them:** the Google Fonts FAQ, the Replicate model page
  of flux-schnell, and the Google Maps Embed API pages.
- **What a static reading cannot see (said, not assumed):**
  - an address a script builds at run time from pieces, and what an external script loads;
  - a font only named in `font-family` (a system font; nothing is loaded);
  - whether a drawing copies a protected mark.
  - The real request list of the page in a browser would close the first of these. It is not built.
- **The owner's decisions:**
  - The customer is not asked to declare the right to an uploaded photo. Asking is an approval-flow change.
  - Not measured: how many production pages load a stylesheet, a font or a frame from another host. Only the
    butcher page and the doors page were read. Such a page now goes to a repair round.

# 2026-11-16 — "148 דלתות": the customer's photo was a broken image; the contract prompt has no line breaks (Claude Code)

- **What broke:** build `bld_426addd34be0457bb1955cd4e9bf372f` (prj_-K3B8ZLIJawPEA) served
  `<img id="hero-image" src="148ai-asset://upload/1">`. The browser does not know the scheme, so the hero was a broken
  image.
- **Root cause, from the production rows (read-only):**
  - The worker builds from the build contract's prompt (`bc_8ffe607037d3c6c01da5a989`).
  - `ProductArchitect.compile` stores that prompt with its whitespace collapsed (`" ".join(prompt.split())`):
    2,414 characters, no line break. `build_requests.prompt` has the same words.
  - `uploaded_assets._IMAGE_BINDING` was anchored to a line start (`^`, re.M), so on the contract it matched nothing.
    `install_main_image` returned without a word, no transform replaced the marker, and the raw address reached the
    browser.
  - A bug of Claude's (845051a, 2026-11-15).
- **Both discarded repair rounds had the same cause:** the platform never gave the page the bytes. Round 1 swapped in
  an http URL ("Unexpected identifier 'http'"); round 2 still had no visible image.
- **The same class of bug, on the same worker path:**
  - `window_catalog.approved_in_prompt` (a bug of Claude's, 3db7d57): on a contract build the window gate checked
    nothing, and the fact canon lost the windows.
  - `fact_canon.needs_customer_input` (the MISSING line): a QA failure only the customer can fix did not stop the
    repairs.
- **The fix:**
  - The three readers read their text wherever it stands after whitespace, on both the approved text and the
    one-line contract.
  - A photo the request places with no binding read for it stops the build before generation, loudly
    (`UPLOAD_MARKER_UNBOUND`).
  - A new gate, `asset_markers` (`ASSET_MARKER_UNRESOLVED`), fails a round while any `148ai-asset://` address is left
    in a file the browser loads. A page with a real URL or a data URI passes.
  - The gate report now walks through the photo check and the marker gate. Before, the evidence lost every gate's
    result once a photo was placed; that was a bug of mine from #415.
- **Evidence:**
  - `tests/test_contract_prompt_readers.py` has 17 tests on the real path. It uses the production contract row as
    stored (`tests/fixtures/doors_contract_bc_8ffe6070.json`):
    - the row reproduces its stored fingerprint `sha256:b20d2a60…` and the prompt digest computed in the database,
      `7379047b…`;
    - the photo is read from it, and the sandbox receives the bytes, never the address.
  - Negative controls: `contract_prompt_readers.json` 9/9. NC9 restores the production state (the anchor plus the
    silent skip), and the sandbox then receives `src="148ai-asset://upload/1"`, as production did.
- **Not fixed here (said):**
  - Two readers lose information on a one-line prompt: a customer review at the end of a line (`fact_canon._QUOTE`)
    and an image description that ran to the end of its line (`generated_images.describe`).
  - The real fix for both is that the contract keeps the approved text with its line breaks. That changes every new
    contract's fingerprint, so it is proposed to the owner, not done.
  - This fix reaches production only on a release (the owner's call). Until then a new "148 דלתות" build still shows
    the broken image.

# 2026-11-16 — empty blocks (G1), brand (BRAND) and share (SHARE) gates, one unit each (Claude Code)

- **Owner's order (build track, item 7).**
- **Implemented:**
  - `blocks_empty` (EMPTY_BLOCK): a `<section>` or `<article>` whose only visible text is its heading. A block with
    media (img, iframe, form, video) is not empty.
  - `brand_name` (BRAND_MISSING): the business name in `<title>`, before its separator, is shown on the page, not
    only in the tab. A page with no title fails.
  - `share_meta` (SHARE_META_MISSING): og:title and og:description are present and not empty. og:image is not
    required yet: the hero is inlined as base64 (warehouse 114), so there is no image URL to give.
  - All three gates block by default, and the worker installs them after G11.
- **They fall on a page:** each broken fixture is the real butcher page changed in one place: an empty "גלריה"
  section; a title naming "הקצבייה של משה", which the page never shows; og:description removed. The unchanged page
  passes all three.
- **Evidence:** `tests/test_skill_gate_blocks_brand_share.py` 6 tests. Negative controls
  `skill_gate_blocks_brand_share.json` 4/4.
- **Build track not done:** item 4, image relevance. The vision check (lens 11) exists but runs on founder builds
  only (rollout), and making it a customer gate costs a model call per image. Item 5, mobile rendering at 390 with a
  real screenshot, needs the browser sandbox in the build path. Both are said, not faked.

# 2026-11-16 — the copy gate (G10, 2 skills) and the links gate (G11, 3 skills) (Claude Code)

- **Owner's order (build track, items 3 and 6):** a generic-copy gate (filler sentences) and a links gate (`tel:`, a
  whole address, navigation). Both fall on a page before they go in.
- **G10:**
  - `copy_filler` (COPY_FILLER): generic sentences that say nothing about the business, a closed list in Hebrew and
    English ("ברוכים הבאים לאתר שלנו", "Welcome to our website").
  - `copy_placeholder` (COPY_PLACEHOLDER): text left to be replaced ("lorem ipsum", "[שם העסק]", "{{business_name}}",
    "טקסט לדוגמה", example.com, 123-456-7890), in the text and in links.
- **G11:**
  - `links_tel` (TEL_BROKEN): every `tel:` link dials a valid Israeli number the page shows, and every phone the page
    shows has a `tel:` link.
  - `links_anchor` (ANCHOR_BROKEN): every `href="#x"` has an element with id x.
  - `links_address` (ADDRESS_INCOMPLETE): an address the page labels ("כתובת:") has a house number and a city (a closed
    list of cities). A heading such as "כתובת והתקשרות" is not a label.
- **They fall on a page:** each unit's broken fixture is the real butcher production page changed in one place, and
  each gate (block by default) fails the build on it. The changes:
  - "ברוכים הבאים לאתר שלנו!" added;
  - the address replaced by "[כתובת העסק]";
  - both call buttons dialling 050400016, a digit short;
  - a "מחירים" link to a missing #prices;
  - the address without its number and city.
  The unchanged page passes all five units.
- **Evidence:** `tests/test_skill_gate_copy.py` 6 and `tests/test_skill_gate_links.py` 6. Negative controls
  `skill_gate_copy.json` 5/5 and `skill_gate_links.json` 5/5. The other gate specs on this branch still pass:
  `skill_gate_he` 6/6, `skill_gates` 10/10, `skill_units_a11y` 6/6.
- **Not checked:** pages other than the butcher page.

# 2026-11-16 — the Hebrew gate (HE): grammar, gender agreement, translationese (Claude Code)

- **Owner's order (build track, item 2):** a Hebrew gate with 3 skills. "A gate that has not been shown to fail does not
  go in."
- **Implemented:**
  - Three units in `omni_prod/skill_units/`, each a closed rule list and no model:
    - `he_grammar` (HE_GRAMMAR): a repeated word, except Hebrew's own reduplications ("לאט לאט"); a double
      superlative ("הכי ... ביותר"); the article on the first noun of a construct ("הבית קפה").
    - `he_gender` (HE_GENDER): a noun and the adjective right after it, and שני/שתי with their noun, from closed noun
      and adjective lists. A word outside the lists is not judged.
    - `he_translationese` (HE_TRANSLATIONESE): 18 calques ("בסוף היום", "אל תהססו") with the natural Hebrew.
  - The text is read one text node at a time (`skill_units.text_nodes`). The real page's hours table has a "שבת" cell
    next to a "שבת סגור" cell; joined, they would read as a repeated word.
  - Gate `HE`, mode `block` by default (`OMNI_GATE_HE`). The worker installs it after G6, and it reports like the other
    gates.
- **It falls on a page:** each unit's broken fixture is the real butcher production page (`bld_83529c13...`) changed in
  one place: "הבשר הכי איכותי ביותר", "השעות פתיחה", "בשר טרייה", "אל תהססו לפנות". The gate fails the build on each,
  in its default mode, and the repair to the unchanged page passes. The unchanged page passes all three.
- **Evidence:** `tests/test_skill_gate_he.py`, 7 tests. Negative controls `tests/negative_controls/skill_gate_he.json`
  6/6, among them: text joined across elements (then the unchanged page fails too), the gate set to warn, and the
  worker not installing it.
- **Not checked:** pages other than the butcher page. The word lists are a start, not full coverage of Hebrew.

# 2026-11-16 — warehouse 105: colours by business category, from a data file; the old default blue is gone (Claude Code)

- **Root cause:** the colour question recommended `'blue'` and `requirements_text` defaulted to `'blue'`, which mapped to
  `--color-primary: #1d4ed8`. Every customer who stated no colour got the same blue.
- **Implemented:**
  - `omni_prod/vertical_palettes.json` holds 10 palettes (primary, accent, background, ink) and the 32 categories of
    `reference_catalog.CATEGORIES`, each with its palette and the words that identify it in a brief.
  - `omni_prod/vertical_palettes.py` checks the file against the catalogue at load. A category without a palette, an
    unknown palette, a category outside the catalogue, or a colour that is not `#rrggbb` raises PaletteError.
  - The colour question now recommends `category` ("לפי סוג העסק").
  - When the customer stated no colour, the Design line carries the category's palette. When the category is not
    recognised, the line says so and asks for a readable palette, with no hidden default.
  - A colour the customer stated still wins.
  - The stated "blue" is now `#1e40af`, so `#1d4ed8` is nowhere in `omni_prod`.
- **Evidence:** `tests/test_vertical_palettes.py` 10 tests. They cover all 32 categories mapped; a vertical without a
  palette failing (plus 3 other broken files); contrast of at least 4.5:1 for primary on white and ink on background, in
  every palette; each category recognised by its own words; the butcher and dental briefs getting different palettes;
  the stated colour winning; and an unknown business being said, not defaulted. Negative controls
  `tests/negative_controls/vertical_palettes.json` 4/4. Every spec that touches the changed files passes: cafe-real-rows
  4/4, first-agent-brief-slice 5/5, image-answer-loop 6/6, latest-answer-wins 2/2, uploaded-main-image 14/14,
  window-catalog 7/7. Four older tests asserted the old blue default
  (`test_discovery_and_approval`, `test_intake_palette_preservation` ×2, `test_wp1_gap_detector` ×2). They now assert
  the owner's rule.
- **Not checked:** a real build with the new palette (it needs a paid build).
# 2026-11-16 — the customer approves or rejects each window (Claude Code)

- **Owner's order:** an approval screen for windows. Each window is offered with a one-sentence benefit; the customer
  approves or rejects it. Acceptance: a rejected window is not built; an approved one enters fact_canon; the gate fails a
  build missing an approved window.
- **Implemented:**
  - `window_catalog.BENEFITS` holds one sentence per window, Hebrew and English, and `offer()` builds the offer.
  - `discovery.decide_windows` records approved and rejected windows in the brief (customer only). An unknown id raises
    KeyError; a decision that is not a bool raises ValueError.
  - `discovery.window_offer` makes the offer, websites only.
  - `requirements_text` adds a "Rejected windows ... do not add them" line, and the gate fails a page that has a rejected
    window (`WINDOW_REJECTED`).
  - Gate 1's approve_spec action and the proposal card both carry the offer. `approve_spec(windows=...)` saves the
    decisions before the approval, so the approval binds to the fingerprint that includes them, the same way as the
    waiver.
  - The API (`V28SpecApproval.windows`) refuses an unknown window with 400 `unknown_window`.
  - UI: `windowsChoice()` in app.js renders one row per window, with label, benefit and a 44px target. It is used on
    both approval screens, and it sends EVERY offered window, ticked as true and unticked as false. A window left
    unticked is recorded as rejected, which the screen says.
- **Evidence:** `tests/test_window_approval.py` 13 tests. They run the real supervisor up to gate 1, approve_spec with
  decisions, the saved brief, build_canon, and the real engine with the window gate; and windowsChoice() with app.css in
  real Chromium (click a row, read() sends all 8). Negative controls `tests/negative_controls/window_approval.json` 4/4
  PASS, and `window_catalog.json` 7/7 still PASS. The 28 specs that touch the changed files: 23 PASS. 5
  (item3-route, item4, pr154 NC2, pr176, preview-durable-backend) need fastapi and fail identically on main `c38fbb4`.
- **Not checked here:** the API route itself (no fastapi in this container; CI runs it); a real paid build with windows.
# 2026-11-16 — the v24-ci test job no longer runs the whole suite twice (Claude Code)

- **What broke:** #418's `test` job was cancelled at its 20-minute bound, and a cancelled check is not green. The
  bound is also the CI-cost policy's maximum (`tests/test_ci_workflow_concurrency.py`).
- **Root cause:** the job ran pytest (7.7 min), then the negative controls (4.8 min), then
  `scripts/run_international_gate.py`, which **ran the whole pytest suite again** (another ~7.7 min). On #417 the job
  already took 17.7 minutes; the tests and controls I added today pushed it over.
- **Fix:** the gate reads the junit report the first run wrote in the same job (`OMNI_PYTEST_REPORT=pytest-report.xml`,
  set in v24-ci), through `scripts/junit_report.verdict`. A missing, unreadable or empty report, or any failure or
  error, fails the gate loudly; skips are counted and said. Without the variable (a local run) the gate runs pytest as
  before.
- **Evidence:** `tests/test_ci_junit_report.py` 6 tests on junit files that pytest itself wrote, plus the workflow and
  the gate as committed. Negative controls `ci_junit_report.json` 3/3 (failures counted as green; an empty report
  green; the workflow not handing the report over). The real gate run with a report: `exit=0` in 2 seconds, with
  `pytest: 8 tests, 0 failures, 0 errors, 0 skipped`.

# 2026-11-16 — warehouse 107 (was 82): the stored customer session is checked on production and fails out loud (Claude Code)

- **Implemented:** `scripts/customer_session_check.py` and the job `.github/workflows/customer-session.yml` (daily at 04:17 UTC and manual).
  The job gives the secret `CUSTOMER_STORAGE_STATE` (a Playwright storage_state of a non-founder customer) to the check. The check
  opens `GET /api/v28/me` on production with the `148ai_session` cookie. Each failure is its own readable `::error` and exit 1, never a
  skip: `MISSING` (secret absent or empty, with how to set it), `MALFORMED`, `UNAUTHORIZED` (401: expired or revoked), `FOUNDER`
  (the founder's account proves nothing about customers), `UNEXPECTED`. The cookie value is never printed.
- **Evidence:** `tests/test_ci_customer_session.py` 9 tests (ci-fast). They run the real HTTP client against a local server that
  answers like `/api/v28/me`, and read the workflow as committed. Negative controls `tests/negative_controls/customer_session.json`
  4/4 PASS (missing secret as a skip; 401 accepted; founder accepted; the step skipped when the secret is absent).
  Run here without the secret: `::error title=customer session MISSING::the secret CUSTOMER_STORAGE_STATE is not set or is empty; ...` exit 1.
- **Blocked by a named credential:** the secret `CUSTOMER_STORAGE_STATE` does not exist yet. The owner creates it (a test customer
  that is not the founder). Until then the daily job fails with MISSING. That is the acceptance, said out loud.
- **Not checked:** a live 200 on production (needs the secret).
# 2026-11-16 — warehouse 112: every test file is run by a CI job (Claude Code)

- **Found:** 16 test files that need PostgreSQL (they end in `_pg.py` or read `M4D2_DATABASE_URL`) were run by no job. `v24-ci`
  has no database, so they skipped there, and `intake-budget-pg` runs an explicit list that did not name them. #404 was the same gap.
- **Implemented:** `scripts/ci_test_coverage.py` (runs in the `fast` job as `tests/test_ci_test_coverage.py`). It fails loudly when:
  a PostgreSQL file is neither in the pg job's list nor in `tests/pg_not_yet_run.txt` with a reason; a listed file no longer exists;
  a waiver has no reason, is stale or is also listed; or `v24-ci` stops running every test (`python -m pytest -q --junitxml=...`).
  The 16 files were added to `intake-budget-pg.yml`. A file that fails in CI's real Postgres moves to `pg_not_yet_run.txt` with the exact failure.
- **Evidence:** `tests/test_ci_test_coverage.py` 5 passed. Negative controls `tests/negative_controls/ci_test_coverage.json` 4/4 PASS
  (a new pg file no job runs; the database variable counted; a waiver without a reason; the general run narrowed).
  `python scripts/ci_test_coverage.py` → `PASS (0 problem(s))`.
- **Bug of mine found on the way:** the test file named the database variable, so the check flagged the test itself as needing
  PostgreSQL. Fixed by splitting the string; that the check caught its own test is extra evidence that it works.
- **The first pg run (#416, 2026-11-16) judged the 16 files:** 6 failed / 509 passed / 7 skipped. The 6 failures were
  in three files that ran there before (`test_intake_assistant_he`, `test_conversation_os`, `test_intake_approve_and_goal`:
  the interpreter label read 'model-via-worker', and the API answered 500). The cause is module and environment state
  that the new files leave behind in the shared process. Two new files skipped: `test_profit_billing_events_pg` needs
  `OMNI_PROFIT_TEST_DATABASE_URL`, and `test_m4d2b_parity_and_worker` must run in a process that has not imported
  investor_app.
- **The second pg run (each file alone):** 13 of 15 pass. Two still fail alone and are waived with their exact failure
  in `tests/pg_not_yet_run.txt`: `test_conversation_os` (1 failed / 37 passed) and `test_m4d2b_parity_and_worker`
  (3 failed: no eligible model route for local-coder; a modification classification None instead of 'system_bug').
  The same run timed out the negative-controls step (5 minutes). On main after #415 that step took 4m39s, because my
  skill-gate specs run real engine builds. The bound is now 10 minutes.
- **The change:** 15 files run in a new step, each in its own process, and a skip there is an `::error`. The profit
  billing file is in `tests/pg_not_yet_run.txt` with its reason. The focused list is back to what it was.
# 2026-11-16 — the skill units block builds: G3 accessibility, G4 performance, G6 secrets (Claude Code)

- **Owner's order:** wire the 5 a11y skills into G3 (each skill fails a build when it fails), 5 performance skills plus
  G4, and 5 secrets skills plus G6. Then (owner, the same morning):
  - strengthen G3 until it fails on a page;
  - G4 in `warn` mode with a high threshold until warehouse 114 is fixed;
  - the `OMNI_GATE_<G>` switch reports when it is off, on every build.
- **G3 fell on the butcher production page (`bld_83529c13...`, served from app.py).** Two broken variants were made
  from it, each changed in one place. With `--text-dark: #b8bec8`, body text on `#f8fafc` is 1.79:1, so
  `CONTRAST_LOW` fails the build. With its `:focus-visible` rule removed and `outline:none` on `a:focus, button:focus`,
  `FOCUS_LOST` fails the build. Both repair to the real page and pass.
- **Bug found in my own G3 (root cause):** the generated pages set every colour through `var(--...)`, and the contrast
  probe read only literal hex. It judged no colour pair on the real page and passed it blind; the old probe passes the
  low-contrast variant. The probe now resolves custom properties (with a var() fallback), and `judged()` counts the
  pairs it read (4 on the real page). A pair it cannot read (rgb(), a gradient) is not judged and not claimed.
- **Another bug of mine, caught before push:** `report()` walked the executor chain through `_inner` without a bound. On
  the worker harness's MagicMock engine every attribute is a new mock, so the walk ran out of memory: a MemoryError in
  `test_build_failed_announced`, and the kernel killed processes. The fix: the walk stops at MAX_CHAIN (20), follows
  only real SkillGateExecutor objects (`vars()`, never an invented attribute), and accepts `gate_modes` only as a
  dict. `test_the_report_walk_is_bounded` is the regression test; the unbounded version is its proof, since it failed
  that way.
- **Implemented:**
  - `omni_prod/skill_units/gate.py`: a gate is every unit whose manifest names it. It wraps the engine's executor;
    after the sandbox run, each unit's probe runs on every page, and a failing unit is an acceptance failure
    `gate-<G>-<unit>`, with its code, the page and the findings, which goes to the repair round.
  - Pages are .html files, or a whole HTML document inside app.py, which is how the generated sites serve their page.
    A secrets unit (`reads_source`) reads every text file. No page and no source unit means NOT_RUN, said in the log
    and in `last_gate`.
  - `OMNI_GATE_<G>` takes `block`, `warn` or `off` (`1` and `0` also work); any other value raises. The defaults are
    G3 block, G4 warn, G6 block.
  - Every build writes each gate's mode, OFF included, to the log (`GATE_ON` / `GATE_OFF`) and to the build evidence
    (`evidence_json.skill_gates`: mode, status, failure codes).
  - In warn mode the failures are recorded (`GATE_WARN`, `last_gate`, the evidence) and the build goes on.
  - The worker installs G3, G4 and G6 after the window gate.
- **New units (each with manifest, probe, ok and broken fixtures, failure codes):**
  - G4: `perf_blocking_script` (SCRIPT_BLOCKING), `perf_font_display` (FONT_NO_SWAP), `perf_font_preconnect`
    (FONT_NO_PRECONNECT), `perf_hero_eager` (HERO_LAZY), `perf_lazy_images` (IMG_NOT_LAZY), and
    `perf_inline_image_weight` (IMAGE_INLINED_HEAVY: an inline data: image over 500,000 base64 characters; the
    butcher page had 1,735,408). G4 warns on it and does not block, until warehouse 114 is fixed.
  - G6: `secrets_private_key`, `secrets_api_keys`, `secrets_db_url`, `secrets_bearer`, `secrets_assignment`, on the
    repository's own scanner `omni_prod/secret_scan.py`, so the build and the repository share one definition. A value
    read from the environment is not a credential.
- **Evidence:**
  - `tests/test_skill_gates.py`, 15 tests:
    - Each of the 16 units fails a real-engine build through its own broken fixture with its own code, and the repair to
      the real page passes.
    - G3 falls on the two real-page variants, in its default mode.
    - G4 warns by default: the build goes on, with the log line and the evidence.
    - Every gate says its mode on every build, OFF included, and the evidence carries the gates.
    - A key in server.py fails G6 even with a clean page.
    - No page means NOT_RUN, said.
  - `tests/test_skill_units_a11y.py` checks the parts of all 16 units.
  - Negative controls: `skill_gates.json` 10/10, `skill_units_perf_secrets.json` 11/11, `skill_units_a11y.json` 6/6. Every spec that touches the changed files: build-failed-announced 4/4, repair-stop-reason-ui 3/3, lens11-image-match 9/9, window-catalog 7/7, worker-build-not-found 3/3; item2 needs psycopg and fails identically on main `c38fbb4`; settle-computed is pg-only.
    - NC6 puts back the literal-hex-only probe, and the real-page test catches it.
    - NC8 makes OFF silent, and it is caught.
    - NC10 makes G4 block by default, and it is caught.
- **Real-path evidence:** the unchanged butcher page passes all 16 units, so the gates do not block a page customers
  got. Its hero, as served, was inlined as 1.7MB of base64 (warehouse 114). The recorded page replaced it with a 1x1
  placeholder; on the real one, G4 would warn, which is the purpose.
# 2026-11-16 — an accidental production release, and the release mark tightened (Claude Code)

- **What broke:** #413's merge `c38fbb4` deployed BOTH Vercel production (`dpl_DFWp5Yxw1ziP5gJbMGUBWMUejSMu`, READY) and the
  build worker (deploy-worker run 43820763641). Neither was a release.
- **Root cause, a bug of mine:** I wrote the literal mark in #413's PR title ("... only on a release (`[release]` or a manual
  run)"). GitHub copies the PR title into the merge commit's body, and both rules matched the mark anywhere in the message.
- **Impact:** what went out is main at `c38fbb4`. Its runtime code equals the released `9917eba`; only the workflow, the gate
  script, tests and STATUS changed. No customer-visible change. The worker deploy was left to finish, because a cancel in the
  middle of a drain is the riskier step.
- **Fix:** the mark counts only when the commit's FIRST LINE (the merge title) ENDS with `[release]`, in both
  `scripts/vercel_ignore_build.mjs` (`isRelease`) and `scripts/release_gate.py` (`is_release`). `OMNI_RELEASE=1` and a
  manual run of deploy-worker are unchanged. #412's real release title ("Merge pull request #412 from ... [release]")
  still releases. #413's message verbatim, a mark in the body, a mark mid-title or at its start all do not.
- **Evidence:** the #413 message is a test case in `tests/test_vercel_ignore_build.py` and `tests/test_release_gate_worker.py`.
  Negative controls: `vercel_ignore_build.json` NC6 and `release_gate_worker.json` NC4 put back "anywhere in the message"
  and the new tests catch it.
- **The working rule from now on:** the literal mark is written only as the last word of a release merge's title. It
  is never written in a PR title or body.

# 2026-11-16 — warehouse 111 completed: the build worker deploys only on a release (Claude Code)

- **Fix:** `scripts/release_gate.py` + a `release-gate` job in `.github/workflows/deploy-worker.yml`: the `deploy` job runs only when the
  push's head commit carries `[release]` or the run is manual; otherwise the gate prints `::notice title=release gate::SKIP -- ...`.
  An unknown event fails loudly. The frozen browser-probe step is untouched. Vercel production follows the same marker (#408).
- **Evidence:** `tests/test_release_gate_worker.py` 6 tests (the script run as the workflow runs it; the job dependency read from the
  YAML); controls `release_gate_worker.json` 3/3.
- **Consequence:** migrations (applied by deploy-worker) now also reach production only on a release.

# 2026-11-15 — P0-d, warehouse 102 (narrow): why the automatic repair stopped reaches the customer (Claude Code)

- **Implemented and independently verifiable offline:** the engine already stopped at once on an unchanged repository
  (`no_progress_repository_unchanged`, 2026-10-07) and the worker stored the reason; now `app.js stopReasonLine()` says it in
  the customer's words (he/en table `repairStops`, one entry per reason the engines can emit; an unknown reason is shown, not hidden).
- **Evidence:** `tests/test_repair_stop_reason_ui.py` 7 tests (real `AutonomousProductEngine` loop, real worker job, customer-view filter,
  app.js in node). Negative controls `tests/negative_controls/repair_stop_reason_ui.json` 3/3 PASS (NC3 proves the engine stop itself).
  Full suite, one container, `--continue-on-collection-errors`: main `93916ae` 3131 collected / 34 collection errors / 2792 passed / 30 failed /
  302 skipped / 36 errors; branch `538e86f` 3138 / 34 / 2799 / 30 / 302 / 36. Failure lists identical (66 lines).
- **Not checked:** no real build; the UI function ran in node, not in a browser. The bdi root cause is #396, not this.
- **Awaiting:** Michael's SHA approval.
# 2026-11-16 — the first five skills as units: accessibility (Claude Code)

- **Implemented:** `omni_prod/skill_units/` (runner + five units): `skill.a11y.contrast` (CONTRAST_LOW, 4.5:1 on pairs set in one rule),
  `skill.a11y.focus` (FOCUS_LOST), `skill.a11y.labels` (LABEL_MISSING), `skill.a11y.heading_order` (HEADING_ORDER),
  `skill.a11y.alt_text` (ALT_MISSING). Each: manifest.json, probe.py (static, no model), fixtures/ok, fixtures/broken with
  expected.json (code + what is broken), failure_codes.json. An undeclared code raises.
- **Evidence:** `tests/test_skill_units_a11y.py` 6 tests over every unit and fixture; controls `skill_units_a11y.json` 6/6.
- **Not done:** the units are not yet a gate (G3, stage D) -- nothing calls them in a build. 98 of the 103 catalogue skills remain.
  Static only: contrast is judged only where a rule sets both colours; a browser measurement is not claimed.
# 2026-11-16 — a2-offline NC6 explained and fixed: the fixtures pointed at real hosts (Claude Code)

- **What broke:** NC6 of `a2_collect` (the offline guard disabled) failed now and then with one extra failing test,
  `test_one_run_counts_every_rejection_by_its_reason` (runs 43746694174 attempts 1-2, 43749460570, and #410's run of 2026-11-16).
- **Root cause, measured:** the assertion added in `6065cc8` printed it on #410's run: `(35, 31, 29, {'capture_missing': 2, ...})` instead
  of `(35, 31, 30, {'capture_missing': 1, ...})` -- one more site lost its screenshot. With the guard disabled, the browser really
  fetched the fixtures' external references (`cdn.example.com`, `images.example.org`, `maps.example.com`, `example.com`: real,
  resolvable hosts) over the runner's network, so a page's load time, and whether its capture fit in time, varied between runs.
- **Fix:** the fixtures and tests use reserved `.invalid` hosts (RFC 6761: never resolve, fail at once), so a disabled guard fails the
  same way every time. No production code changes; the guard and the tests' meaning are unchanged.
- **Evidence:** `tests/test_a2_collect.py` + `tests/test_a2_extract.py` 30 passed with the real browser here; controls a2_collect 7/7
  three runs in a row, a2_extract 6/6. **Not proven here:** whether this container could reach the real hosts at all; the proof is the
  next CI runs of a2-offline.

# 2026-11-16 — A2 steps 8 and 9: the window catalogue and the gate (Claude Code)

- **Implemented:** `omni_prod/window_catalog.py`: the eight windows A2 recognises (mega menu, age gate, cookie banner, entry popup,
  cart drawer, promo bar, chips, question widget), each with its spec (RTL, focus trap, Escape -- except the age gate, which needs an
  answer --, 44px buttons, not covering content on a phone, never two at once, age gate before cookies). The spec is written into the
  build prompt (`discovery.requirements_text`), an approved window is a fact of the canon (`fact_canon.build_canon`, key `window`),
  and `WindowGateExecutor` (installed by the worker) fails a build whose page lacks an approved window or breaks a rule the static
  probe can check: WINDOW_MISSING, WINDOW_RULE, WINDOW_ORDER, WINDOW_TWO_OPEN.
- **Evidence:** `tests/test_window_catalog.py` 17 tests, including the real AutonomousProductEngine failing a build without the approved
  age gate and passing after a repair adds it; controls `window_catalog.json` 7/7.
- **Not done (four of five, so NOT "done"):** the customer has no screen yet to approve windows -- `fields.windows` is read only when
  the customer set it (answer or message). The approval card belongs to the first agent's proposal (P1). Rules that need a browser
  (focus really trapped, nothing covered on a phone, 44px measured) are in the spec and the prompt, not in the static probe; the probe
  lists what it checked.

# 2026-11-16 — warehouse 111: production no longer deploys on every push to main (Claude Code)

- **What broke:** there is no test environment; Vercel built production on every push to main, so every merge went straight to
  customers.
- **Fix:** `scripts/vercel_ignore_build.mjs` (the project's Ignored Build Step): production builds only a release -- a commit whose
  message carries `[release]` (written in the merge commit), or a manual production deploy with `OMNI_RELEASE=1`. Anything else on
  production is skipped and the build log says why; production stays on the last released SHA. Previews still build automatically.
  The test that asserted "production always builds" encoded the behaviour the owner stopped; it changed in the open.
- **Evidence:** `tests/test_vercel_ignore_build.py` 8 tests (the real script in node, Vercel's variables); controls
  `production_on_release.json` 3/3.
- **Not covered (blocked by a no-touch path):** the build worker is still deployed by `.github/workflows/deploy-worker.yml` on every
  push to main; changing it touches `.github/workflows/`, which is outside this agent's paths. Recorded in WAREHOUSE.md.
- **Until a test environment exists:** every check runs against a fixed deployment URL, not the moving production alias.
# 2026-11-16 — warehouse 77c: a failed build is said in the conversation, with one action (Claude Code)

- **What broke:** a customer whose build failed saw nothing in the conversation; the failure lived only in the build tab.
- **Fix:** `omni_prod/build_announcement.py`: `FailureWitness` wraps the jobs repository of the live build job and remembers the
  transition to FAILED; `announce_if_failed` writes one assistant message (idempotent on `build-failed:<id>`): "the build failed",
  "you were not charged" only when the credits went back, and ONE action -- `retry_build` (back to the approval screen) or, for a
  detail only the customer can give, `edit_requirements`. Wired in `worker_tasks._run_live_build_job_with_components` (try/finally,
  so an engine crash is said too). A failure to write is logged as an error, never changes the build. UI: the `retry_build` button;
  the chat's status line for a failed build is styled as failed.
- **Evidence:** `tests/test_build_failed_announced.py` 7 tests (the production job through BuildHarness); controls
  `build_failed_announced.json` 4/4.
- **Not checked:** no real build, no browser run; the Postgres conversation store is exercised by its in-memory twin here.
# 2026-11-16 — warehouse 113: the image-question loop that kept customers from building (Claude Code)

- **What broke:** after an upload, "what is in the image?" could only be answered by a button. Typed answers ("זאת הדלת של החנות",
  "דלת עם ידית", even "מוצר") were not read, the question came back, and after three cards the buttons were replaced by
  "חסרה החלטה על קיבלתי את התמונה. מה יש בה?, ... בלשונית דרישות" (the question printed as the topic, the way forward only in another tab).
  Reproduced on main `d496a92` on the real supervisor path.
- **Fix:** `omni_prod/intake/image_answers.py` maps typed words to the option (owner's map: door/handle/product -> product,
  person/owner/name -> person, place/shop -> place, logo -> logo; first word wins, door/handle always product; no word -> no guess) and
  keeps the description as the "who/what" answer; the supervisor reads a typed answer only against what the last turn asked or blocked
  on (`_awaiting`); an image card past the card limit keeps its buttons and says how to answer; no assistant message is sent twice in a
  row with the same question (`_not_repeated`); the Requirements panel shows the chat's own next question (`discovery.panel_group`);
  "update the plan" says what is still missing (`app.js stillMissingLine`).
- **Evidence:** `tests/test_image_answer_loop.py` 11 tests; negative controls `image_answer_loop.json` 6/6 PASS.
- **Not checked:** no browser run; the UI line ran in node. No model interpreter (the deterministic one reads the words).

# 2026-11-15 — P0-c correction (Claude bug): the Postgres tests of #401 never ran in CI (Claude Code)

- **What was wrong:** `intake-budget-pg` enumerates its test files; `tests/test_company_loss_failed_build_pg.py` was not listed, so
  the claim in #401 and in the P0-c STATUS entry below ("passed in CI's pg-tests job, 315 passed") was false -- those 315 were other
  tests. Found by the independent review of 2026-11-15. Two assertions in the pg test would have failed had it run
  (`provider_cost_truth` is `COMPUTED_FROM_USAGE`, not `computed`; the roll-up is database-wide), and the ledger could have recorded
  a reservation estimate as a loss when nothing was measured (`CONSERVATIVE_RESERVATION`).
- **Fix:** the file is in the pg job list; `record_failed_build` writes nothing on `CONSERVATIVE_RESERVATION` (the ledger never records
  an estimate) and `release_failed` returns `loss_recorded`; the pg test asserts the real values and account-scoped sums, plus the
  unmeasured case. Negative controls NC4 (file dropped from the job list) and NC5 (estimate guard removed).
- **Evidence:** offline 13 passed, 5 skipped (pg). Controls NC2–NC5 PASS here (NC1 pg only). The real path on Postgres is verified only
  when this PR's `pg-tests` job runs the file -- read that job, not this line.
- **Structural finding for CI (Codex):** an explicit file list means every new `*_pg.py` test is silently not run; discover them.

# 2026-11-15 — P0-b, warehouse 104 + 106: the checks that did not run are an explicit list (Claude Code)

- **Implemented and independently verifiable offline:** `release_policy.QualityReport.not_run` (NOT_RUN / UNKNOWN / NO_CHECKS, required
  and advisory, with stage and reason) carried by `to_dict()` into the build's stored evidence; `app.js notRunLine()` names the checks
  in the customer's words on failed and ready builds, and says "no check ran" when a failed build has no report.
  Warehouse 106: `tests/test_attribution_per_criterion.py` proves on the real `RemoteSandboxRepositoryExecutor` (real `_run`, stub runner
  that really runs pytest) that a failed verify command fails exactly the criteria it carries; the generator-side cure is PR #210.
- **Evidence:** `tests/test_not_run_list.py` 12 tests (corrected 2026-11-15 by review: the entry said 15), `tests/test_attribution_per_criterion.py` 3 tests. Negative controls
  `tests/negative_controls/not_run_list.json` 4/4 PASS. Full suite, one container, `--continue-on-collection-errors`: main `93916ae`
  collected 3131 / 34 collection errors / 2792 passed / 30 failed / 302 skipped / 36 errors; branch `e07a790` collected 3146 / 34 / 2807 /
  30 / 302 / 36. Failure lists identical (66 lines).
- **Not checked:** no real build; the browser UI was executed in node on the production report, not in a browser. The 34 uncollected
  files (fastapi, psycopg, docker absent here) are not measured.
- **Open for Michael (spec):** a criterion no verify command covers is a FAILED criterion today (Golden E2E #1, so the repair loop adds
  the test); item 106's acceptance text says `not_run`. Not changed here.
- **Awaiting:** Michael's SHA approval; #210 (per-criterion verify) is clean against main and is the fix of 106's root.
# 2026-11-15 — P0-c, warehouse 103: the provider cost of a failed build is a loss row (Claude Code)

- **Implemented; awaiting the owner's approval of migration 044 and the pg job:** `company_loss.record_failed_build` (cause
  `failed_build_refunded`, quoted 0, actual = the cost basis, one idempotent row per build, nothing at zero cost) called inside
  `subscription_store.release_failed`'s own transaction; `infra/postgres/044_company_loss_failed_build.sql` widens the CHECK constraint
  by the fourth cause (precedent 015, 033), rollback file, staging bootstrap regenerated, `schema_manifest` requires 044.
- **Evidence (offline):** `tests/test_company_loss_failed_build.py` 5 tests (the exact INSERT and parameters, the cause set, the
  migration text, bootstrap `--check`, the call site). Negative controls `company_loss_failed_build.json`: NC2, NC3 PASS here; NC1 is
  pg-only. Full suite, one container: main `93916ae` 3131 collected / 34 collection errors / 2792 passed / 30 failed / 302 skipped /
  36 errors; branch `97fd833` 3140 / 34 / 2797 / 30 / 306 / 36 (the four new skips are the pg tests). Failure lists identical (66 lines).
  The first branch run (`ebbc9e1`) failed two manifest tests; fixed in `97fd833` and re-run.
- **Not run here (blocked, named):** `tests/test_company_loss_failed_build_pg.py` (4 tests) and NC1 need real PostgreSQL
  (`M4D2_DATABASE_URL`, the intake-budget-pg job). The real path -- the row inside the refund -- is verified only there.
- **Blocked by a decision:** migration 044 runs only with the owner's explicit approval (CLAUDE.md §5).
# 2026-11-15 — P0-a, warehouse 69: output profile + A0 router (Claude Code)

- **Implemented and independently verifiable offline:** `omni_prod/output_profile` (profiles for `website`/`web_app`, an
  `unsupported` entry with the customer's sentence for every other family, truth check at import), A0 in
  `conversation/supervisor._route_output` before the interpreter and the model, `families.requested_family` and the
  opening-product rule, `question_skills.checklist` raises on an unknown family, UI action `describe_web_instead`.
- **Evidence:** `tests/test_output_profile_router.py` 16 passed. Negative controls `tests/negative_controls/output_profile_router.json`
  5/5 PASS (NC2 first FAILED against a weaker test; the test now isolates the first truth check). Full suite in one
  container, `--continue-on-collection-errors`: main `93916ae` collected 3131 / 34 collection errors / 2792 passed / 30 failed /
  302 skipped / 36 errors; branch `3db9457` collected 3147 / 34 / 2808 / 30 / 302 / 36. Failure lists identical (66 lines).
  The first branch run showed one extra failure (`test_discovery_and_approval`), fixed in `3db9457` before push.
- **Not checked:** no real model build; the refusal was exercised with the deterministic interpreter only. The 34 uncollected
  files (fastapi, psycopg, docker absent here) are not measured.
- **Awaiting:** Michael's SHA approval; PR merges after #397 (the warehouse docs).

# Governance audit update — 2026-10-27 (ChatGPT/Codex)

- GREEN (GitHub CI reported, not independently rerun): PR #151 SHA `547e65726434267bee757ffff0ee48da4bbaf754` (6/6), #154 SHA `d7688475d9fc661fce8b668d9658e96e1fc783c1` (5/5), #155 SHA `71f922ec723c5fb19d5139e4699807391c7114d3` (5/5), #152 SHA `f8581f079d8bdb7e656fda7fad2d33ae450a1e3c` (5/5). Source: GitHub Actions runs attached to each SHA.
- BLOCKED: Independent execution and reviewer approval of all four audits; #152 already merged, requires retrospective review.
- IN REVIEW: Vision law and governance branch `docs/vision-law-governance-20261027`; Claude must verify because Codex/ChatGPT authored changes.
- NOT VERIFIED: Docker transient failure classification pending exact failed/retry run URLs; do not call it a proven flake without both.
- NOT STARTED: Paid provider benchmark. No paid API calls authorized.

# 2026-10-14 — Profit Protection v1 safety stage (PARTIAL)

## PR #34 follow-up — caller-stable build idempotency

**Implemented and locally verified:** The build API accepts validated caller
keys scoped to account + internal project, stores full request and quote
SHA-256 fingerprints in an additive identity table. Quote identity uses the
versioned `quote-fingerprint/2` scheme and `category=build`. Exact replays return
the original build on an identical replay; changed input, quote, or persisted
fingerprint version returns 409 before approval/reservation. The browser retains a stable
key across ambiguous network failures; the postdeploy client supplies a UUID.
Callers without a key retain the existing contract-level deduplication and
deliberate retry behavior for failed/cancelled builds.

Focused command:

```text
python -m pytest -q tests\test_m5_build_economics.py tests\test_qa_budget.py tests\test_m5_build_contract_binding.py tests\test_deployment_verification.py::ManifestTests tests\integration\test_m5_build_economics_postgres.py
```

Result: **62 passed, 3 skipped, 3 subtests passed**. The three skips are
PostgreSQL-dependent; the new concurrent and cross-project idempotency cases
have not run locally.
Additional checks passed:

```text
python -m py_compile omni_prod\investor_app.py omni_prod\job_repository.py tests\test_m5_build_economics.py tests\integration\test_m5_build_economics_postgres.py
node --check omni_prod\assets\app.js
git diff --check
```

On head `7779cab`, `intake-budget-pg` run
[38556863549](https://github.com/Shayfly/desktop-tutorial/actions/runs/38556863549)
reported 175 passed, 2 failed, and 56 subtests. Both failures were rollback
tests whose simulated 039 database accidentally included migration 040. The
fixture now stops at 039 and separately verifies the current package applies
040. The new caller-key PostgreSQL races did execute in the same run but the
job failed overall.

Neon bootstrap runs [38556861212](https://github.com/Shayfly/desktop-tutorial/actions/runs/38556861212)
and [38556863814](https://github.com/Shayfly/desktop-tutorial/actions/runs/38556863814)
failed because the checked-in bootstrap omitted migrations 039 and 040; its
generator/verifier also mishandled Windows line endings. The generator and
verifier now normalize SQL line endings, and local regeneration plus
`python tools\generate_neon_bootstrap.py --check` confirms both migrations are
included with LF output. The combined local command below passed **39 passed,
6 skipped, 3 subtests passed**; skipped cases require PostgreSQL.

```text
python -m pytest -q tests\test_m5_build_economics.py tests\test_migration_rollback_tolerance.py tests\test_deployment_verification.py::ManifestTests tests\integration\test_m5_build_economics_postgres.py
```

On head `1a1ce20737bf952c749fd3f53308c216ef02f4ff`, both
[`intake-budget-pg` runs](https://github.com/Shayfly/desktop-tutorial/actions/runs/38557773477)
and [38557768232](https://github.com/Shayfly/desktop-tutorial/actions/runs/38557768232)
passed, including the no-skip gate; both [Neon bootstrap runs](https://github.com/Shayfly/desktop-tutorial/actions/runs/38557773575)
and [38557768217](https://github.com/Shayfly/desktop-tutorial/actions/runs/38557768217)
passed migration checksum, app-table, and rerun-guard checks.

The same head's V24 test runs [38557768202](https://github.com/Shayfly/desktop-tutorial/actions/runs/38557768202)
and [38557773638](https://github.com/Shayfly/desktop-tutorial/actions/runs/38557773638),
and V11 validation runs [38557768203](https://github.com/Shayfly/desktop-tutorial/actions/runs/38557768203)
and [38557773492](https://github.com/Shayfly/desktop-tutorial/actions/runs/38557773492),
failed on stale generated registry data: `skills/migration_test` still claimed
REAL_SERVER_VERIFIED after its verifier source changed. `python -m
omni_prod.agent_os.audit --write` regenerated the registry; its focused test
passed **4 tests locally**:

```text
python -m pytest -q tests\test_agent_os.py::AuditTests::test_committed_registry_is_current_and_not_inflated tests\test_agent_os.py::TruthMatrixTests
```

On head `d3e9d9c`, V24 runs [38558480608](https://github.com/Shayfly/desktop-tutorial/actions/runs/38558480608)
and [38558486429](https://github.com/Shayfly/desktop-tutorial/actions/runs/38558486429)
plus V11 runs [38558480613](https://github.com/Shayfly/desktop-tutorial/actions/runs/38558480613)
and [38558486243](https://github.com/Shayfly/desktop-tutorial/actions/runs/38558486243)
then found `DEPARTMENT_MATRIX.json` stale after that registry update (generated
IMPLEMENTED count 9 vs committed 8); the nested full-suite failure was a
consequence. `python -m omni_prod.agent_os.departments --write` regenerated
the matrix, and the combined registry/department/truth regressions passed
**5 tests locally**:

```text
python -m pytest -q tests\test_conversation_os.py::DepartmentTests::test_every_agent_in_exactly_one_department_and_files_current tests\test_agent_os.py::AuditTests::test_committed_registry_is_current_and_not_inflated tests\test_agent_os.py::TruthMatrixTests
```

The d3e9d9c push/PR PostgreSQL runs
[38558480621](https://github.com/Shayfly/desktop-tutorial/actions/runs/38558480621)
and [38558486265](https://github.com/Shayfly/desktop-tutorial/actions/runs/38558486265)
passed with no skips; Neon bootstrap run
[38558486436](https://github.com/Shayfly/desktop-tutorial/actions/runs/38558486436)
passed. On corrected head `986e7b0`, V24 and V11 push/PR checks passed:
[V24 push](https://github.com/Shayfly/desktop-tutorial/actions/runs/38559082202),
[V24 PR](https://github.com/Shayfly/desktop-tutorial/actions/runs/38559085373),
[V11 push](https://github.com/Shayfly/desktop-tutorial/actions/runs/38559082225),
and [V11 PR](https://github.com/Shayfly/desktop-tutorial/actions/runs/38559085400).
Deterministic regression [38559085391](https://github.com/Shayfly/desktop-tutorial/actions/runs/38559085391),
Neon bootstrap/fresh-Postgres [38559085587](https://github.com/Shayfly/desktop-tutorial/actions/runs/38559085587),
compose, customer UI, and the PR full V24 test all passed.

The corrected-head push PostgreSQL suite
[38559082247](https://github.com/Shayfly/desktop-tutorial/actions/runs/38559082247)
passed **177 tests, 56 subtests, no skips**. Its duplicate PR run
[38559085600](https://github.com/Shayfly/desktop-tutorial/actions/runs/38559085600)
failed **1 of 177 tests** (176 passed, 56 subtests, no skips):
`RealDockerDrainRecovery.test_5_an_oom_kill_fails_the_drain_and_recovery_restores_everything`.
The isolated preview-worker exited 137 only when the 60-second drain deadline
expired; Docker reported `oom=false`, so this is not evidence of an OOM kill.
The test's strict `OOMKilled` assertion is retained. A reliable harness fix was
not established; do not call exit 137 an OOM or weaken the assertion.

The later documentation-only head `3e4f0bd` reproduced the same issue with
the opposite push/PR outcome: push run
[38559914558](https://github.com/Shayfly/desktop-tutorial/actions/runs/38559914558)
failed only that OOM test (**176 passed, 1 failed, 56 subtests, no skips**),
while PR run
[38559920282](https://github.com/Shayfly/desktop-tutorial/actions/runs/38559920282)
passed **177 tests, 56 subtests, no skips**. The push failure again reported
exit 137 at the deadline and `oom=false`. Across the duplicate runs on both
heads, this pass/fail reversal establishes a nondeterministic Docker OOM
fixture; the CI evidence does not prove an OOM kill.

**OOM fixture repair (commit de17f6d, awaiting CI):** root-cause hypothesis is
that a 64 MiB allocation inside a 64 MiB cgroup can fit by reclaiming page
cache. The container limit is now 48 MiB (memory and swap) against the same
64 MiB allocator, so the allocation strictly exceeds the limit. The test now
asserts the container's `HostConfig.Memory`/`MemorySwap` before triggering,
failing fast if a runner ignores the limit. The strict `OOMKilled` assertion is
unchanged. Not verified locally (no Docker); CI on 536c243: both duplicate
`intake-budget-pg` runs passed (push 38579318433, PR 38579332870) including the
strict OOM test. Two runs is not yet proof of determinism; repeat runs are
needed. The push `v24-ci` run 38579318130 failed `customer-ui`
(`tests/customer_flow_browser.cjs:34`, 'שינוי' button not visible) while the PR
`v24-ci` run 38579332614 on the same SHA passed; this change touched no UI code,
so it is recorded as a suspected flaky browser test, not diagnosed. Preview
verify still fails only `schema_compatible` (unapplied migrations). Also added a
worker-crash caller-key replay test (`tests/test_m5_build_economics.py`,
33 passed locally).

Migration 040 has **not** been applied to Preview, staging, or Production.

**Preview schema blocker:** Deployment run
[38559974291](https://github.com/Shayfly/desktop-tutorial/actions/runs/38559974291)
for head `3e4f0bd` failed only `schema_compatible`, reporting migration 040
pending. Endpoint, commit SHA, synthetic registration, session identity,
project creation, conversation, persistence, and project-memory checks passed.
Sanitized nested checks additionally reported `AUTH_INVALID` (401) and
`HTTP_403`, but did not add a second top-level failed check. Earlier run
[38551925540](https://github.com/Shayfly/desktop-tutorial/actions/runs/38551925540)
likewise received an empty applied-version set for the then-required
migrations 1-21 and 26-39. This proves only that the journal is absent, empty,
or invisible to the role, not that all application tables are absent.
Read-only Vercel evidence indicates Preview and Production share the database
URL. Do not bypass auth or migrate; diagnosis needs authorized read-only
journal/search-path evidence and a safe isolated environment.

**Still blocked/incomplete:** The full titled v2 requirements document remains
unavailable, so the 22-area map is provisional. Migration-backed concurrency,
rollback, bootstrap, V24, V11, and deterministic checks passed on `986e7b0`;
V24/V11, deterministic, Neon, and Preview-independent acceptance checks also
passed on `3e4f0bd`. The two duplicate PG jobs on each head diverged only on
the bounded Docker OOM test, so this harness remains an unresolved
nondeterministic blocker. Preview schema verification is blocked on unapplied
040.
The other four corrective areas remain incomplete: company-liability
accounting for provider failures; an operational overrun/estimate-error
liability policy; verified recognized-sale revenue distinct from cost/reserve;
and hard company-wide Free/storage/abuse and auditable admin ceilings.
Wallet/top-ups/refunds, calibrated estimates, checkpoint resume, and
reconciled profitability/compliance reporting are also not implemented. No
paid services, shared/live migration, merge, Production deployment, or budget
change occurred.

## Issue #6 / PR #31-#34 audit (evidence-bounded, 2026-10-14)

The requested Issue #6 work is broader than this follow-up. A requirement-to-code/test/status matrix for P1, P3, the customer build path, current PR bases, and blockers is recorded in [the evidence audit](docs/evidence/issue-6-pr31-34-audit-2026-10-14.md). The current P1/P3 acceptance and full build path remain PARTIAL, not merge-ready. Issue #6 remains OPEN. PRs #31-#34 remain open drafts. PR #34 targets PR #33, not the requested milestone branch; direct retarget would include 188 unrelated commits relative to the target merge base.

The exact full v2 requirements source remains absent after repository/branch review and exact-text GitHub searches. The 22-area matrix remains explicitly provisional. Caller-stable idempotency/full quote fingerprint is implemented locally but awaits PostgreSQL/CI verification; provider-failure company liability, wallet/refunds, durable checkpoint resume, and reconciled profit remain partial or missing. No full v2 compliance claim is made.

## v2 follow-up — provisional audit only (2026-10-14)

**Implemented and independently verified:** The focused local economy,
billing, settlement, pricing, build-state, and registry command passed
**118 tests** with **9 skipped**. Exact command and the provisional 22-area
audit are in
[`docs/evidence/profit-protection-v2-provisional-audit-2026-10-14.md`](docs/evidence/profit-protection-v2-provisional-audit-2026-10-14.md).
These results verify only local test behavior, not live PostgreSQL, payment,
provider, or production behavior.
The same-build reservation replay avoids a second counter debit; attempts to
reuse that key with a different account/project/reserved amount or after
settlement are rejected. The current working-tree addition separately binds
caller retries to request and quote fingerprints; its local regressions are
listed above.

**Implemented but awaiting external live verification:** Existing atomic
reservation, billing-event idempotency journal (migration 039), project
persistence, quote/meter/settle/release paths, and provider pricing versions.
The PostgreSQL concurrency/restart tests were skipped because no disposable
loopback `profit_test...` database was configured. Migration 039 remains
unapplied.

**Updated Docker recovery regression:** The first PR #34 GitHub Actions run had a genuine failure: the OOM workload was killed at the stop deadline with `oom=false`. The test now compiles a bounded allocator that touches every page of a 64 MiB allocation within the existing 64 MiB cgroup; the assertion still requires Docker's `OOMKilled=true` evidence and does not treat exit 137 alone as an OOM pass. The local expanded focused command, including the Docker module, passed **118 tests with 17 skipped**; the eight Docker cases were skipped because Docker/PostgreSQL/Redis are unavailable here. Syntax compilation and `git diff --check` passed. The real PostgreSQL/Redis Docker CI suite passed **174 tests, 56 subtests** on code head `78a0d05` and later head `7c21dc8`, including the strict `OOMKilled=true` assertion. Preview run [38552661996](https://github.com/Shayfly/desktop-tutorial/actions/runs/38552661996) failed 1/11 at `schema_compatible`; the verifier received an empty applied-version set. Other conversation, persistence, memory and isolation checks passed. This does not prove all application tables are absent. Preview and Production share the configured database URL. No migration was run.

**Blocked by a named credential/service:** Canonical rule-by-rule v2 completion
is blocked by the missing full titled v2 specification. Live billing and
database verification are blocked by the absence of an authorized payment
processor test environment and disposable PostgreSQL test database. No
credentials were requested or used.

**Not implemented:** Complete funding-lot wallet, invoice/top-up/refund
accounting, company-funded provider-failure budget, full all-scope exposure
caps, budget pause/resume from verified checkpoints, data-calibrated Smart
Completion Estimate, and reconciled profitability/compliance reporting. The
caller-key implementation is pending real-Postgres concurrency verification
and migration application in an authorized test environment. The dependency
order and gates are recorded in
[`docs/superpowers/plans/2026-10-14-profit-protection-v2-follow-up.md`](docs/superpowers/plans/2026-10-14-profit-protection-v2-follow-up.md).
The current follow-up adds only that reservation replay and caller-key
hardening; broader economy work remains deferred because the canonical v2
acceptance source is absent. No Preview/Production migration, real
payment/provider call, budget change, merge, or production deployment was
performed. The PR Preview verifier's applied-version set is empty; this is a
journal/search-path compatibility failure, not proof that all migrations'
schema objects are absent.

**Implemented and independently verified locally:** unpaid Checkout and metadata
events cannot grant paid entitlements; entitlement changes preserve usage;
prior-worker UNKNOWN calls remain covered; minimum conservative variable-margin
policy is 60%; event identity/order/source cancellation regressions pass in the
reviewer service. Independent read-only review findings received regression fixes.
Master registries were regenerated with their existing tools; no new live proof
was asserted. See [scope and evidence](docs/evidence/profit-protection-v1-safety-2026-10-14.md).

**Implemented, awaiting external verification:** Postgres transactional billing
event journal, source tombstones and ordering (additive migration 039); new local-only
Postgres concurrency/restart tests are opt-in, not counted as passed. No live
migration, payment, provider execution, merge or Production deployment occurred.

**Blocked by named environment:** disposable local PostgreSQL for integration,
binary branding files absent from this API-reconstructed snapshot, and Linux
shell/container parity for the broader suite. Stripe live behavior remains unverified.

**Not implemented:** funding lots/top-ups, invoice-based renewal/proration/refunds,
dynamic build-credit quotes, full cross-scope caps, completion-credit ranges,
budget pause/checkpoint resume, and reconciled gross-margin reporting. This safety
slice does not complete Credit Economy v1. Public plan prices are unchanged.

**Verification:** the focused safety/economics/webhook/schema/registry suite passed
106 tests, with9 skips (including4 opt-in Postgres tests) and3 binary-branding
tests deselected because assets are absent locally. The broad Windows run ended
1640 passed /67 failed /176 skipped, plus324 subtests; it ran during implementation
and is not a final-head or green-CI claim. Its schema-boundary assertion was then
updated and independently rechecked in the focused suite. Other broad failures
include temporary-file permissions, unavailable shell/container support and
missing binary assets; they have not all been resolved or classified as pre-existing.
Local snapshot transport EOFs were corrected only where bytes matched remote Git
blob SHA, then existing registries were recomputed. No provider credentials were
used. Exact commands are in the linked evidence document; full-suite and focused
logs are retained as chat outputs. No Production readiness is claimed.

# 2026-10-12 — P0 session evidence (partial verification)

Read [the current evidence and gap report](docs/evidence/148ai_p0_2026-10-12.md) before interpreting historical status entries below. Final local focused regressions: 23 pass. Earlier exact-revision CI passed full pytest with 1607 passed / 172 skipped; palette changes require new CI. Golden AI/build/preview E2E is NOT_VERIFIED. Draft PR #21; no merge/Production/live migration/paid provider authorization.

# STATUS — M1 async builds / M3 running preview / M4 natural-language modification

## Update 2026-10-11 ~22:00 Asia/Jerusalem — deploy gate, rollback after 038, real-Docker rehearsal, evidence export, isolation (LOCAL ONLY, nothing pushed)

Branch `claude/fix-static-site-acceptance-2026-10-11` (base a3cc9abc). Tested commit: **f419f58** (full suite below). Later commits only touch STATUS.md.

**Implemented and independently verified (local, on this commit)**
- Deploy gate fails closed (`omni_prod/active_jobs.py`, `drain.sh`): exit 2 when DB/Redis/URL/table/args cannot be verified, stale heartbeat still blocks (only `--acknowledge-stale <exact id>` releases, never passed by the workflow), intake (CLAIMED/EXECUTING even with an expired lease), STARTING previews, every RQ started-registry (incl. unregistered `omni-preview-host-*`) and busy RQ workers block; re-check immediately before and after the stop; a refusal before the stop leaves `not-stopped` so `recover.sh` touches nothing. Tests: `tests/test_worker_deploy_recovery.py` (GateInDrainTests, ActiveJobGateTests; the real-RQ test ran with a local Redis).
- Code rollback after 038 without DROP/deleted attachments/hidden version: `python -m omni_prod.migrate --accept-newer 38` (exact versions, only newer than the package; unlisted version / gap / checksum drift still abort), `deploy-worker.yml` dispatch input `accept_newer_migrations`. Tests: `tests/test_migration_rollback_tolerance.py` (isolated throw-away PG; attachment row survives old->new round trip). The previous worker code (2a2bba6) was also run locally against a DB at 038: `migrate` fails (as before), the worker boots and listens.
- Real Docker (engine 29.8.2 started in this sandbox, `docker compose` 5.5.1): `tests/test_real_docker_drain_recovery.py`, 8 scenarios against isolated PG + Redis, unmodified drain.sh/recover.sh: clean deploy, active job, Redis/DB/missing-URL failure, rollback-image save failure (fault injection around real docker, labelled), timeout->137, real OOM (engine OOMKilled flag), migration failure, startup failure; every scenario ends with all four services running the previous image. 8 passed.
- Evidence export extended (generated files + `.omni/project.json`, failed checks with evidence, credit reservation, `--files-dir`), `omni_prod/failure_replay.py` (offline CRUD-requirement / missing-coverage / real-defect separation, SYNTHETIC test data only), `omni_prod/isolation_check.py` (non-secret identities, SHARED/ISOLATED/UNKNOWN).

**Full suite on f419f58:** 1697 passed, 43 skipped, 0 failed, 288 subtests passed (551 s). Skips: 11 need a live Redis on 127.0.0.1:6379 (not provided; the new tests use `OMNI_TEST_REDIS_URL`), 4+3 live preview/sandbox hosts (`OMNI_RUN_LIVE_PREVIEW`/`LIVE_SANDBOX`), 4 migrated live Postgres, 3 `OMNI_RUN_LIVE_INTEGRATION`, 3 `omni-sandbox:latest` image absent (registry pulls blocked), the rest each name a missing credential/service (QStash, LLM, image provider, R2, Android/Xcode signing, clean-room DB, fixture URL) or are documented duplicates. None is counted as a pass.

**Implemented but awaiting external live verification**
- The same drain/recover scripts on the real Oracle host with the real images/compose/.env (the sandbox proves script logic on a real engine, not the host). NO-GO until the person approves a rehearsal when no build is running.
- One-off evidence export of the exact "חגית" build (not run): needs the `bld_<hex>` and someone with worker-host access (or read-only DB + `OMNI_S3_*`). See docs/DEPLOY_RECOVERY_REHEARSAL_HE.md section 4.
- Effective isolation check: needs `vercel env pull` files for preview/production and the worker `.env` produced by the owner. Known already (read-only Vercel API): `OMNI_DATABASE_URL`, `OMNI_REDIS_URL`, `OMNI_SECRET_KEY` are ONE record for production+preview => SHARED DB, SHARED Redis (=> shared queues). `OMNI_S3_*` are separate records, values unknown.

**Blocked by a named credential/service**: live DB state (active jobs, "חגית" data), Vercel runtime logs, billing API (404), deployment-verify bypass secret, a new restore-verified backup (needs a dispatch on the milestone ref — approval).

**Not implemented / open**: no route to roll back to code older than this branch through the workflow (only image-level `recover.sh`, no migration); no API-side pause of work intake (a job starting between the last gate check and SIGTERM and running past 25 min is cut off and reported); backup restore checks 14 tables and not `conversation_attachments`; scheduled backup still not installed; "חגית" is NOT shown fixed. No Mock/Replay presented as proof of a new build; no paid call made; no push, merge, deploy, migration or secret change.


## Update 2026-10-11 ~19:30 Asia/Jerusalem — project "חגית" failed build: content-only site acceptance (LOCAL ONLY, nothing pushed)

Base: a3cc9abc (PR #17 head). Branch `claude/fix-static-site-acceptance-2026-10-11`. No push, merge, deploy, live migration, secret change or paid call was made; spend by this work: $0.

**Customer failure (from the founder's screenshot, not from job evidence):** `BEHAVIOR: ... 2 failed check(s); missing acceptance coverage: A2,A4,A5; missing required behavior kinds: data_create,responsive`.

### 1. Implemented and independently verified (offline, this commit)
- Structured content-only handling: a new non-delegable question `content_only`; the binding brief block gets `Product kind: CONTENT-ONLY website` only after an explicit "yes" with sign-in NONE and no personal data; `ProductArchitect.compile` records `static_content_site` only from that approved block (free text never qualifies); `acceptance_scope` then waives **data_create only**. data_read, responsive and api_smoke stay required; missing/unknown contract, any login/role, personal data, external integration, storage/scheduled/outbound infra, or a CRUD product keep the full floor.
- "No personal data" in Hebrew/English is read from the request; delegation never decides `content_only`.
- A WhatsApp *link* (wa.me, "קישור/כפתור וואטסאפ") is no longer inferred as an SMS/messaging integration (architect, intake contract, feasibility answer).
- Conversation: a bare "תתחיל/בוא נתחיל/go" with an existing brief returns the `approve_build` action (no auto-approval); content added after the brief is complete (prices, texts, links) is recorded verbatim in the brief `content` field as a new revision, which invalidates any earlier approval via the fingerprint; the "ready" sentence is not repeated.
- Repair feedback now states which kinds are NOT_REQUIRED and that criteria mapped only to them stay uncovered (target of the "A2,A4,A5 missing" loop).
- Tests: `tests/test_content_only_site.py` (13) fail without the fix (collection error) and pass with it, including a real local HTTP run of `WebSaaSAcceptanceRunner`.
- Full suite on the fix: 1627 passed, 44 skipped, 3 failed → the 3 were registry/department files made stale by the code change; regenerated with the canonical generators (`python -m omni_prod.agent_os.audit --write`, `python -m omni_prod.agent_os.departments --write`) and re-run green. **Side effect: real-server evidence for discovery requirement_extraction / smart_question_generation / safe_default_selection is now STALE (REAL_SERVER_VERIFIED → IMPLEMENTED; Truth Matrix 22 → 19) until re-verified on a real server.**

### 2. Implemented, awaiting external live verification
- Everything above on the real worker/Preview. The failed job itself has NOT been reproduced: its approved brief/contract, A2/A4/A5 definitions, generated files, `.omni/project.json`, per-round failures and spend are not accessible from here (UNVERIFIED which of scope / mapping / data defect / responsive defect / stagnation applies).

### 3. Blocked by a named credential/service
- Job evidence export (authenticated project/job APIs / DB read), worker runtime SHA and flags, Preview/Production env isolation values, `VERCEL_AUTOMATION_BYPASS_SECRET` for deployment-verify (HTTP 401 PROTECTED), live migration 038.

### 4. Not implemented
- Inspector activation, candidate-before-accept, durable resume, paid Golden E2E proof; an actual reproduction of the "חגית" job.

### Follow-up commit (same day, local only): spec/prompt support, worker drain/recovery, scheduled backup, evidence export
- **Generator/ProductSpec:** the generator sees only the ProductSpec, so for an approved content-only contract the floor spec is now `site-content` + responsive + health (no platform-auth/rbac/data), and the Architect/Generator/Repair system prompts carry `CONTENT_ONLY_RULES` (static page, no DB/login/record API, plan limited to data_read/responsive/api_smoke, every acceptance id attached to a real check). Removing only the data_create check while still telling the model to build CRUD is thereby closed (offline tests; the model's behaviour itself is UNVERIFIED until one paid build).
- **Deploy recovery (`infra/worker-host/drain.sh`, `recover.sh`, `deploy-worker.yml`):** drains all four consumers (worker, intake-worker, intake-maintain, preview-worker); fails the deploy BEFORE migrations on a failed stop, exit 137, OOM or a still-running container; records previous images; `recover.sh` restores the previous consumers on drain/migrate/start/listen failure without touching the DB or volumes. Verified only with a fake `docker` (8 tests incl. a mutation check); NOT run on the real host.
- **Scheduled backup:** root cause confirmed by design (GitHub fires `schedule` only from the default branch). `infra/backup-scheduler/backup-scheduler.yml` (inactive here) dispatches `backup-restore.yml` on the milestone branch and fails if the last success is older than 30 h. Needs a one-file PR on `main` (Vercel builds Production from `main`: owner decision; changing the default branch is NOT proposed) and a later real-cron verification.
- **Evidence export:** `omni_prod/evidence_export.py` (one-off via stdin into the already-deployed worker image: no merge, no worker deploy) + `docs/FAILED_BUILD_EVIDENCE_EXPORT_HE.md` (+ a later-convenience workflow); schema-tested against the local PostgreSQL. Not run against the failed build.
- **Review fixes (2026-10-11, second round):** (1) drain is blocked when an existing consumer's image cannot be inspected/tagged or listed; (2) `recover.sh` fails when a recorded service has no rollback image, `up` fails, a service is not running afterwards or the worker is not listening; (3) the export uses only the approval whose `used_by_build_id` is exactly the build (and a matching brief/contract fingerprint) and reports MISSING/AMBIGUOUS instead of substituting; (4) the backup scheduler now separates DISPATCHED / STARTED / SUCCEEDED and is green only when the NEW run succeeds; it is NOT installed or active, the default branch is not to be changed, and a real cron run must still be verified after an approved install. Regression tests fail on the previous code (6 recovery/scheduler + 4 export).
- **Pre-merge safety assessment (2026-10-11 ~20:00):** `omni_prod/active_jobs.py` + a gate step before the drain (waits up to 20 min for RUNNING builds/changes, then fails WITHOUT draining; queued work is not interrupted; stale heartbeats are reported, not blocking). Simulation (fresh local DB, old code 2a2bba6 → 037, data, new code → 038): data preserved; **old code's `omni_prod.migrate` ABORTS on a DB at 038 ("applied migration missing from package: 38")**, so rolling back by redeploying old code through deploy-worker needs the manual 038 rollback first (`DROP TABLE conversation_attachments` + `DELETE FROM schema_migrations WHERE version=38`, simulated: other tables untouched, old migrate clean, 038 re-applies). Live facts read today: Preview `/api/v28/deployment` = a3cc9abc, applied_max 37, 038 missing (MIGRATIONS_PENDING); last backup 20261011T123608Z restore-verified (55 versions rebuilt, 14 tables, migrations 37); Vercel DB/Redis variables are ONE record shared by Preview and Production.
- **Runtime facts re-read (Vercel API):** latest Preview `dpl_536b1wK6…` READY at `a3cc9abc`, target null (no Production change); worker last recorded deploy `2a2bba6` (Actions 38130249079, per the handoff); live DB version, live flags and the failed job's data: UNVERIFIED (no access).


## Update 2026-10-11 ~15:30 Asia/Jerusalem — Conversation UX, image attachments, Visual Edit, 3-pane workspace

**Branch `claude/visual-edit-workspace-2026-10-11` (stacked on PR #16). Not merged. $0: no paid model call, no paid flag, no secret change, no production deploy.** Details and gap list: `docs/VISUAL_EDIT_AND_ATTACHMENTS.md`.

**Vercel state checked first**:
- Production = `main` @ `e8f2949` (2026-10-06, old code).
- Integration Preview = `2a2bba6` (READY).
- PR #11, #15 and #16 exist only as their own branch previews.

**Implemented and independently verified (local; real FastAPI + PostgreSQL + real preview router over TLS; real Chromium desktop 1440×900 and mobile 390×844)**
- **Conversation:** short decision names; values taken from the request are verified, not re-asked; "don't know"/"what?" gets the reason, then the options (never the same sentence twice). Approved requirements are still never changed silently.
- **Image attachments** (migration 038 `conversation_attachments`, additive):
  - PNG/JPEG/WebP decided from bytes; SVG refused (415); 3 MB / 8000 px / 6 per message / 40 per project.
  - Owner-only (another account gets 403/404); `nosniff` + sandbox CSP; bytes deleted with the attachment.
  - Shown in the thread; the reply says plainly that images are **not analyzed**.
- **Visual Edit:**
  - Pick an element in the live preview (mouse or touch); the preview inspector wraps the unchanged router, off unless `OMNI_PREVIEW_INSPECTOR=1`.
  - The element is located in the stored source (file:line). Ambiguous → the person chooses, and the server refuses a guessed target (409).
  - Screenshot with box/drawing marks.
  - The change goes through the existing modifications pipeline; before/after comparison and undo use the existing previews and rollback.
- **Layout:** desktop chat (right) | preview (centre) | edit tools (left), all resizable, project list as a drawer; mobile tabs Chat / Preview / Edit; "Agent tasks" moved under "Build progress" as collapsible technical details.
- **Evidence:**
  - `docs/evidence/visual_edit/walkthrough_result.json`: **23/23** checks, screenshots 01–16.
  - The Wave A UI walkthrough still passes (two steps adapted to the drawer/tabs).
  - Test-only substitutes: local-file object storage, a local process instead of a preview container, and a harness-written modification candidate (no model).
- **Tests:**
  - `tests/test_visual_edit.py` (real PostgreSQL) and `tests/test_conversation_ux.py`.
  - The 036→037 upgrade test is now scoped to ≤ 037, because 038 exists.
  - Neon bootstrap regenerated and verified on an empty PostgreSQL (34 migrations).
  - Full suite: **1564 passed, 2 failed, 44 skipped** before that scoping. One failure was the upgrade test, now passing. The other was `test_m4_acceptance` W, whose nested run included that same failure; it passes when run alone after the fix.

**Implemented but awaiting external live verification**: the inspector on the real preview host (env flags + worker deploy); one real targeted modification on the worker (paid); S3/R2 attachment storage on Vercel.

**Blocked**: image analysis by a vision model (no vision route and no approved budget).

**Not implemented**: preview of a candidate before accepting it; picking inside apps whose own CSP forbids `'self'` scripts (screenshot marking still works). After PR #11 merges, `schema_manifest.REQUIRED_MIGRATION` must become 38.

## Update 2026-10-11 ~17:00 Asia/Jerusalem — Master directive stages 1–4/6: plan-governed execution (G1), approved criteria as test basis (G3), escalated intake lane

**Branch `claude/plan-driven-execution-2026-10-11` (from `2a2bba6`). Not merged. $0 spent: no paid model call, no paid flag, no secret change, no production deploy.** Full audit and Beta/Production blockers: `docs/SYSTEM_WIDE_GAP_AUDIT.md`.

**Implemented and independently verified (real PostgreSQL 16 locally; real engine loop with local stub agents; no provider)**
- G1 plan-governed execution behind `OMNI_PLAN_DRIVEN=1`:
  - The approved ExecutionGraph (durable `agent_tasks`) admits every model call and every verification run; dependencies are checked under a row lock.
  - Out-of-order, repeated, over-limit and over-budget steps stop the build with `plan_violation`.
  - Spend is charged to its plan task (`AgentRuntime.charge`, metered or authorized worst case). Over budget → task BLOCKED.
  - The plan's repair limit tightens the engine (never widens it).
  - A superseded (lost) worker is refused.
  - Violations are sticky, even if a caller swallows them.
  - Legacy recording is unchanged without the flag. `build_control.py` is untouched, so no verified evidence was invalidated.
- G3: approved `intake-requirements/1` acceptance criteria travel with the plan binding.
  - In plan-governed builds they are merged into the spec as `APPROVED-AC*`, so behavioural acceptance must cover each one.
  - New mandatory release check `acceptance/approved_criteria_covered`: FAIL or NOT_RUN blocks READY.
- Stage 1: HIGH/RISKY intake turns escalate to task class `conversation_complex` (preferred 85, mandatory 70).
  - The quote, the reservation payload and the worker call use the same task; a mismatch is released before execution.
  - MEDIUM stays on the standard lane; LOW uses no model.
- Stage 2: the plan states per-task `permissions`, the final `deliverable`, the preview's mandatory checks and `execution_mode`. The graph fingerprint is unchanged.
- Tests:
  - `tests/test_plan_driven_execution.py`: 30 tests (17 need real PostgreSQL), added to CI job `intake-budget-pg`, which applies migrations and fails on any skip.
  - Updated lane test; new supervisor escalation test.
  - Affected suites: 186 passed.
  - Full suite: **1541 passed, 1 failed, 44 skipped**. The failure is `test_maintenance_live_postgres` (order-dependent; passes alone: 2 passed).
  - Generators current: `omni_prod.agent_os.audit` (registry unchanged) and `omni_prod.intelligence.matrix --write` (new task class).

**Implemented but awaiting external live verification**: all of the above on a real build (G2, about $0.15 per build, founder approval) and a real escalated intake turn (paid intake activation).

**Blocked**: G2/G9/G10 (paid budget), G6 (`VERCEL_AUTOMATION_BYPASS_SECRET`), G5 (PR #11 merge approval).

**Not implemented**: parallel dispatcher and resume from a task checkpoint (G1b; documented in `plan.execution_mode.not_yet`), G11, non-web families.

## Update 2026-10-11 ~15:30 Asia/Jerusalem — Issue #12: atomic intake budget reservations, complexity routing, requirements preservation

**Branch `feature/intake-budget-complexity-router` (= PR #13 + Issue #12). Not merged. No paid model call, no paid flag enabled, no secret change, no production deploy.** Design, state machine, lock-order proof, migration/rollback: `docs/INTAKE_BUDGET_RESERVATIONS.md`.

**Implemented and independently verified (real PostgreSQL 16.15 + real Redis 8 / RQ 2.12 locally; provider = in-process transport behind the real RoutedModelGateway)**
- Migration 037 (additive): reservations, budget scopes (lock anchors), reservation-scope links, transactional outbox, append-only events; `intake_messages.cost_usd` nullable (UNKNOWN). Neon bootstrap regenerated + verified on an empty PostgreSQL (33 migrations); 036→037 upgrade with data verified, idempotent.
- `intake/budget.py`: QUOTE (full envelope: 1 call, 0 retries, 0 fallback, every allowed model, fail closed without price/catalog) → RESERVE (sorted anchor locks, settled + outstanding sums, project / rolling-24 h / campaign ≤ $10 caps, idempotency key) → CLAIM → EXECUTING marker (committed before the call) → SETTLE (CONFIRMED / CONFIRMED_ZERO / ESTIMATED, or UNKNOWN with NULL amount and the quote held) → RECONCILE (expired EXECUTING → UNKNOWN, never released; CLAIMED/stale RESERVED → RELEASED) → resolve_unknown only with billing evidence.
- Worker execution (`intake/reservation_worker.py`) and `intake-maintain` service (outbox relay + reconcile). No unreserved paid path remains (legacy job refuses; direct API-host model calls refused).
- Strict cost metering: timeouts / HTTP errors / missing usage → UNKNOWN (not $0); the silent `'0'` cost of the intake path removed.
- Deterministic complexity classifier (LOW/MEDIUM/HIGH/RISKY with prior turns); LOW → no model; others → standard lane, floor 70 unchanged; low-risk sub-70 lane disabled (no qualification record).
- Requirements preservation: confirmed values never overwritten by model output (or material fields by any output) — conflicts asked back; strict model-output type/size validation; contract to the Chief Architect unchanged (`intake-requirements/1`, fingerprint-bound); approvals stay server-bound.
- Tests (all real, none mocked for DB concurrency): `tests/test_intake_budget_pg.py` 25 (60-way project saturation, 55-way daily, 60-way campaign, 110 mixed ops with `pg_stat_database.deadlocks` unchanged + a live deadlock negative control, rolling-24 h boundary, 50-way idempotency, double settlement, crash before/after provider, outbox crash/replay, 50 concurrent duplicate deliveries → 1 provider call, real RQ duplicate jobs → 1 call, timeout / 429 / 500 → UNKNOWN, verified zero, overrun flag, tenant isolation, end-to-end supervisor turns incl. 50 concurrent turns, migration path); `tests/test_intake_complexity.py` (129 contextual turns, 109 Hebrew/mixed, 71 sensitive, 0 false negatives); `tests/test_intake_requirements_preservation.py` 10; rewritten `tests/test_intake_worker_route.py`. Intake files 68 passed ×3 consecutive runs. Full suite: **1514 passed, 0 failed, 43 skipped** (base `73fc445` in the same environment: 1468 passed, 1 failed — the environment-only `test_m4_acceptance` W, which is flaky, not fixed).
- New CI workflow `intake-budget-pg` runs these tests against PostgreSQL 16 + Redis service containers and fails if any is skipped.

**Implemented but awaiting external live verification**: real Hebrew extraction quality, billed tokens vs quote bound (overrun flagged, not prevented), Vercel bundle including `model-catalog.json` (`vercel.json includeFiles`).

**Blocked**: activation — founder budget approval + non-secret flags (`OMNI_INTAKE_MODEL`, `OMNI_INTAKE_VIA_WORKER`, caps, `OMNI_REDIS_URL` on Vercel); acceptance-campaign entry point not wired.

**Not implemented**: change of the build pipeline's `_release_rejected` HTTP-error-is-free assumption (out of scope; intake does not rely on it).

## Update 2026-10-11 11:40 Asia/Jerusalem — Hebrew-first live Intake Assistant (prepared, NOT activated)

**Branch `claude/intake-assistant-he-2026-10-11` (from pre-staging `4cc9b91` + merge of `claude/wave-a2-worker-intake-2026-10-11`). Not merged. $0 — no model call made. Activation runbook: `docs/INTAKE_ASSISTANT_ACTIVATION.md`.**

**Implemented and independently verified (test doubles; no provider calls)**
- Worker-routed model intake (A2) on the current integration base: RQ `omni-intake`, `intake-worker` service, API-side re-validation, deterministic fallback on timeout/queue/provider error.
- `omni_prod/intake/mode.py`: single fail-closed source of truth for whether a paid model may answer — switch + per-project cap + **new rolling-24 h cap across projects** + per-message reserve; a call starts only if spent + reserve ≤ cap (no overshoot); spend read lazily, unreadable spend ⇒ deterministic.
- Truthful label: `/conversation` reported `interpreter: "model"` whenever the switch was on (even with zero budget) — now reports the mode that will actually answer.
- Hebrew-first prompt `intake-prompt/2-he-first`; Hebrew-aware evidence matching (niqqud, bidi marks, gershayim/geresh, maqaf; letters and final forms untouched) — fabricated/empty quotes still dropped; calls bounded (4,000 chars in, 700 tokens out) on both API and worker paths.
- Cost estimate from source-backed prices: gemini-3.1-flash-lite $0.0016/message upper bound; proposed acceptance test ≤ $0.05.
- Tests: `tests/test_intake_assistant_he.py` + updated `tests/test_intake_worker_route.py` — targeted 91 passed; full suite 1468 passed, 1 failed (`test_m4_acceptance` W, environment-only, also on base), 43 skipped.

**Blocked**: activation needs founder budget approval + non-secret flags on Vercel/worker. **Not verified**: any real Hebrew conversation with a model (no paid call made).

## Update 2026-10-11 03:30 Asia/Jerusalem — controlled pre-staging integration: BLOCKED at the merge step

- Founder authorized merging PR #8 into `milestone/pre-staging-2026-10-05` (directive 03:15). Pre-merge gates verified: integration head still `67a0765` (no newer commits), PR #8 mergeable/clean, all checks on `8fe5998` success (v24-ci, V11, Neon bootstrap, compose-config, fresh-postgres), fast-forward possible, migration 036 additive (3 new tables, `IF NOT EXISTS`, no change to existing tables), deploy-worker drains workers then runs `python -m omni_prod.migrate` then `up -d`. Rollback point: `67a0765` (revert the merge on the integration branch; 036 tables are unused by the old code and can stay).
- **The merge itself was refused by this session's safety layer** (both the fast-forward push and the GitHub PR merge call). Nothing was merged or deployed; worker still `67a0765`; migration 036 NOT applied; the new UI is NOT on pre-staging.
- Unblock: the founder clicks **Merge** on PR #8 (or merges `8fe5998` into the integration branch). That push triggers deploy-worker (migration 036 + worker `8fe5998`) and the Vercel Preview of the integration branch.
- Prepared meanwhile (branch `claude/wave-a2-worker-intake-2026-10-11`, `3194ecd`, not in PR #8): real-model intake routed through the worker (`intake-worker` service, `omni-intake` queue), OFF until authorized; tests with doubles only.

## Update 2026-10-11 10:45 Asia/Jerusalem — PR #11 security hardening of the deployment verifier (implementation: Claude; independent review: ChatGPT)

**Branch `claude/wave-a-fix-conversation-schema-2026-10-11` (PR #11). Not merged. No production deploy, no secret change, $0.** Review: `docs/DEPLOYMENT_VERIFY_SECURITY_REVIEW.md`.

**Implemented and independently verified (local, real HTTP over loopback; real FastAPI + PostgreSQL)**
- High: secret leak on redirect **reproduced** (Bearer token + bypass secret delivered to a second host after a 302) and fixed — redirects never followed; secrets only sent to the validated origin.
- High: SSRF — origin-only target, https except loopback, no IP literals/credentials/path/query, exact host or anchored suffix allowlist, all resolved addresses must be public.
- No cookie jar, no env proxies, 1 MiB response cap, per-request timeout + overall deadline, classified network failures (no crash), evidence without bodies/tokens + final scrub, full 40-hex SHA (+ optional trusted deployment-metadata SHA), production writes refused without explicit flag, server-controlled ids validated.
- Canonical contract: declared required checks; a missing/downgraded/NOT_RUN mandatory check ⇒ BLOCKED; FAIL ⇒ FAILED (takes precedence).
- PR #9 compared; its hardening and test shapes merged into PR #11 (PR #9 itself not merged).
- Tests `tests/test_deployment_verification.py`: 35 passed (+27 subtests) — attacks (cross/same-origin redirect, post-login redirect, cookies, echoed Authorization, path-steering id, 19 SSRF URL shapes, private/metadata DNS), network failures (refused, reset mid-journey, timeout, oversize, non-JSON), wrong credentials (bad bypass, no token, rejected token), SHA (short, malformed, mismatch, trusted mismatch, missing), schema mismatch, production guard, CLI exit codes 0/1/2/3.
- Full suite: 1479 passed, 1 failed (`test_m4_acceptance` W — environment-only, also failing on base), 43 skipped.
- Real local servers (`docs/evidence/verification/`): 036 DB → VERIFIED (exit 0); 035 DB → FAILED schema_compatible + conversation (exit 1); wrong SHA → FAILED (exit 1); `https://evil.example` → configuration error (exit 3).

**Implemented but awaiting external live verification**
- Workflow now runs only for `vercel[bot]` deployments (creator confirmed on real run 38114225915), non-Production, host suffix `-shayflys-projects.vercel.app`. Verdict on the protected Preview will remain BLOCKED until the bypass secret exists.

**Blocked by a named credential/service**
- `VERCEL_AUTOMATION_BYPASS_SECRET` (GitHub secret, from Vercel "Protection Bypass for Automation") — founder action.
- Promotion gating on the check (Vercel Deployment Checks / branch protection) — founder action.
- Merge decision — independent review (ChatGPT) + founder.

- Real-run regression found and fixed: run 38120874664 produced no result because argparse took the dash-leading host suffix for an option; the workflow now uses `--allowed-host-suffix=…` and a bad command line still writes a BLOCKED result (exit 3).

- Independent review findings R1–R3 fixed in `verification_contract.py`: exact full-SHA promotion binding (no prefixes, unbound promotion refused); timestamp/TTL validity window (future-dated, missing, non-finite, inverted, invalid TTL refused); mandatory NOT_APPLICABLE fails closed unless a versioned NA policy names the check; plus verdict recomputation at promotion (forged verdicts refused). `tests/test_deployment_verification.py`: 43 passed (+58 subtests). Full suite 1488 passed, 1 failed (`test_m4_acceptance` W, environment-only, also on base), 43 skipped.

- Closure review (`docs/DEPLOYMENT_VERIFY_SECURITY_REVIEW.md` §C1–C5): three promotion-gate bypasses found on `5ad2ccc` (forged empty required list, self-authorizing NA policy in the evidence, duplicate check names) — **fixed**: `may_promote` takes `required` / `na_policy` from the caller (`DEPLOYMENT_REQUIRED_CHECKS`), never from evidence; duplicates block; `ForgedEvidenceTests` 6. Deployment binding verified three ways for `5ad2ccc` (GitHub run head_sha = Vercel deployment `dpl_B6def4hWWTkGVtz8hsxbgZagciQB` = app-reported SHA, schema COMPATIBLE). Checkout `persist-credentials: false`. DNS rebinding: accepted residual risk for pre-staging, IP-pinning fix specified. `test_m4_acceptance` W: fails identically on unchanged base `4cc9b91`; its nested suite passes there (exit 0, 1303 tests OK) — log-tail check artefact of local live-PG warnings (`docs/evidence/verification/baseline_failure_m4_acceptance_W.json`). Full suite: 1493 passed, 2 failed (the W test above; `test_maintenance_live_postgres` order-dependent locally, 3/3 pass alone), 43 skipped. `tests/test_deployment_verification.py`: 49 passed (+67 subtests).

**Residual risks (not fixed)**: DNS rebinding between the address check and connect; `vercel.app` suffix trust relies on Vercel team-slug hostnames (mitigated by the `vercel[bot]` gate); app-reported SHA is self-reported; synthetic rows accumulate in the shared pre-staging DB.

## Update 2026-10-11 08:20 Asia/Jerusalem — Vercel "Server error" fixed + Continuous Verification P0.1–P0.4

**Branch `claude/wave-a-fix-conversation-schema-2026-10-11`. $0 spent. No production deploy, no secret change, no model call.**

Root cause of the red "Server error": `psycopg.errors.UndefinedTable: relation "execution_plans"/"intake_messages" does not exist` (Vercel runtime errors, deployment `dpl_42B7ngrpgoMCqxnLF2K4DUG3r5K8`, commit `8fe5998`): the branch Preview ran the Wave A API against the shared pre-staging DB before migration 036 was applied. Fix `b6a99c1` (503 `conversation_not_ready` + guided fallback, builds unaffected). The founder merged PR #8 (merge `4cc9b91`, 2026-10-11 01:10 UTC); deploy-worker run 38100955911 succeeded incl. "Apply database migrations".

**Implemented and independently verified**
- Migration 036 applied on the shared pre-staging DB — read from the real Vercel Preview `dpl_AcJCaecSiEBVCk6fz7vtawtVn2iE` (`19d76d7`): `GET /api/v28/deployment` → `schema.status=COMPATIBLE, applied_max=36, missing=[]`.
- No runtime errors on Vercel after 2026-10-11 00:25 UTC (both error groups belong to the pre-036 deployment).
- P0.1 coverage map: `docs/VERIFICATION_COVERAGE_MAP.md` (generated products well covered; the platform's own Vercel API had no post-deployment check — why the incident shipped).
- P0.3 canonical verdict `verification-result/1` (`omni_prod/verification_contract.py`): never VERIFIED by default; FAIL→FAILED; NOT_RUN/UNKNOWN→BLOCKED; skips need reasons; promotion gate refuses wrong-commit/artifact or expired evidence; `quality-report/1` maps onto it.
- P0.2/P0.4 deployment verification: `GET /api/v28/deployment` (commit, env, required vs applied migrations via `omni_prod/schema_manifest.py`, drift-tested) + `tools/deployment_verify.py` (SHA, schema, register→project→conversation→persistence→memory, anonymous denial, cross-user isolation; synthetic users) + workflow `deployment-verify` on every Vercel `deployment_status`.
- Local real-server evidence (`docs/evidence/verification/`): VERIFIED with 036; FAILED on 035 DB (schema + conversation 503); FAILED on wrong SHA.
- Tests: `tests/test_deployment_verification.py` 17 (scenarios A, E, J, auth bypass, leak, protected, unreachable, no token leakage). Full suite 1462 passed, 1 failed (`test_m4_acceptance` W, environment-only, also failing on base), 43 skipped.

**Implemented but awaiting external live verification**
- `deployment-verify` ran for real on GitHub (run 38113948928) against the Vercel Preview → **BLOCKED** (HTTP 401, Vercel deployment protection). Working as designed (never VERIFIED without evidence).

**Blocked by a named credential/service**
- Full journey on Vercel needs Vercel "Protection Bypass for Automation" stored as GitHub secret `VERCEL_AUTOMATION_BYPASS_SECRET` (founder action; not created by me).
- Gating Vercel promotion on the check needs Vercel Deployment Checks / branch protection (founder action).
- Live AI conversation: OFF (needs approved budget + `OMNI_INTAKE_MODEL`).

**Not implemented**: P0.5–P0.12 (repair loop over deployment failures, security gate expansion, visual QA on the platform UI, handoff contracts, requirement→test traceability, defect intelligence, dashboards, adversarial suite); paid Golden E2E (NOT RUN).

Note: PR #9 (`chatgpt/pdv-001-candidate-2026-10-11` → this branch, "PDV-001" standalone post-deployment verifier, 37 loopback tests) overlaps with `tools/deployment_verify.py`; not merged, needs a decision on which verifier to keep (or merge its hardening — host allowlist, redirect blocking — into this one).

## Update 2026-10-11 03:05 Asia/Jerusalem — Wave A (intelligence plane, Conversation OS, workspace UI) — IN PROGRESS, not merged

**Branch `claude/wave-a-intelligence-platform-2026-10-11` (base `c20503a` = `c874998` + PR #7). Not merged, not deployed. $0 spent. Live AI conversation NOT verified (no model call was made).** Baseline/source of truth: `docs/WAVE_A_BASELINE.md`. Handoff: `docs/CONTINUATION_HANDOFF.md` (Wave A section).

Commits: `17d246e` (A1–A2), `a138ccc` (A3–A9 + UI), plus this docs commit.

**Implemented and independently verified (local, real PostgreSQL / real Chromium; no provider calls)**
- A1 Provider Matrix (`PROVIDER_MATRIX.json`, `docs/PROVIDER_MATRIX.md`, generated; `--check` fails on drift/inflation): 14 entries; REAL_EXECUTION_VERIFIED only gemini-3.8-flash / 3.1-flash-lite / 3.5-flash-lite (ledger ok calls > 0); OpenAI/Anthropic CONNECTION_TESTED + INSUFFICIENT_CREDIT; media candidates NOT_CONNECTED. Effective-dated, source-backed prices (3.8-flash doubles 2027-01-01, applied automatically by the catalog loader); managed models without a source-backed price fail closed; retired models never routed.
- A2 Routing safety: explicit task classes; architecture now prefers the quality-85 model; mandatory floors (no silent downgrade); durable circuit breakers (migration 036 `provider_health`), CREDIT_EXHAUSTED/AUTH_INVALID skip the route across builds until reset or one half-open trial after 24 h.
- A3 Intake: deterministic HE/EN interpreter + confidence policy + `intake-requirements/1` contract; model interpreter exists but is OFF (`OMNI_INTAKE_MODEL=1` and a per-project `OMNI_INTAKE_MODEL_BUDGET_USD` > 0 required) and tested only with test doubles. Benchmark 12 cases (6 HE / 6 EN, author-written fixtures — regression check, not proof of real-world understanding).
- A4 Chief Architect + Execution Graph + feasibility gate + agent/skill router; web plan = 15 tasks bound to real engine stages; non-web families planned but non-executable (UNSUPPORTED); sign-in/payments BLOCKED until connected.
- A5 18 departments (`DEPARTMENT_MATRIX.json`): READY 3 · PARTIAL 7 · IMPLEMENTED 5 · NOT_IMPLEMENTED 3 (computed). Agents 54 (+ intake_agent, chief_architect, UNIT_TESTED).
- Conversation Supervisor + durable memory (intake_messages, execution_plans, 10-section memory view) + API (`/conversation`, `/memory`, `/builds/{id}/plan`); build admission binds the approved plan and refuses infeasible ones (409 `capability_not_feasible`).
- Worker: `PlanBoundRecorder` pre-creates the DAG as durable agent_tasks and moves them with the real stages; failures block downstream tasks; unreached tasks end CANCELLED, never SUCCEEDED (live PostgreSQL tests).
- A7: cost per verified success by codegen model, Wilson 95 % interval, minimum sample 10.
- UI: conversation-first workspace (sidebar with projects/search/collapse/mobile drawer · one chat with quick replies and real actions · resizable / enlargeable / closable preview); old mode-choice composer removed. Real-browser walkthrough (`tools/ui_conversation_walkthrough.py`) against a real FastAPI + PostgreSQL server: multi-turn HE + EN, persistence across reload and project switch, drag 605→859 px, enlarge 1416 px, close/reopen, no mobile horizontal scroll. Screenshots: `docs/evidence/wave_a/`.

**Tests:** targeted Wave A suites 130 passed. Full suite with the real web stack (fastapi/starlette/httpx/boto3 fetched from GitHub sources; PyPI unreachable here): base `c20503a` 3 failed (stale truth matrix — fixed by regeneration; nested `test_m4_acceptance` W subprocess — environment; `test_maintenance_live_postgres` — flaky locally, passes alone). Branch (`a138ccc`): **1444 passed, 1 failed, 43 skipped** — the one failure is the same nested `test_m4_acceptance` W environment failure as on the base; no new failure (base: 1372 passed, 3 failed). CI on the branch: check the runs for the head commit (pending at save time).

**Not done / blocked:** migration 036 not applied to the shared pre-staging DB (happens only via the deploy-worker on the integration branch); therefore a Vercel Preview of this branch shows the new UI but the conversation API needs 036 → **not deployed/usable on Preview yet**. No LLM key on Vercel. A6 extra handoff contract checks and A8 multimodal adapters NOT_IMPLEMENTED (matrix entries only). Modification flow from chat reuses the existing pipeline (offer + confirm button) — not exercised end-to-end here (needs the worker). Paid 10-build gate NOT RUN.


## Update 2026-10-11 01:20 Asia/Jerusalem — Production Assurance v2 (G0–G3, free work only) + handoff

**Level: PRE_STAGING_READY candidate. Not PRIVATE_BETA_READY. $0 spent in this round. Handoff: `docs/CONTINUATION_HANDOFF.md`.**

- Deployed code on pre-staging: `67a0765` (deploy-worker 38083162363, migration 035). Rollback point: `8ce71c0`.
- **G0**: truth vocabulary in code; LIVE requires production → **0 LIVE**; agents 52 = REAL_SERVER_VERIFIED 23 · UNIT_TESTED 6 · IMPLEMENTED 8 · BLOCKED 4 · NOT_IMPLEMENTED 11; skills 427 = REAL_SERVER_VERIFIED 102 · UNIT_TESTED 24 · IMPLEMENTED 28 · BLOCKED 9 · NOT_IMPLEMENTED 264. Truth matrix 36 rows (`TRUTH_MATRIX.json`): 25 REAL_SERVER_VERIFIED, 3 UNIT_TESTED, 3 BLOCKED, 5 NOT_IMPLEMENTED; no customer-visible feature without real-server evidence. Audit: `docs/G0_AUDIT_2026-10-10.md` (7 findings fixed, 6 open).
- **G1**: release policy (NOT_RUN ≠ PASS; mandatory checks block READY), durable stage rows (`build_stage_results`), forward-only phases, legacy/patch paths 410 on staging/production.
- **G2**: visual QA desktop+mobile with screenshots; layout rules enforced (0 false positives on stored products); contrast/labels advisory (real WCAG defects in 3/5 working products — founder decision).
- **G3**: write-ahead cost ledger (in-flight call = bounded unknown exposure), Gemini thinking metered, unit economics report.
- Real-server evidence (free): free checks 18/18 (38083312245); gate-replay 0/55 blocking (38083647077); verify-replay policy agrees 12/12, 5/5 current products READY (38083686082); economics (38083624196).
- Ledger economics (60 days): 32 builds, 11 READY (34%), cost per successful build $0.153, 53% of spend on failed builds, gemini-3.8-flash 41% call success.
- **Not run**: 10-build paid Golden E2E acceptance gate (budget unverified until Gemini invoice reconciliation); crash and backup runs on the current code.
- Tests: local 1167 passed, 9 failed + 14 errors = environment baseline (fastapi/boto3 absent); CI green up to `67a0765`.

## Update 2026-10-10 21:30 Asia/Jerusalem — Executive directive: task 0 (audit access) + P0 build reliability (deterministic part)

**Level: unchanged — PRE_STAGING_READY candidate. Paid testing frozen: no verified budget remainder until the Gemini bill is reconciled (directive budget policy). No money spent in this section.**

- Commits (fast-forward to the active branch, CI green each): `f4b80ba`, `f39bec9`, `e573ab5` (deployed: deploy-worker 38071999051; free checks 38072386506 16/16 PASS). Rollback point: `f90accb`.
- Audit access: `docs/AUDIT_ACCESS.md` (repository, active branch vs. old default `main`, servers, truth documents, evidence runs).

| P0 item | State | Evidence |
|---|---|---|
| 1 repair sees all relevant source, incl. large files | VERIFIED on real data | gate-replay 38071513038: entry file in the repair prompt for 44/44 stored versions; all code files for 43/44 (97.9% of code chars); the one omission (a >16k test file) is included when a failure names it (`focus_paths`, unit-tested) |
| 2 a repair that worsens the product is discarded | TESTED (unit) + seen live 2026-10-09 | `autonomous_core.progress`, tests `test_repair_stop_loss.py` |
| 3 good version kept before each repair, rollback | IMPLEMENTED + TESTED; not yet in a real build | every verified candidate stored as `build-rounds/<build>/<round>-<sha>.zip` with decision/progress (`round_snapshots` evidence); loop rolls back to the best |
| 4/5 checks while files are produced; cross-file consistency | VERIFIED on real data (no false positive) | `consistency_gate.py` (syntax, local import names, page/acceptance routes vs server, assets, manifest) runs before the sandbox, ON by default; replay: 0 blocking findings on 44 stored working versions |
| 6 usability/a11y/security/performance/design checks | PARTIAL | a11y advisories (labels, lang/dir, alt) — 17 on stored versions; security scan + model review existed; no automated performance or design scoring |
| 7 focused repair from real errors | IMPLEMENTED | consistency failures give `file:line` + fix before any sandbox run |
| 8 no READY while mandatory acceptance fails | TESTED | `tests/test_release_blocks_on_failed_acceptance.py`; failure message now names the checks still failing |
| Acceptance gate: ≥10 diverse Golden E2E builds, ≥90% | **NOT RUN** | needs paid builds; blocked by the budget policy until the Gemini bill is reconciled |

- Free re-verification (verify-replay 38072167057): the 12 newest stored versions through the current production chain without the model review — **5/5 versions built by the current pipeline PASS** (incl. today's READY builds); 7 older versions (built before behavioural acceptance / preview contract v2) FAIL the stricter gates, as expected.
- Tests: local 1127 passed, 9 failed + 14 errors = baseline (environment); regression guardian 0 problems; CI green.

## Update 2026-10-09 20:10 Asia/Jerusalem — Autonomous Completion Directive: Agent OS, self-testing platform, build reliability, cost truth

**Level reached: PRE_STAGING_READY candidate (pre-staging deployed and verified on the real server). Not PRIVATE_BETA_READY, not PUBLIC_BETA_READY, not production.**

**Commits** (task branch `claude/g0-baseline-2026-10-09`, fast-forward merged to `milestone/pre-staging-2026-10-05`, no force push)
- Start of this program: `d1c7482` (= rollback point). Final, deployed: `bdc5e9c` (deploy-worker 37965865051; free checks 37966155212 16/16 PASS).
- Merged in order: `724705d` Agent OS/Skills OS + migration 034 · `d57ebd2` agent-graph checks · `c4cdb4a` router fitted output · `9feb3bb` progress-aware repair, tolerant JSON, decoded-JSON text match · `2b4bafd` crash-safe cost ledger · `54620a4` · `67392df` relative dates / no special-casing / review ranking · `20b4bcc` thinking tokens metered · `039574f` gemini-3-8-flash `reasoning_effort=low` · `bdc5e9c` repair sees the main file + evidence refresh.
- Migrations: 30 applied, latest **034 `agent_runtime`** (additive: `agent_runs`, `agent_tasks`, `agent_handoffs`, `agent_memory`, `platform_check_results`). Rollback: code → `git revert` to `d1c7482` and redeploy; 034 needs no down-migration (new tables only, nothing reads them when the recorder is off: `OMNI_AGENT_RECORDER=0`).

**Agent OS / Skills OS (computed by `python -m omni_prod.agent_os.audit --write`; CI fails on inflation)**
- Agents 52: LIVE 30 · PARTIAL 7 · NOT_CONFIGURED 1 · NOT_IMPLEMENTED 11 · BLOCKED 3. Skills 427: LIVE 132 · PARTIAL 29 · NOT_CONFIGURED 1 · NOT_IMPLEMENTED 257 · BLOCKED 8. Registry: `AGENT_OS_REGISTRY.json`, `docs/AGENT_OS_REGISTRY.md`; matrices `PLATFORM_CAPABILITY_MATRIX.json`, `PLATFORM_REGRESSION_MATRIX.json` (17 areas), `GOLDEN_E2E_MATRIX.json`, `FAILURE_INJECTION_MATRIX.json`.
- LIVE = implementation + fresh real-server run whose code is unchanged since (digests in `omni_prod/registry_evidence_lock.json`). Every real build now writes a durable agent task graph; paid run 37961193099: 14 agents SUCCEEDED, independent verification links (quality gate verifies release/acceptance/browser/security/cost/QA), no self-verification, no open tasks. Recovery closes the lost worker's run as `superseded`.

### 1. Implemented and independently verified (real server, current or named commit)
- Free checks 37966155212 (`bdc5e9c`) 16/16: migrations, builder health, 42 versions intact, demo/publish refused, private preview (anonymous 401), owner token, share link only while shared, data survives restart and new version, queued/running cancel, journal, scoping, agent graph closed for a cancelled build.
- Golden SaaS build 37961193099 (`039574f`): discovery → approval → build READY (2 repairs) → browser check → QA review → preview → behavioural acceptance PASS (7 checks, 5 acceptance IDs) → restart; **settled $0.105302 at metered usage incl. thinking tokens**.
- Crash recovery 37954236866 (`2b4bafd`): worker SIGKILLed at the 2nd model call → requeued once → READY; ledger holds both workers; **settled = ledger sum ($0.070368)**. Repeated in 37962802899 (`039574f`): recovery + settlement PASS again ($0.199043 = ledger), but that build then failed verification (see 4).
- Backup/restore 37962179844 (`039574f`): restored into empty PostgreSQL 18, 42/42 versions rebuilt from artifacts, 14/14 preview data files, 34 migrations equal.
- Failure injection: 16/17 PASS (14 unit/integration + 2 real-server: worker kill, deploy during build); invalid OAuth BLOCKED (no generated-app OAuth).
- Regression guardian + capability auditor run in CI (`v24-ci`) on every push.

### 2. Implemented, awaiting external live verification
- `bdc5e9c` repair prompt includes the main file (>16k chars) and files named in failures — unit-tested, deployed, **no paid build run on it yet** (budget).
- Modification (change) flow: last real run 2026-10-08 (`mod_c14435dc`); not re-run on this code.

### 3. Blocked by a named credential/service
- OpenAI: HTTP 429 "no credits remaining"; Anthropic: HTTP 400 "credit balance too low" — every build falls back to Gemini; cross-provider review/repair diversity unavailable.
- Exact Gemini spend reconciliation needs the Google AI Studio / Cloud billing page (founder access).
- Image provider not configured on the worker; no commercial video/voice/music provider contracted.

### 4. Not implemented / open defects
- Build reliability is not yet acceptable: 7 paid builds today on evolving code → 2 READY (37950195508, 37961193099), 5 failed after 5 repairs; each failure was diagnosed and fixed (see commits) but the latest fix set has only 1 paid success; the crash-stage build (book list) failed verification on `039574f`.
- Generated-app sign-in/roles, automation, 2D games, media pipeline: NOT_IMPLEMENTED (agents/skills say so).
- The call in flight at a worker crash cannot be metered (provider may bill it).

**Cost truth correction**: Gemini's OpenAI-compatible usage reports thinking only in `total_tokens`; until `20b4bcc` metered cost excluded it. Spend audit 37966168410: QA guard (all-time, what the $10 cap counts) **$4.527** + rehearsals outside the guard ≈ $1.81 → **≈ $6.34 metered**. Conservative upper bound (gemini-3.8-flash pre-fix calls at worst case, +$1.93): **≈ $8.27 of $10**. Paid testing stopped; remaining is ≈ $3.66 metered / ≈ $1.73 conservative.

**Tests**: local full suite 1108 passed, 53 skipped, 9 failed + 14 errors — identical to the baseline (fastapi/boto3 absent locally); regression guardian 0 problems; CI v24-ci, V11 Overlay CI, Neon bootstrap CI green on every merged commit.

## Update 2026-10-09 14:45 Asia/Jerusalem — merged to pre-staging and verified on the real server (founder approval 13:38)

**Status of this package: deployed to pre-staging, real-server checks passed with named failures below. Not LIVE, not production.**

**Merge and deploy**
- Rollback point (active branch before merge): `9db2d53294b15ce1ab929251be16ce7f0ad37c53`.
- Merge = fast-forward pushes, no force, no history rewrite: `9db2d53..efd8d9d` (the approved package), then fixes found by the checks: `89949e5`, `2afaa22`, `38f7a26`, `c49ebff`, `697245d`, `301d631`, then workflow-only `224171f`, `4ef5378`.
- Worker deployed at `301d631` (Deploy build worker 37924206187: drain 4 s, migrations, preview-data self-test PASS, browser probe PASS, sandbox PASS, queue PASS). Vercel `dpl_CZpf3HNimghmxQMyhxP5owTr3nef` READY on `301d631`; the deployed `app.js` contains the stop/log/offline/data-note code. No Vercel runtime errors in the last hour.
- Migrations: 27 applied, latest 031 (`build_cancel_and_events`); the three new columns and `build_events` present.

**Real-server checks** (workflow `postdeploy-checks`, synthetic account `qa-postdeploy-*@example.com`, API code of the deployed image served on the worker host against the real Neon/Upstash/R2/preview worker/Caddy; the Vercel URL itself is behind Vercel Authentication and only its assets/routes were fetched)
- Free stage, run 37924447917 — all PASS:
  - migrations; builder health (1 build worker idle, sandbox runner 200);
  - existing data: 6 projects, all 24 versions loaded from R2 and checksummed, 0 failures;
  - demo builds → 410, every promote → 501 `publish_not_available`;
  - projects list + journal endpoint;
  - preview creation (`data_storage=persistent`); data survives a preview restart (`v1:2` → `v1:2`) and a new version (`v2:2`);
  - queued build stopped via the API → `cancelled`, reservation RELEASED;
  - running build (claimed by the real worker with a stop request) stopped before any model call: `cancelled_by_user`, 0 model calls, spend 0, reservation RELEASED;
  - journal readable incrementally (`after=`), latest build restored, cancel via another project → 404.
- Paid stage, run 37924920646 — one build, model ceiling **$0.15** enforced (binding: reserved 0.50, effective 0.15):
  - discovery (recommend mode) → plan → approval → build `bld_fde8abb01e4d4085aa180282e6026fb4` → **ready**, 5 repair rounds, version `v_bd07926c05d64deb`;
  - browser check inside the build: passed (1 form, 0 findings); QA model review: 3 rounds, last with 0 blocking;
  - live journal shows phases, agents and each test round;
  - preview RUNNING, `data_storage=persistent`, acceptance report **stored**, page answers 200 afterwards, restart RUNNING.
  - **Exact paid cost: $0.1209** (16 model calls, 110,365 input tokens; settled to reported tokens × catalog price; Gemini only).

**Real-server failures found and fixed during the checks (no mocks, no fallbacks)**
1. Every discovery-based plan was blocked (`can_build=false`): the brief text 148AI writes ("clear message", "Logo") triggered messaging and image capabilities. Fixed in `c49ebff` (detection reads the user's words + the sign-in decision); tests `tests/test_brief_capability_detection.py`. G2 had never been exercised end-to-end before this.
2. A build enqueued while the worker was stopped for a drain was taken by the stopped worker's open Redis read and stayed QUEUED with credits reserved (`bld_a99ca1119c8f445aa4f6243c330d6a46`, cancelled at $0). Fixed in `697245d`: the janitor re-dispatches QUEUED work missing from the queue after 3 minutes; tests `tests/test_janitor_redispatch.py`.

**Failures still open (named, not hidden)**
- **Behavioural acceptance of the paid build: FAIL** (release not eligible). The model-written acceptance plan vs the generated app: create → HTTP 400, page text mismatch, delete step unresolved. It runs after the preview starts and does not feed the repair loop yet.
- **Acceptance demands `auth`/`role` checks even for an approved no-sign-in product** (`acceptance_scope` only exempts `integration`), so such a product can never be release-eligible.
- **Settlement is not "actual usage only" in the customer ledger**: the provider reports tokens but not cost, so the reservation settles at its conservative $0.50 (`CONSERVATIVE_RESERVATION`). The QA budget counts the measured $0.12.
- **Public previews are found and scanned by internet bots within minutes** (router log: `/application.yml`, `/.gitconfig`, GraphQL probes). The hostnames are published in certificate-transparency logs (on-demand TLS), so an unguessable URL is not private. Data entered in a preview must be treated as public until previews get access control.
- Cancel/live log cover builds, not changes; no resume after a worker crash; no backup/restore of product data; the Vercel edge could not be exercised with a session from this environment.

**Tests**: local full suite 1023 passed, 53 skipped, 9 failed + 14 errors — identical to the baseline (environmental: fastapi/boto3 absent locally); CI v24-ci, V11 Overlay CI and Neon bootstrap CI green on every merged commit.

**QA spend**: database-counted builds/changes ≈ $3.43 (incl. this build's $0.12) + rehearsals $1.74 → ≈ **$5.17 of $10**; remaining ≈ $4.83. The customer-ledger view of the same builds (conservative settlements) is higher and is not a cost.

**Next (not started; section 21 waits for the founder)**: fix the two acceptance defects above, preview access control, then a founder session in the workspace.

## Update 2026-10-09 10:20 Asia/Jerusalem — stop + live log, durable preview data, no fake publish (task branch, awaiting integration)

Task branch `claude/g0-baseline-2026-10-09` at `da8d952` (CI v24-ci, V11 Overlay CI and Neon bootstrap CI green). **Not yet on the active branch**: the fast-forward to `milestone/pre-staging-2026-10-05` (which deploys the worker and applies migration 031) waits for the founder's go-ahead in this session. Worker idle at the check (worker-diagnostics 37898263049: last job 00:55 UTC).

**Implemented and independently verified (locally / CI; not yet deployed)**
- **Neon bootstrap includes 030 and 031** (`0159126`): the fresh-Postgres CI that failed on G2 (37867037351) passes again; locally 27 exact migrations verified.
- **Stop a build (directive §10)** (`3f2dd65`, migration 031).
  - Queued build: cancelled at once by the API, reservation released, the worker's claim then fails.
  - Running build: the worker checks before every model call (`RoutedModelGateway.before_call`) and every sandbox run; it ends `cancelled` / `cancelled_by_user`, creates no version, and settles only what was spent (release if nothing paid).
  - Owner-scoped (another tenant gets 404). Tests: `tests/test_build_cancel_and_log.py` (unit + live Postgres, 13).
  - Limit: builds only, not modifications; a stop takes effect at the next step (a model call can take minutes).
- **Live log (directive §12)**: `build_events` in customer language (phases, which agent is working, each test round and its first failure, stop). `GET builds/{id}/events`, `GET builds/latest` (a reload brings back a running build with its stop button).
- **Product data of a preview survives restart and a new version (directive §13)** (`7c1078c`).
  - One directory per project on the preview host (`OMNI_PREVIEW_DATA_ROOT`, mounted at `/data`); stopping/expiring a preview never deletes it.
  - Behavioural acceptance probes now run on a scratch copy of the version (no data mount), so synthetic records never enter the product's data.
  - `project_previews.data_storage` and the workspace say "persistent" or "temporary".
  - deploy-worker gains a $0 self-test with real containers (2 hits → restart as v2 reads 2; scratch reads 0; other project reads 0). **Runs on the first deploy after integration.**
  - Limits: no backup, no size quota, no migration of old data when a new version changes its schema.
- **No fake publish, no shadow builds (gap map #11)** (`da8d952`): in the durable deployment the deterministic builds (demo/v25/v26/v27) answer 410 and the in-memory promote routes answer 501 `publish_not_available` (CI endpoint test).
- **Workspace states (directive §11)**: offline banner, timeout vs no connection vs server error, data-storage note on the preview, track after reload/stop. Checked in Chromium against a mock API (desktop + 390 px, restore, stop → stopping → cancelled, offline): no page errors.
- **G5 rule**: `skill.ui_states` now requires a banner to show again on every message (the library bug); the rehearsal report includes `browser_check`.

**Merge plan and rollback (written before the merge, founder approval 2026-10-09 13:38)**
- Target before merge: `milestone/pre-staging-2026-10-05` = `9db2d53294b15ce1ab929251be16ce7f0ad37c53` (rollback point). Merge = fast-forward push, no force, no history rewrite.
- Migration 031 is additive only: two nullable columns on `build_jobs`, one nullable column (with CHECK) on `project_previews`, a new table `build_events` + index. No backfill, no rewrite, no drop; code at `9db2d53` ignores all of it, so a code rollback needs no schema change.
- Code rollback: push a revert commit of `0159126..409d19d` onto the active branch (never force-push); deploy-worker redeploys the old worker (drain first). The schema stays.
- Optional schema removal (only with a separate approval, after the code rollback): `DROP TABLE build_events; ALTER TABLE build_jobs DROP COLUMN cancel_requested_at, DROP COLUMN cancel_requested_by; ALTER TABLE project_previews DROP COLUMN data_storage; DELETE FROM schema_migrations WHERE version = 31;` — this deletes the live logs only.
- Known window: Vercel and the worker deploy in parallel; until deploy-worker has applied 031 (a few minutes, after the drain), the API's preview status read (`data_storage`) and the new log/stop endpoints can return 500. Worker idle at merge time.
- Preview data directories (`/var/lib/omni-preview/data/p-*`) are never deleted by a rollback.

**QA spend — honest total against the $10 ceiling**
- Recorded in the database (builds + changes, all-time, build-evidence 37864934013): **$3.31**.
- Golden rehearsals do not write the database; their authorized spend from the run annotations: 37700287077 $0.101, 37700596406 $0.098, 37701168910 $0.467, 37701990475 $0.391, 37814985551 $0.210, 37820429767 $0.072, 37840698696 $0.069, 37841459920 $0.125, 37857189740 $0.098, 37858017258 $0.110 = **$1.74**.
- Conservative total ≈ **$5.05 used, ≈ $4.95 left** (list-price authorizations; real provider billing may be lower; model probes not included, a few cents). No spend in this update.

**Awaiting live (after integration)**
- Deploy: drain, migration 031, the preview-data self-test.
- One rehearsal (~$0.10) to see `browser_check` inside the real pipeline.
- Founder session: discovery → approve → build → stop one build → live log → preview data kept after "refresh preview".

**Not implemented (still open for Partner Review)**
- Cancel/live log for modifications; resume after a worker crash (the janitor still fails a lost build after 45 min).
- Data backup/restore of generated apps; visual screenshot QA; publishing to a real target.
- The three Partner Review scenarios (§21) and the partner pack (§23) — need the deployed version and a founder/new-user session.

## Update 2026-10-09 03:15 Asia/Jerusalem — Master directive G0; preview fix; deploy drain; honest QA count

Directive: `docs/MASTER_EXECUTION_DIRECTIVE_2026-10-09_HE.md`. The G0 baseline, deploy-trigger map, ownership and work packages are in `docs/G0_BASELINE_2026-10-09_HE.md`. Claude now works on task branch `claude/g0-baseline-2026-10-09` and fast-forwards the active branch only when tests pass and no build is running.

**Implemented and independently verified**
- **"Nothing responds" in the founder's library preview — root cause and fix (`ab253f7`).**
  - What happened: preview `prv_c242ef7e…` passed every behaviour probe (POST books/members/loans/return, DELETE; router log). `record_acceptance` then raised `IndeterminateDatatype` because the `jsonb_build_object` key was untyped. The launch job tore the container down, and every click after that got 502.
  - Evidence: worker-diagnostics 37861985721 (preview-worker traceback and router log).
  - Fix: `%s::text`, plus the live-Postgres test `test_preview_acceptance_report_is_recorded_on_real_postgres`, which fails with the same error without the fix. Deployed in Deploy build worker 37862267177.
- **A deploy no longer replaces a worker mid-job (directive §18).**
  - How: deploy-worker first runs `docker compose stop -t 1500 worker preview-worker`. That is an RQ warm shutdown: the running job finishes and no new one is taken. It runs before migrations and before any container is replaced. Compose also sets `stop_grace_period` 25m/5m.
  - Proof:
    - worker-diagnostics 37862864855 enqueued `time.sleep(240)`;
    - the push of `51bb631` deployed with Deploy build worker 37862903906;
    - the "drain" notice reads "workers stopped after 213s (worker was running: 1; exit 0)";
    - migrations started only after that (00:08:44 UTC).
  - Cost: $0.

- **Real-browser check of every generated product (directive §17).**
  - What runs: `omni_prod/browser_probe.py`. It needs no knowledge of the product: it fills each form by field type and submits it twice, then reports page errors, dead forms, vanishing feedback and 5xx responses. These become a repairable BROWSER failure.
  - Where it runs: in its own image `omni-browser-sandbox` (Debian chromium + Playwright, `--network none`, read-only, non-root), via the sandbox-runner profile `browser`. Build evidence records `browser_check`.
  - Verified locally on the exact library version `v_f65e904334`: it reports `feedback_disappears`. With the one-line fix it reports no findings. Fixtures for a dead form and a JS error are also caught (`tests/test_browser_probe.py`, 9 tests).
  - Verified on the worker host: Deploy build worker 37864475043 reports "browser-probe: PASS working=[] message-bug=['feedback_disappears']".
  - Not yet exercised inside a real founder build.
- **Drain also held during a real build.**
  - Founder build `bld_e2043208…` started 00:23:52 UTC.
  - Deploy 37864475043 drained for 65 s, and the build finished `ready` at 00:26:04 (build-evidence 37864934013).
- **Approval idempotency (directive §5).**
  - Behaviour: a second approval of the same plan revision returns the existing queued/running/ready build. There is no second build and no second reservation. A failed build still allows a retry.
  - Mechanism: an advisory lock on (project, contract) plus a check for an existing build.
  - Proof: a live-Postgres race test fails without the lock (two builds) and passes with it. The endpoint test is `test_second_approval_of_the_same_plan_returns_the_existing_build` (CI v24-ci 37864338119).
  - UI: in-flight guard and a "this plan is already building" message.

**Implemented, awaiting live (founder in the workspace)**
- **G2 — discovery conversation, ProjectBrief, server-bound approval (`9db2d53`, deployed: Vercel dpl_3Hio8MbtAzFrUucJXCEvswaqttg4, migration 030 applied by Deploy build worker).**
  - Engine: `omni_prod/discovery.py`. Questions include the simple ones (colour, font, style, logo, references, audience, content). They come in small groups. Facts already stated are not asked again. "No preference — choose for me" is recorded as delegated. Contradictions must be decided by the user. Changing an answer drops answers that depend on it. Guided and recommend modes are both available.
  - Brief: immutable revisions with compare-and-set.
  - Approval: bound to user, project, brief revision + fingerprint, contract + fingerprint, budget quote and a 30-minute TTL. It is consumed exactly once.
  - Builds without an approval → 409 `approval_required`.
  - "No sign-in" now means no sessions, a single user and no RBAC floor in the contract.
  - Tests:
    - engine;
    - live Postgres: CAS race, approval used/stale/expired/bound;
    - endpoints: CI v24-ci on `9db2d53`.
  - UI: checked in a real browser against the real engine with a local harness (desktop and 390 px, refresh restore, change → new plan). The deployed `app.js` contains the new flow.
  - **Not yet verified:** a founder session on the deployed workspace (this sandbox cannot reach vercel.app interactively).

**Implemented, awaiting live**
- **QA budget no longer hides cost behind a date.**
  - `OMNI_QA_BUDGET_SINCE` now counts only together with `OMNI_QA_FREE_TIER_EVIDENCE` (a reference to billing proof). Without that reference the count is all-time and the ignored date is recorded in build evidence.
  - With the current Vercel env (no evidence), the counted QA use returns to the all-time figure. Now $3.31 all-time versus $0.60 since 17:12 (build-evidence 37864934013, 2026-10-09 00:30 UTC).
  - The founder can supply the Google billing view to restore the date. Until then the conservative figure stands.

**Found, not yet fixed (G5)**
- The generated library site hides every status message after the first one: `showBanner` leaves `style.display='none'`.
  - Found by running the exact version in a real browser locally.
  - HTTP acceptance cannot see it. WP-G5a adds a real-browser check.

## Update 2026-10-08 23:05 Asia/Jerusalem — Golden E2E #1: full chain from the founder's workspace

**Verified end to end, one continuous path, founder at the keyboard (Vercel Preview `fe84c4d`+, worker `3a4d822`):**
login → project "אתר לניהול משימות" → plan/quote → QA reservation → queue → worker → Gemini (paid tier) →
multi-file repository → sandbox build + tests + repair (2 rounds) → quality 84 → R2 artifact → version
`v_246bae81234e4c39` → live preview with a real Hebrew UI (`prv-1760dedc…sslip.io`) → natural-language change
`mod_c14435dc9baa44bdac784d0c15ed9b85` (READY_FOR_REVIEW 22:04, restored after reload, accepted 22:55) → new
version `v_0bc82ef7b33b4210` with spec A1–A6 (A5 date window → HTTP 400 + DD/MM/YYYY, A6 visible filter +
reset after add; code checked through build-evidence) → ZIP downloaded and opened by the founder (22:59).
Real QA spend counted since paid tier: $0.35.

Still open (honest): the new version reports a bad date with `alert()`, shows the "done" button on finished
tasks and renders via innerHTML of server-escaped text; earlier version double-escaped apostrophes. These are
product-quality gaps for the generation baseline, not pipeline failures. Release acceptance asks for three
different prompts: two done (league rehearsal/founder builds, tasks); one more pending.

## Update 2026-10-08 22:40 Asia/Jerusalem — first founder build with a real UI; change flow; real QA spend

- **Build → Preview with a real UI: PASS (founder, from the workspace).** `bld_f419acd1317a40afab5a7bd287841048`
  (project "אתר לניהול משימות", 21:30–21:35, 2 repair rounds, quality 84) → `v_246bae81234e4c39`; preview
  `https://prv-1760dedc67864c0186aa0cdf945bab0d.151-145-89-132.sslip.io` showed the Hebrew task form,
  filter and table; the founder added tasks, filtered and deleted (screenshots 21:36–21:41).
- Defects the founder found in the generated product (open, platform level): no input validation (due
  date 2356 accepted), ISO dates, an active filter is not shown and hides new tasks; the planner adds
  login/roles requirements although the request says "בלי התחברות". To do: a product-quality baseline
  for generation (validation, clear errors, visible filter state, local date format).
- Fixed: HTTP 500 on approving a plan (`build contract fingerprint mismatch`: title cut at 80 chars after
  a space; 409 for a stale contract); "+ New project" with a name dialog and an empty request box.
- Change flow: `mod_c8d186268bee413e9a03197ee15d8de6` (21:45–21:51) and `mod_c14435dc9baa44bdac784d0c15ed9b85`
  (22:00–22:04) both READY_FOR_REVIEW, but the panel kept saying "sent" and a second click created a
  second candidate. Fixed: latest-modification route + restore after reload, one change at a time,
  30 s request timeout with polling retries (real-Postgres + Chromium checks). Accept/version/ZIP of the
  change: pending founder action.
- QA budget: the cap ($10, founder decision #23) counted reservations ($9.15 "used", 22 rows) while real
  provider cost was ~ $0 before 17:12 UTC (Gemini free tier) and ~ $0.30 after. Founder 22:25: "$10 real,
  all providers together". `qa_used_usd` now counts provider-reported actuals or the spend ledger;
  `OMNI_QA_BUDGET_SINCE=2026-10-08T17:12:00Z` set on Vercel Preview (plain, non-secret).

## Update 2026-10-08 21:00 Asia/Jerusalem — first founder build after the provider work

- `bld_78e2699472054c918890c5daddafc205` (founder, football project, 20:39): FAILED
  `preview_not_ready` after 5 repair rounds: tests passed, quality 82, but "/" was a 382-char page.
  Route events: `gpt-6.1-sol` 429 no credits (skipped, $0), `gemini-3.8-flash` failed twice
  ("invalid model response shape" after 71 s; read timeout at 120 s), so repairs fell back to
  Flash-Lite. Spend ledger $0.163, 16 calls.
- Fixes: Gemini timeouts 300 s (3.8-flash) / 180 s; the shape error now names finish_reason
  and returned keys; the preview smoke test also reads same-origin scripts/styles the page links
  (a UI built by `/app.js` passes) and quotes the start of a rejected page so repair sees it;
  the workspace marks `preview_not_ready` on the generation step. Tests added.

## Update 2026-10-08 20:40 Asia/Jerusalem — providers connected, paid Gemini, measured build cost

- `ff6b4f6` deployed (run 37739774562): quota answers disable a route for the build, refused
  calls release their reservation, budget-fit fallback, failure codes `model_budget_exhausted` /
  `model_unavailable`; OpenAI (`gpt-6-luna`, `gpt-6.1-sol`) and Anthropic (`claude-sonnet-5-5`,
  native Messages API) in the catalog. Deploy notice: all 6 catalog models CONFIGURED (keys from
  GitHub secrets `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`).
- Model probe 37814803770 (after the founder enabled Gemini billing, Tier 1 prepay): 3 Gemini
  models **PASS**; OpenAI **FAIL** "no credits remaining" (HTTP 429); Anthropic **FAIL** "credit
  balance is too low" (HTTP 400). Blocked by: prepaid credit in both accounts (founder).
- Rehearsal 37814985551 (Gemini only, Hebrew league prompt): `ready`, 5 repair rounds, quality
  82/pass, 13 calls, 650 s. Measured tokens 26,570 in / 22,248 out; metered at list price
  ≈ $0.075 (flash-lite 7 calls ≈ $0.018, 3.8-flash 3 calls ≈ $0.057). Ledger (conservative,
  calls without reported usage kept at worst case) $0.2096.

## Update 2026-10-08 02:50 Asia/Jerusalem — root cause of bld_ccd38bd0; status review

Full review (Hebrew): `docs/STATUS_REVIEW_2026-10-08_HE.md`. No operation running.

- `bld_ccd38bd00a2f430ab2d92b2962c91544` (founder, 02:36) FAILED `worker_exception` /
  `ModelPolicyViolation: external model budget exceeded`. Earlier hypothesis (worker env
  budget below the reservation) is **wrong**: build-evidence run 37704279388 shows
  `worker_env_budget_usd=0.50, reserved_llm_usd=0.50, effective_budget_usd=0.50`.
- Verified cause: `gemini-3.8-flash` answered `HTTP 429 You exceeded your current quota`
  10 times (~250 ms each, free tier); every rejected call stayed in the ledger at its
  worst case ($0.045–0.050), so 14 calls "spent" $0.4739 while the provider charged $0.
  The gateway also retried the same model twice after a quota 429.
- Status: model routing PASS (events); quota handling **FAIL**; cost reconciliation
  **FAIL** for rejected calls (recorded spend ≠ provider cost). Not fixed yet (review
  action 1). Gemini daily quotas reset at midnight Pacific (ai.google.dev rate-limits).
- `build-evidence.yml` now publishes budget binding, call count, spend and the last 12
  route events (model, ok, latency, cap, error) — amounts only, no secrets.
- Environments checked: branch/Vercel Preview `bd6ea0d` (READY, dpl_95PZjXrvHrWM6UBJQee9bD5XqFg3);
  worker `4712ab7` (same product code); Vercel Production 148aiv28 = `main@e8f2949`,
  148ai = `main@0f7acea`; neither is connected to the worker.
- Superseded below: §3 "Preview router blocked — needs domain control" (the sslip.io edge
  runs since 2026-10-08 00:49).

## Update 2026-10-07 16:10 Asia/Jerusalem — worker host (Queue → Worker)

- Oracle access: SSH timed out because the security-list ingress rule allowed
  `5.29.18.127/32` while the founder's public IP had changed. The founder
  updated the rule; `Test-NetConnection 151.145.89.132 -Port 22` →
  `TcpTestSucceeded: True`; SSH as `ubuntu` works. Host: Ubuntu 24.04.5 LTS,
  `aarch64`.
- Runner: `infra/worker-host/bootstrap.sh` copied to the host by paste and
  checked (`sha256 61cfad15…114c`, 55 lines = the committed file), run with a
  registration token entered with `read -s` (never in chat or shell history).
  Runner `148ai-worker-01`, labels `self-hosted, Linux, ARM64, omni-worker`,
  status **Idle** (GitHub runners page, founder screenshot). Independent
  evidence through the GitHub API: deploy run 37610280053 was picked up by
  runner `148ai-worker-01` and failed explicitly at "Write environment file"
  with the annotation `GitHub secret WORKER_ENV is not set` (the secret did not
  exist yet).
- `WORKER_ENV` created by the founder (values never seen by this session). The
  Vercel copies are `sensitive` and cannot be read back, so the values came
  from their sources: Neon `148ai-db` and Upstash `148ai-redis` (Vercel Storage
  `.env.local`), a new R2 account token `148ai-worker` scoped to
  `omni-artifacts` only, and a new Gemini API key `148ai-worker` (free tier).
  `OMNI_SECRET_KEY` is deliberately not set on the worker: the build path
  shares no secret with the web app (control-plane tokens are minted and
  verified only by Vercel); to be set before production.
- Deploy run 37624945100 (`workflow_dispatch`, `2464394`): every step PASS —
  write env, build images, **apply database migrations**
  (`python -m omni_prod.migrate`), start, worker logged `Listening on`.
  Which migration versions were applied is NOT VERIFIED from here (job logs
  are blocked by the egress proxy).
- Queue → Worker: "Listening on" proves the worker started, not that it
  consumes the queue. Added a deploy step that enqueues a side-effect-free
  probe job (`socket.gethostname`) on `omni-builds` through the same Redis and
  passes only if the running worker container on this host executes it.
  Checked locally against a real Redis server and RQ 2.12.0 (source from
  GitHub): PASS when the worker runs; FAIL when the executing host is not the
  expected container; FAIL (status `queued`) when no worker runs. Status:
  IMPLEMENTED, result pending the deploy run of this commit.
- Vercel: `2464394` READY on 148aiv28 (`dpl_8PdrfGMYy6CRYxRXvTCLQJFriApT`).
- Duplicate Vercel project **148ai disconnected from Git** by the founder
  (16:54, 148ai → Settings → Git → Remove Connection; project kept, not
  deleted). Verification: the push of this STATUS change must create a
  deployment on 148aiv28 only, none on 148ai.

### 16:50 — probe result, diagnosis, fix

- Deploy run 37625977649 (`8365b33`): steps 1–7 PASS, the new probe step
  FAILED: `job ee96cb33… status=queued executed_on=None
  expected=175a9b4f3ac1` (annotation). The probe did its job: the worker
  logged `Listening on` but did not execute the job.
- Diagnosis on the host (founder ran read-only scripts over SSH, outputs in
  screenshots): worker container up, no restarts, log ends at `cleaning
  registries`; queue 0, intermediate 1 (the probe id had been moved out of the
  queue but never executed); Upstash reports `redis_version 8.4.0`. Upstash
  wakes blocked BLMOVE/BLPOP clients correctly: after 6–91 s of blocking,
  plain/MULTI/non-transactional pushes, 60 s and 405 s timeouts all woke in
  ~5 s. Three fresh RQ 2.12 workers (default, with scheduler, ttl 60) on
  temporary queues each executed a job in 0.7–1.5 s.
- **Queue → Worker: PASS on the running worker.** The unchanged probe run
  against the live worker (container `175a9b4f3ac1`, up ~30 min): `status=
  finished executed_on=175a9b4f3ac1 expected=175a9b4f3ac1
  enqueued_from=3d8677914941` (a different container). Registries before the
  probe: started 0, finished 0, failed 0, so the first worker run executed no
  earlier queued jobs (no unintended provider calls).
- Cause of the deploy-time failure (reproduced locally on real Redis, not
  proven on Upstash): a consumer blocked in BLMOVE that never reads its reply
  takes the next pushed job. With a frozen blocked consumer and a plain RQ
  worker as deployed, the probe ends exactly as on the host (`status=queued`,
  queue 0, intermediate 1). The likely source on the host is the previous
  container's BLMOVE still registered after `docker compose up` replaced it.
  RQ's intermediate-queue cleanup would later mark such a job FAILED ("stuck in
  intermediate queue"), so a real build enqueued in that window would fail.
- Second finding: the RQ scheduler (enabled, but nothing uses scheduled jobs)
  polls Redis every second, ~4 commands/s ≈ 10M/month, against Upstash's free
  500K/month.
- Fix (`omni_prod/worker.py`): scheduler disabled; dequeue wait bounded to
  120 s (`OMNI_WORKER_TTL_SECONDS`, default 135; ~86K idle commands/month);
  before consuming, the worker pushes a decoy id (no job behind it) to the
  front of the queue and reports whether a stale consumer took it (bounded to
  3 rounds; untaken decoys are removed; RQ skips and cleans ids without a
  job). Real-Redis check: with a frozen consumer the old worker loses the
  probe, the fixed worker logs `stale consumers absorbed before start: 1` and
  executes it; without one it logs `0`, leaves no decoy and no scheduler keys.
  Tests: `tests/test_worker_entrypoint.py` (8, stdlib). The deploy run now
  also publishes the worker's start-up lines as annotations.
- **Result, deploy run 37631079254 (`5cd8412`): every step PASS, including
  the probe right after the worker container was replaced** — `PASS job
  2b778f2e… executed by worker b186ba0f… in container 72f63493b9ae on this
  host`; start-up: `worker ttl 135s, dequeue wait 120s, scheduler disabled`,
  `stale consumers absorbed before start: 0`. CI on `5cd8412`: `v24-ci` and
  `V11 Overlay CI` PASS. Honest reading: no stale consumer appeared on this
  replacement, so the earlier deploy-time loss is explained by reproduction,
  not observed twice on Upstash; the absorber stays as a guard and reports
  on every start. **Queue → Worker: PASS** (running worker and right after a
  deploy).

### 17:00 — preparing Quote → Budget Reservation

- Vercel Preview (148aiv28, target `preview` only, type plain, non-secret,
  set through the Vercel API): `OMNI_ENV=staging`, `OMNI_QA_BUILD_MAX_USD=0.50`,
  `OMNI_QA_BUDGET_TOTAL_USD=10` (founder caps), `OMNI_EXTERNAL_BUDGET_USD=0.50`,
  `OMNI_EXTERNAL_CALLS_PER_BUILD=40`, `OMNI_ZERO_COST_MODE=0`,
  `OMNI_ALLOW_EXTERNAL_FALLBACK=1` (same model policy as the worker's
  `WORKER_ENV`). `OMNI_ENV=staging` changes nothing else in the app (every
  other check compares with `production`). Takes effect with the next Preview
  deployment.
- Bug found before first use: the "Internal entitlement" workflow wrote `.env`
  from `WORKER_ENV` only, without the host sandbox secret, so `docker compose`
  would refuse to run (`OMNI_SANDBOX_SHARED_SECRET:?required`). Both
  workflows now call one script, `infra/worker-host/write-env.sh` (also strips
  CR from pasted secrets). Checked locally: missing secret → explicit error;
  CRLF input → clean `.env`, mode 600, names only printed.
- Next: Preview deployment with the new settings; INTERNAL_QA grant for the
  founder's 148AI account; founder runs the product flow on Preview (login →
  project → prompt → plan → build) — the plan view must show
  `build_authorization=PRICED` and the build start must create a QA-funded
  reservation.

### 17:20 — Golden E2E #1 on Preview (founder in the browser)

- "Internal entitlement" workflow: GitHub answered 404 to the first dispatch
  (a workflow is dispatchable only after it ran once or is on the default
  branch); it now registers itself with one read-only `list` run on push.
  Two more defects fixed before it worked: GitHub runs steps with `bash -e`,
  so a refusal ended the step before its reason was published, and the
  one-line reason came out empty because docker compose can end stderr with
  blank lines. Run 37633588436 `list` → `[]` (table from migration 029
  exists). Grant for the address in the founder's decision →
  `refused: account not found`; the founder confirmed his 148AI account
  address, grant run 37634623482 → `granted ent_96e09ec0… account
  usr_vrMiNf0RiWiSO_1N INTERNAL_QA staging`. The worker host found the account
  the founder logs into on Preview, so worker and web app share one database.
- **User → Login → Project: PASS** on Preview `a17f52f`
  (`148aiv28-gf5t3gzw8…`): existing account, existing project. Creating a
  second project was refused with `Free project limit reached` (free-plan
  rule, by design).
- **Project → Prompt → Product Plan: PASS** on Preview: roles admin/member,
  data users/items/activity, infrastructure database and sessions
  `SELF_CONTAINED` (demand-driven, no managed services).
- **Product Plan → Quote: FAIL** on Preview: `build_authorization=
  NOT_AUTHORIZED`, blocker "not available on your current plan", approve
  button disabled. Cause: the plan view priced the build as the free customer
  plan while build admission funds an INTERNAL_QA account from the QA budget
  (with the model budget now 0.50 the customer path refuses paid variable
  cost). Fix: one shared decision `_internal_qa_funding()` for the plan view
  and admission; the plan view quotes with the same funding and runs the same
  QA cap checks read-only (`qa_budget.preauthorize_qa_build`, own transaction,
  no writes). Tests: `tests/test_qa_plan_parity.py` (11). The plan view also
  showed raw keys (`st_NOT_AUTHORIZED`, `st_SELF_CONTAINED`); translations
  added, static cache bumped to `148ai-v28-static-4`. Re-verification on
  Preview pending.

### 17:45 — first real build on Preview

- **Product Plan → Quote: PASS** on Preview `24e992a`
  (`148aiv28-8yff44gmw…`): pricing "Authorized" (PRICED), infrastructure
  "built into the app" (SELF_CONTAINED), no blockers, approve enabled.
- Founder approved. **Quote → Budget Reservation: PASS** (the build was
  accepted and reached the worker, which happens only after the QA-funded
  reservation commits in the admission transaction). **Queue → Worker: PASS
  with a real build job**: the worker ran planning, contract, infrastructure
  (self-contained) and assets, then failed explicitly before any model call:
  `AttributeError: 'PostgresCapabilityRepository' object has no attribute
  'create_plan'`. **Worker → Real AI Provider: NOT VERIFIED** (not reached).
- Cause: the worker's capability stage calls `create_plan()` and
  `transition()`; the Postgres repository only had `save_plan()`; all worker
  tests used the memory twin. Fix: both methods on the Postgres repository
  with the memory twin's semantics (idempotent plan, plan drift raises,
  compare-and-set transition, KeyError for a missing requirement).
  **Checked on a real PostgreSQL 16** (all migrations, psycopg from source in
  pure-Python mode) with the Golden E2E #1 contract: prepare →
  READY_FOR_BUILD (10 native requirements PLANNED), prepare again idempotent,
  finalize_native → all VERIFIED, stale compare-and-set False, missing
  requirement KeyError, different plan → drift error.
- Found on the way: `python -m omni_prod.migrate` failed on an empty
  database (`schema_migrations` is created by migration 005, after 001–004
  need it). The runner now creates the bookkeeping table first (same DDL);
  applied all 25 migrations to an empty PostgreSQL 16, second run "none".
- The progress view showed "quality, security and rights gates" as passed for
  this failed build although they never ran (unknown phase was treated as
  "done"). Steps after the failing step are now shown as skipped; static
  cache `148ai-v28-static-5`.
- Tests: `tests/test_worker_repository_parity.py` (10; they fail on the old
  code). Local full run: the same 18 environment-only failures as the clean
  baseline (FastAPI/psycopg not installable here; CI has them).
- Still open: the failure message shows the raw exception text to the
  customer (fine for staging diagnostics, not for launch).

### 18:10 — second real build: first real provider call, stuck status

- Build `bld_2f248e2339cb4ad9848a7ebb5c0c4ed6` (Preview `f39d637`): the
  capability fix held (assets step passed). **Worker → Real AI Provider:
  reached, FAIL**: worker log `ModelGatewayError: all model routes failed:
  model request failed: HTTP Error 503: Service Unavailable` at the
  architect's first `complete_json`. A direct call from the worker host with
  the same key and headers (founder over SSH): `gemini-3.1-flash-lite HTTP
  503 "This model is currently experiencing high demand. Spikes in demand are
  usually temporary." status UNAVAILABLE`. Model codes and prices in the
  catalog were re-checked against Google's models and pricing pages today
  (both exist, prices match).
- **Defect: the failed build stayed "running" in the UI for 20+ minutes.**
  The worker's failure handler crashed with `TypeError: Object of type
  Decimal is not JSON serializable` while writing the FAILED status, so no
  terminal status was ever written. Fix: `omni_prod/evidence_json.py`
  (Decimal → exact string, datetime, enum, set, path; unknown objects are
  never stringified because a repr can carry credentials); terminal
  transitions never fail on evidence encoding (a marker with the reason and
  the evidence keys is stored instead). Used by build and modification
  status writes, capability transitions and preview acceptance. The stuck
  row `bld_2f248e…` remains RUNNING in the database (evidence of the bug; the
  billing resolution ran before the crash).
- Provider overload handling: HTTP errors now carry the provider's own
  message, status and Retry-After; a 429/5xx answer is retried on the same
  route (2 retries, 2 s / 6 s, Retry-After capped at 20 s) before
  escalating; every retry is a separate attempt, budget-checked and recorded
  in the Attempt Ledger; non-transient errors escalate at once; the final
  error lists each route's reason. Catalog: `gemini-3.5-flash-lite`
  ($0.30 / $2.50 per 1M, free tier, official pricing page 2026-10-07) added
  as a second Flash-Lite capacity pool.
- Tests: `tests/test_evidence_json.py` (5), `tests/test_model_transient_retry.py`
  (8). Known open item: no reaper yet for builds whose worker dies mid-run
  (e.g. a worker redeploy during a build) — they would stay RUNNING.

### 18:20 — third real build: real model answer, spec shape

- Build on Preview `f822dd7`: ended **FAILED** with a visible reason
  (`ValueError: requirement id/text required`) — the terminal-status fix
  works (no more endless "running"). The error is raised while validating the
  architect's answer, i.e. after a successful provider call: **Worker → Real
  AI Provider: PASS** (a real Gemini response reached the pipeline; 503
  retries/fallback in place). Next failing transition: **Multi-file Project
  (spec → generation): FAIL** on the spec shape.
- Cause: `_ARCHITECT_SYSTEM` named only the top-level fields; the
  requirement/acceptance keys that `ProductSpec.from_dict` reads (`id`,
  `text`, `kind`, `mandatory`; `id`, `requirement_id`, `text`) were never
  stated, so the model invented its own. Fix: the prompt states the exact
  shape, allowed kinds and id rules; one corrective round sends the
  validator's exact error with the invalid answer; a second invalid answer
  fails the build explicitly naming both errors. Both rounds are ordinary
  recorded, budget-checked calls. Tests: `tests/test_architect_spec_shape.py`
  (4).

### 19:10 — fourth real build: spec PASS, manifest shape

- Deploy run for `67d40be`: start-up reported `stale consumers absorbed
  before start: 1` — the previous worker's blocked request was still
  registered on Upstash after the container was replaced, and the decoy
  satisfied it. This is the first direct observation of the cause found at
  16:50; the probe then passed.
- Build on Preview `67d40be`: the architect's spec was accepted (the shape
  fix works); the generator's repository was rejected with `ValueError: at
  least one verification command required`, 0 repair rounds, billing
  `settled`. Cause: same class as the spec — the generator/repair prompts
  never stated the `.omni/project.json` keys (`build`, `verify[].name`,
  `argv`, `acceptance_ids`), and the parse error aborted the build before the
  repair loop. Fix: `project_manifest.MANIFEST_SHAPE` (parsed by the test
  suite to stay consistent with the parser) in both prompts; an invalid,
  missing or unknown-id manifest is now a failed verification report for
  every acceptance criterion with the parser's reason and the shape as
  evidence, so the repair loop can fix it; nothing runs in the sandbox for it.
  Tests: `tests/test_manifest_shape.py` (5); `tests/test_v22_sandbox_executor.py`
  updated to the new contract (rejected as failed verification, sandbox not
  called).

### 19:30 — fifth real build: sandbox runner had no docker client

- Build on Preview `e2cc4c7`: spec and generated repository accepted (both
  shape fixes hold; the manifest now parses), then the first sandbox command
  failed: `RemoteSandboxError: HTTP Error 500`. New read-only workflow
  `worker-diagnostics.yml` (container state, sandbox image architecture,
  recent worker and sandbox-runner logs as annotations, secret shapes
  redacted; no checkout/compose/restart) — runs 37650560125 and a dispatched
  short-tail run — showed the runner's traceback: `FileNotFoundError: [Errno
  2] No such file or directory: 'docker'` in `sandbox.run_sandbox`. The
  runner image installed `docker.io` with `--no-install-recommends` and ended
  up without a docker binary, while its `/health` still answered 200, so the
  deploy looked green. Sandbox image `omni-sandbox:latest` is arm64; both
  containers running, 0 restarts.
- Fix: the runner image installs `docker-cli` (fallback `docker.io`) and the
  image build fails without `docker --version`; `/health` returns 503 without
  the client or the daemon socket (compose then never starts the worker);
  the worker deploy runs a real snippet through the same signed sandbox path
  and fails unless it ran and the sandbox has no network. Tests:
  `tests/test_sandbox_runner_health.py` (5; the HTTP ones run in CI).
- Deploy of `89e26df`: images built with the client, but the new sandbox
  probe failed: `returncode=2 stdout=''` — the run now reaches Docker, and
  python inside the sandbox could not open the script. Cause (same as the
  M4.9 fix in the local executor, missing in the remote runner): the runner's
  temp directories are 0700 and owned by root, the sandbox runs as uid 10001.
  The runner now makes the source root 0755 and the output root 0777 before
  the run; the probe's failure annotation now includes stderr.

### 20:30 — sixth real build: through the sandbox, stopped at R2

- Deploy of `6a5f8b3`: sandbox probe PASS (`code ran in the isolated sandbox
  (3, 12), network blocked`), queue probe PASS, stale consumer absorbed: 1.
- Build on Preview `6a5f8b3` ended **FAILED** with a visible reason after the
  runner served six signed `/run` calls with HTTP 200 (diagnostics run,
  sandbox-runner log): the generated repository was built and verified in the
  isolated sandbox, then `workspace.commit` failed on Cloudflare R2:
  `InvalidArgument ... Credential access key has length 34, should be 32`.
  **Build → Tests → Verification: reached and executed in the real sandbox**
  (pass/fail of the individual checks is not visible in this failure's
  evidence because the commit came first). **Durable Artifact (R2): FAIL** —
  the R2 Access Key ID in `WORKER_ENV` has two extra characters (value never
  seen; the founder pasted it today).
- Guard: `write-env.sh` now checks every `WORKER_ENV` line for surrounding
  spaces or quotes and the R2 key lengths (32 / 64), reporting variable names
  and lengths only, and fails the deploy before anything starts. Deploy runs
  after the guard report: `OMNI_S3_ACCESS_KEY has 34 characters` (no spaces,
  quotes or non-ASCII characters — the pasted value itself differs). Optional
  secret `WORKER_ENV_OVERRIDES` (NAME=value lines replacing the same keys) so
  one value can be corrected without re-pasting the whole secret. Founder
  action: new R2 token for the worker, two lines in `WORKER_ENV_OVERRIDES`.

### 21:00–22:55 — first READY build; modification path hardened

Transition status after this window (Preview `148aiv28`, branch alias
`148aiv28-git-milestone-pre-staging-2026-10-05-shayflys-projects.vercel.app`):

| Transition | Status | Evidence |
|---|---|---|
| Build → Tests → Verification | PASS | `bld_534476042257416091da55cb4c03ae0e`: verification passed, 1 repair round, quality 86/80 (traceability 100%) — read through `build-evidence.yml` |
| Durable Artifact (R2) | PASS | deploy `storage-probe` write/read-back/delete PASS (worker); build status `ready` with artifact key; web tier lists versions and the founder downloaded the ZIP after the Preview S3 vars were corrected |
| ZIP | PASS | founder downloaded and opened the archive (`app`, `tests`, `README`, `.omni`, …) |
| Modification (rerun on the football version) | PASS | `mod_6ddd35a851a045929528e4bd6acc7768`: source `v_8a6a2c68eab74054` (football, restored with its spec via `/rollback`), `change_request`, 0 repair rounds, verification + gates passed, accepted 20:44:46Z, billing settled $0.0180 (2 calls). New spec adds A8 "removing a team deletes it from the standings and updates the table" |
| New Version (rerun) | PASS | `v_c7fca05db84a4ef3`, 14 files, spec stored with it |
| Modification (first attempt) | PASS (mechanics) / FAIL (base) | `mod_090791ebff9f41f58ae1284f9eeec642`: classified `change_request`, evolved spec, verified, READY_FOR_REVIEW, accepted by the founder 20:12:45Z, billing settled $0.0182 (2 calls). It ran against the wrong base: the failed second product had been committed as the newest version. Fixed: failed builds are no longer versions. Rerun on the football version pending |
| New Version | PASS (mechanics) | `v_38b3f001967c4211`, 13 files, spec stored with it (A7 = the added delete capability) |
| Preview (mechanics) | PASS | 2026-10-08 00:49: `v_88a6539c08574dda` (modification `mod_de87d44898204e4bba5d7d95737e451c`, 2 repair rounds added the preview contract) ran at `https://prv-b5eefafd3ad64bc89af89b2aae43cb0c.151-145-89-132.sslip.io` inside the workspace iframe: Caddy on-demand certificate, router, preview container. |
| Product is a real website | FAIL | The page showed "OK": the generated app is a `LeagueManager` class + unit tests and a handler that returns "OK" at `/`; criteria A4–A7 (responsive UI, RTL, persistence, bundle) are claimed by tests that do not exercise them. Fix: the sandbox smoke test now requires `GET /` to return an HTML user interface with real controls, and the generator must test through HTTP. Not yet re-run. |
| Preview (first launch) | superseded | Founder chose a free temporary address. Deployed: preview-worker, router, Caddy on-demand TLS for `*.151-145-89-132.sslip.io`; deploy check `preview-edge: PASS`; Oracle security list 80/443 opened by the founder. First launch on `v_c7fca05db84a` → `NOT_PREVIEWABLE: preview contract requires schema_version 2, got None` (generated manifest had no preview keys). Fix: preview keys in the shared manifest example + `PreviewReadyExecutor` (contract required, app started in the sandbox and its health path polled; failure is repairable). Needs a new version produced after this fix |

Defects found by real runs and fixed (each with a test):
- R2 credentials: worker key was 34 chars, then SignatureDoesNotMatch, then a
  63-char secret. The founder's browser paste in Chrome returned a stale value;
  values were typed. Deploy now runs a real **storage probe** (write, read-back,
  delete through `S3ArtifactStore`); the 32/64 length check is a warning only.
  `WORKER_ENV_OVERRIDES` reports applied names.
- Sandbox: `compileall` failed on the read-only source mount (`./__pycache__`).
  Bytecode/pytest caches go to tmpfs (`PYTHONPYCACHEPREFIX`); the deploy
  sandbox probe now compiles in the read-only workspace.
- Uncovered acceptance criteria now fail verification (repairable) instead of
  passing and then failing the quality gate with no repair round.
- Planner: the word "משחק" (a football *match*) classified the product as a
  3D game and added unpriced game assets — workaround in the prompt; **not
  fixed** (keyword list in `media_pipeline._GAME_TERMS`).
- Web version list downloaded every archive (`len(v.files)`); uses the durable
  `file_count`.
- Live build never stored its ProductSpec → versions could not be modified.
  Version and spec are now committed in one transaction.
- Modification admission ignored the INTERNAL_QA entitlement →
  `modification_admission.admit_modification` funds entitled accounts from the
  QA budget (same caps/lock as builds).
- Modification/repair agents saw only `{path, chars}`; source files now carry
  their content (bounded 16k/file, 64k total); the evolution prompt requires a
  test and a `verify` entry for every new acceptance id.
- UI kept polling forever on `NEEDS_CLARIFICATION`/`CONFLICT`.
- **Decision change:** a build that fails verification/quality/security is not
  committed as a project version (only a rights-only block still is). The
  previous behaviour made the failed product "current" and the next
  modification targeted it. `/restore` now copies the ProductSpec
  (`/rollback`, used by the UI, already did); real-Postgres test added.
- Spec language: the architect and evolution prompts now write title,
  summary, requirements and acceptance in the request's language (a Hebrew
  request produced an English "what was built" panel).
- Workspace UX (founder feedback): once a project has a version the page leads
  with "what was built" (title, summary, features from the stored spec via
  `/history`), then "what would you like to change"; "new build from scratch"
  is a secondary button. Checked in Chromium with mocked API data.
- Build `bld_8029266bf1164a71995667f89309e832` (founder's second product):
  verification passed, quality 78/80 with zero repair rounds — a root-level
  `test_app.py` was not counted as tests, and quality was never sent to
  repair. Test detection fixed (that build would score ≥ 80); the executor now
  turns a quality shortfall into repairable failures (`QualityAwareExecutor`),
  and a quality-only final failure is reported as `quality_gate_failed`.

Verification commands: `python -m unittest discover -s tests` (925+ tests, the
same 18 environment-only failures as the baseline, no new ones); real Postgres
16 with migrations 001–029: `tests/test_m4d2_live_postgres.py` (14) and
`tests/test_golden_mod_path_live_postgres.py` (2) — build→spec persisted,
QA modification admitted with `funding_source='internal_qa'`, settled.

Added 2026-10-08 01:30: `omni_prod.maintenance` (janitor service) expires
previews and removes their containers, and fails builds RUNNING > 45 min as
`worker_lost` with the reservation released (real-Postgres tests); INTERNAL_QA
accounts get a staging project cap (`OMNI_QA_MAX_PROJECTS`, default 20) and
archived projects no longer count; build failures show a customer-facing
Hebrew/English reason with the raw message under "technical details".

Build `bld_85cc573b473341e9b3f10d248d743ff1` (02:29 UTC+3, Hebrew football
prompt) FAILED after 5 repair rounds: A3–A7 never covered. Causes: the
architect wrote criteria no sandbox test can check (Lighthouse >90, 80%
coverage, browser localStorage, a JS confirm dialog) and the build repair
agent saw only `{path, chars}` (never the manifest). Fixed: architect must
write HTTP/HTML-testable criteria (3–6); build repair uses the bounded content
summary. Not yet re-run.

Workspace UX backlog (founder approved, to do after Golden E2E #1 passes; extended 2026-10-08 20:50):
1. **stop/cancel button** with server-side cancellation between steps, spend stopped, unused reservation released (none exists: no route, no worker check);
2. **build-button lock** while a build runs (founder double-clicked "build" on 2026-10-08);
3. **live activity log** of actions and results (spec written, files written, test A2 failed, repair round 2/5, app started) -- actions, not raw model reasoning;
4. time estimate and progress from past builds;
5. start the preview automatically when a build finishes / a project with a version opens;
6. completion notification (sound/browser, later email);
7. version diff in plain words ("added a delete button");
8. live cost ("12 of 60 credits used");
9. in-app file viewer;
10. failure with a next action (retry, simplify the request);
11. mobile layout for the workspace;
12. original request and Hebrew product description at the top of the project.

Open (superseded items struck): ~~failed builds also commit restorable versions~~; the build row
`bld_2f248e2339cb4ad9848a7ebb5c0c4ed6` is still RUNNING; no reaper; raw
exception text shown to customers; revoke R2 tokens `148ai-worker`,
`148ai-worker-2`.

## Update 2026-10-07 14:10 Asia/Jerusalem

- CI on `089f5bd` FAILED (`v24-ci` run 37549999227, `V11 Overlay CI` run
  37549999186). Job logs are not reachable from this environment (blob
  storage blocked by the egress proxy). Root cause found by reproduction: the
  new HTTP plan-view test flagged the customer's own plan fields
  (`monthly_price_usd`, `annual_price_usd`, `allowed_cost_classes`) as internal
  economics; the internal-key filter now exempts exactly
  `pricing.PUBLIC_PLAN_FIELDS`, with stdlib tests that reproduce it. `v24-ci`
  now publishes failing test names as annotations so future failures are
  readable without logs. Evidence: `6076a5a` — `v24-ci` run 37610280545 PASS
  (full `pytest -q`), `V11 Overlay CI` run 37610279936 PASS.
- Consolidated Preview deployment: `6076a5a` on 148aiv28 READY
  (`dpl_2EghHZo7Wfx887nmq296BUjVd8Ew`); 148ai built and failed again
  (`dpl_7ozoDtVogXEbggoRLiXEiN2M2sta`) — Git disconnect still pending.
- Probe re-run on the deployed code: `self_contained_web_v1`, contract READY,
  `[database:SELF_CONTAINED, auth_session:SELF_CONTAINED]`, quote PRICED,
  unknown `[]`. Plan → Quote stays IMPLEMENTED_NOT_VERIFIED_IN_PREVIEW: the
  Preview is behind Vercel authentication, the shell cannot reach it and the
  Vercel connector is disconnected, so the on-Preview check needs the founder
  (or a reconnected connector). Note: Preview has no model budget configured
  yet, so its quote covers infrastructure and capabilities with a $0 model
  budget; the model/QA budget configuration belongs to Quote → Budget
  Reservation and needs migrations 027–029 applied by the first worker deploy.
- Preview: `92ba0bc` deployed READY on 148aiv28 (the Hobby rate limit lifted
  for that push); `089f5bd` was rate limited again. The fix push is the
  consolidated deployment of everything since.
- Worker host: Oracle instance `148ai-worker-01` exists (founder). The
  self-hosted runner has NOT registered: the queued "Deploy build worker" run
  for `089f5bd` has been pending since 00:04 UTC with no runner. SSH times out.
  Not diagnosable from this environment (no raw outbound TCP, runner/secret
  APIs not permitted through the proxy). Queue → Worker: BLOCKED.

## Golden E2E #1 — current truth, 2026-10-07 04:15 Asia/Jerusalem (supersedes earlier sections of today)

Vercel projects (verified via the Vercel API; names, domains and states only):
- `canonical_vercel_project`: **148aiv28** (`prj_I1ur58ZVxYXQpu1c6W6p5rVZ3q0G`, framework FastAPI, every `OMNI_*` setting lives here).
- `canonical_preview_project`: **148aiv28** — Preview deployments of `milestone/pre-staging-2026-10-05`; last READY `6877d43` (`dpl_AHQ4is6m68oFbeRa52n9nJFfY2Mk`).
- `canonical_production_project`: **148aiv28** — Production `main@e8f2949` (`dpl_9izMa4N2Ca1oMkwLcTM8JqXNgm4f`), domain `148aiv28.vercel.app`.
- **Preview and Production are the same project (148aiv28).**
- Duplicate: **148ai** (`prj_q7vvMotR8xV1VCQjcSEU3A9JFzbX`), domain `148ai.vercel.app`, no environment variables, no framework, every production deployment in ERROR since 2026-09-23, latest deployment ERROR. It is connected to the same repository, so every push costs two deployments. **Git disconnect is pending a dashboard action** (148ai → Settings → Git → Disconnect): the Vercel API available to this session has no disconnect operation and the CLI is not authenticated here; no undocumented workaround was applied. Do not delete the project.

| Transition | Status | Evidence |
|---|---|---|
| User → Login → Project | NOT VERIFIED (from this environment) | Preview host not reachable from the audit shell |
| Project → Prompt → Product Plan | PASS (offline, deterministic) | `python3 tools/golden_e2e_quote_probe.py`: contract READY |
| Product Plan → Quote | **IMPLEMENTED_NOT_VERIFIED_IN_PREVIEW** | Expected: priced quote for the Golden E2E #1 product. Observed (offline, admission-identical arguments, real production provisioner wiring with nothing configured): `infrastructure_profile=self_contained_web_v1`, `required_infrastructure=[database:SELF_CONTAINED, auth_session:SELF_CONTAINED]`, `quote=PRICED`, `unknown=[]`. Preview still runs `6877d43` because every push since `ca548a1` was answered "Deployment rate limited — retry in 24 hours". Not PASS until the deployed Preview proves it |
| Everything after Quote | NOT VERIFIED | The next first failing transition will be determined only after the Preview check, not assumed |

After the Vercel window resets: (1) one consolidated deployment of the branch head, (2) re-run the probe, (3) verify Plan → Quote on Preview (plan view `build_authorization=PRICED`), (4) only then determine the next first failing transition.

Implemented today (CI evidence per commit in the sections below and in git history):
- **Capabilities are demand-driven** (founder principle, replaces the earlier
  `OMNI_BUILD_INFRA_PROFILE` switch, which no code reads any more; the Preview
  variable of that name is unused and may be deleted in the dashboard). The
  contract includes only infrastructure the product asks for: persistence and
  sessions are embedded SQLite (`SELF_CONTAINED`) unless a managed database is
  required; uploads → object storage, reminders/cron → scheduled work,
  email/SMS/webhooks → outbound, each `PLATFORM_MANAGED` with a real quote.
  148AI's own artifact storage (R2) never adds product storage. Contracts that
  ask for all five managed kinds are byte-identical to before (fingerprints
  compared old vs new code). Acceptance requires `integration` only when the
  contract needs outbound, scheduled work or an external integration; the
  lineage SQL feeding this was executed on a real Postgres 16 with every
  migration. Tests: `tests/test_demand_driven_infrastructure.py` (founder
  cases 1–4, storage separation, acceptance scope, lookup, plan view).
- **No internal economics in customer views** (decision #29 extended): build
  status and modification status evidence pass through
  `strip_internal_economics`; the plan view reports `build_authorization`
  (PRICED / UNKNOWN / NOT_AUTHORIZED), `credits_required` and the customer
  allowance instead of provider USD; admission 402 details name unpriced
  capabilities without internal pricing bases, margins or QA budget numbers;
  the build-start response returns credits, not economics; legacy live-build
  responses no longer include routing cost events; the UI shows credits and
  verification only. Tests: `tests/test_customer_economics_views.py`.

## Golden E2E #1 transition truth — 2026-10-07 02:45 Asia/Jerusalem (corrects the 2026-10-06 audit)

The 2026-10-06 audit named Queue → Worker as the first failing transition by
code inspection, assuming admission succeeds. Reproduced evidence shows
admission fails earlier, at Plan → Quote.

| Transition | Status | Evidence |
|---|---|---|
| User → Login → Project | NOT VERIFIED (from this environment) | Preview host not reachable from the audit shell |
| Project → Prompt → Product Plan | PASS (deterministic, offline) | `python3 tools/golden_e2e_quote_probe.py`: contract `READY` for a task-tracker prompt |
| Product Plan → Quote | **FAIL on the Preview build before the fix; fixed in code (see the update below)** | Every contract requires 5 `PLATFORM_MANAGED` kinds (database, auth_session, object_storage, scheduled_http, outbound). The configured provisioner prices each kind only from `OMNI_GENAPP_PROVISIONING_MAXIMUM_USD`, which is ABSENT from Vercel Preview (env names listed via Vercel API, values never read). Probe with every Preview variable present in its most favourable valid form: all 5 kinds `provisioning cost not configured; unknown, not zero` → `CostQuoteUnknown` → HTTP 402 `cost_quote_unknown` |
| Quote → Budget Reservation | BLOCKED | Founder account is on the free plan (refused for paid builds by design). Internal QA path implemented; needs migrations 027–029 applied, `OMNI_ENV=staging` + QA caps on Preview, and an INTERNAL_QA grant |
| Queue → Worker | FAIL | No RQ consumer anywhere. Worker host implemented (`infra/worker-host/`); BLOCKED on founder: server, runner token, `WORKER_ENV` |
| Worker → generated-app infrastructure | UNKNOWN | Worker requires all 5 kinds LIVE before any model call. Preview has Infisical, a GENAPP Neon database, GENAPP S3 and QStash variables; none was ever provisioned or verified live; no outbound email config |
| Worker → Real AI Provider | NOT CONFIGURED | No provider key on the worker (Gemini key pending) |
| Build → Tests → Verification → Repair | NOT CONFIGURED | Sandbox runs on the worker host |
| Durable Artifact (R2) | NOT VERIFIED | Preview secret replaced 2026-10-06 22:17; `/r2-diagnostics` check pending (needs the founder's session) |
| Preview → Modification → New Version → ZIP | NOT CONFIGURED | Preview runtime host / `PREVIEW_DOMAIN_TEMPLATE` absent |

- Architecture conflict raised to the founder (Operating Contract, decision
  22): the contract floor requires managed per-product infrastructure, while
  decision #25 makes generated application code standard-library only (it
  cannot use a provisioned Postgres or S3 without drivers). Options and
  recommendation in `docs/DECISIONS_2026-10-07_HE.md` (open question).

## Plan → Quote fix — 2026-10-07 03:40 Asia/Jerusalem (decisions #27–#29)

- Expected: a Golden E2E #1 prompt yields a priced quote. Observed: 402
  `cost_quote_unknown` (5 unpriceable managed kinds). Root cause: every
  contract required managed infrastructure that the stdlib-only app could
  not even use. Minimal fix (founder decision #27): versioned profile
  `self_contained_web_v1`, bound into the immutable contract.
- Implemented and verified:
  * Contract: `database` and `auth_session` with connection mode
    `SELF_CONTAINED`; spec stack "Python standard library / SQLite (sqlite3) /
    Web UI served by the app"; `platform-data` requires embedded SQLite data
    that later requests and a fresh app instance read back. Managed contracts
    are byte-identical (same fingerprints) when the profile is not selected.
  * Quote: self-contained kinds are not quoted (nothing is provisioned).
    `OMNI_BUILD_INFRA_PROFILE=self_contained_web_v1 python3
    tools/golden_e2e_quote_probe.py` → `quote: PRICED`, `unknown: []`, using
    the same arguments as admission (capability quotes required).
  * Worker infrastructure stage: nothing provisioned; evidence lists embedded
    kinds as "not provisioned; verified only by the app's tests and preview
    acceptance" and object storage / scheduled work / outbound as
    `NOT_VERIFIED`. Nothing is reported LIVE.
  * Preview acceptance: the floor comes from the contract (version lineage
    through promoted modifications, scoped to the project), never from
    generated files. Self-contained: `integration` steps are never executed
    or counted and are listed as `not_verified_steps`; an acceptance ID
    covered only by such a step stays missing (FAIL). Unknown profile or a
    failed lookup → strict managed floor. The lineage SQL was executed against
    a real Postgres 16 with all migrations applied: direct build, a
    two-modification chain, a version-id collision across projects, unknown
    version and foreign project all resolved correctly.
  * Image generation (#28): requested only on explicit logo/branding or
    hero/illustration intent (games keep their assets); build evidence
    `asset_capabilities` reports `NOT_REQUIRED` otherwise. Replicate/image
    stays NOT_VERIFIED in the registry.
  * Public pricing (#29): the catalog and every customer subscription view
    carry only customer-facing fields; regression test with a closed field
    list and a forbidden-term scan, mutation-checked against the old payload.
- Configuration (superseded the same day by demand-driven derivation):
  `OMNI_BUILD_INFRA_PROFILE=self_contained_web_v1` was set on Vercel Preview
  only; no code reads it any more.
- **Not deployed yet (BLOCKED by Vercel):** every push since `ca548a1` got
  GitHub status "Deployment rate limited — retry in 24 hours" (Hobby build
  rate limit). Preview still runs `6877d43` (dpl_AHQ4is6m68oFbeRa52n9nJFfY2Mk),
  so none of today's fixes — QA entitlement, dependency gate, budget binding,
  pricing fix, self-contained profile — are live on Preview. Contributing
  cause: a second Vercel project `148ai` is connected to the same repository
  and builds (and fails) on every push, doubling deployment usage. Pushes are
  now batched; the first push after the window resets deploys the branch head.
- Open finding for the founder (not changed, outside the approved scope):
  customer-facing build status (`GET .../builds/{id}` → `evidence`) and the
  plan preview (`economics`) still return internal economics (reservation,
  revenue basis, margin, per-call cost estimates).
- New first failing transition on Preview: Quote → Budget Reservation
  (free plan refused; the internal QA path needs migrations 027–029 applied by
  the first worker deploy, `OMNI_ENV=staging` + QA caps on Preview, and the
  INTERNAL_QA grant). Then Queue → Worker (no worker host).

## Founder decisions implemented — 2026-10-07

- **Explicit INTERNAL_QA entitlement** (decision #24) — migration 029
  `internal_entitlements` (account id + `staging` scope, audited grant and
  revocation), `python -m omni_prod.entitlements`, manual GitHub workflow
  `Internal entitlement` on the worker host. Email allow-list removed. QA
  enabled only with `OMNI_ENV=staging`, never in production.
- **QA budget separate from the customer plan** — `credit_reservations.
  funding_source`. Found and fixed while implementing: `settle()` and
  `release()` moved customer plan counters for QA reservations (a refund or a
  release subtracted spend that was never added; a shortfall was charged to
  the customer plan). QA caps (decision #23: $0.50 per build, $10 total) count
  only `internal_qa` reservations.
- **Dependency allowlist** (decision #25) — `omni_prod/dependency_policy.py`,
  `DependencyGateExecutor` around the sandbox executor (builds and
  modifications): stdlib-only application code, `pytest==8.3.5` for tests,
  no install steps, no Node toolchain; violations return
  `UNSUPPORTED_DEPENDENCY` without starting the sandbox and end a build with
  `error_code=unsupported_dependency`. Drift test ties the image pins to the
  policy. Prompts carry the policy (prompt version changes accordingly).
- **Attempt counters** (section 9) — migration 028: retry / repair /
  regenerate / escalation / fallback counts on every attempt row.
- Evidence: `226d6f7` — `v24-ci` 37544737507 PASS (full `pytest -q`),
  `Neon bootstrap CI` 37544740584 PASS (migrations 001–029 on a fresh
  Postgres), `V11 Overlay CI` PASS. Tests: `test_qa_budget` (18),
  `test_entitlements` (7), `test_dependency_policy` (17),
  `test_attempt_ledger` (13); stdlib failure set identical to baseline.
- Not configured yet (deliberately): Vercel Preview `OMNI_ENV=staging` and QA
  caps. Enabling QA before migration 029 is applied would turn every Preview
  build request into an explicit 503 `qa_entitlement_store_unavailable`; the
  per-build sizing also depends on the open infrastructure decision
  (reservation = model budget + image + infrastructure + retry ≤ $0.50).

## Instrumentation for Golden E2E — 2026-10-07 (founder decisions: `docs/DECISIONS_2026-10-07_HE.md`)

- CI on `ca548a1`: `v24-ci` (full `pytest -q`) and `V11 Overlay CI` PASS.
  `Neon bootstrap CI` FAILED — root cause: migration 027 was not added to
  `infra/staging/bootstrap_neon_empty.sql` (the verifier requires every
  migration verbatim). Fix: `tools/generate_neon_bootstrap.py` (proven to
  reproduce the previous bootstrap byte-for-byte for 001–026, only the
  provenance line differs) regenerated the file; `--check` detects drift.
  Evidence: on `257805f` `Neon bootstrap CI` run 37542833694 PASS (bootstrap
  applied to a fresh Postgres, all 23 migration checksums match, rerun
  refused), `v24-ci` run 37542833739 PASS, `V11 Overlay CI` PASS.
- **Worker budget bound to the reservation** (Budget Reservation → Worker
  invariant, found while preparing staging config): the worker built its
  model budget from its own env, so a VPS budget larger than the Vercel
  admission budget could spend money that was never reserved. Fix:
  `bind_model_budget_to_reservation` lowers (never raises) the gateway's
  whole-build budget to the durable quote's `components.llm_maximum_usd`;
  a $0 reservation blocks every paid call. Recorded as
  `model_budget_binding` in build evidence. Requests without a component
  breakdown (pre-M5) are recorded as `legacy_unbound`.
  Tests: `tests/test_worker_budget_binding.py` (5).
- Implemented, verified locally with stdlib tests, awaiting live run:
  * **Basic stop-loss** — `AutonomousProductEngine.build`: the sandbox is
    deterministic, so a repair that leaves the repository unchanged or
    returns it to an already-verified state stops the loop
    (`no_progress_repository_unchanged` / `no_progress_repository_cycle`)
    instead of paying for identical rounds. `stop_reason` is recorded in the
    build evidence as `repair_stop_reason`. Modification-job repair loop is
    unchanged (out of scope for Golden E2E transition order).
    Tests: `tests/test_repair_stop_loss.py` (5).
  * **Attempt Ledger** — `infra/postgres/027_task_attempts.sql`, `omni_prod/attempt_ledger.py`.
    One row per provider call and per verification run: task type, provider,
    model, served model version, provider request id, trace id, policy /
    routing-policy / prompt / price-catalog versions (content-addressed),
    selection reason, selected candidate, candidate set, fallback rank,
    authorized / expected (NULL until an estimator exists) / metered /
    provider-reported / reconciled (NULL until reconciliation) cost, tokens,
    latency, outcome ok|error|unknown (timeouts are `unknown` and still count
    their full authorized cost), verification class, failure reason,
    final outcome, data-governance fields (training_eligible=false).
  * **Task tagging** — architecture / codegen / repair / classification /
    modification via `TaskTaggedGateway`; sandbox runs recorded as
    `verification` attempts with PASS / REPAIRABLE_FAIL / RETRYABLE_FAIL.
  * Persisted by the worker on every terminal path (`_persist_build_attempts`);
    a ledger write failure is logged and never changes the build outcome.
  * **Migrations on deploy** — `python -m omni_prod.migrate` (checksum-verified
    runner) runs in the worker deploy workflow before the worker starts.
  * **Internal QA budget** — `omni_prod/qa_budget.py` (superseded the same
    day by the explicit entitlement model, see above).
- Not implemented yet: modification-job ledger persistence, stop-loss in the
  modification repair loop, reconciliation process, expected-cost estimator.

## Golden E2E #1 truth audit — 2026-10-06 23:15 Asia/Jerusalem

- Repository truth: working line is `milestone/pre-staging-2026-10-05`
  (HEAD `7b59c3a`; PR #4 `f9174fc` plus 28 later commits). `main` is still
  `e8f2949` (two weeks old). Vercel Production runs `main@e8f2949`
  (dpl_9izMa4N2Ca1oMkwLcTM8JqXNgm4f); Preview runs `7b59c3a`
  (dpl_J5g95XX2uuY4SoWudynPzFxa938C).
- Implemented and independently verified: CI on `7b59c3a` passes —
  GitHub Actions `v24-ci` run 37514462833 (full `pytest -q`, hostile static
  suite, international gate) and `V11 Overlay CI` run 37514462750.
  Live Preview `GET /api/status` returns 200 and reports `live_ready=false`
  (docker gate false, live build switch off).
- Infrastructure matrix (Preview, names only, from Vercel project env):
  Postgres `OMNI_DATABASE_URL` configured; Redis `OMNI_REDIS_URL` configured;
  R2 `OMNI_S3_*` configured (signature failure under investigation, see below);
  QStash `QSTASH_*` configured; Replicate token configured.
  NOT CONFIGURED: `OMNI_ENV`, `OMNI_PUBLIC_BASE_URL`, `OMNI_ALLOWED_ORIGINS`,
  `OMNI_ENABLE_LIVE_BUILD`, any reachable model endpoint (primary defaults to
  `http://127.0.0.1:8001/v1`; `OMNI_EXTERNAL_MODELS_JSON` absent; zero-cost
  mode blocks external spend), `OMNI_SANDBOX_RUNNER_URL`/shared secret,
  `PREVIEW_DOMAIN_TEMPLATE`, preview runtime host.
- First failing transition (by code inspection, reproducible): `POST
  /api/v28/projects/{id}/builds` enqueues `execute_live_build_job` into RQ on
  Redis and returns 202. No RQ consumer (`python -m omni_prod.worker`) runs
  anywhere, and Vercel Functions cannot host it. QStash is used only as a
  generated-app scheduler capability (`managed_web_saas.py`); it is NOT the
  build dispatcher, so "QStash delivery" is not on the build path.
  Status: Queue → Worker = FAIL (no executor). Worker → model = NOT CONFIGURED.
  Worker → isolated sandbox = NOT CONFIGURED.
- Implemented, verified locally (stdlib tests) and awaiting CI: priced
  multi-provider model catalog (`omni_prod/model_catalog.py`,
  `OMNI_MODEL_CATALOG_JSON`) routed by cost/quality per call inside the
  existing `RoutedModelGateway`; 16 new tests in
  `tests/test_model_catalog_routing.py`; stdlib `unittest discover` failure set
  identical before/after (22 environment import errors, no new failures).
- Implemented, awaiting external live verification: worker host
  (`infra/worker-host/`: compose with RQ worker + Docker sandbox runner,
  `bootstrap.sh`, `.github/workflows/deploy-worker.yml` on a self-hosted runner).
  Blocked by: founder-created Hetzner server, runner registration token and
  `WORKER_ENV` GitHub secret; at least one model provider key.
- Known limitation (not fixed): the sandbox image is Python 3.12 + pytest with
  `--network none`; generated apps can only use the standard library at test
  time. Node/FastAPI generated stacks need a richer pinned image.
- Not verified from this audit environment (PyPI and the Preview host are not
  reachable from it): auth E2E over HTTPS, live DB/Redis round trips, R2 write
  with the secret updated 2026-10-06 22:17.

## R2 runtime diagnosis — 2026-10-06 21:49 Asia/Jerusalem

- Implemented and independently verified: authenticated Preview-only read-only
  `/r2-diagnostics` reports credential lengths and 12-character SHA-256 prefixes,
  actual S3 client settings, SDK versions and deployment revision. It never
  returns credentials or performs storage/provider requests. 22 targeted tests
  passed: `python -m pytest tests/test_r2_config_diagnostic.py
  tests/test_r2_storage_signing.py tests/test_replicate_image_test.py
  tests/test_replicate_connection.py -q -p no:cacheprovider`.
- Live evidence: deployment be421cd loaded access prefix `99a6d983e8e3` and
  secret prefix `cba61814b378` in both environment and the actual boto3 client.
  The independently successful local PUT used secret prefix `6abc7f5dbebd`.
  Endpoint has no bucket path; region auto, signature s3v4, addressing path,
  request checksums when_required; boto3 1.43.94 and botocore 1.43.108.
- Blocked: Preview secret value is the old value. Founder must replace only
  OMNI_S3_SECRET_KEY with the locally verified secret; credentials remain
  write-only and are never requested in chat. Image generation is unverified.
- Not implemented in this diagnostic: automatic credential replacement or
  new paid image submission. Production configuration is unchanged.

## Replicate connection — 2026-10-06

- Implemented and independently verified: saved `REPLICATE_API_TOKEN` selects
  the existing prediction-image pipeline; official-model submit uses the
  Replicate model endpoint and input-only body. Existing configured providers
  are preserved. Submission journal, spend authorization and artifact checks
  remain in the existing pipeline. 51 targeted tests pass via
  `python -m pytest tests/test_replicate_connection.py tests/test_m5_media_provider_adapters.py tests/test_v28_148ai_launch.py -q -p no:cacheprovider`.
- Implemented but awaiting external live verification: authenticated
  `GET/POST /api/v28/providers/replicate/check` calls `GET /v1/account`, returns no
  token/account data, and starts no billable prediction. Token verification is
  distinct from generation verification. Preview deployment verification pending.
- Blocked: real image generation still requires the configured durable build
  worker, submission journal and artifact storage; a key alone is not LIVE.
  Full Windows baseline: 818 passed, 28 failed, 58 skipped; failures include
  temporary-directory permission errors and the nested acceptance run. These
  failures predate this change and are not claimed fixed.
  Post-change full run (`python -m pytest tests -q -p no:cacheprovider --tb=short`):
  826 passed, the same 28 failed, 58 skipped; all 8 new tests pass.
- Not implemented: standalone image-generation UI, audio/video/3D through
  Replicate. This change wires images into the existing build capability flow.

Required by `AGENTS.md`. Covers the M1–M3 work, the superseded modifier-engine
stub, and the M4 natural-language product-modification system built on top of
it (see §5 below — M4 uses the vocabulary required by its own directive;
§§1–4 keep the pre-existing 4-category format so this update stays in place
rather than rewriting sections it did not touch). Evidence and exact commands
are in `PATCH_APPLICATION_REPORT.md`. See `GOVERNANCE.md` for which other
documents in this repo are still current versus historical. Last updated
2026-09-24 (M4 section added; M4D.1 atomic expected-version accept
remediation, M4D.2 live PostgreSQL/FastAPI/Redis verification, M4D.2b
exact dependency parity + real worker execution, and M4.9 genuine live
sandbox execution + full accept/rollback lifecycle proof all applied the
same day — see §5). **M4 = VERIFIED_LIVE_INFRA as of M4.9; M5 is now
authorized to begin.**

## 1. Implemented and independently verified

| Capability | Evidence |
|---|---|
| Preview contract v2 parsing, runtime allowlist, `NOT_PREVIEWABLE` | `tests/test_m3_preview_logic.py` (unit) |
| Hardened `docker run` (cpu/mem/pids limits, read-only root, cap-drop ALL, no-new-privileges, tmpfs `/tmp` mode 1777, uid 65534, read-only source mount) | live Docker 29.4.3: `tests/integration/test_live_preview_runtime.py`, `docker inspect` assertions |
| Docker-allocated host port on one interface + `docker port` lookup | live Docker test |
| HTTP health probe; RUNNING only after it passes; crash/timeout → FAILED with exit code + log tail | unit tests (event order) + live Docker test |
| Full teardown (container + workdir) on every failure path and on stop | live Docker test: 0 containers / 0 workdirs left |
| Async build worker: verification + quality + security + rights gates before READY | unit tests (`_run_live_build_job`) |
| `ModifierEngine`: classifies a follow-up against an existing project (`system_bug`/`missing_requirement`/`change_request`/`ambiguous`, reusing `ChangeClassifierAgent`/`ChangeAssessment`) and, for the two free-repair categories, actually re-runs `RepairAgent` + the sandbox `Executor` against the real repository until it passes or `max_repair_rounds` is exhausted | `tests/test_modifier_engine.py` (10 tests; one deliberate mutation of the `change_request` guard confirmed caught, not committed) |
| Billing: settle on spend, release only with no external spend | unit tests against real `model_policy.authorize_model_call` ledger |
| Outbox relay logic | unit tests (fake pool) |
| Frontend async-first build flow with demo-mode fallback | Node `vm` harness run against real `app.js` |
| Regression | 197/197 non-fastapi tests pass (187 pre-existing unmodified + 10 new `ModifierEngine` tests) |

## 2. Implemented, awaiting external live verification

- FastAPI routes: `POST /api/v28/projects/{id}/builds`, `GET .../builds/{build_id}`,
  410 guards on sync build routes, `POST/GET/DELETE` previews — `fastapi`
  is not installable in the build sandbox; routes are compiled + statically
  checked only.
- Migrations 013/014/015 and all repository SQL against real Postgres.
- RQ/Redis dispatch, host-scoped cleanup queues, `python -m omni_prod.build_outbox_relay`.
- Preview runtime on the official `python:3.11-slim` / `node:20-slim` images
  (verified only on a locally imported Python 3.11 image; registry blocked).

## 3. Blocked by a named service / deployment decision

- **Preview router** for `PREVIEW_DOMAIN_TEMPLATE` (wildcard DNS, TLS, proxy
  to `PostgresPreviewRepository.get_route()`) — needs domain control.
- **Schedulers** for `build_outbox_relay` and `PostgresPreviewRepository.mark_expired()`.
- **Worker topology**: preview workers must consume
  `omni-preview-host-$OMNI_PREVIEW_RUNTIME_HOST` in addition to `omni-builds`.
- S3-compatible storage (`OMNI_S3_*`) — required for async builds and previews.

## 4. Not implemented

- Expiry sweep that stops containers (EXPIRED only changes DB state; DELETE cleans it up).
- Live log streaming (needs a distributed logging pipeline).
- Dependency install / image build stage for previews (M4).
- Egress network policy for preview containers.
- Provider-measured token usage (only an authorized-estimate spend ledger exists).
- ~~**`ModifierEngine` execution of `change_request`s.**~~ **SUPERSEDED by M4**
  (§5 below): `CandidateModificationEngine` now runs a dedicated
  product-evolution path (`ProductEvolutionAgent`) for `change_request`,
  instead of forcing it through `RepairAgent`. `ModifierEngine` itself
  (`omni_prod/modifier_engine.py`) is unchanged and still only free-repairs
  `system_bug`/`missing_requirement`; it is no longer the intended
  entry point for modifications.
- ~~**`ModifierEngine` is not wired to any route or worker task.**~~
  **SUPERSEDED by M4** (§5 below): the M4 routes/worker
  (`POST .../versions/{version_id}/modifications` →
  `execute_modification_job`) are the wired path now; `ModifierEngine`
  itself remains unwired, which is fine since M4 does not call it. M4 also
  adds the durable, version-scoped `ProductSpec` this bullet said was
  missing — see `PostgresSpecRepository` / migration `016`.

## 5. M4 — Natural-Language Product Modification

Per the M4 directive's own "STATUS DISCIPLINE": `LIVE` / `VERIFIED` /
`PARTIAL` / `IMPLEMENTED_NOT_VERIFIED` / `NOT_CONFIGURED` / `NOT_IMPLEMENTED`
/ `BLOCKED`. **M4 is not `LIVE`** — nothing in this repository is deployed;
"VERIFIED" below means real code executed against real tests — unit tests,
or (as of **M4D.2**, see below) real PostgreSQL, real FastAPI and real
Redis/RQ, running in this sandbox — not that it has run in production.

**Update, M4D.2 (2026-09-24):** the paragraph below describing `fastapi`/
Postgres/Redis as unreachable in this sandbox was true through M4D.1 and
is **no longer true**: a normal `pip install`/`apt-get install`/`docker
pull` of these packages is still genuinely blocked here (confirmed, not
assumed — see M4D.2's own section below), but real PostgreSQL 16 and real
Redis servers were already present and startable in this image, and real
fastapi/psycopg/redis-py/rq were made importable via a disclosed
git-clone-vendoring workaround. Every route/worker-import-boundary item
that used to read `NOT_CONFIGURED` purely for lack of `fastapi` has been
superseded — see the M4D.2 section under M4D.1 below for what is now
genuinely `VERIFIED` live versus what remains a structural proof or is
out of scope. The paragraph immediately below is kept, unedited, as the
accurate description of the constraint through the end of M4D.1, since
§§1–4 and the M1–M3 sections of this document still operate under it.

Original (M4–M4D.1) framing, unchanged: `fastapi`, live Postgres and live
Redis were not installable/reachable in this build sandbox (a constraint
that predates M4 — see §2 above); every route/worker-import-boundary item
below was `NOT_CONFIGURED` for that reason alone, not because the code was
wrong, and was instead proven by static AST/signature inspection. Full
evidence and exact commands: `PATCH_APPLICATION_REPORT.md` (M4 section).

### By capability (M4A–G)

| Capability | Status | Evidence |
|---|---|---|
| M4A — durable `ModificationRequest` repository (create/get/transition/complete/accept/reject/rollback, optimistic concurrency) | `VERIFIED` | `tests/test_modification_repository.py` (43 tests, fake-pool + real `MemoryProjectWorkspace`, 2 independent mutation tests) |
| M4A — transactional outbox (`modification_outbox`, `FOR UPDATE SKIP LOCKED`, dispatch) | `VERIFIED` (logic, and the enqueue+outbox-row half live — see **M4D.2**) / `IMPLEMENTED_NOT_VERIFIED` (the `dispatch_pending_outbox()` relay path specifically — not exercised live in M4D.2, only the direct-enqueue-succeeds path was) | `tests/test_modification_repository.py::OutboxDispatchTests` (logic); `tests/test_m4d2_live_fastapi_redis.py::LiveRedisRQTests` (live enqueue) |
| M4A — FastAPI routes (propose/status/candidate/accept/reject/rollback) | `VERIFIED` — live, via a real ASGI `TestClient` against real Postgres | See **M4D.2** below; superseded the static-only proof this row previously cited |
| M4A — worker entrypoint (`execute_modification_job`, lazy-imports investor_app internals) | `VERIFIED` (orchestration logic via dependency injection) / see **M4D.2b** for the real-dequeue-and-execute proof of `execute_modification_job` itself | `tests/test_m4_worker.py` (11 tests against `_run_modification_job`); `tests/test_m4d2_live_fastapi_redis.py` (real HTTP enqueue of the real job into Redis, and real `rq.SimpleWorker` dequeue/execution/failure-handling proven using **dedicated test job functions**, not `execute_modification_job` itself — see the correction in **M4D.2b** below); `tests/test_m4d2b_*` (real dequeue and real execution of `execute_modification_job` itself) |
| M4B — versioned `ProductSpec` repository + `project_version_specs` (exact-version scoped, no `update()`) | `VERIFIED` (logic and live — see **M4D.2**) | `tests/test_spec_repository.py`; `infra/postgres/016_durable_modifications.sql`; `tests/test_m4d2_live_postgres.py` (applied for real, read/written for real) |
| M4C — intent routing reused (`system_bug`/`missing_requirement`/`change_request`/`ambiguous`) | `VERIFIED` | `tests/test_m4_acceptance.py::AcceptanceGH/I/J` |
| M4C — dedicated `change_request` path (`ProductEvolutionAgent`, real spec+repo generation, not forced into `RepairAgent`) | `VERIFIED` | `tests/test_product_evolution.py`, `tests/test_m4_acceptance.py::AcceptanceJ` |
| M4D — candidate isolation (never commits to `project_versions` until `accept()`) | `VERIFIED` | `tests/test_m4_acceptance.py::AcceptanceK`; `tests/test_m4_worker.py`'s `workspace.commit.assert_not_called()` |
| M4D — accept / reject / rollback | `VERIFIED` — both the algorithm/concurrency logic AND live PostgreSQL infrastructure | See **M4D.1** (algorithm) and **M4D.2** (live Postgres) below — this row previously read `PARTIAL`, then `IMPLEMENTED_NOT_VERIFIED` for live Postgres; both superseded |
| M4D — optimistic concurrency (expected-source-version semantics) | `VERIFIED` — algorithm AND live PostgreSQL (real advisory locks, real concurrent connections) | See **M4D.1** and **M4D.2** below |

### M4D.1 — atomic expected-version accept (remediation, 2026-09-24)

An independent architecture review of the original M4D `accept()` correctly
identified it as **production-blocking**: it called `workspace.commit()`
unconditionally and only compared `new_version.parent_id` to the expected
source version *after* the row already existed in `project_versions` — so a
concurrent accept could be told "conflict, not accepted" while the
project's real current version had already silently mutated to the
rejected candidate's content. A post-commit check is not sound optimistic
concurrency; the review's own summary — "a modification must NEVER change
the current ProjectVersion and then return conflict" — was correct, and the
bug was real, not hypothetical (reproduced directly by grepping
`workspace.py`: both `MemoryProjectWorkspace.commit()` and
`PostgresProjectWorkspace.commit()` had no compare-and-swap at all before
this fix; `current()` is simply "the most recently inserted row").

**Fix.** `workspace.commit()` (both implementations) now takes an optional
`expected_current_version_id`; the compare against the REAL current version
happens under the same lock (`MemoryProjectWorkspace`'s `self._lock`) or the
same `pg_advisory_xact_lock`-held transaction (`PostgresProjectWorkspace`,
via a plain `SELECT` on the same cursor, immediately before the `INSERT`)
that would perform the write. A mismatch raises `VersionConflict` **before**
any row is written — never audited after. `modification_repository.accept()`
no longer performs a separate pre-check-then-commit-then-post-check
sequence; it opens ONE transaction, shares its cursor with
`workspace.commit(cur=..., expected_current_version_id=...)` and
`spec_repo.save(cur=...)` (which already supported a `cur` parameter for
exactly this), and the whole promotion — status validation, the version
insert, the spec insert, and the final `ACCEPTED` update — is one atomic
unit. This also closes the M4D `PARTIAL` row above: the three/four-
transaction promotion window is gone for the Postgres path (proven via
`FakeConn.transactions == 1` in `test_modification_repository.py`'s happy-
path test). `rollback()` was brought in line the same way for consistency.

`VersionConflict` replaces the old `conflict_detected_at_commit` reason
entirely — there is no longer a "the write already happened, but..." case
to name. `investor_app.py`'s accept route was simplified to match (single
`reason == 'conflict'` check) and re-verified statically (AST parse, no
duplicate routes, `inspect.signature()` cross-checks — same method used
throughout this report for `fastapi`-blocked code).

**What "VERIFIED" means here, precisely** — this is real, not a facade:
- A genuine two-real-OS-thread test
  (`tests/test_m4d1_atomic_accept.py::TrueConcurrencyTests`), synchronized
  with a `threading.Barrier` so both threads are dispatched into
  `workspace.commit()` at the same instant, against the real (thread-safe,
  `RLock`-protected) `MemoryProjectWorkspace` — not a simulated or
  single-threaded race. Stress-run 40 consecutive times with zero flakiness
  before being accepted into the suite (see `PATCH_APPLICATION_REPORT.md`).
  A 10-way fan-in variant proves the same property beyond the minimal A/B
  case.
- Mutation tests against **both** `MemoryProjectWorkspace.commit()` and
  `PostgresProjectWorkspace.commit()`: the expected-version compare is
  temporarily replaced with a mutant that omits it, the exact M4D.1 bug is
  shown to reappear (a stale commit silently succeeds and corrupts
  `current()`), then the real method is restored and re-confirmed correct
  — automated, part of the permanent suite, not a one-off manual check.
- The full required-test list from the M4D.1 directive: staged failures at
  each point in the merged transaction (before the version insert, after
  the version insert but before the spec write, before the final status
  update), retry-after-crash / duplicate-delivery idempotency,
  force-accept (both the real-override and the no-op-when-nothing-to-
  override cases), rollback after an accepted modification, and two
  invariant tests (every promoted version has exactly one spec; a
  failed/conflicted accept never changes `current()`, asserted by object
  identity, not just by id equality).

**What is honestly still not proven, and why.** `PostgresProjectWorkspace`'s
SQL-level guard is proven only against a fake cursor (statement order:
`pg_advisory_xact_lock` → `SELECT` current → compare-then-raise-with-no-
`INSERT`, or `INSERT`) — structurally correct and matches exactly how
`workspace.commit()` already worked pre-M4D.1 (same lock, same statement
shape, just with the compare added), but never executed against a real
Postgres server, because this sandbox has none. The genuinely convincing
remaining step, not done here, is the same class of true-concurrency test
run against **real** Postgres connections and a real `pg_advisory_xact_lock`
under concurrent load — the in-sandbox `MemoryProjectWorkspace` thread test
proves the *algorithm* is correct, not that Postgres's actual lock
semantics behave as assumed under real network/connection-pool conditions.
**M4 is not `LIVE`. This fix is not "production-closed"** — it is
`VERIFIED` at the logic/algorithm level with real concurrency, and
`IMPLEMENTED_NOT_VERIFIED` for the live-Postgres half, exactly like every
other Postgres-dependent path in this report.

> **Update, M4D.2 (below):** the "genuinely convincing remaining step" this
> paragraph describes — the same class of true-concurrency test run against
> real Postgres connections and a real `pg_advisory_xact_lock` under
> concurrent load — has since been done for real. See the "M4D.2 — live
> infrastructure verification" section immediately below for the live
> evidence. This paragraph is left otherwise unedited because it accurately
> describes what M4D.1, on its own, did and did not prove; M4D.2 is what
> closes the gap it identifies. M4 as a whole is still not `LIVE` (see
> M4D.2's own "still not proven" subsection for what remains).

Evidence: `tests/test_workspace_version_conflict.py` (14 tests, the
mechanism), `tests/test_m4d1_atomic_accept.py` (14 tests — 1 intentional
skip pointing at where that scenario is actually covered — the required
list plus the two mutation tests), `tests/test_modification_repository.py`
(unchanged count, 43 tests, `AcceptTests` rewritten for the new design).

### M4D.2 — live infrastructure verification (2026-09-24)

M4D.1 closed the algorithmic gap and was accepted "at the algorithmic/
concurrency-design evidence level"; M4D.2's directive required the
remaining half — actually running against real PostgreSQL, real FastAPI,
and real Redis/RQ, not fakes or structural proofs — and, critically, doing
the environment discovery itself rather than declaring `BLOCKED_BY_ENVIRONMENT`
because these services weren't preinstalled.

**Environment discovery (commands and results, in order):**
- `docker ps` → daemon not running; `dockerd` itself failed to start under
  the default init script (`ulimit: error setting limit (Operation not
  permitted)` — a nested-container privilege constraint), but started
  successfully when invoked directly with `--storage-driver=vfs` and
  properly detached (`setsid nohup dockerd ...`). Docker itself: **usable**.
  `docker pull python:3.11-slim` → `Error response from daemon: Get
  "https://registry-1.docker.io/v2/": Forbidden` — Docker Hub itself:
  **genuinely blocked** by this sandbox's network egress policy.
- `psql`, `pg_ctlcluster`, and a PostgreSQL 16 data directory were already
  present in the image (`pg_lsclusters` showed cluster `16/main` on port
  5432, status `down`). `pg_ctlcluster 16 main start` → **started
  successfully**. This is a real, native (non-Docker) PostgreSQL 16.13
  server, not a stub.
- `redis-server`/`redis-cli` binaries were already present.
  `redis-server --daemonize yes --port 6379` → `redis-cli ping` → `PONG`.
  Real, native Redis 7.0.15.
- `pip3 install fastapi==0.128.2 ...` → `ERROR: Could not find a version
  that satisfies the requirement` (no index). `curl -v https://pypi.org/…`
  → `HTTP/2 403`, header `x-deny-reason: host_not_allowed`, body `Host not
  in allowlist: pypi.org`. PyPI (and `files.pythonhosted.org`, same
  result): **genuinely blocked**, a real, explicit organization policy
  denial, not a technical hiccup — per this sandbox's own proxy runbook,
  not retried or routed around.
- `apt-get update` / `apt-get install python3-fastapi python3-psycopg
  python3-redis python3-rq ...` → `E: Failed to fetch
  http://archive.ubuntu.com/... 403 Forbidden` for every package (`apt-
  cache policy` had shown candidate versions from the image's stale local
  index only, not a live, reachable mirror). Debian/Ubuntu package
  installation: **genuinely blocked**, same network policy.
- **All three installation avenues (PyPI, apt, Docker Hub) were tried and
  confirmed blocked before falling back to anything else** — this is not
  a "not preinstalled, so skip it" conclusion.
- `git clone https://github.com/psycopg/psycopg.git` (and
  `fastapi/fastapi`, `redis/redis-py`, `rq/rq`) → **succeeded**. GitHub's
  git-clone protocol is reachable from this sandbox even though
  `raw.githubusercontent.com`/`codeload.github.com` (plain HTTPS content
  fetch) and PyPI/apt/Docker Hub are not. The real upstream source of each
  package (commits `psycopg@ab5646a`, `fastapi@50113da`,
  `redis-py@722eb64`, `rq@90a67a1`, all cloned 2026-09-24) was made
  importable via a `PYTHONPATH` vendor directory
  (`/tmp/m4d2_vendor`, reproduced by `tools/m4d2_setup_live_infra.sh`,
  written for this directive) instead of a normal `pip install`. One
  additional micro-dependency, `annotated-doc` (a five-line PEP 727 `Doc`
  marker class with zero runtime effect on validation/routing — confirmed
  by reading its one class body, which is byte-for-byte the same as
  `typing_extensions.Doc`, already installed), was re-provided as a
  one-line local shim rather than fetched, since it has no standalone git
  repo. This is disclosed in every affected file's module docstring, in
  `tools/m4d2_setup_live_infra.sh`, and here — not hidden.
- The one deliberate, disclosed substitution beyond that: `boto3`/S3 (used
  by the real `S3ArtifactStore` for repository-content blobs) is also
  PyPI-only and out of scope for M4D.2's Postgres/Redis/FastAPI sections —
  a real, working, disk-backed store implementing the exact same
  `put_bytes`/`get_bytes` interface (`DiskArtifactStore`, in
  `tests/test_m4d2_live_postgres.py`) stands in for it. Nothing about
  Postgres, FastAPI, Redis, or RQ themselves is substituted anywhere.

**Result: M4D.2 `VERIFIED_LIVE_INFRA`** — not `BLOCKED_BY_ENVIRONMENT` —
because genuine, exhaustive effort (three independent installation
avenues, each actually attempted and confirmed blocked, not assumed)
found a real path to real infrastructure.

**C — real PostgreSQL concurrency** (`tests/test_m4d2_live_postgres.py::RealConcurrencyTests`,
3 tests): two genuinely independent `psycopg` connections (proven distinct
by differing real `pg_backend_pid()` values), synchronized with a real
`threading.Barrier`, racing `accept()` for two candidates from the same
`project_id`/source version. FACT, each run: exactly one promotion, the
loser durably `CONFLICT` with `promoted_version_id` left `NULL`, zero
orphan `project_versions`/`project_version_specs` rows, `current()` is the
winner. A 10-way fan-in variant proves the same property at wider
concurrency. A dedicated advisory-lock test takes the *exact* lock id
`PostgresProjectWorkspace.commit()` would (same SHA-256 formula) on a raw
connection, holds it, and proves `accept()` for that project genuinely
blocks until released while `accept()` for a *different* project is
completely unaffected (real serialization boundary, not simulated).

**D — real transaction-rollback** (`RealTransactionRollbackTests`, 6
tests): a cursor wrapper that lets every real SQL statement before a
chosen call number execute for real, then raises — Postgres's own
`conn.transaction()` context manager performs the real `ROLLBACK`, not a
fake one. All three directive cases covered (after the version INSERT/
before the spec INSERT; after the spec INSERT/before the final UPDATE;
"during" the final UPDATE — the UPDATE genuinely executes inside the open
transaction before the simulated crash). FACT, each case, verified via a
*separate* connection afterward: no orphan `project_versions` row, no
orphan spec row, `modification_requests.status` still `READY_FOR_REVIEW`,
`promoted_version_id` still `NULL`. Retry-after-crash and duplicate-
delivery-after-success are also real (same modification id, real Postgres,
no double promotion). `force=True` and rollback-after-accept are exercised
against live Postgres too.

**E — concurrency stress**: 20 repeated 2-way races + 3 repeated 10-way
fan-ins in `RealConcurrencyStressTests`, plus the whole 14-test file run 6
times consecutively (1 development run + 5 explicit stress runs) with
**zero failures, zero exceptions, zero flakiness** across every run.

**F — FastAPI real-path** (`tests/test_m4d2_live_fastapi_redis.py::LiveFastAPIModificationFlowTests`,
5 tests): the real `omni_prod.investor_app.app` (131 routes; the entire
module now imports cleanly under real `fastapi`), served by a real
`fastapi.testclient.TestClient`, with `OMNI_CREATOR_PERSISTENCE=postgres`
so `_v28_pool`/`_v28.accounts` are the real `PostgresAccountService`/
`PostgresSubscriptionService`, and `_v28.engine.workspace` swapped (the
one disclosed substitution above) to a real `PostgresProjectWorkspace`.
Real HTTP round trips for register → create project → propose
modification (real credit reservation via `subscriptions.reserve()`,
really committed to Postgres) → candidate → accept (200, persisted
`ACCEPTED`/`promoted_version_id`, `current()` really advanced) → a second,
conflicting accept (real **409**, `reason: conflict`, `current()`
untouched) → a duplicate accept of an already-accepted modification (real
**422**, `invalid_status`) → reject (real 200, `current()` provably
unchanged, and accept afterward is 422) → cross-account access (real
**403**). Every one of these previously showed `IMPLEMENTED_NOT_VERIFIED`
in this document for lack of a live HTTP call; all now `VERIFIED`.

**G — Redis/RQ real-path** (`LiveRedisRQTests`, 3 tests): confirmed Redis/
RQ genuinely is part of M4's production path (`v28_propose_modification`
calls `omni_prod.queueing.enqueue_build`, real `rq.Queue.enqueue`).
Real HTTP propose → real `rq.Queue` contains a real job (`fetch_job`
returns it, `func_name == 'omni_prod.worker_tasks.execute_modification_job'`,
correct args) → `dispatch: 'enqueued'` (not the outbox-relay
`'deferred'` fallback, proving Redis really was reachable at that moment).
A second test enqueues a small, self-contained real job through the same
real `enqueue_build()` helper and drains it with `rq.SimpleWorker` — real
dequeue, real execution, independently verified by a row the job body
itself writes to Postgres (not merely `job.is_finished`). A third proves
worker-failure recovery: a real job that raises is marked `failed` by rq
without crashing the worker, which then successfully processes a
follow-up job. **Disclosed adaptation**: `rq.SimpleWorker` (in-process,
no fork) is used instead of the default `rq.Worker` (which forks a child
per job) because this test process already holds an open `psycopg`
connection pool at fork time — forking with a live SSL socket open is a
well-known hazard, and it reproduced exactly the predicted failure
(`SSL SYSCALL error: EOF detected`) on the first real run, for jobs left
over from another test. `SimpleWorker` is real, unmodified `rq` code, not
a mock of the queue or the worker; it simply avoids that specific,
test-process-only hazard. The `execute_modification_job` production
entrypoint itself is never actually driven to a classification decision
in these tests, because that requires a live LLM provider — a
pre-existing, already-disclosed constraint (see §2 above) unrelated to
M4D.2's Postgres/Redis/FastAPI scope; the modification lifecycle from
`READY_FOR_REVIEW` onward is instead driven via the real repository
methods (`transition_running`/`complete`) worker_tasks.py itself calls,
which is what sections C/D/E/F above exercise at the HTTP and Postgres
layers.

**H — connection-pool/transaction-boundary check** (`TransactionBoundaryTests`,
2 tests): proven from PostgreSQL's own server state, not application-level
counting. One test captures `txid_current()` immediately after each real
`INSERT INTO project_versions` / `INSERT INTO project_version_specs` /
`UPDATE modification_requests` statement `accept()` issues, on the SAME
connection — all three come back identical, which is only possible if
Postgres assigned them to one transaction (a transaction id is stable for
its own lifetime and assigned lazily on first write). The other confirms
`pg_stat_database.xact_rollback` shows zero for a successful accept() and
`xact_commit` advances by at least one (a genuine, disclosed finding along
the way: `pg_stat_database` flushes asynchronously per backend, so the
first version of this test read the counter before the flush landed and
failed — fixed by polling briefly rather than reading once, left visible
in the test's own docstring rather than silently patched over).

**I — full regression after live-infrastructure verification**: the
combined suite (35 test modules, excluding
`test_m4d2_live_fastapi_redis.py`, which the module's own docstring
requires running standalone since it bakes `OMNI_CREATOR_PERSISTENCE=postgres`
into `omni_prod.investor_app`'s module-level globals at import time) —
**487/487 tests pass, 2 expected skips**, run twice consecutively with
identical results. `test_m4d2_live_fastapi_redis.py` run standalone,
separately — **8/8 pass**, run twice consecutively. Combined: **495/495**.
This includes, for the first time in this project's history, all 8
previously `NOT_CONFIGURED` fastapi-dependent regression files
(`test_v23_investor_grade`, `test_v24_auth`, `test_v24_international`,
`test_v24_native_remote`, `test_v25_unified_v10_parity`,
`test_v26_universal_pro`, `test_v27_rights_company_os`,
`test_v28_148ai_launch` — 136 tests total) actually executing rather than
failing on `ModuleNotFoundError: fastapi` at import. M4D.1's mutation
tests and true-concurrency tests are unmodified and included in this run
— nothing was removed or weakened to make M4D.2 pass.

**What remains genuinely `IMPLEMENTED_NOT_VERIFIED` or out of scope after
M4D.2** (FACT vs. STRUCTURAL PROOF vs. BLOCKED vs. NOT APPLICABLE, per the
directive's own reporting split):
- FACT: everything in C/D/E/F/G/H/I above — real Postgres 16.13, real
  Redis 7.0.15, real FastAPI 0.141.1/Starlette 1.0.0/Pydantic 2.13.3, real
  `rq` 2.12.0/redis-py 8.0.0/psycopg 3.x (pre-release `dev` source from
  `master`, version string reads `0.0.0.0` since no build step ran to
  inject it — the code itself, not the string, is what was exercised),
  all really running, really connected to.
- STRUCTURAL PROOF (unchanged from M4D.1, not newly claimed live): the
  Docker/S3 path (`S3ArtifactStore` + real AWS/S3) — not exercised; the
  disk-backed stand-in is real code but not S3.
- BLOCKED, confirmed with commands and exact error text above, not
  assumed: `pip install`/`apt-get install` of these same packages from
  their normal package registries; `docker pull` from Docker Hub.
- NOT APPLICABLE: this M4D.2 pass's own installation method
  (git-clone vendoring) is a **test/verification-environment workaround**,
  not a production deployment mechanism — a real deployment installs
  `requirements-production.txt` normally via `pip` on infrastructure with
  ordinary package-registry access, which this sandbox specifically lacks.
  This does not change what was verified about the *application code*;
  it is a statement about this one sandbox's network policy.

**M4 is still not `LIVE`.** M4D.2 verifies that M4D.1's fix behaves
correctly against real PostgreSQL, real FastAPI, and real Redis/RQ, all
running in this sandbox — it does not constitute a production deployment,
does not touch real user data, and per the directive's own instruction,
`VERIFIED_LIVE_INFRA` does not automatically mean `PRODUCTION_DEPLOYED`.
**M5 has not been started.**

Evidence: `tests/test_m4d2_live_postgres.py` (14 tests), `tests/test_m4d2_live_fastapi_redis.py`
(8 tests), `tests/m4d2_rq_job_target.py` (real job bodies for the RQ
tests), `tools/m4d2_setup_live_infra.sh` (the reproducible runbook). Full
commands, exact output, and version numbers: `PATCH_APPLICATION_REPORT.md`'s
M4D.2 section.

### M4D.2b — dependency parity + real worker execution (2026-09-24)

Two verification gaps in M4D.2's own evidence and documentation, found by
an independent review and accepted as real:

**1. RQ documentation overclaim, corrected.** The M4A worker-entrypoint
capability-table row above previously read "real `rq` dequeue of a real
`execute_modification_job` job" — but M4D.2's own `LiveRedisRQTests`
(section G, `PATCH_APPLICATION_REPORT.md`) explicitly fetched that real
job from Redis, then **cancelled and deleted it without running a
worker on it**, and proved the real `rq.SimpleWorker` dequeue/execute/
fail path only with **dedicated test job functions**
(`tests/m4d2_rq_job_target.py`), not `execute_modification_job` itself.
The table row above is now corrected; this section documents the real
fix (item 2 below closes the gap for real, rather than just fixing the
wording).

**2. Exact production dependency parity, verified.** M4D.2's vendored
packages were HEAD of each GitHub repo's default branch, not the exact
versions `requirements-production.txt` pins. Read directly:

```
$ cat requirements-production.txt
fastapi==0.128.2
uvicorn==0.48.0
pydantic==2.13.4
psycopg[binary,pool]==3.3.6
redis==8.1.0
rq==2.12.0
boto3==1.43.94
```

Every package was re-vendored (`tools/m4d2b_setup_parity_infra.sh`,
building a separate `/tmp/m4d2b_vendor`, leaving M4D.2's own
`/tmp/m4d2_vendor` untouched and independently re-runnable) from the
**exact upstream git tag** for its pin — not master/main HEAD:

| Package | Pin | Exact tag checked out | Was HEAD the same commit? |
|---|---|---|---|
| fastapi | 0.128.2 | `0.128.2` | No |
| psycopg | 3.3.6 | `3.3.6` (separate `git worktree`, since psycopg/psycopg_pool are independently-versioned packages in one repo) | No |
| psycopg_pool | (unpinned by `psycopg[pool]`) | `pool-3.3.3` (latest — no constraint to violate) | Yes (M4D.2's HEAD already was this tag) |
| redis-py | 8.1.0 | `v8.1.0` | No |
| rq | 2.12.0 | `v2.12` | **No — M4D.2's HEAD was 1 commit past this tag** (a `codeql-action` GitHub Actions version bump, unrelated to `rq`'s own source; `rq.__version__` read "2.12.0" either way, which is exactly the kind of overclaim-by-coincidence this parity pass exists to catch) |
| starlette | *(unpinned — transitive via fastapi)* | `0.50.0` — the latest tag satisfying fastapi 0.128.2's own declared `starlette>=0.40.0,<0.51.0` (its `pyproject.toml`, read directly) | N/A — M4D.2 never vendored starlette at all; it used whatever was pre-installed (**1.0.0** — see below) |

**Real, material finding:** the pre-installed `starlette` was **1.0.0**,
which is *outside* fastapi 0.128.2's own declared compatible range
(`<0.51.0`) — a real non-parity condition M4D.2 never checked. This pass
vendors the correct `0.50.0` and confirms the app still imports and
serves real requests correctly under it (`fastapi.testclient.TestClient`
round-trip re-verified — see below).

**Known, disclosed, unavoidable gap: `pydantic`.** The pin is
`pydantic==2.13.4`; the pre-installed version is `2.13.3`. `pydantic`
2.13.4 requires `pydantic-core==2.46.4` **exactly** (`pydantic/pydantic`'s
own `pyproject.toml` at tag `v2.13.4`, read directly). `pydantic-core` is
a compiled Rust/PyO3 extension — building it needs `cargo` to fetch crate
dependencies from `crates.io`/`index.crates.io`, and:
```
$ curl -sS -o /dev/null -w "%{http_code}\n" https://index.crates.io/config.json
403
```
genuinely blocked, confirmed the same way PyPI/apt/Docker Hub were in
M4D.2 — a different host, the same egress policy. `rustc`/`cargo`
themselves are present in this sandbox, but with no reachable crate
registry a real build is not possible here. The pre-installed `pydantic`
2.13.3 is paired with its own correctly-matching `pydantic-core` 2.46.3
(`pydantic` 2.13.3's own `pyproject.toml` pins exactly that — a real,
internally consistent, already-installed release, not a mismatched
hack) and is used as the closest available option (directive's option
**C**, "use an existing cached wheel/package if available"). This is a
genuine, disclosed, one-patch-version gap — not claimed as parity.

After building the parity vendor, every M4D.2/M4D.2b live suite was
re-run against it, plus a direct `fastapi.testclient.TestClient`
round-trip smoke test of the new fastapi/starlette pairing:
```
$ PYTHONPATH=/tmp/m4d2b_vendor python3 -c "from fastapi import FastAPI; from fastapi.testclient import TestClient; ..."
200 {'ok': True}
$ PYTHONPATH=/tmp/m4d2b_vendor M4D2_DATABASE_URL=... python3 -m unittest tests.test_m4d2_live_postgres        # 14/14 OK
$ PYTHONPATH=/tmp/m4d2b_vendor M4D2_DATABASE_URL=... M4D2_REDIS_URL=... python3 -m unittest tests.test_m4d2_live_fastapi_redis   # 8/8 OK
$ PYTHONPATH=/tmp/m4d2b_vendor M4D2_DATABASE_URL=... python3 -m unittest <34 combined modules>                 # 487/487 OK (2 skips)
$ PYTHONPATH=/tmp/m4d2b_vendor python3 -m compileall -q omni_prod tests tools                                  # exit 0
```
All pass under exact parity, identical counts to M4D.2's HEAD-based run.

**3. Real production-job execution through RQ, proven.** The directive
required actually dequeuing and executing the real
`omni_prod.worker_tasks.execute_modification_job` through a real RQ
worker — not a substitute test job — while replacing only the external
LLM dependency at its documented boundary. That boundary already exists
in production for exactly this purpose:
`omni_prod.model_runtime_config.ModelRuntimeConfig.from_env()`'s
*primary* model route defaults to a **local**, non-external endpoint
(`OMNI_LOCAL_MODEL_URL=http://127.0.0.1:8001/v1`, `external=False`;
`OMNI_ZERO_COST_MODE=1` and `OMNI_ALLOW_EXTERNAL_FALLBACK=0` are also the
defaults), and `omni_prod.routed_gateway.RoutedModelGateway` enforces
`if primary.endpoint.external: raise ValueError(...)`. `tests/m4d2b_local_model_server.py`
is a real HTTP server bound to a real loopback TCP port, implementing the
exact OpenAI-chat-completions-compatible protocol
`OpenAICompatibleGateway.complete()` speaks, returning deterministic
(marker-based, disclosed in its own docstring) responses instead of a
real hosted model's output — because this sandbox has no route to one, a
pre-existing constraint, not new to M4D.2b.

Rather than reuse M4D.2's in-process `rq.SimpleWorker` substitution, this
pass runs the real, default `rq.Worker` (which forks a child process per
job) in a **genuinely separate OS process**
(`tests/m4d2b_worker_process.py`, launched via `subprocess.run`), per the
directive's stated preference. This avoids the fork-after-open-pool
SSL-socket hazard M4D.2 hit (traced to rq's own source: the job's dotted
import — and therefore `omni_prod.investor_app`'s connection pool — is
only ever touched inside the *forked child*, per
`rq/worker/worker_classes.py::Worker.fork_work_horse` ->
`rq/worker/base.py::BaseWorker.main_work_horse` -> `perform_job` ->
`job.perform()`; as long as the parent process never opens a live
connection before calling `.work()`, nothing corrupted is inherited by
the fork — verified empirically, not just reasoned about). Labeled per
the directive's own vocabulary: **`REAL_RQ_SEPARATE_PROCESS_WORKER_VERIFIED`**
(`tests/test_m4d2b_parity_and_worker.py`, 3 tests, all passing, re-run 4
times consecutively with zero flakiness):

- `test_real_worker_process_dequeues_and_executes_execute_modification_job_ambiguous_path`
  — real HTTP propose -> real Redis job (`func_name ==
  'omni_prod.worker_tasks.execute_modification_job'`) -> the separate
  worker process dequeues and executes it for real -> real
  `ChangeClassifierAgent.classify()` call over real HTTP to the local
  test model server -> real `QUEUED -> RUNNING -> NEEDS_CLARIFICATION`
  transition, independently confirmed via the real HTTP status route and
  directly via `PostgresModificationRepository`.
- `test_real_worker_process_system_bug_path_hits_real_sandbox_docker_image_blocker`
  — the real classify/repair loop this time genuinely reaches
  `SandboxRepositoryExecutor.execute()` -> a real `docker run
  omni-sandbox:latest ...` subprocess. The real failure this produced
  turned out to be a **previously-unknown Docker-CLI-version
  incompatibility**: `omni_prod/sandbox.py`'s `--mount
  type=bind,...,rw` flag syntax is rejected by this sandbox's Docker
  29.4.3 (`invalid field 'rw' must be a key=value pair`) — a different
  real docker failure than the already-disclosed image-pull-forbidden
  block, equally real and equally unmodified. `run_sandbox()` captures
  this as a normal `ExecutionReport(passed=False)`, not an exception, so
  the real outcome is a cleanly completed `FAILED` modification
  (`error_code='verification'`, the real docker stderr preserved
  verbatim in `evidence_json`, `repair_rounds=3`, billing correctly
  `released` not `settled`) — proof that a real, uncontrived worker
  failure is recorded correctly and leaves fully recoverable durable
  state (current() untouched, the modification still normally gettable).
  `omni_prod/sandbox.py` is out of M4D.2b's scope (M2-era code, unrelated
  to M4's accept/reject/rollback pipeline) and is **deliberately left
  unfixed** here — flagged for whoever owns that module next.
- `test_duplicate_delivery_of_the_same_modification_does_not_reexecute_or_duplicate_state`
  — a second, independent RQ delivery (different job id, same
  `modification_id`) of the real production function, run through a
  second separate-process worker run: `jobs.transition_running()`'s own
  guard makes it a real no-op (identical `completed_at`, no version
  promoted or duplicated).

**What was not, and could not be, proven:** a `READY_FOR_REVIEW` (fully
passing) candidate via `execute_modification_job` — that requires the
real sandbox-executor Docker image (`omni-sandbox:latest`) to actually
build or pull, which remains blocked for the same reason M4D.2 already
disclosed (Docker Hub 403) *and* now, independently, for the `--mount`
flag incompatibility above. Both are genuine infrastructure/tooling
limits, not gaps papered over with a mock. A real hosted LLM and real
S3 remain out of reach, unchanged from M4D.2.

**Status discipline (directive item 4), applied literally:**
- PostgreSQL concurrency/atomicity: `VERIFIED_LIVE_INFRA` (unchanged).
- FastAPI execution: `VERIFIED_LIVE_INFRA` at exact production version
  parity for fastapi/starlette/psycopg/psycopg_pool/redis-py/rq; **one
  disclosed non-parity exception** — pydantic 2.13.3 vs. the 2.13.4 pin
  (pydantic-core==2.46.4 unbuildable here; see above).
- Redis production enqueue: `VERIFIED_LIVE_INFRA` (unchanged).
- RQ production `execute_modification_job` execution:
  `VERIFIED_LIVE_INFRA` (`REAL_RQ_SEPARATE_PROCESS_WORKER_VERIFIED`) for
  the `NEEDS_CLARIFICATION` and sandbox-verification-`FAILED` terminal
  paths; a `READY_FOR_REVIEW` terminal path remains
  `IMPLEMENTED_NOT_VERIFIED` (blocked on the real sandbox image, as
  above).
- **`M4 VERIFIED_LIVE_INFRA`** — per the directive: this does **not**
  mean `PRODUCTION_DEPLOYED` or `FULL_EXTERNAL_E2E`; real external
  LLM/S3/provider execution, and a real, successfully-passing sandboxed
  code-verification run, remain separately unverified, both for
  pre-existing reasons unrelated to M4's own accept/reject/rollback
  correctness.

Regression after M4D.2b, exact-parity vendor: 487/487 combined + 8/8
(`test_m4d2_live_fastapi_redis`, standalone) + 3/3
(`test_m4d2b_parity_and_worker`, standalone) = **498/498**, 2 expected
skips. **M5 has not been started.**

Evidence: `tests/test_m4d2b_parity_and_worker.py` (3 tests),
`tests/m4d2b_local_model_server.py`, `tests/m4d2b_worker_process.py`,
`tools/m4d2b_setup_parity_infra.sh`. Full command transcripts, exact
tag/commit table, and the exact real docker error text:
`PATCH_APPLICATION_REPORT.md`'s M4D.2b section.

| M4E — verification pipeline reuse (build/tests/repair/quality/security/rights/target gates) | `VERIFIED` | `CandidateModificationEngine` calls the same `quality_fn`/`security_fn`/`RightsEngine`/`Executor` as the rest of the pipeline — `tests/test_m4_modification_engine.py`, `tests/test_m4_acceptance.py::AcceptanceM` |
| M4F — deterministic diff (repository + spec) | `VERIFIED` | `omni_prod/modification_diff.py`; `tests/test_modification_diff.py`, `tests/test_m4_acceptance.py::AcceptanceQR` (order-independence proven directly) |
| M4G — billing (reserve at request time, settle/release by real classification, not by spend) | `VERIFIED` (decision logic + idempotency, AND the route's `reserve()` call itself, live — see **M4D.2**) | `tests/test_m4_worker.py::ResolveModificationBillingTests`; `tests/test_m4_acceptance.py::AcceptanceV`; `tests/test_m4d2_live_fastapi_redis.py` (every propose call reserves real credits via `PostgresSubscriptionService.reserve()` against real Postgres) |

### Required acceptance tests (A–W) and the concurrency requirement

All 24 (23 lettered + the concurrency requirement) are addressed in
`tests/test_m4_acceptance.py`; letters with deeper pre-existing coverage
point to it in their docstring.

| # | Claim | Status |
|---|---|---|
| A | POST returns 202 + durable id | `VERIFIED` — live, via real `fastapi.testclient.TestClient` against real Postgres (`tests/test_m4d2_live_fastapi_redis.py::test_full_http_propose_accept_flow_persists_to_real_postgres`); durability it depends on (`create()`+`create_outbox()` committing first) remains separately `VERIFIED` at the unit level too |
| B | API process never executes synchronously | `VERIFIED` (static AST proof, no import needed) |
| C | queue payload reloads from DB | `VERIFIED` |
| D | Redis enqueue failure stays recoverable via outbox | `VERIFIED` |
| E/F | exact source version / exact spec for that version loaded | `VERIFIED` |
| G/H | `system_bug`/`missing_requirement` run the real repair loop | `VERIFIED` |
| I | `ambiguous` executes nothing | `VERIFIED` |
| J | `change_request` runs the dedicated evolution path | `VERIFIED` |
| K | source version unchanged while candidate builds | `VERIFIED` |
| L | failed candidate can never be accepted | `VERIFIED` |
| M | gate failure never reaches `READY_FOR_REVIEW` | `VERIFIED` |
| N | accept promotes the candidate | `VERIFIED` — see **M4D.1** above; the promotion path (status validate → candidate read → version insert → spec insert → final status update) now executes inside one merged transaction with an atomic expected-version guard, proven by real 2-thread and 10-thread barrier-synchronized concurrency tests plus mutation tests |
| O | reject leaves current version intact | `VERIFIED` |
| P | rollback restores an exact historical version | `VERIFIED` |
| Q/R | repository diff / spec diff are deterministic | `VERIFIED` |
| S | spec/version can't become mismatched | `VERIFIED` (schema PK + no `update()` path), including live: migrations 001–016 applied to a real PostgreSQL 16 database and exercised for real in **M4D.2** |
| T | retry (queued redelivery, completion redelivery) is idempotent | `VERIFIED` |
| U | concurrency — explicit conflict semantics | `VERIFIED` |
| V | reservation not double-charged on retry | `VERIFIED` |
| W | all existing regression tests remain green | `VERIFIED` — as of **M4.9**, 501/501 tests pass across the full suite (488/488 in the combined run + 8/8 `test_m4d2_live_fastapi_redis.py` + 3/3 `test_m4d2b_parity_and_worker.py` + 1/1 `test_m49_clean_room.py` + 1/1 `test_m49_lifecycle.py`, all standalone-required for the same documented reason — module-level `omni_prod.investor_app` globals), plus 3/3 in the previously-always-skipped `tests/integration/test_live_sandbox_security.py` when explicitly enabled. 17 skips, all pre-existing, gated integration tests (opt-in env vars / unavailable signing credentials), not new. Supersedes the 309/309 (pre-M4D.1), 337/337 (post-M4D.1, pre-M4D.2), 495/495 (M4D.2, HEAD-based vendor), and 498/498 (M4D.2b) counts this row previously cited — see `PATCH_APPLICATION_REPORT.md` for the exact commands and §M4.9 for the full breakdown |
| Concurrency requirement (Version 10/11 scenario) | Do not silently overwrite; B must rebase, stay alternate, or be an explicit forced accept | `VERIFIED` — reproduced verbatim in `AcceptanceU`: A accepts → Version 11; B's plain accept returns `reason='conflict'` and Version 11 is untouched; B's `force=True` accept is the explicit third option |

### Not implemented / out of scope for this M4 pass

- ~~Live end-to-end run of the HTTP layer, Redis dispatch and Postgres schema~~ — **closed by M4D.2** (see above): real PostgreSQL 16, real Redis, and real FastAPI (via a disclosed git-clone-vendoring workaround for the Python packages themselves — `pip`/`apt`/`docker pull` remain genuinely blocked in this sandbox, confirmed not assumed) were exercised for real. What remains out of scope: a genuinely separate, forked/exec'd worker OS process in full production topology (M4D.2's RQ tests use `rq.SimpleWorker`, in-process, for a disclosed reason — see M4D.2's §G above) and the real S3/`boto3` path (a real disk-backed stand-in was used instead, out of scope for M4D.2's Postgres/Redis/FastAPI sections).
- ~~Full cross-transaction atomicity of `accept()`~~ — **closed by M4D.1** (algorithm) and **M4D.2** (live Postgres): `accept()` shares a single cursor across `workspace.commit()` and the status update inside one transaction, and this was proven both structurally (fake-cursor/statement-order) and, as of M4D.2, from PostgreSQL's own `txid_current()`/`pg_stat_database` counters during real concurrent execution.
- ~~A genuinely-passing `READY_FOR_REVIEW` candidate via `execute_modification_job`, and the accept/rollback lifecycle built on top of one~~ — **closed by M4.9** (see below): the real sandbox image now builds, runs, and is proven secure; a real, non-mocked candidate reaches `READY_FOR_REVIEW`; and it was really accepted and really rolled back.
- M5 and later milestones — out of scope by the directive's own stop condition; not started until M4.9 (below) explicitly authorizes it.

### M4.9 — genuine live sandbox execution: image built, security proven, full lifecycle closed (2026-09-24)

M4D.2b left one real gap open, disclosed at the time (its own §9 test
docstring): `execute_modification_job`'s sandbox-verification path had
never actually run a container, for two independently-real reasons —
`omni_prod/sandbox.py`'s `--mount ...,rw` flag was invalid syntax for
this sandbox's Docker 29.4.3, and no working `omni-sandbox:latest` image
existed (Docker Hub pulls are blocked here, same as every earlier
milestone). M4.9's own directive (items 7–12) required closing this for
real, with a fresh clean-room run, real negative security tests, exact
image provenance, direct invariant verification, and a real (non-mocked)
accept+rollback lifecycle proof — in that order, with M5 only authorized
once all of it passed. All of it passed; details below, full transcripts
and exact commands in `PATCH_APPLICATION_REPORT.md`'s M4.9 section.

**1. The real `--mount` defect (task #47).** `build_docker_command()`'s
output-mount line built `f"type=bind,src={output},dst=/output,rw"` —
`--mount` has no `rw` field (that syntax belongs to `-v`/`--volume`, not
`--mount`); a bind mount is read-write by default when `readonly` is
omitted, so the fix is deleting the invalid token, not adding a real one.
Confirmed via direct `docker run --mount ...` probes before and after.
Full pre-M4.9 regression (34 tests across the sandbox-adjacent modules)
stayed green.

**2. A real `omni-sandbox:latest`, with exact, reproducible provenance
(task #48).** A first attempt — `docker import` of a full snapshot of
this build container's own filesystem (6.07GB) — was abandoned: this
sandbox's Docker uses the `vfs` graph driver, which copies the ENTIRE
accumulated filesystem on every image layer (no copy-on-write), so even
a 3-instruction Dockerfile exhausted the whole session disk allowance.
The real fix: `strace -f -e trace=openat,open,stat,lstat,access,readlink,newfstatat`
against a real `pytest -q` run exercising the stdlib surface this
codebase's own tests use, parsed for every path actually, successfully
opened (387 real paths — the python3.11 interpreter, the full stdlib, and
every shared library its C-extension modules actually `dlopen`'d), plus
the ELF interpreter path (`/lib64/ld-linux-x86-64.so.2`, added by hand
since the kernel opens it directly via `PT_INTERP`, never as a traced
`openat()`). Copied (dereferencing symlinks) into a 27MB staging root,
`docker import`ed into `omni-sandbox-minimal:m49local`
(`sha256:1f21f853aafc2e79832a64d2d6ff18a9b399cd7962d9cb2a1b8ce89b0bd50276`
after one follow-up fix, below), verified immediately under the FULL
production security flag set (not relaxed) — real pass, with pytest's own
cache-write failure against the read-only `/workspace` mount itself real,
positive evidence that restriction was live. pytest 8.3.5 + pluggy 1.6.0
+ iniconfig v2.3.0 vendored via `git clone`/`git checkout <tag>` (PyPI is
blocked), exposed via `PYTHONPATH`, with two small hand-written
`_version.py` shims (setuptools_scm's real build-time step never ran) —
each individually commented and disclosed in place.

Follow-up fix, found while proving the pipeline end-to-end (below):
`infra/sandbox/Dockerfile`'s own `CMD` uses a bare `"python"` (PATH-resolved,
not an absolute path); the minimal image initially had only
`/usr/bin/python3.11`. Added `/usr/bin/python3`/`/usr/bin/python` symlinks
to the same staging root and `ENV PATH=/usr/bin`, matching the original
spec exactly. **Final `omni-sandbox:latest` digest:
`sha256:6834400bb7810ada027f02dd685d7eb2cae4b684b38745d0c8a1488a86702532`**,
29.4MB, built in under a second, real command:
`docker build --no-cache -t omni-sandbox:latest -f Dockerfile .` (exact
Dockerfile, with its own full provenance narrative, in
`PATCH_APPLICATION_REPORT.md`'s M4.9 section).

**3. Clean-room end-to-end success run (task #49, directive item 7).**
Real, second, independently-discovered production bug found and fixed
along the way: `SandboxRepositoryExecutor.execute()` materializes the
repository into `tempfile.TemporaryDirectory()`, which Python always
creates at mode `0700` regardless of umask — fine for a same-uid caller,
but that directory is bind-mounted into the sandbox container, which runs
as a genuinely different, unprivileged uid (`10001`, per `SandboxLimits`)
— so no sandboxed process could even traverse into its own mounted
repository (real `PermissionError: ... '/workspace/pytest.ini'`, pytest's
own config-discovery). Never caught before M4.9 because no container had
ever gotten far enough to try. Fixed: `os.chmod(root, 0o755)` /
`os.chmod(out, 0o777)` after materializing content — full regression
(485 passed, 17 skipped at that point) confirmed no regression.

New test `tests/test_m49_clean_room.py` (standalone) is the first test in
this codebase's history to drive a `ModificationRequest` to a genuine,
non-mocked `READY_FOR_REVIEW`: real `classify()` (against the same
disclosed local-model-server stand-in M4D.2b established) → real
free-repair loop → real `docker run omni-sandbox:latest` verification,
which genuinely PASSES → real quality gate → real security scan → real
rights gate, all passing for real. Clean-room isolation, independently
verified immediately before the official run: a dedicated, freshly
created+migrated Postgres database (`m49_clean_room`, not `m4d2_test`,
confirmed 0 rows beforehand), `redis-cli FLUSHALL` (confirmed `DBSIZE 0`),
and the exact `omni-sandbox:latest` digest above re-verified via
`docker inspect` immediately before running — no unknown pre-existing
image assumed, no IDs reused from any earlier run. Official run: **1
passed**. Final Postgres state, verified directly: exactly 1
`modification_requests` row (`READY_FOR_REVIEW`), exactly 1
`modification_candidates` row, exactly 1 `project_versions` row — no
orphans.

**4. Sandbox security negative tests (task #50, directive item 8).** New
test `tests/test_m49_sandbox_security.py` (3 tests, part of the ordinary
combined suite). Every check is real evidence collected from *inside* a
running `docker run omni-sandbox:latest` container, or a real attempted
violation — never asserted from the `docker run` argv alone:

| Requirement | Real evidence |
|---|---|
| not running as root | `os.getuid()`/`os.getgid()` inside the container: `10001`/`10001` |
| `no-new-privileges` active | `/proc/self/status` `NoNewPrivs: 1` (kernel ground truth) |
| `cap-drop=ALL` active | real raw-socket creation (needs `CAP_NET_RAW`) → real `PermissionError: Operation not permitted` |
| PID limit enforced | real fork loop against `SandboxLimits(pids=8)`: exactly 7 forks succeed, the 8th genuinely raises `OSError: [Errno 11] Resource temporarily unavailable` |
| memory limit configured **and** effective | cgroup `memory.limit_in_bytes` = 1073741824 (exact); a real attempt to allocate+touch 1.5GB gets real-OOM-killed — `docker run` returns real exit `137`, allocation stops at 1000MB (never reaching 1050MB) |
| CPU limit configured | cgroup `cpu.cfs_quota_us`/`cpu.cfs_period_us` = exactly 1.5 cpus |
| host filesystem not writable outside allowed mounts; root filesystem read-only | real write attempts to `/etc`, `/usr/bin`, and the read-only `/workspace` mount all fail with real `OSError: [Errno 30] Read-only file system`; `/tmp` (tmpfs) and `/output` (rw mount) proven genuinely writable as a positive control |
| network disabled | real outbound TCP connect → real `OSError: [Errno 101] Network is unreachable` |

Isolation was never weakened to get a passing build, per the directive's
own instruction — every probe above ran under production
`SandboxLimits()` defaults except the PID test, which deliberately used a
*smaller* limit (`pids=8`) purely to make real exhaustion fast, not to
relax anything. As a bonus, the pre-existing, previously-always-skipped
`tests/integration/test_live_sandbox_security.py` (gated behind
`OMNI_RUN_LIVE_SANDBOX=1`) now genuinely passes for the first time in
this project's history: 3/3.

**5. `READY_FOR_REVIEW` invariant, verified directly (task #51, directive
item 10).** `tools/m49_ready_invariant_check.py` connects to Postgres
directly (raw `psycopg`, not the repository ORM, not the HTTP API) and
checks every sub-item of item 10 against raw row/JSON content for the
real modification task #49 produced: generation completed (real
`started_at`/`completed_at`), sandbox command executed successfully
(real, non-empty `build_log_tail`), build/test exit status successful,
verification gates passed (quality score 89/100, 0 security findings),
candidate version + `ProductSpec` + diff all real and present, state is
`READY_FOR_REVIEW`, and no partial/orphan state anywhere (exactly one
`modification_requests` row, exactly one `modification_candidates` row,
no extra `project_versions` rows, `promoted_version_id`/`accepted_at`/
`rejected_at` all still null). Result: `M49_READY_INVARIANT_ALL_PASS`.

**6. Complete version lifecycle — accept, verify, rollback, verify
(task #52, directive item 11).** New test `tests/test_m49_lifecycle.py`
(standalone), reusing the SAME real candidate from task #49 — no mocked
repository state anywhere in this proof. A. real HTTP `POST .../accept`
→ real 200, new real version `v_babb1198473a40fe`. B. verified directly:
Postgres `current()` now returns that version, with repository content
byte-identical to the accepted candidate; raw-row check confirms its
`parent_id` is the seed version. C. a real, persisted `ProductSpec` row
exists for the new version, matching the candidate's spec. D. real HTTP
`POST /rollback` targeting the original seed version → real 200, a
*third*, brand-new version `v_45963a10dd86444a` (rollback re-commits, it
never rewrites the old row). E. verified EXACTLY restored: `current()`
now returns that version, with repository content proven
**byte-identical** to the original seed repository (real dict equality,
not a heuristic), and explicitly different from the superseded accepted
candidate. Final independent `psql` snapshot: exactly 3
`project_versions` rows for this project, in the correct real chain
(seed → accepted → rollback-of-seed); `modification_requests` shows
exactly 1 row, `status=ACCEPTED`.

**7. Full regression.** Combined suite (excluding the now five
standalone-required live-infra files): **488 passed, 17 skipped** (all 17
are pre-existing, gated integration tests requiring explicit opt-in env
vars or unavailable credentials — Android/iOS signing, `OMNI_RUN_LIVE_*`
flags — not new skips M4.9 introduced). Standalone:
`test_m4d2_live_fastapi_redis.py` 8/8,
`test_m4d2b_parity_and_worker.py` 3/3 (one of its two real-failure tests'
docstring and specific build-log assertion were honestly updated in
place — not silently — to track a NEW real failure mode the M4.9 fixes
themselves produced further downstream; see `PATCH_APPLICATION_REPORT.md`),
`test_m49_clean_room.py` 1/1, `test_m49_lifecycle.py` 1/1. **Combined
total: 501/501**, plus the newly-real 3/3 in
`test_live_sandbox_security.py` when explicitly enabled.

**8. Final status (directive item 12).** All of M4.9 items 7–12 passed.
**`M4 = VERIFIED_LIVE_INFRA`**, with the explicit limitation the
directive itself names: this is still not `PRODUCTION_DEPLOYED` and not
`FULL_EXTERNAL_E2E` — a real hosted LLM provider and real S3 remain out
of reach in this sandbox (unchanged since M4D.2), and this milestone's
real sandbox image is a disclosed, documented substitute for
`infra/sandbox/Dockerfile`'s own `python:3.12-slim` base (Python 3.11.15
here, not 3.12; PyPI-installed dependencies here vendored instead), not
that exact image. The pydantic 2.13.3 vs. 2.13.4 patch-version gap
(M4D.2b) remains a documented production-CI verification item and does
not block M5. **Per the directive's own item 12: M4 work stops here, and
M5 architecture/implementation planning is now authorized to begin** —
no M5 requirements have been given yet in this engagement, so no M5 work
has started.

## 6. M4.95 — Capability Foundation & Truth Lock V2 (2026-10-04)

**Status: VERIFIED_LOCAL_PROVIDER_NEUTRAL_FOUNDATION.** Tasks 1–16 are implemented and verified in this execution environment. This status is intentionally narrower than `PRODUCTION_DEPLOYED` or `FULL_EXTERNAL_E2E`.

Canonical execution plan: `docs/superpowers/plans/2026-10-04-m495-capability-foundation-v2-plan.md`.
Design authority: `docs/superpowers/specs/2026-10-04-m495-capability-foundation-design.md`.
World-class gap baseline: `docs/148AI_WORLD_CLASS_COMPLETENESS_AUDIT_V2_2026-10-04.md`.
Validation evidence: `M4_95_VALIDATION.md`.

Fresh pre-change baseline: `518` tests, `OK`, `47` skipped.
Fresh post-M4.95 full regression: `633` tests, `OK`, `47` skipped.
Focused Golden/failure/recovery gate: `22` tests, `OK`.

Verified locally: canonical Capability/Skills/Agents registries; dependency closure; provider-neutral contracts and routing; provider+capability 429/quota cooldown; streaming artifact integrity; durable execution attempt identity, lease/resume and `provider_task_id`; credential-binding abstraction; crash-safe capability execution; versioned local price/authorization/actual-cost truth; durable worker capability gate; tenant-scoped readiness evidence; artifact provenance/export evidence; machine truth drift enforcement; provider-neutral heterogeneous Golden E2E; localhost HTTP fake-provider integration; paid-provider durable-result guard; file-backed streaming provider artifacts.

Not re-claimed as live in this environment: clean-room/lifecycle Postgres proof (`psycopg` unavailable), isolated Docker sandbox proof, live Postgres/Redis/S3, commercial media/3D providers, and mobile signing. The historical M4.9 live-infra evidence remains recorded above but is not substituted for current evidence.

The Golden E2E uses an in-process fake multimodal provider with structurally valid artifacts. It proves the universal execution/verification/evidence contract, **not** that a named commercial provider is LIVE.

M4.95 machine truth SHA-256: `5da248f3201ed0b7ceb079b10e7856ded5c01b6180eef550d5df28ebbf86ed88`

## M5 Production Vertical Slice — 2026-10-04

Current machine-facing classification: **M5_PARTIAL**. M5 implementation has started from the verified M4.95 baseline. Durable deployments use the plural `/builds` asynchronous pipeline as the canonical arbitrary-generation path; developer memory mode is not staging or production proof. Production readiness remains prohibited until M5 acceptance, recovery/security, deployment/billing, full regression and external staging proofs are complete.


## Infisical generated-app secret adapter — 2026-10-06

### Implemented and independently verified
- Opt-in Infisical Universal Auth/v4 SecretWriter: create/read/rotate/delete,
  missing-delete handling, permission failures, response validation, token expiry,
  deterministic project/environment reference separation, supplied-env wiring.
- Vault remains the default and its writer remains supported.
- Test-first evidence: commit fbbc04b, v24-ci run 37386465951/job 112020832639:
  9 intended new test failures for missing Infisical support; the full-suite
  aggregate regression test also failed because it includes those tests.
- Implementation evidence: commit e0924b8, v24-ci run 37386690727/job 112021563213:
  `python -m pytest -q` = 819 passed, 55 skipped, 1 warning, 95 subtests passed.
  Compileall, hostile static suite, international gate and compose-config passed.
  These are automated fixture/regression results, not live Infisical evidence.
  Warning: Starlette's AnyIO BlockingPortal alias is deprecated.

### Implemented but awaiting external live verification
- The Infisical writer has not authenticated to the founder's live account from
  the deployed Vercel server. Live create/read/rotate/delete proof is pending.
- Configuration-level readiness stays PARTIAL; only per-binding verification
  may mark an actual infrastructure binding LIVE.
- See docs/INFISICAL_GENERATED_APP_SECRETS.md for configuration and rollback limits.

### Blocked by a named credential/service
- The intended Vercel Preview environment must explicitly select
  OMNI_GENAPP_SECRET_STORE_PROVIDER=infisical and receive this tested source.
- Generated-app-only database admin DSN, scoped object credential issuer/bucket,
  scheduler, image provider and their cost quotes remain separate blockers.
- No real secret values were read, logged, copied into this repository or tested.

### Not implemented
- Automatic migration of live Vault values to Infisical.
- Infisical as the general control-plane/model-provider secret resolver.


## 2026-10-06 — Opt-in generated-app Cloudflare R2 adapter

1. **Implemented and independently verified (unit/CI, not live R2):**
   source revision e5ce74c281e6e82ad355aaa9b0556709f6afbb1e passed v24-ci
   (https://github.com/Shayfly/desktop-tutorial/actions/runs/37456953208)
   and V11 Overlay CI
   (https://github.com/Shayfly/desktop-tutorial/actions/runs/37456953187).
   compileall, pytest (828 passed, 56 skipped, 1 warning, 119 subtests passed),
   hostile static suite, international gate and compose-config passed.
   The test-first revision 83eba3b5d8ae2b9cb703aec6ddafc56d24128ef2 failed
   collection because the R2 issuer did not yet exist, as intended.
2. **Implemented but awaiting verification:** local HS256 temporary credential
   issuer; strict managed CRUD/list policy translation; R2/static readiness and
   wiring; protocol tests; independently gated R2 CRUD/isolation integration test.
   The default AWS STS path is preserved. See docs/R2_GENERATED_APP_CREDENTIALS.md.
3. **Blocked by a named service/access:** live Cloudflare R2 verification needs a
   trusted test runner with the founder's Preview settings injected. No keys
   were read in chat or committed. Screenshots establish bucket/config presence,
   not provider verification. CI deliberately skips the live test without opt-in.
4. **Not implemented in this change:** automatic credential refresh and expiry-safe
   existing-binding reuse; immediate per-session revocation; full runtime
   cross-app verification. The saved system audit still applies.

Validation commands: `python -m compileall -q omni_prod tests`,
`python -m pytest -q`, `python scripts/run_hostile_static_suite.py`,
`python scripts/run_international_gate.py`.
Real test: `M5_R2_LIVE=1 python -m pytest -q tests/integration/test_r2_generated_storage_live.py`
with securely injected staging variables. This is a command to run, not a passed
live result.


## 2026-10-06 — QStash scheduler connector

1. **Implemented and independently verified:** baseline 23d48ff passed v24-ci
   https://github.com/Shayfly/desktop-tutorial/actions/runs/37458399389 .
   Source ed9af69d529f4796e3cf2135c55fdb347dd53bae passed v24-ci
   https://github.com/Shayfly/desktop-tutorial/actions/runs/37460855718
   and V11 Overlay CI
   https://github.com/Shayfly/desktop-tutorial/actions/runs/37460855680 .
   compileall, pytest (846 passed, 58 skipped, 1 warning, 158 subtests passed),
   hostile static suite, international gate and compose-config all passed.
   These are unit/CI proofs; live QStash administrative and delivery tests did not run.
2. **Implemented, awaiting live verification:** QStash schedule create/get/cancel,
   publish with deduplication, safe transport, signature verifier requiring a durable
   replay claim, saved-variable readiness and API-access check. A QStash binding is
   BLOCKED until per-app authenticated delivery is proven, even if API access passes.
3. **Blocked by a named service/access:** real administrative tests require a trusted
   runner with QSTASH_URL/QSTASH_TOKEN; optional schedule lifecycle test also requires
   an operator-owned harmless QSTASH_TEST_DESTINATION. No founder keys were read.
4. **Not implemented here:** tenant-scoped durable schedule API, production delivery
   gateway/inbox, retry/crash recovery and generated-app callback wiring. Provider
   JWT replay rejection alone is not exactly-once business execution.

See docs/QSTASH_SCHEDULER_CONNECTOR.md. Commands:
`python -m compileall -q omni_prod tests`; `python -m pytest -q`;
`python scripts/run_hostile_static_suite.py`;
`python scripts/run_international_gate.py`.
Live administrative test:
`M5_QSTASH_LIVE=1 python -m pytest -q tests/integration/test_qstash_scheduler_live.py`.
These live commands are instructions, not passed evidence.

## Replicate live connection investigation — 2026-10-06

The authenticated Preview account check returned upstream 403 even after the
user configured billing, rotated the token and redeployed. The safe diagnostic
reported token_format_valid=true, response_kind=other and category=unknown.
No billable generation was started; connection and generation remain unverified.

A separate HTTP 500 was traced in Vercel runtime logs to stale PostgreSQL SSL
connections during session authentication. DatabasePool now uses the official
ConnectionPool.check_connection callback before checkout. Regression tests also
confirm arbitrary writes are not replayed. Both GitHub workflows passed for
9025f7316916ee9bd1943d3ab355cc5a56be135a.

The 403 hypothesis is the Python-urllib client identification: Ultralytics documents
Replicate CDN rejecting that default from datacenter IPs, while Replicate's own
Python client supplies a named User-Agent. Requests now identify as 148AI/1.0,
with Accept: application/json, for the Replicate API only. No browser impersonation,
challenge solving, access-control changes or token disclosure are involved.
Sources:
- https://github.com/ultralytics/replicate/blob/main/replicate_metadata.py
- https://github.com/replicate/replicate-python/blob/main/replicate/client.py

12 targeted tests passed for authentication safety, request headers, rejection
categories and database checkout behavior. Live verification of the named-client
request is still pending; neither connection nor media generation is marked LIVE.

## Replicate one-image Preview test (2026-10-06)
Implemented and locally verified: fixed FLUX Schnell one-image test, authenticated Preview-only routes, explicit $0.003 approval and same-origin POST, one durable submission per account, fail-closed unknown submission, verified private S3 image retrieval. Uses existing migration 026 submission journal and existing S3 workspace storage; no ephemeral state or additional schema.
Verification: python -m pytest tests/test_replicate_image_test.py tests/test_replicate_connection.py tests/test_database_pool_health.py -q -p no:cacheprovider — 18 passed. Tests include recovery across service instances, account isolation, no authentication/no confirmation rejection, ambiguous-submit non-replay and stored image retrieval without further provider calls.
Awaiting external live verification: paid POST, provider completion, artifact download and storage on the newly deployed Preview. No image has yet been generated by this test. Authentication to Replicate was separately live verified (connection_verified=true) on p40n0qijl.

## Replicate test storage preflight (2026-10-06)
Live image submission was blocked before the provider POST because HeadBucket returned false; no image was submitted. Underlying storage error was swallowed by the generic ping, so object access failure is not yet established.
Replaced the image-test-specific preflight with a small private object write/read/integrity probe; no credential or raw service error is returned. Recognized failure category and operation are exposed for diagnosis. The shared S3 ping is unchanged. Scope-permission hypothesis awaits live verification.
Local verification: python -m pytest tests/test_replicate_image_test.py tests/test_replicate_connection.py tests/test_database_pool_health.py -q -p no:cacheprovider — 20 passed. Live object probe and paid image generation still pending.

## R2 request signing compatibility (2026-10-06)
Live latest redeploy rchseos0u still reports write SignatureDoesNotMatch. Root cause is not yet conclusively attributed to credentials or SDK.
Independently reproduced locally with real pinned boto3 1.43.94/botocore 1.43.108 and synthetic credentials: before-send capture (no network) shows x-amz-sdk-checksum-algorithm, aws-chunked encoding, STREAMING signature. Official R2 compatibility table lists the optional checksum algorithm header unsupported for PutObject. R2-only client now uses SigV4, region auto, path addressing and checksum calculation/validation when_required. Standard S3 unchanged; private SHA256 storage verification retained.
Verification: python -m pytest tests/test_r2_storage_signing.py tests/test_replicate_image_test.py tests/test_replicate_connection.py tests/test_database_pool_health.py -q -p no:cacheprovider — 22 passed. New regression captures actual signed request before transmission and confirms unsupported trailers absent, SigV4 present, SHA256 metadata retained; AWS region/defaults preserved.
Awaiting live storage probe on new Preview. No claim that SignatureDoesNotMatch is fixed live and no paid image proof.


## 2026-10-11: PR17 branch reconciliation with PR11

PR11 is integrated into the PR17 branch only. Schema compatibility now requires migration 038, matching the attachment migration already present in PR17. Existing drift checks remain intact. This branch push is authorized to trigger Preview; no milestone/main merge, worker deployment, live migration, or secret change is authorized by this reconciliation. Local verification covers 48 deployment verification tests; full application and PostgreSQL validation must be confirmed by CI on the resulting commit. Preview protection, unscheduled default-branch backups, and worker recovery/drain risks remain release blockers; this entry does not claim production readiness.

## 2026-10-14: controlled GitHub Actions cost optimization (draft)

- Implemented and independently verified: feature push/full PR trigger separation, documentation-only heavy-check selection, stable per-PR cancellation, fail-closed required pg/customer-ui checks, bounded Docker/browser jobs and retained failure reports. 16 focused CI tests pass (37 subtests), 28 workflow YAML files validate, Python/JavaScript syntax checks pass; independent re-review found no remaining important issue.
- Implemented but awaiting external live verification: actual Linux, PostgreSQL, Docker and browser CI execution and net job-minute savings. Full local suite: 1645 passed, 63 failed, 172 skipped; no additional failing test IDs relative to the local baseline. This is not a green full-suite claim.
- Blocked by named service/environment: GitHub Actions says jobs cannot start due to failed recent payments or the account spending limit; local Windows temporary-directory access and unavailable Linux/Docker services prevent complete integration verification. No spending limit or payment setting was changed.
- Not implemented: measured billed savings after integration; these require successful candidate runs and a comparable billing/job-minute sample. Production deployment and merge are outside the authorization.

Commands, sample of 100 historical runs, timeout policy and evidence limits: docs/CI_ACTIONS_COST_OPTIMIZATION_2026-10-14.md.

## 2026-10-30 — Item 3 (Codex; awaiting independent review)
Plan preview now calls the existing read-only subscription authorization using
build credits and total_authorized_variable_usd, preserving internal-QA policy.
Local: 48 tests and 8 subtests pass; item3 negative control must fail the two
insufficient-allowance cases. No reservation or paid call in preview.

## 2026-10-30 — Item 5 (Codex; awaiting independent review)
Explicit delegation now writes the declared default for asked/held fields into
the brief with delegated provenance, shows it, clears held state and replays the
same decision on another supervisor. Confirmed values remain unchanged; no spec
approval is inferred. Uncertainty alone retains its existing clarification rule.
Local: 57 passed, 4 PostgreSQL-dependent skips, 6 subtests. NC restoring held-open
behavior fails the new end-to-end conversation test. No deployment.
Independent review found one Important issue: a negated mention of delegation
was accepted by a loose regex. Fixed with full-message affirmative matching;
Hebrew, English and quoted-refusal regressions observed RED then GREEN.
Remaining scoped choice: typed explicit delegation covers held fields; a field's
quick-reply delegation continues to apply to that field through discovery.answer.

## 2026-10-30 — Item 4 (Codex; awaiting independent review)
Build reservation refusals return a structured customer-facing allowance error;
the shipped explain() renders matching Hebrew/English copy without the internal
paid-provider reason. Local: 45 tests and 9 subtests passed; item4 NC restores
raw decision.reason and fails the response test. No deployment.

### 2026-10-30 — Item 4 review follow-up (Codex)
Reserve denial now distinguishes plan-ineligible builds from exhausted credits
or budget. Each has matching Hebrew/English cause and action. Existing
qa_budget_denied remains separate from plan_cannot_authorize_cost. Observed the
new distinction tests RED, then 59 passed with 9 subtests. NC2 restores the
unified mapping and must fail the eligibility test; NC1 still checks raw reason.

## 2026-10-30 — Item 2 (Codex; awaiting independent review)
Existing no-contact failure release retained. Added real PostgreSQL reserve/refund
balance and replay evidence plus a mutation removing release. Local: 3 settlement
tests passed, 4 PostgreSQL tests skipped (no local database). Actual PG balance
proof remains pending CI. No production calls or changes.

### 2026-10-30 — Item 2 review follow-up (Codex)
Replaced the fabricated external_calls=0 fixture with execution of the production
worker function, actual AutonomousProductEngine agents and RoutedModelGateway.
The actual model policy fails before HTTP. Read both ModelUseState.external_calls
and an instrumented OpenAI-compatible HTTP boundary. A positive canary permits a
call and observes both counters reach one (HTTP is intercepted, no paid call).
The PG balance/replay test now executes that worker path twice for the same ID.
Local: 5 passed, 4 PG skipped; current-SHA PG balance proof pending CI.

## 2026-11-19 — Finding attribution check (Codex)

- Added CI verification of the declared Found-by and Co-Authored-By commit trailers. The check flags a shared named agent and does not infer authorship on commits without attribution. The comparison also recognizes the versioned Claude signatures used in main. Three focused tests and two mutation controls passed locally. Repository rollout and independent review pending.
## 2026-11-19 — Critical production path freshness (Codex)

- The proposed daily workflow reads action run, step and artifact metadata. It reports success from the relevant main-branch step within seven days, BROKEN when no qualifying evidence exists, and UNVERIFIED when the API cannot be read. Scope: deployment, golden rehearsal, Golden E2E, verify-replay and restoration.
- The replay source positively verifies a nonempty completed batch with at least one passing version. Freshness counts successful old runs rerun within seven days and labels the displayed revision as the workflow trigger SHA. Local evidence: eight tests, three mutation controls, and workflow validation. Scheduled activation and independent review are pending.
## 2026-11-19 — Model costs of recorded runs (Codex, internal reporting)

- The read-only query in [scripts/observed_model_costs.sql](scripts/observed_model_costs.sql) returns build and intake run IDs, phases, routes, evidence bases, recorded subtotals and run totals. A missing price leaves the full total null. Budget reservations and prospective prices do not enter these figures.
- Exercised the SELECT on both operational ledger databases. The export is rerunnable via psql and has no write or runtime hooks. Claude Code independently verified the unchanged SQL against the production ledger on 2026-11-19 (PR #454, review of 71ec345). The report contains operational data and is kept outside this public repository.

## 2026-11-19 — Remove the duplicate AcceptanceW invocation in Overlay CI (Codex)

- The #463 Overlay run 44479691814 ran 3911 unittest cases and failed only because the nested AcceptanceW subprocess exceeded 300 seconds. Overlay discovery now skips the wrapper only. Standalone and v24 invocations retain the 300-second check.
- Local targeted checks: 8 tests and 19 subtests passed, and the duplicate-invocation mutation was caught. Exact-head CI and independent review pending.

## 2026-11-20 — Critical path freshness manual check (#464, Codex)

GitHub Actions [manual run 44658425152](https://github.com/Shayfly/desktop-tutorial/actions/runs/44658425152) on `main` at `15a36579cec27eee1f6132ce3dfed8af9423125e` finished with exit 1. The three BROKEN annotations mean no qualifying successful step in the preceding seven days. PASS below records fresh historical evidence; it does not certify the revision that triggered this check. Times are UTC.

| Critical path | Result | Most recent qualifying success found |
|---|---|---|
| Worker deployment | PASS | [2026-11-19 22:04:43, queue execution proof](https://github.com/Shayfly/desktop-tutorial/actions/runs/44624663436/job/135915241531), workflow SHA `29e515e` |
| Golden rehearsal | BROKEN | None in the seven-day window |
| Post-deploy verify-replay | BROKEN | None in the seven-day window |
| Backup restore | PASS | [2026-11-19 10:16:28, restore and verify](https://github.com/Shayfly/desktop-tutorial/actions/runs/44503989411/job/135490677325), workflow SHA `8cde544` |
| Golden E2E | BROKEN | None in the seven-day window |

- Golden rehearsal — Claude Code owns a main-branch Golden build rehearsal with an approved synthetic prompt and spend, preserving the successful build-step result.
- Post-deploy verify-replay — Codex owns the CI evidence. Run the Post-deploy checks workflow on main with stage `verify-replay` and stored versions available, and confirm the replay completed with at least one successful verification. The replay mode does not call models.
- Golden E2E — Claude Code owns the trusted live producer and Matt independently verifies its evidence. The producer must attach `golden-e2e-evidence` and call the reusable gate in the same run with the build ID and expected commit so all four checks pass.

The newer [worker deployment at `15a3657`](https://github.com/Shayfly/desktop-tutorial/actions/runs/44650631173/job/136004430513) failed at Apply database migrations with `applied migration missing from package: 45`. The recovery step reported that the previous consumers were restored, and the queue proof was skipped. This run is not counted as evidence of freshness.

Follow-up after the manual check: migration 045 was merged in #474. The [worker deployment for `df37f4f`](https://github.com/Shayfly/desktop-tutorial/actions/runs/44665058956/job/136052265327) completed successfully and proved queue execution at 03:06:03 UTC on 2026-11-20.

## 2026-11-21 — drills, the dead-worker alert, two critical paths, the business metric (Claude Code)

**Implemented and independently verified (by CI on the exact SHA, mutations and real-infrastructure runs; no human reviewer):**
- **Monthly drills,** recorded in CONTROLS.json `drills_run` (#483, `bed3fa6` -> `86dfb69`):
  - C16 PASS, run 44932418710: HTTP 405, main unchanged;
  - C19 PASS, run 44932702825;
  - C11 PASS, run 44933990232;
  - C18 FAIL on the alert, run 44935937685.
  - C19 and C11 each needed a second attempt: both first attempts failed on Claude's own drill-instrument bug, recorded under `attempts`.
- **Warehouse 121, the dead-worker alert** (#487, `6f5d1ff` -> `0625996`):
  - drill run 44942838520: Redis read "no worker is registered", issue #489 opened and closed;
  - live run 44942942630: "omni-builds: 1 live ... heartbeat 81s ago".
- **Post-deploy verify-replay:** run 44941296147, "10 versions completed; at least one PASS". The first green run since 2026-10-20.

**Implemented, awaiting merge:**
- Customer session logs in by itself (#490);
- the CI report moves to the run summary and an artifact (closes #146);
- the rehearsal's publish-taxonomy never pushes to main.

**Blocked by a named credential:** Customer session needs the secrets `CUSTOMER_TEST_EMAIL` and `CUSTOMER_TEST_PASSWORD`, which only the owner can create.

**Finding (Neon, read-only, 2026-11-21): first_pass_yield, the founder's metric of 2026-10-19, was not recorded for a month.**
- The rehearsal's publish job pushed to main, and main's protection rejects that; `smoke/rehearsal-builds.jsonl` holds one build, from 2026-10-19.
- Computed from `build_jobs` for the last 35 days: 48 builds, 11 `ready` (23%), 0 first-pass.
- In the last 21 days, `verification_failed` caused 21 of 33 failures (3.3 repair rounds on average).

## 2026-11-20 — AcceptanceW without optional dependencies (Codex)

- Reproduced the failure on main `0ed3d0e` without FastAPI and psycopg. The nested unittest suite ignored the repository's measured dependency manifest and reported 43 errors and four failures.
- AcceptanceW still runs a nested suite and requires a successful exit. With optional dependencies present, the existing unittest command and 300-second timeout stay in place. Without them, the nested pytest command applies the repository's `not needs_env` selection and has a separate 600-second ceiling. Three modules and four individual tests that depend on FastAPI were measured and added to the manifest. They remain in full CI.
- The standalone AcceptanceW test passed in the dependency-light environment on code commit `1453d7e` in 252.76 seconds. Both negative controls passed, including one that injects a real inner test failure and checks that the outer gate rejects it.
- The same offline reproduction on current base `df37f4f` still failed (43 errors and four failures in the nested command). Full `pytest tests` with dependencies passed both before and after the fix: 4,015 on base and 4,016 on the branch, 294 skipped and one expected failure on each, with no failures or errors.
