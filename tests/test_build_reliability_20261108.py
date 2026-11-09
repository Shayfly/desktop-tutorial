"""Founder build bld_ca727ba7 (2026-11-08): what failed, pinned.

1. The acceptance runner could not capture '[0].id' from a JSON array, so a correct app failed A2-A4.
2. Sonnet 5.5 ran adaptive thinking by default and returned no text; its repair answer opened with prose.
3. The repair loop stopped after 2 of 6 rounds on one unchanged patch.
4. The founder had nothing to open after a failed build.
"""
import json
import unittest
from unittest import mock

from omni_prod.autonomous_core import AcceptanceFailure, AutonomousProductEngine, ExecutionReport
from omni_prod.model_gateway import ANTHROPIC_JSON_ONLY_RULE, ModelEndpoint, OpenAICompatibleGateway
from omni_prod.repository_patch import parse_patch
from omni_prod.web_saas_acceptance import _capture


class _Json:
    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


class CapturePathTests(unittest.TestCase):
    def cap(self, path, data):
        out = {}
        _capture({'v': path}, _Json(data), out)
        return out['v']

    def test_root_array_index(self):
        self.assertEqual(self.cap('[0].id', [{'id': 1}, {'id': 3}]), 1)

    def test_nested_index_forms(self):
        data = {'items': [{'id': 7}]}
        for path in ('items[0].id', 'items.0.id', '$.items[0].id'):
            with self.subTest(path=path):
                self.assertEqual(self.cap(path, data), 7)

    def test_plain_keys_and_digit_object_key_still_work(self):
        self.assertEqual(self.cap('data.id', {'data': {'id': 'x'}}), 'x')
        self.assertEqual(self.cap('0', {'0': 'zero'}), 'zero')

    def test_missing_index_is_a_failure(self):
        with self.assertRaises(AssertionError):
            self.cap('[2].id', [{'id': 1}])
        with self.assertRaises(AssertionError):
            self.cap('[0].id', {'id': 1})


class _Resp:
    def __init__(self, payload):
        self.body, self.headers = json.dumps(payload).encode(), {}

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class AnthropicRequestTests(unittest.TestCase):
    def gateway(self, model, extra=()):
        gw = OpenAICompatibleGateway(ModelEndpoint(name='a', base_url='https://x.invalid', model=model, api_key='k',
                                                   external=True, api_style='anthropic', extra_body=extra))
        sent = {}

        def urlopen(req, timeout=None):
            sent.update(json.loads(req.data))
            return _Resp({'content': [{'type': 'text', 'text': '{"ok": true}'}], 'stop_reason': 'end_turn'})
        gw._urlopen = urlopen
        return gw, sent

    def test_sonnet_5_5_turns_off_up_front_thinking_and_states_the_json_rule(self):
        gw, sent = self.gateway('claude-sonnet-5-5')
        self.assertEqual(gw.complete_json(system='S', user='U'), {'ok': True})
        self.assertEqual(sent['thinking'], {'type': 'between_tools'})
        self.assertTrue(sent['system'].startswith('S') and sent['system'].endswith(ANTHROPIC_JSON_ONLY_RULE))

    def test_catalog_value_wins_and_other_models_are_untouched(self):
        gw, sent = self.gateway('claude-sonnet-5-5', extra=(('thinking', json.dumps({'type': 'adaptive'})),))
        gw.complete_json(system='S', user='U')
        self.assertEqual(sent['thinking'], {'type': 'adaptive'})
        gw, sent = self.gateway('claude-other')
        gw.complete(system='S', user='U')
        self.assertNotIn('thinking', sent)
        self.assertEqual(sent['system'], 'S')        # plain complete() is not a JSON call

    def test_catalog_entry_sets_between_tools(self):
        import pathlib
        catalog = json.loads(pathlib.Path('infra/worker-host/model-catalog.json').read_text())
        items = catalog if isinstance(catalog, list) else catalog['models']
        sonnet = next(m for m in items if m['name'] == 'anthropic-claude-sonnet-5-5')
        self.assertEqual(sonnet['extra_body']['thinking'], {'type': 'between_tools'})


class _Arch:
    def create_spec(self, prompt):
        return 'spec'


class _Gen:
    def generate(self, spec):
        return parse_patch({'files': [{'path': 'app.py', 'content': 'v0'}]})


class _Rep:
    def __init__(self, contents):
        self.contents, self.calls, self.failures = list(contents), 0, []

    def repair(self, **kw):
        self.calls += 1
        self.failures.append(kw['failures'])
        return parse_patch({'files': [{'path': 'app.py', 'content': self.contents.pop(0)}]})


class _Exec:
    def __init__(self, passing=()):
        self.passing = set(passing)

    def execute(self, *, repository, spec):
        if repository['app.py'] in self.passing:
            return ExecutionReport(True)
        return ExecutionReport(False, (AcceptanceFailure('A1', f"boom at {repository['app.py']}"),))


class SecondChanceTests(unittest.TestCase):
    def engine(self, rep, ex, chances):
        e = AutonomousProductEngine(architect=_Arch(), generator=_Gen(), repairer=rep, executor=ex,
                                    max_repair_rounds=6, repair_ceiling=6)
        e.no_progress_retries = chances
        return e

    def test_default_keeps_the_stop_loss(self):
        rep = _Rep(['v0', 'v1'])
        result = self.engine(rep, _Exec(), 0).build('p')
        self.assertEqual((result.stop_reason, rep.calls), ('no_progress_repository_unchanged', 1))

    def test_one_second_chance_is_told_and_can_pass(self):
        rep = _Rep(['v0', 'v1'])
        result = self.engine(rep, _Exec(passing={'v1'}), 1).build('p')
        self.assertEqual((result.status, result.stop_reason, rep.calls), ('ready', 'passed', 2))
        self.assertIn('NO_PROGRESS', [f['acceptance_id'] for f in rep.failures[1]])

    def test_chances_are_bounded(self):
        rep = _Rep(['v0', 'v0', 'v0'])
        result = self.engine(rep, _Exec(), 1).build('p')
        self.assertEqual((result.stop_reason, rep.calls), ('no_progress_repository_unchanged', 2))

    def test_running_out_of_rounds_is_labelled_as_such(self):
        rep = _Rep(['v0', 'v1', 'v2', 'v3', 'v4', 'v5', 'v6'])
        result = self.engine(rep, _Exec(), 1).build('p')
        self.assertEqual(result.stop_reason, 'max_repair_rounds')
        self.assertEqual(result.repair_rounds, 6)


class FounderDraftTests(unittest.TestCase):
    def test_only_founder_and_only_check_failures(self):
        from omni_prod.worker_tasks import _founder_draft_allowed, _version_message
        with mock.patch.dict('os.environ', {'OMNI_FOUNDER_ACCOUNT_IDS': 'usr_f'}):
            self.assertTrue(_founder_draft_allowed({'user_id': 'usr_f'}, 'verification_failed'))
            self.assertFalse(_founder_draft_allowed({'user_id': 'usr_c'}, 'verification_failed'))
            self.assertFalse(_founder_draft_allowed({'user_id': 'usr_f'}, 'security_gate_failed'))
            with mock.patch.dict('os.environ', {'OMNI_FOUNDER_DRAFT_VERSIONS': '0'}):
                self.assertFalse(_founder_draft_allowed({'user_id': 'usr_f'}, 'verification_failed'))
        self.assertIn('DRAFT', _version_message('b1', True))
        self.assertEqual(_version_message('b1', False), '148AI async live build b1')


if __name__ == '__main__':
    unittest.main()


class StationSkillPackTests(unittest.TestCase):
    """CEO 2026-11-08 23:04: 10-20 world-class skills, each tied to the stations that use it."""

    def test_pack_size_and_every_station_has_a_method(self):
        from omni_prod.skills_runtime import WEB_SKILLS, skills_for
        self.assertTrue(10 <= len(WEB_SKILLS) <= 20)
        keys = {role: {s.key for s in skills_for(role)} for role in ('architect', 'generator', 'repair', 'reviewer')}
        self.assertIn('skill.spec_precision', keys['architect'])
        self.assertIn('skill.acceptance_plan', keys['generator'])
        self.assertIn('skill.repair_method', keys['repair'])
        self.assertIn('skill.security_basics', keys['reviewer'])

    def test_family_specific_skills_say_when_they_apply(self):
        from omni_prod.skills_runtime import DATA_INTEGRITY, GAME_2D, LANDING_CONVERSION
        self.assertTrue(GAME_2D.guidance.startswith('ONLY for a game'))
        self.assertTrue(LANDING_CONVERSION.guidance.startswith('ONLY for a website or landing page'))
        self.assertIn('ONLY when the product books a resource', DATA_INTEGRITY.guidance)

    def test_prompts_carry_the_skills(self):
        import omni_prod.autonomous_agents as agents
        self.assertIn('skill.repair_method@1', agents._REPAIR_SYSTEM)
        self.assertIn('skill.acceptance_plan@1', agents._GENERATOR_SYSTEM)
        self.assertIn('skill.spec_precision@1', agents._ARCHITECT_SYSTEM)


class SkillStaticCheckTests(unittest.TestCase):
    def test_new_checks_report_advisory_findings(self):
        from omni_prod.skills_runtime import static_findings
        repo = {'app.py': 'cur.execute(f"SELECT * FROM t WHERE id={x}")\ncur.execute("SELECT 1 WHERE a=?", (a,))',
                'index.html': '<html><label for="n">n</label><input id="n"><input id="p"><p>Lorem ipsum</p></html>'}
        got = {(f.skill, f.severity) for f in static_findings(repo)}
        for skill in ('skill.security_basics', 'skill.accessibility', 'skill.copy_quality'):
            self.assertIn((skill, 'advisory'), got)
        clean = {'app.py': 'cur.execute("SELECT 1 WHERE a=?", (a,))'}
        self.assertFalse([f for f in static_findings(clean) if f.skill == 'skill.security_basics'])


class RepairVisibilityTests(unittest.TestCase):
    """bld_624610bc (2026-11-09): a 51K-char app.py was hidden from every repair round."""

    def test_large_entry_file_is_shown_to_the_repairer(self):
        from omni_prod.modifier_engine import repo_summary
        repo = {'app.py': 'x = 1\n' * 9000, '.omni/project.json': '{}'}      # 54K chars
        files = {f['path']: f for f in repo_summary(repo, [])['files']}
        self.assertIn('content', files['app.py'])

    def test_sonnet_output_cap_and_code_structure_skill(self):
        import pathlib
        from omni_prod.skills_runtime import WEB_SKILLS
        catalog = json.loads(pathlib.Path('infra/worker-host/model-catalog.json').read_text())
        items = catalog if isinstance(catalog, list) else catalog['models']
        sonnet = next(m for m in items if m['name'] == 'anthropic-claude-sonnet-5-5')
        self.assertGreaterEqual(sonnet['max_output_tokens'], 40000)
        self.assertIn('skill.code_structure', {s.key for s in WEB_SKILLS})


class IndentationGuardTests(unittest.TestCase):
    """bld_3f5dc453 / bld_5b2e8f58 (2026-11-09): flattened Python from Sonnet was adopted and burned every round."""

    FLAT = {'files': [{'path': 'app.py', 'content': 'def f():\nreturn 1\n'}]}
    GOOD = {'files': [{'path': 'app.py', 'content': 'def f():\n    return 1\n'}]}

    def test_guard_rejects_only_lost_indentation(self):
        from omni_prod.autonomous_agents import _code_shape_guard
        from omni_prod.model_gateway import ModelJSONRejected
        with self.assertRaises(ModelJSONRejected):
            _code_shape_guard(self.FLAT)
        _code_shape_guard(self.GOOD)
        _code_shape_guard({'files': [{'path': 'a.py', 'content': 'x = (\n'}]})   # other syntax: repair's job
        _code_shape_guard({'files': [{'path': 'index.html', 'content': '<p>\n</p>'}]})

    def test_router_escalates_to_the_next_model(self):
        from decimal import Decimal
        from omni_prod.autonomous_agents import _code_shape_guard
        from omni_prod.model_catalog import CatalogModel
        from omni_prod.model_policy import ModelUsePolicy
        from omni_prod.model_router import ModelOption, RoutingPolicy
        from omni_prod.routed_gateway import RoutedModelGateway

        def m(name, price):
            return CatalogModel(endpoint=ModelEndpoint(name=name, base_url='https://x.invalid', model=name, api_key='k',
                                                       external=True),
                                option=ModelOption('p', name, 90, 1000, Decimal(price), Decimal(price)),
                                max_output_tokens=4000, api_key_env='K')
        gw = RoutedModelGateway(ranked=(m('first', '1'), m('second', '5')),
                                routing_policy=RoutingPolicy(minimum_quality=0, prefer_cost=True),
                                policy=ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                                                      external_budget_usd=Decimal('10'),
                                                      max_external_calls_per_build=10))
        used = []

        def attempt(route, method, kwargs, why, **kw):
            used.append(route.endpoint.name)
            return self.FLAT if route.endpoint.name == 'first' else self.GOOD
        with mock.patch.object(gw, '_attempt', side_effect=attempt):
            out = gw.complete_json(system='s', user='u', max_tokens=100, task='codegen', validate=_code_shape_guard)
        self.assertEqual(out, self.GOOD)
        self.assertEqual(used, ['first', 'second'])


class MissingKindHintTests(unittest.TestCase):
    def test_missing_delete_says_what_a_passing_step_is(self):
        from omni_prod.behavior_acceptance import _failure_text
        msg, evidence = _failure_text({'checks': [], 'missing_kinds': ['data_delete']})
        self.assertIn('SUCCESSFULLY removes or cancels', msg + evidence)

    def test_reviewer_treats_timing_edge_cases_as_advisory(self):
        from omni_prod.product_review import _REVIEW_SYSTEM
        self.assertIn('rapid repeated clicks', _REVIEW_SYSTEM)
class BuildRestoreUiTests(unittest.TestCase):
    """2026-11-09: a queued/running build vanished after a reload; a finished build's result was not shown again."""

    def setUp(self):
        import pathlib
        self.js = pathlib.Path('omni_prod/assets/app.js').read_text(encoding='utf-8')

    def test_background_quote_never_clears_an_active_build(self):
        self.assertIn("if (open === true && (!S.build || isTerminal(S.build.status))) S.build = null;", self.js)
        self.assertNotIn("    S.build = null; renderDiscovery(); renderPlan(); renderTrack();", self.js)

    def test_finished_build_is_restored_without_preview_start(self):
        start = self.js.index('async function restoreBuild()')
        body = self.js[start:self.js.index('\n}\n', start)]
        self.assertIn('if (isTerminal(b.status))', body)
        self.assertNotIn('startPreview', body)


class ReviewConvergenceTests(unittest.TestCase):
    """bld_9bd3c1c4 (2026-11-09): all checks passed; five review rounds kept finding new edge cases."""

    def executor(self, rounds):
        from omni_prod.autonomous_core import ExecutionReport
        from omni_prod.product_review import ProductReviewExecutor

        class Gw:
            accepts_task_tag = True
            last_usage = None

            def __init__(self):
                self.calls = []

            def complete_json(self, **kw):
                self.calls.append(json.loads(kw['user']))
                return {'findings': rounds.pop(0)}

        class Inner:
            def execute(self, **kw):
                return ExecutionReport(True)
        gw = Gw()
        return ProductReviewExecutor(Inner(), gateway=gw, max_reviews=6), gw

    def f(self, skill, file, problem='p'):
        return {'skill': skill, 'severity': 'blocking', 'file': file, 'problem': problem, 'fix': 'x'}

    def test_new_minor_finding_in_a_re_review_does_not_block(self):
        ex, gw = self.executor([[self.f('skill.ui_states', 'static/app.js')],
                                [self.f('skill.form_validation', 'rules.py', 'lone surrogate -> 500')]])
        self.assertFalse(ex.execute(repository={'app.py': ''}, spec=None).passed)
        self.assertTrue(ex.execute(repository={'app.py': ''}, spec=None).passed)
        self.assertIn('previous_blocking', gw.calls[1])

    def test_repeated_or_security_findings_still_block(self):
        ex, _ = self.executor([[self.f('skill.ui_states', 'static/app.js')],
                               [self.f('skill.ui_states', 'static/app.js'), self.f('skill.security_basics', 'db.py')]])
        ex.execute(repository={'app.py': ''}, spec=None)
        report = ex.execute(repository={'app.py': ''}, spec=None)
        self.assertFalse(report.passed)
        self.assertEqual(len(report.failures), 2)


class IntakeTruncatedReplyTests(unittest.TestCase):
    """2026-11-09 19:24: a long brief made Haiku spend all 1,400 output tokens; the user saw 'the agent could not answer'."""

    def test_reply_is_salvaged_from_cut_json(self):
        from omni_prod.intake.reservation_worker import salvage_reply
        self.assertEqual(salvage_reply('{"reply": "שלום! הבנתי את הבקשה לדף נחיתה.", "proposals": [{"x": "'),
                         'שלום! הבנתי את הבקשה לדף נחיתה.')
        self.assertIsNone(salvage_reply('{"proposals": ['))

    def test_output_budget_and_message_cap(self):
        from decimal import Decimal
        from omni_prod.intake.interpreter import MAX_OUTPUT_TOKENS
        self.assertGreaterEqual(MAX_OUTPUT_TOKENS, 2400)
        # Venice price ceiling 0.90 USD per million output tokens: still far under the 0.015 per-message cap.
        self.assertLess(Decimal(MAX_OUTPUT_TOKENS) * Decimal('0.90') / Decimal(10**6), Decimal('0.005'))


class IntakeFalseBlockerTests(unittest.TestCase):
    """2026-11-09 19:32: a café landing page with a WhatsApp button and 'בלי תשלום' was blocked as payments + SMS."""

    def kinds(self, text):
        import re
        from omni_prod.intake.contract import _INTEGRATION_WORDS, strip_negated
        from omni_prod.product_architect import strip_whatsapp_links
        t = strip_negated(strip_whatsapp_links(text))
        return [k for k, p in _INTEGRATION_WORDS if re.search(p, t, re.I)]

    def test_excluded_and_link_only_features_are_not_integrations(self):
        self.assertEqual(self.kinds('כפתור "הזמנה ב-WhatsApp" למעלה. תפריט עם מחירים. בלי הרשמה, בלי התחברות ובלי תשלום.'), [])
        self.assertEqual(self.kinds('No payments, without stripe.'), [])

    def test_real_integrations_are_still_found(self):
        self.assertEqual(self.kinds('צריך תשלום באשראי ושליחת הודעות תזכורת'), ['payments', 'sms'])
        self.assertIn('payments', self.kinds('notes: checkout with stripe'))

    def test_blocker_is_hebrew(self):
        from omni_prod.conversation.supervisor import ConversationSupervisor, _TXT
        msg = ConversationSupervisor._finding_message({'item': 'integration: payments', 'alternative': 'x'}, 'he', _TXT['he'])
        self.assertNotRegex(msg, r'[A-Za-z]{4,}')

    def test_chat_resends_a_dropped_request_with_the_same_key(self):
        import pathlib
        js = pathlib.Path('omni_prod/assets/app.js').read_text(encoding='utf-8')
        self.assertIn('await whenVisible();', js)
        self.assertIn("if (err.status !== 0 || err.detail === 'timeout' || attempt >= 3) throw err;", js)


class IntakeNegationEinTests(unittest.TestCase):
    """2026-11-09 19:55: 'אין תשלום ואין שליחת הודעות' still blocked as payments + SMS."""

    def kinds(self, text):
        import re
        from omni_prod.intake.contract import _INTEGRATION_WORDS, strip_negated
        t = strip_negated(text)
        return [k for k, p in _INTEGRATION_WORDS if re.search(p, t, re.I)]

    def test_ein_negates(self):
        self.assertEqual(self.kinds('אין תשלום ואין שליחת הודעות, רק כפתור קישור ל-וואטסאפ'), [])

    def test_a_need_after_a_negation_is_kept(self):
        self.assertEqual(self.kinds('אין לי אתר ואני צריך תשלום באשראי'), ['payments'])


class CapabilityNegationTests(unittest.TestCase):
    """2026-11-09 20:20: café landing page stuck on 'no verified price' for integration.payment from 'ובלי תשלום'."""

    PROMPT = ('אני רוצה דף נחיתה לבית קפה. תפריט עם מחירים: קפה הפוך – 14 ₪. כפתור ירוק "הזמנה ב-WhatsApp" למעלה ובסוף. '
              'בלי הרשמה, בלי התחברות ובלי תשלום. רק דף שמציג את העסק.')

    def test_excluded_payment_is_not_a_capability(self):
        from omni_prod.product_architect import ProductArchitect
        c = ProductArchitect().compile(self.PROMPT, project_id='p', contract_version=1)
        keys = {r.key for r in c.capability_plan.requirements}
        self.assertNotIn('integration.payment', keys)
        self.assertNotIn('integration.messaging', keys)
        self.assertEqual(tuple(c.required_integrations), ())

    def test_requested_payment_still_is(self):
        from omni_prod.product_architect import ProductArchitect
        c = ProductArchitect().compile('חנות קטנה עם תשלום באשראי בסוף ההזמנה', project_id='p', contract_version=1)
        self.assertIn('integration.payment', {r.key for r in c.capability_plan.requirements})


class LandingSmokeTests(unittest.TestCase):
    """bld_c85cca89 (2026-11-09): a café landing page (only a WhatsApp link) failed 6 rounds as 'placeholder'."""

    def run_smoke(self, html):
        import http.server, pathlib, subprocess, sys, tempfile, threading
        from omni_prod.preview_smoke import _SMOKE
        d = pathlib.Path(tempfile.mkdtemp())
        (d / 'index.html').write_text(html, encoding='utf-8')
        (d / 'serve.py').write_text(
            'import http.server, os, functools\n'
            'h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=os.path.dirname(__file__))\n'
            'http.server.ThreadingHTTPServer(("127.0.0.1", int(os.environ["PORT"])), h).serve_forever()\n')
        (d / '.omni').mkdir()
        import socket
        s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
        (d / '.omni' / 'project.json').write_text(json.dumps({'port': port, 'start': [sys.executable, 'serve.py']}))
        r = subprocess.run([sys.executable, '-c', _SMOKE], cwd=d, capture_output=True, text=True, timeout=60)
        return r.stdout.splitlines()[0]

    def test_content_page_with_only_links_passes(self):
        page = ('<!doctype html><html lang="he" dir="rtl"><head><title>קפה</title></head><body><h1>קפה בוקר טוב</h1>'
                '<p>' + 'הקפה הכי טוב בשכונה, מאפים טריים כל בוקר וישיבה בחוץ. ' * 8 + '</p>'
                '<a href="https://wa.me/972501234567">הזמנה ב-WhatsApp</a></body></html>')
        self.assertEqual(self.run_smoke(page), 'PREVIEW-SMOKE OK')

    def test_bare_placeholder_still_fails(self):
        self.assertIn('placeholder', self.run_smoke('<!doctype html><html><body><p>Coming soon</p></body></html>'))
