from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json

@dataclass(frozen=True)
class MemoryEntry:
    id: str
    project_id: str
    kind: str
    text: str
    created_at: str
    source_version: str | None = None

class ProjectMemory:
    """Append-only project decision memory with deterministic context compaction."""
    def __init__(self, *, max_entries: int = 500):
        if max_entries < 1:
            raise ValueError('max_entries must be positive')
        self.max_entries = max_entries
        self._entries: dict[str, list[MemoryEntry]] = {}

    def append(self, *, project_id: str, kind: str, text: str, source_version: str | None = None) -> MemoryEntry:
        if not project_id.strip() or not kind.strip() or not text.strip():
            raise ValueError('project_id, kind and text are required')
        bucket = self._entries.setdefault(project_id, [])
        idx = len(bucket) + 1
        item = MemoryEntry(
            id=f'{project_id}-m{idx:05d}', project_id=project_id, kind=kind.strip(), text=text.strip(),
            created_at=datetime.now(timezone.utc).isoformat(), source_version=source_version,
        )
        bucket.append(item)
        if len(bucket) > self.max_entries:
            del bucket[:len(bucket)-self.max_entries]
        return item

    def list(self, project_id: str) -> tuple[MemoryEntry, ...]:
        return tuple(self._entries.get(project_id, ()))

    def context(self, project_id: str, *, max_chars: int = 12000) -> str:
        if max_chars < 128:
            raise ValueError('max_chars too small')
        selected: list[MemoryEntry] = []
        used = 0
        for entry in reversed(self._entries.get(project_id, [])):
            line = f'[{entry.kind}] {entry.text}'
            if used + len(line) + 1 > max_chars:
                continue
            selected.append(entry)
            used += len(line) + 1
        selected.reverse()
        return '\n'.join(f'[{e.kind}] {e.text}' for e in selected)

    def export(self, project_id: str) -> str:
        return json.dumps([asdict(x) for x in self.list(project_id)], ensure_ascii=False, indent=2)
