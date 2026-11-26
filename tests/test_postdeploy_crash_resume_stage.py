"""crash-verify reads the build record it judges (S4.2; review of 78d3b79, 2026-11-26).

tests/test_postdeploy_crash_resume.py judged resume_verdict on its own and ran the stage once, with the started-over
ledger and no checkpoint in the record, asserting only "started over". That stage case also passes when the stage reads
the record wrongly: a silent default in place of the database value (`... or {'resumed_from': ...}`) or a constant
handed to resume_verdict -- the started-over ledger fails either way. The reviewer's two mutations of that line were
not caught. Here the stage runs with:
  * a ledger that continued (the killed worker finished architecture and codegen; the next worker only repairs and
    reviews) and NO checkpoint in the record: it must fail, and only for the missing checkpoint;
  * the same ledger WITH a checkpoint in the record: it must pass, and say the record's own values;
  * the started-over ledger with no checkpoint: it must fail on both counts.

The checkpoint's name is not compared with the ledger, by design for now: the ledger records the task types each worker
called, not checkpoint ids, and the checkpoint vocabulary (spec, round N, ...) is for S4.2's implementation to define.
What the ledger can show -- that no step a build makes once was called again -- resume_verdict checks.

Real path: the real stage_crash_verify and resume_verdict; only the database, the API and the reservation answers are
replaced. The ledger rows are those of tests/test_postdeploy_crash_resume.py (inspect run 37955419872), copied so this
file stands alone. Mutations: tests/negative_controls/postdeploy_crash_resume_stage.json.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest import mock

from omni_prod import postdeploy_checks as p

BUILD = 'bld_5e344e95ef8646269176b92edbfd4a21'
KILLED, RECOVERED = 'trc_killed', 'trc_recovered'
CHECK = 'crash: build continued from its last checkpoint (S4.2)'


def at(minute, second=0):
    return datetime(2026, 10, 9, 15, minute, second, tzinfo=timezone.utc)


STARTED_OVER = [                                    # inspect run 37955419872: the recovered worker called it all again
    (KILLED, 0, 'architecture', 'error', at(47, 20)), (KILLED, 1, 'architecture', 'ok', at(47, 22)),
    (RECOVERED, 0, 'architecture', 'error', at(50, 40)), (RECOVERED, 1, 'architecture', 'ok', at(50, 42)),
    (RECOVERED, 2, 'codegen', 'ok', at(51, 30)), (RECOVERED, 4, 'repair', 'ok', at(53, 0)),
    (RECOVERED, 5, 'review', 'error', at(54, 0)), (RECOVERED, 6, 'review', 'error', at(54, 1)),
    (RECOVERED, 7, 'review', 'ok', at(54, 5)),
]
CONTINUED = [
    (KILLED, 0, 'architecture', 'ok', at(47, 20)), (KILLED, 1, 'codegen', 'ok', at(48, 0)),
    (RECOVERED, 0, 'repair', 'ok', at(51, 0)), (RECOVERED, 1, 'review', 'ok', at(51, 30)),
]
# What the record says, with values no default could guess.
RECORDED = {'resumed_from': {'checkpoint': 'round 3', 'repository_sha256': 'c0ffee' * 10 + 'beef', 'rounds_spent': 3}}


def stage(ledger, recovery) -> dict:
    """The S4.2 result of the real crash-verify stage, over these database answers."""
    state = {'token': 't', 'crash_project': 'prj', 'crash_build': BUILD}
    asked = []

    def sql(query, params=()):
        asked.append(query.split(' FROM ')[0])
        if query.startswith('SELECT recovery_attempts'):
            return [(1, '0.06916125')]
        if query.startswith('SELECT count(*), COALESCE(sum(metered_cost_usd)'):
            return [(len(ledger), Decimal('0.07036800'), len({row[0] for row in ledger}))]
        if "economics_settlement'->'cost_basis'" in query:
            return [({'earlier_workers': {'calls': '2', 'metered_usd': '0.00120675', 'unknown_calls': '0'}},)]
        if query.startswith('SELECT trace_id, attempt_seq, task_type, outcome, created_at FROM task_attempts'):
            assert "kind = 'provider_call'" in query and params == (BUILD,)
            return list(ledger)
        if query.startswith("SELECT evidence_json->'recovery' FROM build_jobs"):
            assert params == (BUILD,)
            return [(recovery,)]
        raise AssertionError(query)

    def api(method, path, body=None, token=None, timeout=60.0):
        if path.endswith('/events?after=0'):
            return 200, {'events': [{'kind': 'info', 'message': 'recovered'}]}
        return 200, {'status': 'ready', 'error_code': None}
    p.RESULTS.clear()
    with mock.patch.object(p, 'sql', sql), mock.patch.object(p, 'api', api), \
            mock.patch.object(p, 'reservation', return_value={'status': 'SETTLED', 'settled': '0.070368'}), \
            mock.patch.object(p, 'record_agent_graph'), mock.patch('builtins.print'):
        p.stage_crash_verify(state)
    assert "SELECT evidence_json->'recovery'" in asked     # the stage read the record from the database
    [result] = [r for r in p.RESULTS if r['check'] == CHECK]
    return result


def test_a_continued_build_whose_record_names_no_checkpoint_fails():
    result = stage(CONTINUED, None)
    assert result['ok'] is False, result
    assert result['detail'].startswith('the build record does not name the checkpoint it continued from')
    assert 'started over' not in result['detail'] and 'recovery.resumed_from=null' in result['detail']


def test_the_stage_judges_the_record_it_reads():
    result = stage(CONTINUED, RECORDED)
    assert result['ok'] is True, result
    assert '"checkpoint": "round 3"' in result['detail'] and RECORDED['resumed_from']['repository_sha256'] in result['detail']
    assert "killed worker finished=['architecture', 'codegen'] recovered worker called=['repair', 'review']" in result['detail']


def test_a_build_that_started_over_with_no_checkpoint_fails_on_both_counts():
    result = stage(STARTED_OVER, None)
    assert result['ok'] is False
    assert 'started over: the recovered worker called architecture again' in result['detail']
    assert 'the build record does not name the checkpoint it continued from' in result['detail']
