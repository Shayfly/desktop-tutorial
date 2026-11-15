"""First agent, UI slice: the proposal view and its edits (the API wraps these). Real path: the butcher's production
brief (rev 8) through the real canon, editor and brief_slice; the repository is the in-memory one with the
BriefRepository compare-and-set contract (tests.test_first_agent_brief_slice.MemoryBriefs)."""
import json
import unittest
from pathlib import Path

from omni_prod.discovery import Brief
from omni_prod.first_agent import proposal as P
from tests.test_first_agent_brief_slice import MemoryBriefs

FX = json.loads((Path(__file__).resolve().parent / 'fixtures' / 'butcher_prj_fV8kB7FwuNimGw.json').read_text())
BUTCHER = Brief.from_dict(FX['brief'])


class TheView(unittest.TestCase):
    def test_the_butcher_sees_his_card_and_price(self):
        v = P.view(MemoryBriefs(BUTCHER).latest('prj'))
        self.assertTrue(v['ok'])
        self.assertEqual([r['key'] for r in v['cards'][0]['rows']], ['hero', 'products', 'hours', 'location', 'contact', 'footer'])
        self.assertEqual((v['price']['amount_ils'], v['price']['label_he']), (189, 'הערכה'))
        self.assertEqual(v['brief_fingerprint'], FX['fingerprint'])
        self.assertTrue(any(f['key'] == 'phone' for f in v['facts']))

    def test_a_blocked_proposal_is_not_shown_to_the_customer(self):
        b = Brief.from_dict({**FX['brief'], 'prompt': 'אתר לאטליז "שמעון". טלפון 0504000162. שעות פתיחה וכתובת.'})
        v = P.view(MemoryBriefs(b).latest('prj'))
        self.assertFalse(v['ok'])
        self.assertIsNone(v['cards'])
        self.assertEqual({x['row'] for x in v['agent_blocks']}, {'hours', 'location'})


class Edits(unittest.TestCase):
    def test_an_edit_is_saved_as_structure_and_undo_restores_the_brief(self):
        repo = MemoryBriefs(BUTCHER)
        out = P.edit(repo, project_id='prj', account_id='usr', revision=1, op='move_up', key='hours')
        self.assertEqual([r['key'] for r in out['proposal']['cards'][0]['rows']][:3], ['hero', 'hours', 'products'])
        self.assertEqual(out['proposal']['revision'], 2)
        self.assertNotEqual(out['proposal']['brief_fingerprint'], FX['fingerprint'])   # the approval would bind this
        again = P.view(repo.latest('prj'))                                             # the stored structure is used
        self.assertEqual([r['key'] for r in again['cards'][0]['rows']][1], 'hours')
        back = P.undo(repo, project_id='prj', account_id='usr', undo=out['undo'])
        self.assertEqual(back['proposal']['brief_fingerprint'], FX['fingerprint'])
        self.assertEqual(back['proposal']['revision'], 3)

    def test_a_stale_tab_is_refused(self):
        repo = MemoryBriefs(BUTCHER)
        P.edit(repo, project_id='prj', account_id='usr', revision=1, op='remove', key='footer')
        with self.assertRaises(P.StaleProposal):
            P.edit(repo, project_id='prj', account_id='usr', revision=1, op='remove', key='hero')

    def test_a_customer_rewrite_is_kept_marked(self):
        repo = MemoryBriefs(BUTCHER)
        out = P.edit(repo, project_id='prj', account_id='usr', revision=1, op='set_detail', key='footer',
                     value='בשר טרי כל בוקר')
        footer = out['proposal']['cards'][0]['rows'][-1]
        self.assertEqual((footer['detail'], footer.get('edited')), ('בשר טרי כל בוקר', True))


if __name__ == '__main__':
    unittest.main()
