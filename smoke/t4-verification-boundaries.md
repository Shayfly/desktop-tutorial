# T4 verification boundaries — per-case evidence

- command: `python3 -I tools/redteam_verification_boundaries.py` → exit **0**
- generated on top of commit `7ac44c8e829334e0afc5a86e33d3c84183766f90` (the code under test is this file's own commit; source SHA-256 below)
- original 26: **26/26 met**, false successes **0**; T4 cases: **16/16 met**
- probe stdout SHA-256: `07a67642c422c2b467cd0883b957c8f62d234aabc98b595fdfb8523d3885757c`

| file | SHA-256 |
|---|---|
| `omni_prod/verification_verdict.py` | `5f989166af717df53237a57e2f6ecda33183d7391675605c5108ea4522b331d8` |
| `omni_prod/browser_probe.py` | `2fba2146a944330f30e2b1a4693c6e7b0b7390ffc6429870461fb63cd173d9b0` |
| `omni_prod/visual_qa.py` | `8bc50c1bb6af62f7ee47587290c27fc3891c0c2d4132ebf6ddb9f5368fde4769` |
| `omni_prod/behavior_acceptance.py` | `e53d085bfc17bbb484a7da6ab256c52ac531c0e223e51374c22e5efb3334cef2` |
| `omni_prod/preview_smoke.py` | `040d22a2acc6999ebcacdad16f7709c41cffab1740e05850402985ad6bb88b67` |
| `omni_prod/verification_group.py` | `e7ceaaae16d9641d37dcdc5addfdeca4d916621c3260d37914ee708806ce48b5` |
| `tools/redteam_verification_boundaries.py` | `b7bf43a075963c3d626b1817f23fc3ad9a34d0f7195bc1b123e3ecfe3e45fbf1` |

## The 26 original cases

| # | id | expected | main @8634a57 | observed | failure ids | result |
|---|---|---|---|---|---|---|
| 1 | `BrowserFlowExecutor_timeout` | FAIL | passed=True (FALSE SUCCESS) | FAIL | BROWSER_UNVERIFIED | **MET** |
| 2 | `BrowserFlowExecutor_missing_output` | FAIL | passed=True (FALSE SUCCESS) | FAIL | BROWSER_UNVERIFIED | **MET** |
| 3 | `VisualQAExecutor_timeout` | FAIL | passed=True (FALSE SUCCESS) | FAIL | VISUAL_UNVERIFIED | **MET** |
| 4 | `VisualQAExecutor_missing_output` | FAIL | passed=True (FALSE SUCCESS) | FAIL | VISUAL_UNVERIFIED | **MET** |
| 5 | `BrowserFlowExecutor_json_list` | FAIL | raises AttributeError | FAIL | BROWSER_UNVERIFIED | **MET** |
| 6 | `VisualQAExecutor_json_list` | FAIL | raises TypeError | FAIL | VISUAL_UNVERIFIED | **MET** |
| 7 | `BehaviorAcceptanceExecutor_json_list` | FAIL | raises AttributeError | FAIL | BEHAVIOR_UNVERIFIED | **MET** |
| 8 | `browser_empty_object` | FAIL | passed=True (FALSE SUCCESS) | FAIL | BROWSER_UNVERIFIED | **MET** |
| 9 | `browser_nonzero_exit_with_pass_payload` | FAIL | passed=True (FALSE SUCCESS) | FAIL | BROWSER_UNVERIFIED | **MET** |
| 10 | `behavior_nonzero_exit_with_pass_payload` | FAIL | passed=True (FALSE SUCCESS) | FAIL | BEHAVIOR_UNVERIFIED | **MET** |
| 11 | `PreviewReadyExecutor_BuildCancelled` | PROPAGATES BuildCancelled | passed=False, BuildCancelled swallowed | PROPAGATED BuildCancelled |  | **MET** |
| 12 | `PreviewReadyExecutor_AttemptLedgerUnavailable` | PROPAGATES AttemptLedgerUnavailable | passed=False, AttemptLedgerUnavailable swallowed | PROPAGATED AttemptLedgerUnavailable |  | **MET** |
| 13 | `PreviewReadyExecutor_ModelPolicyViolation` | PROPAGATES ModelPolicyViolation | passed=False, ModelPolicyViolation swallowed | PROPAGATED ModelPolicyViolation |  | **MET** |
| 14 | `BehaviorAcceptanceExecutor_BuildCancelled` | PROPAGATES BuildCancelled | passed=False, BuildCancelled swallowed | PROPAGATED BuildCancelled |  | **MET** |
| 15 | `BehaviorAcceptanceExecutor_AttemptLedgerUnavailable` | PROPAGATES AttemptLedgerUnavailable | passed=False, AttemptLedgerUnavailable swallowed | PROPAGATED AttemptLedgerUnavailable |  | **MET** |
| 16 | `BehaviorAcceptanceExecutor_ModelPolicyViolation` | PROPAGATES ModelPolicyViolation | passed=False, ModelPolicyViolation swallowed | PROPAGATED ModelPolicyViolation |  | **MET** |
| 17 | `BrowserFlowExecutor_BuildCancelled` | PROPAGATES BuildCancelled | passed=True (FALSE SUCCESS) | PROPAGATED BuildCancelled |  | **MET** |
| 18 | `BrowserFlowExecutor_AttemptLedgerUnavailable` | PROPAGATES AttemptLedgerUnavailable | passed=True (FALSE SUCCESS) | PROPAGATED AttemptLedgerUnavailable |  | **MET** |
| 19 | `BrowserFlowExecutor_ModelPolicyViolation` | PROPAGATES ModelPolicyViolation | passed=True (FALSE SUCCESS) | PROPAGATED ModelPolicyViolation |  | **MET** |
| 20 | `VisualQAExecutor_BuildCancelled` | PROPAGATES BuildCancelled | passed=True (FALSE SUCCESS) | PROPAGATED BuildCancelled |  | **MET** |
| 21 | `VisualQAExecutor_AttemptLedgerUnavailable` | PROPAGATES AttemptLedgerUnavailable | passed=True (FALSE SUCCESS) | PROPAGATED AttemptLedgerUnavailable |  | **MET** |
| 22 | `VisualQAExecutor_ModelPolicyViolation` | PROPAGATES ModelPolicyViolation | passed=True (FALSE SUCCESS) | PROPAGATED ModelPolicyViolation |  | **MET** |
| 23 | `group_exception_suppresses_later_checks` | FAIL, both checks ran, the crashed check named | passed=False | FAIL | SIMPLENAMESPACE_EXCEPTION | **MET** |
| 24 | `group_false_with_empty_failures` | FAIL | passed=False | FAIL |  | **MET** |
| 25 | `group_string_false` | FAIL | passed=False | FAIL |  | **MET** |
| 26 | `group_true_with_failures` | FAIL | passed=True (FALSE SUCCESS) | FAIL |  | **MET** |

## T4 cases (NO_CHECKS, positive controls with a real check, Matt's three blockers, group propagation)

| # | id | expected | observed | failure ids | result |
|---|---|---|---|---|---|
| 27 | `no_checks_browser_zero_forms` | NO_CHECKS | NO_CHECKS | BROWSER_NO_CHECKS | **MET** |
| 28 | `no_checks_behavior_pass_with_zero_checks` | NO_CHECKS | NO_CHECKS | BEHAVIOR_NO_CHECKS | **MET** |
| 29 | `no_checks_visual_nothing_inspected` | NO_CHECKS | NO_CHECKS | VISUAL_NO_CHECKS | **MET** |
| 30 | `positive_browser_one_form_exercised` | PASS | PASS |  | **MET** |
| 31 | `positive_behavior_one_passing_check` | PASS | PASS |  | **MET** |
| 32 | `positive_visual_controls_inspected` | PASS | PASS |  | **MET** |
| 33 | `positive_group_real_stages` | PASS | PASS |  | **MET** |
| 34 | `positive_group_fails_when_one_real_stage_reports_no_checks` | NO_CHECKS | NO_CHECKS | BROWSER_NO_CHECKS | **MET** |
| 35 | `positive_content_site_page_observed_no_forms` | PASS | PASS |  | **MET** |
| 36 | `content_site_with_a_javascript_error` | FAIL | FAIL | BROWSER | **MET** |
| 37 | `behavior_no_acceptance_and_no_plan` | NO_CHECKS | NO_CHECKS | BEHAVIOR_NO_CHECKS | **MET** |
| 38 | `behavior_non_python_runtime` | FAIL | FAIL | BEHAVIOR_UNVERIFIED | **MET** |
| 39 | `preview_non_python_runtime` | FAIL | FAIL | PREVIEW_UNVERIFIED | **MET** |
| 40 | `group_propagates_BuildCancelled` | PROPAGATES BuildCancelled | PROPAGATED BuildCancelled |  | **MET** |
| 41 | `group_propagates_AttemptLedgerUnavailable` | PROPAGATES AttemptLedgerUnavailable | PROPAGATED AttemptLedgerUnavailable |  | **MET** |
| 42 | `group_propagates_ModelPolicyViolation` | PROPAGATES ModelPolicyViolation | PROPAGATED ModelPolicyViolation |  | **MET** |
