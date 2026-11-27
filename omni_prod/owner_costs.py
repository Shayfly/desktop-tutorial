"""What builds cost US -- the owner's cost report (the owner, 2026-11-26 10:13 and 10:20 UTC).

"אני רוצה לראות תוצאות של בניה ולדעת כמה שיותר נתונים על עלויות מבחינתנו ולא מהצד של הלקוח" and "לא מחייב אם אין לנו את
כל הנתונים ... אבל לעדכן לדוגמא אין לי את הנתונים של העלות בגימיני".

Every number is READ from a table that already records it; nothing is estimated here:
  task_attempts          every model call: task (stage), model, tokens, metered cost (tokens x the source-backed price)
  provider_usage_events  every image (capability) call: actual, else computed/estimate; 'unpriced:' = no price
  build_jobs             status, error code, times, repair rounds, evidence (settlement, cost_record, cost_data_missing)
  credit_reservations    credits reserved and how they ended (SETTLED = charged, RELEASED = given back)
  credit_ledger          the refund rows of failed builds
  company_loss_events    the provider cost of failed builds that the company bore
  intake_reservations    the conversation before a build (per project, between the previous build and this one)
A cost that is not recorded is UNKNOWN and named in `missing_cost_data`, never 0.

Tenant safety: the route that serves this is the founder account's only (403 for every other account). The report
carries no account id, e-mail, prompt or project id: a build is its id, whether it is the owner's, and its numbers.
"""
from __future__ import annotations

import html
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal

MAX_DAYS = 90
STAGES = ('intake_conversation', 'direction_sketch', 'architecture', 'codegen', 'repair', 'review', 'vision_checks', 'images',
          'translations_and_general', 'classification', 'modification', 'other')
_TASK_STAGE = {'architecture': 'architecture', 'codegen': 'codegen', 'repair': 'repair', 'review': 'review',
               'general': 'translations_and_general', 'classification': 'classification',
               'modification': 'modification'}
VISION_MARK = 'vision call'          # routed_gateway writes it into selection_reason of a call with images
UNPRICED_PREFIX = 'unpriced:'
from .attempt_ledger import price_unknown   # the one mark the gateway writes (money review B1)


def _d(v) -> Decimal:
    return Decimal(str(v)) if v is not None else Decimal('0')


def _s(v) -> str | None:
    if v is None:
        return None
    return format(Decimal(str(v)).quantize(Decimal('0.000001')), 'f')


def _json(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except ValueError:
            return {}
    return v or {}


def stage_of(task_type: str | None, selection_reason: str | None) -> str:
    if task_type == 'review' and VISION_MARK in str(selection_reason or ''):
        return 'vision_checks'
    return _TASK_STAGE.get(str(task_type or ''), 'other')


def cost_report(pool, *, days: int = 14, scope: str = 'all', founder_ids: set[str] | frozenset = frozenset(),
                now: datetime | None = None) -> dict:
    """The report for the last `days` days (by build creation time). scope 'all': every build (the company's cost);
    'owner': the founder account's builds only. Raises ValueError on an unknown scope or a day count out of 1..90."""
    if scope not in ('all', 'owner'):
        raise ValueError(f"scope must be 'all' or 'owner', not {scope!r}")
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= MAX_DAYS:
        raise ValueError(f'days must be an integer 1..{MAX_DAYS}')
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    founders = sorted(str(x) for x in founder_ids)
    with pool.connection() as conn:
        builds = conn.execute(
            "SELECT bj.id, bj.status, bj.error_code, bj.created_at, bj.started_at, bj.finished_at, bj.repair_rounds, "
            "       bj.ai_cost, bj.actual_provider_cost_usd, bj.evidence_json, br.user_id = ANY(%s), "
            "       br.public_project_id, cr.credits_reserved, cr.status, cr.settled_provider_cost_usd, "
            "       cr.funding_source "
            "FROM build_jobs bj LEFT JOIN build_requests br ON br.build_id = bj.id "
            "LEFT JOIN credit_reservations cr ON cr.build_id = bj.id "
            "WHERE bj.created_at >= %s AND bj.created_at < %s ORDER BY bj.created_at",
            (founders, since, now)).fetchall()
        if scope == 'owner':
            builds = [b for b in builds if b[10]]
        ids = [b[0] for b in builds]
        attempts = conn.execute(
            "SELECT build_id, attempt_seq, kind, task_type, COALESCE(model, provider), selection_reason, input_tokens, "
            "       output_tokens, metered_cost_usd, provider_reported_cost_usd, authorized_cost_usd, outcome, created_at "
            "FROM task_attempts WHERE build_id = ANY(%s) ORDER BY build_id, attempt_seq", (ids,)).fetchall()
        usage = conn.execute(
            "SELECT build_id, requirement_id, provider, pricing_version, estimated_cost_usd, maximum_cost_usd, "
            "       actual_cost_usd, usage_json, created_at FROM provider_usage_events WHERE build_id = ANY(%s) "
            "ORDER BY id", (ids,)).fetchall()
        losses = conn.execute(
            "SELECT build_id, COALESCE(sum(actual_usd), 0), COALESCE(sum(overrun_usd), 0), count(*) "
            "FROM company_loss_events WHERE build_id = ANY(%s) GROUP BY build_id", (ids,)).fetchall()
        refunds = conn.execute(
            "SELECT substring(idempotency_key from 'failed-build-release:(.*)'), COALESCE(sum(delta), 0) "
            "FROM credit_ledger WHERE idempotency_key = ANY(%s) GROUP BY 1",
            ([f'failed-build-release:{i}' for i in ids],)).fetchall()
        projects = sorted({b[11] for b in builds if b[11]})
        intake = conn.execute(
            "SELECT project_id, reserved_at, COALESCE(model, provider), state, cost_state, actual_usd, "
            "COALESCE(quote->>'task', '') FROM intake_reservations WHERE project_id = ANY(%s) AND reserved_at < %s ORDER BY reserved_at",
            (projects, now)).fetchall()
        project_builds = conn.execute(
            "SELECT br.public_project_id, bj.created_at FROM build_jobs bj JOIN build_requests br ON br.build_id = bj.id "
            "WHERE br.public_project_id = ANY(%s) ORDER BY bj.created_at", (projects,)).fetchall()
    return _assemble(builds, attempts, usage, losses, refunds, intake, project_builds, days=days, scope=scope,
                     since=since, now=now)


def _assemble(builds, attempts, usage, losses, refunds, intake, project_builds, *, days, scope, since, now) -> dict:
    by_build_attempts = defaultdict(list)
    for a in attempts:
        by_build_attempts[a[0]].append(a)
    by_build_usage = defaultdict(list)
    for u in usage:
        by_build_usage[u[0]].append(u)
    loss = {r[0]: r for r in losses}
    refund = {r[0]: int(r[1]) for r in refunds}
    earlier = defaultdict(list)
    for project, created in project_builds:
        earlier[project].append(created)

    per_build, missing = [], {}
    agg_day = defaultdict(lambda: {'builds': 0, 'ready': 0, 'failed': 0, 'cancelled': 0, 'known_cost_usd': Decimal('0'),
                                   'loss_usd': Decimal('0'), 'unknown_items': 0})
    agg_model = defaultdict(lambda: {'calls': 0, 'input_tokens': 0, 'output_tokens': 0, 'known_cost_usd': Decimal('0'),
                                     'calls_without_cost': 0, 'builds': set()})
    agg_stage = defaultdict(lambda: {'calls': 0, 'known_cost_usd': Decimal('0'), 'calls_without_cost': 0,
                                     'builds': set()})
    agg_outcome = defaultdict(lambda: {'builds': 0, 'known_cost_usd': Decimal('0'), 'loss_usd': Decimal('0')})

    def gap(kind, name, why, build_id, when, calls=0, tokens=0):
        key = (kind, name, why)
        row = missing.setdefault(key, {'kind': kind, 'name': name, 'why': why, 'builds': set(), 'calls': 0,
                                       'tokens': 0, 'first_seen': None, 'last_seen': None})
        if build_id:
            row['builds'].add(build_id)
        row['calls'] += calls
        row['tokens'] += tokens
        stamp = when.isoformat() if hasattr(when, 'isoformat') else (str(when) if when else None)
        if stamp:
            row['first_seen'] = min(filter(None, [row['first_seen'], stamp]))
            row['last_seen'] = max(filter(None, [row['last_seen'], stamp]))

    for b in builds:
        (bid, status, error_code, created, started, finished, repair_rounds, ai_cost, actual, evidence, owner,
         project, credits, res_status, settled, funding) = b
        evidence = _json(evidence)
        stages = defaultdict(lambda: {'calls': 0, 'input_tokens': 0, 'output_tokens': 0, 'known_cost_usd': Decimal('0'),
                                      'calls_without_cost': 0})
        models = defaultdict(lambda: {'calls': 0, 'input_tokens': 0, 'output_tokens': 0, 'known_cost_usd': Decimal('0'),
                                      'calls_without_cost': 0})
        rounds = defaultdict(lambda: {'calls': 0, 'known_cost_usd': Decimal('0'), 'calls_without_cost': 0})
        verifications = 0
        known = Decimal('0')
        stand_in = Decimal('0')
        unknown_items = 0
        for a in by_build_attempts.get(bid, ()):
            _, seq, kind, task, model, reason, tin, tout, metered, reported, authorized, outcome, when = a
            if kind == 'verification':
                verifications += 1
                continue
            stage = stage_of(task, reason)
            cost = reported if reported is not None else metered
            for bucket in (stages[stage], models[model or '?']):
                bucket['calls'] += 1
                bucket['input_tokens'] += int(tin or 0)
                bucket['output_tokens'] += int(tout or 0)
            m = agg_model[model or '?']
            m['calls'] += 1
            m['input_tokens'] += int(tin or 0)
            m['output_tokens'] += int(tout or 0)
            m['builds'].add(bid)
            st = agg_stage[stage]
            st['calls'] += 1
            st['builds'].add(bid)
            if stage == 'repair':     # repair round = the verification runs before it (attempt_seq order)
                rounds[max(1, verifications)]['calls'] += 1
            if cost is None:
                if not (authorized or 0) > 0 and outcome == 'error':
                    continue          # refused before any service: nothing to price
                unknown_items += 1
                for bucket in (stages[stage], models[model or '?'], m, st):
                    bucket['calls_without_cost'] += 1
                if stage == 'repair':
                    rounds[max(1, verifications)]['calls_without_cost'] += 1
                if price_unknown(reason):     # money review B1: UNKNOWN; the plan was charged the stand-in
                    stand_in += _d(authorized)
                    why = 'price_missing: tokens recorded, no price (the plan is charged the stand-in worst case)'
                elif tin is not None or tout is not None:
                    why = 'flat_authorization: a configured route without a catalog price'
                else:
                    why = 'usage_not_reported: the provider answered nothing measurable (timeout)'
                gap('model', model or '?', why, bid, when, calls=1, tokens=int(tin or 0) + int(tout or 0))
                continue
            c = _d(cost)
            known += c
            for bucket in (stages[stage], models[model or '?'], m, st):
                bucket['known_cost_usd'] += c
            if stage == 'repair':
                rounds[max(1, verifications)]['known_cost_usd'] += c
        images = {'calls': 0, 'known_cost_usd': Decimal('0'), 'calls_without_cost': 0, 'basis': []}
        for u in by_build_usage.get(bid, ()):
            _, rid, provider, pv, est, mx, act, uj, when = u
            uj = _json(uj)
            images['calls'] += 1
            agg_stage['images']['calls'] += 1
            agg_stage['images']['builds'].add(bid)
            if str(pv or '').startswith(UNPRICED_PREFIX) and act is None:
                images['calls_without_cost'] += 1
                agg_stage['images']['calls_without_cost'] += 1
                unknown_items += 1
                gap('capability', f'{provider}:{rid}', 'price_missing: the provider has no price configured', bid, when,
                    calls=1)
                continue
            value = act if act is not None else (uj.get('computed_cost_usd') if uj.get('computed_cost_usd') is not None
                                                 else est)
            if value is None:        # migration 048: a NULL estimate is unknown, never added as 0
                images['calls_without_cost'] += 1
                agg_stage['images']['calls_without_cost'] += 1
                unknown_items += 1
                gap('capability', f'{provider}:{rid}', 'price_missing: no estimate recorded (NULL)', bid, when, calls=1)
                continue
            images['basis'].append('actual' if act is not None else
                                   ('computed_from_usage' if uj.get('computed_cost_usd') is not None else 'estimate'))
            images['known_cost_usd'] += _d(value)
            agg_stage['images']['known_cost_usd'] += _d(value)
            known += _d(value)
        # the conversation that led to this build: its project's intake calls since the project's previous build
        prior = [t for t in earlier.get(project, []) if t < created]
        start = max(prior) if prior else None
        conv = {'calls': 0, 'known_cost_usd': Decimal('0'), 'calls_without_cost': 0}
        sketch = {'calls': 0, 'known_cost_usd': Decimal('0'), 'calls_without_cost': 0}     # S6.3: a part of `conv`
        for row in intake:
            p, when, model, state, cost_state, act = row[:6]
            task = row[6] if len(row) > 6 else ''
            if p != project or when >= created or (start is not None and when < start) or state == 'RELEASED':
                continue
            parts = (conv, sketch) if task == 'direction_sketch' else (conv,)
            for part in parts:
                part['calls'] += 1
            if act is None or state == 'UNKNOWN':
                for part in parts:
                    part['calls_without_cost'] += 1
                gap('intake_model', model or '?', 'intake call with unknown cost (UNKNOWN reservation)', bid, when, 1)
                continue
            for part in parts:
                part['known_cost_usd'] += _d(act)
        # the conversation's own calls and the direction sketches' words are two stages; `conv` stays the total of both
        talk = {k: conv[k] - sketch[k] for k in conv}
        for stage_key, part in (('intake_conversation', talk), ('direction_sketch', sketch)):
            agg_stage[stage_key]['calls'] += part['calls']
            agg_stage[stage_key]['known_cost_usd'] += part['known_cost_usd']
            agg_stage[stage_key]['calls_without_cost'] += part['calls_without_cost']
            if part['calls']:
                agg_stage[stage_key]['builds'].add(bid)
        for item in evidence.get('cost_data_missing') or []:
            gap(str(item.get('kind')), str(item.get('name')), f"{item.get('gap')}: {item.get('why')}", bid, created)
        lrow = loss.get(bid)
        loss_usd = _d(lrow[1]) if lrow else Decimal('0')
        settlement = evidence.get('economics_settlement') or {}
        record = settlement.get('cost_record') or {}
        day = created.date().isoformat() if hasattr(created, 'date') else str(created)[:10]
        build_cost = known + conv['known_cost_usd']
        ad = agg_day[day]
        ad['builds'] += 1
        ad[{'ready': 'ready', 'failed': 'failed', 'cancelled': 'cancelled'}.get(status, 'failed')] += 1 \
            if status in ('ready', 'failed', 'cancelled') else 0
        ad['known_cost_usd'] += build_cost
        ad['loss_usd'] += loss_usd
        ad['unknown_items'] += unknown_items + conv['calls_without_cost']
        outcome_key = status if status == 'ready' else f'{status}:{error_code or "-"}'
        ao = agg_outcome[outcome_key]
        ao['builds'] += 1
        ao['known_cost_usd'] += build_cost
        ao['loss_usd'] += loss_usd
        stage_rows = {k: {**v, 'known_cost_usd': _s(v['known_cost_usd'])} for k, v in stages.items()}
        stage_rows['images'] = {k: (_s(v) if k == 'known_cost_usd' else v) for k, v in images.items()}
        stage_rows['intake_conversation'] = {k: (_s(v) if k == 'known_cost_usd' else v) for k, v in talk.items()}
        stage_rows['direction_sketch'] = {k: (_s(v) if k == 'known_cost_usd' else v) for k, v in sketch.items()}
        per_build.append({
            'build_id': bid, 'owner_build': bool(owner), 'status': status, 'error_code': error_code,
            'created_at': created.isoformat() if hasattr(created, 'isoformat') else str(created),
            'duration_seconds': int((finished - started).total_seconds()) if finished and started else None,
            'repair_rounds': repair_rounds,
            'provider_cost_known_usd': _s(build_cost),
            'stand_in_charged_usd': _s(stand_in),      # NOT a cost: the authorized worst case of price-unknown calls
            'cost_complete': unknown_items + conv['calls_without_cost'] == 0,
            'unknown_cost_items': unknown_items + conv['calls_without_cost'],
            'stages': stage_rows,
            'repair_rounds_cost': {str(k): {**v, 'known_cost_usd': _s(v['known_cost_usd'])}
                                   for k, v in sorted(rounds.items())},
            'models': {k: {**v, 'known_cost_usd': _s(v['known_cost_usd'])} for k, v in sorted(models.items())},
            'recorded': {'ai_cost': None if Decimal(str(record.get('stand_in_usd') or 0)) > 0 else _s(ai_cost),
                         'llm_known_usd': record.get('llm_known_usd'), 'stand_in_usd': record.get('stand_in_usd'),
                         'actual_provider_cost_usd': _s(actual),
                         'settled_provider_cost_usd': _s(settled), 'cost_record_basis': record.get('basis'),
                         'cost_record_total_usd': record.get('total_usd'),
                         'provider_cost_truth': settlement.get('provider_cost_truth'),
                         'founder_no_build_limit': bool(((evidence.get('economics_quote') or {}).get('components')
                                                        or {}).get('founder_no_build_limit'))},
            'credits': {'reserved': credits, 'reservation_status': res_status, 'funding_source': funding,
                        'charged': credits if res_status == 'SETTLED' else 0,
                        'released': refund.get(bid, credits if res_status == 'RELEASED' else 0)},
            'loss_usd': _s(loss_usd),
            'cost_data_missing': evidence.get('cost_data_missing') or [],
            'bounds_near': record.get('bounds_near') or [],
        })

    def fin(d: dict) -> dict:
        return {k: (_s(v) if isinstance(v, Decimal) else (len(v) if isinstance(v, set) else v)) for k, v in d.items()}

    total_known = sum((_d(b['provider_cost_known_usd']) for b in per_build), Decimal('0'))
    total_loss = sum((_d(b['loss_usd']) for b in per_build), Decimal('0'))
    gaps = [{**{k: v for k, v in g.items() if k != 'builds'}, 'builds': len(g['builds'])}
            for g in sorted(missing.values(), key=lambda g: (g['kind'], g['name'], g['why']))]
    return {
        'schema': 'owner-costs/1', 'scope': scope, 'days': days,
        'from': since.isoformat(), 'to': now.isoformat(),
        'totals': {'builds': len(per_build), 'owner_builds': sum(1 for b in per_build if b['owner_build']),
                   'ready': sum(1 for b in per_build if b['status'] == 'ready'),
                   'failed': sum(1 for b in per_build if b['status'] == 'failed'),
                   'provider_cost_known_usd': _s(total_known), 'failed_builds_loss_usd': _s(total_loss),
                   'builds_with_unknown_cost': sum(1 for b in per_build if not b['cost_complete'])},
        'missing_cost_data': gaps,
        'per_day': {k: fin(v) for k, v in sorted(agg_day.items())},
        'per_model': {k: fin(v) for k, v in sorted(agg_model.items())},
        'per_stage': {k: fin(agg_stage[k]) for k in STAGES if k in agg_stage},
        'per_outcome': {k: fin(v) for k, v in sorted(agg_outcome.items())},
        'builds': per_build,
        'basis': ('model calls: provider-reported cost, else tokens x the source-backed price schedule '
                  '(task_attempts.metered_cost_usd); images: actual, else computed_from_usage, else the quoted estimate; '
                  'conversation: intake_reservations.actual_usd. Unknown is never 0: see missing_cost_data.'),
    }


def _money(v) -> str:
    return '—' if v is None else f'${Decimal(str(v)).quantize(Decimal("0.0001"))}'


def render_html(report: dict) -> str:
    """A small self-contained page (Hebrew, right to left, readable on a phone). No script, no external file."""
    e = html.escape
    t = report['totals']
    rows = lambda items, cols: ''.join('<tr>' + ''.join(f'<td>{e(str(c))}</td>' for c in cols(k, v)) + '</tr>'
                                       for k, v in items)
    gaps = ''.join(f"<li><b>{e(g['name'])}</b> ({e(g['kind'])}) — {e(g['why'])}: {g['builds']} בניות, {g['calls']} "
                   f"קריאות, מאז {e(str(g['first_seen'] or '—'))[:10]}</li>" for g in report['missing_cost_data'])
    builds = ''.join(
        f"<details><summary>{e(b['build_id'][:12])} · {e(b['status'])}{' · ' + e(b['error_code']) if b['error_code'] else ''}"
        f" · {_money(b['provider_cost_known_usd'])}{'' if b['cost_complete'] else ' + לא ידוע'}"
        f"{' · שלך' if b['owner_build'] else ''}</summary><table><tr><th>שלב</th><th>קריאות</th><th>עלות ידועה</th>"
        f"<th>בלי עלות</th></tr>"
        + rows(b['stages'].items(), lambda k, v: (k, v['calls'], _money(v['known_cost_usd']), v['calls_without_cost']))
        + f"</table><p>משך: {b['duration_seconds'] if b['duration_seconds'] is not None else '—'} שניות · סבבי תיקון: "
          f"{b['repair_rounds']} · קרדיטים נגבו {b['credits']['charged']}, הוחזרו {b['credits']['released']} · הפסד: "
          f"{_money(b['loss_usd'])}</p></details>" for b in report['builds'])
    css = ('body{font-family:system-ui,sans-serif;margin:0;padding:16px;background:#fff;color:#151410;font-size:16px}'
           'table{border-collapse:collapse;width:100%;margin:8px 0}td,th{border-bottom:1px solid #ddd;padding:6px;'
           'text-align:right}.wrap{overflow-x:auto}.cards{display:flex;flex-wrap:wrap;gap:8px}.card{border:1px solid '
           '#ddd;border-radius:8px;padding:8px 12px;min-width:140px}details{margin:6px 0}summary{cursor:pointer;'
           'min-height:44px;line-height:44px}@media (prefers-color-scheme:dark){body{background:#151410;color:#f4f1e8}}')
    return (
        '<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1"><title>עלויות הבנייה</title>'
        f'<style>{css}</style></head><body>'
        f"<h1>כמה עולות לנו הבניות</h1><p>{report['days']} ימים אחרונים · {'כל הבניות' if report['scope'] == 'all' else 'הבניות שלך'}</p>"
        f"<div class='cards'><div class='card'>בניות: {t['builds']} (שלך {t['owner_builds']})</div>"
        f"<div class='card'>הצליחו {t['ready']} · נכשלו {t['failed']}</div>"
        f"<div class='card'>עלות ידועה: {_money(t['provider_cost_known_usd'])}</div>"
        f"<div class='card'>הפסד מבניות שנכשלו: {_money(t['failed_builds_loss_usd'])}</div>"
        f"<div class='card'>בניות עם עלות לא ידועה: {t['builds_with_unknown_cost']}</div></div>"
        f"<h2>נתוני עלות חסרים</h2><ul>{gaps or '<li>אין</li>'}</ul>"
        "<h2>לפי יום</h2><div class='wrap'><table><tr><th>יום</th><th>בניות</th><th>הצליחו</th><th>נכשלו</th>"
        "<th>עלות ידועה</th><th>הפסד</th></tr>"
        + rows(report['per_day'].items(), lambda k, v: (k, v['builds'], v['ready'], v['failed'],
                                                         _money(v['known_cost_usd']), _money(v['loss_usd'])))
        + "</table></div><h2>לפי מודל</h2><div class='wrap'><table><tr><th>מודל</th><th>קריאות</th><th>טוקנים נכנסים</th>"
          "<th>טוקנים יוצאים</th><th>עלות ידועה</th><th>בלי עלות</th></tr>"
        + rows(report['per_model'].items(), lambda k, v: (k, v['calls'], v['input_tokens'], v['output_tokens'],
                                                           _money(v['known_cost_usd']), v['calls_without_cost']))
        + "</table></div><h2>לפי שלב</h2><div class='wrap'><table><tr><th>שלב</th><th>קריאות</th><th>עלות ידועה</th>"
          "<th>בלי עלות</th></tr>"
        + rows(report['per_stage'].items(), lambda k, v: (k, v['calls'], _money(v['known_cost_usd']),
                                                           v['calls_without_cost']))
        + "</table></div><h2>לפי תוצאה</h2><div class='wrap'><table><tr><th>תוצאה</th><th>בניות</th><th>עלות ידועה</th>"
          "<th>הפסד</th></tr>"
        + rows(report['per_outcome'].items(), lambda k, v: (k, v['builds'], _money(v['known_cost_usd']),
                                                             _money(v['loss_usd'])))
        + f"</table></div><h2>כל בנייה</h2>{builds}<p><small>{e(report['basis'])}</small></p></body></html>")
