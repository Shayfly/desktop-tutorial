from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable


class RequirementStatus(str, Enum):
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    PARTIAL = "PARTIAL"
    IMPLEMENTED_NOT_VERIFIED = "IMPLEMENTED_NOT_VERIFIED"
    VERIFIED_LOCAL = "VERIFIED_LOCAL"
    GATED_EXTERNAL = "GATED_EXTERNAL"
    VERIFIED_EXTERNAL = "VERIFIED_EXTERNAL"
    BLOCKED = "BLOCKED"
    SUPERSEDED = "SUPERSEDED"


@dataclass(frozen=True)
class RequirementRecord:
    requirement_id: str
    milestone: str
    title: str
    status: RequirementStatus
    source_specs: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    implementation_paths: tuple[str, ...] = ()
    test_ids: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    external_gates: tuple[str, ...] = ()
    commit_sha: str | None = None
    last_verified_at: str | None = None
    superseded_by: str | None = None


class RequirementLedger:
    def __init__(self, records: Iterable[RequirementRecord]) -> None:
        source = tuple(records)
        by_id: dict[str, RequirementRecord] = {}
        for record in source:
            if not record.requirement_id.strip():
                raise ValueError("requirement_id must not be empty")
            if record.requirement_id in by_id:
                raise ValueError(f"duplicate requirement id: {record.requirement_id}")
            by_id[record.requirement_id] = record
        self._records = source
        self._by_id = by_id
        self._validate_dependencies()

    def all(self) -> tuple[RequirementRecord, ...]:
        return self._records

    def get(self, requirement_id: str) -> RequirementRecord:
        try:
            return self._by_id[requirement_id]
        except KeyError as exc:
            raise KeyError(f"unknown requirement id: {requirement_id}") from exc

    def contains(self, requirement_id: str) -> bool:
        return requirement_id in self._by_id

    def _validate_dependencies(self) -> None:
        for record in self._records:
            for dep in record.dependencies:
                if dep not in self._by_id:
                    raise ValueError(f"unknown requirement dependency {dep} for {record.requirement_id}")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(key: str) -> None:
            if key in visited:
                return
            if key in visiting:
                raise ValueError(f"requirement dependency cycle at {key}")
            visiting.add(key)
            for dep in self._by_id[key].dependencies:
                visit(dep)
            visiting.remove(key)
            visited.add(key)

        for key in self._by_id:
            visit(key)

    def validate(self, root: Path) -> None:
        verified = {RequirementStatus.VERIFIED_LOCAL, RequirementStatus.VERIFIED_EXTERNAL}
        for record in self._records:
            for source in record.source_specs:
                if not (root / source).exists():
                    raise ValueError(f"{record.requirement_id}: missing source spec {source}")
            if record.status in verified:
                if not record.implementation_paths:
                    raise ValueError(f"{record.requirement_id}: verified without implementation paths")
                if not record.test_ids:
                    raise ValueError(f"{record.requirement_id}: verified without test ids")
                if not record.evidence_refs:
                    raise ValueError(f"{record.requirement_id}: verified without evidence refs")
                if not record.commit_sha:
                    raise ValueError(f"{record.requirement_id}: verified without commit sha")
                if not record.last_verified_at:
                    raise ValueError(f"{record.requirement_id}: verified without last_verified_at")
                for rel in record.implementation_paths:
                    if not (root / rel).exists():
                        raise ValueError(f"{record.requirement_id}: missing implementation path {rel}")
                for test_id in record.test_ids:
                    test_path = test_id.split("::", 1)[0]
                    if not (root / test_path).exists():
                        raise ValueError(f"{record.requirement_id}: missing test path {test_path}")
                for evidence in record.evidence_refs:
                    if not (root / evidence).exists():
                        raise ValueError(f"{record.requirement_id}: missing evidence {evidence}")
            if record.status is RequirementStatus.SUPERSEDED and not record.superseded_by:
                raise ValueError(f"{record.requirement_id}: superseded without superseded_by")


def _record_from_dict(data: dict[str, object]) -> RequirementRecord:
    return RequirementRecord(
        requirement_id=str(data["requirement_id"]),
        milestone=str(data["milestone"]),
        title=str(data["title"]),
        status=RequirementStatus(str(data["status"])),
        source_specs=tuple(data.get("source_specs", ())),
        dependencies=tuple(data.get("dependencies", ())),
        implementation_paths=tuple(data.get("implementation_paths", ())),
        test_ids=tuple(data.get("test_ids", ())),
        evidence_refs=tuple(data.get("evidence_refs", ())),
        external_gates=tuple(data.get("external_gates", ())),
        commit_sha=data.get("commit_sha") or None,
        last_verified_at=data.get("last_verified_at") or None,
        superseded_by=data.get("superseded_by") or None,
    )


def load_requirement_ledger(path: Path) -> RequirementLedger:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported requirement ledger schema_version")
    return RequirementLedger(_record_from_dict(item) for item in payload.get("requirements", ()))


def _task_numbers(plan_path: Path) -> tuple[int, ...]:
    text = plan_path.read_text(encoding="utf-8")
    heading_numbers = tuple(int(value) for value in re.findall(r"^### Task (\d+):", text, re.MULTILINE))
    if heading_numbers:
        return heading_numbers
    # Revised milestone plans may use a canonical numbered task list instead of Task headings.
    return tuple(int(value) for value in re.findall(r"^(\d+)\. \*\*[^\n]+\*\*", text, re.MULTILINE))


def _task_requirement_id(milestone: str, number: int) -> str:
    return f"{milestone}-T{number:02d}"


def validate_plan_task_coverage(plan_path: Path, milestone: str, ledger: RequirementLedger) -> tuple[str, ...]:
    missing = []
    for number in _task_numbers(plan_path):
        key = _task_requirement_id(milestone, number)
        if not ledger.contains(key):
            missing.append(key)
    return tuple(missing)


def run_check(root: Path) -> None:
    ledger = load_requirement_ledger(root / "REQUIREMENT_LEDGER.json")
    ledger.validate(root)
    plans = (
        ("M4.95", root / "docs/superpowers/plans/2026-10-04-m495-capability-foundation-v2-plan.md"),
        ("M5", root / "docs/superpowers/plans/2026-10-04-m5-production-vertical-slice.md"),
    )
    missing: list[str] = []
    for milestone, path in plans:
        missing.extend(validate_plan_task_coverage(path, milestone, ledger))
    if missing:
        raise ValueError(f"plan tasks missing from requirement ledger: {missing}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    if args.check:
        run_check(Path(args.root))
        print("requirement-ledger: OK")


if __name__ == "__main__":
    main()
