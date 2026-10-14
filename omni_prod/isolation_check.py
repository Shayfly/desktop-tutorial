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
from pathlib import Path
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


def db_instance_identity(url: str | None) -> str | None:
    if not url:
        return None
    u = urlsplit(url)
    return f"{_host(u.hostname)}:{u.port or 5432}" if u.hostname else None


def redis_identity(url: str | None) -> str | None:
    if not url:
        return None
    u = urlsplit(url)
    return f"{(u.hostname or '').lower()}:{u.port or 6379}/{u.path.lstrip('/') or '0'}" if u.hostname else None


def redis_instance_identity(url: str | None) -> str | None:
    if not url:
        return None
    u = urlsplit(url)
    return f"{(u.hostname or '').lower()}:{u.port or 6379}" if u.hostname else None


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


def _compare_service(identity_a, identity_b, instance_a, instance_b, labels, service):
    if not identity_a or not identity_b or not instance_a or not instance_b:
        return {'verdict': 'UNKNOWN', labels[0]: identity_a, labels[1]: identity_b,
                'why': 'a value is missing or invalid on at least one side'}
    if instance_a == instance_b:
        reason = (f'both environments use the same {service} instance; a different logical database or Redis '
                  'number is not isolated' if identity_a != identity_b else
                  f'both environments point at the same {service} instance')
        return {'verdict': 'SHARED', labels[0]: identity_a, labels[1]: identity_b, 'why': reason}
    return {'verdict': 'ISOLATED', labels[0]: identity_a, labels[1]: identity_b,
            'why': f'{service} endpoints differ'}


def compare(a: dict, b: dict, labels=('A', 'B')) -> dict:
    ia, na = identities(a)
    ib, nb = identities(b)
    rows = {}
    db_a = ia['database']
    db_b = ib['database']
    db_instance_a = None if db_a is None else next((db_instance_identity(a.get(k)) for k in DB_KEYS if a.get(k)), None)
    db_instance_b = None if db_b is None else next((db_instance_identity(b.get(k)) for k in DB_KEYS if b.get(k)), None)
    rows['database'] = _compare_service(db_a, db_b, db_instance_a, db_instance_b, labels, 'PostgreSQL')

    redis_a = ia['redis']
    redis_b = ib['redis']
    redis_instance_a = None if redis_a is None else next((redis_instance_identity(a.get(k)) for k in REDIS_KEYS if a.get(k)), None)
    redis_instance_b = None if redis_b is None else next((redis_instance_identity(b.get(k)) for k in REDIS_KEYS if b.get(k)), None)
    rows['redis'] = _compare_service(redis_a, redis_b, redis_instance_a, redis_instance_b, labels, 'Redis')

    if ia['object_storage'] is None or ib['object_storage'] is None:
        rows['object_storage'] = {'verdict': 'UNKNOWN', labels[0]: ia['object_storage'], labels[1]: ib['object_storage'],
                                  'why': 'a value is missing on at least one side'}
    elif ia['object_storage'] == ib['object_storage']:
        rows['object_storage'] = {'verdict': 'SHARED', 'identity': ia['object_storage'],
                                  'why': 'both environments point at the same resource'}
    else:
        rows['object_storage'] = {'verdict': 'ISOLATED', labels[0]: ia['object_storage'], labels[1]: ib['object_storage']}
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
    bad.extend(f'secrets_equality:{k}' for k, value in sec.items() if value == 'SAME')
    return {'labels': list(labels), 'resources': rows, 'notes': na + nb, 'all_isolated': not bad, 'blocking': bad,
        'rule': 'A write test, migration, restore or paid call may only target an environment whose resources are ISOLATED and confirmed by the person.'}


def compare_staging(staging: dict, production: dict, preview: dict) -> dict:
    """Require a labeled staging environment to use separate services from both existing targets."""
    comparisons = {
        'staging_vs_production': compare(staging, production, ('staging', 'production')),
        'staging_vs_preview': compare(staging, preview, ('staging', 'preview')),
    }
    label = (staging.get('OMNI_ENV') or '').strip().lower()
    blocking = []
    if label != 'staging':
        blocking.append('OMNI_ENV must be exactly staging')
    for pair, result in comparisons.items():
        if not result['all_isolated']:
            blocking.extend(f'{pair}:{resource}' for resource in result['blocking'])
    return {
        'environments': ['staging', 'production', 'preview'],
        'staging_environment_label': {'configured': label or None, 'verdict': 'PASS' if label == 'staging' else 'BLOCKED'},
        'comparisons': comparisons,
        'all_isolated': not blocking,
        'blocking': blocking,
        'rule': ('Staging must use separate PostgreSQL and Redis instances from Production and existing Preview. '
                 'Provider-console resource identities must also be checked; different DNS names alone cannot prove '
                 'that aliases do not point to the same managed instance.'),
    }


def main(argv: list[str]) -> int:
    files = [argv[i + 1] for i, x in enumerate(argv[:-1]) if x == '--env-file']
    labels = [argv[i + 1] for i, x in enumerate(argv[:-1]) if x == '--label'] or ['A', 'B']
    if '--show' in argv and len(files) == 1:
        import json
        ids, notes = identities(parse_env(Path(files[0]).read_text(encoding='utf-8')))
        print(json.dumps({'identities': ids, 'notes': notes}, indent=2))
        return 0
    import json
    envs = [parse_env(Path(f).read_text(encoding='utf-8')) for f in files]
    if len(files) == 2 and len(labels) == 2:
        out = compare(*envs, labels=tuple(labels))
    elif len(files) == 3 and len(labels) == 3 and set(labels) == {'staging', 'production', 'preview'}:
        by_label = dict(zip(labels, envs))
        out = compare_staging(by_label['staging'], by_label['production'], by_label['preview'])
    else:
        print('usage: python -m omni_prod.isolation_check --env-file a.env --env-file b.env [--label x --label y] '
              '[or three files labeled staging, production, preview] | --show --env-file a.env', file=sys.stderr)
        return 2
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0 if out['all_isolated'] else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
