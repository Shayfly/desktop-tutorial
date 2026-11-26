"""S4.2 on the real server: killed mid-build, the build continues from its last checkpoint (law 2, 2026-11-26).

The plan's acceptance for the crash step: kill the worker mid-build and the build continues from its last checkpoint
instead of starting over, with the build record showing it. crash-verify (omni_prod/postdeploy_checks.py) now records
'crash: build continued from its last checkpoint (S4.2)' through resume_verdict, beside the checks it had.

The real ledger of the one crash build whose recovery finished READY, bld_5e344e95 (run 37954236866, ledger printed by
inspect run 37955419872, 2026-10-09): the killed worker called architecture (gpt-6-luna HTTP 429, then
gemini-3.1-flash-lite ok, $0.00120675); the worker that finished called architecture again -- the same two calls, paid
twice -- and then codegen, repair and review. That is starting over, and the build record named no checkpoint. The log
prints no trace ids: 'trc_killed' and 'trc_recovered' stand for the two workers, whose rows the log shows twice for
attempt 0 and 1 (each worker counts its own attempts from 0) and the settlement counted as earlier_workers calls=2.

Real path: the real resume_verdict and the real stage_crash_verify; only the database, the API and the clock answers are
replaced, by the logged rows. Mutations: tests/negative_controls/postdeploy_crash_resume.json.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest import mock

from omni_prod import postdeploy_checks as p

KILLED, RECOVERED = 'trc_killed', 'trc_recovered'


def at(minute, second=0):
    return datetime(2026, 10, 9, 15, minute, second, tzinfo=timezone.utc)


# inspect run 37955419872, "attempts": the provider calls (attempt_seq | task_type | model | outcome)
LOGGED = [
    (KILLED, 0, 'architecture', 'error', at(47, 20)),        # gpt-6-luna: HTTP 429 no credits remaining
    (KILLED, 1, 'architecture', 'ok', at(47, 22)),           # gemini-3.1-flash-lite 0.00120675
    (RECOVERED, 0, 'architecture', 'error', at(50, 40)),     # the same two calls again after the recovery
    (RECOVERED, 1, 'architecture', 'ok', at(50, 42)),
    (RECOVERED, 2, 'codegen', 'ok', at(51, 30)),             # gemini-3.8-flash 0.05357925
    (RECOVERED, 4, 'repair', 'ok', at(53, 0)),
    (RECOVERED, 5, 'review', 'error', at(54, 0)),            # claude-sonnet-5-5: HTTP 400 credit balance too low
    (RECOVERED, 6, 'review', 'error', at(54, 1)),            # gpt-6.1-sol: HTTP 429
    (RECOVERED, 7, 'review', 'ok', at(54, 5)),               # gemini-3.8-flash
]
RESUMED = {'resumed_from': {'checkpoint': 'round 0', 'repository_sha256': 'a' * 64, 'rounds_spent': 0}}
# A build that continued: the killed worker wrote the spec and the first code; the next worker repairs from there.
CONTINUED = [
    (KILLED, 0, 'architecture', 'ok', at(47, 20)),
    (KILLED, 1, 'codegen', 'ok', at(48, 0)),
    (RECOVERED, 0, 'repair', 'ok', at(51, 0)),
    (RECOVERED, 1, 'review', 'ok', at(51, 30)),
]


def test_the_logged_recovery_started_over_and_named_no_checkpoint():
    ok, detail = p.resume_verdict(LOGGED, None)
    assert ok is False
    assert 'started over: the recovered worker called architecture again, which the killed worker had finished' in detail
    assert 'does not name the checkpoint' in detail
    assert detail.endswith("workers=2 killed worker finished=['architecture'] recovered worker called=['architecture', "
                           "'codegen', 'repair', 'review'] repeated=['architecture'] recovery.resumed_from=null")


def test_starting_over_fails_even_when_the_record_claims_a_checkpoint():
    ok, detail = p.resume_verdict(LOGGED, RESUMED)
    assert ok is False and 'started over' in detail and 'does not name' not in detail


def test_a_build_that_continued_from_its_checkpoint_passes():
    ok, detail = p.resume_verdict(CONTINUED, RESUMED)
    assert ok is True, detail
    assert detail.startswith("workers=2 killed worker finished=['architecture', 'codegen'] recovered worker "
                             "called=['repair', 'review'] repeated=[]")


def test_continuing_without_saying_so_in_the_record_fails():
    for recovery in (None, {}, {'resumed_from': {}}, {'resumed_from': 'round 0'}, {'resumed_from': {'checkpoint': ''}}):
        ok, detail = p.resume_verdict(CONTINUED, recovery)
        assert ok is False and 'does not name the checkpoint' in detail, recovery


def test_a_kill_before_any_finished_step_tests_nothing():
    early = [(KILLED, 0, 'architecture', 'error', at(47, 20)), (RECOVERED, 0, 'architecture', 'ok', at(50, 0))]
    ok, detail = p.resume_verdict(early, RESUMED)
    assert ok is False and 'the kill came before anything could be continued' in detail


def test_one_worker_is_no_recovery():
    ok, detail = p.resume_verdict([row for row in CONTINUED if row[0] == KILLED], RESUMED)
    assert ok is False and '1 worker(s) in the ledger: no recovery to judge' in detail
    assert p.resume_verdict([], RESUMED)[0] is False


def test_the_workers_are_told_apart_by_their_first_call_not_by_the_row_order():
    ok, detail = p.resume_verdict(list(reversed(CONTINUED)), RESUMED)
    assert ok is True, detail
    ok, detail = p.resume_verdict(list(reversed(LOGGED)), None)
    assert ok is False and "repeated=['architecture']" in detail


def test_crash_verify_records_the_s42_check_from_the_ledger():
    """The stage itself: the logged build (READY after one recovery, settled = ledger) still fails S4.2."""
    state = {'token': 't', 'crash_project': 'prj', 'crash_build': 'bld_5e344e95ef8646269176b92edbfd4a21'}

    def sql(query, params=()):
        if query.startswith('SELECT recovery_attempts'):
            return [(1, '0.06916125')]
        if query.startswith('SELECT count(*), COALESCE(sum(metered_cost_usd)'):
            return [(9, Decimal('0.07036800'), 2)]
        if "economics_settlement'->'cost_basis'" in query:
            return [({'earlier_workers': {'calls': '2', 'metered_usd': '0.00120675', 'unknown_calls': '0'}},)]
        if query.startswith('SELECT trace_id, attempt_seq, task_type, outcome, created_at FROM task_attempts'):
            assert "kind = 'provider_call'" in query and params == (state['crash_build'],)
            return LOGGED
        if query.startswith("SELECT evidence_json->'recovery'"):
            return [(None,)]
        raise AssertionError(query)

    def api(method, path, body=None, token=None, timeout=60.0):
        if path.endswith('/events?after=0'):
            return 200, {'events': [{'kind': 'info', 'message': 'השרת שעבד על זה הפסיק להגיב. מתחיל מחדש מהתחלה.'}]}
        return 200, {'status': 'ready', 'error_code': None}
    p.RESULTS.clear()
    with mock.patch.object(p, 'sql', sql), mock.patch.object(p, 'api', api), \
            mock.patch.object(p, 'reservation', return_value={'status': 'SETTLED', 'settled': '0.070368'}), \
            mock.patch.object(p, 'record_agent_graph'), mock.patch('builtins.print'):
        p.stage_crash_verify(state)
    by = {r['check']: r for r in p.RESULTS}
    assert by['crash: build recovered after its worker was killed']['ok'] is True
    assert by["crash: lost worker's calls are in the ledger and the settlement"]['ok'] is True
    s42 = by['crash: build continued from its last checkpoint (S4.2)']
    assert s42['ok'] is False and 'started over' in s42['detail']
