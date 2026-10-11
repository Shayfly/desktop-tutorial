"""Minimal read-only, observed HTTP contract validation; no sensitive echoes."""
from __future__ import annotations

from typing import Any


def validate(name: str, data: Any) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "Expected JSON object"
    if name == "public_pricing":
        return True, "Pricing JSON object received"
    if name == "auth_me":
        if not {"id", "email", "created_at", "subscription"}.issubset(data):
            return False, "Identity response missing mandatory keys"
        return True, "Identity contract received (details omitted)"
    if name == "auth_projects":
        if not isinstance(data.get("projects"), list):
            return False, "Projects response missing array"
        return True, "Projects array received (contents omitted)"
    if name == "proj_conversation":
        if not {"messages", "discovery", "plan", "plan_id", "interpreter"}.issubset(data) or not isinstance(data.get("messages"), list):
            return False, "Conversation contract mismatch"
        return True, "Conversation contract received (messages omitted)"
    if name in ("proj_memory", "proj_discovery"):
        return True, f"{name} JSON object received"
    return False, "Unknown contract"
