"""Golden build rehearsal: the real generation pipeline, without customer state.

Runs exactly the engine a live build uses (`investor_app._live_components()`:
the configured model routes, the remote sandbox, dependency gate, preview
readiness incl. a real start of the app, quality-as-repair) on one prompt, then
the same quality gate the release uses. Writes nothing to the database, opens
no project, reserves no credits; the model gateway's own external budget
(OMNI_EXTERNAL_BUDGET_USD) bounds spend. Prints a compact JSON report.

Golden E2E #1 (2026-10-08): every failure so far was found by the founder
pressing "build" and sending a screenshot. This lets the platform's own
pipeline be exercised and iterated on directly.

    python -m omni_prod.rehearsal "<prompt>"
"""
from __future__ import annotations

import json
import sys
import time


MAX_BRIEF_STEPS = 40


def approved_prompt(request: str, answers: dict) -> str:
    """The prompt a CUSTOMER's build gets: the request plus the approved brief block (discovery.requirements_text),
    built by the conversation's own functions. Calibration, 2026-11-17 (rehearsals 44025252867, 44025259144): a raw
    request has no brief, so a cafe's page was contracted as an app ("missing required behavior kinds: auth,
    data_create, role") and its phone number was called invented -- failures no customer's build has.
    `answers` are the customer's own answers to the questions that may never be defaulted ({question id: value});
    every other question is delegated, as "you decide" does. A question that must be answered and is not in
    `answers` raises: nothing is guessed."""
    from . import discovery as d
    brief = d.start(request)
    for _ in range(MAX_BRIEF_STEPS):                      # bounded: the catalogue is finite
        must = d.must_ask(brief)
        if must:
            q = must[0]
            if q.id not in answers:
                raise ValueError(f'the brief needs the customer\'s answer to {q.id!r} '
                                 f'(one of {[o.value for o in q.options]}); pass it in answers')
            brief = d.answer(brief, {q.id: answers[q.id]})
            continue
        if d.catalog_complete(brief):
            break
        _, group = d.next_group(brief)
        if not group:
            break
        brief = d.answer(brief, {q.id: d.DELEGATE for q in group})
    else:
        raise ValueError(f'the brief was not complete after {MAX_BRIEF_STEPS} steps')
    return (brief.prompt + '\n' + d.requirements_text(brief))[:12000]


def run(prompt: str) -> dict:
    from .investor_app import _live_components
    from .quality_gate import assess_repository
    from .worker_tasks import spend_snapshot
    started = time.monotonic()
    engine, gateway = _live_components()
    report: dict = {'prompt': prompt}
    # The content-document route, in the worker's order: right after the components, before any install that wraps
    # the architect (worker_tasks._run_live_build_job). The rehearsal has no account: OMNI_SITE_LIBRARY=on exercises it.
    # The worker fails a customer's build on any error here (an unknown OMNI_SITE_LIBRARY value, an empty account
    # list): the rehearsal stops the same way, before any spend -- it never builds and judges the legacy path while the
    # route was intended. install() changes nothing on the engine before everything that can raise is resolved.
    site_error = None
    try:
        from . import site_content
        report['site_route'] = site_content.install(engine, prompt=prompt, gateway=gateway, request=None).to_dict()
    except Exception as exc:
        site_error = f'{type(exc).__name__}: {exc}'[:1500]
        report.update(site_route_error=site_error[:300], outcome='exception', error=site_error)
    # Same requirements-aware acceptance scope a real build gets from its contract.
    try:
        from .product_architect import ProductArchitect
        from .worker_tasks import set_acceptance_scope
        set_acceptance_scope(engine, ProductArchitect().compile(prompt, project_id='rehearsal',
                                                                 contract_version=1).to_dict())
    except Exception as exc:
        report['acceptance_scope_error'] = f'{type(exc).__name__}: {exc}'[:300]
    # What the worker installs from the approved request alone, in the worker's order (worker_tasks.run_build).
    # Rehearsal 44043708644 (the butcher, 2026-11-17): the review was never given the request, so its fact canon was
    # empty and the customer's own opening hours were called "invented" -- a blocking finding and a paid repair round
    # that no customer's build has. A step that cannot be installed is in the report, never skipped in silence.
    try:
        from .page_locale import install as install_page_locale
        install_page_locale(engine, prompt)
        from .share_preview import install as install_share_preview
        install_share_preview(engine)
        from .product_review import install_review_request
        report['review_request_installed'] = install_review_request(engine, prompt)
        from .fact_canon import install_facts
        report['facts_carried'] = len(install_facts(engine, prompt))
        from .page_outline import install as install_page_outline
        report['outline_carried'] = len(install_page_outline(engine, prompt))
    except Exception as exc:
        report['request_installs_error'] = f'{type(exc).__name__}: {exc}'[:300]
    # The same skill gates a customer's build runs (gate.WORKER_GATES), each in its own mode. A calibrating gate warns:
    # its findings are in the report, which is how a gate is calibrated on real generated pages before it blocks.
    try:
        from .skill_units.gate import install_all
        install_all(engine)
        from .runtime_load import install as install_runtime_load
        install_runtime_load(engine)
        # A request for a game is also judged as a game (omni_prod/game_runtime). The game profile is NOT open to
        # customers; this is how the engine is proven able to build one before the profile is declared (a profile is
        # a promise the engine must keep, output_profile.check_truth).
        from .intake.families import classify_family
        report['family'] = classify_family(prompt)
        if report['family'] == 'game':
            from .game_runtime import install as install_game_runtime
            install_game_runtime(engine)
    except Exception as exc:
        report['skill_gates_error'] = f'{type(exc).__name__}: {exc}'[:300]
    # G-APPLE, last, right before the build: the design contract goes into the prompt, as in a customer's build.
    try:
        from .attempt_ledger import TaskTaggedGateway
        from .g_apple import install as install_apple_gate
        prompt = install_apple_gate(engine, prompt=prompt,
                                    gateway=TaskTaggedGateway(getattr(gateway, '_inner', gateway), 'review'))
    except Exception as exc:
        report['g_apple_error'] = f'{type(exc).__name__}: {exc}'[:300]
    try:
        if site_error is not None:          # the worker fails here too: no build, no spend
            raise RuntimeError(f'the content route could not be decided, so the build did not start: {site_error}')
        result = engine.build(prompt)
    except Exception as exc:
        report.update(outcome='exception', error=f'{type(exc).__name__}: {exc}'[:1500])
        result = None
    if result is not None:
        quality = assess_repository(spec=result.spec, repository=result.repository)
        report.update(
            outcome=result.status, repair_rounds=result.repair_rounds,
            stop_reason=getattr(result, 'stop_reason', None),
            acceptance=[f'{a.id}: {a.text}' for a in result.spec.acceptance],
            files=sorted(result.repository)[:40],
            manifest=result.repository.get('.omni/project.json', '')[:800],
            failures=[{'id': f.acceptance_id, 'message': f.message[:300], 'evidence': (f.evidence or '')[-900:]}
                      for f in result.report.failures][:6],
            quality={'score': quality.score, 'passed': quality.passed, 'blockers': list(quality.blockers)},
            trace=getattr(engine, 'trace', [])[:8],
            review=[{'round': r.get('round'), 'enforced': r.get('enforced'), 'reviewer': r.get('reviewer'),
                     'model': r.get('model'), 'blocking': r.get('blocking'),
                     'findings': [f"{f['severity']}/{f['source']} {f['skill']}: {f['problem'][:160]}" for f in r.get('findings', [])][:8]}
                    for r in getattr(getattr(engine, 'executor', None), 'reviews', [])][:4],
            browser_check=getattr(getattr(engine, 'executor', None), 'last_probe', None),
            behavior_acceptance=__import__('omni_prod.worker_tasks', fromlist=['x']).behavior_evidence(engine),
        )
    report['release_policy'] = release_policy(engine, gateway, result)
    from .skill_units.gate import report as skill_gate_report
    report['skill_gates'] = skill_gate_report(engine)
    from .g_apple import report as apple_gate_report
    report['g_apple'] = apple_gate_report(engine)
    from .runtime_load import report as runtime_load_report
    report['runtime_load'] = runtime_load_report(engine)
    from .game_runtime import report as game_runtime_report
    report['game_runtime'] = game_runtime_report(engine)
    from .site_content import report as site_route_report
    report['site_route'] = site_route_report(engine) or report.get('site_route')
    report['failure_taxonomy'] = getattr(engine, 'failure_taxonomy', [])
    report['first_pass'] = getattr(engine, 'first_pass', None)
    spent, calls = spend_snapshot(gateway)
    report.update(model_calls=calls, authorized_spend_usd=str(spent), seconds=round(time.monotonic() - started))
    report.update(cost_projection(gateway))
    return report


def release_policy(engine, gateway, result) -> dict:
    """The worker's release policy on the rehearsal's build: the decision a customer's build gets after its checks.

    Production 2026-11-17, bld_a875456f: every build failed `release_policy_failed` for half a day (a chain walk that
    could not reach three stages) while five rehearsals of the same code reported "ready" -- the rehearsal stopped
    at the engine's result and never asked the policy. It asks now, with the worker's own function, and a build the
    policy blocks is not a ready rehearsal.
    Not the customer's path, said here: the request's rights are not assessed in a rehearsal (no account, no
    markets), so `rights_clear` is reported NOT_ASSESSED and never counted as the reason for a block."""
    if result is None:
        return {'decision': 'NOT_RUN', 'reason': 'the build raised before it had a result'}
    from types import SimpleNamespace
    from .quality_gate import assess_repository
    from .security_testing import hostile_repository_scan
    from .worker_tasks import release_quality_report
    quality = assess_repository(spec=result.spec, repository=result.repository)
    qr = release_quality_report('rehearsal', engine, gateway, result, quality,
                                hostile_repository_scan(result.repository), SimpleNamespace(publish_allowed=True))
    if qr is None:
        return {'decision': 'UNAVAILABLE', 'reason': 'the quality report could not be generated'}
    blocking = [f'{c.stage}/{c.check}: {c.status}' + (f' ({c.detail})' if c.detail else '') for c in qr.blocking]
    return {'decision': qr.decision, 'blocking': blocking, 'not_run': qr.not_run, 'rights_clear': 'NOT_ASSESSED'}


def cost_projection(gateway) -> dict:
    """Measured tokens of this build and what the same tokens cost on every
    catalog model (list price; a different model would write a different
    number of tokens, so this is a price comparison, not a prediction)."""
    from decimal import Decimal
    tin = tout = 0
    by_model: dict[str, list[int]] = {}
    for rec in getattr(getattr(gateway, 'recorder', None), 'records', []) or []:
        i, o = getattr(rec, 'input_tokens', None), getattr(rec, 'output_tokens', None)
        if i is None or o is None:
            continue
        tin, tout = tin + i, tout + o
        agg = by_model.setdefault(rec.model or '?', [0, 0, 0])
        agg[0] += i; agg[1] += o; agg[2] += 1
    prices = {}
    for m in getattr(gateway, 'ranked', ()):
        opt = m.option
        prices[m.endpoint.name] = str(((Decimal(tin) * opt.input_per_million + Decimal(tout) * opt.output_per_million)
                                       / Decimal(1_000_000)).quantize(Decimal('0.0001')))
    return {'tokens': {'input': tin, 'output': tout, 'by_model': by_model}, 'same_tokens_cost_usd': prices}


def annotations(report: dict) -> list[str]:
    """GitHub notice lines (at most 10 per step are kept by GitHub)."""
    def note(title, body):
        body = str(body)[:3400].replace('%', '%25').replace('\r', '').replace('\n', '%0A')
        return f'::notice title={title}::{body}'
    q = report.get('quality') or {}
    lines = [note('outcome', f"{report.get('outcome')} rounds={report.get('repair_rounds')} stop={report.get('stop_reason')} "
                             f"quality={q.get('score')}/{'pass' if q.get('passed') else 'fail'} {q.get('blockers') or ''} "
                             f"calls={report.get('model_calls')} spend={report.get('authorized_spend_usd')} "
                             f"seconds={report.get('seconds')} {report.get('error', '')}"),
             note('acceptance', '\n'.join(report.get('acceptance') or [])),
             note('files', ', '.join(report.get('files') or []) + '\n' + (report.get('manifest') or ''))]
    lines.append(note('taxonomy', f"first_pass={report.get('first_pass')} failures="
                                  + json.dumps(report.get('failure_taxonomy') or [], ensure_ascii=False)))
    policy = report.get('release_policy') or {}
    lines.append(note('release policy', json.dumps(
        {k: policy.get(k) for k in ('decision', 'reason', 'blocking', 'rights_clear')}, ensure_ascii=False)
        + '\nnot run: ' + json.dumps([f"{n['stage']}/{n['check']}" for n in policy.get('not_run') or []])))
    if report.get('site_route_error'):
        lines.append('::error title=site route::the route could not be decided, so a customer\'s build would fail the '
                     'same way; the rehearsal did not build: ' + str(report['site_route_error']).replace('\n', ' '))
    if policy.get('decision') not in (None, 'READY', 'NOT_RUN'):
        lines.append('::error title=release policy::a customer\'s build would FAIL: '
                     + '; '.join(policy.get('blocking') or [str(policy.get('reason'))]).replace('\n', ' ')[:1500])
    if report.get('skill_gates') or report.get('skill_gates_error'):
        lines.append(note('skill gates', report.get('skill_gates_error') or '\n'.join(
            f"{g} mode={r.get('mode')} status={r.get('status', 'NOT_RUN')} "
            + json.dumps(r.get('failures') or [], ensure_ascii=False)[:600]
            for g, r in report['skill_gates'].items())))
    if report.get('g_apple') or report.get('g_apple_error'):
        apple = report.get('g_apple') or {}
        last = apple.get('last') or {}
        lines.append(note('g-apple', report.get('g_apple_error') or json.dumps({
            'mode': apple.get('mode'), 'contract': (apple.get('contract') or {}).get('fingerprint'),
            'status': last.get('status'), 'reason': last.get('reason'), 'not_run': last.get('not_run'),
            # calibration reads WHAT was measured, not only where (two builds said MEASURE with no number to read)
            'static': [(f['code'], f['where'], f.get('why', '')) for f in last.get('static') or []][:25],
            'render': [(f['code'], f['width'], f['selector'], f.get('why', '')) for f in last.get('render') or []][:25],
            'reviewers': [{k: r.get(k) for k in ('reviewer', 'status', 'p0', 'reason', 'category_marks', 'findings')}
                          for r in last.get('reviewers') or []]}, ensure_ascii=False)))
    if (report.get('runtime_load') or {}).get('last') or (report.get('game_runtime') or {}).get('last'):
        lines.append(note('runtime', json.dumps({'family': report.get('family'), 'load': report['runtime_load'].get('last'),
                                                 'game': report['game_runtime'].get('last')}, ensure_ascii=False)))
    if report.get('tokens'):
        lines.append(note('cost', f"tokens {json.dumps(report['tokens'])}\nsame tokens on each model (USD): "
                                  f"{json.dumps(report.get('same_tokens_cost_usd'))}"))
    if report.get('review'):
        lines.append(note('qa review', '\n'.join(
            f"round {r['round']} enforced={r['enforced']} reviewer={r['reviewer']} model={r['model']} blocking={r['blocking']}\n  "
            + '\n  '.join(r['findings']) for r in report['review'])))
    if report.get('behavior_acceptance') is not None:
        ba = report['behavior_acceptance']
        last = (ba or {}).get('last') or {}
        lines.append(note('behavior acceptance', json.dumps({'rounds': ba.get('rounds'), 'last': {
            'status': last.get('status'), 'summary': last.get('summary'),
            'failed': [c for c in (last.get('checks') or []) if not c.get('passed')][:4]}}, ensure_ascii=False)))
    if report.get('browser_check') is not None:
        lines.append(note('browser check', json.dumps(report['browser_check'], ensure_ascii=False)))
    if report.get('trace'):
        lines.append(note('repair rounds', '\n'.join(
            f"round {t['round']}: failing {t['failing']} changed {t['changed']} :: {t['first_failure'][-500:]}"
            for t in report['trace'])))
    for i, f in enumerate((report.get('failures') or [])[:5]):
        lines.append(note(f"failure {i + 1} {f['id']}", f['message'] + '\n' + f['evidence']))
    return lines


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or not argv[0].strip():
        print('usage: python -m omni_prod.rehearsal "<prompt>" [\'{"content_only": "yes", ...}\']', file=sys.stderr)
        return 2
    prompt, brief_mode = argv[0], len(argv) > 1 and bool(argv[1].strip())
    if brief_mode:                                        # the customer's path: an approved brief, not a raw request
        answers = json.loads(argv[1])
        if not isinstance(answers, dict):
            raise ValueError('answers must be a JSON object of question id -> value')
        prompt = approved_prompt(argv[0], answers)
    report = run(prompt)
    report['brief_mode'] = brief_mode
    print('REHEARSAL ' + json.dumps(report, ensure_ascii=False))
    for line in annotations(report):
        print(line)
    return 0 if ready(report) else 1


def ready(report: dict) -> bool:
    """A rehearsal is ready when a customer's build would be: the engine said ready, the quality gate passed AND the
    release policy decided READY."""
    return (report.get('outcome') == 'ready' and bool(report.get('quality', {}).get('passed'))
            and (report.get('release_policy') or {}).get('decision') == 'READY')


if __name__ == '__main__':
    raise SystemExit(main())
