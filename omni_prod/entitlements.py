"""Grant, revoke and list internal entitlements (migration 029).

    python -m omni_prod.entitlements grant  --email E --reason R --by WHO
    python -m omni_prod.entitlements revoke --email E --reason R --by WHO
    python -m omni_prod.entitlements list

Only `INTERNAL_QA` in the `staging` scope exists (founder decision
2026-10-07 #24). A grant is bound to the account id that the email resolves to
at grant time; changing the account's email later does not move or extend it.
Every grant and revocation keeps who, when and why. Output shows entitlement
and account ids only, never emails or the connection string.
"""
from __future__ import annotations

import argparse
import os
import sys
import uuid

from .qa_budget import QA_ENTITLEMENT, QA_ENVIRONMENT


class EntitlementError(RuntimeError):
    pass


def _account_id(cur, email: str) -> str:
    cur.execute('SELECT id FROM creator_accounts WHERE lower(email) = lower(%s)', (email.strip(),))
    rows = cur.fetchall()
    if len(rows) != 1:
        raise EntitlementError('account not found' if not rows else 'email matches more than one account')
    return rows[0][0]


def _required(value: str, name: str) -> str:
    if not value or not value.strip():
        raise EntitlementError(f'{name} is required')
    return value.strip()


def grant(cur, *, email: str, reason: str, granted_by: str) -> dict:
    """Idempotent: an existing active grant is returned unchanged."""
    reason, granted_by = _required(reason, 'reason'), _required(granted_by, 'granted_by')
    account_id = _account_id(cur, _required(email, 'email'))
    cur.execute(
        'SELECT id FROM internal_entitlements WHERE account_id = %s AND entitlement = %s '
        'AND environment = %s AND revoked_at IS NULL',
        (account_id, QA_ENTITLEMENT, QA_ENVIRONMENT),
    )
    existing = cur.fetchone()
    if existing:
        return {'action': 'already_active', 'entitlement_id': existing[0], 'account_id': account_id}
    entitlement_id = f'ent_{uuid.uuid4().hex}'
    cur.execute(
        'INSERT INTO internal_entitlements(id, account_id, entitlement, environment, reason, granted_by) '
        'VALUES (%s, %s, %s, %s, %s, %s)',
        (entitlement_id, account_id, QA_ENTITLEMENT, QA_ENVIRONMENT, reason, granted_by),
    )
    return {'action': 'granted', 'entitlement_id': entitlement_id, 'account_id': account_id,
            'entitlement': QA_ENTITLEMENT, 'environment': QA_ENVIRONMENT}


def revoke(cur, *, email: str, reason: str, revoked_by: str) -> dict:
    reason, revoked_by = _required(reason, 'reason'), _required(revoked_by, 'revoked_by')
    account_id = _account_id(cur, _required(email, 'email'))
    cur.execute(
        'UPDATE internal_entitlements SET revoked_at = now(), revoked_by = %s, revoke_reason = %s '
        'WHERE account_id = %s AND entitlement = %s AND environment = %s AND revoked_at IS NULL RETURNING id',
        (revoked_by, reason, account_id, QA_ENTITLEMENT, QA_ENVIRONMENT),
    )
    row = cur.fetchone()
    return {'action': 'revoked' if row else 'none_active', 'entitlement_id': row[0] if row else None,
            'account_id': account_id}


def list_entitlements(cur) -> list[dict]:
    cur.execute('SELECT id, account_id, entitlement, environment, granted_at, revoked_at '
                'FROM internal_entitlements ORDER BY granted_at')
    return [{'entitlement_id': r[0], 'account_id': r[1], 'entitlement': r[2], 'environment': r[3],
             'granted_at': str(r[4]), 'revoked_at': None if r[5] is None else str(r[5])} for r in cur.fetchall()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='python -m omni_prod.entitlements')
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('grant', 'revoke'):
        p = sub.add_parser(name)
        p.add_argument('--email', required=True)
        p.add_argument('--reason', required=True)
        p.add_argument('--by', required=True, dest='actor')
    sub.add_parser('list')
    args = parser.parse_args(argv)
    url = os.getenv('OMNI_DATABASE_URL', '').strip()
    if not url:
        print('OMNI_DATABASE_URL is not set', file=sys.stderr)
        return 2
    import psycopg
    try:
        with psycopg.connect(url, connect_timeout=10) as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    if args.command == 'grant':
                        result = grant(cur, email=args.email, reason=args.reason, granted_by=args.actor)
                    elif args.command == 'revoke':
                        result = revoke(cur, email=args.email, reason=args.reason, revoked_by=args.actor)
                    else:
                        result = list_entitlements(cur)
    except EntitlementError as exc:
        print(f'refused: {exc}', file=sys.stderr)
        return 1
    print(result)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
