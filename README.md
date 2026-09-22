# 148AI V28 — Vercel Review Preview

Private deployment repository for the current **148AI V28 Launch Candidate** review UI.

## Purpose
This repo is intentionally a **visual / interactive Vercel preview** so the product can be reviewed from a real URL without exposing the full private source package.

The canonical verified source remains `148AI-V28-Launch-Candidate-Reviewer.zip`.

## Current verified V28 baseline
- 231 tests passed
- 11 documented live-only skips
- 0 failures
- 200/200 offline benchmark cases
- Rights/IP gates
- Pricing / plan controls
- Branding / provenance
- PWA / mobile source paths
- Multi-user / versioning architecture

## External production gates not represented as live here
PostgreSQL, Redis, S3/R2, GPU model server, remote Docker sandbox, media engines, Stripe, email, DNS/TLS, signed Android AAB, signed iOS IPA.

## Vercel
Import this repository into Vercel as a static project. `vercel.json` is included.
