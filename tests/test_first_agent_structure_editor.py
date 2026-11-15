"""First agent, slice 2 (docs/spec/first-agent.md v0.2): the structure card and the editor.

Real path: the butcher's own request (tests/fixtures/butcher_served_page_2026_11_14.json, brief rev 8) through the
real fact canon. The card the customer would see is the sketch's: six rows in order, each from what he wrote, marked
as a general suggestion (the library is empty), 189 NIS as an estimate, nothing blocked."""
import json
import unittest
from pathlib import Path

from omni_prod.fact_canon import build_canon
from omni_prod.first_agent.editor import review
from omni_prod.first_agent.structure import apply_edit, build_card

BRIEF = json.loads((Path(__file__).resolve().parent / 'fixtures' / 'butcher_served_page_2026_11_14.json').read_text())['brief']
TEXT = BRIEF['prompt']


def card_for(text, **kw):
    return build_card(text, canon=build_canon(text), **kw)


class TheButcherCard(unittest.TestCase):
    def setUp(self):
        self.canon = build_canon(TEXT)
        self.card = build_card(TEXT, canon=self.canon, vertical='butcher')

    def test_six_rows_in_order_each_from_what_he_wrote(self):
        rows = {r['key']: r for r in self.card['rows']}
        self.assertEqual([r['key'] for r in self.card['rows']], ['hero', 'products', 'hours', 'location', 'contact', 'footer'])
        self.assertIn('האטליז של סבא שמעון', rows['hero']['detail'])
        self.assertIn('התמונה תיווצר אחרי האישור', rows['hero']['detail'])
        self.assertEqual(rows['products']['detail'], 'בשר בקר טרי · עוף · הודו · קציצות מוכנות · שיפודים להזמנה')
        self.assertEqual(rows['hours']['detail'], 'א׳–ה׳ 07:00–19:00 · ו׳ 07:00–14:00 · שבת סגור')
        self.assertEqual(rows['location']['detail'], 'רחוב נתיב המזלות 22, ירושלים')
        self.assertEqual(rows['contact']['detail'], '0504000162')
        self.assertTrue(all(r['has_content'] for r in self.card['rows']))

    def test_marked_general_because_the_library_is_empty(self):
        self.assertTrue(self.card['generic'])
        self.assertEqual(self.card['generic_reason'], 'הצעה כללית: עוד אין לנו דוגמה לתחום הזה')
        self.assertEqual(card_for(TEXT)['generic_reason'], 'עוד לא ידוע התחום: זו הצעה כללית')

    def test_a_library_example_is_used_as_is_and_not_marked(self):
        card = build_card(TEXT, canon=self.canon, vertical='butcher',
                          library_order=['hero', 'products', 'story', 'hours', 'contact', 'footer'])
        self.assertFalse(card['generic'])
        self.assertEqual([r['key'] for r in card['rows']][2], 'story')
        with self.assertRaises(ValueError):
            build_card(TEXT, canon=self.canon, library_order=['hero', 'special_offer'])

    def test_the_editor_passes_it_with_the_sketch_price(self):
        v = review([self.card], canon=self.canon)
        self.assertEqual((v['ok'], v['blocks'], v['removed'], v['shown_to_customer']), (True, [], [], True))
        self.assertEqual((v['price']['amount_ils'], v['price']['label_he'], v['price']['blocks']), (189, 'הערכה', False))


class TheEditor(unittest.TestCase):
    def test_a_fact_asked_for_and_not_given_blocks_and_a_waiver_releases_it(self):
        text = 'אתר לאטליז "שמעון". טלפון 0504000162. שעות פתיחה וכפתור התקשרות.'
        canon = build_canon(text)
        card = build_card(text, canon=canon)
        v = review([card], canon=canon)
        self.assertFalse(v['ok'])
        self.assertEqual([(b['rule'], b['row'], b['missing']) for b in v['blocks']],
                         [('completeness', 'hours', ['hours']), ('completeness', 'location', ['address'])])
        self.assertFalse(v['shown_to_customer'])
        self.assertTrue(review([card], canon=canon, waived=('hours', 'address'))['ok'])

    def test_a_section_the_product_cannot_hold_is_infeasible(self):
        card = {**card_for(TEXT), 'kind': 'song'}
        v = review([card], canon=build_canon(TEXT))
        self.assertTrue(v['blocks'])
        self.assertEqual({b['rule'] for b in v['blocks']}, {'feasibility'})

    def test_a_row_without_content_is_removed_and_said(self):
        text = 'אתר לאטליז "שמעון". טלפון 0504000162. כתובת: רחוב הרצל 1, חיפה. שעות: א׳–ה׳ 08:00–18:00.'
        canon = build_canon(text)
        v = review([build_card(text, canon=canon)], canon=canon)
        self.assertTrue(v['ok'], v['blocks'])
        self.assertEqual([r['row'] for r in v['removed']], ['products'])
        self.assertNotIn('products', [r['key'] for r in v['cards'][0]['rows']])

    def test_price_never_blocks_even_at_the_ceiling(self):
        many = {**card_for(TEXT), 'rows': card_for(TEXT)['rows'] * 4}
        v = review([many, card_for(TEXT)], canon=build_canon(TEXT))
        self.assertTrue(v['ok'])
        self.assertEqual((v['price']['amount_ils'], v['price']['clamped']), (399, 'ceiling'))

    def test_cards_stack_with_one_shared_price(self):
        v = review([card_for(TEXT), card_for(TEXT)], canon=build_canon(TEXT))
        self.assertEqual(len(v['cards']), 2)
        self.assertEqual(v['price']['raw_ils'], 12 * 25 + 39)


class Edits(unittest.TestCase):
    def test_move_remove_and_rewrite_a_row(self):
        card = card_for(TEXT)
        up = apply_edit(card, 'move_up', 'hours')
        self.assertEqual([r['key'] for r in up['rows']][:3], ['hero', 'hours', 'products'])
        self.assertNotIn('footer', [r['key'] for r in apply_edit(card, 'remove', 'footer')['rows']])
        new = apply_edit(card, 'set_detail', 'footer', 'בשר טרי כל בוקר')
        self.assertEqual(new['rows'][-1]['detail'], 'בשר טרי כל בוקר')
        self.assertTrue(new['rows'][-1]['edited'])                     # what the customer changed is kept marked
        self.assertNotIn('edited', card['rows'][-1])                   # the original card is untouched

    def test_bad_edits_fail_loudly(self):
        card = card_for(TEXT)
        for op, key, val in (('explode', 'hero', None), ('remove', 'nope', None), ('set_detail', 'hero', '  ')):
            with self.assertRaises((KeyError, ValueError)):
                apply_edit(card, op, key, val)

    def test_a_section_the_customer_asked_for_is_added(self):
        text = TEXT + ' ותוסיפו גלריה של הדלפק.'
        self.assertIn('gallery', [r['key'] for r in card_for(text)['rows']])


if __name__ == '__main__':
    unittest.main()
