"""Backups that are proven by a restore (autonomous completion directive §5).

Run by `.github/workflows/backup-restore.yml` on the worker host, inside the
deployed worker image, with the real environment. Never prints secrets.

    python -m omni_prod.backup snapshot  /bk STAMP   # counts + project manifest (before the dump)
    python -m omni_prod.backup upload    /bk STAMP   # dump + preview data -> object storage
    python -m omni_prod.backup fetch     /bk STAMP   # download the stored copies back (restore source)
    python -m omni_prod.backup verify    /bk STAMP RESTORED_DATABASE_URL
    python -m omni_prod.backup prune     KEEP_DAYS

What is backed up:
  * the platform database (pg_dump custom format, made by the workflow);
  * a project manifest: every project version with its checksum and artifact
    key; the artifacts themselves are content-addressed, immutable objects in
    the same store and are re-verified on every run;
  * generated-app data of previews (/var/lib/omni-preview/data, tar.gz).

What "verified" means here: the dump that was *uploaded* is downloaded again
and restored into an empty PostgreSQL; the restored database must hold the
same migrations, at least the counted rows of every durable table, and every
project version must rebuild from its artifact to its recorded checksum; the
uploaded data archive must contain exactly the files (and SHA-256) of the
live data directory at snapshot time.

Known limit: the backups live in the same object store as the artifacts (one
failure domain); the managed database has its own point-in-time recovery.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import tarfile
import time
from datetime import datetime, timedelta, timezone

PREFIX = 'backups'
DURABLE_TABLES = ('creator_accounts', 'creator_projects', 'project_versions', 'build_jobs', 'build_requests',
                  'credit_reservations', 'creator_subscriptions', 'm5_build_contracts', 'modification_requests',
                  'project_briefs', 'build_approvals', 'internal_entitlements', 'project_previews', 'schema_migrations')
DATA_ROOT = os.getenv('OMNI_PREVIEW_DATA_ROOT', '/var/lib/omni-preview/data')


def _pool():
    from .investor_app import _v28_pool
    if _v28_pool is None:
        raise RuntimeError('OMNI_CREATOR_PERSISTENCE=postgres is required')
    return _v28_pool


def _store():
    from .investor_app import _v28
    store = getattr(_v28.engine.workspace, 'storage', None)
    if store is None:
        raise RuntimeError('no object storage configured')
    return store


def _counts(conn) -> dict:
    out = {}
    for table in DURABLE_TABLES:
        if conn.execute('SELECT to_regclass(%s)', (f'public.{table}',)).fetchone()[0] is None:
            continue
        out[table] = conn.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
    return out


def _data_digests(root: str) -> dict:
    digests = {}
    if not os.path.isdir(root):
        return digests
    for dirpath, _, files in os.walk(root):
        for name in files:
            path = os.path.join(dirpath, name)
            with open(path, 'rb') as f:
                digests[os.path.relpath(path, root)] = hashlib.sha256(f.read()).hexdigest()
    return digests


def snapshot(bk: str, stamp: str) -> dict:
    with _pool().connection() as conn:
        counts = _counts(conn)
        migrations = [r[0] for r in conn.execute('SELECT version FROM schema_migrations ORDER BY version').fetchall()]
        versions = [{'id': r[0], 'project_id': r[1], 'sha256': r[2], 'artifact_key': r[3]}
                    for r in conn.execute('SELECT id, project_id, repository_sha256, artifact_key FROM project_versions '
                                          'ORDER BY created_at').fetchall()]
    manifest = {'stamp': stamp, 'created_at': datetime.now(timezone.utc).isoformat(), 'counts': counts,
                'migrations': migrations, 'versions': versions, 'data_files': _data_digests(DATA_ROOT)}
    with open(os.path.join(bk, 'manifest.json'), 'w') as f:
        json.dump(manifest, f)
    return {'tables': len(counts), 'versions': len(versions), 'data_files': len(manifest['data_files']),
            'migrations': migrations[-1] if migrations else None}


def _key(stamp: str, name: str) -> str:
    return f'{PREFIX}/{stamp}/{name}'


def upload(bk: str, stamp: str) -> dict:
    store = _store()
    out = {}
    for name in ('manifest.json', 'db.dump', 'preview-data.tgz'):
        path = os.path.join(bk, name)
        with open(path, 'rb') as f:
            data = f.read()
        obj = store.put_bytes(_key(stamp, name), data)
        out[name] = {'bytes': obj.size, 'sha256': obj.sha256[:16]}
    return out


def fetch(bk: str, stamp: str) -> dict:
    """Download the stored copies (with their SHA-256 verified) as the restore source."""
    store = _store()
    os.makedirs(os.path.join(bk, 'restore'), exist_ok=True)
    out = {}
    for name in ('manifest.json', 'db.dump', 'preview-data.tgz'):
        data = store.get_bytes(_key(stamp, name), verify=True)
        with open(os.path.join(bk, 'restore', name), 'wb') as f:
            f.write(data)
        out[name] = len(data)
    return out


def verify(bk: str, stamp: str, restored_url: str) -> dict:
    import psycopg
    from .workspace import _checksum
    with open(os.path.join(bk, 'restore', 'manifest.json')) as f:
        manifest = json.load(f)
    result: dict = {'stamp': stamp}
    with psycopg.connect(restored_url) as conn:
        restored_counts = _counts(conn)
        restored_migrations = [r[0] for r in conn.execute('SELECT version FROM schema_migrations ORDER BY version')]
        restored_versions = {r[0]: (r[1], r[2]) for r in conn.execute(
            'SELECT id, repository_sha256, artifact_key FROM project_versions')}
    short = {t: (manifest['counts'][t], restored_counts.get(t)) for t in manifest['counts']
             if restored_counts.get(t, -1) < manifest['counts'][t]}
    result['tables'] = {'checked': len(manifest['counts']), 'short': short}
    result['migrations_equal'] = restored_migrations[:len(manifest['migrations'])] == manifest['migrations']
    # Every version rebuilds from its artifact to its recorded checksum.
    from .investor_app import _v28
    ws = _v28.engine.workspace
    bad, rebuilt = [], 0
    for v in manifest['versions']:
        row = restored_versions.get(v['id'])
        if row is None or row[0] != v['sha256']:
            bad.append(f"{v['id']}: missing or different in the restored database")
            continue
        try:
            repo = ws._unzip_repo(_store().get_bytes(row[1], verify=True))
            if _checksum(repo) != v['sha256']:
                bad.append(f"{v['id']}: checksum")
            else:
                rebuilt += 1
        except Exception as exc:
            bad.append(f"{v['id']}: {type(exc).__name__}")
    result['projects'] = {'versions': len(manifest['versions']), 'rebuilt': rebuilt, 'failures': bad[:10]}
    expected = manifest['data_files']
    restored, missing = compare_data_archive(os.path.join(bk, 'restore', 'preview-data.tgz'), expected)
    result['preview_data'] = {'files': len(expected), 'restored': restored, 'missing_or_changed': missing[:10]}
    result['verified'] = (not short and result['migrations_equal'] and not bad and not missing)
    return result


def compare_data_archive(path: str, expected: dict) -> tuple[int, list[str]]:
    """(files in the archive, files of the snapshot that are missing or differ)."""
    restored = {}
    with tarfile.open(path, 'r:gz') as tar:
        for m in tar.getmembers():
            if m.isfile():
                rel = m.name.split('/', 1)[1] if m.name.startswith('data/') else m.name
                restored[rel] = hashlib.sha256(tar.extractfile(m).read()).hexdigest()
    return len(restored), sorted(k for k in expected if restored.get(k) != expected[k])


def prune(keep_days: int) -> dict:
    store = _store()
    cutoff = datetime.now(timezone.utc) - timedelta(days=int(keep_days))
    client, bucket = store.client, store.bucket
    stamps = set()
    paginator = client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix=PREFIX + '/'):
        for obj in page.get('Contents', []):
            stamps.add((obj['Key'].split('/')[1], obj['Key']))
    removed = 0
    for stamp, key in stamps:
        try:
            when = datetime.strptime(stamp, '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if when < cutoff:
            client.delete_object(Bucket=bucket, Key=key)
            removed += 1
    kept = len({s for s, _ in stamps})
    return {'objects_removed': removed, 'backups_listed': kept}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0]
    try:
        if cmd == 'snapshot':
            out = snapshot(argv[1], argv[2])
        elif cmd == 'upload':
            out = upload(argv[1], argv[2])
        elif cmd == 'fetch':
            out = fetch(argv[1], argv[2])
        elif cmd == 'verify':
            out = verify(argv[1], argv[2], argv[3])
        elif cmd == 'prune':
            out = prune(int(argv[1]))
        else:
            raise SystemExit(f'unknown command {cmd}')
    except Exception as exc:
        print(f'::error title=backup {cmd}::{type(exc).__name__}: {str(exc)[:400]}')
        return 1
    ok = out.get('verified', True)
    print(f"::{'notice' if ok else 'error'} title=backup {cmd}::" + json.dumps(out, default=str)[:3500])
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
