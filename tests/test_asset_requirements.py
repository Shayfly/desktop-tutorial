"""Image generation is requested only when the product asks for it
(founder decision 2026-10-07 #28); otherwise the build reports NOT_REQUIRED."""
import unittest

from omni_prod.capability_planner import asset_capability_status
from omni_prod.media_pipeline import AssetKind, CreativeDirector
from omni_prod.product_architect import ProductArchitect

TASK_TRACKER = ("Build a team task tracker web app: users sign up and log in, create projects, add tasks with "
                "title, due date and status, assign tasks to teammates, and see a dashboard of overdue tasks.")


def _contract(prompt):
    return ProductArchitect().compile(prompt, project_id="proj_assets", contract_version=1)


def _kinds(prompt):
    return {(r.kind, r.required) for r in CreativeDirector().plan(prompt).requests}


class AssetRequirementTests(unittest.TestCase):
    def test_internal_saas_requests_no_generated_image(self):
        self.assertEqual(_kinds(TASK_TRACKER), set())
        contract = _contract(TASK_TRACKER)
        self.assertNotIn("media.image.generate", {r.key for r in contract.capability_plan.requirements})
        status = asset_capability_status(contract.capability_plan)
        self.assertEqual(status["media.image.generate"], "NOT_REQUIRED")
        self.assertEqual(set(status.values()), {"NOT_REQUIRED"})

    def test_user_uploaded_photos_are_not_generation(self):
        self.assertEqual(_kinds("Build a photo sharing app where users upload images and comment"), set())

    def test_brand_site_with_logo_and_hero_requires_image_generation(self):
        kinds = _kinds("Build a brand website for my bakery with a logo and a hero image")
        self.assertIn((AssetKind.ICON, True), kinds)
        self.assertIn((AssetKind.IMAGE, True), kinds)
        status = asset_capability_status(_contract("Build a brand website for my bakery with a logo and a hero image").capability_plan)
        self.assertEqual(status["media.image.generate"], "REQUIRED")

    def test_hebrew_branding_intent(self):
        self.assertIn((AssetKind.ICON, True), _kinds("בנה אתר למספרה עם לוגו ומיתוג"))

    def test_games_keep_their_asset_requirements(self):
        kinds = _kinds("Build a 3D delivery racing game in Unreal")
        self.assertIn((AssetKind.ICON, True), kinds)
        self.assertIn((AssetKind.MODEL3D, True), kinds)
        self.assertIn((AssetKind.IMAGE, False), kinds)

    def test_worker_helper(self):
        from omni_prod.worker_tasks import asset_capability_status as worker_status
        self.assertIsNone(worker_status(None))
        self.assertEqual(worker_status(_contract(TASK_TRACKER).capability_plan)["media.image.generate"], "NOT_REQUIRED")


if __name__ == "__main__":
    unittest.main()
