"""G-APPLE: the design contract, the static enforcement and refusal list, the two reviewers and the gate
(the owner, 2026-11-17). The contract is built from a real approved brief (the conversation's own functions); the
render probe's real-browser cases are in tests/test_g_apple_render.py. Negative controls follow (owner: tomorrow)."""
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from omni_prod import g_apple as A
from omni_prod import rehearsal
from omni_prod.autonomous_core import ExecutionReport
from omni_prod.g_apple import contract as C, reviewers as V, static as S
from omni_prod.skill_units import gate as G

CAFE = ('אתר לבית קפה שכונתי בתל אביב בשם קפה נחמה: תפריט עם מחירים, הסיפור שלנו, שעות פתיחה 07:00-19:00, '
        'טלפון 03-5551234, כתובת אבן גבירול 100 תל אביב')
PROMPT = rehearsal.approved_prompt(CAFE, {'content_only': 'yes', 'personal_data': 'no', 'login': 'none'})
CONTRACT = C.build(PROMPT)
ROOT = Path(__file__).resolve().parent.parent


def page(css='', body='<h1>קפה נחמה</h1><a class="btn" href="tel:035551234">התקשרו</a>', root=None):
    base = '''body{background:var(--color-bg);color:var(--color-text);font-family:var(--font-family);font-size:var(--text-16);margin:0}
h1{font-size:var(--text-40);font-weight:var(--weight-bold);margin:0 0 var(--space-16)}
.btn{background:var(--color-primary);color:var(--color-on-primary);padding:var(--space-16) var(--space-24);border-radius:var(--radius);border:1px solid var(--color-primary)}
.btn:hover{opacity:.9} .btn:active{opacity:.8} .btn:focus-visible{outline:2px solid var(--color-text)}
@media (max-width: 600px){ h1{font-size:var(--text-32)} }'''
    return (f'<!doctype html><html lang="he" dir="rtl"><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>קפה נחמה</title><style>{CONTRACT["css"] if root is None else root}\n'
            f'{base}\n{css}</style></head><body>{body}</body></html>')


def codes(html):
    return sorted({f['code'] for f in S.check(html, CONTRACT)})


class TheContract(unittest.TestCase):
    def test_it_is_locked_from_the_approved_brief_and_is_the_same_every_time(self):
        self.assertEqual(C.build(PROMPT), CONTRACT)
        t = CONTRACT['tokens']
        self.assertEqual((t['--radius'], t['--weight-regular'], t['--weight-bold']), ('8px', '400', '700'))
        self.assertEqual([t[f'--text-{px}'] for px in C.TYPE_PX], [f'{px}px' for px in C.TYPE_PX])
        self.assertTrue(all(px % 8 == 0 or px == 4 for px in C.SPACE_PX))
        self.assertEqual(len(C.WEIGHTS), 2)
        self.assertIn("'Heebo'", t['--font-family'])
        self.assertEqual(CONTRACT['dropped']['why'], 'one accent colour: the primary')
        self.assertIn(CONTRACT['fingerprint'], C.rules(CONTRACT))
        self.assertIn(CONTRACT['css'], C.rules(CONTRACT))

    def test_every_text_pair_is_measured_and_readable(self):
        for pair, ratio in CONTRACT['contrast'].items():
            self.assertGreaterEqual(ratio, C.MIN_UI_CONTRAST if pair == 'primary on bg' else C.MIN_TEXT_CONTRAST, pair)
        self.assertEqual(C.contrast('#000000', '#ffffff'), 21.0)
        self.assertEqual(C.contrast('#777777', '#777777'), 1.0)

    def test_a_palette_that_does_not_read_is_corrected_not_shipped(self):
        weak = PROMPT.replace(CONTRACT['tokens']['--color-text'], '#e5e5e5')       # pale text on a pale page
        fixed = C.build(weak)
        self.assertGreaterEqual(fixed['contrast']['text on bg'], 7.0)
        self.assertNotEqual(fixed['fingerprint'], CONTRACT['fingerprint'])

    def test_a_raw_request_has_no_contract_and_nothing_is_defaulted(self):
        with self.assertRaises(C.ContractError):
            C.build(CAFE)
        with self.assertRaises(C.ContractError):
            C.build(PROMPT.split('Design: style')[0])


class StaticEnforcement(unittest.TestCase):
    def test_a_page_that_keeps_the_contract_has_no_finding(self):
        self.assertEqual(S.check(page(), CONTRACT), [])

    def test_each_contract_rule(self):
        cases = {
            'RAW_COLOUR': 'p{color:#ff0000}',
            'PX_OFF_SCALE': 'p{margin:13px}',
            'THIRD_WEIGHT': 'p{font-weight:500}',
            'RADIUS_OFF': '.card{border-radius:14px}',
            'SECOND_ACCENT': 'p{color:var(--color-accent)}',
        }
        for code, css in cases.items():
            self.assertEqual(codes(page(css)), [code], css)
        self.assertEqual(codes(page(root=':root{--color-bg:#ffffff}')).count('CONTRACT_MISSING'), 1)
        self.assertIn('FOCUS_VISIBLE_MISSING', codes(page().replace('.btn:focus-visible{outline:2px solid var(--color-text)}', '')))
        self.assertEqual(codes(page().replace('.btn:hover{opacity:.9}', '')), ['STATE_MISSING'])

    def test_what_is_on_the_scale_or_not_a_size_is_not_a_finding(self):
        ok = ('.wrap{max-width:1100px;width:100%;min-height:400px;border-top:2px solid var(--color-border);'
              'padding:var(--space-32) 16px;gap:8px;font-weight:bold;border-radius:50%}')
        self.assertEqual(S.check(page(ok), CONTRACT), [])

    def test_the_refusal_list(self):
        three = ''.join(f'<div class="card"><svg></svg><h3>יתרון {i}</h3><p>טקסט</p></div>' for i in range(3))
        cases = {
            'LOREM': page(body='<h1>קפה</h1><p>Lorem ipsum dolor sit amet</p>'),
            'CAROUSEL': page(body='<h1>קפה</h1><div class="carousel"><div>א</div></div>'),
            'THREE_ICON_CARDS': page(body=f'<h1>קפה</h1><div class="features">{three}</div>'),
            'EMOJI_ICON': page(body='<h1>קפה</h1><ul><li><span>☕</span> קפה טרי</li></ul>'),
            'HERO_GRADIENT_STROKE': page('.hero{background:linear-gradient(90deg,var(--color-bg),var(--color-surface))} '
                                         '.hero h1{-webkit-text-stroke:1px var(--color-text)}'),
            'CENTER_EVERYWHERE': page('body{text-align:center}'),
            'SHADOW_EVERYWHERE': page(''.join(f'.s{i}{{box-shadow:0 8px 24px var(--color-border)}}' for i in range(5))),
            'BUTTON_STYLES': page('.btn-a{background:var(--color-surface)} .btn-b{background:var(--color-text)} '
                                  '.btn-c{background:var(--color-muted)}'),
        }
        for code, html in cases.items():
            self.assertIn(code, codes(html), code)
        four = three + '<div class="card"><svg></svg><h3>יתרון 4</h3></div>'
        self.assertNotIn('THREE_ICON_CARDS', codes(page(body=f'<h1>קפה</h1><div class="features">{four}</div>')))
        self.assertNotIn('EMOJI_ICON', codes(page(body='<h1>קפה</h1><p>הקפה שלנו טרי ☕ וחם, בואו לטעום אותו</p>')))

    def test_many_findings_of_one_code_are_capped_and_counted(self):
        many = S.check(page(''.join(f'.c{i}{{color:#00000{i}}}' for i in range(9))), CONTRACT)
        raw = [f for f in many if f['code'] == 'RAW_COLOUR']
        self.assertEqual(len(raw), S.MAX_PER_CODE + 1)
        self.assertIn('and 4 more', raw[-1]['why'])


class _Vision:
    accepts_task_tag = True

    def __init__(self, answers):
        self.answers, self.calls = answers, []

    def complete_json(self, **kw):
        self.calls.append(kw)
        answer = self.answers[len(self.calls) - 1]
        if isinstance(answer, Exception):
            raise answer
        return answer


SHOTS = {'desktop': b'\x89PNG-desktop', 'mobile': b'\x89PNG-mobile'}
CLEAN = [{'findings': []}, {'findings': [], 'category_marks': ['השם קפה נחמה', 'תפריט עם מחירים']}]


class TheReviewers(unittest.TestCase):
    def test_two_separate_calls_with_two_instructions_and_the_screenshots(self):
        vision = _Vision(CLEAN)
        a, b = (V.review(vision, name, SHOTS, business=CAFE) for name in V.REVIEWERS)
        self.assertEqual((a['status'], a['p0'], b['status'], b['p0']), ('REVIEWED', 0, 'REVIEWED', 0))
        self.assertEqual(len(vision.calls), 2)
        self.assertNotEqual(vision.calls[0]['system'], vision.calls[1]['system'])
        self.assertEqual(vision.calls[0]['images'], (SHOTS['desktop'], SHOTS['mobile']))
        self.assertNotIn('קפה נחמה', vision.calls[0]['user'])              # the typography reviewer is not told the brand
        self.assertIn('קפה נחמה', vision.calls[1]['user'])
        self.assertIn('do NOT write code', vision.calls[0]['system'])
        self.assertEqual(b['category_marks'], ['השם קפה נחמה', 'תפריט עם מחירים'])

    def test_a_finding_keeps_its_selector_and_severity_and_p0_is_counted(self):
        vision = _Vision([{'findings': [{'selector': 'header h1', 'severity': 'P0', 'viewport': 'phone', 'problem': 'הכותרת חתוכה'},
                                        {'selector': '.menu', 'severity': 'P2', 'viewport': 'both', 'problem': 'ריווח לא אחיד'}]}])
        r = V.review(vision, 'typography_layout', SHOTS)
        self.assertEqual((r['p0'], [f['selector'] for f in r['findings']]), (1, ['header h1', '.menu']))

    def test_a_page_with_no_mark_of_its_business_is_p0_by_the_category_clause(self):
        r = V.review(_Vision([{'findings': [], 'category_marks': []}]), 'brand_category', SHOTS, business=CAFE)
        self.assertEqual(r['p0'], 1)
        self.assertIn('any business', r['findings'][0]['problem'])

    def test_what_cannot_be_trusted_is_not_run_never_no_findings(self):
        bad = [RuntimeError('no vision route'), 'not a dict', {'findings': 'x'},
               {'findings': [{'selector': 'h1', 'severity': 'HIGH', 'problem': 'x'}]}, {'findings': []}]
        names = ['typography_layout'] * 4 + ['brand_category']
        for answer, name in zip(bad, names):
            r = V.review(_Vision([answer]), name, SHOTS)
            self.assertEqual(r['status'], 'NOT_RUN', answer)
            self.assertTrue(r['reason'])
        self.assertEqual(V.review(None, 'typography_layout', SHOTS)['status'], 'NOT_RUN')
        self.assertEqual(V.review(_Vision([]), 'typography_layout', {})['reason'], 'no screenshots')

    def test_a_deadline_ends_the_build_instead_of_being_a_result(self):
        from omni_prod.build_control import BuildDeadline
        with self.assertRaises(BuildDeadline):
            V.review(_Vision([BuildDeadline('out of time')]), 'typography_layout', SHOTS)


class _Inner:
    """Everything below the gate: passes, has this round's screenshots, and has no sandbox (render is NOT_RUN)."""
    last_shots = SHOTS

    def __init__(self, passed=True):
        self.passed = passed

    def execute(self, *, repository, spec):
        return ExecutionReport(self.passed, (), 'log')


def gate(html, mode, answers=CLEAN, inner=None):
    g = A.AppleGateExecutor(inner or _Inner(), CONTRACT, mode, gateway=_Vision(list(answers)), business=CAFE)
    return g, g.execute(repository={'index.html': html}, spec=None)


class TheGate(unittest.TestCase):
    def test_it_enters_at_warn_and_is_installed_last_right_before_the_build(self):
        self.assertIn('APPLE', G.CALIBRATING)
        engine = SimpleNamespace(executor=_Inner())
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('OMNI_GATE_APPLE', None)
            prompt = A.install(engine, prompt=PROMPT, gateway=_Vision(list(CLEAN)))
        self.assertEqual(engine.gate_modes['APPLE'], 'warn')
        self.assertIn(f"Design contract {CONTRACT['fingerprint']}", prompt)
        self.assertEqual(A.report(engine)['contract']['fingerprint'], CONTRACT['fingerprint'])
        worker = (ROOT / 'omni_prod' / 'worker_tasks.py').read_text(encoding='utf-8')
        at = worker.index('build_prompt = install_apple_gate(engine')
        for earlier in ('install_asset_marker_gate(engine)', 'install_asset_plan(engine', 'install_runtime_load(engine)',
                        'install_main_image(engine', "install_skill_gate(engine, 'G5')"):
            self.assertLess(worker.index(earlier), at, earlier)
        rest = worker[worker.index("'review'))", at):worker.index("_report_phase(jobs, build_id, 'GENERATING'")]
        self.assertNotIn('install', rest)                                  # nothing is installed after it
        self.assertIn("evidence['g_apple'] = apple_gate_report(engine)", worker)
        self.assertIn('install_apple_gate(engine, prompt=prompt', (ROOT / 'omni_prod' / 'rehearsal.py').read_text(encoding='utf-8'))

    def test_in_warn_everything_is_recorded_and_nothing_blocks(self):
        with self.assertLogs(A.__name__, level='INFO') as logs:
            g, report = gate(page('p{color:#ff0000}'), 'warn',
                             [{'findings': [{'selector': 'h1', 'severity': 'P0', 'viewport': 'both', 'problem': 'אין היררכיה'}]}, CLEAN[1]])
        self.assertTrue(report.passed)
        last = g.last_apple
        self.assertEqual((last['status'], [f['code'] for f in last['static']]), ('fail', ['RAW_COLOUR']))
        self.assertEqual([r['p0'] for r in last['reviewers']], [1, 0])
        self.assertTrue(any('render: no sandbox' in n for n in last['not_run']))       # said, not passed over
        self.assertTrue(any('APPLE mode=warn status=fail' in line for line in logs.output))

    def test_in_block_a_static_finding_and_a_reviewers_p0_fail_the_build_and_a_p1_does_not(self):
        g, report = gate(page('p{color:#ff0000}'), 'block')
        self.assertFalse(report.passed)
        self.assertIn('RAW_COLOUR', report.failures[0].message)
        p0 = [{'findings': [{'selector': '.hero', 'severity': 'P0', 'viewport': 'phone', 'problem': 'טקסט חתוך'}]}, CLEAN[1]]
        g, report = gate(page(), 'block', p0)
        self.assertEqual([f.acceptance_id for f in report.failures], [A.ACCEPTANCE_ID])
        self.assertIn('טקסט חתוך', report.failures[0].message)
        self.assertNotIn('{', report.failures[0].message.split(':', 1)[1])               # a problem, never code
        p1 = [{'findings': [{'selector': '.hero', 'severity': 'P1', 'viewport': 'phone', 'problem': 'ריווח'}]}, CLEAN[1]]
        self.assertTrue(gate(page(), 'block', p1)[1].passed)

    def test_a_clean_page_with_two_clean_reviewers_is_p0_zero(self):
        g, report = gate(page(), 'block')
        self.assertTrue(report.passed)
        self.assertEqual((g.last_apple['static'], sum(r['p0'] for r in g.last_apple['reviewers'])), ([], 0))

    def test_a_clean_page_whose_reviewer_did_not_run_is_not_run_never_a_pass(self):
        # one reviewer answers in the wrong shape: it did not review, so a page with no static finding is NOT_RUN
        g, report = gate(page(), 'block', [{'nonsense': True}, CLEAN[1]])
        self.assertTrue(report.passed)                                    # NOT_RUN never blocks ...
        self.assertEqual(g.last_apple['status'], 'NOT_RUN')               # ... and is never reported as a pass
        self.assertTrue(any(n.split(':')[0] in V.REVIEWERS for n in g.last_apple['not_run']))   # which one, and why

    def test_without_a_contract_the_gate_says_not_run_with_the_reason(self):
        engine = SimpleNamespace(executor=_Inner())
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('OMNI_GATE_APPLE', None)
            self.assertEqual(A.install(engine, prompt=CAFE), CAFE)                       # a raw request: nothing added
        with self.assertLogs(A.__name__, level='WARNING'):
            engine.executor.execute(repository={'index.html': page()}, spec=None)
        self.assertEqual(A.report(engine)['last']['status'], 'NOT_RUN')
        self.assertIn('no Design line', A.report(engine)['last']['reason'])

    def test_a_page_that_failed_earlier_is_not_judged_and_off_is_said(self):
        g, report = gate(page(), 'block', inner=_Inner(False))
        self.assertEqual((report.passed, g.last_apple), (False, None))
        engine = SimpleNamespace(executor=_Inner())
        with mock.patch.dict(os.environ, {'OMNI_GATE_APPLE': 'off'}), self.assertLogs(A.__name__, 'WARNING') as logs:
            self.assertEqual(A.install(engine, prompt=PROMPT), PROMPT)
        self.assertIn('GATE_OFF gate=APPLE', logs.output[0])


if __name__ == '__main__':
    unittest.main()
