# E1 contract migration — S1 (INCOMPLETE: raw grep and test execution pending)

## Contract (before → after)

- Before: `tail after the first JSON object => verdict=rejected => complete_json raises ModelGatewayError`.
- After: `tail => verdict=accepted_with_unexplained_tail => complete_json succeeds; the full tail is recorded`.
- Invalid first object still rejects. An unexplained tail is **not** a known envelope.

## Scope search — GitHub indexed search, NOT grep

A local `grep -rn` of the **complete** repository could not be executed in this environment: the repository is not mounted and GitHub DNS access from the execution container fails. The connector's indexed search is on the default branch (main), **not this PR branch**. These results are navigation evidence only, not complete raw grep evidence.

Commands required to close this S1:

```bash
grep -rnE 'parse_model_json|content after the first JSON value|content before the JSON value|verdict|rejected_json|rejected_model_json|tail_status|trailing_chars|assertRaises\(ModelGatewayError\)' omni_prod tests > e1-contract-grep.txt
cat e1-contract-grep.txt
```

### Indexed search matches relevant to the contract (2026-10-23)

| Search | Located paths (non-exhaustive) |
|---|---|
| parse_model_json | omni_prod/model_gateway.py; tests/test_t3_json_no_silent_trailing.py |
| content after the first JSON value | omni_prod/model_gateway.py; tests/test_t3_rejected_json_durable.py; tests/test_t3_json_no_silent_trailing.py |
| content before the JSON value | omni_prod/model_gateway.py; tests/test_t3_json_no_silent_trailing.py |
| verdict | omni_prod/model_gateway.py; tests/test_t3_json_no_silent_trailing.py |
| rejected_json | omni_prod/routed_gateway.py; omni_prod/worker_tasks.py; tests/test_t3_rejected_json_durable.py; tests/test_t3_json_no_silent_trailing.py |
| rejected_model_json | omni_prod/worker_tasks.py; tests/test_t3_rejected_json_durable.py |
| tail_status | PR branch: omni_prod/model_gateway.py; tests/test_e1_json_tail_recovery.py (not indexed on main) |
| trailing_chars | omni_prod/model_gateway.py; tests/test_t3_json_no_silent_trailing.py |
| assertRaises(ModelGatewayError) | tests/test_model_json_parsing.py; tests/test_t3_rejected_json_durable.py; tests/test_t3_json_no_silent_trailing.py; tests/test_t5_codegen_route_every_class.py; tests/test_failure_injection.py; tests/test_model_transient_retry.py; tests/test_intelligence_plane.py; tests/test_m5_llm_usage_evidence.py; tests/test_model_catalog_routing.py; tests/test_provider_quota_and_dialects.py |

## Migration decisions

| Path | Decision | Reason |
|---|---|---|
| omni_prod/model_gateway.py | REMAIN | E1 parsing behavior already changed on PR branch; user prohibits further changes |
| tests/test_t3_rejected_json_durable.py | MIGRATE | Existing `RAW` is valid first JSON plus prose; strict-rejection assertions no longer apply. Preserve all actual-invalid-JSON rejection/durability cases |
| tests/test_t3_json_no_silent_trailing.py | MIGRATE | Restore original trailing-text fixture as accepted-with-tail; add separate malformed-first-object rejection case; don't silently replace inputs |
| tests/test_e1_json_tail_recovery.py | REMAIN / VERIFY | Synthetic 7807/7825 shape, **not** historical raw output |
| omni_prod/routed_gateway.py | REVIEW | Accepted-response sink added in #121; verify success/failure partition and redaction |
| omni_prod/worker_tasks.py | REVIEW | Both accepted and rejected manifests must be disjoint, durable and redacted |
| omni_prod/evidence_export.py | REVIEW | Manifest currently exposes storage keys, not raw body; requirement to extract actual 18 bytes remains pending |
| Other `assertRaises(ModelGatewayError)` matches | REMAIN unless proven tail-specific | Exception can reflect genuine provider/JSON failures unrelated to trailing content |

## Required test changes by full name

- `tests/test_t3_rejected_json_durable.py::RejectedJsonIsDurable` — all cases currently use the valid-first-object `RAW` fixture; redirect these to a **separate** genuine invalid-JSON fixture without dropping test coverage.
- `tests/test_t3_rejected_json_durable.py::DurabilityIsWhatTheWritesAchieved` — preserve and adapt rejection durability cases, plus clean success.
- `tests/test_t3_rejected_json_durable.py::EveryPersistedTextFieldIsRedacted` — retain trailing accepted-path redaction, leading rejection redaction, failure and identifiers.
- `tests/test_t3_json_no_silent_trailing.py::TrailingContentIsNotIgnored` — accepted tail with full diagnosis; genuine invalid JSON rejected; pre-object prose remains rejected.
- `tests/test_t3_json_no_silent_trailing.py::TheRoutedGatewayKeepsTheRawAnswer` — separate accepted-with-tail and invalid-first-object routes.
- `tests/test_e1_json_tail_recovery.py::E1TailRecovery` — verify exact 7807/7825 shape.

## Evidence gap

No `grep -rn` stdout, pytest RED/GREEN list, network-namespace result, CI-check results or production artifact is claimed by this draft. **S1 OPEN, S2 NOT STARTED.**
