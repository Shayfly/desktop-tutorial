# Conversation UX, image attachments and Visual Edit (2026-10-11)

Founder directive "148AI Conversation UX + Visual Editing". Target loop: "build me an app" → see it working → point at what you don't like → ask for a change → see the result. No code knowledge and no knowledge of agents is needed. **No new build engine:** every change goes through the existing modification pipeline, which produces a candidate, runs the checks, waits for accept or reject, then creates a version and a preview. Existing rollback and previews are reused.

## What exists now

| Capability | Where | Status |
|---|---|---|
| Short, material-only replies | `conversation/supervisor.py` | IMPLEMENTED + TESTED (unit + real browser) |
| Image attachments (chat and editor) | migration 038, `attachments.py`, `/attachments` API, `visual-edit.js` | IMPLEMENTED + TESTED (real PostgreSQL; real browser) |
| Image analysis by a vision model | — | **NOT IMPLEMENTED / BLOCKED**: needs a vision route and an approved budget. The UI and the stored state say `NOT_ANALYZED`. |
| Element picking in the live preview | `preview_inspector.py` (wraps the unchanged `preview_router.py`), `visual-edit.js` | IMPLEMENTED + TESTED locally through the real router over TLS. **Off in deployment** until `OMNI_PREVIEW_INSPECTOR=1` and `OMNI_WORKSPACE_ORIGINS` are set on the worker host. |
| Selection → source file and line | `visual_edit.locate` + `/visual-edit/locate` | IMPLEMENTED + TESTED |
| Targeted change through the existing pipeline | `V28ModificationRequest.target` / `attachment_ids` → `compose_followup` | IMPLEMENTED + TESTED (request reaches the queue). The worker's model step was **not** run (paid). |
| Screenshot with marks (box, free drawing) | `visual-edit.js` canvas → attachment `screenshot` with `regions` | IMPLEMENTED + TESTED |
| Before/after comparison, undo | existing previews + existing `/rollback` | IMPLEMENTED + TESTED |
| Layout | `index.html`, `app.css`, `visual-edit.js` | IMPLEMENTED + TESTED. Desktop: chat (right in Hebrew), preview (centre), edit tools (left); every area resizes and the project list is a drawer. Mobile: Chat / Preview / Edit tabs. |

### Conversation
- Decisions are named in a word or two ("פרטים אישיים: כן"), not by repeating the question.
- A value taken from the request is verified ("רק לוודא — …"), not asked from scratch.
- "לא יודע", "מה?" or "למה?" gets the reason and the "בחרו עבורי" way out. A second one gets the options. The same sentence is never repeated.
- Approved requirements are never changed silently. This is the existing Issue #12 behaviour, still covered by `test_intake_requirements_preservation`.

### Attachments
- Accepted: PNG, JPEG, WebP. The type comes from the file's bytes; SVG, GIF and HTML are refused (415).
- Limits: 3 MB after the browser downsizes (photos are re-encoded, which also drops camera location metadata), 8000 px per side, 6 per message, 40 live per project.
- Isolation: every read and delete filters on project and owning account; the API checks project ownership first. Another account gets 403/404.
- Served with `nosniff`, `CSP: default-src 'none'; sandbox`, `no-store`.
- Bytes live in the project artifact bucket under `attachments/<account>/<project>/` and are deleted with the attachment.

### Visual Edit
1. "בחירת רכיב" sends `148ai:inspect` to the preview iframe. Origins are checked both ways.
2. The inspector highlights under the pointer or finger. On click or tap it posts a bounded description of the element (tag, id, classes, a few attributes, visible text, CSS path, box). It never sends form values, cookies or storage.
3. `locate()` searches the exact stored files of the shown version for the strongest anchors:
   - id, then test id / name / aria-label / placeholder, then visible text, then classes;
   - the enclosing tag must match.
4. Result handling:
   - **UNIQUE**: "נמצא בקוד: file:line".
   - **AMBIGUOUS**: the person picks one place, or "אף אחד מאלה — אתאר במילים". The places are described by page and nearby heading; code is under "פרטים טכניים".
   - **NOT_FOUND**: the person describes the change in words.
   - The server refuses a target it cannot resolve: 409 `target_ambiguous`. Nothing is changed on a guess.
5. The person's words, the exact location and a scope rule ("keep every other part unchanged") go to the existing modification endpoint. Any marked screenshot goes along as context, flagged "not analyzed automatically".

## Verification (local, $0)
- `tests/test_visual_edit.py`:
  - image validation;
  - attachment repository on real PostgreSQL (create/read/delete, cross-account and cross-project isolation, tamper refusal, limit, schema checks);
  - locate / choose / compose;
  - inspector injection and gzip handling;
  - the router wrapper end to end over real sockets.
- `tests/test_conversation_ux.py`: conversation behaviour.
- `tools/ui_visual_edit/walkthrough.py`: real Chromium, desktop 1440×900 and mobile 390×844. Result: **23/23 checks** (`docs/evidence/visual_edit/walkthrough_result.json`, screenshots 01–16).
  - Real components: FastAPI, PostgreSQL (migrations through 038), the attachments API, locate, the modification API (queue, accept, rollback), the preview API with real access tokens, and the real preview router wrapped by the inspector over TLS.
  - Test-only substitutes:
    - object storage = local files (S3/R2 not exercised);
    - the preview "container" = a local process (no Docker daemon in this environment);
    - the modification **candidate was written by the harness, not by a model**, so the generated change itself is not evidence of the engine.
- `tools/ui_conversation_walkthrough.py` (Wave A) still passes. Two steps were adapted to the deliberate layout change: the project drawer and the mobile tabs.

## Remaining gaps
1. **Vision analysis of images**: needs a vision-capable route in the catalog and a founder-approved budget. Until then images are context only.
2. **Inspector in deployment**:
   - set `OMNI_PREVIEW_INSPECTOR=1` and `OMNI_WORKSPACE_ORIGINS=<workspace origin(s)>` on the worker host;
   - compose already runs `omni_prod.preview_inspector` (pass-through when off);
   - then verify on the real preview host.
3. **Real targeted change**: one paid modification on the worker, to verify that the engine honours the target and scope (G10 in `docs/SYSTEM_WIDE_GAP_AUDIT.md`).
4. **Preview of a candidate before accepting**: not available. Comparison and undo happen after accept, and undo is one click.
5. **Generated apps with a strict CSP**: an app whose CSP forbids `'self'` scripts blocks the inspector. Picking then reports "not available"; screenshot marking still works.
6. **Migration 038 vs PR #11**: when both are merged, `schema_manifest.REQUIRED_MIGRATION` must become 38.
