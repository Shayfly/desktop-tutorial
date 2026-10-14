import unittest

from omni_prod.conversation.store import MemoryConversationStore


class ConversationPreferencesTests(unittest.TestCase):
    def test_default_language_and_saved_preference_are_account_scoped(self):
        store = MemoryConversationStore()
        self.assertEqual(store.preferences_for('account-a'), {'language': 'he'})
        self.assertEqual(store.save_preferences('account-a', {'language': 'en'}), {'language': 'en'})
        self.assertEqual(store.preferences_for('account-a'), {'language': 'en'})
        self.assertEqual(store.preferences_for('account-b'), {'language': 'he'})

    def test_invalid_or_unknown_preferences_are_rejected(self):
        store = MemoryConversationStore()
        for preferences in ({'language': 'fr'}, {'language': ''}, {'language': 'he', 'tone': 'concise'}):
            with self.subTest(preferences=preferences):
                with self.assertRaises(ValueError):
                    store.save_preferences('account-a', preferences)


if __name__ == '__main__':
    unittest.main()
