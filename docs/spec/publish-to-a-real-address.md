# Publish to a real address — design

Status: **design only**. No code, no migration, no provider change is made by this document.
Author: Claude Code, 2026-11-21. Code facts are from `origin/main` at `a77c1b8`.
Owner's order (2026-11-21): "148ai will be a product factory: a conversation goes in, a working product comes out, at a live address, in any language. Publishing to a real address enters the scope. Without it there is no product."

Conventions: every claim about our code carries `file:line`. Every platform claim carries a URL, read 2026-11-21. A number without a source is marked **estimate**. A fact that could not be checked is marked **not verified** and repeated in section 8.

How the platform sources were read: `vercel.com` is not reachable from this session (DNS refused), so Vercel pages were read through the Vercel documentation search tool (a third-party index of the published docs). The URL given is the page the excerpt names; the full page was not read. Neon pages were read in full through the Neon documentation tool.

---

## 1. What exists today, and where the journey ends

### 1.1 How a build's result is stored
- A build's output is a **version**: a dictionary of path → text. It is zipped and stored in object storage under a content address, `repositories/<sha256>.zip` (`omni_prod/workspace.py:183-192`), and a row is written to `project_versions` with `repository_sha256`, `artifact_key`, `file_count` (`omni_prod/workspace.py:209-210`; table `infra/postgres/010_international_product.sql:13-20`).
- The store is S3-compatible; Cloudflare R2 hosts are recognised (`omni_prod/storage.py:17,33`), and the worker host's own notes name R2 (`infra/worker-host/docker-compose.yml:4-5`).
- **A version is text only.** Unzipping decodes every file as UTF-8 (`omni_prod/workspace.py:151-155`). A binary file (an image) cannot be stored as a file today; this is warehouse item 118 (`WAREHOUSE.md`, row 118).
- Versions are immutable and can be restored (`omni_prod/workspace.py:250`).

### 1.2 What the generated product is at runtime
- A server process, started from `.omni/project.json`: `runtime` (allowlisted image: `python:3.11-slim` or `node:20-slim`), `start` (argv), `port`, `health_path` (`omni_prod/preview_runtime.py:44`, `:123-165`).
- The generator's contract is "Python standard library, SQLite, web UI served by the app" (`omni_prod/product_architect.py:33`), with records in one SQLite file under `DATA_DIR` (`omni_prod/product_architect.py:29`; `omni_prod/dependency_policy.py:66-67`).
- **A content-only site is also a server today.** When the customer explicitly says the site only shows information, with no sign-in and no personal data, the contract gets the default `static_content_site` (`omni_prod/product_architect.py:104`, `:336`; `omni_prod/discovery.py:815-821`), and the acceptance run waives record creation (`omni_prod/web_saas_acceptance.py:101-110`). The artifact is still a generated Python server that answers HTTP.
- **Not found on `origin/main`:** a "content route" that renders a deterministic page from a content document. `grep` for `content_doc`, `ContentDoc`, `content route`, `render_page`, `static_site` finds only `tests/test_content_only_site.py`. If that route exists on another branch, section 3 uses it directly; if not, section 3 does not depend on it.

### 1.3 Preview, end to end
1. `POST /api/v28/projects/{project_id}/versions/{version_id}/previews` checks the version's contract, creates a `project_previews` row with a TTL and enqueues a job (`omni_prod/investor_app.py:3016`, `:3033-3066`).
2. The TTL is **3600 seconds** by default (`omni_prod/investor_app.py:2983`).
3. The preview worker on the worker host starts one Docker container per preview: 0.5 CPU, 512 MB, 64 processes, read-only root, all capabilities dropped, non-root user, source mounted read-only, port bound to loopback (`omni_prod/preview_runtime.py:49-65`, `:212-244`). Only this orchestrator and the janitor hold the Docker socket (`infra/worker-host/docker-compose.yml:126-156`, `:177-193`).
4. The address is `https://prv-<hex>.<suffix>`. Caddy issues a certificate on demand, only when the router confirms the name is a running preview on this host (`infra/worker-host/Caddyfile:1-15`; `omni_prod/preview_router.py:135-138`).
5. The router proxies only while the row is `RUNNING` **and** `expires_at > now()` (`omni_prod/preview_repository.py:283-299`). After that it answers `404 This preview is not running (stopped, expired or unknown).` (`omni_prod/preview_router.py:141-142`).
6. A janitor marks expired previews and removes their containers every 30 minutes (`omni_prod/maintenance.py:51-56`, `:203-207`; `infra/worker-host/docker-compose.yml:177-186`).
7. Data: when `OMNI_PREVIEW_DATA_ROOT` is set, each project gets one host directory mounted at `/data`, which survives a preview restart and a new version (`omni_prod/preview_runtime.py:236-240`, `:403-409`; `infra/worker-host/docker-compose.yml:148-150`). Otherwise the data is in a 64 MB tmpfs and the UI says "נתונים זמניים: מה שתזינו יימחק כשהתצוגה תיעצר." (`omni_prod/assets/app.js:100`; `omni_prod/investor_app.py:2998-2999`). **The persistent directory lives on one VPS disk.** The compose file itself says "nothing on this host is the source of truth" (`infra/worker-host/docker-compose.yml:4-5`). No backup of that directory was found — **not verified**.

### 1.4 Sharing
- A preview is `PRIVATE` by default; the owner may set `SHARED` or `PUBLIC` (`infra/postgres/032_preview_access.sql:17-18`). The reason is recorded: preview hostnames appear in certificate-transparency logs and scanners hit them within minutes (`infra/postgres/032_preview_access.sql:3-5`).
- `SHARED` returns a link that is valid 7 days (`omni_prod/preview_access.py:27`; `omni_prod/investor_app.py:3112-3124`).
- **`PUBLIC` returns no link.** The endpoint adds `share_url` only for `SHARED` (`omni_prod/investor_app.py:3120-3123`), and the UI shows the link field only when `mode === 'SHARED'` (`omni_prod/assets/app.js:1212`). A customer who picks "כולם (ציבורי)" sees nothing to send. And the address would die within the hour anyway (1.3, step 5).

### 1.5 What "publish" is today
- The button exists (`omni_prod/assets/index.html:199`). Its only handler writes a sentence (`omni_prod/assets/app.js:1474`, `:1963`): "הפרסום לאוויר עוד לא מוגדר בשרת הזה. אפשר להוריד את הקוד ולבדוק בתצוגה המקדימה." (`omni_prod/assets/app.js:32`).
- The planner tells the customer the same before a build: "פרסום בכתובת קבועה עדיין אינו זמין. קיימות תצוגה פרטית והורדת קוד." (`omni_prod/assets/app.js:1767`; `omni_prod/planning/feasibility.py:99-102`).
- A `deployments` table exists (`infra/postgres/001_control_plane.sql:17-29`) with a repository class that retires the active row and inserts a new one in one transaction (`omni_prod/deployments.py:40-71`). Its callers are the acceptance pipeline and a staging simulation (`omni_prod/acceptance_pipeline.py:43`; `omni_prod/staging_simulation.py:28`). No API route writes it.
- `/hosted/v28/{deployment_id}` serves `index.html` of an **in-memory** deployment (`omni_prod/investor_app.py:3783-3789`; `omni_prod/unified_engine.py:279`, `:332-334`). It does not survive a restart of the function. It is not a publishing path.
- `generated_app_bindings` already distinguishes `preview` from `production` for a generated app's database, session, storage (`infra/postgres/021_generated_app_bindings.sql:12-13`). It holds references to secrets, never values (`:27-30`).
- The product mission already asks for "one verified deployment path for generated web apps, with an explicit distinction between preview and production publishing" (`PRODUCT_MISSION_AND_ACCEPTANCE.md:15`).

### 1.6 Exactly where the journey ends
The customer talks, approves, a build runs, a version is stored, a preview opens inside the workspace. Then:
- pressing "פרסום" gives a sentence about a server that is "not configured" and an offer to "download the code";
- the preview address stops answering after one hour;
- "public" sharing gives no link.

There is no address the customer can give to another person that still works tomorrow.

### 1.7 The hosting mandate that binds this design
- Web experience and control plane on Vercel. Untrusted generated code and long builds run in an isolated external sandbox/worker or a verified Vercel Sandbox; no host Docker socket in a publicly reachable function. Persisted state is durable outside ephemeral function storage (`AGENTS.md`, "For Vercel…" paragraph).
- CEO approval is mandatory for schema/data migrations, provider or paid-route changes, changes to the client approval flow, and new spend (`AGENTS.md`, "Changes to `omni_prod/**`…"). Scope may not grow because a model or an agent proposed it (`docs/OPERATING_CONTRACT_HE.md:211-241`). Publishing entered the scope by the owner's order above; each schema change and each new provider in this document still needs his explicit approval.

---

## 2. What "published" must mean for the customer

### 2.1 The promise
1. **A permanent address.** One address the customer can say out loud, print, and send. It does not change when the site changes.
2. **It stays up.** It answers when nobody from 148AI is awake and after any of our machines restarts. There is no "sleep" and no expiry.
3. **It shows the approved version.** What visitors see is exactly the version the customer looked at when pressing the button. A later change in the workspace does not reach visitors until the customer publishes again.
4. **Their data is kept** (tier B only): what visitors entered is still there after a restart, a new version, and a move between machines.
5. **Take down and put back.** The customer can take the site down at any moment; the address stays theirs; publishing again brings it back at the same address.
6. **Failure changes nothing.** If publishing fails, what was live before is still live, unchanged.

### 2.2 What the customer sees and presses
One button, one sentence, one address. No "deploy", "server", "domain", "DNS", "hosting", "version", "build", "URL", "link" (use "address").

The address is proposed by us from the business name, in Latin letters. The customer may change it before the first publish; it is the only field.

| Moment | Hebrew | English |
|---|---|---|
| Sentence above the button | האתר יקבל כתובת קבועה שאפשר לשלוח לכל אחד. | Your site gets a permanent address you can send to anyone. |
| Field label | הכתובת של האתר | The site's address |
| Button, first time | לפרסם את האתר | Publish the site |
| While working | מעלים את האתר לאוויר… | Putting your site on air… |
| Success | האתר באוויר. זו הכתובת שלו: | Your site is live. This is its address: |
| Action 1 | העתקת הכתובת | Copy the address |
| After copy | הכתובת הועתקה | Address copied |
| Action 2 | שליחה בוואטסאפ | Send on WhatsApp |
| Action 3 | פתיחת האתר | Open the site |
| Live, with unpublished changes | באוויר מוצג האתר כפי שאישרתם. יש שינויים שעוד לא פורסמו. | Visitors see the site as you approved it. Some changes are not published yet. |
| Button, later times | לפרסם את השינויים | Publish the changes |
| Take down | להוריד את האתר מהאוויר | Take the site down |
| Take down, confirm | להוריד את האתר מהאוויר? מי שיפתח את הכתובת יראה שהאתר לא זמין. הכתובת נשמרת לכם, ואפשר לפרסם שוב בכל רגע. | Take the site down? Anyone who opens the address will see that the site is not available. The address stays yours and you can publish again at any time. |
| After take down | האתר ירד מהאוויר. הכתובת שמורה לכם. | The site is down. The address is kept for you. |
| Address taken | הכתובת הזאת תפוסה. הכתובת הפנויה הקרובה: | That address is taken. The closest free one: |
| Address not allowed | בכתובת אפשר להשתמש באותיות באנגלית, בספרות ובמקף. | An address can use English letters, digits and a hyphen. |
| Not ready (a check failed) | אי אפשר לפרסם עדיין. צריך לתקן: | It cannot be published yet. This needs fixing: |
| Failed, nothing live before | הפרסום לא הצליח ושום דבר לא עלה לאוויר. אפשר לנסות שוב. | Publishing did not work and nothing went live. You can try again. |
| Failed, a site was live | הפרסום לא הצליח. האתר שהיה באוויר נשאר בדיוק כמו שהיה. אפשר לנסות שוב. | Publishing did not work. The site that was live is exactly as it was. You can try again. |
| Tier B, before it is built | אתר ששומר פרטים של מבקרים עוד אי אפשר לפרסם. אפשר להמשיך לעבוד עליו ולראות אותו כאן. | A site that keeps visitors' details cannot be published yet. You can keep working on it and see it here. |
| Visitor, site taken down | האתר הזה לא זמין כרגע. | This site is not available right now. |
| Visitor, unknown address | אין אתר בכתובת הזאת. | There is no site at this address. |

Rules for these strings:
- Hebrew is plural or neutral, never gendered (rule merged in #481, `git log` `cb30e31`).
- "Not ready" is followed by the failed check in the customer's words, one line per check, taken from the gate's own finding. A raw gate code is never shown.
- The WhatsApp action opens a share with the address as the text. The `https://wa.me/?text=` form is **not verified** against WhatsApp's documentation.
- The address shown after success is read from the same record the server routes on (section 6, criterion 7), never built in the browser.

The three strings that exist today and must be removed when slice 1 ships: `publishNotConfigured` (`omni_prod/assets/app.js:32`, `:161`), the planner's "publishing" line (`omni_prod/assets/app.js:1767`), and the feasibility finding (`omni_prod/planning/feasibility.py:99-102`).

---

## 3. Two tiers, and the order to build them

Tier A: **content sites.** Visitors only read. Nothing a visitor does is stored.
Tier B: **apps with data**: records, sign-in, payments.

Order: **A first, then B.** A needs no customer data, no secrets and no running generated code at serving time, so the whole promise of section 2 can be kept and proven with the infrastructure we already pay for. B needs a durable home for each product's data and a place where untrusted code runs all the time; neither exists (1.3 step 7).

Which tier a version belongs to is decided by one authority that already exists: the persistence decision (`omni_prod/persistence.py:1-11`) and the `static_content_site` default (`omni_prod/product_architect.py:336`). Slice 1 adds one check at publish time (3.1) and never trusts the label alone.

### 3.1 Tier A — the key idea: publish the bytes, not the program

At publish time the approved version is started **once** in the existing isolated runtime, with no data mount (the same "scratch copy" the acceptance probes use: `omni_prod/preview_runtime.py:446-461` with `persistent=False`; `omni_prod/worker_tasks.py:1880-1885`). A bounded reader fetches `/` and every same-site page and file it links to, and stores each response body with its content type. That set of bytes is the **snapshot**. The container is removed. Visitors are served the snapshot; generated code never runs for a visitor.

Bounds (every loop has a limit; a breach fails the publish loudly): at most 200 addresses and 25 MB per snapshot, 10 s per response — **estimates to be calibrated on real builds**; the largest page seen so far carried a 1.7 MB inline image (`WAREHOUSE.md`, row 114).

A version is **snapshot-eligible** only if all of these hold; otherwise it is tier B:
1. its contract carries `static_content_site`;
2. two reads of every address return identical bytes (a page that changes between reads is a program, not a document);
3. no page contains a form or script that sends data to the site's own address;
4. the reader stayed inside the bounds.

If the content route of the brief (a deterministic page rendered from a content document) is merged, it replaces the "start once and read" step: the renderer's output **is** the snapshot. Everything after that step is the same.

Three ways to serve the snapshot:

| | A1. One Vercel project for all sites, wildcard address | A2. The worker host (Caddy + a static router) | A3. One Vercel project per site |
|---|---|---|---|
| How | A small "sites" project. `*.<sites-domain>` points at it. The function reads `Host`, finds the live snapshot, returns the bytes with cache headers. | Extend `preview_router` to serve snapshot files for site names; Caddy already issues certificates on demand (`infra/worker-host/Caddyfile`). | Create a Vercel project per customer and upload the snapshot as a deployment (the "multi-project" pattern, https://vercel.com/docs/platforms/multi-project-platforms/concepts). |
| Cost per site per month | **Estimate: under $0.05** — storage of one snapshot of a few MB plus cached reads. Basis: no per-site compute; object storage and CDN prices **not verified**. | **Estimate: $0** incremental; the host is already paid. | **Not verified.** Project-count limits and per-project cost were not found. |
| Time to first byte | CDN hit: **estimate tens of ms**. Miss: one function run plus one lookup; our function is slow to start today (warehouse 100, `WAREHOUSE.md` row 100). | One VPS in Frankfurt, no CDN: **estimate 30–80 ms** in Israel/Europe, more elsewhere. | CDN, static: best of the three. |
| Isolation of untrusted code | None runs at serving time. Customer HTML/JS runs in the visitor's browser on a domain that is **not** ours (3.3). | Same, but the public edge shares a machine with the Docker socket holders. | Same as A1, plus a project boundary per customer. |
| Durability | Snapshot in object storage; pointer in Postgres. No state on any machine. | Files must be re-fetched from object storage after a host loss; the host is a single point of failure. | Held by Vercel as deployments; our copy still in object storage. |
| Update / rollback | Switch one pointer in one transaction; rollback is the same switch to the previous snapshot. | Same pointer; plus file sync on the host. | Vercel promote/rollback per project. |
| What breaks | Cache must be cleared on take-down (short lifetime plus purge). Wildcard needs our sites domain on Vercel's nameservers (below). | Host down = every customer site down. Preview load and public traffic share 1 VPS. | Hundreds of projects to manage; limits unknown; a customer's own domain is easy, everything else is harder. |

Platform facts used:
- Tenant hostnames are added to a shared project and "follow the project's current production deployment" (https://vercel.com/docs/platforms/multi-tenant-platforms/reference).
- A wildcard certificate cannot be issued unless the domain uses Vercel's nameservers or delegates `_acme-challenge` to Vercel (https://vercel.com/docs/domains/managing-dns-records).
- Function region defaults to `iad1`; a project may pin a region (https://vercel.com/docs/project-configuration/vercel-ts). Our `vercel.json` sets no region.
- Python function bundle limit 500 MB (https://vercel.com/docs/functions/runtimes/python).
- Maximum function duration per plan, response-size limit, the number of domains a project may hold, and wildcard pricing: **not verified**.

**Recommendation for tier A: A1.** A separate Vercel project that only serves snapshots, on a separate domain, pinned to Frankfurt, with the snapshot in object storage and the pointer in Postgres. Reason: it is the only option where "stays up" does not depend on one machine, it keeps the mandate (web on Vercel, no generated code in a public function, state outside the function), it adds no new provider, and rollback is one row. A2 is the fallback if the owner does not want a second Vercel project; it must then be described to customers as best-effort, which contradicts section 2.1 item 2.

A separate project, not a route in the control plane, because a bug in the public sites path must not be able to reach account data, and a flood of visitors to customer sites must not slow the workspace.

### 3.2 Tier B — apps with data

| | B1. Our own apps host: one container per app, started on request | B2. Vercel Sandbox per app | B3. Change what we generate: Vercel Functions + a Neon project per app |
|---|---|---|---|
| How | The preview runtime contract unchanged (`omni_prod/preview_runtime.py:49-65`), on a host that is **not** the build worker. A router starts the container on the first request and stops it when idle. The SQLite file is copied to object storage continuously and restored on start. | One named, persistent sandbox per app; filesystem is snapshotted on stop and restored on resume (https://vercel.com/docs/sandbox/concepts/persistent-sandboxes). | The generator stops emitting "stdlib + SQLite + `DATA_DIR`" (`omni_prod/product_architect.py:29-33`) and emits an app against Postgres; each app gets its own Neon project. |
| Cost per app per month | **Estimate: $1–3** when always on (512 MB each; about 6 per 4 GB machine), **under $0.50** when started on request. Basis: container envelope in code; VPS prices **not verified**. | **Not verified.** Sandbox pricing was not found. | Database: Neon bills $0.106 per compute-unit hour and suspends idle computes after 1–5 minutes (https://neon.com/docs/guides/ai-agent-integration). An idle app costs storage only. Function cost **not verified**. |
| Time to first byte | Running: tens of ms. Cold: container start plus restore — **estimate 2–5 s**, to be measured. | Resume time **not verified**. | Function cold start (our own is slow, warehouse 100) plus a database wake of "a few hundred milliseconds" (same Neon page). |
| Isolation | Docker with dropped capabilities, read-only root, non-root. Shared kernel. Socket held by a private orchestrator, never a public function. | A VM per sandbox; outbound network can be denied (https://vercel.com/docs/sandbox/concepts/firewall). Strongest. | Each app is its own project and its own database. |
| Data durability | As good as the copy job: a crash loses the seconds since the last copy. Must be tested by killing the host. | Data lives in the sandbox filesystem snapshot. Snapshots expire 30 days after last use unless set never to expire (https://vercel.com/docs/sandbox/concepts/snapshots). What is lost if a sandbox dies without a clean stop: **not verified**. | Postgres with point-in-time recovery: 1 day on the sponsored tier, up to 7 days paid (same Neon page). Strongest. |
| Update / rollback | New version = new container on the same data. Rollback of code is a pointer; rollback of data needs a schema rule (below). | Point the sandbox at an earlier snapshot (https://vercel.com/docs/sandbox/sdk-reference, `currentSnapshotId`) — code and data roll back together. | Neon snapshot before each publish; restore on rollback. |
| What breaks | One host again, unless we run two. SQLite allows one writer. | A session is capped: 45 minutes on Hobby, 24 hours on Pro and Enterprise (https://vercel.com/docs/sandbox/ecosystem/gemini-api); 10 concurrent sandboxes on Hobby (https://vercel.com/docs/sandbox/ecosystem/harbor). An always-on site must be resumed over and over. Sandbox in Frankfurt: **not verified** (default region `iad1`, https://vercel.com/docs/sandbox/sdk-reference). | Every gate, test and repair loop is written for the SQLite contract. It is a new generator. It needs the Neon Agent Plan (enrolment **not verified**) — a provider change. |

Neon's own guidance for a platform like ours is a project per tenant, not a branch or a database per tenant (https://neon.com/docs/guides/embedded-postgres; https://neon.com/docs/guides/multitenancy). A branch per product inside `148ai-db-v2` is ruled out for a second reason: a child branch copies the parent's roles and passwords (https://neon.com/docs/guides/protected-branches), and one project allows 20 concurrently active computes by default (https://neon.com/docs/manage/computes).

**Recommendation for tier B: B1, with the data copy as the first acceptance test, and only after tier A is live.** Reason: it publishes exactly what was built and tested, with the envelope that already passed the security review, and it adds no provider. B3 is the better end state for durability and should be the next design after B1 runs; it is a new generator, not a publishing feature. B2 cannot be recommended while its price, its resume time, its EU region and its crash behaviour are all unverified.

Open problem for any B option, to be designed before B starts: **a new version against old data.** Today a schema is created with `CREATE TABLE IF NOT EXISTS` at startup (`omni_prod/skills_runtime.py:754`). A republish that changes a table has no migration. Until that is solved, B republish must refuse a version whose schema differs from the live one, and say so.

### 3.3 The address

**First: an address on our domain** — `<name>.<sites-domain>`.

- **Use a separate registrable domain for customer sites, not `148ai.com`.** A customer page runs its own scripts in the visitor's browser. On a subdomain of our main domain it could read or set cookies scoped to the parent, and a phishing page there would damage the reputation of the address our own customers log in at. Asking for the sites domain to be added to the Public Suffix List, so browsers treat every `<name>` as a separate site, is the usual step — the process and timing are **not verified**.
- Needs from us, once: buy the domain; put it on Vercel's nameservers (wildcard requirement above); add `*.<sites-domain>` to the sites project. Certificates: one wildcard certificate covers every name, so a new site needs no issuance and no waiting.
- **Naming rules:** lowercase `a–z`, digits, hyphen; 3–40 characters; starts with a letter; ends with a letter or digit; no two hyphens in a row (this also excludes `xn--` names). Proposed from the business name by transliteration; the customer may edit it. Hebrew-letter addresses are out of slice 1.
- **Collisions:** the name is unique in the database (a unique index, not a check in code). The first to publish holds it. A taken name is never given, moved or overwritten; the customer is offered the closest free one.
- **A name stays with its owner while the site is down.** If it were released at once, anyone could publish a different page at an address people already know. How long it is held after the account closes is an owner decision (section 7).
- **Reserved names** (never given; the list is global data and is read from `main` or the database, never from a branch — `CLAUDE.md` §4): `www`, `app`, `api`, `admin`, `login`, `auth`, `account`, `pay`, `billing`, `checkout`, `mail`, `smtp`, `support`, `help`, `status`, `security`, `abuse`, `postmaster`, `legal`, `privacy`, `terms`, `static`, `assets`, `cdn`, `preview`, anything starting `prv-`, `148ai` and its look-alikes.
- **Abuse and phishing:** a second list of protected names (banks, government, payment and delivery brands, in Hebrew transliteration and English) blocks names that contain them; such a request goes to a person, not to an automatic "no". Every customer page carries a small "report this site" line that reaches us. Take-down is section 4.

**Second: the customer's own domain** — after slice 1.

- What Vercel provides: a domain is added to the shared project by API; each custom domain gets its own certificate, issued automatically, separate from the wildcard one (https://vercel.com/docs/platforms/multi-tenant-platforms/configuring-domains). If the domain is already used by another Vercel account, the customer must add a TXT record at `_vercel` to prove ownership (https://vercel.com/docs/domains/managing-dns-records). "Verified" proves ownership only; whether the domain actually points at us is a separate check (`misconfigured`), and the customer may be told "it works" only after that check (https://vercel.com/docs/platforms/multi-tenant-platforms/quickstart). Certificate success and failure arrive as webhooks (https://vercel.com/docs/webhooks/webhooks-api). Removal is two calls: from the project, then from the account (https://vercel.com/docs/platforms/multi-tenant-platforms/configuring-domains).
- What it needs from the customer: a change at the company where they bought the domain. The exact record values for a root domain and for a subdomain are **not verified**. This is the one step in the whole product that a person who "does not know what an app is" cannot do alone. Two honest ways: we buy and connect the domain for them (the registrar's programmatic purchase and its prices are **not verified**), or a person helps them once. Which one is an owner decision.
- The address on our domain keeps working and redirects to the customer's domain once it is connected.

---

## 4. Safety and law

### 4.1 What must be true before a page is public
Every check runs **on the snapshot bytes** — the bytes that will be served — not on the source and not on an earlier build's report. The snapshot's hash is stored with the result, and the server refuses to serve a snapshot whose hash has no passing result.

| Must be true | Exists today | Gap |
|---|---|---|
| Facts on the page are the facts the customer gave (phone, address, hours, name) | Fact canon from the approved request (`omni_prod/fact_canon.py:1-13`; `omni_prod/worker_tasks.py:1025-1030`) | Runs during the build on the build's page. Must run on the snapshot. It reads a 45,000-character window (`WAREHOUSE.md`, release table row 1), so a page with a large inline image can hide facts from it. |
| No invented testimonials or claims | One testimonial rule for generator and reviewer (#491, `a77c1b8`) | Same: must run on the snapshot. |
| Rights are clear (images, fonts, media, names) | `rights_clear` blocks release (`omni_prod/release_policy.py:241`; `omni_prod/rights_ip.py:259`); units `rights_font_source`, `rights_image_source`, `rights_media_source` (`omni_prod/skill_units/`) | Must run on the snapshot. |
| No secret in the page | units `secrets_*` (`omni_prod/skill_units/`) | Must run on every file of the snapshot. |
| Accessible | units `a11y_alt_text`, `a11y_contrast`, `a11y_focus`, `a11y_heading_order`, `a11y_labels` | **No accessibility statement page exists** (no match for "הצהרת נגישות" in `omni_prod`). |
| Privacy and terms pages | — | **Not found.** No generated privacy or terms page, and no "domain file" that defines them, was found on `origin/main`. |
| Contact details of the business on the page | Fact canon requires a phone or an address for a website (`omni_prod/fact_canon.py:428`) | Publishing must fail, not warn, when both are missing. |
| The page works | Acceptance on a running preview, `release_eligible` (`omni_prod/preview_repository.py:276-281`) | The version published must be a version with a passing report. |
| A shared address shows a title and description | `omni_prod/share_preview.py` (#480) | The address inside those tags must be the public address, not a preview address. |

Three gaps block slice 1 and belong in it: the accessibility statement, the privacy/terms pages, and the report line. Their text is a legal matter. Which Israeli requirements apply to a small business site (accessibility regulations, privacy law) is **not verified** and needs a lawyer; this document does not state the law.

### 4.2 Who is the publisher
Proposed position, to be confirmed by the owner with legal advice: **the customer is the publisher** of the site and is responsible for what it says; 148AI hosts it and may take it down. The customer agrees to this once, in plain words, at the first publish. Each published site names the business and its contact details (4.1). The footer line "נבנה ב-148AI" follows the plan's existing branding rule (`omni_prod/pricing.py:64`, `:94`).

### 4.3 Take-down
- Two different states: `unpublished` (the customer's own action; they can publish again) and `suspended` (ours; the customer cannot publish again until we lift it). Both stop serving within the cache lifetime (section 6, criterion 4).
- Every suspension records who, when, why and the evidence. The customer is told in plain words.
- A report from a visitor reaches a person. Until the owner sets a policy (section 7), the team suspends at once only for: impersonation of another business, collection of passwords or card numbers, and content that is plainly illegal; everything else waits for the owner.

### 4.4 The EU region
- The database is in AWS `eu-central-1` (`docs/DB_TARGETS.md:20`). The worker host's home region is Frankfurt (`infra/worker-host/README_HE.md:15`). The control-plane function has no region set (`vercel.json`), and Vercel's default is `iad1` (https://vercel.com/docs/project-configuration/vercel-ts) — this mismatch is warehouse item 100 (`WAREHOUSE.md`, row 100). The word "Frankfurt" is not written in that row; the brief for this document states the decision as Frankfurt, and this design follows it.
- For publishing: the sites project is pinned to Frankfurt; snapshots are stored in an EU location; for tier B, product data and its copies stay in the EU. Vercel's Frankfurt region identifier, Blob store regions (default `iad1`, https://vercel.com/docs/cli/blob) and R2's location options are **not verified**.
- A CDN copies public pages to edges outside the EU. For tier A that is public content with no visitor data. Server logs with visitor IP addresses are personal data; where Vercel keeps them is **not verified**.

---

## 5. Data model and API sketch

**Proposal only. No migration is written. A schema change needs the owner's explicit approval (`AGENTS.md`; `CLAUDE.md` §5).**

### 5.1 Tables

`published_sites` — one row per site address.

| Column | Meaning |
|---|---|
| `id` | `site_<hex>` |
| `project_id` | the project; one live site per project in slice 1 (unique) |
| `account_id` | the owner |
| `name` | the address label; **unique index**; immutable after first publish in slice 1 |
| `state` | `draft`, `published`, `unpublished`, `failed`, `suspended` (CHECK) |
| `live_release_id` | the release visitors see; NULL unless `published` (CHECK ties the two) |
| `tier` | `content` or `app` |
| `terms_accepted_at`, `terms_version` | the publisher agreement (4.2) |
| `suspended_reason`, `suspended_by`, `suspended_at` | take-down record |
| `created_at`, `updated_at` | |

`site_releases` — one immutable row per publish attempt that produced a snapshot.

| Column | Meaning |
|---|---|
| `id` | `rel_<hex>` |
| `site_id` | |
| `version_id`, `repository_sha256` | the approved version and its content hash (`project_versions`) |
| `snapshot_key`, `snapshot_sha256` | the manifest in object storage (`sites/<sha256>/manifest.json`) and its hash; the manifest lists every file with its own hash, size and content type |
| `gates` (JSONB) | every check of 4.1: name, result, detail, the snapshot hash it ran on, the fact-canon hash |
| `status` | `READY`, `REJECTED` (a gate failed), `FAILED` (we failed) |
| `requested_by`, `requested_at` | who pressed the button, on which version |
| `idempotency_key` | unique per site |
| `went_live_at`, `retired_at` | |
| `live_check` (JSONB) | after going live: the address fetched, status, hash of the bytes received (section 6, criterion 1) |

`site_events` — append-only audit: `published`, `republished`, `unpublished`, `rolled_back`, `suspended`, `restored`, `name_refused`, `publish_rejected`, `publish_failed`; with actor, time, release id, detail.

`site_reserved_names` — the reserved and protected lists of 3.3, so they are global data and not a branch's constant.

The existing `deployments` table (`infra/postgres/001_control_plane.sql:17-29`) is left as it is. It has no name, no state and no gate record, and it requires a `build_id`; extending it would change a table two other modules write. This overlap is reported, not resolved here.

### 5.2 Endpoints (control plane, owner-authenticated like the preview endpoints, `omni_prod/investor_app.py:3008-3014`)

| Call | Does |
|---|---|
| `GET /api/v28/projects/{project_id}/site` | state, address, live version, whether unpublished changes exist, the suggested name when `draft` |
| `POST /api/v28/projects/{project_id}/site/name-check` | `{name}` → free / taken / not allowed, and the closest free name. Reserves nothing. |
| `POST /api/v28/projects/{project_id}/site/publish` | `{version_id, name?, accept_terms?}` + `Idempotency-Key`. `202` with a release id. |
| `GET /api/v28/projects/{project_id}/site/releases/{release_id}` | progress and result, with the customer-language reason on `REJECTED` |
| `POST /api/v28/projects/{project_id}/site/unpublish` | stops serving; keeps the name |
| `POST /api/v28/projects/{project_id}/site/rollback` | `{release_id}` → an earlier `READY` release becomes live (same switch as publish; no new snapshot) |
| `POST /internal/sites/{site_id}/suspend`, `/restore` | operator only; reason required |

Sites project (public, no authentication, no account data): `GET` and `HEAD` on any path of `<name>.<sites-domain>`. Any other method answers `405`.

### 5.3 States

```
draft ──publish ok──▶ published ──unpublish──▶ unpublished ──publish ok──▶ published
  │                      │  ▲                                    
  └─publish fails─▶ failed  └── publish fails: stays published, release FAILED/REJECTED
any ──operator──▶ suspended ──operator──▶ unpublished
```

- `failed` is only "the first publish did not succeed". A failed republish never leaves `published` (2.1 item 6).
- A state not in the list is an error, not a default.

### 5.4 The publish sequence
1. Lock the site row. Check owner, version belongs to the project, state allows it, terms accepted.
2. Claim the name (insert under the unique index). A conflict ends here with "taken"; nothing else was written.
3. Produce the snapshot (3.1) on the worker. Check eligibility.
4. Run the gates of 4.1 on the snapshot bytes. Any failure → release `REJECTED`, reasons stored, live pointer untouched.
5. Store files and manifest by hash. Read the manifest back and compare its hash.
6. One transaction: retire the current live release, set `live_release_id`, state `published`, write the event. The transaction asserts the previous `live_release_id` it read in step 1.
7. Clear the address from the cache. Fetch the public address from outside and compare the hash of what arrived with the manifest. A mismatch → the same transaction in reverse, release `FAILED`.

### 5.5 Idempotency
- The same `Idempotency-Key` for the same site returns the same release and does no work twice, like the build request rule (`infra/postgres/040_build_request_idempotency.sql`).
- Publishing the version that is already live returns the live release.
- Steps 5–7 are safe to repeat: files are addressed by hash; the pointer switch is conditional on the old value.
- Two publishes at once for one site: the row lock serialises them; the second sees the first's result.

### 5.6 What is recorded as evidence, per release
Version id and hash; snapshot manifest hash and each file's hash; each gate with its result and the hash it ran on; the fact-canon hash; who pressed and when; the terms version accepted; the live check (address, status, received hash, time); every state change in `site_events`. A release with any of these missing is not `READY`.

---

## 6. Acceptance criteria for slice 1 (tier A on our domain)

Each is an observable test on the real path: the real endpoints, the real worker, the real object store, the real sites project, read from outside over HTTPS. A double that stands in for the router, the store or the gates does not count (`AGENTS.md`, seam rule).

1. **The address serves the approved version, byte for byte.** Publish version V of a content site. Fetch `https://<name>.<sites-domain>/` from a machine outside our network. The SHA-256 of the body equals the manifest's hash for `/`, and the manifest belongs to a release whose `version_id` is V.
2. **A later version does not leak.** Create version V2 in the workspace without publishing. The address still returns V's bytes. Then publish V2; it returns V2's bytes.
3. **It stays up without us.** With the build worker, the preview worker and the preview router stopped, the address still answers 200 with the same hash. 25 hours after publishing (longer than any preview TTL), the same.
4. **Unpublished means not served.** After `unpublish`, the address returns the "not available" page with status 404 — from two different networks — within 60 seconds (**estimate**; the bound becomes the tested number). No snapshot byte is served after that.
5. **Republish returns at the same address.** After 4, publish again: same address, 200, the hash of the release just published.
6. **A taken name is never overwritten.** Account A publishes at `name`. Account B publishes with the same `name`: B gets "taken" and a suggestion; A's address returns A's bytes with A's hash before and after; no row of A changed. Two simultaneous first publishes for one free name: exactly one succeeds.
7. **The address shown is the address served.** The address in the success message, the address in the API response and the address in the page's share tags are the same string, and fetching that exact string returns the release's bytes.
8. **A page that fails the truth gate is not published.** Take a real production build row (read-only, fingerprint checked), change the phone number in the page so it differs from the fact canon, publish: the release is `REJECTED`, the customer reads the reason in plain words, the address returns what it returned before (or "no site" on a first publish), and no snapshot of the rejected page is reachable at any address.
9. **Every other gate of 4.1 blocks the same way** (rights, secrets, missing contact details, missing accessibility statement, missing privacy page): one test each, same shape as 8.
10. **A failed publish changes nothing.** Make the store refuse writes during step 5 of a republish: the address returns the previous release's hash; state is `published`; the release is `FAILED`; the customer reads the "exactly as it was" sentence.
11. **Reserved and protected names are refused**, including with different letter case and with a trailing dot.
12. **A site with visitor data cannot take this path.** A version with a form that posts to its own address, or whose two reads differ, is refused with the tier B sentence; nothing is served.
13. **Idempotent.** The same request sent three times produces one release, one snapshot, one `published` event.
14. **Suspension.** An operator suspends: the address stops within the same bound as 4; the customer's publish is refused with a plain sentence; the event carries actor and reason.
15. **No generated code runs for a visitor.** During 100 fetches of a published site, no container is started on any host (observed from the Docker event stream), and the sites project holds no credential for the control-plane database beyond read access to the two sites tables.
16. **Zero technical terms.** The strings of 2.2, in Hebrew and English, contain none of the banned words; checked against the shipped UI text.
17. **Evidence is complete.** For the release of criterion 1, every item of 5.6 is present and the hashes agree with each other.

**Mutations that must be caught** (`tests/negative_controls/publish_site.json`, run by `scripts/run_negative_controls.py`; database-backed ones carry `"envs": ["pg"]`). Each names the criterion that must turn red:

| # | Mutation | Caught by |
|---|---|---|
| M1 | Publish serves the project's newest version instead of the approved one | 1, 2 |
| M2 | The router ignores `state` and keeps serving an unpublished site | 4, 14 |
| M3 | The name claim is an upsert: a second account's publish replaces the first | 6 |
| M4 | The truth gate's result is ignored (or it runs on the source instead of the snapshot, and the snapshot differs) | 8 |
| M5 | The address shown is built in the browser from the typed name and differs from the name stored | 7 |
| M6 | A failed republish clears the live pointer | 10 |
| M7 | The cache is not cleared on take-down and has a long lifetime | 4 |
| M8 | The live check after publish is skipped or its mismatch is ignored | 1, 17 |
| M9 | The reserved list is read from the branch, or compared case-sensitively | 11 |
| M10 | The eligibility check trusts `static_content_site` alone | 12 |
| M11 | A repeated request creates a second release | 13 |
| M12 | An unknown `state` value is treated as `published` | 4 |
| M13 | The two-read comparison is skipped, so a page with a changing value is frozen | 12 |

Not in slice 1: the customer's own domain; tier B; Hebrew-letter addresses; changing a name after publishing; more than one site per project; visitor statistics.

Work this slice touches that is already promised elsewhere (`CLAUDE.md` §7.2, reported in advance): warehouse **118** (images as files) changes `omni_prod/workspace.py:145-155` and `omni_prod/preview_runtime.py:358`, which the snapshot step reads; a snapshot must store bytes, and a version stores only text. If 118 lands first, the snapshot reads real image files; if not, slice 1 stores the bytes the running site returns and does not need 118. Warehouse **100** (function region) decides the region setting the sites project copies.

---

## 7. Decisions the owner must make

Each has a recommendation. The team follows the recommendation until he answers, except where it says "waits".

| # | Decision | Recommendation |
|---|---|---|
| 1 | **Which domain carries customer sites.** | A new, short, separate domain bought for this purpose, not `148ai.com`. Buying it is a purchase: **waits** for him. Until then slice 1 is built and tested on a throwaway name. |
| 2 | **A second Vercel project for customer sites (A1), or the worker host (A2).** | A1. Creating the project is new infrastructure: **waits** for his yes. |
| 3 | **The schema of section 5.** | Approve the four tables as proposed. No migration is written before that. |
| 4 | **Price and limits per plan**: how many live sites, whether Free may publish, whether the "built with 148AI" line can be removed, traffic limits. | Free: one live site, with the line, on our domain. Paid plans: more sites and removal of the line by the existing branding rule (`omni_prod/pricing.py:64`). No traffic limit until there is a measured cost. All numbers are his. |
| 5 | **Take-down policy**: what we suspend without asking, who decides the rest, how fast, whether the customer is told first. | Section 4.3: suspend at once for impersonation, credential or card collection, plainly illegal content; everything else goes to him. |
| 6 | **Who is the publisher, and the words the customer agrees to.** | The customer is the publisher; 148AI hosts. The text needs a lawyer: **waits**. |
| 7 | **The legal pages**: is an accessibility statement and a privacy page required on every published site, and who writes the template. | Yes to both on every site, from one template per language, filled from the fact canon. The template text **waits** for legal advice. |
| 8 | **How long a name is held** after a site is taken down, and after an account closes. | Held as long as the account exists; 12 months after it closes. |
| 9 | **Do apps with data wait for tier A?** | Yes. Until tier B exists the customer of an app reads the honest sentence of 2.2 and keeps the private preview. |
| 10 | **Tier B direction**: our own apps host (B1) now and a Postgres-based generator (B3) later, or wait for B3. | B1 after tier A, designed in its own document, starting with the data-copy test. |
| 11 | **The customer's own domain**: do we buy it for them, or help them connect one they bought. | Buy it for them, as a paid add-on, after slice 1. Needs price verification. |
| 12 | **EU region for the sites project and the snapshots.** | Frankfurt, as already decided for warehouse 100. |

---

## 8. What was not verified

Platform facts:
1. Vercel: the number of domains one project may hold, per plan; wildcard domain pricing.
2. Vercel: maximum function duration per plan; function response-size limit; cold-start time of a Python function.
3. Vercel: CDN cache lifetime rules and purge-by-tag behaviour and timing.
4. Vercel: the DNS record values a customer sets for a root domain and for a subdomain.
5. Vercel: Blob pricing, size limits, EU store regions; whether a Blob store can sit behind our own address.
6. Vercel Sandbox: pricing; resume time; whether Frankfurt is an available region; what is lost when a sandbox dies without a clean stop. The 45-minute and 24-hour session caps and the 10-sandbox concurrency figure come from two integration pages, not from the limits page.
7. Vercel: project-count limits and cost for one project per site (A3); programmatic domain purchase and prices.
8. Vercel: where request logs with visitor IP addresses are stored.
9. Cloudflare R2: prices, location options, public serving. No R2 page was read.
10. Caddy on-demand certificates and the certificate authority's rate limits (relevant to A2). No page was read.
11. Neon: whether 148AI is or can be enrolled in the Agent Plan; the limits quoted are that plan's.
12. Public Suffix List: process and timing.
13. WhatsApp's share-link format.
14. All Vercel pages were read as excerpts through a third-party index, not as full pages; `vercel.com` could not be fetched from this session.

Our own system:
15. The "content route" (a deterministic page from a content document) and the "domain file" (privacy/terms per domain) named in the brief were not found on `origin/main` at `a77c1b8`.
16. Whether the preview data directory on the worker host is backed up.
17. Whether a record of "the customer approved this built version" exists. `build_approvals` records approval of the request before a build (`infra/postgres/030_project_briefs_and_approvals.sql:42-57`). This design defines approval as pressing Publish on a named version.
18. That "Frankfurt" is recorded as the decision for warehouse 100: the row does not contain the word.
19. No test was run, no browser was opened and nothing was deployed for this document. Every cost and time figure is an estimate.

Law:
20. Which Israeli accessibility and privacy requirements apply to a small business site, and what the publisher agreement must say. Not legal advice.
