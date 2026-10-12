"""Effective Preview vs Production isolation check (DB, queues, storage) -- read-only, prints NO secrets.

    python -m omni_prod.isolation_check --env-file preview.env --env-file production.env [--label preview --label production]
    python -m omni_prod.isolation_check --show --env-file preview.env

Each --env-file is a dotenv-style file the OPERATOR produced (for Vercel: `vercel env pull <file> --environment=<target>`;
for the worker host: its .env). The tool never connects to anything, never writes, and prints only non-secret identity
fingerprints: host (Neon `-pooler` normalised away), port, database / Redis db number, bucket and queue names. Equal
fingerprints = SHARED; different = ISOLATED; a missing value on either side = UNKNOWN. Secrets are only compared for
equality and the result is a word, never a value or hash.

Exit code 0 only if every checked resource is ISOLATED. SHARED or UNKNOWN is a warning sign: no test write, migration,
backup restore or paid call may target the environment until the person has confirmed the target.
"""
from __future__ import annotations

import hashlib
import re
import sys
from urllib.parse import urlsplit

DB_KEYS = ('OMNI_DATABASE_URL', 'DATABASE_URL', 'POSTGRES_URL', 'POSTGRES_PRISMA_URL', 'POSTGRES_URL_NON_POOLING')
REDIS_KEYS = ('OMNI_REDIS_URL', 'KV_URL', 'REDIS_URL')
SECRET_KEYS = ('OMNI_SECRET_KEY', 'OMNI_SANDBOX_SHARED_SECRET')


def parse_env(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        m = re.match(r'\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$', line)
        if m and not line.lstrip().startswith('#'):
            v = m.group(2).strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in '"\'':
                v = v[1:-1]
            out[m.group(1)] = v
    return out


def _host(h: str) -> str:
    h = (h or '').lower()
    return re.sub(r'-pooler(?=\.)', '', h)          # Neon pooled and direct endpoints are the same database


def db_identity(url: str | None) -> str | None:
    if not url:
        return None
    u = urlsplit(url)
    return f"{_host(u.hostname)}:{u.port or 5432}/{u.path.lstrip('/')}" if u.hostname else None


def redis_identity(url: str | None) -> str | None:
    if not url:
        return None
    u = urlsplit(url)
    return f"{(u.hostname or '').lower()}:{u.port or 6379}/{u.path.lstrip('/') or '0'}" if u.hostname else None


def s3_identity(env: dict) -> str | None:
    ep, bucket = env.get('OMNI_S3_ENDPOINT'), env.get('OMNI_S3_BUCKET')
    if not (ep and bucket):
        return None
    return f"{(urlsplit(ep).hostname or ep).lower()}/{bucket}" + (f"/{env['OMNI_S3_PREFIX']}" if env.get('OMNI_S3_PREFIX') else '')


def identities(env: dict) -> dict:
    """Non-secret identities. A resource may be configured under several variable names; they must agree."""
    out, notes = {}, []
    dbs = {k: db_identity(env.get(k)) for k in DB_KEYS if env.get(k)}
    out['database'] = next(iter(set(dbs.values())), None) if len(set(dbs.values())) <= 1 else None
    if len(set(dbs.values())) > 1:
        notes.append(f'database variables disagree with each other: {sorted(dbs)}')
    reds = {k: redis_identity(env.get(k)) for k in REDIS_KEYS if env.get(k)}
    out['redis'] = next(iter(set(reds.values())), None) if len(set(reds.values())) <= 1 else None
    if len(set(reds.values())) > 1:
        notes.append(f'redis variables disagree with each other: {sorted(reds)}')
    out['object_storage'] = s3_identity(env)
    out['preview_queue_host'] = env.get('OMNI_PREVIEW_RUNTIME_HOST') or None
    out['environment_label'] = env.get('OMNI_ENV') or None
    return out, notes


def compare(a: dict, b: dict, labels=('A', 'B')) -> dict:
    ia, na = identities(a)
    ib, nb = identities(b)
    rows = {}
    for res in ('database', 'redis', 'object_storage'):
        if ia[res] is None or ib[res] is None:
            rows[res] = {'verdict': 'UNKNOWN', labels[0]: ia[res], labels[1]: ib[res],
                         'why': 'a value is missing (or its variables disagree) on at least one side'}
        elif ia[res] == ib[res]:
            rows[res] = {'verdict': 'SHARED', 'identity': ia[res], 'why': 'both environments point at the same resource'}
        else:
            rows[res] = {'verdict': 'ISOLATED', labels[0]: ia[res], labels[1]: ib[res]}
    # queues live in Redis: sharing Redis means sharing queues unless the queue names differ per environment
    rows['queues'] = {'verdict': rows['redis']['verdict'],
                      'why': ('queues are RQ keys inside Redis: same Redis = same omni-builds / omni-previews / omni-intake queues, so a '
                              'Preview deployment can enqueue work a Production worker executes' if rows['redis']['verdict'] == 'SHARED'
                              else 'follows the Redis verdict')}
    sec = {}
    for k in SECRET_KEYS:
        if a.get(k) and b.get(k):
            sec[k] = 'SAME' if a[k] == b[k] else 'DIFFERENT'
        else:
            sec[k] = 'UNKNOWN'
    rows['secrets_equality'] = sec
    bad = [r for r, v in rows.items() if r != 'secrets_equality' and v['verdict'] != 'ISOLATED']
    return {'labels': list(labels), 'resources': rows, 'notes': na + nb, 'all_isolated': not bad and not any(
        v == 'SAME' for v in sec.values()), 'blocking': bad,
        'rule': 'A write test, migration, restore or paid call may only target an environment whose resources are ISOLATED and confirmed by the person.'}


def main(argv: list[str]) -> int:
    files = [argv[i + 1] for i, x in enumerate(argv[:-1]) if x == '--env-file']
    labels = [argv[i + 1] for i, x in enumerate(argv[:-1]) if x == '--label'] or ['A', 'B']
    if '--show' in argv and len(files) == 1:
        import json
        ids, notes = identities(parse_env(open(files[0], encoding='utf-8').read()))
        print(json.dumps({'identities': ids, 'notes': notes}, indent=2))
        return 0
    if len(files) != 2 or len(labels) != 2:
        print('usage: python -m omni_prod.isolation_check --env-file a.env --env-file b.env [--label x --label y] | --show --env-file a.env',
              file=sys.stderr)
        return 2
    import json
    out = compare(*(parse_env(open(f, encoding='utf-8').read()) for f in files), labels=tuple(labels))
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0 if out['all_isolated'] else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
