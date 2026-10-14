import unittest

from omni_prod.capability_planner import CapabilityPlanner
from omni_prod.capability_registry import CapabilityRegistry
from omni_prod.media_pipeline import CreativeDirector
from omni_prod.unified_engine import UnifiedPromptPlanner
from omni_prod.universal_brain import OmniUniversalBrain


BASE_LIFECYCLE = {
    "software.plan",
    "software.architecture",
    "software.code.generate",
    "software.dependencies.install",
    "software.build",
    "software.test",
    "software.repair",
    "software.preview",
    "software.export",
}


def build_plan(prompt: str):
    unified = UnifiedPromptPlanner().plan(prompt)
    creative = CreativeDirector().plan(prompt, targets=unified.targets)
    return CapabilityPlanner(CapabilityRegistry()).plan(
        prompt=prompt, unified_plan=unified, creative_plan=creative
    )


class CapabilityPlannerTests(unittest.TestCase):
    def keys(self, prompt):
        return {item.key for item in build_plan(prompt).requirements}

    def test_normal_web_prompt_keeps_full_software_lifecycle(self):
        keys = self.keys("Build a CRM for technicians and customers")
        self.assertTrue(BASE_LIFECYCLE.issubset(keys))
        self.assertIn("target.web", keys)

    def test_3d_game_requires_mesh_texture_audio_and_game_target(self):
        keys = self.keys("Build a 3D football game in Unreal with crowd sound and music")
        self.assertTrue(BASE_LIFECYCLE.issubset(keys))
        self.assertIn("target.game.3d", keys)
        self.assertIn("media.3d.mesh.generate", keys)
        self.assertIn("media.3d.texture", keys)
        self.assertIn("media.audio.sfx", keys)
        self.assertIn("media.audio.music", keys)

    def test_voice_assistant_maps_tts_stt_and_realtime_voice_when_requested(self):
        keys = self.keys(
            "Build a realtime voice assistant that listens on the microphone, uses speech to text, and speaks replies"
        )
        self.assertIn("target.agent", keys)
        self.assertIn("media.audio.tts", keys)
        self.assertIn("media.audio.stt", keys)
        self.assertIn("media.audio.realtime_voice", keys)
        self.assertIn("ai.agent.tools", keys)

    def test_video_request_maps_real_video_capability(self):
        keys = self.keys("Build a product site and generate a promotional video reel")
        self.assertIn("media.video.generate", keys)

    def test_multiplayer_requirement_is_not_silently_dropped(self):
        plan = build_plan("Build an online multiplayer 3D racing game with matchmaking")
        by_key = {item.key: item for item in plan.requirements}
        by_id = {item.id: item for item in plan.requirements}
        self.assertTrue(by_key["game.multiplayer"].required)
        self.assertTrue(by_key["game.matchmaking"].required)
        self.assertIn("game.multiplayer", {by_id[d].key for d in by_key["game.matchmaking"].dependency_ids})

    def test_integrations_are_derived_from_existing_unified_capabilities(self):
        keys = self.keys("Build a delivery app with maps, payments and chat messaging")
        self.assertIn("integration.maps", keys)
        self.assertIn("integration.payment", keys)
        self.assertIn("integration.messaging", keys)

    def test_requirement_ids_and_dependency_order_are_deterministic(self):
        first = build_plan("Build a 3D game")
        second = build_plan("Build a 3D game")
        self.assertEqual(first, second)
        CapabilityRegistry().validate_plan(first)
        ids = {r.id for r in first.requirements}
        self.assertEqual(len(ids), len(first.requirements))

    def test_brain_decision_exposes_capability_plan_without_breaking_old_fields(self):
        decision = OmniUniversalBrain().decide("Build an iOS booking app with payments")
        data = decision.to_dict()
        self.assertIn("plan", data)
        self.assertIn("agents", data)
        self.assertIn("creative", data)
        self.assertIn("rights", data)
        self.assertIn("principles", data)
        self.assertIn("capabilities", data)
        self.assertIn("requirements", data["capabilities"])
        self.assertIn("target.ios.source", {r.key for r in decision.capabilities.requirements})


if __name__ == "__main__":
    unittest.main()
