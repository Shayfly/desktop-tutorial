"""S6.3 slice 2: the words of a direction sketch, reserved and recorded, on REAL PostgreSQL.

Real migrations (049 included), the real ReservationService, the real execute_reservation (claim -> EXECUTING -> one call
-> meter -> settle), the real content validator and the real store. The only double is the provider's HTTP transport, behind
the real RoutedModelGateway (as tests/test_intake_budget_pg.py does). No paid call. Skipped, reported, when PostgreSQL is
unavailable (M4D2_DATABASE_URL).

The owner's decision (2026-11-26): the first sketch in a project is on the company, at most $0.10; a failed call does not use
up the free sketch; a further sketch is never charged here (slice 5)."""
from __future__ import annotations

import copy as _copy
import os
import threading
import unittest
import uuid
from decimal import Decimal
from pathlib import Path
from unittest import mock

from omni_prod import direction_sketch as DS
from omni_prod import discovery as D
from omni_prod.direction_sketch import copy as C
from omni_prod.direction_sketch import store as S
from omni_prod.intake import budget as B
from omni_prod.intake import reservation_worker as RW

ROOT = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv('M4D2_DATABASE_URL', '').strip()
SALON = 'אני רוצה אתר תדמית למספרה שלי בחיפה, קוראים לה "סטודיו נועה". טלפון 04-5551234'
ENV = {'OMNI_DIRECTION_SKETCH': 'on', 'OMNI_SITE_LIBRARY': 'on', 'OMNI_INTAKE_MODEL': '1', 'OMNI_INTAKE_VIA_WORKER': '1',
       'OMNI_ZERO_COST_MODE': '0', 'OMNI_ALLOW_EXTERNAL_FALLBACK': '1', 'OMNI_INTAKE_MODEL_BUDGET_USD': '0.15',
       'OMNI_INTAKE_DAILY_BUDGET_USD': '5', 'GEMINI_API_KEY': 'test-only-not-a-key'}
GOOD = {'schema': '148ai.site_content/1', 'name': 'סטודיו נועה', 'tagline': 'מספרה בחיפה',
        'description': 'מספרה בחיפה, סטודיו נועה.',
        'sections': {'hero': {'title': 'תספורת שמתאימה לכם', 'lead': 'מספרה בחיפה, עם תור שנוח לכם.',
                              'cta': 'לקביעת תור'},
                     'services': {'title': 'מה אנחנו עושים', 'nav': 'שירותים',
                                  'items': [{'title': 'תספורת', 'desc': 'תספורת לנשים ולגברים.'},
                                            {'title': 'צבע', 'desc': 'צבע לשיער.'}]}}}


class Transport:
    """The provider's HTTP client, behind the REAL gateway: answers `doc`, reports its usage."""
    calls = 0
    lock = threading.Lock()

    def __init__(self, doc=None, *, mode='ok', input_tokens=900, output_tokens=300, reported=None):
        self.doc, self.mode = GOOD if doc is None else doc, mode
        self.input_tokens, self.output_tokens, self.reported = input_tokens, output_tokens, reported
        self.last_usage = None
        self.last_response_model = None

    def complete_json(self, **kw):
        with Transport.lock:
            Transport.calls += 1
        if self.mode == 'timeout':
            raise TimeoutError('read timed out')
        if self.mode == 'not_json':
            from omni_prod.model_gateway import ModelJSONRejected
            raise ModelJSONRejected('not JSON', raw='plain words', diagnostic={})
        from omni_prod.provider_usage import ProviderUsage
        self.last_usage = ProviderUsage(provider='gemini', model='gemini-3.1-flash-lite', external=True,
                                        request_id=f'req-{uuid.uuid4().hex[:8]}', request_id_source='header',
                                        response_id=None, input_tokens=self.input_tokens,
                                        output_tokens=self.output_tokens, cached_tokens=0,
                                        provider_reported_cost_usd=self.reported, usage_reported=True)
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
                                  transient_retries=0, gateway_factory=lambda endpoint: transport,
                                  sleep=lambda s: None)
    return factory


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
        cls.dbname = f'sk_{uuid.uuid4().hex[:10]}'
        cls.admin.execute(f'CREATE DATABASE {cls.dbname}')
        cls.url = DATABASE_URL.rsplit('/', 1)[0] + '/' + cls.dbname
        with psycopg.connect(cls.url) as conn:
            apply_migrations(conn, discover_migrations(ROOT / 'infra' / 'postgres'))
        cls.pool = DatabasePool(cls.url, max_size=30, timeout_seconds=30)
        cls.svc = B.ReservationService(cls.pool)
        cls.store = S.SketchStore(cls.pool)

    @classmethod
    def tearDownClass(cls):
        cls.pool.close()
        cls.admin.execute(f'DROP DATABASE IF EXISTS {cls.dbname} WITH (FORCE)')
        cls.admin.close()

    def setUp(self):
        patcher = mock.patch.dict(os.environ, ENV)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.queue: list[str] = []
        self.account, self.project = f'usr_{uuid.uuid4().hex[:8]}', f'prj_{uuid.uuid4().hex[:8]}'

    # -- helpers --------------------------------------------------------------------------------------------------
    def sql(self, q, args=()):
        with self.pool.connection() as conn:
            with conn.transaction():
                cur = conn.execute(q, args)
                return cur.fetchall() if cur.description else None

    def direction(self, text=SALON):
        r = DS.ready(D.start(text), account_id=self.account, has_version=False, has_open_build=False)
        self.assertTrue(r.ok, r.reason)
        return r.direction

    def sketch(self, direction=None, *, project=None, seq=0, account=None, tail=''):
        d = direction or self.direction()
        row, _ = self.store.create(project_id=project or self.project, account_id=account or self.account,
                                   brief_revision=1, brief_fingerprint='f' * 16,
                                   direction_fp=DS.direction_fp(d) + tail, copy_fp=DS.copy_fp(d), seq=seq,
                                   record=d.to_dict())
        return row, d

    def request(self, row, d, **kw):
        return C.request(self.store, self.svc, self.queue.append, row, d, **kw)

    def run_worker(self, transport=None, **kw):
        outs = [RW.execute_reservation(self.pool, rid, gateway_factory=gateway_with(transport or Transport()), **kw)
                for rid in self.queue]
        self.queue.clear()
        return outs

    def finalise(self, row, d):
        return C.finalise(self.store, self.svc, self.store.get(row.id, row.project_id, row.account_id), d)

    def free_scope(self, project=None, account=None):
        return f'sketch-free:{account or self.account}:{project or self.project}'

    def free_counted(self, project=None, account=None) -> Decimal:
        return self.svc.counted(self.free_scope(project, account))


class TheMigration(PG):
    def test_it_is_applied_and_its_down_file_removes_it(self):
        self.assertEqual(self.sql("SELECT to_regclass('public.direction_sketches') IS NOT NULL")[0][0], True)
        self.assertEqual(self.sql('SELECT count(*) FROM schema_migrations WHERE version = 49')[0][0], 1)
        import psycopg
        # on a throw-away database of its own: the down file, then the migration again (idempotent)
        name = f'skdown_{uuid.uuid4().hex[:8]}'
        self.admin.execute(f'CREATE DATABASE {name}')
        try:
            url = DATABASE_URL.rsplit('/', 1)[0] + '/' + name
            from omni_prod.migration_runner import apply_migrations
            from omni_prod.migrations import discover_migrations
            with psycopg.connect(url) as conn:
                apply_migrations(conn, discover_migrations(ROOT / 'infra' / 'postgres'))
            with psycopg.connect(url, autocommit=True) as conn:
                conn.execute((ROOT / 'infra' / 'postgres' / 'rollback' / '049_direction_sketches.down.sql').read_text())
                self.assertIsNone(conn.execute("SELECT to_regclass('public.direction_sketches')").fetchone()[0])
                self.assertEqual(conn.execute('SELECT count(*) FROM schema_migrations WHERE version = 49').fetchone()[0], 0)
                self.assertEqual(conn.execute('SELECT count(*) FROM schema_migrations WHERE version = 48').fetchone()[0], 1)
            with psycopg.connect(url) as conn:
                apply_migrations(conn, discover_migrations(ROOT / 'infra' / 'postgres'))
                self.assertEqual(conn.execute("SELECT to_regclass('public.direction_sketches') IS NOT NULL").fetchone()[0], True)
        finally:
            self.admin.execute(f'DROP DATABASE IF EXISTS {name} WITH (FORCE)')

    def test_a_database_without_the_table_fails_closed(self):
        import psycopg
        name = f'skmiss_{uuid.uuid4().hex[:8]}'
        self.admin.execute(f'CREATE DATABASE {name}')
        try:
            from omni_prod.db import DatabasePool
            pool = DatabasePool(DATABASE_URL.rsplit('/', 1)[0] + '/' + name, max_size=2, timeout_seconds=5)
            try:
                with self.assertRaises(S.SketchStoreMissing):
                    S.SketchStore(pool).get('skt_' + 'a' * 24, 'p', 'a')
            finally:
                pool.close()
        finally:
            self.admin.execute(f'DROP DATABASE IF EXISTS {name} WITH (FORCE)')


class TheFirstSketchIsOnTheCompany(PG):
    def test_its_call_is_reserved_on_the_free_scope_and_no_credit_is_touched(self):
        d = self.direction()
        row, _ = self.sketch(d)
        before = self.sql('SELECT count(*) FROM credit_reservations')[0][0]
        out = self.request(row, d)
        self.assertEqual((out['state'], out['reason']), ('pending', None), out)
        r = self.svc.get(out['reservation_id'])
        self.assertEqual((r.quote['task'], r.state, r.account_id, r.project_id), ('direction_sketch', B.RESERVED,
                                                                                self.account, self.project))
        scopes = {s for (s,) in self.sql('SELECT scope FROM intake_reservation_scopes WHERE reservation_id = %s', (r.id,))}
        self.assertEqual(scopes, {B.DAILY_SCOPE, self.free_scope()})
        self.assertNotIn(f'project:{self.account}:{self.project}', scopes)            # never the conversation's $0.15
        self.assertEqual(self.sql('SELECT count(*) FROM credit_reservations')[0][0], before)
        stored = self.store.get(row.id, self.project, self.account)
        self.assertEqual((stored.funding, stored.copy_state, stored.reservation_id), ('company_first', 'pending', r.id))
        self.assertEqual(stored.credits, 0)

    def test_a_written_sketch_has_its_words_and_its_three_timestamps(self):
        d = self.direction()
        row, _ = self.sketch(d)
        self.request(row, d)
        outs = self.run_worker()
        self.assertTrue(outs[0]['ok'], outs)
        done = self.finalise(row, d)
        self.assertEqual((done.copy_state, done.copy['sections']['hero']['title']), ('written', GOOD['sections']['hero']['title']))
        self.assertIsNotNone(done.offered_at)
        self.assertIsNotNone(done.copy_ready_at)
        stamps = self.sql('SELECT reserved_at, executing_at, settled_at FROM intake_reservations WHERE id = %s',
                          (done.reservation_id,))[0]
        self.assertTrue(all(stamps), stamps)
        spent = self.sql("SELECT COALESCE(SUM(actual_usd), 0) FROM intake_reservations WHERE id = %s", (done.reservation_id,))[0][0]
        self.assertGreater(Decimal(spent), 0)
        self.assertLessEqual(self.free_counted(), C.SKETCH_MAX_USD)
        # the p50 / p95 query of S5.2 runs on those rows
        got = self.sql("SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY extract(epoch FROM (copy_ready_at - offered_at))) "
                       "FROM direction_sketches WHERE copy_state = 'written'")
        self.assertIsNotNone(got[0][0])

    def test_finalise_is_idempotent_and_never_touches_the_brief_or_a_build(self):
        d = self.direction()
        row, _ = self.sketch(d)
        self.request(row, d)
        self.run_worker()
        once = self.finalise(row, d)
        twice = self.finalise(row, d)
        self.assertEqual((once.copy_state, twice.copy_state, once.copy_ready_at), ('written', 'written', twice.copy_ready_at))
        for table in ('build_jobs', 'build_approvals', 'credit_reservations'):
            self.assertEqual(self.sql(f'SELECT count(*) FROM {table}')[0][0], 0, table)

    def test_two_concurrent_claims_of_the_free_slot_exactly_one_wins(self):
        d = self.direction()
        rows = [self.sketch(d, seq=i)[0] for i in range(6)]
        barrier = threading.Barrier(len(rows))
        got = []

        def go(r):
            barrier.wait(timeout=20)
            got.append(self.store.claim(r.id, r.project_id, r.account_id, 'company_first'))
        threads = [threading.Thread(target=go, args=(r,)) for r in rows]
        [t.start() for t in threads]
        [t.join(30) for t in threads]
        self.assertEqual(sorted(got), sorted([S.FREE] + [S.BUSY] * (len(rows) - 1)), got)

    def test_a_second_sketch_after_a_written_free_one_is_not_free(self):
        d = self.direction()
        first, _ = self.sketch(d)
        self.request(first, d)
        self.run_worker()
        self.assertEqual(self.finalise(first, d).copy_state, 'written')
        second, _ = self.sketch(d, seq=1)
        out = self.request(second, d)
        self.assertEqual((out['state'], out['reason']), ('refused', 'free_sketch_used'), out)
        self.assertEqual(self.store.get(second.id, self.project, self.account).copy_state, 'none')
        self.assertEqual(self.sql('SELECT count(*) FROM intake_reservations WHERE account_id = %s', (self.account,))[0][0], 1)

    def test_another_project_has_its_own_free_sketch(self):
        d = self.direction()
        a, _ = self.sketch(d)
        b, _ = self.sketch(d, project=self.project + 'b')
        self.assertEqual(self.request(a, d)['state'], 'pending')
        self.assertEqual(self.request(b, d)['state'], 'pending')


class AFailedCallDoesNotUseUpTheFreeSketch(PG):
    def attempt(self, row, d, transport):
        out = self.request(row, d)
        self.assertEqual(out['state'], 'pending', out)
        self.run_worker(transport)
        return self.finalise(row, d)

    def test_not_json_a_timeout_and_a_blocked_document_free_the_slot(self):
        d = self.direction()
        row, _ = self.sketch(d)
        phone = _copy.deepcopy(GOOD)
        phone['sections']['hero']['lead'] = 'התקשרו אלינו: 04-9998877'
        for case, transport in (('not json', Transport(mode='not_json')), ('timeout', Transport(mode='timeout')),
                                ('a phone in the copy', Transport(phone))):
            with self.subTest(case=case):
                done = self.attempt(row, d, transport) if case != 'a phone in the copy' else None
                if done is None:
                    break
                self.assertEqual(done.copy_state, 'failed', done)
                self.assertIsNone(done.copy)
        # after the first failure the slot is free: another sketch of the project may take it
        other, _ = self.sketch(d, seq=1)
        self.assertEqual(self.store.claim(other.id, self.project, self.account, 'company_first'), S.FREE)

    def test_the_fourth_attempt_after_three_failures_is_refused(self):
        d = self.direction()
        row, _ = self.sketch(d)
        for n in range(C.FREE_ATTEMPTS):
            done = self.attempt(row, d, Transport(mode='not_json'))
            self.assertEqual(done.copy_state, 'failed', (n, done))
        out = self.request(self.store.get(row.id, self.project, self.account), d)
        self.assertEqual(out['state'], 'refused')
        self.assertTrue(out['reason'].startswith('free_attempts_used'), out)
        self.assertEqual(self.store.attempts(self.project, self.account), C.FREE_ATTEMPTS)
        self.assertLessEqual(self.free_counted(), C.SKETCH_MAX_USD)

    def test_a_blocked_document_is_not_stored_as_copy(self):
        d = self.direction()
        for label, mutate in (('a phone', lambda g: g['sections']['hero'].__setitem__('lead', 'התקשרו 04-9998877')),
                              ('an invented number', lambda g: g['sections']['hero'].__setitem__('lead', 'כבר 1,500 לקוחות מרוצים')),
                              ('a section not asked for', lambda g: g['sections'].__setitem__('faq', {'title': 'x', 'items': []}))):
            with self.subTest(label):
                project = f'prj_{uuid.uuid4().hex[:8]}'
                doc = _copy.deepcopy(GOOD)
                mutate(doc)
                row, _ = self.sketch(d, project=project)
                self.assertEqual(self.request(row, d)['state'], 'pending')
                self.run_worker(Transport(doc))
                done = self.finalise(row, d)
                self.assertEqual((done.copy_state, done.copy), ('failed', None), done)
                self.assertTrue(done.copy_reason.startswith('not shown'), done.copy_reason)


class TheCap(PG):
    def test_a_quote_above_the_cap_reserves_nothing(self):
        d = self.direction()
        row, _ = self.sketch(d)
        real = B.quote(system='s', user='u', max_tokens=C.MAX_TOKENS, task=C.TASK)
        dear = B.Quote(C.SKETCH_MAX_USD + Decimal('0.00000001'), real.envelope)     # one hundred-millionth over the cap
        with mock.patch.object(B, 'quote', return_value=dear):
            out = self.request(row, d)
        self.assertEqual((out['state'], out['reason']), ('refused', 'sketch_over_cap'), out)
        self.assertEqual(self.sql('SELECT count(*) FROM intake_reservations WHERE account_id = %s', (self.account,))[0][0], 0)
        self.assertEqual(self.store.get(row.id, self.project, self.account).copy_state, 'none')

    def test_with_the_free_scope_nearly_full_the_next_reserve_is_refused_and_the_sketch_stays_deterministic(self):
        d = self.direction()
        row, _ = self.sketch(d)
        other = self.svc.reserve(idempotency_key=f'prefill:{uuid.uuid4().hex}', account_id=self.account,
                                 project_id=self.project, quote_=B.Quote(Decimal('0.095'), {'task': 'direction_sketch'}),
                                 caps=B.Caps(C.SKETCH_MAX_USD, Decimal('5')), purpose='sketch-free',
                                 payload={'task': 'direction_sketch'})
        self.assertEqual(self.free_counted(), Decimal('0.095'))
        out = self.request(row, d)
        self.assertEqual(out['state'], 'failed')
        self.assertTrue(out['reason'].startswith('limit:'), out)
        stored = self.store.get(row.id, self.project, self.account)
        self.assertEqual((stored.copy_state, stored.copy), ('failed', None))
        self.assertLessEqual(self.free_counted(), C.SKETCH_MAX_USD)
        self.assertEqual(self.svc.get(other.id).state, B.RESERVED)

    def test_the_total_on_a_projects_free_scope_never_passes_the_cap(self):
        d = self.direction()
        rows = [self.sketch(d, seq=i)[0] for i in range(3)]
        for row in rows:
            self.request(row, d)
            self.run_worker(Transport(mode='not_json'))
            self.finalise(row, d)
            self.assertLessEqual(self.free_counted(), C.SKETCH_MAX_USD)

    def test_an_actual_above_the_quote_is_a_company_loss_row(self):
        d = self.direction()
        row, _ = self.sketch(d)
        out = self.request(row, d)
        quoted = self.svc.get(out['reservation_id']).quoted_usd
        self.run_worker(Transport(reported=quoted * 2))
        rows = self.sql("SELECT cause FROM company_loss_events WHERE reservation_id = %s", (out['reservation_id'],))
        self.assertEqual([r[0] for r in rows], ['metered_overrun'], rows)


class TheKillSwitch(PG):
    def test_a_switch_off_before_the_request_reserves_nothing(self):
        d = self.direction()
        row, _ = self.sketch(d)
        with mock.patch.dict(os.environ, {'OMNI_ZERO_COST_MODE': '1'}):
            out = self.request(row, d)
        self.assertEqual(out['state'], 'refused')
        self.assertEqual(self.sql('SELECT count(*) FROM intake_reservations WHERE account_id = %s', (self.account,))[0][0], 0)
        self.assertEqual(self.store.get(row.id, self.project, self.account).copy_state, 'none')

    def test_a_switch_off_before_the_worker_releases_it_and_the_slot_stays_free(self):
        d = self.direction()
        row, _ = self.sketch(d)
        out = self.request(row, d)
        before = Transport.calls
        with mock.patch.dict(os.environ, {'OMNI_ZERO_COST_MODE': '1'}):
            done = RW.execute_reservation(self.pool, out['reservation_id'])     # no factory: the real build_gateway
        self.assertEqual(done['state'], B.RELEASED, done)
        self.assertEqual(Transport.calls, before)                                 # the provider was never contacted
        failed = self.finalise(row, d)
        self.assertEqual(failed.copy_state, 'failed')
        self.assertTrue(failed.copy_reason.startswith('released'), failed.copy_reason)
        self.assertEqual(self.free_counted(), 0)
        other, _ = self.sketch(d, seq=1)
        self.assertEqual(self.store.claim(other.id, self.project, self.account, 'company_first'), S.FREE)

    def test_a_queue_that_is_down_releases_the_money_and_the_slot(self):
        d = self.direction()
        row, _ = self.sketch(d)

        def broken(_):
            raise ConnectionError('redis down')
        out = C.request(self.store, self.svc, broken, row, d)
        self.assertEqual((out['state'], out['reason']), ('failed', 'queue_unavailable'), out)
        self.assertEqual(self.svc.get(out['reservation_id']).state, B.RELEASED)
        self.assertEqual(self.free_counted(), 0)
        self.assertEqual(self.store.get(row.id, self.project, self.account).copy_state, 'failed')


class WhatTheWorkerRuns(PG):
    def test_a_payload_naming_another_task_than_its_quote_is_released_and_never_sent(self):
        d = self.direction()
        row, _ = self.sketch(d)
        system, user = C.prompt(d)
        quote = B.quote(system=system, user=user, max_tokens=C.MAX_TOKENS, task=C.TASK)
        r = self.svc.reserve(idempotency_key=f'mismatch:{uuid.uuid4().hex}', account_id=self.account,
                             project_id=self.project, quote_=quote, caps=B.Caps(C.SKETCH_MAX_USD, Decimal('5')),
                             purpose='sketch-free', payload={'system': system, 'user': user, 'max_tokens': C.MAX_TOKENS,
                                                             'task': 'conversation_complex'})
        before = Transport.calls
        out = RW.execute_reservation(self.pool, r.id, gateway_factory=gateway_with(Transport()))
        self.assertEqual((out['state'], out['error']), (B.RELEASED, 'reserved task mismatch'), out)
        self.assertEqual(Transport.calls, before)

    def test_the_task_is_a_reserved_one_and_has_a_class(self):
        from omni_prod.intelligence.task_policy import TASK_CLASSES
        self.assertIn('direction_sketch', RW.RESERVED_TASKS)
        self.assertIn('direction_sketch', TASK_CLASSES)
        self.assertEqual(B.quote(system='s', user='u', max_tokens=100, task='direction_sketch').envelope['task'], 'direction_sketch')


class AnUnknownCall(PG):
    def test_fails_the_sketch_and_its_quote_stays_held_on_the_free_scope(self):
        d = self.direction()
        row, _ = self.sketch(d)
        out = self.request(row, d)
        r = self.svc.claim(out['reservation_id'], worker_id='t')
        self.assertTrue(self.svc.mark_executing(r))
        quoted = r.quoted_usd
        self.svc.settle(r, cost_state=B.COST_UNKNOWN, actual_usd=None, failure_reason='timeout after the request was sent')
        done = self.finalise(row, d)
        self.assertEqual(done.copy_state, 'failed')
        self.assertTrue(done.copy_reason.startswith('unknown'), done.copy_reason)
        self.assertEqual(self.free_counted(), quoted)                       # held in full: a failed attempt still counts
        self.assertEqual(self.store.attempts(self.project, self.account), 1)


class TheOwnersOwnAccount(PG):
    def test_every_sketch_of_the_owner_is_funded_by_the_company_outside_the_one_free_rule(self):
        from omni_prod import pricing
        owner = pricing.OWNER_ACCOUNT_ID
        d = self.direction()
        got = []
        for i in range(3):
            row, _ = self.sketch(d, account=owner, project=self.project, seq=i)
            out = self.request(row, d)
            got.append((out['state'], self.store.get(row.id, self.project, owner).funding))
        self.assertEqual(got, [('pending', 'owner')] * 3)
        self.assertEqual(self.sql('SELECT count(*) FROM credit_reservations')[0][0], 0)
        self.assertEqual(self.sql("SELECT count(*) FROM direction_sketches WHERE funding = 'company_first'")[0][0], 0)


class TheStoreIsPerTenant(PG):
    def test_create_is_idempotent_and_a_sketch_of_another_account_or_project_is_not_found(self):
        d = self.direction()
        a, made = self.sketch(d)[0], None
        b, _ = self.sketch(d)
        self.assertEqual(a.id, b.id)
        self.assertEqual(self.sql('SELECT count(*) FROM direction_sketches WHERE project_id = %s', (self.project,))[0][0], 1)
        self.assertIsNone(self.store.get(a.id, self.project, 'usr_someone_else'))
        self.assertIsNone(self.store.get(a.id, 'prj_other', self.account))
        self.assertIsNone(self.store.get('skt_' + 'f' * 24, self.project, self.account))
        self.assertEqual(self.store.get(a.id, self.project, self.account).id, a.id)

    def test_the_table_refuses_a_malformed_row(self):
        import psycopg
        for bad in ("'nope'", "'skt_zz'"):
            with self.subTest(bad=bad), self.assertRaises(psycopg.errors.CheckViolation):
                self.sql("INSERT INTO direction_sketches (id, project_id, account_id, brief_revision, brief_fingerprint, "
                         "direction_fp, copy_fp, funding, copy_state, record) VALUES (" + bad + ", 'p', 'a', 1, 'f', 'd', 'c', "
                         "'none', 'none', '{}')")
        with self.assertRaises(psycopg.errors.CheckViolation):          # credits only on a customer-funded sketch
            self.sql("INSERT INTO direction_sketches (id, project_id, account_id, brief_revision, brief_fingerprint, "
                     "direction_fp, copy_fp, funding, copy_state, credits, record) VALUES ('skt_' || repeat('a', 24), 'p', "
                     "'a', 1, 'f', 'd', 'c', 'company_first', 'none', 1, '{}')")


class TheCardsState(PG):
    """service.view and service.page: what the routes answer, on the real store and the real reservations."""

    def made(self):
        from omni_prod.direction_sketch import service as SK
        brief = D.start(SALON)
        row = type('BriefRow', (), {'brief': brief, 'revision': 1, 'fingerprint': brief.fingerprint()})()
        sketch, words = SK.create(self.store, self.svc, self.queue.append, row, account_id=self.account,
                                  project_id=self.project, has_version=False, has_open_build=False)
        return SK, sketch, words

    def test_a_pending_sketch_is_finalised_when_its_state_is_read_and_its_page_carries_the_words(self):
        SK, sketch, words = self.made()
        self.assertEqual(words['state'], 'pending', words)
        self.assertEqual(SK.view(self.store, self.svc, sketch)['state'], 'pending')
        self.run_worker()
        seen = SK.view(self.store, self.svc, self.store.get(sketch.id, self.project, self.account))
        self.assertEqual((seen['state'], seen['words'], seen['funding']), ('written', 'model', 'free'))
        html = SK.page(self.store, self.store.get(sketch.id, self.project, self.account))
        self.assertIn(GOOD['sections']['hero']['title'], html)
        self.assertNotIn('כאן תופיע שורת הפתיחה', html)
        self.assertIn('draft-ribbon', html)

    def test_the_customers_view_names_no_amount_no_reservation_and_no_prompt(self):
        SK, sketch, _ = self.made()
        self.run_worker()
        seen = SK.view(self.store, self.svc, self.store.get(sketch.id, self.project, self.account))
        text = repr(seen).lower()
        for hidden in ('usd', 'quote', 'irs_', 'reservation', 'prompt', 'approved project brief', self.account.lower()):
            self.assertNotIn(hidden, text, hidden)

    def test_the_same_request_is_the_same_sketch_and_reserves_once(self):
        SK, first, _ = self.made()
        _, second, again = self.made()
        self.assertEqual(first.id, second.id)
        self.assertEqual(self.sql("SELECT count(*) FROM intake_reservations WHERE account_id = %s AND quote->>'task' = 'direction_sketch'",
                                  (self.account,))[0][0], 1)
        self.assertEqual(len(self.queue), 1)

    def test_a_change_of_colour_after_the_words_reuses_them_and_costs_nothing(self):
        SK, first, _ = self.made()
        self.run_worker()
        SK.view(self.store, self.svc, self.store.get(first.id, self.project, self.account))     # finalised: written
        brief = D.start(SALON)
        brief.fields['color'] = {'value': 'כחול', 'source': 'answer', 'question_id': 'color', 'confidence': 'stated'}
        row = type('BriefRow', (), {'brief': brief, 'revision': 2, 'fingerprint': brief.fingerprint()})()
        second, words = SK.create(self.store, self.svc, self.queue.append, row, account_id=self.account,
                                  project_id=self.project, has_version=False, has_open_build=False)
        self.assertNotEqual(first.id, second.id)
        self.assertEqual((second.funding, second.copy_state, second.copy_from, words['state']), ('none', 'written', first.id, 'written'))
        self.assertEqual(self.queue, [])                                                   # no second call
        self.assertEqual(self.sql("SELECT count(*) FROM intake_reservations WHERE account_id = %s", (self.account,))[0][0], 1)
        html = SK.page(self.store, second)
        self.assertIn(GOOD['sections']['hero']['title'], html)                              # the same words, the new colour
        self.assertEqual(SK.view(self.store, self.svc, second)['funding'], 'free')


if __name__ == '__main__':
    unittest.main()
