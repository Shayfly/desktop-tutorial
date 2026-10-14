# Omni Creator V25 — Unified Core Merge Manifest

## Parent
V24 International Readiness is the direct source parent.

## Legacy V10 recovery
The original V10 ZIP was rediscovered in Library metadata, but raw-byte access to that historical Project file remains authorization-blocked. Therefore this release does **not** claim an unverifiable line-by-line merge.

Instead, the original V10 validation is treated as a behavior contract. V25 implements and tests every documented V10 capability relevant to the core product path:
- generated app auth/RBAC
- hosted deployment authentication + isolation
- authenticated WebSocket
- maps/realtime/payment planning
- Android Studio source
- Godot 4 source
- safe AI patching
- Omni Android AAB workflow contract
- build/preview/export/promotion/version isolation

Evidence: `tests/test_v25_unified_v10_parity.py`, `LIVE_HTTP_V25.json`.

## V24 layers retained
Production control plane, resilience, release safety, supply-chain security, outbox/recovery, observability, model routing, autonomous core, control center, internationalization, mobile/game source generators, billing, teams, integrations and benchmark catalog remain in the V25 source tree and regression suite.

## Source of truth rule
From V25 forward, V25+ is the canonical code line. Historical V10 is evidence/baseline only, not a required runtime dependency.

## External gates not faked
GPU Open-Weight inference, live Docker hostile execution, PostgreSQL/Redis/S3 live integration, signed AAB/IPA and console certification remain explicit external gates.
