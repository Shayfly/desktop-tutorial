from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from .agents_registry import build_canonical_agents_registry, validate_master_registries
from .capability_registry import CapabilityRegistry
from .integration_center import IntegrationCenter
from .skills_registry import build_canonical_skills_registry


class TruthDriftError(RuntimeError):
    pass


def _join(values: Iterable[str]) -> str:
    items = tuple(values)
    return ", ".join(items) if items else "—"


def _json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(v) for v in value]
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(_json_safe(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_truth_snapshot() -> dict[str, Any]:
    capabilities = CapabilityRegistry()
    skills = build_canonical_skills_registry(capabilities)
    agents = build_canonical_agents_registry(skills)
    report = validate_master_registries(capabilities, skills, agents)
    center = IntegrationCenter()

    capability_rows = []
    for definition in capabilities.all():
        row = asdict(definition)
        row["status"] = center.capability_status(definition).value
        capability_rows.append(_json_safe(row))
    skill_rows = [_json_safe(asdict(skill)) for skill in skills.all()]
    agent_rows = [_json_safe(asdict(agent)) for agent in agents.all()]

    base = {
        "schema_version": 1,
        "milestone": "M4.95",
        "registry_version": skills.version,
        "status_vocabulary": ["LIVE", "PARTIAL", "NOT_CONFIGURED", "NOT_IMPLEMENTED", "BLOCKED"],
        "capability_count": len(capability_rows),
        "skill_count": len(skill_rows),
        "agent_count": len(agent_rows),
        "registry_report": {
            "uncovered_capabilities": list(report["uncovered_capabilities"]),
            "unknown_agent_skills": [list(item) for item in report["unknown_agent_skills"]],
        },
        "capabilities": capability_rows,
        "skills": skill_rows,
        "agents": agent_rows,
        "truth_rules": {
            "source_presence_is_not_live": True,
            "unknown_cost_is_not_zero": True,
            "estimate_is_not_actual": True,
            "real_execution_or_explicit_failure": True,
        },
    }
    digest = hashlib.sha256(_canonical_json(base).encode("utf-8")).hexdigest()
    return {**base, "sha256": digest}


def truth_lock_snapshot() -> dict[str, Any]:
    snapshot = canonical_truth_snapshot()
    return {
        "capability_count": snapshot["capability_count"],
        "skill_count": snapshot["skill_count"],
        "agent_count": snapshot["agent_count"],
        "uncovered_capabilities": snapshot["registry_report"]["uncovered_capabilities"],
        "unknown_agent_skills": snapshot["registry_report"]["unknown_agent_skills"],
        "sha256": snapshot["sha256"],
    }


def render_capability_matrix(registry: CapabilityRegistry | None = None) -> str:
    registry = registry or CapabilityRegistry()
    center = IntegrationCenter()
    lines = [
        "# 148AI Capability Matrix — Machine Truth Lock",
        "",
        "> Generated from canonical code. Do not edit by hand.",
        "> Source presence, an enum, a plan, or an API key alone is never evidence that a capability is LIVE.",
        "",
        "| Capability | Family | Status | Provider-backed | Dependencies |",
        "|---|---|---|---:|---|",
    ]
    for definition in registry.all():
        lines.append(
            f"| `{definition.key}` | `{definition.family}` | **{center.capability_status(definition).value}** | "
            f"{'yes' if definition.provider_backed else 'no'} | {_join(f'`{d}`' for d in definition.dependency_keys)} |"
        )
    lines += [
        "",
        "## Status semantics",
        "",
        "- `LIVE`: verified against the intended production path with current evidence.",
        "- `PARTIAL`: meaningful implementation exists but the full production contract is not yet verified.",
        "- `NOT_CONFIGURED`: implementation/contract may exist, but required provider/runtime configuration is absent.",
        "- `NOT_IMPLEMENTED`: canonical product scope exists but execution is not implemented.",
        "- `BLOCKED`: an explicit dependency, policy, budget, or external gate prevents execution.",
        "",
    ]
    return "\n".join(lines)


def render_skills_registry(skills=None) -> str:
    capabilities = CapabilityRegistry()
    skills = skills or build_canonical_skills_registry(capabilities)
    lines = [
        "# 148AI Master Skills Registry — Machine Truth Lock",
        "",
        f"> Registry version: `{skills.version}`. Generated from `omni_prod.skills_registry`; do not edit by hand.",
        "",
        "| Skill | Status | Capabilities | Dependencies | Cost model |",
        "|---|---|---|---|---|",
    ]
    for skill in skills.all():
        lines.append(
            f"| `{skill.key}` | **{skill.status.value}** | {_join(f'`{c}`' for c in skill.capability_keys)} | "
            f"{_join(f'`{d}`' for d in skill.dependency_keys)} | `{skill.cost_model}` |"
        )
    lines += ["", "Every canonical capability must resolve to at least one skill. CI tests enforce this.", ""]
    return "\n".join(lines)


def render_agents_registry(agents=None) -> str:
    capabilities = CapabilityRegistry()
    skills = build_canonical_skills_registry(capabilities)
    agents = agents or build_canonical_agents_registry(skills)
    lines = [
        "# 148AI Master Agents Registry — Machine Truth Lock",
        "",
        "> Generated from `omni_prod.agents_registry`; do not edit by hand.",
        "",
        "| Agent | Role | Status | Allowed skills | Agent dependencies |",
        "|---|---|---|---:|---|",
    ]
    for agent in agents.all():
        lines.append(
            f"| `{agent.key}` | {agent.role} | **{agent.status.value}** | {len(agent.allowed_skills)} | "
            f"{_join(f'`{d}`' for d in agent.dependency_agents)} |"
        )
    lines += ["", "Agent skill references and dependency cycles are validated in code and CI tests.", ""]
    return "\n".join(lines)


def render_truth_files() -> dict[str, str]:
    snapshot = canonical_truth_snapshot()
    capabilities = CapabilityRegistry()
    skills = build_canonical_skills_registry(capabilities)
    agents = build_canonical_agents_registry(skills)
    skill_json = {
        "schema_version": 1,
        "registry_version": skills.version,
        "truth_sha256": snapshot["sha256"],
        "skills": snapshot["skills"],
    }
    agent_json = {
        "schema_version": 1,
        "truth_sha256": snapshot["sha256"],
        "agents": snapshot["agents"],
    }
    return {
        "CAPABILITY_MATRIX.md": render_capability_matrix(capabilities),
        "MASTER_SKILLS_REGISTRY.md": render_skills_registry(skills),
        "MASTER_AGENTS_REGISTRY.md": render_agents_registry(agents),
        "MASTER_SKILLS_REGISTRY.json": json.dumps(skill_json, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        "MASTER_AGENTS_REGISTRY.json": json.dumps(agent_json, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        "M4_95_MACHINE_TRUTH.json": json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    }


def expected_documents() -> dict[str, str]:
    return render_truth_files()


def write_truth_files(root: Path = Path(".")) -> None:
    for relative, content in render_truth_files().items():
        (root / relative).write_text(content, encoding="utf-8")


def write_truth_documents(root: Path = Path(".")) -> None:
    write_truth_files(root)


def check_truth_files(root: Path = Path(".")) -> None:
    drift = []
    for relative, content in render_truth_files().items():
        path = root / relative
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            drift.append(relative)
    if drift:
        raise TruthDriftError("truth-lock drift: " + ", ".join(drift))


def truth_documents_in_sync(root: Path = Path(".")) -> tuple[bool, tuple[str, ...]]:
    try:
        check_truth_files(root)
        return True, ()
    except TruthDriftError as exc:
        suffix = str(exc).split(":", 1)[-1].strip()
        return False, tuple(part.strip() for part in suffix.split(",") if part.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="148AI machine truth lock")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.write:
        write_truth_files()
        return 0
    try:
        check_truth_files()
    except TruthDriftError as exc:
        print(str(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
