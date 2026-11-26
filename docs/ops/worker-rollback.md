# Worker rollback (fix forward to the old behaviour)

Found by the release review of 2026-11-26: there was no worker rollback that could pass CI. This page is the procedure.

## Why a rollback is a PR on main

- `deploy-worker.yml` deploys only `main`: the push trigger is `branches: [main]` (line 24), and a manual run with any
  other ref is refused (lines 66-72, "Manual deployments for this experiment must use main"). The checked-out ref is
  the pushed or selected branch (line 76). The deploy job runs only on a release (`scripts/release_gate.py`, line 54):
  a push whose head commit title ends with `[release]`, or a manual run.
- So rolling the worker back means putting the old code on `main` and releasing it. Nothing runs an older commit.
- A plain `git revert` of the release does not pass:
  - it reverts `docs/identity/allowed-deletions.json` and `docs/identity/allowed-identity-changes.json` too. Their
    record counts drop, and CLAUDE.md section 8 treats a drop as a stop;
  - the release moved the flag-off pipeline digest A -> B. The rollback moves it B -> A, and A is already the
    `to_digest` of the entry that introduced A. Until 2026-11-26 `scripts/identity_declared.py` refused the whole file
    when a `to_digest` repeated ("to_digest declared more than once").

## The rule that makes it declarable

`scripts/identity_declared.py` accepts an explicit revert entry. Tests: `tests/test_identity_declared.py`, class
`RevertEntries`. Negative controls: NC6-NC20 in `tests/negative_controls/identity_declared.json`.

- The entry carries `"revert_of": "<id>"`. The value is the id exactly, with no surrounding white space, and it names
  exactly one entry that stands **earlier in the file** (above the revert).
- The named entry is itself valid: signed, and, if it is a revert too, the exact revert of its own target.
- `from_digest` / `to_digest` are that entry's `to_digest` / `from_digest` (swapped).
- `added` / `removed` are that entry's `removed` / `added`; `changed` and `data_changed` are equal to its own.
- It is signed like any entry (reviewer rules unchanged, CLAUDE.md section 8).
- Only such an entry may repeat a `to_digest`. The file is read from the top. A plain entry that repeats any
  `to_digest` above it, a revert's included, refuses the whole file. So do a repeat without `revert_of`, a
  `revert_of` naming no entry or a later one, other digests, and other path sets.
- One entry is reverted at most once. A reverted entry is consumed and never matches again, and only an exact revert
  consumes. Re-landing the reverted change later needs its own entry, with `revert_of` naming the revert.

Remaining risk: the check proves that a revert is the exact swap of a signed entry in the file. It cannot prove that
the entry describes a release that really happened. An author and a reviewer who both sign could declare a made-up
target and its revert together. The reviewer's signature on both entries is the only control there.

### When the revert entry is needed, and when it cannot help

- `identity_declared.py` decides only when `identity.yml` runs in blocking mode (lines 52-60). Blocking mode means
  the gate freeze is active (`docs/gate-freeze.json`), or the PR touches one of `SITE_AUTH_FILES`. Lines 103-112 run
  the check only when the digest differs and the job blocks. Otherwise a digest change is published as a notice and
  does not block, so the PR passes without the entry. Add the entry anyway: whether the job blocks is only known when
  CI runs, and the entry records the rollback.
- The entry declares B -> A, where B is the `to_digest` of the reverted entry. It works only while main's digest is
  still B, that is, while R is the latest change of the flag-off pipeline.
  - A rollback across two releases (C -> A) matches no single entry.
  - Neither does a rollback after any later digest change on main.
  - Both need their own plain, signed entry for the actual change. Its `to_digest` then repeats one already in the
    file, which the rule refuses. That case is not solved here: stop and ask the owner.

## Procedure

Let R be the release to undo, `PRE` the main commit just before R merged, and E the identity entry R added (A -> B).

1. **Branch from current main** (CLAUDE.md section 2.7: check `git merge-base HEAD origin/main`).
2. **Restore the pre-release content of the code files, not the declaration files.**
   - For every path R added: `git rm`. For every path R modified: `git checkout PRE -- <path>`.
   - Leave out `docs/identity/allowed-deletions.json` and `docs/identity/allowed-identity-changes.json`. They only
     grow.
   - Leave out shared state and evidence (`STATUS.md`, `TASKS.md`, `DECISIONS.md`, `docs/evidence/**`, `smoke/**`).
     Record the rollback there as a new entry instead.
   - **Keep every migration file R added.** Migrations are additive, and the old code runs against the newer schema
     (`infra/worker-host/recover.sh`, header).
   - If the restored package is older than the database, the strict migration step fails. The deploy has already
     drained the workers: `drain` (line 213) runs before `migrate` (line 219). The recovery step then restores
     `omni-rollback/<svc>:prev`, which are the images of the release being rolled back. The run is red, and the
     worker is back on the code you wanted to remove.
   - If a migration file must go anyway, do not rely on the push. Run deploy-worker by hand on `main` with
     `accept_newer_migrations` set to the exact versions (input at lines 14-17, used at lines 216-230).
   - Check: `OMNI_SITE_AUTH_V2=0 python3 -m omni_prod.pipeline_identity` prints A, the `from_digest` of E.
3. **Declare every deleted line with a signed record.** Restoring code deletes lines. Each file with deletions against
   main needs a record in `docs/identity/allowed-deletions.json`, bound to its digest:
   `python3 scripts/deletions_declared.py origin/main --digest <path>`. The reviewer signs (CLAUDE.md section 8). The
   number of records only goes up, by exactly the number added. Also run
   `python3 scripts/weakening_declared.py origin/main` for any test line the restore brings back.
4. **Add the revert identity entry at the END of `changes`** in `docs/identity/allowed-identity-changes.json`.
   Placing it at the end puts the revert below its target and below the entry that introduced A. The last entry's
   `}` gains a comma; git shows that as an added line, but if `deletions_declared.py` lists the file, declare it as
   in step 3.
   ```json
   {"id": "<E.id>-revert", "revert_of": "<E.id>", "from_digest": "<B>", "to_digest": "<A>",
    "added": <E.removed>, "removed": <E.added>, "changed": <E.changed>, "data_changed": <E.data_changed>,
    "reason": "...", "author": "...", "reviewer": "shai", "reviewed_at": "YYYY-MM-DD", "signature_note": "..."}
   ```
   Check it with the manifests of main (B) and the branch (A):
   `python3 scripts/identity_declared.py B A base-source.json head-source.json`. It must print
   `identity change declared::<E.id>-revert (revert of <E.id>)` and exit 0.
5. **Guards** (exit 0): `python3 scripts/deletions_declared.py origin/main`,
   `python3 scripts/weakening_declared.py origin/main`, `python3 -m omni_prod.system_map --check`.
6. **PR with `[release]` at the end of the title.** It goes through the normal approval and green CI on the exact SHA
   (CLAUDE.md section 2).
7. **deploy-worker rolls forward to the old behaviour** on the merge push, like any release.

Simulated on 2026-11-26 in a scratch clone, for the sites bundle (E = `sites-bundle-2026-11-26`, f2fd495d ->
fd3a45bf). E exists only on the branch `claude/practical-hopper-oi3qj2-sites-bundle` (1d84272), not on main: the
simulation took that branch as the released main.

- Restoring 33 added and 61 modified paths gave digest f2fd495d, with a source manifest byte-equal to main's.
- With the revert entry appended at the end of `changes`, `identity_declared.py` exited 0.
- Without `revert_of`, it exited 1: `to_digest declared more than once: f2fd495d7d48`. The main script of cb403c0
  gives the same result even with `revert_of`.
- With the revert placed at the top, above its target, it exited 1 as well.
- The deletion guard then listed the 94 files with deleted lines that step 3 declares.

## Automatic recovery inside one deploy

This is for a deploy that fails partway. It is not a rollback of a release that deployed successfully.

- **Snapshot before the build.** Lines 116-121 run `infra/worker-host/snapshot-rollback.sh`, which tags every running
  consumer as `omni-rollback/<svc>:prev` before `docker compose build` (script lines 2-13: tag, commit, or rebuild
  from the running container's revision, accepted only when three code hashes match). `drain.sh` (lines 29-62)
  records the same images when it stops the consumers.
- **Restore on failure.** Steps `drain` (line 213), `migrate` (219), `start` (233) and `listen` (259) are watched by
  the step at lines 276-281. On `failure()` of any of them, it runs `infra/worker-host/recover.sh`. That script
  starts each recorded service from `omni-rollback/<svc>:prev` (`up -d --no-build --no-deps`, line 42) and checks that
  each one runs and that the worker logs `Listening on`. It never touches the database or volumes. The run stays red.

## Vercel (web)

- Vercel production builds only on a release (`scripts/vercel_ignore_build.mjs`, lines 6-10). Production then stays
  on the last released deployment.
- To roll the web back, promote the previous production deployment: dashboard (Deployments, Instant Rollback),
  `vercel rollback <deployment-url-or-id>`, or `POST /v1/projects/{projectId}/rollback/{deploymentId}`. It switches
  routing without a rebuild. On the Hobby plan only the immediately previous production deployment can be the target.
  `vercel promote <deployment>` undoes the rollback. (Source: vercel.com/docs/deployments/rollback-production-deployment,
  read 2026-11-26.)
- This does not move the worker. Roll both back together when a release changed both.
