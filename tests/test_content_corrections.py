"""Up to three corrections on the content route (the owner, 2026-11-26, WAREHOUSE 136 option a: a limit that is not
money is cancelled; one correction and then a failed build becomes a fixed, stated bound of three -- CLAUDE.md
section 3, every loop bounded).

The real route through site_content.install, the real validator, the real section library and the real pre-pass gates;
only the model gateway is scripted, by role and in order (AGENTS.md rule 2). The brief is the owner's production row
(bld_b0eb47a5, read only; its fingerprint is asserted in test_site_content_render.py).

  a document fixed by its third correction is built; one still invalid after the third fails loudly, its problems
  and every round in the evidence
  a copy finding before the sandbox is rewritten up to the same bound, and the two kinds share it
  every round is in the build evidence (site_route.correction_rounds) with the bound beside it, on success and on failure
"""
import json
import os
import unittest
from decimal import Decimal
from unittest import mock

from tests.test_site_content_agents import routed
from tests.test_site_content_engine import BAD_PATH, BAD_TEXT, CONTENT, GOOD_TEXT, PROMPT

from omni_prod import site_content
from omni_prod.site_content import agents as A

PHONE_PATH = 'sections.services.items[1].desc'
PHONE_TEXT = 'התקשרו אלינו 03-5551234 לייעוץ.'          # FACT_IN_COPY: a phone the model wrote in copy


def doc_with(path, text):
    return A.set_path(json.loads(json.dumps(CONTENT)), path, text)


INVALID = doc_with(PHONE_PATH, PHONE_TEXT)            # blocks validation
BAD_COPY = doc_with(BAD_PATH, BAD_TEXT)               # valid, but the HE gate (at block) fails its copy


class SequenceGateway:
    """The model, scripted in order: each content call takes the next document (the last one repeats), each rewrite
    the next {path: text}. Records every call (role, user payload)."""
    accepts_task_tag = False

    def __init__(self, contents, rewrites=()):
        self.contents, self.rewrites, self.calls = list(contents), list(rewrites), []

    def complete_json(self, *, system, user, max_tokens=4096, images=(), **_):
        role = {A._CONTENT_SYSTEM: 'content', A._CONTENT_REPAIR_SYSTEM: 'rewrite'}.get(system, 'other')
        self.calls.append((role, user, max_tokens))
        if role == 'content':
            doc = self.contents.pop(0) if len(self.contents) > 1 else self.contents[0]
            return json.loads(json.dumps(doc))
        if role == 'rewrite':
            return {'set': self.rewrites.pop(0)}
        raise AssertionError(f'an unexpected model call: {system[:80]!r}')

    def roles(self):
        return [r for r, _, _ in self.calls]


def generate(gw, **env):
    engine = routed(gw)
    spec = engine.architect.create_spec(PROMPT)
    with mock.patch.dict(os.environ, env):
        files = engine.generator.generate(spec)
    return engine, files


class TheBound(unittest.TestCase):
    def test_the_bound_is_three_and_stated_in_the_evidence(self):
        self.assertEqual(A.MAX_CORRECTIONS, 3)
        engine, _ = generate(SequenceGateway([CONTENT]))
        report = site_content.report(engine)                      # the build evidence's 'site_route'
        self.assertEqual((report['correction_bound'], report['correction_rounds']), (3, []))
        self.assertEqual(report['content_calls'], 1)

    def test_a_document_fixed_by_its_third_correction_is_built(self):
        gw = SequenceGateway([INVALID, INVALID, INVALID, CONTENT])
        engine, files = generate(gw)
        self.assertTrue(files)
        self.assertEqual(gw.roles(), ['content'] * 4)              # the call and three corrections
        rounds = site_content.report(engine)['correction_rounds']
        self.assertEqual([(r['round'], r['kind'], r['call']) for r in rounds],
                         [(1, 'validation', 'content'), (2, 'validation', 'content'), (3, 'validation', 'content')])
        for r in rounds:
            self.assertIn({'path': PHONE_PATH, 'code': 'FACT_IN_COPY'}, r['asked'])
        self.assertEqual(site_content.report(engine)['content_calls'], 4)

    def test_a_document_still_invalid_after_three_corrections_fails_loudly(self):
        gw = SequenceGateway([INVALID])
        engine = routed(gw)
        with self.assertRaises(A.SiteContentInvalid) as caught:
            engine.generator.generate(engine.architect.create_spec(PROMPT))
        self.assertEqual(gw.roles().count('content'), 4)           # never a fifth call
        self.assertIn('after 3 corrections', str(caught.exception))
        self.assertIn((PHONE_PATH, 'FACT_IN_COPY'), {(p['path'], p['code']) for p in caught.exception.problems})
        from omni_prod import worker_tasks as W
        evidence = W._site_route_evidence(engine)                  # what a failed build records
        self.assertEqual(len(evidence['correction_rounds']), 3)
        self.assertEqual(evidence['correction_bound'], 3)
        self.assertIn((PHONE_PATH, 'FACT_IN_COPY'), {(p['path'], p['code']) for p in evidence['problems']})
        self.assertEqual(W.failure_code(caught.exception), 'site_content_invalid')

    def test_a_copy_finding_is_rewritten_until_it_passes_within_the_bound(self):
        gw = SequenceGateway([BAD_COPY], rewrites=[{BAD_PATH: BAD_TEXT}, {BAD_PATH: GOOD_TEXT}])
        engine, files = generate(gw, OMNI_GATE_HE='block')
        self.assertEqual(gw.roles(), ['content', 'rewrite', 'rewrite'])
        rounds = site_content.report(engine)['correction_rounds']
        self.assertEqual([(r['kind'], r['call']) for r in rounds], [('copy_check', 'rewrite')] * 2)
        self.assertEqual([a['path'] for a in rounds[0]['asked']], [BAD_PATH])
        self.assertTrue(any('HE_GENDER' in f for f in rounds[0]['asked'][0]['findings']), rounds[0])
        page = dict((f.path, f.content) for f in files)['public/index.html']
        self.assertIn(GOOD_TEXT, page)
        self.assertNotIn(BAD_TEXT, page)

    def test_validation_and_copy_rounds_share_the_one_bound(self):
        gw = SequenceGateway([INVALID, INVALID, BAD_COPY], rewrites=[{BAD_PATH: GOOD_TEXT}])
        engine, _ = generate(gw, OMNI_GATE_HE='block')
        self.assertEqual(gw.roles(), ['content', 'content', 'content', 'rewrite'])
        self.assertEqual([r['kind'] for r in site_content.report(engine)['correction_rounds']],
                         ['validation', 'validation', 'copy_check'])
        gw = SequenceGateway([INVALID, INVALID, BAD_COPY], rewrites=[{BAD_PATH: BAD_TEXT}, {BAD_PATH: GOOD_TEXT}])
        engine = routed(gw)
        with mock.patch.dict(os.environ, {'OMNI_GATE_HE': 'block'}):
            with self.assertRaises(A.SiteContentInvalid) as caught:
                engine.generator.generate(engine.architect.create_spec(PROMPT))
        self.assertIn('a copy finding remains after 3 corrections', str(caught.exception))
        self.assertEqual(gw.roles(), ['content', 'content', 'content', 'rewrite'])      # no fourth correction
        self.assertEqual(len(engine.site_report['correction_rounds']), 3)

    def test_a_rewrite_that_breaks_the_document_gets_a_correction_not_a_failure(self):
        # before: "the rewrite made the document invalid" ended the build; now it is one more round, within the bound
        gw = SequenceGateway([BAD_COPY, CONTENT], rewrites=[{BAD_PATH: PHONE_TEXT}])
        engine, files = generate(gw, OMNI_GATE_HE='block')
        self.assertEqual(gw.roles(), ['content', 'rewrite', 'content'])
        self.assertEqual([r['kind'] for r in site_content.report(engine)['correction_rounds']],
                         ['copy_check', 'validation'])
        self.assertTrue(files)


class TheTokensAreMeasuredNotCapped(unittest.TestCase):
    """The owner, 2026-11-26 ~16:10 UTC: "לבטל מגבלה על טוקנים כרגע רק מדידה". No product-chosen output cap on the
    content path: every call asks for its model's own documented maximum (the catalogue's max_output_tokens), and every
    call's real tokens, cost and stop reason are in the build evidence. A real RoutedModelGateway over a catalogue; only
    the provider's HTTP answer is scripted."""

    CATALOG = [
        {"name": "big", "provider": "big", "base_url": "https://big.example/v1", "model": "big-1", "api_key_env": "BIG_KEY",
         "quality": 92, "input_per_million": "0.10", "output_per_million": "0.20", "max_output_tokens": 64000},
        {"name": "mid", "provider": "mid", "base_url": "https://mid.example/v1", "model": "mid-1", "api_key_env": "MID_KEY",
         "quality": 90, "input_per_million": "0.05", "output_per_million": "0.10", "max_output_tokens": 32768},
    ]

    def routed_gateway(self, finish='stop', usage=(1200, 900)):
        from decimal import Decimal
        from omni_prod.model_catalog import parse_model_catalog
        from omni_prod.model_policy import ModelUsePolicy
        from omni_prod.provider_usage import ProviderUsage
        from omni_prod.routed_gateway import RoutedModelGateway, RoutingPolicy
        sent = []

        class Provider:
            def __init__(self, endpoint):
                self.endpoint, self.last_usage, self.last_finish_reason = endpoint, None, None

            def complete_json(self, *, system, user, max_tokens, validate=None, **_):
                sent.append((self.endpoint.name, max_tokens))
                self.last_usage = ProviderUsage(self.endpoint.name, self.endpoint.model, True, 'req', 'header:x',
                                                'resp', usage[0], usage[1], None, None, True)
                self.last_finish_reason = finish
                data = json.loads(json.dumps(CONTENT))
                if validate is not None:
                    validate(data)
                return data
        gw = RoutedModelGateway(ranked=parse_model_catalog(json.dumps(self.CATALOG), {'BIG_KEY': 'k', 'MID_KEY': 'k'}),
                                routing_policy=RoutingPolicy(minimum_quality=70),
                                policy=ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                                                      external_budget_usd=Decimal('5.00'),
                                                      max_external_calls_per_build=20),
                                gateway_factory=Provider)
        return gw, sent

    def test_each_call_asks_for_its_models_own_maximum(self):
        gw, sent = self.routed_gateway()
        self.assertEqual(A.output_maximum(gw), 64000)
        engine, _ = generate(gw)
        self.assertEqual(sent, [('mid', 32768)])              # the cheapest eligible model, given ITS maximum
        self.assertFalse(hasattr(A, 'MAX_CONTENT_TOKENS') or hasattr(A, 'MAX_REWRITE_TOKENS'))
        scripted = SequenceGateway([INVALID, CONTENT])         # no catalogue on the gateway: the repository's
        generate(scripted)
        self.assertEqual({m for _, _, m in scripted.calls}, {64000})   # claude-sonnet-5-5's 64,000 (model-catalog.json)

    def test_every_call_is_measured_with_its_cost_and_the_build_totals(self):
        gw, _ = self.routed_gateway()
        engine, _ = generate(gw)
        usage = site_content.report(engine)['content_usage']
        self.assertEqual((usage['calls'], usage['attempts'], usage['unmeasured_calls']), (1, 1, 0))
        self.assertEqual((usage['input_tokens'], usage['output_tokens']), (1200, 900))
        # metered by the router from the provider's tokens at the catalogue price: 1200 x 0.05 + 900 x 0.10 per million
        self.assertEqual(usage['metered_cost_usd'], str(Decimal('0.00015')))
        call = usage['per_call'][0]
        first = call['attempts'][0]
        self.assertEqual((call['role'], call['max_tokens']), ('content', 64000))              # asked: the largest
        self.assertEqual((first['model'], first['max_tokens_sent'], first['model_maximum'], first['finish_reason']),
                         ('mid-1', 32768, 32768, 'stop'))                                   # sent: ITS maximum
        self.assertEqual(usage['truncated_at_model_maximum'], [])
        self.assertEqual([r.task_type for r in gw.recorder.records], ['codegen'])     # and in the attempt ledger

    def test_a_call_that_stops_at_the_model_maximum_is_said_loudly(self):
        gw, _ = self.routed_gateway(finish='length')
        with self.assertLogs('omni_prod.site_content.agents', 'ERROR') as logs:
            engine, _ = generate(gw)
        usage = site_content.report(engine)['content_usage']
        self.assertEqual(usage['truncated_at_model_maximum'], ['content'])
        self.assertTrue(usage['per_call'][0]['attempts'][0]['truncated_at_model_maximum'])
        self.assertIn('SITE_CONTENT_TRUNCATED', logs.output[0])

    def test_a_stop_below_the_model_maximum_is_said_as_the_budget_allowance(self):
        # fit_to_budget (money, kept) may send less than the model's maximum; a stop there is not "the model's maximum"
        from types import SimpleNamespace as NS
        record = NS(kind='provider_call', attempt_seq=1, model='m', outcome='ok', input_tokens=10, output_tokens=12000,
                    metered_cost_usd=Decimal('0.1'), failure_reason=None)
        gw = NS(recorder=NS(records=[record]),
                attempt_output={1: {'finish_reason': 'length', 'max_tokens_sent': 12000, 'model_maximum': 64000}})
        with self.assertLogs('omni_prod.site_content.agents', 'ERROR') as logs:
            usage = A.usage_summary([A._measured(gw, 0, 'content', 64000)])
        self.assertEqual((usage['truncated_at_model_maximum'], usage['truncated_at_budget_allowance']), ([], ['content']))
        self.assertIn('at=budget_allowance', logs.output[0])

    def test_a_gateway_with_no_records_is_said_unmeasured_never_zero(self):
        engine, _ = generate(SequenceGateway([CONTENT]))
        usage = site_content.report(engine)['content_usage']
        self.assertEqual((usage['unmeasured_calls'], usage['input_tokens'], usage['metered_cost_usd']), (1, None, None))
        self.assertFalse(usage['per_call'][0]['measured'])


class AShortenedListIsSaidByName(unittest.TestCase):
    """Review S5, narrowed by the owner's order of 2026-11-26 16:10: the only room is the model's own output maximum.
    The model is told that room and names a list it shortened only when one would really not fit; the evidence records
    it, the customer's words say it, and no correction is spent on it."""

    def test_the_room_is_in_the_payload_and_the_largest_document_needs_it(self):
        gw = SequenceGateway([CONTENT])
        generate(gw)
        payload = json.loads(gw.calls[0][1])
        room = int(64000 * A.CHARS_PER_TOKEN_ESTIMATE)              # claude-sonnet-5-5's maximum (model-catalog.json)
        self.assertEqual(payload['output_room']['characters'], room)
        self.assertIn('"shortened"', payload['output_room']['rule'])
        from omni_prod.site_content import schema as K
        self.assertIn('shortened (optional)', payload['schema'])
        self.assertLess(len(json.dumps(CONTENT, ensure_ascii=False)), room)   # the owner's brief: 2,118

        def largest(spec):                                     # every string at its bound, every list at its maximum
            if isinstance(spec, K.Str):
                return spec.max
            if isinstance(spec, K.Lst):
                return spec.max * largest(spec.item)
            if isinstance(spec, K.Obj):
                return sum(largest(f) for f in spec.fields.values())
            if isinstance(spec, dict):
                return sum(largest(f) for f in spec.values())
            return 12
        # ESTIMATE: every list at its maximum (90,966 characters) fits the largest model's room (160,000); a smaller
        # model's room may not, and only then is `shortened` the honest answer
        self.assertLess(sum(largest(s) for s in K.SECTIONS.values()), room)

    def test_a_shortened_list_is_recorded_and_said_without_a_correction(self):
        doc = json.loads(json.dumps(CONTENT))
        doc['shortened'] = [{'list': 'services.items', 'left_out': 6, 'why': 'the answer had to fit its room'}]
        gw = SequenceGateway([doc])
        engine, files = generate(gw)
        self.assertEqual(gw.roles(), ['content'])                        # no correction spent
        report = site_content.report(engine)
        self.assertEqual(report['shortened'], doc['shortened'])
        self.assertEqual(report['shortened_said'], [A.shortened_said(doc['shortened'][0])])
        self.assertIn('השירותים', report['shortened_said'][0])
        self.assertIn('6 לא נכנסו', report['shortened_said'][0])

    def test_a_shortened_entry_that_names_no_offered_list_is_corrected(self):
        bad = json.loads(json.dumps(CONTENT))
        bad['shortened'] = [{'list': 'gallery.images', 'left_out': 0, 'why': ''}]
        gw = SequenceGateway([bad, CONTENT])
        engine, _ = generate(gw)
        rounds = site_content.report(engine)['correction_rounds']
        self.assertEqual(rounds[0]['asked'], [{'path': 'shortened[0]', 'code': 'SCHEMA_SHAPE'}])


if __name__ == '__main__':
    unittest.main()
