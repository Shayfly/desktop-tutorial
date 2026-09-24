# V27 Reviewer Checklist

1. Run `python -m pytest -q`.
2. Run `python scripts/run_v27_release_gate.py`.
3. Register two V27 creator accounts and verify project/rights isolation.
4. Build an original project and verify Rights Gate = CLEAR.
5. Build `Build a football game with Messi and Ronaldo` and verify Promote returns 409.
6. Upload evidence and verify it remains unverified.
7. Verify `/rights/review` fails without `OMNI_RIGHTS_REVIEW_KEY`.
8. Review evidence with the separate reviewer credential and verify gate can clear.
9. Export project ZIP and inspect `rights/rights-manifest.json`.
10. Use Original Alternative and verify detected third-party identifiers are removed from the replacement brief.
11. Review `ONE_PERSON_COMPANY_OS_HE.md` and `/api/v27/company-os`.
12. Treat legal conclusions as external human decisions; do not treat the automated assessment as counsel.
