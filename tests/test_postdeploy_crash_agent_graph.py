"""The agent-graph check that ended crash-recovery run 37954236866 red (law 2, 2026-11-26).

Run 37954236866 (2026-10-09, 2b4bafd, job 113900545454), step "Crash recovery (kill the build worker mid-build)": the
build recovered and was READY, the settlement matched the ledger, and crash-verify still failed on

    FAIL run=run_1fe72082ba8e45078d27 outcome=None tasks=15 succeeded=[14 agents] open=[] ... missing=[] verified=[7]

The worker writes the build's status (worker_tasks._run_live_build_job, jobs.transition) before it closes the build's
agent run (execute_live_build_job's finally: recorder.finish), and the check read the run in between. Inspect run
37955419872 (green, 54620a4) shows the same run closed 'ready' at 15:55:26 with the 15 tasks below. Fixed by 54620a4:
record_agent_graph waits, up to 60 s, for the run to be closed (postdeploy_checks.py, the first line of the function).

Real path: the real record_agent_graph, agent_graph and wait of omni_prod.postdeploy_checks; only the database answer
(the logged rows of agent_runs and agent_tasks) and the clock are replaced.
Mutations: tests/negative_controls/postdeploy_crash_agent_graph.json.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest import mock

from omni_prod import postdeploy_checks as p

RUN = 'run_1fe72082ba8e45078d27'
# inspect run 37955419872: the run's tasks in order, and crash-verify's log for who verified whom
STATES = ('discovery_agent:SUCCEEDED requirements_agent:SUCCEEDED product_planner:SUCCEEDED architecture_agent:SUCCEEDED '
          'coding_agent:SUCCEEDED qa_agent:FAILED repair_agent:SUCCEEDED code_review_agent:SUCCEEDED qa_agent:SUCCEEDED '
          'browser_rehearsal_agent:SUCCEEDED behavioral_acceptance_agent:SUCCEEDED security_agent:SUCCEEDED '
          'cost_economics_agent:SUCCEEDED release_agent:SUCCEEDED quality_gate_agent:SUCCEEDED').split()
VERIFIED_BY = {'behavioral_acceptance_agent': 'quality_gate_agent', 'browser_rehearsal_agent': 'quality_gate_agent',
               'cost_economics_agent': 'quality_gate_agent', 'qa_agent': 'quality_gate_agent',
               'release_agent': 'quality_gate_agent', 'repair_agent': 'qa_agent', 'security_agent': 'quality_gate_agent'}
# The detail of crash-verify's FAIL line in run 37954236866, word for word.
LOGGED_DETAIL = (
    "run=run_1fe72082ba8e45078d27 outcome=None tasks=15 succeeded=['architecture_agent', 'behavioral_acceptance_agent', "
    "'browser_rehearsal_agent', 'code_review_agent', 'coding_agent', 'cost_economics_agent', 'discovery_agent', "
    "'product_planner', 'qa_agent', 'quality_gate_agent', 'release_agent', 'repair_agent', 'requirements_agent', "
    "'security_agent'] open=[] self_verified=[] missing=[] verified=['behavioral_acceptance_agent<-quality_gate_agent', "
    "'browser_rehearsal_agent<-quality_gate_agent', 'cost_economics_agent<-quality_gate_agent', "
    "'qa_agent<-quality_gate_agent', 'release_agent<-quality_gate_agent', 'repair_agent<-qa_agent', "
    "'security_agent<-quality_gate_agent']")


def task_rows():
    ids = {}
    rows = []
    for i, item in enumerate(STATES):
        agent, state = item.split(':')
        ids[agent] = f't{i}'                          # a later task of the same agent (qa_agent) is the verifier
        rows.append([f't{i}', agent, state, None, None])
    for row in rows:
        verifier = VERIFIED_BY.get(row[1])
        if verifier and row[2] == 'SUCCEEDED':
            row[3], row[4] = ids[verifier], verifier
    return [tuple(r) for r in rows]


class Worker:
    """The database as the check saw it: the run is closed after `closes_after` reads of agent_runs."""
    def __init__(self, closes_after: int | None):
        self.closes_after, self.reads = closes_after, 0

    def sql(self, query, params=()):
        if 'FROM agent_runs' in query:
            self.reads += 1
            closed = self.closes_after is not None and self.reads > self.closes_after
            return [(RUN, 'ready' if closed else None, closed)]
        assert 'FROM agent_tasks' in query and params == (RUN,), query
        return task_rows()


class Clock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def check(closes_after):
    worker, clock = Worker(closes_after), Clock()
    p.RESULTS.clear()
    with mock.patch.object(p, 'sql', worker.sql), \
            mock.patch.object(p, 'time', SimpleNamespace(monotonic=clock.monotonic, sleep=clock.sleep)), \
            mock.patch('builtins.print') as printed:
        p.record_agent_graph('bld_5e344e95ef8646269176b92edbfd4a21', 'ready', ('coding_agent', 'quality_gate_agent'))
    [result] = p.RESULTS
    worker.printed = [c.args[0] for c in printed.call_args_list]
    return result, worker, clock


def test_the_rows_are_the_logged_run():
    rows = task_rows()
    assert len(rows) == 15 and len({r[1] for r in rows if r[2] == 'SUCCEEDED'}) == 14


def test_a_run_still_open_when_read_fails_with_the_logged_line():
    # never closed within the window: the check fails closed, with exactly the detail run 37954236866 logged
    result, worker, clock = check(closes_after=None)
    assert (result['check'], result['ok']) == ('agent task graph recorded', False)
    assert result['detail'] == LOGGED_DETAIL[:900]
    assert worker.printed == ['::error title=postdeploy agent task graph recorded::FAIL ' + LOGGED_DETAIL]   # the log line
    assert clock.now >= 60 and worker.reads > 1              # it waited the full minute, bounded, then read


def test_a_run_closed_after_the_build_status_passes():
    # what happened: the status was written first and the run closed moments later (inspect run 37955419872)
    result, worker, clock = check(closes_after=2)
    assert result['ok'] is True, result
    assert result['detail'].startswith(f'run={RUN} outcome=ready tasks=15 ')
    assert worker.reads == 4 and clock.now == 6.0             # two open reads, then the closed one, then the read


def test_the_check_still_fails_a_run_that_closed_with_another_outcome():
    worker, clock = Worker(closes_after=0), Clock()
    p.RESULTS.clear()
    with mock.patch.object(p, 'sql', worker.sql), \
            mock.patch.object(p, 'time', SimpleNamespace(monotonic=clock.monotonic, sleep=clock.sleep)), \
            mock.patch('builtins.print'):
        p.record_agent_graph('bld_x', 'cancelled', ())
    assert p.RESULTS[0]['ok'] is False and 'outcome=ready' in p.RESULTS[0]['detail']
