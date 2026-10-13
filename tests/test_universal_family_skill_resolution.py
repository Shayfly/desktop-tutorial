"""Universal family skill resolution: approved Product IR beats keywords.

These tests do not assume that a product family is production ready. They only
verify that the EXISTING Agent OS resolver selects the correct skills.
"""
import unittest

from omni_prod.agent_os.resolver import required_skills, resolve, MISSING


def contract(prompt, *required):
    return {
        "prompt": prompt,
        "user_roles": ["user"],
        "product_family": "self_contained_web_v1",
        "capability_plan": {"requirements": [
            {"key": key, "required": True} for key in required
        ]},
    }


class ProductIRSkillResolutionTests(unittest.TestCase):
    def test_web_about_games_does_not_require_game_engine(self):
        req = required_skills(contract(
            "אתר תוכן עם מאמרים על משחקי מחשב ומשחקי 2D", "target.web"))
        self.assertIn("page_generation", req)
        self.assertNotIn("collision", req)
        self.assertNotIn("gameplay_test", req)

    def test_site_about_video_does_not_trigger_image_generation(self):
        req = required_skills(contract(
            "אתר תדמית המסביר על טכנולוגיית יצירת וידאו", "target.web"))
        self.assertNotIn("text_to_image", req)
        self.assertNotIn("image_quality_check", req)

    def test_font_assistant_and_pot_location_stay_web(self):
        req = required_skills(contract(
            "אתר עציצים עם מיקום במרפסת ופונט Assistant", "target.web"))
        self.assertNotIn("collision", req)
        self.assertNotIn("text_to_image", req)
        self.assertNotIn("workflow_test", req)

    def test_real_2d_game_requests_gameplay_skills(self):
        req = required_skills(contract("משחק 2D", "target.web", "target.game.2d"))
        for skill in ("collision", "player_input", "gameplay_test", "touch_controls"):
            self.assertIn(skill, req)

    def test_real_media_creation_requests_media_skills(self):
        req = required_skills(contract(
            "תמונה שיווקית שנוצרת דרך AI", "target.web", "media.image.generate"))
        self.assertIn("text_to_image", req)
        self.assertIn("image_quality_check", req)

    def test_real_automation_requests_workflow_skills(self):
        req = required_skills(contract("אוטומציה", "target.web", "target.automation"))
        self.assertIn("trigger_definition", req)
        self.assertIn("workflow_test", req)

    def test_optional_game_target_does_not_inflate_mandatory_skills(self):
        c = contract("דף נחיתה על משחקים", "target.web")
        c["capability_plan"]["requirements"].append(
            {"key": "target.game.2d", "required": False})
        self.assertNotIn("collision", required_skills(c))

    def test_string_false_does_not_count_as_required(self):
        c = contract("דף נחיתה", "target.web")
        c["capability_plan"]["requirements"].append(
            {"key": "target.game.2d", "required": "false"})
        self.assertNotIn("collision", required_skills(c))

    def test_legacy_without_capability_plan_retains_original_route(self):
        req = required_skills({"prompt": "משחק 2D", "user_roles": ["user"]})
        self.assertIn("collision", req)

    def test_missing_game_skill_is_reported_not_claimed_available(self):
        c = contract("משחק 2D", "target.web", "target.game.2d")
        result = resolve(c, {"requirement_extraction": "LIVE"})
        self.assertEqual(result["overall"], MISSING)
        self.assertIn("collision", result["missing"])


if __name__ == "__main__":
    unittest.main()
