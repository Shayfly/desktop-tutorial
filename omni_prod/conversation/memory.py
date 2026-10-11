"""Structured project memory (Unified Conversation OS §3).

A read model over the durable tables -- nothing here is a second copy of the
truth, and chat history is only one of ten separate sections:

  1 conversation          intake_messages
  2 approved requirements brief fields the customer stated/answered (project_briefs)
  3 assumptions           brief fields chosen by 148AI (delegated/default), unapproved until the brief is approved
  4 architecture          execution_plans (latest plan for the latest brief)
  5 execution plan + deps execution_plans.plan.execution_graph
  6 agent/skill execution agent_runs + agent_tasks of the latest build
  7 builds + versions     build_jobs, project_versions
  8 verification          build_stage_results of the latest build
  9 cost                  credit_reservations of the project's builds
 10 open items            pending questions, contradictions, feasibility blockers

Every section is scoped to one project the caller is authorized for (the API
resolves the project key first). Brief revisions are immutable, so an earlier
approved decision is never erased by a later change: `history` lists them.
"""
from __future__ import annotations

from .. import discovery as d

SCHEMA = 'project-memory/1'


def _q(pool, sql, args):
    try:
        with pool.connection() as conn:
            return conn.execute(sql, args).fetchall()
    except Exception as exc:  # a missing table on an older database: say so, never fail the page
        return exc


def snapshot(pool, *, project_id: str, internal_key: str, store, briefs) -> dict:
    out: dict = {'schema': SCHEMA, 'project_id': project_id}
    msgs = store.messages_for(project_id, limit=50)
    out['conversation'] = [{'role': m['role'], 'content': m['content'], 'brief_revision': m['brief_revision'],
                            'intent': (m.get('interpretation') or {}).get('intent')} for m in msgs]
    row = briefs.latest(project_id)
    if row is not None:
        f = row.brief.fields
        out['approved_requirements'] = {k: v['value'] for k, v in f.items() if v.get('source') in ('message', 'answer')}
        out['assumptions'] = {k: v['value'] for k, v in f.items() if v.get('source') in ('delegated', 'default')}
        out['brief'] = {'revision': row.revision, 'fingerprint': row.fingerprint, 'complete': row.complete}
        out['open_items'] = {'questions': [q.id for q in d.pending(row.brief)], 'contradictions': d.contradictions(row.brief)}
        plan = store.plan_for(project_id, row.fingerprint)
        if plan:
            p = plan['plan']
            out['architecture'] = {'plan_id': plan['id'], 'status': p.get('status'), 'architecture': p.get('architecture'),
                                   'feasibility': p.get('feasibility'), 'capability_gaps': p.get('capability_gaps')}
            out['execution_plan'] = {'tasks': [{'id': t['task_id'], 'department': t['department'], 'agent': t['responsible_agent'],
                                                'depends_on': t['dependencies']} for t in p['execution_graph']['tasks']],
                                     'layers': p.get('layers')}
            out['open_items']['blockers'] = [g['item'] for g in p.get('capability_gaps') or []]
    hist = _q(pool, 'SELECT revision, complete, fingerprint, created_at FROM project_briefs WHERE project_id = %s ORDER BY revision',
              (project_id,))
    out['history'] = [{'revision': r[0], 'complete': r[1], 'fingerprint': r[2][:16], 'at': r[3].isoformat()}
                      for r in hist] if isinstance(hist, list) else 'unavailable'
    builds = _q(pool, 'SELECT id, status, phase, version_id, created_at FROM build_jobs WHERE project_id = %s '
                      'ORDER BY created_at DESC LIMIT 5', (internal_key,))
    out['builds'] = [{'build_id': r[0], 'status': r[1], 'phase': r[2], 'version_id': r[3], 'at': r[4].isoformat()}
                     for r in builds] if isinstance(builds, list) else 'unavailable'
    versions = _q(pool, 'SELECT id, parent_id, repository_sha256, created_at FROM project_versions WHERE project_id = %s '
                        'ORDER BY created_at DESC LIMIT 10', (internal_key,))
    out['versions'] = [{'version_id': r[0], 'parent': r[1], 'sha256': r[2][:16], 'at': r[3].isoformat()}
                       for r in versions] if isinstance(versions, list) else 'unavailable'
    latest = builds[0][0] if isinstance(builds, list) and builds else None
    if latest:
        tasks = _q(pool, 'SELECT t.agent_key, t.state, t.evidence ->> \'plan_task\' FROM agent_tasks t JOIN agent_runs r ON r.id = t.run_id '
                         "WHERE r.subject_kind = 'build' AND r.subject_id = %s AND r.outcome IS DISTINCT FROM 'superseded' "
                         'ORDER BY t.created_at', (latest,))
        out['agent_execution'] = [{'agent': r[0], 'state': r[1], 'plan_task': r[2]} for r in tasks] if isinstance(tasks, list) else 'unavailable'
        checks = _q(pool, 'SELECT check_key, status, required, decision FROM build_stage_results WHERE build_id = %s ORDER BY id',
                    (latest,))
        out['verification'] = [{'check': r[0], 'status': r[1], 'required': r[2], 'decision': r[3]}
                               for r in checks] if isinstance(checks, list) else 'unavailable'
    cost = _q(pool, 'SELECT r.build_id, r.credits_reserved, r.estimated_provider_cost_usd, r.settled_provider_cost_usd, r.status '
                    'FROM credit_reservations r WHERE r.project_id = %s ORDER BY r.created_at DESC LIMIT 5', (internal_key,))
    out['cost'] = [{'build_id': r[0], 'credits': r[1], 'reserved_usd': str(r[2]), 'settled_usd': None if r[3] is None else str(r[3]),
                    'status': r[4]} for r in cost] if isinstance(cost, list) else 'unavailable'
    out['conversation_cost_usd'] = str(store.conversation_cost(project_id))
    return out
