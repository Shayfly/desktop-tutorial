"""Route honesty, cause 2: a request one page cannot hold was accepted ("all preconditions hold").

The owner's build bld_3938e570 (the production row, redacted: tests/fixtures/site_content_bld_3938e570.json) asked
for a picture next to each category, a page per category, and to upload more products later. The content route
renders one page (render.APP_PY: GET / only, every other path 404), pictures only in the hero and story places, and
nothing its owner can edit; a4.pictures counted ONE picture, and nothing looked for pages or later editing.

one_page.beyond reads the customer's words; a picture per item, separate pages, or the owner editing later sends the
build to the legacy path (which writes the site's code, its own routes and pages) by name, with the words that asked.
Near-misses -- a hero that fits "כל מסך", a link that opens "בעמוד חדש", "דף נחיתה", "בלי תמונות", the customer
sending pictures now -- stay on the content route. The real decide(); nothing is scripted."""
import unittest

from tests.test_route_honesty import GOA, decide, with_request

from omni_prod.site_content import facts as Fx
from omni_prod.site_content import one_page

HITS = {
    'תמונה של כל נושא': 'picture_per_item', 'ליד כל מוצר תשים תמונה': 'picture_per_item',
    'לכל מנה תמונה משלה': 'picture_per_item', 'עם תמונות של המוצרים': 'picture_per_item',
    'תמונות לכל הקטגוריות': 'picture_per_item', 'תמונה לכל אחד מהמוצרים': 'picture_per_item',
    'a photo for each product': 'picture_per_item',
    'photos of the dishes': 'picture_per_item', 'product photos on the page': 'picture_per_item',
    'עמוד נפרד לכל קטגוריה': 'separate_pages', 'דף לכל מוצר': 'separate_pages',
    'שאוכל לפתוח כל נושא לעמוד חדש': 'separate_pages', 'עמודים נפרדים לשירותים': 'separate_pages',
    'לכל קטגוריה יהיה עמוד': 'separate_pages', 'אתר של כמה עמודים': 'separate_pages',
    'a separate page for each category': 'separate_pages', 'each product has its own page': 'separate_pages',
    'a multi-page site': 'separate_pages',
    'אני אוכל אחר כך להעלות עוד מוצרים': 'owner_edits_later', 'שאוכל לעדכן מחירים באתר': 'owner_edits_later',
    'לעדכן את המבצעים בעצמי': 'owner_edits_later', 'עם ממשק ניהול': 'owner_edits_later',
    'שתהיה לי אפשרות להוסיף מוצרים בהמשך': 'owner_edits_later',
    'I will add new products myself': 'owner_edits_later',
    'we want to be able to update the prices later': 'owner_edits_later', 'with an admin panel': 'owner_edits_later',
}
NEAR_MISSES = (
    'תמונה ראשית שנראית טוב בכל מסך', 'תמונה ראשית ורשימה של כל המוצרים', 'כל הקישורים ייפתחו בעמוד חדש',
    'קישור לאינסטגרם שנפתח בעמוד חדש', 'לכל שירות יש פסקה בעמוד', 'דף נחיתה בעברית למאפייה', 'הכל בעמוד אחד',
    'בלי תמונות מלאי של פטישים', 'בלי עמוד נפרד, הכל בדף אחד', 'אני אעלה לכם תמונות של החנות',
    'אני יכול להעלות לך את הלוגו עכשיו', 'אוכל טרי שאפשר להוסיף לו עוד רטבים', 'תמונה ראשית גדולה של כוס קפה',
    'כל השירותים מוצגים בעמוד הראשי', 'I can send you photos of the shop', 'a landing page with one hero image',
    'every link opens in a new page', 'בלי תמונה לכל מוצר', 'תמונות של החנות', 'הלקוח יוכל להוסיף מוצרים לסל',
    'תבנה לי אתר עם רשימה של כל סוגי הבשרים', 'אני רוצה להוסיף את המוצרים הבאים: חלות, לחמים',
    'כפתור להתקשרות בראש העמוד', 'תמונה ראשית שכל אחד יאהב', 'אני יכול להעלות לכם עוד תמונות של החנות',
    'I can upload more photos for you',
)


class OnePageCannotHoldIt(unittest.TestCase):
    def test_the_owners_request_goes_to_the_legacy_path_by_name(self):
        route = decide(GOA)
        self.assertEqual(route.route, 'legacy')
        self.assertTrue(route.reason.startswith('beyond_one_page: '), route.reason)
        found = one_page.beyond(Fx.customer_text(GOA))
        self.assertEqual([k for k, _ in found], ['picture_per_item', 'separate_pages', 'owner_edits_later'])
        words = dict(found)
        self.assertIn('כל נושא', words['picture_per_item'])
        self.assertIn('תמונה', words['picture_per_item'])
        self.assertIn('לעמוד חדש', words['separate_pages'])
        self.assertIn('להעלות', words['owner_edits_later'])
        for kind, said in found:
            self.assertIn(f'{kind} "{said}"', route.reason)
        # the customer's own request says all three; the approved brief's Screens line is read too, never alone
        self.assertEqual([k for k, _ in one_page.beyond(Fx.request_text(GOA))],
                         ['picture_per_item', 'separate_pages', 'owner_edits_later'])

    def test_a4_still_counts_one_picture(self):
        # verified, unchanged: the count is what the planner buys (a spend decision); the route reads one_page instead
        from omni_prod.a4 import pictures
        self.assertEqual(pictures(GOA)['asked'], 1)

    def test_every_kind_in_hebrew_and_english(self):
        for text, kind in HITS.items():
            with self.subTest(text):
                self.assertIn(kind, [k for k, _ in one_page.beyond(text)])

    def test_near_misses_stay_on_the_content_route(self):
        for text in NEAR_MISSES:
            with self.subTest(text):
                self.assertEqual(one_page.beyond(text), [])
        for text in NEAR_MISSES[:8]:
            with self.subTest(route=text):
                self.assertEqual(decide(with_request(text + '.')).route, 'section_library')

    def test_each_kind_on_the_route_names_itself(self):
        for text, kind in (('ליד כל שירות תשימו תמונה.', 'picture_per_item'),
                           ('עמוד נפרד לכל תחום התמחות.', 'separate_pages'),
                           ('ושאוכל לעדכן את השאלות הנפוצות בעצמי.', 'owner_edits_later')):
            with self.subTest(kind):
                route = decide(with_request(text))
                self.assertEqual(route.route, 'legacy')
                self.assertTrue(route.reason.startswith(f'beyond_one_page: {kind} "'), route.reason)


if __name__ == '__main__':
    unittest.main()
