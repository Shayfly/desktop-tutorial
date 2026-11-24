# A2 — rights-cleared reference comparison (candidate, not live)

Owner directive #523. Google Gemini 3.8 Flash is the intended comparison
model. The Google Search Grounding terms effective 2026-03-23 restrict
automated collection of links, indexing and identification of pages for
crawling/scraping. See https://aistudio.google.com/docs/terms#grounding-with-google-search
(section Use Restrictions, read 2026-11-24). Do not connect this library
collector to Google Search Grounding under the standard terms. A different
licensed discovery service or explicit written permission is required for
automated acquisition. A user-facing grounded answer is a separate use case,
with its own display and retention requirements.

The additive `omni_prod/a2/approved_research.py` module is a pure adapter
around the existing approved reference store. It does not invoke a provider.
It admits 3–8 fresh cards of the requested closed-catalog category, approved
by the existing library rules, with distinct source URLs and explicit rights
grants bound to the complete card revision SHA-256. Only owned or independently
licensed origins are admitted. Source URL, capture timestamp and rights
evidence stay in the server-side evidence envelope; only the closed schema
structure and existing measured scores form the model input. No customer
description, raw images, copied text or reviewer prose is included.

The future trusted transport must independently validate the actual license,
grant authenticity and expiry, persist the prepared request and its two
digests immutably, admit one metered Gemini call with the existing accounting
mechanism, and bind the response to that stored request. It must send the
input digest alongside the sanitized model input and ask for exactly three
distinct reference IDs with supported strengths. The validator rejects new
references, unmeasured strengths, extra free text and modified evidence.
Its result is a recommendation, not a build approval or verified site.
No cost is claimed. No live provider route, acquisition service, storage
migration, or browser/network policy is activated by this change.

The test fixtures are synthetic; their grants do not prove any real license.
For integration, test missing/expired grants and ambiguous provider outcomes,
verify live account and model identity, prove the metered call and independent
review, and use a licensed acquisition source before turning on collection.
