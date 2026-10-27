"""C4 (2026-10-27): the approval screen shows every item the approval locks, one line each, assumptions marked,
each editable, and an approval covers only what was shown."""
from __future__ import annotations

import dataclasses
import pathlib
import unittest

from omni_prod import discovery as d

ROOT = pathlib.Path(__file__).resolve().parents[1]


def brief_flowers():
    b = d.start('אתר לחנות פרחים עם משלוחים לאילת ותשלום במזומן בלבד', mode=d.RECOMMEND)
    return d.answer(b, {'login': 'none', 'personal_data': 'no', 'content_only': 'no'})


class ApprovalItemsTests(unittest.TestCase):
    def test_every_locked_item_is_one_line(self):
        b = brief_flowers()
        items = d.approval_items(b)
        locked = d._locked(b)
        self.assertEqual([x['key'] for x in items], [k for k, _, _ in locked])
        self.assertEqual(len(items), len(b.fields) + 1)                       # every field + the request text
        self.assertEqual(d.summary(b)['approval']['locked_count'], len(items))
        for x in items:
            self.assertTrue(x['label'] and isinstance(x['value'], str), x)
            self.assertIn(x['edit'], ('form', 'chat'))

    def test_assumptions_are_marked_and_customer_decisions_are_not(self):
        b = brief_flowers()
        by = {x.get('field'): x for x in d.approval_items(b)}
        self.assertFalse(by['login']['assumed'])                               # answered by the customer
        assumed = {f for f, v in b.fields.items() if v['source'] in ('default', 'delegated')}
        self.assertTrue(assumed)
        self.assertEqual({f for f, x in by.items() if f and x['assumed']}, assumed)
        self.assertEqual({x['edit'] for x in by.values() if x.get('field')}, {'form'})

    def test_the_build_inputs_are_all_on_the_screen(self):
        """Logo and semantic decisions reach requirements_text, so they must be shown and locked too."""
        b = dataclasses.replace(brief_flowers(), assets={'logo': {'id': 'att_1', 'sha256': 'ab' * 32}},
                                semantic_decisions=[{'key': 'integration.maps', 'decision': 'required',
                                                     'evidence': 'משלוחים', 'reason': 'x'},
                                                    {'key': 'some.new.capability', 'decision': 'not_required',
                                                     'evidence': '', 'reason': 'y'}])
        keys = [x['key'] for x in d.approval_items(b)]
        self.assertIn('asset:logo', keys)
        self.assertIn('semantic:integration.maps', keys)
        self.assertIn('semantic:some.new.capability', keys)                    # unknown keys are shown, not dropped
        self.assertEqual(len(keys), d.summary(b)['approval']['locked_count'])

    def test_fingerprint_moves_with_anything_shown_and_only_with_that(self):
        b = brief_flowers()
        fp = d.approval_fingerprint(b)
        self.assertEqual(fp, d.approval_fingerprint(d.Brief.from_dict(b.to_dict())))
        changed = d.answer(b, {'color': 'ורוד עדין'})
        self.assertNotEqual(fp, d.approval_fingerprint(changed))
        relabelled = d.Brief.from_dict(b.to_dict())
        relabelled.fields['color'] = dict(relabelled.fields['color'], source='answer')
        self.assertNotEqual(fp, d.approval_fingerprint(relabelled))            # "assumption" -> "yours" is shown
        hinted = d.Brief.from_dict(b.to_dict())
        hinted.hints['style'] = 'warm'                                          # never reaches the build
        self.assertEqual(fp, d.approval_fingerprint(hinted))

    def test_english_screen_locks_the_same_items(self):
        b = brief_flowers()
        he, en = d.summary(b, 'he')['approval'], d.summary(b, 'en')['approval']
        self.assertEqual(he['fingerprint'], en['fingerprint'])
        self.assertEqual([x['key'] for x in he['items']], [x['key'] for x in en['items']])
        self.assertEqual(en['items'][0]['label'], 'Your request')


class BrowserFixtureTests(unittest.TestCase):
    def test_committed_browser_fixture_is_what_the_server_code_produces(self):
        import json
        from tests import approval_screen_fixture as F
        committed = json.loads((ROOT / 'tests/approval_screen_fixture.json').read_text())
        self.assertEqual(committed, json.loads(json.dumps(F.fixture(), ensure_ascii=False)))
        ap = committed['view']['summary']['approval']
        self.assertTrue(committed['view']['complete'])
        self.assertEqual(len(ap['items']), ap['locked_count'])


class ApprovalEndpointSourceTests(unittest.TestCase):
    """The API gate needs fastapi to run; these read the source so the gate cannot silently disappear."""
    def test_endpoint_refuses_an_approval_that_was_not_shown(self):
        src = (ROOT / 'omni_prod/investor_app.py').read_text()
        body = src[src.index("def v28_build_approval"):src.index("@app.post('/api/v28/projects/{project_id}/build-contracts')")]
        self.assertIn('req.shown_fingerprint != d.approval_fingerprint(row.brief)', body)
        self.assertLess(body.index('approval_not_shown'), body.index('create_approval'))

    def test_client_sends_the_fingerprint_and_counts_rendered_rows(self):
        js = (ROOT / 'omni_prod/assets/app.js').read_text()
        self.assertIn("shown_fingerprint: shownAp ? shownAp.fingerprint : null", js)
        self.assertIn("querySelectorAll('#approvalItems > li').length", js)
        self.assertIn('shown !== ap.locked_count', js)

    def test_postdeploy_check_approves_what_the_screen_shows(self):
        src = (ROOT / 'omni_prod/postdeploy_checks.py').read_text()
        self.assertIn("'shown_fingerprint': shown['fingerprint']", src)


if __name__ == '__main__':
    unittest.main()
