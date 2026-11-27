"""Run 45869754310 (golden-rehearsal, main 4d85e30): the build finished `failed repair_rounds=3 failures=14`, then the
rehearsal crashed writing its annotations (`KeyError: 'failing'`): the repair trace has four kinds of entry and only the
per-round one has `failing`. The trace here is written by the real AutonomousProductEngine (one engine per kind), never
copied by hand, and the failed rehearsal must name what the run lacked: the ids and messages of every round."""
import json
import unittest
from types import SimpleNamespace

from omni_prod import rehearsal as R
from omni_prod.autonomous_core import (AcceptanceFailure, AutonomousProductEngine, ExecutionReport, RepairDeclined)
from omni_prod.model_gateway import ModelGatewayError
from omni_prod.repository_patch import parse_patch

FAILS = (AcceptanceFailure('A1', 'GET / did not return the name'), AcceptanceFailure('VISUAL', 'text overlaps at 390px'))


def real_engine(repair, extra_files=None):
    class Architect:
        def create_spec(self, prompt): return 'spec'

    class Generator:
        def generate(self, spec): return parse_patch({'files': [{'path': 'app.py', 'content': 'v0'}]})

    class Repairer:
        calls = 0
        def repair(self, **kw):
            Repairer.calls += 1
            return repair(Repairer.calls)

    class Executor:
        def execute(self, *, repository, spec): return ExecutionReport(False, FAILS)

    return AutonomousProductEngine(architect=Architect(), generator=Generator(), repairer=Repairer(),
                                   executor=Executor(), max_repair_rounds=3)


def patch(n): return parse_patch({'files': [{'path': 'app.py', 'content': f'v{n}'}]})


def declined(n):
    raise RepairDeclined('platform_render_defect', 'an image without alt', paid_call=True)


def no_route(n):
    raise ModelGatewayError('all model routes failed: a: no valid JSON')


PROMPT = 'אתר לאטליז "בשר השכונה" ברחוב הרצל 12, חיפה. טלפון 04-8123456.'
TEST = 'import app\n\ndef test_title():\n    assert app.TITLE == "Butcher"\n'


def escalated_trace():
    """The same expected value of a test fixed twice: the loop's own `escalated` entry (tests/test_repair_test_edits)."""
    fixes = [TEST.replace('== "Butcher"', '== "Butcher shop"'), TEST.replace('== "Butcher"', '== "The butcher"')]

    class Architect:
        def create_spec(self, prompt): return 'spec'

    class Generator:
        def generate(self, spec):
            return parse_patch({'files': [{'path': 'app.py', 'content': 'TITLE = "x"'},
                                          {'path': 'tests/test_app.py', 'content': TEST}]})

    class Repairer:
        def repair(self, **kw):
            return parse_patch({'files': [{'path': 'tests/test_app.py', 'content': fixes.pop(0) if fixes else 'x'}]})

    class Executor:
        runs = 0
        def execute(self, *, repository, spec):
            Executor.runs += 1                       # a different message each round: not "the same failure"
            return ExecutionReport(False, (AcceptanceFailure('A1', f'fail {Executor.runs}'),) + FAILS)

    eng = AutonomousProductEngine(architect=Architect(), generator=Generator(), repairer=Repairer(), executor=Executor(),
                                  max_repair_rounds=4)
    result = eng.build(PROMPT)
    assert result.stop_reason == 'test_value_fixed_twice', result.stop_reason
    return eng.trace


def built(repair):
    eng = real_engine(repair)
    eng.build('p')
    return eng


class TheRealTraceShapes(unittest.TestCase):
    def test_every_kind_the_core_writes_is_named_and_printed(self):
        traces = {'failing': built(patch).trace, 'repair_declined': built(declined).trace,
                  'repair_model_unavailable': built(no_route).trace}
        traces['escalated'] = escalated_trace()
        for kind, trace in traces.items():
            self.assertIn(kind, {R.trace_kind(t) for t in trace}, kind)
        entries = [t for tr in traces.values() for t in tr]
        text = '\n'.join(R.trace_line(t) for t in entries)
        self.assertIn("failing ['A1', 'VISUAL']", text)
        self.assertIn('repair declined (platform_render_defect, paid_call=True)', text)
        self.assertIn('no model route answered the repair', text)
        self.assertIn('escalated', text)

    def test_annotations_do_not_crash_on_a_trace_of_every_kind(self):
        trace = built(patch).trace + built(declined).trace + built(no_route).trace
        report = {'outcome': 'failed', 'trace': trace + escalated_trace()}
        line = [l for l in R.annotations(report) if 'title=repair rounds::' in l][0]
        self.assertIn("failing ['A1', 'VISUAL']", line)

    def test_an_unknown_kind_fails_loudly_with_its_name(self):
        with self.assertRaises(ValueError) as cm:
            R.annotations({'outcome': 'failed', 'trace': [{'round': 1, 'a_new_kind': 'x'}]})
        self.assertIn('a_new_kind', str(cm.exception))


class TheFailedReportSaysWhatFailed(unittest.TestCase):
    def report(self):
        eng = built(declined)
        failing = lambda: SimpleNamespace(acceptance_id='SEQ', message='m' * 900)
        eng._taxonomy_rounds = eng._taxonomy_rounds + [(9, [failing() for _ in range(12)])]
        return {'prompt': 'x', 'outcome': 'failed', 'stop_reason': 'platform_render_defect', 'build_id': 'rehearsal-1',
                'error_code': 'verification_failed', 'release_gate_message': 'build did not pass sandbox verification',
                'site_route': {'route': 'content_document', 'reason': 'library route'},
                'model_calls': 7, 'authorized_spend_usd': '0.4275',
                'tokens': {'input': 10, 'output': 5, 'by_model': {'gpt-x': [10, 5, 7]}},
                'round_failures': R.round_failures(eng), 'trace': eng.trace}

    def test_the_lines_carry_the_id_the_code_the_failing_ids_the_route_and_the_cost(self):
        lines = R.annotations(self.report())
        head = [l for l in lines if l.startswith('::error title=failed build::')][0]
        for word in ('build_id=rehearsal-1', 'error_code=verification_failed', 'build did not pass sandbox verification',
                     'route=content_document', 'spend_usd=0.4275', 'calls=7', 'gpt-x: 7 calls'):
            self.assertIn(word, head)
        per_round = [l for l in lines if l.startswith('::error title=failing per round::')][0]
        self.assertIn('A1: GET / did not return the name', per_round)
        self.assertIn('VISUAL: text overlaps at 390px', per_round)
        self.assertIn('(+2 not shown)', per_round)                       # 12 in the last round, 10 kept, said so
        self.assertNotIn('m' * 301, per_round)                           # a message is cut at 300
        self.assertTrue(all('\n' not in l for l in lines))

    def test_a_ready_report_prints_no_failure_section(self):
        lines = R.annotations({'prompt': 'x', 'build_id': 'rehearsal-1', 'outcome': 'ready', 'quality': {'passed': True},
                               'release_policy': {'decision': 'READY'}})
        self.assertFalse([l for l in lines if 'failed build' in l])


if __name__ == '__main__':
    unittest.main()
