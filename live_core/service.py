from __future__ import annotations

import re

from .store import BuildRecord, ProjectRecord, Store, VersionRecord


def _project_title(prompt: str) -> str:
    compact = re.sub(r"\s+", " ", prompt).strip()
    return (compact[:56] or "My 148AI Product").strip()


class CustomerService:
    def __init__(self, store: Store) -> None:
        self.store = store

    def ensure_project(self, owner_id: str, prompt: str, project_id: str | None = None) -> ProjectRecord:
        if project_id:
            project = self.store.get_project(project_id, owner_id)
            if not project:
                raise KeyError("project not found")
            return project
        return self.store.create_project(owner_id, _project_title(prompt))

    def start_build(self, owner_id: str, prompt: str, project_id: str | None = None) -> BuildRecord:
        prompt = prompt.strip()
        if len(prompt) < 3:
            raise ValueError("prompt must contain at least 3 characters")
        project = self.ensure_project(owner_id, prompt, project_id)
        build = self.store.create_build(owner_id, project.id, prompt)
        self.store.append_build_event(build.id, "planning", "Preparing product specification")
        return build

    def list_projects(self, owner_id: str) -> list[ProjectRecord]:
        return self.store.list_projects(owner_id)

    def list_versions(self, owner_id: str, project_id: str) -> list[VersionRecord]:
        if not self.store.get_project(project_id, owner_id):
            raise KeyError("project not found")
        return self.store.list_versions(project_id, owner_id)
