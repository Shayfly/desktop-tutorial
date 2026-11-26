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


class TheCostOfACorrection(unittest.TestCase):
    """Review S6: the dollar figure in agents.py is measured here. ESTIMATE: an upper bound from the platform's own token
    bounds (input = bytes + 64, as intake.budget.quote; output = the call's max_tokens) at the catalogue's prices."""

    def test_one_correction_is_at_most_about_eleven_cents_on_the_code_station(self):
        from decimal import Decimal
        from pathlib import Path
        catalog = {m['model']: m for m in json.loads((Path(__file__).resolve().parent.parent / 'infra' / 'worker-host'
                                                      / 'model-catalog.json').read_text(encoding='utf-8'))}
        gw = SequenceGateway([INVALID, CONTENT])
        generate(gw)
        _, user, max_tokens = gw.calls[1]                         # the correction
        tokens_in = len(A._CONTENT_SYSTEM.encode()) + len(user.encode()) + 64
        worst = {name: (Decimal(tokens_in) * Decimal(catalog[name]['input_per_million'])
                        + Decimal(max_tokens) * Decimal(catalog[name]['output_per_million'])) / Decimal(1_000_000)
                 for name in ('claude-sonnet-5-5', 'gemini-3.8-flash')}
        self.assertEqual(max_tokens, A.MAX_CONTENT_TOKENS)
        self.assertTrue(Decimal('0.09') < worst['claude-sonnet-5-5'] < Decimal('0.13'), worst)
        self.assertTrue(Decimal('0.03') < worst['gemini-3.8-flash'] < Decimal('0.05'), worst)
        self.assertLess(worst['claude-sonnet-5-5'] * A.MAX_CORRECTIONS, Decimal('0.39'))


class AShortenedListIsSaidByName(unittest.TestCase):
    """Review S5 (2026-11-26): the raised maxima do not all fit one answer of MAX_CONTENT_TOKENS (money, unchanged).
    The model is told its room and names a list it shortened; the evidence records it, the customer's words say it, and
    no correction is spent on it."""

    def test_the_room_is_in_the_payload_and_the_largest_document_needs_it(self):
        gw = SequenceGateway([CONTENT])
        generate(gw)
        payload = json.loads(gw.calls[0][1])
        self.assertEqual(payload['output_room']['characters'], A.OUTPUT_CHARS)
        self.assertIn('"shortened"', payload['output_room']['rule'])
        from omni_prod.site_content import schema as K
        self.assertIn('shortened (optional)', payload['schema'])
        self.assertLess(len(json.dumps(CONTENT, ensure_ascii=False)), A.OUTPUT_CHARS)   # the owner's brief: 2,118

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
        self.assertGreater(sum(largest(s) for s in K.SECTIONS.values()), A.OUTPUT_CHARS)   # 90,966 > 20,000

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
