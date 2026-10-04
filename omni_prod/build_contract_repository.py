from __future__ import annotations

import json
from typing import Protocol

from .build_contract import BuildContract
from .db import DatabasePool


class BuildContractNotFound(KeyError):
    pass


class BuildContractStore(Protocol):
    def save(self, contract: BuildContract) -> None: ...
    def get(self, contract_id: str, *, project_id: str) -> BuildContract: ...
    def latest(self, project_id: str) -> BuildContract | None: ...
    def list_revisions(self, project_id: str) -> tuple[BuildContract, ...]: ...


class MemoryBuildContractRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, BuildContract] = {}
        self._by_project_version: dict[tuple[str, int], str] = {}

    def save(self, contract: BuildContract) -> None:
        if not contract.verify_fingerprint():
            raise ValueError("cannot save build contract with invalid fingerprint")
        key = (contract.project_id, contract.contract_version)
        if contract.id in self._by_id or key in self._by_project_version:
            raise ValueError("build contract revision already exists")
        existing_versions = [version for (project, version) in self._by_project_version if project == contract.project_id]
        if existing_versions and contract.contract_version != max(existing_versions) + 1:
            raise ValueError("build contract revisions must be monotonic")
        if not existing_versions and contract.contract_version != 1:
            raise ValueError("first build contract revision must be version 1")
        self._by_id[contract.id] = contract
        self._by_project_version[key] = contract.id

    def get(self, contract_id: str, *, project_id: str) -> BuildContract:
        contract = self._by_id.get(contract_id)
        if contract is None:
            raise BuildContractNotFound(contract_id)
        if contract.project_id != project_id:
            raise PermissionError("build contract does not belong to project")
        return contract

    def latest(self, project_id: str) -> BuildContract | None:
        revisions = self.list_revisions(project_id)
        return revisions[-1] if revisions else None

    def list_revisions(self, project_id: str) -> tuple[BuildContract, ...]:
        rows = [c for c in self._by_id.values() if c.project_id == project_id]
        return tuple(sorted(rows, key=lambda c: c.contract_version))


class PostgresBuildContractRepository:
    """Append-only durable Build Contract repository.

    Migration 020 also rejects UPDATE/DELETE at the database boundary. This
    class deliberately exposes no mutation method beyond inserting a new
    revision.
    """

    def __init__(self, pool: DatabasePool) -> None:
        self._pool = pool

    def save(self, contract: BuildContract) -> None:
        if not contract.verify_fingerprint():
            raise ValueError("cannot save build contract with invalid fingerprint")
        payload = json.dumps(contract.to_dict(), ensure_ascii=False, sort_keys=True)
        try:
            with self._pool.connection() as conn:
                with conn.transaction():
                    with conn.cursor() as cur:
                        # Lock the owning project row first. PostgreSQL does not allow
                        # FOR UPDATE on aggregate rows, and the project lock serializes
                        # revision allocation for this project without a global lock.
                        cur.execute(
                            "SELECT id FROM creator_projects WHERE id=%s FOR UPDATE",
                            (contract.project_id,),
                        )
                        if not cur.fetchone():
                            raise ValueError("project does not exist")
                        cur.execute(
                            "SELECT COALESCE(MAX(contract_version),0) FROM m5_build_contracts WHERE project_id=%s",
                            (contract.project_id,),
                        )
                        row = cur.fetchone()
                        latest = int(row[0]) if row else 0
                        if contract.contract_version != latest + 1:
                            raise ValueError(
                                f"build contract revisions must be monotonic: expected {latest + 1}, got {contract.contract_version}"
                            )
                        cur.execute(
                            "INSERT INTO m5_build_contracts(id,project_id,contract_version,status,capability_plan_fingerprint,contract_fingerprint,contract_json,created_at) "
                            "VALUES(%s,%s,%s,%s,%s,%s,%s::jsonb,%s)",
                            (
                                contract.id,
                                contract.project_id,
                                contract.contract_version,
                                contract.status.value,
                                contract.capability_plan_fingerprint,
                                contract.contract_fingerprint,
                                payload,
                                contract.created_at,
                            ),
                        )
        except ValueError:
            raise
        except Exception as exc:
            text = str(exc).lower()
            if "unique" in text or "duplicate" in text:
                raise ValueError("build contract revision already exists") from exc
            raise

    @staticmethod
    def _decode(row) -> BuildContract:
        data = row[0]
        if isinstance(data, str):
            data = json.loads(data)
        return BuildContract.from_dict(data)

    def get(self, contract_id: str, *, project_id: str) -> BuildContract:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT contract_json FROM m5_build_contracts WHERE id=%s AND project_id=%s",
                    (contract_id, project_id),
                )
                row = cur.fetchone()
                if row:
                    return self._decode(row)
                cur.execute("SELECT project_id FROM m5_build_contracts WHERE id=%s", (contract_id,))
                owner = cur.fetchone()
        if owner:
            raise PermissionError("build contract does not belong to project")
        raise BuildContractNotFound(contract_id)

    def latest(self, project_id: str) -> BuildContract | None:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT contract_json FROM m5_build_contracts WHERE project_id=%s ORDER BY contract_version DESC LIMIT 1",
                    (project_id,),
                )
                row = cur.fetchone()
        return self._decode(row) if row else None

    def list_revisions(self, project_id: str) -> tuple[BuildContract, ...]:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT contract_json FROM m5_build_contracts WHERE project_id=%s ORDER BY contract_version ASC",
                    (project_id,),
                )
                rows = cur.fetchall()
        return tuple(self._decode(row) for row in rows)
