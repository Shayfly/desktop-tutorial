# site_auth_v2 — hardened sign-in in built products

Work order 001 (Michael 2026-11-10), mapped to this codebase. Draft PR #292. Flag `site_auth_v2`, read only in
`omni_prod/feature_flags.py`, default off.

## Decisions (recorded, owner-approved 2026-11-10)
- **Identity per site.** No central identity service, no production migration. "Sign in with a 148AI account" stays
  a later option.
- **scrypt, not Argon2id, for now.** The preview runtime is stdlib-only (founder decision 2026-10-07 #25); Argon2id
  needs `argon2-cffi` in the allowlist and the preview image (an infrastructure change, after the frozen run).
  Parameters: `n=2**16, r=8, p=1, dklen=64, salt 16 bytes`, stored as `scrypt$65536$8$1$<salt>$<hash>`; verification
  reads the parameters from the string.
- **Sign-up answers 409 for an existing e-mail.** Without e-mail sending, "200 always" would be a lie. Consequence,
  stated in the product's privacy note: sign-up reveals whether an account exists for an e-mail. Login and reset do
  NOT reveal it (one error text; reset always 202).
- **`__Host-` / Secure cookies on loopback.** Browsers treat `http://127.0.0.1` / `localhost` as a secure context;
  the acceptance checker does the same (`_LoopbackSecurePolicy`), so a correct product does not fail on environment.
  Fixture: `test_secure_host_cookie_is_returned_on_loopback`.
- **Rate limit per client, not per proxy.** The client is the first `X-Forwarded-For` address only when the direct
  peer is in `TRUSTED_PROXIES` (default `127.0.0.1,::1`). Each check uses its own documentation-range client address,
  so buckets never leak between checks.

## What the flag turns on
skill `skill.site_auth` (guidance + probe `_auth_source_rules`); the hardening checks appended to the shipped runner
(cookie flags, rotation, server-side logout, uniform error, 429 on the 6th login, per-client counting); the sign-in
form in a real browser at 320px / 140%.

## Identity (with the flag off)
`.github/workflows/identity.yml`, from a worktree of the baseline, same interpreter:
- behavioural digest (prompts, skills, probes, sandbox scripts, arm-brief derivations) equal;
- source identity: the gate closure (imports AND Python files named in string literals) compared as ASTs after
  removing only flag blocks and declared `_FLAG_ONLY` names; every non-Python input compared as bytes; the stripped
  amount reported (above 8 names or 250 lines: a warning to read it by eye);
- additive only: every line deleted from the baseline is declared in `docs/identity/allowed-deletions.json`.

## Merging on 13.11 (the gate freeze)
The `freeze` job fails on #292 by design, and the merge is NOT a silent override. Michael's order constraint
(2026-11-10): the freeze comes off, #292 merges immediately, the freeze restarts from the new SHA, and no other PR
lands in between. A separate freeze-off PR cannot guarantee that -- between it and #292, main would sit unfrozen.
So #292 itself carries the freeze change, and there is never a moment with the freeze off:

Michael's merge order of 2026-11-10 22:07 supersedes the 13.11 date: merge now, the 5-arm frozen run (flag
off) executes on the merged tree right after. His correction is also in: the new freeze cannot pin the merge SHA
(it is written before the merge exists), so it pins the FINAL BRANCH CONTENT COMMIT and the merge SHA goes in the
external run report only.

1. ONE closing commit on #292 rewrites `docs/gate-freeze.json`: `"active": true`, `"starts": "merge of PR #292"`,
   `"baseline"` = the FINAL branch head (corrected to e196a92 before arm 1: commits after the closing commit move the head, so the pin is set last and verified tree-identical to the merge), valid until the END of frozen-run arm 5 with 72h as a backstop. The freeze check passes a PR that
   changes the definition itself (logged as `::notice ... a reviewed decision`) -- the only sanctioned way through,
   which is why this commit needs the approval on record: the rewrite is a baseline deletion, declared and signed
   by a reviewer in `docs/identity/allowed-deletions.json` like any other.
2. Precondition, not a check: `git log <closing-commit>..origin/main` must be EMPTY. Non-empty means main moved and
   the pinned-baseline comparison is no longer against the tree being merged -- stop and re-run the regression.
3. #292 merges with a MERGE COMMIT, never squash: a squash drops the branch commits from main's history and the
   pinned baseline SHA would dangle in fresh clones; a merge commit keeps it an ancestor of main forever. From that
   instant the new freeze definition is on main and any PR touching a gate file is blocked again. Old freeze until
   the merge, new freeze from the merge: no gap, no PR in between by construction.
4. The merge commit SHA, the CI run, the identity annotations and the new freeze window go in the run report; then
   the 5 arms run. `BASELINE_SHA` in identity.yml stays 2c1d6cb through this merge (flag off, #292 IS that
   baseline -- the identity job proves it); the first gate PR after the new freeze moves it forward to the pinned
   commit, with its own reviewed declaration.
