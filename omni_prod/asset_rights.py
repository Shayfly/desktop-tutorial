"""S13.3 (the owner, 2026-11-27, answer 6): the rights record of a generated asset.

One row per asset in `asset_rights` (infra/postgres/050_media_infra.sql): who generated it (provider, model, the
provider's task id), on what terms (the terms URL, the day they were read, whether the terms allow commercial use, what
they forbid), and who owns it. The owner is always the customer; the table refuses any other value.

The gate. require() is the only question the delivery path asks (media_store.TenantMediaStore.deliver and .link):
  - no row for (account, project, sha256)           RightsMissing   (unknown blocks; there is no default row)
  - commercial_use is false                         RightsRestricted
  - the terms were read more than 90 days ago        RightsStale     (the freshness rule of the plan: a year-old reading
                                                                     of a provider's terms is not a reading)
  - the database cannot answer                       the error propagates; nothing is delivered
A row is evidence: it is never updated or deleted (trigger). Recording the same asset twice with the same facts is
accepted and changes nothing; with different facts it raises RightsConflict, so a second run cannot rewrite history.
Nothing here calls a provider and nothing is estimated: the fields are what the caller read, and a caller that read
nothing cannot pass the checks (an https terms link, a named provider and model, a real date).
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

from .artifact_keys import media_key_prefix

TERMS_MAX_AGE_DAYS = 90
KINDS = ('image', 'sprite', 'audio', 'video', 'model')
MIGRATION = '050_media_infra'
MISSING_TABLE = f'MISSING: migration {MIGRATION} (infra/postgres/{MIGRATION}.sql) is not applied to this database'
_HEX = re.compile(r'[0-9a-f]{64}')
_COLUMNS = ('account_id', 'project_id', 'build_id', 'sha256', 'media_key', 'kind', 'mime', 'provider', 'model',
            'provider_task_id', 'terms_url', 'terms_read_on', 'commercial_use', 'restrictions', 'prompt_sha256')


class RightsError(RuntimeError):
    code = 'rights_error'


class RightsMissing(RightsError):
    code = 'rights_missing'


class RightsRestricted(RightsError):
    code = 'rights_restricted'


class RightsStale(RightsError):
    code = 'rights_terms_stale'


class RightsConflict(RightsError):
    code = 'rights_conflict'


@dataclass(frozen=True)
class AssetRight:
    account_id: str
    project_id: str
    sha256: str
    media_key: str
    kind: str
    mime: str
    provider: str
    model: str
    terms_url: str
    terms_read_on: dt.date
    commercial_use: bool
    build_id: str | None = None
    provider_task_id: str | None = None
    restrictions: str = ''
    prompt_sha256: str | None = None
    owner: str = 'customer'

    def validate(self) -> None:
        if self.owner != 'customer':
            raise ValueError('the owner of a generated asset is the customer')
        if self.kind not in KINDS:
            raise ValueError(f'unknown asset kind {self.kind!r}')
        if not _HEX.fullmatch(self.sha256 or ''):
            raise ValueError('sha256 must be 64 hex digits')
        if self.prompt_sha256 is not None and not _HEX.fullmatch(self.prompt_sha256):
            raise ValueError('prompt_sha256 must be 64 hex digits or absent')
        if not (self.provider or '').strip() or not (self.model or '').strip():
            raise ValueError('a rights record names its provider and model')
        if not re.fullmatch(r'https://[^\s]+', self.terms_url or ''):
            raise ValueError('terms_url must be an https link to the terms that were read')
        if not isinstance(self.terms_read_on, dt.date) or isinstance(self.terms_read_on, dt.datetime):
            raise ValueError('terms_read_on is the date the terms were read (a date)')
        if not isinstance(self.commercial_use, bool):
            raise ValueError('commercial_use is true or false, never unknown')
        if not self.media_key.startswith(media_key_prefix(self.account_id) + f'projects/{self.project_id}/media/'):
            raise ValueError("the asset's key is not under its account and project")

    def row(self) -> tuple:
        return tuple(getattr(self, c) for c in _COLUMNS)


def _missing(exc: Exception) -> bool:
    return 'asset_rights' in str(exc) and 'does not exist' in str(exc)


class AssetRightsStore:
    """The rights gate over PostgreSQL. `pool` is omni_prod.db.DatabasePool (anything with .connection())."""

    def __init__(self, pool, *, today=None) -> None:
        self._pool = pool
        self._today = today or dt.date.today

    def record(self, right: AssetRight) -> bool:
        """True when a row was written, False when the same facts were already recorded. RightsConflict otherwise."""
        right.validate()
        placeholders = ', '.join(['%s'] * len(_COLUMNS))
        with self._pool.connection() as conn:
            with conn.transaction():
                cur = conn.execute(
                    f'INSERT INTO asset_rights ({", ".join(_COLUMNS)}) VALUES ({placeholders}) '
                    'ON CONFLICT (account_id, project_id, sha256) DO NOTHING', right.row())
                if cur.rowcount == 1:
                    return True
                have = self._select(conn, right.account_id, right.project_id, right.sha256)
        if have is None or have.row() != right.row():
            raise RightsConflict('this asset already has a rights record with other facts; a record is never rewritten')
        return False

    @staticmethod
    def _select(conn, account_id, project_id, sha256) -> AssetRight | None:
        cols = ', '.join(_COLUMNS)
        found = conn.execute(f'SELECT {cols} FROM asset_rights WHERE account_id = %s AND project_id = %s AND sha256 = %s',
                             (account_id, project_id, sha256)).fetchone()
        if found is None:
            return None
        d = dict(zip(_COLUMNS, found))
        return AssetRight(owner='customer', **d)

    def get(self, *, account_id: str, project_id: str, sha256: str) -> AssetRight | None:
        try:
            with self._pool.connection() as conn:
                return self._select(conn, account_id, project_id, sha256)
        except Exception as exc:
            if _missing(exc):
                raise RightsError(MISSING_TABLE) from exc
            raise

    def require(self, *, account_id: str, project_id: str, sha256: str) -> AssetRight:
        right = self.get(account_id=account_id, project_id=project_id, sha256=sha256)
        if right is None:
            raise RightsMissing('this file has no rights record; it is not delivered')
        if not right.commercial_use:
            raise RightsRestricted(f'the terms of {right.provider} do not allow commercial use: {right.restrictions or "no reason recorded"}')
        age = (self._today() - right.terms_read_on).days
        if age > TERMS_MAX_AGE_DAYS:
            raise RightsStale(f'the terms of {right.provider} were read {age} days ago (limit {TERMS_MAX_AGE_DAYS}); read them again')
        return right

    def stale_terms(self) -> list[tuple[str, str, int]]:
        """(provider, model, age in days) of every provider whose newest reading of its terms is over the limit. The
        freshness check (a path 'provider terms' in critical-path-freshness.yml) reads this."""
        with self._pool.connection() as conn:
            rows = conn.execute('SELECT provider, model, max(terms_read_on) FROM asset_rights GROUP BY provider, model').fetchall()
        today = self._today()
        return sorted((p, m, (today - d).days) for p, m, d in rows if (today - d).days > TERMS_MAX_AGE_DAYS)
