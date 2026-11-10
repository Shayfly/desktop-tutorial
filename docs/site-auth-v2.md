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

1. After 13.11 17:52: gate regression on the tip of main (both approved builds pass, `self_check` green), the tip
   SHA is recorded as the final baseline, and the frozen run (5 arms, flag off) runs against it.
2. With Michael's explicit approval, ONE closing commit on #292 rewrites `docs/gate-freeze.json`:
   `"active": true`, `"starts": "merge of PR #292"`, 72h, reason pointing at the frozen run's report. The freeze
   check passes a PR that changes the definition itself (logged as `::notice ... a reviewed decision`) -- that is
   the only sanctioned way through, which is why this commit needs the approval on record.
3. Before pressing merge: `git log <final-baseline-SHA>..origin/main` must be EMPTY. If anything landed, main moved
   since the frozen run -- go back to step 1. Then #292 merges (squash); from that instant the new freeze definition
   is on main and any PR touching a gate file is blocked again. Old freeze until the merge, new freeze from the
   merge: no gap, no PR in between by construction.
4. The merge commit SHA, the CI run, the identity annotations and the new freeze window go in the run report.
