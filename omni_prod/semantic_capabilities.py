"""Verified semantic capability decisions from the EXISTING intake conversation.

This is a bounded data contract, not an LLM client, builder or authority to pay.
Decisions are recorded in the approved Brief JSON and are therefore bound to
its fingerprint and explicit customer approval. The normal dependency DAG,
provider quote and admission checks remain authoritative.
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Mapping

SCHEMA_VERSION = 1
LINE_PREFIX = "Semantic capability decisions v1: "
MAX_DECISIONS = 16
# Exclusions can affect ambiguous, user-facing products/capabilities only.
# Never allow a model to suppress the build, testing, preview or security floor.
SUPPORTED = frozenset({
    "target.agent", "ai.agent.tools", "ai.agent.memory", "ai.agent.eval",
    "integration.maps", "integration.messaging", "integration.email",
    "integration.webhook", "media.audio.tts", "media.audio.stt",
    "media.audio.realtime_voice", "media.image.generate",
    "media.video.generate", "target.mobile", "target.automation",
})
CHOICES = frozenset({"required", "not_required", "uncertain"})


def _norm(value: str) -> str:
    value = unicodedata.normalize("NFC", value)
    value = re.sub(r"[\u0591-\u05bd\u05bf\u05c1\u05c2\u05c4\u05c5\u05c7\u200b-\u200f\u202a-\u202e\u2066-\u2069]", "", value)
    return " ".join(value.casefold().split())


def validate_decisions(raw: object, *, customer_text: str) -> tuple[list[dict], list[str]]:
    """Reject ungrounded model inferences. Evidence must come from the user text."""
    if not isinstance(raw, list):
        return [], ["semantic_decisions must be a list"]
    validated, rejected, seen = [], [], set()
    for item in raw[:MAX_DECISIONS]:
        if not isinstance(item, dict):
            rejected.append("semantic decision not an object")
            continue
        key, status, evidence, reason = (
            item.get("key"), item.get("decision"), item.get("evidence"), item.get("reason")
        )
        if key not in SUPPORTED or status not in CHOICES or not isinstance(evidence, str) or not isinstance(reason, str):
            rejected.append("unsupported semantic decision")
            continue
        if key in seen or not (3 <= len(evidence) <= 240) or not (1 <= len(reason) <= 220):
            rejected.append("duplicate or oversized semantic decision")
            continue
        if _norm(evidence) not in _norm(customer_text):
            rejected.append("semantic decision has no quote from customer message")
            continue
        seen.add(key)
        validated.append({"key": key, "decision": status, "evidence": evidence, "reason": reason})
    if len(raw) > MAX_DECISIONS:
        rejected.append("semantic decision limit exceeded")
    return validated, rejected


def updated_decisions(previous: object, new: object) -> list[dict]:
    """Latest user turn supersedes only the named capability; preserve the rest."""
    out = {x["key"]: dict(x) for x in (previous or ()) if isinstance(x, dict) and x.get("key") in SUPPORTED}
    for item in new or ():
        if isinstance(item, dict) and item.get("key") in SUPPORTED:
            out[item["key"]] = dict(item)
    return list(out.values())[:MAX_DECISIONS]


def encode_approved(decisions: object) -> str:
    safe = [dict(x) for x in decisions or () if isinstance(x, dict) and x.get("key") in SUPPORTED]
    return LINE_PREFIX + json.dumps({"version": SCHEMA_VERSION, "decisions": safe[:MAX_DECISIONS]},
                                    separators=(",", ":"), ensure_ascii=False)


def read_approved(full_prompt: str) -> list[dict]:
    """Read only the generated approved-brief section, never a raw user sentence."""
    marker = "--- Approved project brief"
    if marker not in full_prompt:
        return []
    block = full_prompt.split(marker, 1)[1]
    lines = [s for s in block.splitlines() if s.startswith(LINE_PREFIX)]
    if len(lines) != 1:
        return []
    try:
        parsed = json.loads(lines[0][len(LINE_PREFIX):])
    except (ValueError, TypeError):
        return []
    if not isinstance(parsed, dict) or parsed.get("version") != SCHEMA_VERSION:
        return []
    raw = parsed.get("decisions")
    if not isinstance(raw, list) or len(raw) > MAX_DECISIONS:
        return []
    # Recheck persisted model evidence against ORIGINAL request, not brief text.
    original = full_prompt.split(marker, 1)[0]
    accepted, _ = validate_decisions(raw, customer_text=original)
    return accepted


def overrides(decisions: object) -> dict[str, str]:
    """Only required/not_required decisions influence the capability DAG."""
    return {d["key"]: d["decision"] for d in (decisions or ())
            if isinstance(d, Mapping) and d.get("key") in SUPPORTED
            and d.get("decision") in ("required", "not_required")}
