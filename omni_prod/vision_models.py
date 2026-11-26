"""Which provider models a call with images may go to (Michael 2026-11-15: "vision first, then the live probe").

The router (routed_gateway._route) had no vision filter: a call carrying images (lens 11's image check, the design
review) could be routed to any eligible model, and a model that cannot read the image would answer from the text
alone -- a confident verdict about a picture it never saw. This list is the only source of truth; a model that is not
on it is never sent images, the refusal is recorded on the route, and a call with no vision route left fails loudly.

It is a global list in code (on main), not a field of the worker's model catalog secret: a reviewed change, read the
same way by every branch and every environment (Michael's global-data rule, 2026-11-15).

A model is added only with evidence: a production answer to an image call, or the live probe
(scripts/vision_probe.py), which sends a known picture and checks the model names what is in it."""
from __future__ import annotations

# provider model id (ModelEndpoint.model) -> evidence
_PROBE = 'vision-probe run 43689691749 (2026-11-15, main be831c6): red circle and blue triangle both named correctly'
# Law 2 (2026-11-26): the first probe, run 43657047045 (f02404a), had the same answers from all six models but ended
# red: its step failed on an empty stderr (fixed by 7d79150; tests/test_vision_probe_step.py). This is its green re-run.
VISION_MODELS: dict[str, str] = {
    'gpt-6.1-sol': 'production: 20 design reviews scored from screenshots (build_jobs.evidence_json design_review, '
                   'last bld_83529c13 2026-11-14 18:25Z); ' + _PROBE,
    'gemini-3.8-flash': 'production: 4 design reviews scored from screenshots (last bld_5a37dc27 2026-11-13 06:09Z); '
                        + _PROBE,
    'gemini-3.1-flash-lite': _PROBE,
    'gemini-3.5-flash-lite': _PROBE,
    'gpt-6-luna': _PROBE,
    'claude-sonnet-5-5': _PROBE,
}


def accepts_images(model: str | None) -> bool:
    return bool(model) and model in VISION_MODELS
