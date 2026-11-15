"""A2 (Gemini): collect design references and compose directions (docs/spec/gemini-a2.md).

Offline first (Shai 2026-11-15 15:29): every skill here runs against pages served from this machine; a request to
any other host is blocked and counted, never made. Live search and live sites wait for a cost decision.

contract -- every output is a document of docs/spec/a2_direction.schema.json (validated, loud on failure)
search   -- 1.1: candidates from a list (offline "library" source); live Gemini grounding is not wired
verify   -- 1.2: live / fast / light / direction / robots, measured in a real browser
capture  -- 1.3: full-page screenshots at 390 and 1440, stored by sha256
collect  -- one bounded run: search -> verify -> capture, with the funnel

A2 never writes to the customer: no output has a field for customer-facing words.
"""
