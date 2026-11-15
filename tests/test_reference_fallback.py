"""Step 6: the closed catalogue (appendices A and B) and the graded fallback (section 9).

The appendices are the whole list: a category or a link outside them must fail loudly, never be invented. The
fallback walks at most two links, takes another vertical only where appendix B marks it, and when nothing survives
it says so (`weak`, no attribution) and puts the category in the collect queue.
"""
import unittest
from datetime import datetime, timezone

from omni_prod import reference_catalog as C
from omni_prod import reference_fallback as F
from omni_prod.reference_store import MemoryReferenceStore
from tests.reference_cards_fixture import card

NOW = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)


def store_with(*pairs):
    s = MemoryReferenceStore()
    for n, category in pairs:
        s.add_card(card(n, vertical=category), extraction_version='x1')
    return s


class TheClosedCatalogue(unittest.TestCase):
    def test_appendix_a_is_exactly_thirty_categories(self):
        self.assertEqual(len(C.CATEGORIES), 30)
        self.assertEqual(C.CATEGORIES['delis'], 'מעדניות וגורמה')

    def test_a_category_outside_the_appendices_is_refused(self):
        for bad in ('tattoo_studios', 'fish_shops', 'clothes', ''):
            with self.assertRaises(C.CatalogError):
                C.check(bad)

    def test_every_link_names_known_categories_and_never_itself(self):
        for a, b, _ in C.LINKS:
            self.assertTrue(C._known(a) and C._known(b), (a, b))
            self.assertNotEqual(a, b)

    def test_a_reserve_category_is_reachable_only_as_a_marked_cross_vertical_link(self):
        for a, b, cross in C.LINKS:
            for slug in (a, b):
                if slug in C.RESERVE:
                    self.assertTrue(cross, slug)
        self.assertFalse(C.collectable('pet_shops'))
        self.assertEqual(C.neighbours('vets'), [('pet_shops', True)])

    def test_the_lines_that_could_not_be_resolved_are_listed_not_guessed(self):
        self.assertEqual([line for line, _ in C.UNRESOLVED], ['קליניקות ↔ פיזיותרפיה'])

    def test_neighbours_are_in_the_appendix_order(self):
        self.assertEqual(C.neighbours('restaurants'), [('cafes', False), ('alcohol', False), ('cabins', False)])
        self.assertEqual(C.neighbours('lawyers'), [])          # appendix B gives it none: no fallback


class TheGradedFallback(unittest.TestCase):
    def test_the_category_itself_comes_first(self):
        out = F.offer_for(store_with((1, 'restaurants'), (2, 'cafes')), 'restaurants', now=NOW)
        self.assertEqual((out['category'], out['distance'], out['status'], out['attribution']),
                         ('restaurants', 0, 'ok', True))
        self.assertEqual(out['collect_requested'], None)

    def test_one_link_then_two_links_and_never_three(self):
        one = F.offer_for(store_with((1, 'cafes')), 'restaurants', now=NOW)
        self.assertEqual((one['category'], one['distance']), ('cafes', 1))
        two = F.offer_for(store_with((1, 'catering')), 'restaurants', now=NOW)       # restaurants -> cafes -> catering
        self.assertEqual((two['category'], two['distance']), ('catering', 2))
        three = F.offer_for(store_with((1, 'hvac')), 'renovation', now=NOW)          # renovation -> electrical -> plumbing -> hvac
        self.assertEqual((three['status'], three['cards'], three['attribution']), ('weak', [], False))

    def test_a_foreign_vertical_only_where_the_appendix_marks_it(self):
        crossed = F.offer_for(store_with((1, 'pet_shops')), 'vets', now=NOW)
        self.assertEqual((crossed['category'], crossed['cross_vertical'], crossed['status']),
                         ('pet_shops', True, 'ok'))
        self.assertEqual([n for n, _ in C.neighbours('fashion')], ['jewelry'])
        self.assertNotIn('fashion', [n for n, _ in C.neighbours('vets')])            # no fish -> clothes

    def test_an_empty_category_asks_for_a_collection_and_never_waits(self):
        s = store_with((1, 'cafes'))
        out = F.offer_for(s, 'restaurants', now=NOW, brief_id='brf_1')
        self.assertEqual(out['collect_requested'], 'empty_category')
        self.assertEqual(s.open_collect_requests(),
                         [{'category': 'restaurants', 'reason': 'empty_category', 'brief_id': 'brf_1'}])
        F.offer_for(s, 'restaurants', now=NOW, brief_id='brf_2')                      # not queued twice
        self.assertEqual(len(s.open_collect_requests()), 1)

    def test_weak_says_so_asks_for_a_collection_and_offers_nothing_it_does_not_have(self):
        s = MemoryReferenceStore()
        out = F.offer_for(s, 'lawyers', now=NOW)
        self.assertEqual((out['status'], out['attribution'], out['cards'], out['collect_requested']),
                         ('weak', False, [], 'weak_category'))

    def test_a_stale_card_still_answers_instead_of_falling_to_a_neighbour(self):
        from datetime import timedelta
        old = (NOW - timedelta(days=91)).strftime('%Y-%m-%dT%H:%M:%SZ')
        s = MemoryReferenceStore()
        s.add_card(card(1, vertical='restaurants', captured_at=old), extraction_version='x1')
        s.add_card(card(2, vertical='cafes'), extraction_version='x1')
        out = F.offer_for(s, 'restaurants', now=NOW)
        self.assertEqual((out['category'], out['distance']), ('restaurants', 0))
        self.assertEqual(out['cards'][0].effective_status(NOW), 'stale')

    def test_the_chain_is_bounded_and_each_category_once(self):
        got = F.chain('renovation')
        self.assertEqual([c for c, _, _ in got][:1], ['renovation'])
        self.assertTrue(all(d <= F.MAX_LINKS for _, d, _ in got))
        self.assertEqual(len({c for c, _, _ in got}), len(got))

    def test_the_store_rows_match_the_appendix(self):
        s = MemoryReferenceStore()
        for category, ns in C.rows_for_store():
            s.set_adjacent(category, ns)
        self.assertEqual([a['category'] for a in s.adjacent('restaurants')], ['cafes', 'alcohol', 'cabins'])
        self.assertEqual(s.adjacent('vets'), [{'category': 'pet_shops', 'cross_vertical': True, 'rank': 1}])


if __name__ == '__main__':
    unittest.main()
