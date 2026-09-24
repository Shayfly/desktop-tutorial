from __future__ import annotations
import json
from .product_spec import ProductSpec


class SpecNotFound(KeyError):
    pass


class PostgresSpecRepository:
    """M4B: durable, version-linked `ProductSpec` storage.

    The invariant this repository exists to hold: `ProjectVersion N <->
    ProductSpec N`, one immutable row per version id (`project_version_specs`,
    migration 016 -- `version_id` is the primary key, not a surrogate). There
    is deliberately no `update()`: the only way a project's spec changes is a
    *new* version getting its *own* spec row, so `get(version_id, ...)`
    always returns the exact spec that version was built/modified against --
    never "the project's latest spec" for an older version being re-opened,
    which is the specific bug M4B's directive names ("never load latest spec
    when modifying an older version").
    """

    def __init__(self, pool):
        self.pool = pool

    def save(self, *, version_id: str, project_id: str, spec: ProductSpec, cur=None) -> None:
        """Idempotent: ON CONFLICT DO NOTHING, matching
        subscription_store.py's reserve() convention for the same reason --
        a retried write for a version id that already has a spec row is a
        safe no-op (the row is immutable, so there is nothing to reconcile),
        not an error. Pass `cur` to participate in a caller-managed
        transaction (e.g. committing the candidate version and its spec
        atomically), the same pattern job_repository.py's
        create_with_cursor()/create_outbox() use."""
        sql = (
            "INSERT INTO project_version_specs(version_id, project_id, spec_json) "
            "VALUES (%s, %s, %s::jsonb) ON CONFLICT (version_id) DO NOTHING"
        )
        params = (version_id, project_id, json.dumps(spec.to_dict()))
        if cur is not None:
            cur.execute(sql, params)
            return
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as c:
                    c.execute(sql, params)

    def get(self, version_id: str, project_id: str) -> ProductSpec:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT spec_json FROM project_version_specs WHERE version_id = %s AND project_id = %s",
                    (version_id, project_id),
                )
                row = cur.fetchone()
        if not row:
            raise SpecNotFound(f'no spec stored for version {version_id!r}')
        data = row[0]
        if isinstance(data, str):
            data = json.loads(data)
        return ProductSpec.from_dict(data)
