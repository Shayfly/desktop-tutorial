"""72 (Michael 2026-11-11): a Vercel Preview never writes to Production's database.

Evidence (PR 312, /api/v28/deployment on a preview): the Neon integration of 148ai-db-v2 already creates a
`preview/<git branch>` database branch for every deployment and hands it to the deployment as DB2_DATABASE_URL, but the
app reads OMNI_DATABASE_URL, which on Preview is Production's endpoint. So every preview test -- every smoke account,
every reservation -- landed in Production.

`apply()` runs once at the Vercel entrypoint, before anything reads the environment: on VERCEL_ENV=preview it points
OMNI_DATABASE_URL at the preview's own branch. If there is no branch database, or it is Production's, the preview
gets NO database (requests that need one answer 503) -- it never falls back to Production. Production and the worker
are untouched (they never run with VERCEL_ENV=preview). `OMNI_PREVIEW_DATABASE=shared` restores the old sharing,
as an explicit, logged choice.
"""
from __future__ import annotations

import logging
import os

from .isolation_check import db_identity

BRANCH_KEY = 'DB2_DATABASE_URL'          # the 148ai-db-v2 Neon integration's per-preview branch
_LOG = logging.getLogger('omni_prod.preview_isolation')


def apply(env=None) -> str:
    """Returns what was done: 'not_preview' | 'shared' | 'branch' | 'no_database'."""
    env = os.environ if env is None else env
    if env.get('VERCEL_ENV') != 'preview':
        return 'not_preview'
    if env.get('OMNI_PREVIEW_DATABASE', '').strip().lower() == 'shared':
        _LOG.warning('preview_isolation: OMNI_PREVIEW_DATABASE=shared -- this preview writes to the shared database')
        return 'shared'
    production = db_identity(env.get('OMNI_DATABASE_URL'))
    branch_url = (env.get(BRANCH_KEY) or '').strip()
    branch = db_identity(branch_url)
    if branch and branch != production:
        env['OMNI_DATABASE_URL'] = branch_url
        _LOG.info('preview_isolation: database = preview branch %s', branch)
        return 'branch'
    env.pop('OMNI_DATABASE_URL', None)   # fail closed: no database rather than Production's
    _LOG.warning('preview_isolation: no separate preview database (branch=%s); database disabled', branch)
    return 'no_database'
