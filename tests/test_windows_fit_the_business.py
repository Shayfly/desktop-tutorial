"""The owner, 2026-11-19, on the law-firm site: "בחלונות באתר שום דבר לא קשור למה הוא מציע" -- every site was offered
all eight windows (a cart and an age gate to a law firm). The offer now follows the request: cookies and a question
widget for every site, a cart / chips / mega menu only for a shop, an age gate only for alcohol or tobacco, a promotion
bar or entry popup only with a sale or a shop. A window the customer already decided on is always shown."""
import unittest

from omni_prod import window_catalog as W

LAW = 'משרד עורכי דין כהן ושות׳ בתל אביב, דיני עבודה. כמה עולה ייעוץ ראשון? טלפון 03-5551234'
BUTCHER = 'האטליז של סבא שמעון בירושלים, מבצעים כל שבוע, טלפון 050-4000162'
WINE = 'חנות יין אונליין עם קטגוריות, סל קניות ומשלוחים'


class TheWindowsFitTheBusiness(unittest.TestCase):
    def test_a_law_firm_gets_cookies_and_a_question_widget_only(self):
        self.assertEqual([w['id'] for w in W.offer('he', text=LAW)], ['cookie_banner', 'question_widget'])

    def test_a_sale_brings_the_promotion_windows_and_no_cart(self):
        self.assertEqual(W.relevant(BUTCHER), ['cookie_banner', 'entry_popup', 'promo_bar', 'question_widget'])

    def test_a_wine_shop_gets_every_window_with_the_age_gate(self):
        self.assertEqual(W.relevant(WINE), list(W.CATALOG))

    def test_a_word_inside_another_word_is_not_a_reason(self):
        self.assertNotIn('cart_drawer', W.relevant('מסעדה עם סלט ירוק וסלסלת לחם'))   # סל inside סלט / סלסלה
        self.assertNotIn('age_gate', W.relevant('בית קפה בעין כרם'))                     # no wine word

    def test_a_decided_window_is_never_hidden(self):
        offer = W.offer('he', approved=['age_gate'], rejected=['cart_drawer'], text=LAW)
        self.assertEqual({w['id']: w['state'] for w in offer},
                         {'age_gate': 'approved', 'cookie_banner': None, 'cart_drawer': 'rejected',
                          'question_widget': None})

    def test_without_the_request_every_window_is_listed(self):
        self.assertEqual([w['id'] for w in W.offer('he')], list(W.CATALOG))

    def test_a_window_without_an_offer_rule_raises(self):
        W.CATALOG['new_window'] = W.CATALOG['chips']
        try:
            with self.assertRaises(KeyError):
                W.relevant(LAW)
        finally:
            del W.CATALOG['new_window']


if __name__ == '__main__':
    unittest.main()
