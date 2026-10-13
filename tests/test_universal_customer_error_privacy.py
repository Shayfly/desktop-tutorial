"""The normal customer never needs to choose a model or see provider internals.

Model/provider audit remains in the restricted founder runtime, not in UI errors.
"""
from pathlib import Path
import unittest

JS = (Path(__file__).resolve().parents[1] / "omni_prod" / "assets" / "app.js")


class UniversalCustomerErrorPrivacyTests(unittest.TestCase):
    def test_known_model_quota_code_maps_to_generic_message(self):
        source = JS.read_text(encoding="utf-8")
        friendly = source.split("function friendlyError(b) {", 1)[1].split("\n}", 1)[0]
        self.assertIn("unknownBuildError", friendly)
        self.assertNotIn("error_message", friendly)
        self.assertNotIn("provider quota\\/credits", friendly)

    def test_api_errors_are_not_concatenated_with_raw_server_messages(self):
        source = JS.read_text(encoding="utf-8")
        explain = source.split("function explain(err) {", 1)[1].split("\n}", 1)[0]
        self.assertNotIn("err.message", explain)
        self.assertNotIn("err.detail.message", explain)
        self.assertIn("case 402: return t('err402');", explain)
        self.assertIn("case 422: return t('err422');", explain)
        self.assertIn("case 503:", explain)

    def test_translations_exist_for_hebrew_and_english(self):
        source = JS.read_text(encoding="utf-8")
        self.assertEqual(source.count("unknownBuildError:"), 2)
        self.assertEqual(source.count("err422:"), 2)
        self.assertIn("פרטי התקלה נשמרו לאבחון מאובטח", source)


if __name__ == "__main__":
    unittest.main()
