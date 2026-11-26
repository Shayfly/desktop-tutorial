"""S4.2 without a database: the engine continues from each checkpoint exactly as it would have gone on, and a checkpoint
is trusted only when every stored byte matches its sha256 (the owner chose to continue, 2026-11-26 10:13 UTC).

Real path: AutonomousProductEngine with the real ArchitectAgent, GeneratorAgent and RepairAgent on the real
RoutedModelGateway and OpenAICompatibleGateway; only the HTTP answer is scripted (Model below answers from the request
alone, so the same question gets the same answer). The checks are a pure function of the repository. The killed worker,
the janitor and PostgreSQL are in tests/test_crash_resume_pg.py. Mutations: tests/negative_controls/crash_resume.json.
"""
from __future__ import annotations

import io
import json
import re
import subprocess
import unittest
import zipfile
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from omni_prod import build_checkpoint as C
from omni_prod.attempt_ledger import TaskTaggedGateway
from omni_prod.autonomous_agents import (_ARCHITECT_SYSTEM, _GENERATOR_SYSTEM, _REPAIR_SYSTEM, ArchitectAgent,
                                         GeneratorAgent, RepairAgent)
from omni_prod.autonomous_core import (AcceptanceFailure, AutonomousProductEngine, ExecutionReport, ResumePoint,
                                       report_to_dict)
from omni_prod.model_catalog import CatalogModel
from omni_prod.model_gateway import ModelEndpoint, OpenAICompatibleGateway
from omni_prod.model_policy import ModelUsePolicy
from omni_prod.model_router import ModelOption, RoutingPolicy
from omni_prod.routed_gateway import RoutedModelGateway
from omni_prod.workspace import _checksum

ROOT = Path(__file__).resolve().parents[1]
SPEC = {'title': 'Reading list', 'summary': 'Add, list and mark books.', 'stack': ['python'],
        'requirements': [{'id': 'R1', 'text': 'Books can be added and listed', 'kind': 'functional'}],
        'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'VERSION reaches 4'}]}
ROLE = {_ARCHITECT_SYSTEM: 'architect', _GENERATOR_SYSTEM: 'generator', _REPAIR_SYSTEM: 'repair'}


def model_answer(role: str, user: str) -> dict:
    """From the request alone. Repair: VERSION n -> n+1, with two detours that exercise the loop's memory: at 1 the first
    answer breaks the build (discarded, then told so) and at 2 the first answer goes back to 1 (a cycle, then a second
    chance)."""
    if role == 'architect':
        return SPEC
    if role == 'generator':
        return {'files': [{'path': 'app.py', 'content': 'VERSION = 0\n'}]}
    payload = json.loads(user)
    ids = {f.get('acceptance_id') for f in payload['failures']}
    n = next(int(m.group(1)) for f in payload['failures'] for m in [re.search(r'VERSION is (\d+)', f['message'])] if m)
    if n == 1 and 'REPAIR_REGRESSION' not in ids:
        return {'files': [{'path': 'app.py', 'content': 'VERSION = broken\n'}]}
    if n == 2 and 'NO_PROGRESS' not in ids:
        return {'files': [{'path': 'app.py', 'content': 'VERSION = 1\n'}]}
    return {'files': [{'path': 'app.py', 'content': f'VERSION = {n + 1}\n'}]}


class Model:
    """The HTTP answer of an OpenAI-compatible endpoint (urlopen of OpenAICompatibleGateway). `calls`: every request, by
    role -- the calls on the real gateway seam."""

    def __init__(self):
        self.calls = []

    def urlopen(self, req, timeout):
        body = json.loads(req.data.decode('utf-8'))
        system, user = body['messages'][0]['content'], body['messages'][1]['content']
        role = ROLE.get(system, 'other')
        self.calls.append(role)
        text = json.dumps(model_answer(role, user))
        payload = {'id': 'r', 'model': 'scripted', 'choices': [{'message': {'content': text}, 'finish_reason': 'stop'}],
                   'usage': {'prompt_tokens': 10, 'completion_tokens': 10}}

        class Resp(io.BytesIO):
            headers = {}
        return Resp(json.dumps(payload).encode('utf-8'))

    def count(self):
        return {r: self.calls.count(r) for r in sorted(set(self.calls))}


class Checks:
    """A pure function of the repository: VERSION must reach 4; 'broken' fails the build itself (ranked worse)."""

    def execute(self, *, repository, spec):
        text = repository.get('app.py', '')
        if 'broken' in text:
            return ExecutionReport(False, (AcceptanceFailure('A1', 'build failed: app.py does not run', 'broken'),))
        n = int(re.search(r'VERSION = (\d+)', text).group(1))
        if n >= 4:
            return ExecutionReport(True, (), f'v{n} ok', 1)
        return ExecutionReport(False, (AcceptanceFailure('A1', f'VERSION is {n}; needs 4', f'app.py v{n}'),),
                               f'v{n}', 1)


def engine(model: Model, hook=None):
    catalog = CatalogModel(endpoint=ModelEndpoint(name='scripted', base_url='http://127.0.0.1:9/v1', model='scripted',
                                                  api_key='test-fixture-only', external=True),
                           option=ModelOption('p', 'scripted', 90, 100, Decimal('1'), Decimal('2')),
                           max_output_tokens=65536, api_key_env='K')
    gateway = RoutedModelGateway(ranked=(catalog,), routing_policy=RoutingPolicy(minimum_quality=0),
                                 policy=ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                                                       external_budget_usd=Decimal('5'), max_external_calls_per_build=60),
                                 gateway_factory=lambda ep: OpenAICompatibleGateway(ep, urlopen=model.urlopen),
                                 transient_retries=0, sleep=lambda s: None)
    e = AutonomousProductEngine(architect=ArchitectAgent(TaskTaggedGateway(gateway, 'architecture')),
                                generator=GeneratorAgent(TaskTaggedGateway(gateway, 'codegen')),
                                repairer=RepairAgent(TaskTaggedGateway(gateway, 'repair')), executor=Checks(),
                                max_repair_rounds=6, repair_ceiling=6)
    e.no_progress_retries = 1                             # as production (_live_components)
    e.checkpoint_hook = hook
    return e, gateway


def outcome(result, e) -> dict:
    return {'status': result.status, 'repository': result.repository, 'rounds': result.repair_rounds,
            'stop_reason': result.stop_reason, 'report': report_to_dict(result.report),
            'taxonomy': e.failure_taxonomy, 'first_pass': e.first_pass, 'trace': e.trace,
            'test_edits': e.test_edits.evidence()}


def stored(stage: str, payload: dict) -> ResumePoint:
    """A checkpoint as it comes back from storage: JSON in, JSON out (proves the state is JSON-only)."""
    from omni_prod.product_spec import ProductSpec
    spec = ProductSpec.from_dict(json.loads(C.canonical(payload['spec'].to_dict())))
    if stage == 'spec':
        return ResumePoint('spec', spec)
    loop = json.loads(C.canonical(payload['loop']))
    return ResumePoint(stage, spec, int(loop['rounds']), json.loads(C.canonical(payload['repository'])), loop)


class EngineContinuesFromEveryCheckpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = Model()
        cls.checkpoints = []
        e, _ = engine(cls.model, hook=lambda stage, payload: cls.checkpoints.append((stage, payload)))
        cls.uninterrupted = outcome(e.build('a reading list'), e)

    def test_the_uninterrupted_build_writes_a_checkpoint_after_the_spec_round_0_every_round_and_the_loop(self):
        self.assertEqual(self.model.count(), {'architect': 1, 'generator': 1, 'repair': 6})
        self.assertEqual([(s, (p.get('loop') or {}).get('rounds')) for s, p in self.checkpoints],
                         [('spec', None), ('round', 0), ('round', 1), ('round', 2), ('round', 3), ('round', 4),
                          ('round', 5), ('finished', 6)])
        self.assertEqual(self.uninterrupted['status'], 'ready')
        self.assertEqual(self.uninterrupted['rounds'], 6)
        # the detours happened, so the carried memory is what decides the later rounds
        self.assertTrue(any('discarded' in t for t in self.uninterrupted['trace']))
        self.assertTrue(any('second_chance' in t for t in self.uninterrupted['trace']))

    def test_each_checkpoint_continues_to_the_same_result_without_calling_a_covered_stage_again(self):
        for index, (stage, payload) in enumerate(self.checkpoints):
            with self.subTest(checkpoint=index, stage=stage, round=(payload.get('loop') or {}).get('rounds')):
                model = Model()
                e, gateway = engine(model)
                result = e.build('a reading list', resume=stored(stage, payload))
                self.assertEqual(outcome(result, e), self.uninterrupted)
                tasks = [r.task_type for r in gateway.recorder.records if r.kind == 'provider_call']
                self.assertNotIn('architecture', tasks)                   # the spec is in every checkpoint
                if stage != 'spec':
                    self.assertNotIn('codegen', tasks)                    # the code from round 0 on
                done = (payload.get('loop') or {}).get('rounds') or 0
                self.assertEqual(model.count().get('repair', 0), 0 if stage == 'finished' else 6 - done)
                self.assertEqual(e.resumed_from, {'stage': stage, 'round': None if stage == 'spec' else done})

    def test_the_round_budget_is_the_builds_not_a_new_one(self):
        stage, payload = self.checkpoints[3]                              # after repair round 2
        loop = dict(json.loads(C.canonical(payload['loop'])), max_repair_rounds=3)
        e, _ = engine(Model())
        result = e.build('a reading list', resume=ResumePoint('round', stored(stage, payload).spec, 2,
                                                              payload['repository'], loop))
        self.assertEqual((result.status, result.repair_rounds, result.stop_reason), ('failed', 3, 'max_repair_rounds'))

    def test_an_unknown_stage_or_a_partial_resume_point_raises(self):
        spec = stored(*self.checkpoints[0]).spec
        with self.assertRaises(ValueError):
            ResumePoint('half', spec)
        with self.assertRaises(ValueError):
            ResumePoint('round', spec, 1)
        with self.assertRaises(ValueError):
            ResumePoint('round', spec, 1, {'app.py': ''}, {'version': 99})


class MemoryStore:
    def __init__(self):
        self.objects = {}

    def put_bytes(self, key, data):
        self.objects[key] = bytes(data)

    def get_bytes(self, key):
        return self.objects[key]


def unzip(data: bytes) -> dict:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        return {n: zf.read(n).decode('utf-8') for n in zf.namelist()}


def zip_repo(repo: dict) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as zf:
        for k, v in repo.items():
            zf.writestr(k, v)
    return out.getvalue()


class Writer(C.CheckpointWriter):
    """The real writer without the database: the record is kept, the ledger query answers nothing."""

    def __init__(self, store, engine_):
        super().__init__(pool=None, build_id='bld_unit', epoch=0, store=store, zip_repo=zip_repo,
                         contract_fingerprint='cfp', prompt='a reading list', engine=engine_, round_snapshots=[])
        self.records = []

    def __call__(self, stage, payload):
        rec = self.record(stage, payload)
        self.records.append(rec)
        self.last = rec


class CheckpointIsTrustedOnlyByItsBytes(unittest.TestCase):
    def setUp(self):
        from unittest import mock
        patcher = mock.patch.object(C, 'completed_paid_calls', return_value={'count': 0, 'calls': []})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.store = MemoryStore()
        e, _ = engine(Model())
        self.writer = Writer(self.store, e)
        e.checkpoint_hook = self.writer
        self.result = e.build('a reading list')
        self.round2 = next(r for r in self.writer.records if r['stage'] == 'round' and r['round'] == 2)

    def load(self, record, **kw):
        args = dict(store=self.store, unzip=unzip, contract_fingerprint='cfp', prompt='a reading list',
                    build_id='bld_unit')
        args.update(kw)
        return C.load(record, **args)

    def test_every_record_is_usable_and_loads_its_round(self):
        for record in self.writer.records:
            self.assertEqual(C.usable(record), (True, ''), record['stage'])
        loaded = self.load(self.round2)
        self.assertEqual(loaded.resume.round, 2)
        self.assertEqual(_checksum(loaded.resume.repository), self.round2['snapshot']['sha256'])
        self.assertEqual(loaded.resumed_from()['checkpoint'], 'round 2')
        self.assertEqual(C.label(self.writer.records[0]), 'spec')
        self.assertEqual(C.label(self.writer.records[-1]), 'finished after round 6')

    def test_a_changed_byte_in_any_stored_object_is_refused(self):
        for part in ('spec', 'snapshot', 'state'):
            with self.subTest(part):
                key = self.round2[part]['key']
                good = self.store.objects[key]
                self.store.objects[key] = good[:-1] + bytes([good[-1] ^ 1])
                try:
                    with self.assertRaises(C.CheckpointUnusable) as ctx:
                        self.load(self.round2)
                    self.assertIn('sha256', str(ctx.exception))
                finally:
                    self.store.objects[key] = good

    def test_a_repository_whose_content_differs_from_the_recorded_checksum_is_refused(self):
        key = self.round2['snapshot']['key']
        forged = zip_repo({'app.py': 'VERSION = 9\n'})
        self.store.objects[key] = forged
        record = dict(self.round2, snapshot=dict(self.round2['snapshot'], zip_sha256=C.sha256_hex(forged)))
        with self.assertRaises(C.CheckpointUnusable) as ctx:
            self.load(record)
        self.assertIn('checksum', str(ctx.exception))

    def test_another_prompt_or_contract_or_a_missing_object_is_refused(self):
        for kw, word in (({'prompt': 'another request'}, 'prompt'), ({'contract_fingerprint': 'other'}, 'contract')):
            with self.subTest(word):
                with self.assertRaises(C.CheckpointUnusable) as ctx:
                    self.load(self.round2, **kw)
                self.assertIn(word, str(ctx.exception))
        del self.store.objects[self.round2['state']['key']]
        with self.assertRaises(C.CheckpointUnusable):
            self.load(self.round2)

    def test_a_key_outside_this_builds_prefix_is_refused(self):
        keys = ('build-checkpoints/bld_other/x.json', 'build-checkpoints/bld_unitx/x.json',
                'build-checkpoints/bld_unit/../bld_other/x.json', 'build-checkpoints/bld_unit/./x.json',
                'build-checkpoints/bld_unit//x.json', 'build-checkpoints/bld_unit/..\\x')
        for part in ('spec', 'snapshot', 'state'):
            for key in keys:
                with self.subTest(part=part, key=key):
                    record = {**self.round2, part: {**self.round2[part], 'key': key}}
                    with self.assertRaises(C.CheckpointUnusable) as ctx:
                        self.load(record)
                    self.assertIn('not under build-checkpoints/bld_unit/', str(ctx.exception))

    def test_usable_names_why_not(self):
        cases = ((None, 'no checkpoint'), ({**self.round2, 'version': 2}, 'version'),
                 ({**self.round2, 'resumable': False, 'why_not': 'content route'}, 'content route'),
                 ({**self.round2, 'stage': 'half'}, 'unknown checkpoint stage'),
                 ({**self.round2, 'snapshot': {'key': 'k'}}, 'snapshot'), ({**self.round2, 'round': None}, 'round'))
        for record, word in cases:
            ok, why = C.usable(record)
            self.assertFalse(ok)
            self.assertIn(word, why)

    def test_only_the_janitors_resume_decision_for_this_attempt_continues(self):
        resume = {'decision': 'resume', 'recovery_attempt': 1}
        self.assertIsNone(C.resume_record({'epoch': 1, 'checkpoint': self.round2, 'recovery': None}))
        self.assertIsNone(C.resume_record({'epoch': 1, 'checkpoint': self.round2,
                                           'recovery': {'decision': 'restart', 'recovery_attempt': 1}}))
        self.assertIs(C.resume_record({'epoch': 1, 'checkpoint': self.round2, 'recovery': resume}), self.round2)
        for claim in ({'epoch': 2, 'checkpoint': self.round2, 'recovery': resume},
                      {'epoch': 1, 'checkpoint': None, 'recovery': resume}):
            with self.assertRaises(C.CheckpointUnusable):
                C.resume_record(claim)


class TheVerificationHistoryIsCarried(unittest.TestCase):
    def chain(self):
        from omni_prod.behavior_acceptance import BehaviorAcceptanceExecutor
        from omni_prod.design_review import DesignCritic
        from omni_prod.product_review import ProductReviewExecutor
        from omni_prod.visual_qa import VisualQAExecutor
        visual = VisualQAExecutor.__new__(VisualQAExecutor)
        visual.__dict__.update(_inner=BehaviorAcceptanceExecutor.__new__(BehaviorAcceptanceExecutor), visual_rounds=[],
                               design_critic=DesignCritic(None))
        visual._inner.__dict__.update(_inner=None, history=[])
        review = ProductReviewExecutor(visual)
        return SimpleNamespace(executor=review), review, visual

    def test_the_review_and_the_design_critic_continue_with_their_history(self):
        e1, review, visual = self.chain()
        review.reviews = [{'round': 1, 'enforced': True, 'alongside': False, 'blocking': 1, 'findings': [
            {'skill': 's', 'severity': 'blocking', 'source': 'reviewer', 'file': 'a.py', 'problem': 'p', 'fix': 'f'}]}]
        review.gate_waste_rounds, review.gate_waste_usd, review._spend_at_review = 2, Decimal('0.0123'), [(Decimal('0.5'), 3)]
        visual.design_critic.polish_rounds_used, visual.design_critic.reviews = 1, [{'round': 1, 'status': 'REVIEWED'}]
        visual.visual_rounds, visual._inner.history = [{'status': 'PASS'}], [{'status': 'FAIL'}]
        saved = json.loads(C.canonical(C.capture_executors(e1)))
        e2, review2, visual2 = self.chain()
        self.assertEqual(C.restore_executors(e2, saved), [])
        self.assertEqual(review2.reviews, review.reviews)
        self.assertEqual((review2.gate_waste_rounds, review2.gate_waste_usd, review2._spend_at_review),
                         (2, Decimal('0.0123'), [(Decimal('0.5'), 3)]))
        self.assertEqual(review2._previous_blocking(), review._previous_blocking())
        self.assertEqual(visual2.design_critic.polish_rounds_used, 1)      # the one polish round is not given again
        self.assertEqual((visual2.visual_rounds, visual2._inner.history), ([{'status': 'PASS'}], [{'status': 'FAIL'}]))

    def test_a_chain_without_the_executor_says_so(self):
        e1, review, _ = self.chain()
        saved = C.capture_executors(e1)
        self.assertEqual(C.restore_executors(SimpleNamespace(executor=None), saved),
                         sorted(saved, key=list(saved).index))


class TheImageCheckIsReplayed(unittest.TestCase):
    """S4 (re-review of 73ed4b7): a verdict is replayed only for the same subject AND the same image bytes; any other
    image is asked of the real model (fail closed), never given the old verdict."""
    BAKERY, OTHER = b'the bakery picture the lost worker checked', b'a different picture, never shown to a model'

    def verdicts(self):
        import hashlib
        return ([{'requirement_id': 'r1', 'sha256': 'artifact', 'subject': 'a bakery', 'status': 'MATCH',
                  'shows': 'bread', 'reason': 'ok'},
                 {'requirement_id': 'hero', 'subject': '', 'status': 'DROPPED', 'reason': 'no subject recorded'}],
                [{'subject': 'a bakery', 'sha256': hashlib.sha256(self.BAKERY).hexdigest()}])

    def model(self):
        model = SimpleNamespace(calls=[])
        model.complete_json = lambda **kw: model.calls.append(kw['images'][0]) or {'matches': False, 'shows': 'a pie',
                                                                                   'reason': 'not bread'}
        return model

    def test_the_same_bytes_are_replayed_with_no_model_call(self):
        from omni_prod.image_match import verify
        verdicts, questions = self.verdicts()
        model = self.model()
        replay = C.ReplayVision(verdicts, questions, fallback=model)
        out = verify(replay, [SimpleNamespace(requirement_id='r1', sha256='artifact', data=self.BAKERY)], {'r1': 'a bakery'})
        self.assertEqual((out[0]['status'], replay.replayed, model.calls), ('MATCH', 1, []))

    def test_other_bytes_under_the_same_subject_are_asked_of_the_model(self):
        from omni_prod.image_match import ImageDoesNotMatch, verify
        verdicts, questions = self.verdicts()
        model = self.model()
        replay = C.ReplayVision(verdicts, questions, fallback=model)
        with self.assertRaises(ImageDoesNotMatch):                 # the real model saw a pie: the check fails closed
            verify(replay, [SimpleNamespace(requirement_id='r1', sha256='artifact', data=self.OTHER)], {'r1': 'a bakery'})
        self.assertEqual((replay.replayed, replay.asked_again, model.calls), (0, 1, [self.OTHER]))
        with self.assertRaises(ValueError):                        # and with no model behind it, it raises
            C.ReplayVision(verdicts, questions).complete_json(user='{"customer_asked_to_see": "a bakery"}',
                                                              images=(self.OTHER,))

    def test_a_first_run_records_each_question_with_its_bytes(self):
        import hashlib
        engine = SimpleNamespace()
        vision = C.vision_for(engine, self.model(), None)
        vision.complete_json(user='{"customer_asked_to_see": "a bakery"}', images=(self.BAKERY,), task='review')
        self.assertEqual(engine.image_questions, [{'subject': 'a bakery',
                                                   'sha256': hashlib.sha256(self.BAKERY).hexdigest()}])


class TheSameBudgets(unittest.TestCase):
    def test_the_earlier_workers_recorded_calls_and_cost_count_against_the_build_budget(self):
        from omni_prod.model_policy import ModelPolicyViolation, authorize_model_call
        _, gateway = engine(Model())
        gateway.state.external_calls, gateway.state.external_spend_usd = 1, Decimal('0.01')
        version = gateway.policy_version
        out = C.carry_budget(gateway, {'external_calls': 3, 'metered_usd': Decimal('0.004'),
                                       'unanswered_authorized_usd': Decimal('0.11')})
        self.assertEqual(out, {'carried': True, 'external_calls': 3, 'metered_usd': '0.004',
                               'unanswered_authorized_usd': '0.11', 'budget_left_usd': '4.886', 'calls_left': 57})
        self.assertEqual((gateway.policy.external_budget_usd, gateway.policy.max_external_calls_per_build),
                         (Decimal('4.886'), 57))
        self.assertNotEqual(gateway.policy_version, version)
        # this worker's own spend is untouched: the settlement adds the earlier workers from the ledger itself
        self.assertEqual((gateway.state.external_calls, gateway.state.external_spend_usd), (1, Decimal('0.01')))
        endpoint = ModelEndpoint(name='x', base_url='http://127.0.0.1:9/v1', model='x', api_key='k', external=True)
        with self.assertRaises(ModelPolicyViolation):     # 0.01 spent + 4.88 > 4.886 left of the build's 5
            authorize_model_call(endpoint=endpoint, policy=gateway.policy, state=gateway.state,
                                 estimated_cost_usd=Decimal('4.88'))


class TheTerminalEvidenceCarriesTheRecord(unittest.TestCase):
    def test_carried_keys_join_a_terminal_transition_and_never_replace_the_runs_own(self):
        from omni_prod.models import BuildStatus
        seen = []
        jobs = SimpleNamespace(transition=lambda **kw: seen.append(kw) or True, other=lambda: 'through')
        carry = C.CarryEvidence(jobs, lambda: {'recovery': {'decision': 'resume'}, 'checkpoint': {'stage': 'finished'},
                                               'checkpoint_errors': None})
        carry.transition(build_id='b', expected=BuildStatus.QUEUED, target=BuildStatus.RUNNING)
        carry.transition(build_id='b', expected=BuildStatus.RUNNING, target=BuildStatus.READY,
                         evidence_json={'billing': 'settled', 'checkpoint': 'own'})
        self.assertNotIn('evidence_json', seen[0])
        self.assertEqual(seen[1]['evidence_json'], {'billing': 'settled', 'checkpoint': 'own',
                                                    'recovery': {'decision': 'resume'}})
        self.assertEqual(carry.other(), 'through')


class TheCustomerReadsThatItContinued(unittest.TestCase):
    def ui(self, lang: str) -> dict:
        source = (ROOT / 'omni_prod' / 'assets' / 'app.js').read_text(encoding='utf-8')
        js = source[source.index('const T ='):source.index('const S =')] + \
            f'\nconsole.log(JSON.stringify({{r: T[{json.dumps(lang)}].logResumed, s: T[{json.dumps(lang)}].logRestarted,' \
            f' c: T[{json.dumps(lang)}].errCodes.checkpoint_unusable}}));'
        return json.loads(subprocess.run(['node', '-e', js], capture_output=True, text=True, check=True).stdout)

    def test_the_janitors_lines_are_the_screens_lines_in_hebrew_arabic_and_english(self):
        from omni_prod.maintenance import RECOVERY_LINES
        for lang in ('he', 'en', 'ar'):
            with self.subTest(lang):
                ui = self.ui(lang)
                self.assertEqual(ui['r'], RECOVERY_LINES['resumed'][lang])
                self.assertEqual(ui['s'], RECOVERY_LINES['restarted'][lang])
                self.assertTrue(ui['c'])
        self.assertIn('בלי להתחיל מחדש', RECOVERY_LINES['resumed']['he'])
        self.assertIn('without starting over', RECOVERY_LINES['resumed']['en'])
        self.assertIn('دون البدء من جديد', RECOVERY_LINES['resumed']['ar'])

    def test_the_build_log_shows_a_janitor_line_in_the_customers_language(self):
        source = (ROOT / 'omni_prod' / 'assets' / 'app.js').read_text(encoding='utf-8')
        self.assertIn("serverLine(e.message)", source)
        self.assertRegex(source, r"SERVER_LOG_LINES = \['logResumed', 'logRestarted'\]")


if __name__ == '__main__':
    unittest.main()
