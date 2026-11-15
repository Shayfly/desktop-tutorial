"""Step 7: graded rejection, the two signals, and the owner's alert (sections 10-11 of the task document).

The contract runs here on the memory store; tests/test_reference_store_pg.py runs the same alert on real PostgreSQL.
"""
import unittest
from datetime import datetime, timedelta, timezone

from omni_prod import reference_offers as O
from omni_prod.reference_store import MemoryReferenceStore, ReferenceStoreError
from tests.reference_cards_fixture import card, card_id

T0 = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)


def at(minutes):
    return T0 + timedelta(minutes=minutes)


def store_with(*pairs):
    s = MemoryReferenceStore()
    for n, category in pairs:
        s.add_card(card(n, total=10 - (n % 3), vertical=category), extraction_version='x1')
    return s


def run_alert_scenario(store, O=O, category='cafes'):
    """30 offers, then rejections one at a time; returns the rejection counts at which an alert fired."""
    for i in range(30):
        store.record_offer(brief_id=f'b{i}', category=category, card_id=None, at=at(i))
    fired = []
    for n in range(1, 22):
        signal = 'disliked' if n % 2 else 'asked_another'          # the two signals are equal
        out = O.reject(store, brief_id=f'b{n}', category=category, level='all', signal=signal, now=at(100 + n))
        if out['alert']:
            fired.append(n)
    return fired


class GradedRejection(unittest.TestCase):
    def test_a_layer_rejection_reselects_from_the_same_pool(self):
        s = store_with((1, 'cafes'), (2, 'cafes'), (3, 'cafes'))
        first = O.next_layer(s, brief_id='b', category='cafes', layer='palette', now=T0)
        O.reject(s, brief_id='b', category='cafes', level='layer', layer='palette', card_id=first.card_id,
                 signal='disliked', now=T0)
        second = O.next_layer(s, brief_id='b', category='cafes', layer='palette', now=T0)
        self.assertNotEqual(first.card_id, second.card_id)
        self.assertEqual(second.category, 'cafes')                       # same pool, no neighbour, no network
        self.assertEqual(O.next_layer(s, brief_id='b', category='cafes', layer='font', now=T0).card_id,
                         first.card_id)                                  # the font of that card was not rejected
        self.assertEqual(s.open_collect_requests(), [])

    def test_a_used_up_pool_returns_nothing_and_never_loops_back(self):
        s = store_with((1, 'cafes'))
        only = O.next_layer(s, brief_id='b', category='cafes', layer='palette', now=T0)
        O.reject(s, brief_id='b', category='cafes', level='layer', layer='palette', card_id=only.card_id,
                 signal='asked_another', now=T0)
        self.assertIsNone(O.next_layer(s, brief_id='b', category='cafes', layer='palette', now=T0))

    def test_a_domain_rejection_moves_to_the_next_card_and_queues_a_collection(self):
        s = store_with((1, 'cafes'), (2, 'cafes'))
        first = O.next_offer(s, brief_id='b', category='cafes', now=T0, want=1)['cards'][0]
        O.reject(s, brief_id='b', category='cafes', level='domain', card_id=first.card_id, signal='disliked', now=T0)
        again = O.next_offer(s, brief_id='b', category='cafes', now=T0, want=1)['cards'][0]
        self.assertNotEqual(again.card_id, first.card_id)
        self.assertEqual(s.open_collect_requests(), [{'category': 'cafes', 'reason': 'domain_rejected', 'brief_id': 'b'}])
        other = O.next_offer(s, brief_id='another', category='cafes', now=T0, want=2)['cards']
        self.assertIn(first.card_id, [c.card_id for c in other])        # rejected for THAT customer only

    def test_rejecting_everything_goes_one_link_up_for_this_customer(self):
        s = store_with((1, 'cafes'), (2, 'restaurants'))
        O.reject(s, brief_id='b', category='cafes', level='all', signal='disliked', now=T0)
        out = O.next_offer(s, brief_id='b', category='cafes', now=T0)
        self.assertEqual((out['category'], out['distance']), ('restaurants', 1))
        self.assertEqual(O.next_offer(s, brief_id='c', category='cafes', now=T0)['category'], 'cafes')

    def test_a_rejection_is_one_of_three_levels_and_one_of_two_signals(self):
        s = store_with((1, 'cafes'))
        for bad in (dict(level='whatever', signal='disliked'), dict(level='all', signal='hated'),
                    dict(level='layer', signal='disliked'), dict(level='domain', signal='disliked'),
                    dict(level='layer', signal='disliked', card_id=card_id(1), layer='shadow')):
            with self.assertRaises(ReferenceStoreError):
                O.reject(s, brief_id='b', category='cafes', now=T0, **bad)


class TheAlert(unittest.TestCase):
    def test_it_fires_at_ten_of_thirty_and_again_every_five(self):
        self.assertEqual(run_alert_scenario(MemoryReferenceStore()), [10, 15, 20])

    def test_nine_of_thirty_is_quiet(self):
        s = MemoryReferenceStore()
        for i in range(30):
            s.record_offer(brief_id=f'b{i}', category='cafes', at=at(i))
        for n in range(1, 10):
            self.assertIsNone(O.reject(s, brief_id=f'b{n}', category='cafes', level='all', signal='disliked',
                                       now=at(100 + n))['alert'])

    def test_old_rejections_outside_the_last_thirty_offers_do_not_count(self):
        s = MemoryReferenceStore()
        for n in range(1, 10):                                      # 9 rejections long ago
            s.record_offer(brief_id=f'o{n}', category='cafes', at=at(n))
            s.record_rejection(brief_id=f'o{n}', category='cafes', component_key='all:cafes', signal='disliked',
                               at=at(n))
        for i in range(30):                                         # then 30 offers nobody rejected
            s.record_offer(brief_id=f'b{i}', category='cafes', at=at(100 + i))
        out = O.reject(s, brief_id='x', category='cafes', level='all', signal='disliked', now=at(200))
        self.assertIsNone(out['alert'])                              # 1 in the window, not 10

    def test_the_count_resets_only_when_the_owner_changes_something(self):
        s = MemoryReferenceStore()
        self.assertEqual(run_alert_scenario(s), [10, 15, 20])
        self.assertEqual(O.status_report(s, ['cafes'])['alerts'],
                         [{'category': 'cafes', 'rejections': 20, 'offers': 30, 'alerts': 3}])   # still standing
        with self.assertRaises(ReferenceStoreError):
            O.owner_changed(s, 'cafes', by='michael', now=at(300))
        self.assertEqual(len(O.status_report(s, ['cafes'])['alerts']), 1)
        O.owner_changed(s, 'cafes', by='shai', now=at(300))
        self.assertEqual(O.status_report(s, ['cafes'])['alerts'], [])
        for i in range(30):
            s.record_offer(brief_id=f'n{i}', category='cafes', at=at(400 + i))
        fired = [n for n in range(1, 11) if O.reject(s, brief_id=f'n{n}', category='cafes', level='all',
                                                      signal='asked_another', now=at(500 + n))['alert']]
        self.assertEqual(fired, [10])                                # counted from the change, from zero

    def test_the_same_count_never_fires_twice(self):
        s = MemoryReferenceStore()
        run_alert_scenario(s)
        self.assertIsNone(O.check_alert(s, 'cafes', now=at(999)))

    def test_the_status_report_shows_the_collect_queue(self):
        s = store_with((1, 'cafes'))
        first = O.next_offer(s, brief_id='b', category='cafes', now=T0)['cards'][0]
        O.reject(s, brief_id='b', category='cafes', level='domain', card_id=first.card_id, signal='disliked', now=T0)
        self.assertEqual(O.status_report(s, ['cafes'])['collect_queue'],
                         [{'category': 'cafes', 'reason': 'domain_rejected', 'brief_id': 'b'}])


if __name__ == '__main__':
    unittest.main()
