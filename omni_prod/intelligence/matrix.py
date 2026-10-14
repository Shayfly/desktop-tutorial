"""Generated Provider Matrix (Wave A §3): PROVIDER_MATRIX.json + docs/PROVIDER_MATRIX.md.

    python -m omni_prod.intelligence.matrix --write   # regenerate
    python -m omni_prod.intelligence.matrix --check   # CI: fail on drift or inflation

Sources (never the generated files): `inventory` (typed entries + evidence),
`prices` (effective-dated schedule), `lifecycle` (retirements),
`infra/worker-host/model-catalog.json` (what the worker routes),
`agent_os.providers` (commercial status) and `task_policy` (eligibility).

`validate()` refuses:
  * a state stronger than its evidence (credential/connection/verification)
  * PRODUCTION_LIVE (no production exists)
  * a catalog route missing from the inventory, or an inventory entry claiming
    to be in the catalog that is not
  * a catalog price different from the price schedule in force
  * a routable entry with no source-backed price, or a RETIRED model in the catalog
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from . import lifecycle, prices, states as S, task_policy
from .inventory import DEPLOY_NOTICE, GAPS, INVENTORY, LEDGER, LEDGER_OK_CALLS, LEGACY_ROUTES, PROBE, GOLDEN, REPLICATE_ACCOUNT, VERCEL_ENV_NAMES

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / 'infra' / 'worker-host' / 'model-catalog.json'
JSON_OUT = ROOT / 'PROVIDER_MATRIX.json'
MD_OUT = ROOT / 'docs' / 'PROVIDER_MATRIX.md'
SCHEMA = 'provider-matrix/1'
# The matrix is a dated statement: lifecycle/price "now" is this day, so a
# regenerated file is reproducible and changes only when the date is bumped.
AS_OF = date(2026, 10, 11)

CREDENTIAL_EVIDENCE = {DEPLOY_NOTICE.ref, VERCEL_ENV_NAMES.ref}
CONNECTION_EVIDENCE = {PROBE.ref, REPLICATE_ACCOUNT.ref}
EXECUTION_EVIDENCE = {LEDGER.ref, GOLDEN.ref}


def load_catalog(path: Path = CATALOG) -> list[dict]:
    return json.loads(path.read_text(encoding='utf-8'))


def _health_of(entry) -> str:
    if entry.health_note.startswith('HTTP 429 no credits') or 'credit balance' in entry.health_note:
        return S.CREDIT_EXHAUSTED
    if entry.verification_state == S.REAL_EXECUTION_VERIFIED:
        return S.HEALTHY
    return S.UNKNOWN


def _implementation(entry) -> str:
    if entry.execution_adapter.startswith('none'):
        return 'NOT_IMPLEMENTED'
    if entry.verification_state == S.REAL_EXECUTION_VERIFIED:
        return 'REAL_SERVER_VERIFIED'
    if entry.health_note:
        return 'BLOCKED'
    return 'IMPLEMENTED'


def build(catalog: list[dict] | None = None, as_of: date = AS_OF) -> dict:
    from ..agent_os.providers import commercial_status
    catalog = load_catalog() if catalog is None else catalog
    by_name = {c['name']: c for c in catalog}
    rows = []
    for e in INVENTORY:
        price = prices.price_at(e.provider_model_id, as_of)
        life = lifecycle.state(e.provider_model_id, as_of)
        health = _health_of(e)
        cat = by_name.get(e.model_key)
        status, plan, basis = commercial_status(e.model_key)
        rows.append({
            'provider_key': e.provider_key, 'model_key': e.model_key, 'provider_model_id': e.provider_model_id,
            'id_source': e.id_source, 'model_family': e.model_family, 'provider_type': e.provider_type,
            'capability_types': list(e.capability_types), 'intended_task_types': list(e.intended_task_types),
            'execution_adapter': e.execution_adapter, 'adapter_implementation_path': e.adapter_implementation_path,
            'supported_modalities': list(e.supported_modalities), 'supported_languages': list(e.supported_languages),
            'context_window': e.context_window, 'maximum_output_tokens': e.maximum_output_tokens,
            'supports_tool_calls': e.supports_tool_calls, 'supports_structured_output': e.supports_structured_output,
            'supports_streaming': e.supports_streaming, 'supports_reasoning': e.supports_reasoning,
            'supports_vision': e.supports_vision, 'supports_function_calling': e.supports_function_calling,
            'credential_reference_names': list(e.credential_reference_names), 'credential_scope': e.credential_scope,
            'credential_state': e.credential_state, 'connection_state': e.connection_state,
            'verification_state': e.verification_state, 'implementation_status': _implementation(e),
            'health': health,
            'availability': S.availability_of(credential_state=e.credential_state, health=health, lifecycle=life)
            if e.in_catalog else 'NOT_ROUTED',
            'last_verified_at': e.last_verified_at,
            'evidence_reference': [f'{x.ref} @ {x.at}' + (f' (commit {x.commit})' if x.commit else '') + f': {x.observed}'
                                   for x in e.evidence],
            'price_schedule_reference': None if price is None else
            {'effective_from': str(price.effective_from), 'effective_until': str(price.effective_until) if price.effective_until else None,
             'source_url': price.source_url, 'verified_at': price.verified_at},
            'price_in_force': None if price is None else price.to_dict(),
            'price_changes_announced': [r.to_dict() for r in prices.history(e.provider_model_id) if r.effective_from > as_of],
            'deprecation_state': life, 'replacement_model': (lifecycle.BY_MODEL.get(e.provider_model_id).successor
                                                             if e.provider_model_id in lifecycle.BY_MODEL else None),
            'deprecation_warning': lifecycle.warning(e.provider_model_id, as_of),
            'commercial_status': status, 'commercial_plan': plan,
            'commercial_usage_constraints': e.commercial_usage_constraints,
            'security_constraints': e.security_constraints, 'known_limitations': e.known_limitations,
            'fallback_eligibility': e.fallback_eligibility, 'in_worker_catalog': e.in_catalog,
            'catalog_quality': cat.get('quality') if cat else None,
            'eligible_tasks': [t.key for t in task_policy.TASK_CLASSES.values()
                               if cat and task_policy.eligible(t.key, model_id=e.provider_model_id, quality=int(cat['quality']))],
            'current_operational_status': _operational(e, health, life),
            'blocker': e.health_note,
        })
    return {
        'schema': SCHEMA, 'as_of': str(as_of),
        'summary': _summary(rows),
        'models': rows,
        'task_classes': task_policy.describe(),
        'legacy_routes': list(LEGACY_ROUTES),
        'capability_gaps': list(GAPS),
        'state_rules': {f'{a}={v}': rule for (a, v), rule in S.EVIDENCE_REQUIRED.items()},
    }


def _operational(e, health, life) -> str:
    if life == lifecycle.RETIRED:
        return 'RETIRED: never routed'
    if not e.in_catalog:
        return 'candidate: not routed (not in the worker catalog)'
    if health == S.CREDIT_EXHAUSTED:
        return 'configured but blocked: provider account has no credit'
    if e.verification_state == S.REAL_EXECUTION_VERIFIED:
        return 'routing real builds'
    return 'configured, unverified'


def _summary(rows) -> dict:
    out: dict[str, dict[str, int]] = {}
    for axis in ('credential_state', 'connection_state', 'verification_state', 'availability', 'implementation_status'):
        counts: dict[str, int] = {}
        for r in rows:
            counts[r[axis]] = counts.get(r[axis], 0) + 1
        out[axis] = dict(sorted(counts.items()))
    out['models'] = len(rows)
    return out


def validate(matrix: dict | None = None, catalog: list[dict] | None = None) -> list[str]:
    catalog = load_catalog() if catalog is None else catalog
    matrix = build(catalog) if matrix is None else matrix
    problems = list(prices.validate())
    by_key = {r['model_key']: r for r in matrix['models']}
    if len(by_key) != len(matrix['models']):
        problems.append('duplicate model_key in the inventory')
    for e in INVENTORY:
        refs = {x.ref for x in e.evidence}
        if e.credential_state == S.CREDENTIAL_PRESENT and not refs & CREDENTIAL_EVIDENCE:
            problems.append(f'{e.model_key}: CREDENTIAL_PRESENT without a credential observation')
        if e.connection_state in (S.CONNECTION_TESTED, S.CONNECTION_FAILED) and not refs & CONNECTION_EVIDENCE:
            problems.append(f'{e.model_key}: {e.connection_state} without a recorded provider answer')
        if e.verification_state == S.REAL_EXECUTION_VERIFIED:
            if not refs & EXECUTION_EVIDENCE or LEDGER_OK_CALLS.get(e.provider_model_id, 0) <= 0:
                problems.append(f'{e.model_key}: REAL_EXECUTION_VERIFIED without execution evidence '
                                '(no successful ledger call for this model id)')
            if e.connection_state != S.CONNECTION_TESTED:
                problems.append(f'{e.model_key}: verified execution requires a tested connection')
            if e.health_note:
                problems.append(f'{e.model_key}: verified but carries a blocking health note')
        if e.verification_state == S.PRODUCTION_LIVE:
            problems.append(f'{e.model_key}: PRODUCTION_LIVE claimed but no production environment exists')
        for v, axis in ((e.credential_state, S.CREDENTIAL_STATES), (e.connection_state, S.CONNECTION_STATES),
                        (e.verification_state, S.VERIFICATION_STATES)):
            if v not in axis:
                problems.append(f'{e.model_key}: unknown state {v}')
    inv_catalog = {e.model_key: e for e in INVENTORY if e.in_catalog}
    for c in catalog:
        e = inv_catalog.get(c['name'])
        if e is None:
            problems.append(f'catalog route {c["name"]} is not in the inventory')
            continue
        if e.provider_model_id != c['model']:
            problems.append(f'{c["name"]}: catalog model {c["model"]} != inventory {e.provider_model_id}')
        if (e.credential_reference_names or ('',))[0] != c.get('api_key_env'):
            problems.append(f'{c["name"]}: credential reference differs from the catalog api_key_env')
        row = prices.price_at(c['model'], AS_OF)
        if row is None:
            problems.append(f'{c["name"]}: routable model without a source-backed price')
        elif (Decimal(str(c['input_per_million'])) != row.input_per_million
              or Decimal(str(c['output_per_million'])) != row.output_per_million):
            problems.append(f'{c["name"]}: catalog price {c["input_per_million"]}/{c["output_per_million"]} != schedule '
                            f'{row.input_per_million}/{row.output_per_million} (effective {row.effective_from})')
        if lifecycle.state(c['model'], AS_OF) == lifecycle.RETIRED:
            problems.append(f'{c["name"]}: RETIRED model in the catalog')
    names = {c['name'] for c in catalog}
    for key in inv_catalog:
        if key not in names:
            problems.append(f'{key}: inventory says in_catalog but the catalog has no such route')
    return problems


def markdown(m: dict) -> str:
    s = m['summary']
    lines = [
        '# Provider Matrix (generated)', '',
        f'Generated by `python -m omni_prod.intelligence.matrix --write` from `omni_prod/intelligence/` '
        f'(schema `{m["schema"]}`, as of {m["as_of"]}). Do not edit by hand.', '',
        'Axes are independent: CREDENTIAL_PRESENT ≠ CONNECTION_TESTED ≠ REAL_EXECUTION_VERIFIED ≠ PRODUCTION_LIVE. '
        'No model is PRODUCTION_LIVE (no production environment exists).', '',
        f'Summary: {s["models"]} entries · credential {s["credential_state"]} · connection {s["connection_state"]} · '
        f'verification {s["verification_state"]} · availability {s["availability"]}', '',
        '| Model id | Provider | Type | Credential | Connection | Verification | Availability | Lifecycle | Price in force | Role / blocker |',
        '|---|---|---|---|---|---|---|---|---|---|',
    ]
    for r in m['models']:
        p = r['price_in_force'] or {}
        price = ' / '.join(x for x in (
            p.get('input_per_million') and f'in ${p["input_per_million"]}', p.get('output_per_million') and f'out ${p["output_per_million"]}',
            p.get('per_image') and f'${p["per_image"]}/image', p.get('per_video_second') and f'${p["per_video_second"]}/s video',
            p.get('per_audio_second') and f'${p["per_audio_second"]}/s audio', p.get('per_song') and f'${p["per_song"]}/song') if x) or 'no source-backed price'
        if r['price_changes_announced']:
            price += ' (change announced: ' + ', '.join(f'{c["effective_from"]}' for c in r['price_changes_announced']) + ')'
        life = r['deprecation_state'] + (f' → {r["replacement_model"]}' if r['replacement_model'] else '')
        role = r['current_operational_status'] + (f' — {r["blocker"]}' if r['blocker'] else '')
        lines.append(f'| `{r["provider_model_id"]}` | {r["provider_key"]} | {r["provider_type"]} | {r["credential_state"]} '
                     f'({r["credential_scope"]}) | {r["connection_state"]} | {r["verification_state"]} | {r["availability"]} | '
                     f'{life} | {price} | {role} |')
    lines += ['', '## Task classes (routing eligibility)', '', '| Task | Preferred floor | Mandatory floor | Independent of |',
              '|---|---|---|---|']
    for t in m['task_classes']:
        lines.append(f'| {t["task"]} | {t["preferred_floor"]} | {t["mandatory_floor"]} | {", ".join(t["independent_of"]) or "—"} |')
    lines += ['', '## Legacy / unwired routes', '']
    lines += [f'- `{x["route"]}` ({x["path"]}): {x["state"]} — {x["note"]}' for x in m['legacy_routes']]
    lines += ['', '## Capability gaps', '']
    lines += [f'- `{x["capability"]}`: {x["state"]} — {x["note"]}' for x in m['capability_gaps']]
    lines += ['', '## Evidence', '']
    seen = []
    for r in m['models']:
        for ev in r['evidence_reference']:
            if ev not in seen:
                seen.append(ev)
    lines += [f'- {x}' for x in seen]
    return '\n'.join(lines) + '\n'


def render(m: dict) -> tuple[str, str]:
    return json.dumps(m, indent=1, ensure_ascii=False, sort_keys=False) + '\n', markdown(m)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog='omni_prod.intelligence.matrix')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args(argv)
    m = build()
    problems = validate(m)
    js, md = render(m)
    if args.write:
        if problems:
            print('\n'.join(problems))
            return 1
        JSON_OUT.write_text(js, encoding='utf-8')
        MD_OUT.write_text(md, encoding='utf-8')
        print(json.dumps(m['summary']))
        return 0
    if args.check:
        stale = [p.name for p, want in ((JSON_OUT, js), (MD_OUT, md))
                 if not p.exists() or p.read_text(encoding='utf-8') != want]
        for p in problems + [f'{s} is stale: run python -m omni_prod.intelligence.matrix --write' for s in stale]:
            print(p)
        return 1 if problems or stale else 0
    print(js)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
