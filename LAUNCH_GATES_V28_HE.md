# 148AI — Public Launch Gates

Public launch requires all critical gates green:
1. Creator persistence: PostgreSQL live + restart persistence test.
2. Redis/queue live.
3. Artifact storage live + checksum roundtrip.
4. Remote sandbox live + network/rootfs/source-readonly hostile suite.
5. Open-weight model live + real benchmark run.
6. Media provider live for enabled paid media capabilities.
7. Billing provider live: checkout + signed webhook + idempotency + cancellation/refund state.
8. Email verification/reset live.
9. Domain/TLS/DNS + production origins.
10. Backup + restore drill.
11. Rights/IP gate and brand/trademark review.
12. Mobile signing only before claiming store-ready binaries.
13. Founder approval after Release Council technical green.

No gate can be converted to green by documentation alone.
