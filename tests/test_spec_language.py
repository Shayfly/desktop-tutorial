"""The spec is written in the customer's language (founder feedback 2026-10-07)."""
import unittest
from omni_prod.autonomous_agents import _ARCHITECT_SYSTEM
from omni_prod.product_evolution import _EVOLUTION_SYSTEM


class SpecLanguageTests(unittest.TestCase):
    def test_architect_writes_in_the_request_language(self):
        self.assertIn("same language as the user's request", _ARCHITECT_SYSTEM)

    def test_evolution_keeps_the_spec_language(self):
        self.assertIn('same language as the existing spec', _EVOLUTION_SYSTEM)


if __name__ == '__main__':
    unittest.main()
