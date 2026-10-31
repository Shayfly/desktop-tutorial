# #131: JSON prefix policy and credential-safe suffix evidence

## Decision

Leading prose remains rejected, including `Here is the JSON:` and `הנה ה-JSON:`.
Only whitespace/BOM and the existing complete Markdown envelope are removed.
The parser does not search arbitrary prose for a brace: that can select an example
or an unrelated value rather than the requested answer. Tail prose is different:
it follows a value already decoded at the start of the recognized envelope.
This PR retains the existing tail classifications and acceptance policy.

`leading_chars=57` on the failing fixture was not a model response with a JSON
prefix: that fixture was changed to `not json <synthetic credential> trailing`
and contained no JSON value. Replacing a trailing-content fixture with this input
removed the code path that populates `trailing_starts`. The corrected fixture is
a valid first object followed by a conflicting second object containing the marker.
It exercises a real rejected suffix under the new contract.

## Suffix evidence and redaction

`tail_raw_utf8_b64` is retained. It contains the UTF-8 suffix after the existing
credential redaction layers, encoded as Base64. `tail_raw_redacted` identifies
whether the parser changed this text. Non-sensitive bytes are preserved subject
to the existing redaction policy, including its long-token filter. Length and span
fields continue to describe the original response; redacted text can differ in length.
The existing rejection `raw_sha256` continues to identify the original response.
This is credential-safe evidence, not an unredacted credential archive.

The parser redacts before encoding. The persistence boundary also decodes this
field, applies the same redaction layers, and re-encodes it. It must not apply a
long-token regex directly to the encoded string: that destroys valid Base64 and
loses the retained suffix evidence. Other diagnostic text fields keep their
existing recursive redaction. No general redaction pattern is weakened.

`EveryPersistedTextFieldIsRedacted.assert_absent` now recursively inspects decoded
`*_b64` fields as well as serialized text. Base64 is reversible encoding, not
redaction: substring checks on serialized JSON cannot find an encoded credential.
Invalid Base64 also fails the check. A negative-control test supplies an encoded
synthetic credential and proves the assertion rejects it. Parser regressions cover
prose, conflicting JSON, and malformed JSON tails containing the same marker.

## CI diagnosis before changes

Examined head: `e83feab350e8fbee54fb7514207c7b93b37eb283`.

- v24-ci run `40191681365`, test job `121163808400`: 2 failed, 1994 passed.
- Direct failure: `EveryPersistedTextFieldIsRedacted.test_trailing_excerpt_is_redacted_in_the_stored_object`, missing `trailing_starts`.
- Second failure: `AcceptanceW.test_W_every_non_fastapi_test_module_passes`, because its subprocess runs the same failing test.
- V11 Overlay CI run `40191681433`, validate job `121163808413`: the same direct failure and AcceptanceW wrapper failure.

These logs establish the observed failures. The encoded-secret problem is an
additional genuine defect exposed by strengthening the tests, not the assertion
reported by that CI run. Both defects are addressed without changing CI workflows.

## Verification before push

- `python -m unittest tests.test_model_json_parsing tests.test_t3_json_no_silent_trailing tests.test_t3_rejected_json_durable -v`: 36 tests, OK, including char 7807.
- `python -m compileall -q omni_prod tests` and `git diff --check`: exit 0.
- Full local pytest on the final code: 1998 passed, 187 skipped, 411 subtests passed; AcceptanceW failed because its subprocess hit `TimeoutExpired` in `tests.test_reservation_worker_sigterm.SigtermTests.test_sigterm_during_the_sleep_exits_0_within_seconds`. No parser/redaction test failed. No signal-handling code or test timeout was changed.
- Fresh `python -m pytest -q tests/test_reservation_worker_sigterm.py tests/test_m4_acceptance.py::AcceptanceW::test_W_every_non_fastapi_test_module_passes`: 3 passed in 103.42s, including the complete non-FastAPI subprocess suite. The earlier timeout did not reproduce in this recheck; its underlying cause is not established.
- Local V11 network-namespace execution is unavailable (`unshare: Operation not permitted`); its authoritative result must come from head CI. The isolation gate was not bypassed.
- Independent read-only diff review: no critical or important findings. Separate direct invocation of `redact_fields` with an unredacted encoded synthetic credential passed (decoded credential removed and Base64 retained).

Approval remains conditional on green head CI and the founder's own run with zero failures and zero errors. Nothing is merged by this change.


## Focused follow-up, 2026-10-25

Owner decision LANG-001 corrects the product record to every language; #131 remains parser-only. Syntax-based tail classification accepts Arabic, Japanese, Russian and Hebrew prose without an alphabet allowlist. Leading prose is rejected by the same diagnostic condition in every language. The gateway's rejection includes a concise schema-format correction and explicitly preserves the requested content language. `trailing_starts` is retained, alongside `tail_class`; no replacement or alias is needed. Its consumers remain the durable diagnostic redaction path and T3 tests.

The separately authorized SIGTERM **test-only** change increases scheduling allowance from 5 to 30 seconds, adds bounded phase reads, and replaces the mid-pass timed sleep with a parent-controlled stdin barrier. A wrapper observes the real production signal handler; the parent releases the current pass only after the handler completes. OS SIGTERM, graceful exit code 0, pass completion and pool cleanup remain asserted. No intake/worker implementation is changed. Twenty repeated executions of both tests: 40 tests passed in 4.635s. This is evidence of these runs, not proof against arbitrarily long scheduler starvation.

Final follow-up validation before push: `python -m pytest -q --junitxml=/tmp/131-language-final.xml` completed with **2001 passed, 187 skipped, 420 subtests passed, 0 failed, 0 errors**, in 201.87 seconds. One upstream Starlette deprecation warning remains. The prior timeout did not recur. Focused parser/durability/SIGTERM suite: 40 tests, OK. Independent read-only follow-up review found no critical or important issue. The owner explicitly authorized publication and auto-merge of #131 after green CI on 2026-10-25; the earlier approval condition above is superseded for this PR by that instruction.
