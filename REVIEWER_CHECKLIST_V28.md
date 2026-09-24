# V28 Reviewer Checklist — 148AI

Please try to break the product rather than review the claims.

1. Run `python -m pytest -q`.
2. Run `python scripts/run_v28_release_gate.py`.
3. Inspect `omni_prod/pricing.py`: verify hard provider caps and free-plan restrictions.
4. Try disabling branding on Free/Basic; it must fail.
5. Upgrade a test user to Pro only through the admin-protected path; visible branding can then be removed.
6. Verify Business white-label and persistent `.148ai/provenance.json`.
7. Create two accounts and attempt cross-user project/history/export/rights access.
8. Test an IP-risk prompt and confirm Publish is blocked.
9. Inspect `omni_prod/creator_accounts.py` and migrations 011/012 for production persistence readiness.
10. Confirm Integration Center never returns secret values.
11. Run V10 parity and V27 rights tests separately.
12. Do not accept GPU/Docker/Postgres/Stripe/media/mobile-signing claims without the live gates.
13. Call `/api/v28/billing/checkout` without Stripe configuration; it must fail closed and leave the user on Free.
14. Verify an invalid Stripe webhook signature cannot change plan; only a valid verified event or protected admin path may assign a paid plan.
