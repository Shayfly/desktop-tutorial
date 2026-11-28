"""Warehouse 124: a customer's screenshot round, reserved and recorded, on REAL PostgreSQL.

Real migrations, the real ReservationService, the real execute_reservation (claim -> EXECUTING -> one call -> meter -> settle),
the real RoutedModelGateway, the real attachment table and the real conversation store. The only doubles: the provider's HTTP
transport behind the gateway (it records what it was given and answers an edit block) and the object store's bytes (a dict).
No paid call. Skipped, reported, without PostgreSQL (M4D2_DATABASE_URL).

Proved: the image reaches the model reduced, with the window width and the build id; the round is reserved under its own scope,
so the conversation's turn counter and cost cap never move (acceptance 4, rule 3); a round is stored whole whatever happens to
the call; a model with no evidence that it reads images is never priced; the reservation is the call."""
from __future__ import annotations

import copy as _copy
import hashlib
import json
import os
import unittest
import uuid
from decimal import Decimal
from pathlib import Path
from unittest import mock

from omni_prod import attachments as A
from omni_prod import shot_fix as SF
from omni_prod.intake import budget as B
from omni_prod.intake import reservation_worker as RW
from tests.shot_fix_support import FIX_ANSWER, WORK, png

ROOT = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv('M4D2_DATABASE_URL', '').strip()
ENV = {'OMNI_INTAKE_MODEL': '1', 'OMNI_INTAKE_VIA_WORKER': '1', 'OMNI_ZERO_COST_MODE': '0', 'OMNI_ALLOW_EXTERNAL_FALLBACK': '1',
       'OMNI_INTAKE_MODEL_BUDGET_USD': '0.15', 'OMNI_INTAKE_DAILY_BUDGET_USD': '5', 'GEMINI_API_KEY': 'test-only-not-a-key',
       'OMNI_SHOT_FIX': 'on', 'OMNI_SHOT_FIX_PROJECT_USD': '1.00'}


class Transport:
    """The provider's HTTP client, behind the REAL gateway: answers `doc` and reports its usage; keeps what it was asked."""
    calls: list = []

    def __init__(self, doc=None):
        self.doc, self.last_usage, self.last_response_model = FIX_ANSWER if doc is None else doc, None, None

    def complete_json(self, **kw):
        from omni_prod.provider_usage import ProviderUsage
        Transport.calls.append(kw)
        self.last_usage = ProviderUsage(provider='gemini', model='gemini-3.1-flash-lite', external=True,
                                        request_id=f'req-{uuid.uuid4().hex[:8]}', request_id_source='header', response_id=None,
                                        input_tokens=2400, output_tokens=300, cached_tokens=0, provider_reported_cost_usd=None,
                                        usage_reported=True)
        return _copy.deepcopy(self.doc)


def gateway_with(transport):
    from omni_prod.model_catalog import parse_model_catalog
    from omni_prod.model_policy import ModelUsePolicy
    from omni_prod.model_router import RoutingPolicy
    from omni_prod.routed_gateway import RoutedModelGateway
    raw = (ROOT / 'infra' / 'worker-host' / 'model-catalog.json').read_text()

    def factory(quoted, models):
        cat = parse_model_catalog(raw, {'GEMINI_API_KEY': 'test-only-not-a-key'})
        ranked = tuple(m for m in cat if m.option.model in models)
        return RoutedModelGateway(ranked=ranked, routing_policy=RoutingPolicy(minimum_quality=70),
                                  policy=ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                                                        external_budget_usd=quoted, max_external_calls_per_build=1),
                                  transient_retries=0, gateway_factory=lambda endpoint: transport, sleep=lambda s: None)
    return factory


class Objects:
    """The object store's bytes in a dict (the SQL rows are real)."""

    def __init__(self):
        self.data = {}

    def put_bytes(self, key, data):
        self.data[key] = data
        return mock.Mock(sha256=hashlib.sha256(data).hexdigest())

    def get_bytes(self, key):
        return self.data[key]


class PG(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DATABASE_URL:
            raise unittest.SkipTest('BLOCKED: M4D2_DATABASE_URL (real PostgreSQL) not configured')
        try:
            import psycopg
            cls.admin = psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=5)
        except Exception as exc:
            raise unittest.SkipTest(f'BLOCKED: PostgreSQL unreachable ({type(exc).__name__})')
        from omni_prod.db import DatabasePool
        from omni_prod.migration_runner import apply_migrations
        from omni_prod.migrations import discover_migrations
        cls.dbname = f'sf_{uuid.uuid4().hex[:10]}'
        cls.admin.execute(f'CREATE DATABASE {cls.dbname}')
        cls.url = DATABASE_URL.rsplit('/', 1)[0] + '/' + cls.dbname
        with psycopg.connect(cls.url) as conn:
            apply_migrations(conn, discover_migrations(ROOT / 'infra' / 'postgres'))
        cls.pool = DatabasePool(cls.url, max_size=20, timeout_seconds=30)
        cls.svc = B.ReservationService(cls.pool)

    @classmethod
    def tearDownClass(cls):
        cls.pool.close()
        cls.admin.execute(f'DROP DATABASE IF EXISTS {cls.dbname} WITH (FORCE)')
        cls.admin.close()

    def setUp(self):
        patcher = mock.patch.dict(os.environ, ENV)
        patcher.start()
        self.addCleanup(patcher.stop)
        from omni_prod.conversation.store import PostgresConversationStore
        self.account, self.project = f'usr_{uuid.uuid4().hex[:8]}', f'prj_{uuid.uuid4().hex[:8]}'
        self.objects, self.transport = Objects(), Transport()
        Transport.calls = []
        self.repo = A.AttachmentRepository(self.pool, self.objects)
        self.store = PostgresConversationStore(self.pool)
        self.turn_caps = B.Caps(project_usd=Decimal('0.15'), daily_usd=Decimal('5'), project_turns=8)

    def sql(self, q, args=()):
        with self.pool.connection() as conn:
            with conn.transaction():
                cur = conn.execute(q, args)
                return cur.fetchall() if cur.description else None

    def enqueue(self, reservation_id):
        """The worker, run at once: claim -> one call through the real gateway -> meter -> settle."""
        RW.execute_reservation(self.pool, reservation_id, gateway_factory=gateway_with(self.transport))

    def reader(self, key, *, purpose_scope_cap='1.00', service=None):
        caps = B.Caps(project_usd=Decimal(purpose_scope_cap), daily_usd=Decimal('5'), project_turns=None)
        return SF.ReservedShotReader(service or self.svc, self.enqueue, account_id=self.account, project_id=self.project,
                                     request_key=key, caps=caps, wait_seconds=5)

    def round(self, key, *, data=None, width=390, reader=None):
        return SF.round_of(project_id=self.project, account_id=self.account, build_id='bld_abc123', version_id='ver_1',
                           work=dict(WORK), data=data or png(3000, 1800), width=width, note='', lang='he', repo=self.repo,
                           reader=reader or self.reader(key), store=self.store, request_key=key)

    def turns(self):
        return self.svc.conversation_usage(f'project:{self.account}:{self.project}')['turns']

    # ------------------------------------------------------------------------------------------------------------
    def test_the_image_reaches_the_model_reduced_with_the_width_and_the_build_id(self):
        data = png(3000, 1800)
        record = self.round('k-one', data=data, width=430)
        self.assertEqual(record['outcome'], 'fix_ready', record['evidence'])
        self.assertEqual(len(Transport.calls), 1)                                        # one call: the reservation IS the call
        call = Transport.calls[0]
        self.assertEqual(len(call['images']), 1)
        self.assertEqual(A.validate_image(call['images'][0])[1:], (1400, 840))           # reduced: the long side is 1,400
        self.assertEqual(hashlib.sha256(call['images'][0]).hexdigest(), record['reduced']['sha256'])
        said = json.loads(call['user'])
        self.assertEqual((said['viewport_width'], said['build_id'], said['version_id']), (430, 'bld_abc123', 'ver_1'))
        self.assertEqual(sorted(said['files']), ['app.js', 'index.html', 'style.css'])
        # the originals are stored as they came, in the real attachment table, and the reduced copy beside them
        row = self.repo.get(project_id=self.project, account_id=self.account, attachment_id=record['original']['attachment_id'])
        self.assertEqual(self.repo.read(row), data)
        red = self.repo.get(project_id=self.project, account_id=self.account, attachment_id=record['reduced']['attachment_id'])
        self.assertEqual(self.repo.read(red), call['images'][0])

    def test_the_round_is_reserved_under_its_own_scope_and_the_line_names_the_reservation(self):
        record = self.round('k-scope')
        rid = next(line for line in record['evidence'] if line['stage'] == 'model_call')['reservation_id']
        scopes = [r[0] for r in self.sql('SELECT scope FROM intake_reservation_scopes WHERE reservation_id = %s', (rid,))]
        self.assertIn(f'shot-fix:{self.account}:{self.project}', scopes)
        self.assertNotIn(f'project:{self.account}:{self.project}', scopes)
        state, task, quote = self.sql('SELECT state, quote->>\'task\', quote FROM intake_reservations WHERE id = %s', (rid,))[0]
        self.assertEqual((state, task), ('SETTLED', 'screenshot_fix'))
        self.assertNotIn('turn_cap', quote)                                              # an image round holds no turn

    def test_three_image_rounds_leave_the_conversations_turn_counter_where_it_was(self):
        before = self.turns()
        for i, width in enumerate((390, 430, 1280)):
            record = self.round(f'k-turn-{i}', data=png(2000 + i, 1500), width=width)
            self.assertEqual(record['outcome'], 'fix_ready')
        self.assertEqual(len(Transport.calls), 3)
        self.assertEqual((before, self.turns()), (0, 0))
        # and the conversation's own turns still count from zero, under the cap the owner removed the limit of (None = no cap):
        # here the cap is 8, to prove the counter itself
        quote = B.quote(system='s', user='u', max_tokens=200, task='conversation')
        r = self.svc.reserve(idempotency_key=f'conv-{self.project}', account_id=self.account, project_id=self.project, quote_=quote,
                             caps=self.turn_caps, payload={'system': 's', 'user': 'u', 'max_tokens': 200, 'task': 'conversation'})
        self.assertEqual(r.quote['turn_cap']['used_before'], 0)                          # three image rounds were not turns
        self.assertEqual(Decimal(r.quote['caps'][f'project:{self.account}:{self.project}']['counted_before']), 0)

    def test_image_rounds_never_spend_the_conversations_cost_cap(self):
        for i in range(3):
            self.round(f'k-cap-{i}', data=png(2100 + i, 1500))
        usage = self.svc.conversation_usage(f'project:{self.account}:{self.project}')
        self.assertEqual((usage['settled_usd'], usage['held_usd'], usage['turns']), ('0', '0', 0))
        shots = self.svc.conversation_usage(f'shot-fix:{self.account}:{self.project}')
        self.assertEqual(shots['turns'], 3)                                              # they are counted, in their own scope

    def test_a_spent_budget_is_said_in_words_and_the_images_are_still_kept(self):
        record = self.round('k-budget', reader=self.reader('k-budget', purpose_scope_cap='0.000001'))
        self.assertEqual(record['outcome'], 'busy')
        self.assertEqual(Transport.calls, [])                                            # nothing was sent
        self.assertEqual(len(self.repo.list(project_id=self.project, account_id=self.account)), 2)
        self.assertEqual([line['stage'] for line in record['evidence']], list(SF.STAGES))
        self.assertEqual(self.sql('SELECT count(*) FROM intake_reservations WHERE account_id = %s', (self.account,))[0][0], 0)

    def test_a_model_with_no_evidence_that_it_reads_images_is_never_priced(self):
        with mock.patch('omni_prod.vision_models.VISION_MODELS', {}):
            record = self.round('k-blind')
        self.assertEqual(record['outcome'], 'not_connected')
        self.assertEqual(Transport.calls, [])
        self.assertIn('no quote', next(line for line in record['evidence'] if line['stage'] == 'model_call')['detail'])

    def test_the_conversation_agents_venice_profile_is_never_the_quote_of_an_image(self):
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_PROVIDER': 'venice'}):
            quote = B.quote(system='s', user='u', max_tokens=200, task='screenshot_fix', images=1, routed_only=True)
        self.assertNotEqual(quote.envelope.get('provider'), 'venice')
        self.assertTrue(all(m['model'].startswith('gemini') or m['model'] for m in quote.envelope['models']))
        with self.assertRaises(B.QuoteUnavailable):
            B.quote(system='s', user='u', max_tokens=200, task='screenshot_fix', images=1)        # an image is routed-only

    def test_the_worker_refuses_images_on_a_task_that_was_not_quoted_for_them(self):
        quote = B.quote(system='s', user='u', max_tokens=200, task='conversation')
        r = self.svc.reserve(idempotency_key=f'bad-{self.project}', account_id=self.account, project_id=self.project, quote_=quote,
                             caps=B.Caps(project_usd=Decimal('0.15'), daily_usd=Decimal('5')),
                             payload={'system': 's', 'user': 'u', 'max_tokens': 200, 'task': 'conversation',
                                      'images_b64': ['aGk=']})
        out = RW.execute_reservation(self.pool, r.id, gateway_factory=gateway_with(self.transport))
        self.assertEqual(out['state'], B.RELEASED)
        self.assertEqual(Transport.calls, [])

    def test_a_retried_read_with_the_same_key_is_one_reservation_and_one_call(self):
        user = SF.user_message(build_id='bld_abc123', version_id='ver_1', width=390, lang='he', note='', files={'style.css': 'a{}'})
        image = SF.shrink(png(1600, 900)).data
        first = self.reader('k-same').read(system=SF.SYSTEM, user=user, image=image)
        again = self.reader('k-same').read(system=SF.SYSTEM, user=user, image=image)
        self.assertEqual(first, again)
        self.assertEqual(self.sql('SELECT count(*) FROM intake_reservations WHERE account_id = %s', (self.account,))[0][0], 1)
        self.assertEqual(len(Transport.calls), 1)


if __name__ == '__main__':
    unittest.main()
