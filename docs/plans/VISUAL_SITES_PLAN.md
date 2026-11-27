# Visual level of the content sites: diagnosis and design

Author: Claude Code (chief architect), 2026-11-27. No production code was written, nothing was committed, pushed,
merged or deployed, and no paid service was called.

Order executed: the owner's message of 2026-11-27 ("אני לא רוצה שנבנה אתרים שנראים גנרים, אני רוצה רמה יותר גבוהה עם
ויזואלים"), under inbox/002 (plan v3 and the decisions of 2026-11-25/26; rule 10: the customers' sites first).

Code read: `origin/main` at `a034c58`, exported to
`/tmp/claude-0/-home-user-desktop-tutorial/ef722132-a1de-581a-aa3a-c4e5105bcddd/scratchpad/vd_main_a034c58`.
`origin/main` moved to `e29015c` while I worked; of the files this document cites, only
`omni_prod/providers/image_provider.py` (an unpriced provider still runs) and `WAREHOUSE.md` (an update to item 136)
changed (`git diff --stat a034c58 origin/main -- <the cited paths>`). Line numbers below are those of `a034c58`.

---

## 1. Evidence

### 1.1 The section library, rendered with the real code

Script: `.../scratchpad/vd_work/render_verticals.py` (content: `.../scratchpad/vd_work/verticals.py`).
Each page takes the route's own steps (`omni_prod/site_content/__init__.py`, `decide()`): category ->
`vertical_palettes.palette_for` -> the palette's entry in `section_library/directions.json` -> `typography.pair_for` ->
`g_apple.contract.build(..., fonts=pair)` -> `section_library.page`. The lawyer page goes through the whole real path:
the production prompt of `bld_b0eb47a5` (fixture `tests/fixtures/site_content_bld_b0eb47a5.json`, sha256 asserted),
its scripted content document, `site_content.render.render`. The other seven use synthetic content I wrote in the
shape `render.to_library` emits (fictional businesses). Fonts were loaded live from Google Fonts. Viewports are
`visual_qa.VIEWPORTS` (1440x900 and 390x844 touch).

Screenshots (all under `/tmp/claude-0/-home-user-desktop-tutorial/ef722132-a1de-581a-aa3a-c4e5105bcddd/scratchpad/vd_shots/`):

| File | What |
|---|---|
| `sheet_library_desktop_first.png` | first desktop screen of 8 verticals |
| `sheet_library_mobile_first.png` | first phone screen of the same 8 |
| `sheet_library_desktop_full.png`, `sheet_library_mobile_full.png` | whole pages, side by side |
| `lib_<vertical>_<desktop|mobile>_<first|full>.png` | 32 single screenshots |
| `sheet_library_photo_desktop_first.png`, `sheet_library_photo_mobile_first.png`, `libphoto_*` | 4 verticals with a hero photo and a story photo (a labelled placeholder grid drawn locally; no image was generated) |
| `overlay_check_lawyer_panel_green_photo.png`, `overlay_check_after_zindex_probe.png` | the hero-photo overlay bug and the probe of its cause (section 2.2) |
| `library_measurements.json`, `library_photo_measurements.json` | the measurements below |
| `html/<vertical>.html` | the rendered pages |

Measured on the 8 pages (desktop; `library_measurements.json`):

| Vertical | Palette / direction | Font pair | Pictures | Full-bleed sections | Shadows | Animated elements | Page height, phone |
|---|---|---|---|---|---|---|---|
| lawyers (real fixture) | counsel / formal | he-frank-heebo | 0 | 0 | 0 | 4 | 5,544 px |
| dental | clinic / formal | he-miriam-plex | 0 | 0 | 0 | 4 | 5,136 px |
| cafes | hearth / warm | he-secular-heebo | 0 | 0 | 0 | 4 | 4,644 px |
| cabins | retreat / warm | he-fredoka-heebo | 0 | 0 | 0 | 4 | 4,397 px |
| plumbing | trade / bold | he-karantina-rubik | 0 | 0 | 0 | 4 | 5,145 px |
| gyms | energy / bold | he-suez-notosans | 0 | 0 | 0 | 4 | 5,201 px |
| hair_salons | blush / elegant | he-david-assistant | 0 | 0 | 0 | 4 | 4,446 px |
| photographers | studio / elegant | he-frank-heebo | 0 | 0 | 0 | 4 | 5,216 px |

- Every page: 4 text colours, 4 to 6 large background colours, sections of 1 or 2 columns only, the same section
  order (hero, services, about, [process], cta, faq, contact).
- Markup skeleton (tags and classes, no words) compared pairwise with `difflib`: similarity 0.758 to 0.993, mean 0.899
  over 28 pairs (gyms vs plumbing 0.993; cafes vs hair salon 0.972).
- With a hero photo (`library_photo_measurements.json`): the photo covers 15.7% of the first desktop screen in the
  `split` hero and 10.7% in the `banner` hero and in the elegant direction, where a 16:9 photo is cropped to a strip of
  about 1152x120 px with the opening hours printed on it. On a phone it covers 29 to 30%, again with the facts printed
  on it.

### 1.2 The five most recent READY builds in production

Neon project `148ai-db-v2` (`aged-tree-68103298`), default branch, read-only: every call was
`run_sql_transaction` whose first statement is `SET TRANSACTION READ ONLY`. Fetched: `build_jobs.id`, `status`,
`created_at`, and from `evidence_json` the keys `site_route`, `asset_plan`, `asset_capabilities`, `g_apple`,
`visual_qa`, `capabilities` (image requirements, usage, image_match), `provider_spend_usd` and token counts per model;
and `project_previews.id, status, preview_url, expires_at`. No prompt, no account and no page text was fetched. The
reviewers' findings quote business names, phones and addresses; they are left out here.

`SELECT status, phase, count(*) FROM build_jobs GROUP BY 1,2` -> ready 16, failed 42, cancelled 4.

| Build | Date | Route (reason) | Pictures on the page | Design score | Text elements (desktop) | Provider spend |
|---|---|---|---|---|---|---|
| `bld_6a278b91` | 11-26 | legacy (`image_place_products`) | 2: a generated "logo" and the customer's own product photo | 57 | 35 | $0.637 |
| `bld_a02d9a6e` | 11-25 | **section_library** (counsel / formal / he-david-assistant) | 0 | 70 | 89 | $0.108 |
| `bld_dd5d5f0b` | 11-25 | legacy (`name_not_declared`) | 0 | 77 | 38 | $0.949 |
| `bld_c35b8332` | 11-23 | legacy (`no_design_contract`) | 0 | 76 | 40 | $0.526 |
| `bld_1d477f37` | 11-22 | legacy (`phone_not_one`) | 1: a generated hero photo that matches its subject | 87 | 36 | $0.705 |

What the evidence says about each:

- `bld_a02d9a6e`, the only one that reached the designed library. The design critic: "The large navy panel occupies
  nearly half the hero but offers mostly empty decoration and two contact details ... without showing what the store
  sells". Its default hero picture was generated and paid for, then dropped: `capabilities.image_match` =
  `DROPPED, "no subject recorded: the customer did not ask for this picture"`, with a Replicate usage row of $0.003
  beside it. The reviewers describe a smoking-products shop; its `site_route` says category `lawyers`, domain `lawyer`
  (the bug the route-honesty change of 2026-11-25 fixed: a business with no signal was taken for a law firm). The
  palette such a business gets is unchanged today: the neutral one is the law firm's navy with a serif heading
  (`vertical_palettes.py:74`, `NO_SIGNAL = 'lawyers'`).
  `site_route.skipped` includes `"gallery: gallery images are not on this route yet"`.
- `bld_dd5d5f0b` and `bld_c35b8332`: the same `DROPPED` picture with the same $0.003 row. The critic on the first:
  "The large bullseye-like graphic reads as a placeholder"; on the second: "The large concentric-circle graphic ...
  makes the hero feel more like a placeholder".
- `bld_6a278b91`: the customer uploaded a photo of the product and placed it in the products section. That alone sent
  the build to the legacy path (`site_content/__init__.py:192`). The critic: "התמונות אינן מציגות דלתות, הפתיח בדסקטופ
  חצי ריק". Score 57, and the build is READY.
- `bld_1d477f37`: the only page with a relevant photo, and the highest score of the five (87): "A polished, coherent
  salon page with a strong photograph". One build; an observation, not a proof.

Route share since the route exists (builds from 2026-11-21 that carry a `site_route.route`): 8 legacy (4 READY,
4 failed) and 2 section_library (one READY, one failed).

Previews: **not screenshotted**. All 13 `project_previews` rows of these versions are `EXPIRED` (a preview lived one
hour), and `curl` to the five hosts returns `CONNECT tunnel failed, response 403` from this session's egress proxy.
The builds' own screenshots exist as object-storage keys (`visual_qa.viewports.*.screenshot_key`,
`build-visual/<build>/...jpg`); this session has no read access to that storage, and I did not look for one. The
stored page files were not fetched: they carry customers' details, which the task excluded.

### 1.3 Cost facts (measured, from the same rows)

- A generated picture: $0.003, `cost_basis: computed_from_usage`, `price_source: replicate.com/pricing#2026-10-06`
  (FLUX schnell), in all five builds.
- The library-route build: 2 content calls (claude-sonnet-5-5: 9,015 in / 3,403 out tokens) and 4 vision review
  calls (gpt-6.1-sol: 22,215 in / 1,187 out). At the catalogue prices (`omni_prod/intelligence/prices.py:104,109`,
  $2 / $10 per million) that is $0.10836, exactly the recorded spend. One vision review call therefore costs about
  $0.014 (computed from those tokens).
- Legacy builds: $0.526 to $0.949 (4 builds), with 15 to 41 model calls each.

---

## 2. Diagnosis: why the sites look generic

One line: the designed path cannot hold pictures, the path that holds pictures is not designed, and no gate asks for
a picture.

### 2.1 By dimension

| Dimension | Finding | Evidence |
|---|---|---|
| **Imagery** | The main cause. 3 of the last 5 READY pages have no picture at all; 8 of 8 library renders have none. The hero "visual" is a coloured box with the opening hours, or a line drawing chosen per direction (`section_library/__init__.py:197-208`: lines, columns, arches, diagonals), the same drawing for every business of that direction. | 1.1 table; 1.2 table; `sheet_library_mobile_first.png` |
| **The picture pipeline and the designed route exclude each other** | `decide()` sends a build to the legacy path when a photo is placed anywhere but hero or story (`:192`), when an icon is asked (`:196`), when more than one picture is asked (`:199`), or when a picture of each item is asked (`:206`, `one_page.beyond`). The library has a `gallery` section (`__init__.py:427`) that the route never fills (`schema.py:103`). So "a picture per item" exists only where the model writes the page from nothing. | code lines; `bld_6a278b91`; `site_route.skipped` of `bld_a02d9a6e` |
| **Hero** | With no photo: a box. With a photo: a boxed panel covering 11 to 16% of a desktop screen, never full-bleed, with the facts printed on the photo. | `sheet_library_photo_desktop_first.png`; 1.1 |
| **Layout repetition** | One section order; every section is a centred 1152 px column of 1 or 2 columns on alternating plain and tint bands; no full-bleed element; `about` and `faq` leave half the row empty. Variety is 5 axes of 2 options picked by a hash of the name (`__init__.py:606-620`). Skeleton similarity 0.76 to 0.99. | 1.1; `lib_cafes_desktop_full.png` |
| **Palette** | 10 palettes for 32 categories, each reduced to one accent: the contract drops the palette's second colour (`g_apple/contract.py:108,142`, "one accent colour: the primary"), and `static.py:152-160` refuses a second one. A business with no category signal gets the law-firm navy. | `g_apple.contract.dropped` in all four contracts of 1.2; `bld_a02d9a6e` |
| **Typography** | The strongest part today, and not the problem: 7 different font pairs on 8 pages, a display face per direction, 56 or 72 px headlines. | 1.1 table; `sheet_library_desktop_first.png` |
| **Motion** | One 250 ms entrance on 4 hero elements (`library.css:260-261`) and hover transitions. Nothing else moves. An existing test forbids hiding content until scroll (`tests/test_section_library.py:115`), for a good reason: the reviewers screenshot 300 ms after load. | 1.1 (`animated_elements: 4`) |
| **Density** | A phone page is 4,400 to 5,500 px, 5 to 6.5 screens, of text and boxes with no picture to break it. Legacy pages are thin instead: 35 to 40 text elements against 89 on the library page. | 1.1; 1.2 |
| **Image art direction** | One prompt shape for every business: the subject, then "Original <purpose> for a web page; realistic, high quality" (`image_prompt.py:61-63`). The only style input is the one word of the brief's "Design: style" (`capability_planner.py:571`). Every picture is 16:9 (`generated_images.py:101-103`). Nothing ties the pictures of one site to one look. | code lines |
| **Gates** | Nothing blocks a page for looking generic. Visual QA enforces five "not broken" rules (`visual_qa.py:197`). The design critic's score gates nothing: only `must_fix` counts, once (`design_review.py:94`); a 57 shipped. G-APPLE and PRO are at warn (`gate.py:72-73`). PRO's "has a visual" is satisfied by any `<svg>` (`design_minimum/probe.py:27`): all 8 picture-less renders pass it, two of them with nothing but phone, WhatsApp and menu icons. | `U.run('design_minimum', page)` = `{'status': 'pass'}` on 8 of 8; `<img>` 0 on each; hair salon and photographer: 8 `<svg>`, all 24x24 icons |

### 2.2 Defects found on the way (Claude's code; said before any fix)

1. **The default hero picture was generated, paid for and thrown away** in 3 of the last 5 READY builds
   (`image_match.py:91`). Claude's bug: the default hero had no subject. `#541` (merged 2026-11-26 17:23 UTC) gives it
   one from the brief's business line (`capability_planner.py`, `_image_subject`). No READY build exists after that
   merge (the latest is 2026-11-26 16:13 UTC), so the fix is **not verified in production**.
2. **The hero photo's colour overlay is painted under the photo.** `library.css:112-114` gives `::before` z-index 0
   and leaves the `<img>` at auto; the image is the panel's last child (`__init__.py:307-318`, pinned by
   `tests/test_section_library.py:197`), so it paints over the overlay. Reproduced on the real page: with a pure
   green photo the bottom edge of the panel, where the overlay is 94% primary, reads `(0, 255, 0)`
   (`vd_work/overlay_check.py`; `overlay_check_lawyer_panel_green_photo.png`). White facts (formal, bold) or dark
   facts (warm, elegant) sit on the raw photo. Probe on a scratch copy: overlay z-index 1, content 2 -> the same pixel
   reads `(28, 69, 89)` = 94% of `#1e3a5f` over green. Claude's bug. It will show on the first library build whose
   hero survives, which `#541` now makes the normal case.
3. **`design_minimum` counts an icon as the page's visual** (above). Claude's bug in the gate's definition.

---

## 3. Constraints that shape the design

- **Iron law 9** (every claim with a source) and lens 11: a picture shows what the customer's own words name, and is
  checked by `image_match`. So no "atmosphere" picture with an invented subject. Every subject below is the
  customer's words: the business line, or an item they listed.
- **Iron law 4**: no new question to the customer unless it blocks the build.
- **Iron law 30 / OWNERS rule 5**: new spend, a provider or model change, and the customer's approval flow are the
  owner's. Section 7 asks.
- **Cost**: the $2 per build ceiling stays (CLAUDE.md section 6). Warehouse 136: cost is counted, no new limit or
  price is built.
- **The owner's rule 4 for gates**: a new gate or rule enters at warn, is calibrated on three builds with a proven
  fall on a broken page, and only then blocks.
- **CLAUDE.md section 4**: thresholds and art-direction data are global; they are read from the platform at run time
  (as `directions.json` already says), never from the built repository.
- **Law 9 of AGENTS.md**: no parallel system. Everything below extends `section_library`, `site_content`, `a4`,
  `image_prompt`, `visual_qa`, `skill_units/design_minimum` and `g_apple`.
- **Law 11**: every slice is revertible by reverting its PR; `LIBRARY_VERSION` (and so `RENDERER_VERSION`) is bumped
  whenever the page's bytes change.

### Warehouse collisions, said in advance (CLAUDE.md section 7.2)

| Item | State in WAREHOUSE.md | Collision |
|---|---|---|
| **125** design contract per category | released 2026-11-21, order 5, "בתכנון", no section of its own yet | Slices S4 and S5 **are** 125 and widen it (image style, second colour, texture, hero composition are not in its wording). Its section, acceptance criteria and mutations must be written first (rule 7.4), and the widening is the owner's (question 4). |
| **123** page typology and skeletons | released, order 4, "בתכנון" | 123 owns which sections a page type has, their order, density and image-to-text ratio, and "a threshold table per type". S2's thresholds are one table for the business page only, placed so 123 can later split it per type. S5 adds variants inside existing sections and no page type. S5 should wait for 123 or be folded into it. |
| **122** mandatory fields | released, order 3, "בתכנון" | The owner's recorded order is 122 -> 123 -> 125, with the warning "אם תעשה v3 לפני 122, תקבל וריאציות יפות של תוכן ריק". S0 to S3 are not 125 (they repair and connect what exists), but doing visuals now is still ahead of 122. Question 1. |
| **126** font pairs | built (`omni_prod/typography`) | Two fonts and two weights per build stay. No slice adds a face or a weight. |
| **127** 30 domains | released, first in its queue; `domain_registry.json` carries facts, references and terms | Art direction is **not** added to the domain files (their one schema is 127's acceptance 1). It stays in `directions.json`. The no-category business that gets the lawyer palette is a category-detection problem, 127's and 122's; not designed here. |
| **128** image and voice intake | released, queued | None. A competitor's screenshot gives a skeleton only; nothing here reads it. |
| **129** script layer | partly built (`LIBRARY_SCRIPT = 'hebrew'`) | Every new layout uses logical properties; the library writes no new words of its own except where stated; headings still pass `T.check_headings`. |
| **130** separate apps pipeline | released, queued | None. `not_content_only` stays on the legacy path; this design covers content sites only. |
| **118** image as a file | "בבנייה"; not verified on a production build | S3 depends on it: several pictures per page must be files, not inline data. |
| **124** see, screenshot, fix the component | released, "בתכנון" | New sections must stay addressable as one component each (one `<section id>` per section, as today). |
| **136** cost limits and pricing | in the warehouse | No limit or price is built. Costs below are reported, not enforced. |

---

## 4. Decision

**Recommended: bring pictures into the designed path, measure them, then give each trade an art direction.**
In order: repair the photo hero and the gate's definition of a visual (S0); make the first screen photo-led (S1);
measure visual quality in the browser run that already exists (S2); let builds with pictures stay on the library
route, with a picture in each item's card and a real gallery (S3); one image style per trade, applied to every
picture of a build (S4); more compositions (S5); motion and texture (S6).

Why this order: the evidence puts the missing picture first (2.1), the library is already where type, colour and
spacing are good, and it costs a fifth of the legacy path ($0.11 against $0.53 to $0.95, section 1.3). S0 to S2 add
no spend at all.

### Alternatives rejected

| Alternative | Why not |
|---|---|
| **Art direction first** (125 as written: palette, type scale, spacing) | The renders already differ in colour and font per trade and still look alike. Without pictures a richer contract gives eight differently coloured text pages. It comes fourth, not first. |
| **Improve the legacy path**: a stronger art-director prompt and a critic loop on model-written pages | 4 of the 5 READY builds are legacy: scores 57 to 87, 35 to 40 text elements, 5 to 9 times the cost, a different page every run, and no deterministic check of composition is possible on free-form markup. It also reverses the owner's direction of 2026-11-20 (designed sections, the model fills them). |
| **Buy a template kit or stock photos** | A new provider and licence (the owner's decision), a second section system beside the library (law 9 of AGENTS.md), and a stock photo of "a cafe" is less the customer's than a picture made from their own words and checked against them. |
| **A new vision reviewer that scores "premium"** | Taste scored by a model is not a gate one can calibrate; the existing critic already records a score. The task's rule is a deterministic check or a vision check that exists: S2 is deterministic and reuses `image_match` and the two G-APPLE reviewers unchanged. |
| **Change the type scale now** (a 96 px step in `contract.TYPE_PX`) | Typography is the strongest part (2.1). The change alters every contract fingerprint and must be replayed against stored versions (`gate_regression`). Not worth it before pictures. |

### Risks

1. **Picture quality.** FLUX schnell is the cheapest tier; earlier builds got mountains for bread and eggs for beef
   (`image_match.py:4-6`). `image_match` checks the subject, not the quality. I have seen no production picture
   (1.2). A page that leads with a weak picture can look worse than a page with none. Mitigation: S1's cover layout is
   used only for a picture that passed `image_match`; question 3 asks the owner about a stronger model.
2. **118 is unverified in production.** Several pictures per page lean on it. S3 does not start before one production
   build shows a picture served as a file.
3. **More pictures, more ways to fail a build.** A required picture that does not match stops the build
   (`ImageDoesNotMatch`). Per-item pictures generated by default (question 2, option ב) must be optional: a picture
   that fails its check is dropped and said, and the card renders without it; the build does not fail.
4. **Page weight.** `a4.PAGE_IMAGE_BUDGET_BYTES` is 1.5 MB for all pictures; `web_rendition.fit_page` re-encodes to
   fit and warns. Eight pictures leave about 190 KB each. G4 stays at warn.
5. **Calibration on few builds.** Production has 16 READY builds in all. Thresholds in S2 are first estimates; they
   stay at warn until three builds confirm them.
6. **The legacy share.** Raising the library does nothing for a build that never reaches it (8 of 10 routed builds).
   S3 removes four of the reasons; the others (`name_not_declared`, `phone_not_one`, `no_design_contract`) are outside
   this design and should be counted per week from `site_route.reason`.

---

## 5. The slices

Common to every slice:
- One PR per slice (iron law 26), from current `main`; the whole suite before a push (CLAUDE.md section 2 rule 8);
  browser tests never in parallel (section 8א).
- Mutations go in `tests/negative_controls/<name>.json` in the existing format (`file`, `old`, `new`, `targets`,
  `expect_failed`); the runner is `scripts/run_negative_controls.py`.
- The PR carries before/after contact sheets of the 8 reference verticals, made by the scratch script of section 1.1
  moved into `tools/` (it uses only repository code and Playwright).
- Costs: "measured" means read from section 1.3; everything else is marked an estimate.

### S0. Repair what is broken (no new design)

| | |
|---|---|
| **What** | (a) The hero photo's overlay paints above the photo and under the text. (b) `design_minimum` counts a picture, not an icon: `<img>`, `<picture>`, `<video>`, a CSS `url(...)` background, or an `<svg>` that is not inside `<a>`, `<button>` or `<summary>`. (c) One production build verifies that the default hero survives (`#541`) and is readable. |
| **Where** | (a) `omni_prod/section_library/library.css:112-114`; bump `LIBRARY_VERSION` (`__init__.py:34`). (b) `omni_prod/skill_units/design_minimum/probe.py:27`, its `manifest.json` description and `fixtures/`. |
| **Acceptance** | 1. Playwright, the real `page()` with a solid-colour photo, each of the four directions, both viewports: the pixel under the lowest fact row is within 8 per channel of the overlay colour; every text node inside `.panel--photo` has contrast >= 4.5 against the pixels under it. 2. `U.run('design_minimum', page)` fails with `DESIGN_TOO_BASIC` on the two elegant renders (hair salon, photographer: 8 SVGs, all of them icons inside controls), and passes on a page with one `<img>`. It still passes on the six renders that carry the panel drawing, including the two `banner` pages where the CSS hides that drawing (`library.css:324`): a static probe cannot see what is displayed, which is why S2 measures in the browser. 3. The conformance matrix (`tests/test_section_library_conformance.py`) and `tests/test_site_content_render.py` stay green. 4. (c) one production build on the library route: `asset_plan.plan` has a `hero` slot, `capabilities.image_match[0].status = MATCH`, and its stored desktop and phone screenshots are attached to the PR. |
| **Mutations** | overlay z-index back to 0 -> the pixel test fails; the `svg` alternative restored to "any svg" -> the icon-only fixture passes and the test fails; the photo set `loading="lazy"` -> `perf_hero_eager` fails (exists). |
| **Cost per build** | $0 added. PRO is at warn: a picture-less page is reported, not blocked. |
| **Warehouse** | none. (c) needs the owner: question 5. |

### S1. A photo-led first screen

| | |
|---|---|
| **What** | Two hero layouts that exist only when `hero.image` exists: `cover` (the photo fills the first screen edge to edge, the headline and the action on a scrim) and `photo` (the photo fills one half to the viewport edge; the facts are a strip under the hero). The facts never sit on the photo. Without an image the hero stays `split` or `banner` as today. On a phone the photo comes first and the headline and the main action are still on the first screen. |
| **Where** | `section_library/__init__.py`: `LAYOUTS['hero']` (`:606`), `layout_for` (`:610`; a photo layout named for a page with no image raises, never a silent default), `hero` (`:292`); `library.css` (logical properties only; the scrim from `--color-text` / `--color-primary` with `color-mix`, no raw colour); `site_content/schema.py` and `validate.py` get the new variants through `LAYOUTS` (`validate.py:389-397`) with no change of their own. |
| **Acceptance** (Playwright, real page, `visual_qa.VIEWPORTS`) | 1. Hero photo's visible area / viewport area >= 0.40 desktop and >= 0.35 phone (today 0.107 to 0.157 and 0.29 to 0.30). 2. `h1` and the primary action lie wholly inside the first screen on both. 3. Text over the photo: contrast >= 4.5 against the sampled pixels, for a white photo and for a black photo. 4. No enforced `visual_qa` finding; `g_apple.static.check` = []; `tests/test_section_library.py:115` (settled after 300 ms) passes; nothing scrolls sideways at 320, 390, 1440. 5. All four directions x the "photo hero" shape of the conformance matrix pass every gate. 6. The page fingerprint changes: `LIBRARY_VERSION` bumped. |
| **Mutations** | the scrim removed -> criterion 3 fails; `layout_for` returns `split` for a page with an image -> criterion 1 fails; `cover` rendered for a page without an image -> the "raises" test fails; the facts strip dropped -> the existing facts tests fail. |
| **Cost per build** | $0 added: the picture is the default hero that is already generated ($0.003, measured) and checked. |
| **Warehouse** | Touches what 125 will own (a direction's hero). Reported, not blocked: S1 changes composition, not the contract. |

### S2. Visual quality, measured where the page is already opened

| | |
|---|---|
| **What** | Visual QA's in-sandbox audit (`visual_qa.py`, `SCRIPT` / `AUDIT`) already opens the built page at both viewports. Add measurements to its report and four advisory rules to `RULES`. No new gate, no new browser run, no model. |
| **Measures** (written to `evidence_json.visual_qa.viewports.<v>.measures`) | `pictures` (rendered `<img>`/`<picture>`/`<video>`/background images of at least 120x120 CSS px); `first_screen_picture_share`; `page_picture_share`; `longest_run_without_picture` (in viewport heights); `compositions` (distinct signatures of a section: column count, has a picture, full-bleed); `text_on_picture_min_contrast` (canvas sampling of same-origin images). |
| **Rules** (advisory first: the owner's rule 4) | `no_picture` (a business page with zero pictures); `small_hero_picture` (a hero picture under the S1 shares); `text_on_picture` (contrast under 4.5, or 3 for large text); `long_run_without_picture` (on a page with 3 or more pictures, more than 2.5 phone screens with none). The thresholds live in one table in `directions.json` under a new key `visual_thresholds`, read from the platform; a missing key or an unknown rule name raises. |
| **Scope** | The layout rules judge only a page that carries the library's body marker (`data-148-kit`, `section_library/__init__.py:713`) or a contact action (the test `design_minimum` uses); an app or a game is not judged. `text_on_picture` judges every page. |
| **Acceptance** | 1. On the 8 picture-less renders: `no_picture` fires on each, on both viewports. 2. On the S1 pages: none of the four fires. 3. On the pre-S0 photo page: `text_on_picture` fires. 4. The measures of the 8 reference pages are asserted against a stored table (the numbers of section 1.1), so a silent change of the measure fails. 5. With `OMNI_VISUAL_QA_ENFORCE` unset, no build's outcome changes (the five enforced rules are the same). 6. The seam rule: the test runs the real `SCRIPT` audit text, as `tests/test_section_library.py:88-113` does, not a copy. |
| **Mutations** | the picture threshold of 120 px removed -> icons count and `no_picture` stops firing; the thresholds table read with a default -> the missing-key test fails; `no_picture` added to nothing (rule computed, never reported) -> criterion 1 fails; the measure returns 0 for a CSS background image -> the fixture with a background fails. |
| **After three production builds** | Each rule that fired on no good page moves into `DEFAULT_ENFORCED` (`visual_qa.py:197`) in its own PR, with the three builds as evidence. `no_picture` should block only after question 2 is answered (a customer may say "no pictures": `media_pipeline._NO_PICTURES`; that page is exempt). |
| **Cost per build** | $0 added (deterministic, same run). |
| **Warehouse** | 123 will want this table per page type; the single table is placed so it can be split. Reported. |

### S3. Pictures inside the designed sections (builds with pictures stay on the library route)

| | |
|---|---|
| **What** | (a) `services` cards and rows can carry a picture per item. (b) The route fills `gallery`. (c) `decide()` stops sending these to the legacy path when everything else holds: a photo placed in `products` or `gallery`, more than one picture asked, a picture of each item. Separate pages and "I will edit it later" still go to the legacy path, by name, as today. |
| **Binding a picture to its item** (the design decision an implementer should not have to make) | The fact sheet gains `items`: the brief's own item list, read by the one existing reader (`capability_planner._brief_items` / `item_pictures`), each addressed as `@item:N`, the way prices are `@price:N` and reviews are referenced today (`render.py:83-90, 171-176`). A `services` item in the model's document may carry `"item": "@item:N"`. The renderer attaches the picture whose A4 slot is `place: products` and whose `alt` is item N's words (`a4/__init__.py`, `_slot` and `plan`). The model never sees or chooses a picture. An unknown reference is `REF_UNKNOWN` (exists); a pictured item that no card references is a new validation code `ITEM_PICTURE_UNPLACED`, corrected by the existing content repair. |
| **All or none** | A services section shows pictures only when every card has one (the library's rule: "a section is given in full or left out"); otherwise it renders without pictures and says so in `skipped`, and the pictures go to the gallery, so nothing paid for is dropped silently. |
| **Where** | `section_library/__init__.py`: `services` (`:337`), `gallery` (`:427`), `LAYOUTS['services']` gains `picture-cards` and `feature` (alternating picture and text rows for up to 4 items), `gallery` gets one composed grid (one large tile, the rest small); `site_content/__init__.py:186-206`; `site_content/facts.py` (`_images`, `:309`; `items`); `site_content/schema.py:103` (`NEVER['gallery']` removed) and the services item schema; `site_content/render.py` `to_library` (`:145-148`); `a4.check` unchanged (it reads `<img>` on the page). |
| **Acceptance** | 1. A brief that asks for a picture of each of N listed items, all other preconditions holding: `decide()` = `section_library`; the page has N pictures, each inside the card whose heading is that item, `alt` = the item's words; `a4.check` passes. 2. A brief with the customer's own photo placed in `products` (the shape of `bld_6a278b91`) stays on the library route and the photo is in the products section. 3. A brief that asks for separate pages still routes to legacy with `beyond_one_page: separate_pages`. 4. One item's picture missing: the section renders without pictures, `skipped` says why, the pictures are in the gallery. 5. Preview smoke serves every `/assets` file (118's check) and the page has no `data:image`. 6. The S2 measures on the reference page with 6 item pictures: `longest_run_without_picture` <= 2.5, `compositions` >= 4. 7. Item maxima (`tests/test_item_maxima.py`) hold with pictures at 320 and 1440. |
| **Mutations** | `decide()` returns legacy for `picture_per_item` again -> criterion 1 fails; the picture of item N attached to card N+1 -> the alt-in-card test fails; `NEVER['gallery']` restored -> criterion 4 fails; a card with a missing picture renders an empty box -> the "all or none" test fails; the model's document allowed to name a picture -> the schema test fails. |
| **Cost per build** | Per picture: $0.003 (measured) plus one `image_match` check, about $0.005 to $0.014 (estimate: one picture per call; a full review call measured $0.014). Six item pictures: about $0.05 to $0.10 (estimate). The library route measured $0.108 without pictures, so such a build is about $0.16 to $0.21 (estimate), against $0.53 to $0.95 measured on the legacy path that carries these requests today. Far under $2. |
| **Warehouse** | 118 (depends on it; see risk 2). 123 (no page type added). 124 (one section, one component, unchanged). |

### S4. One art direction per trade, applied to every picture of a build (this is warehouse 125, widened)

Blocked on the owner's answer to question 4 and on 125's own section in WAREHOUSE.md.

| | |
|---|---|
| **What** | Each of the 10 palettes in `directions.json` gains an `art` block: `image_style` (one fixed English clause: light, crop, depth, tone, e.g. for hearth "warm window light, close crop, shallow depth of field, natural earthy tones"), `image_ratio` per place (hero 16:9; an item card 4:3; a gallery tile 1:1 or 3:4), `second_colour_use` (where the palette's own accent may appear: the eyebrow, numerals, hairlines), `texture` (`none`, `rules`, `dots`, `grain`: CSS built from tokens only), `hero` (which S1 layouts the direction may take). A category may override `image_style` only. Written by hand, versioned, read from the platform; not written by a model. |
| **The "style seed"** | Consistency comes from the shared clause, not from a number: every picture of a build gets the same `image_style` and palette words after its own subject, and the same fixed negative list. A provider `seed` only makes one picture reproducible on retry; it does not make two different subjects look alike, so it is not relied on. |
| **Where** | `section_library/directions.json` (and its test, which already fails on a palette with a missing key); `capability_planner._image_constraints` (`:558-583`: `style` comes from the palette's `art.image_style` when the route is the library, else as today); `generated_images.aspect_ratio` (`:101`: by place); `image_prompt.final_prompt` (`:61`); `g_apple/contract.py:108,142` (the accent is kept as `--color-accent` with its contrast computed, `VERSION` 2) and `static.py:152-160` (`SECOND_ACCENT` allows exactly that token); `library.css` (textures, accent use). |
| **Acceptance** | 1. Every palette has every `art` key; an unknown `texture` or hero name raises at import. 2. Seam rule: with the real `PredictionImageProvider.submit` and a recording `urlopen`, every picture request of one build ends with the same style clause and carries its place's ratio. 3. The saved `prompt-en.txt` of each picture contains the clause (evidence). 4. Two businesses of different directions differ in at least three of: hero layout, texture, second-colour use, heading face (asserted on the 8 reference pages). 5. The accent passes its contrast minimum or is corrected, as the other tokens are; `static.check` = [] on every palette. 6. Stored versions replay: `gate_regression` on a version built under contract `VERSION` 1 still passes against its own contract. |
| **Mutations** | the clause left off the item pictures -> criterion 2 fails; every place asks 16:9 -> the ratio test fails; a palette's `art` falls back to another palette's -> criterion 1 fails; the accent used as a button colour -> `BUTTON_STYLES` / `SECOND_ACCENT` fails; an unknown texture renders as `none` in silence -> the "raises" test fails. |
| **Vision check that exists** | `image_match` (subject) and the G-APPLE `brand_category` reviewer ("the imagery contradicts the trade" is a P0 in its instruction, `reviewers.py`) run unchanged. No new reviewer. |
| **Cost per build** | $0 added by the style clause. A stronger image model is a separate decision (question 3). |
| **Warehouse** | 125 (this is it), 126 (two fonts, two weights kept), 127 (domain files not touched). |

### S5. More compositions

Best folded into 123, or done after it.

| | |
|---|---|
| **What** | Variants inside existing sections, chosen by the direction first and the name hash second (the existing `layout_for`): `about` as an asymmetric 7/5 row with the story photo bleeding to the edge; the numbers strip and the call-to-action band as full-bleed bands; the gallery's composed grid from S3 in two more arrangements. |
| **Acceptance** | The conformance matrix passes for every palette x shape x new variant; item maxima at 320 and 1440; the skeleton similarity of the 8 reference pages (the measure of section 1.1, moved into the conformance test) has mean <= 0.80 and no pair of different directions above 0.90 (today: mean 0.899, max 0.993; first estimates); S2 `compositions` >= 4 on every reference page. |
| **Mutations** | `layout_for` ignores the direction -> the similarity bound fails; a full-bleed band scrolls sideways at 320 -> the overflow test fails; an unknown variant accepted -> `LAYOUT_UNKNOWN` test fails. |
| **Cost per build** | $0. |
| **Warehouse** | 123 (collision: skeleton, density). 129 (logical properties). |

### S6. Motion and texture

| | |
|---|---|
| **What** | CSS only, no library: a slow scale on the hero photo and item pictures driven by scroll position (`animation-timeline: view()`, inside `@supports`), a hover state on pictured cards, the textures of S4. Content is never hidden waiting for a scroll. |
| **Acceptance** | `tests/test_section_library.py:115` passes unchanged (no element of `main` under 0.99 opacity 300 ms after load); under `prefers-reduced-motion` nothing animates; layout shift measured in Playwright is 0; `static.check` = [] (durations and easing from the contract's motion tokens only); no enforced visual finding. |
| **Mutations** | a reveal that starts at opacity 0 -> the 300 ms test fails (the existing test is the control); the reduced-motion block removed -> its test fails; a duration outside the tokens -> `static.check` fails. |
| **Cost per build** | $0. |
| **Warehouse** | none. |

### Order and dependencies

`S0 -> S1 -> S2` (no spend, no owner decision except the one verification build) `-> S3` (after 118 is seen in
production; default pictures depend on question 2) `-> S4` (after question 4 and 125's section) `-> S5` (with or
after 123) `-> S6`.

---

## 6. Not tested, said openly

- No production page was seen: previews expired, the proxy refuses their host, no access to the stored screenshots.
  The description of the five builds rests on their evidence rows and the reviewers' words.
- No generated picture was seen, so the quality of FLUX schnell on these trades is unknown to me.
- `#541`'s default-hero fix and warehouse 118 have no production build behind them.
- Current prices of stronger image models were not read (the proxy refuses `replicate.com`).
- How the five builds would route on today's `main` was not replayed: that needs their prompts, which carry
  customers' details.
- The seven synthetic pages are my content, not the content model's; the real model may write longer or shorter
  copy. The lawyer page is the real fixture.
- Thresholds in S1, S2 and S5 are first estimates from 8 renders, to be calibrated on three builds.

---

## 7. Questions for the owner (one decision each)

1. **סדר העבודה.** ב-2026-11-21 נקבע הסדר 122 (שדות חובה) -> 123 (סוגי עמוד) -> 125 (חוזה עיצובי), עם האזהרה
   שעיצוב לפני תוכן נותן "וריאציות יפות של תוכן ריק". התמונות והפתיח (S0 עד S3) אינם 125, אבל הם לפני 122.
   - (א) מתחילים עכשיו ב-S0 עד S3, ו-122 ו-123 ממשיכים אחריהם. **מומלץ.**
   - (ב) שומרים על הסדר: קודם 122 ו-123, ורק אז ויזואלים.

2. **תמונות כברירת מחדל.** היום אתר מקבל תמונה ראשית אחת, ותמונה לכל פריט רק כשהלקוח ביקש.
   - (א) נשאר כך.
   - (ב) כל שירות או מוצר שהלקוח רשם מקבל תמונה גם בלי שביקש, אלא אם אמר "בלי תמונות". העלות נכנסת למחיר שהלקוח
     רואה לפני האישור. תוספת: בערך 0.01 עד 0.02 דולר לתמונה (הערכה). **מומלץ.**
   - (ג) שואלים את הלקוח שאלה אחת: "תמונה לכל שירות?".

3. **מודל התמונות.** היום FLUX schnell, 0.003 דולר לתמונה (נמדד). זה המודל הזול, ולא ראיתי את התמונות שלו.
   - (א) נשארים איתו ובודקים את התוצאה בעין אחרי S1.
   - (ב) בדיקה חד-פעמית: אותן 10 תמונות במודל הנוכחי ובמודל חזק יותר, ואתה בוחר בעין. מחיר מודל חזק: בערך 0.03 עד
     0.06 דולר לתמונה (הערכה מזיכרון, לא נבדקה מול המחירון). **מומלץ.**
   - (ג) מחליפים מודל בלי בדיקה.

4. **פריט 125 במחסן.** הוא כתוב כ"פלטה, סקאלת גופנים, ריווח, ניגודיות". S4 מוסיף לו סגנון תמונות לכל תחום, צבע
   שני, טקסטורה והרכב הפתיח.
   - (א) מרחיבים את 125 לכלול גם את אלה. **מומלץ.**
   - (ב) 125 נשאר כמו שהוא, והתוספות מקבלות מספר מחסן חדש.

5. **בנייה אחת לאימות.** התיקון ששומר את התמונה הראשית (#541) ותיקון הכיסוי שלה (S0) לא נראו עדיין בייצור.
   - (א) אתה בונה אתר אחד אחרי S0, ואני קורא את הראיות.
   - (ב) אני מריץ בנייה אחת של חזרה. עלות: בערך 0.11 עד 0.25 דולר (הערכה; הבנייה היחידה במסלול הזה עלתה 0.108).
   - (ג) מחכים לבנייה הבאה שלך, בלי בנייה מיוחדת.
