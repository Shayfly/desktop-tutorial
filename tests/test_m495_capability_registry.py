import unittest

from omni_prod.capabilities import (
    CapabilityDefinition,
    CapabilityPlan,
    CapabilityRequirement,
    CapabilityStatus,
)
from omni_prod.capability_registry import CapabilityRegistry, CANONICAL_CAPABILITY_KEYS


EXPECTED_KEYS = {
    # Software lifecycle
    "software.plan", "software.architecture", "software.code.generate",
    "software.code.modify", "software.dependencies.install", "software.build",
    "software.test", "software.repair", "software.preview", "software.export",
    "software.deploy.web",
    # Product targets
    "target.web", "target.saas", "target.backend", "target.database",
    "target.android.source", "target.android.build", "target.ios.source",
    "target.ios.build", "target.desktop.source", "target.agent",
    "target.automation", "target.game.2d", "target.game.3d",
    # Image / 2D
    "media.image.generate", "media.image.edit", "media.image.remove_background",
    "media.image.upscale", "media.vector.generate", "media.texture.generate",
    "media.sprite.generate",
    # 3D / animation
    "media.3d.mesh.generate", "media.3d.texture", "media.3d.multiview",
    "media.3d.retopology", "media.3d.optimize", "media.3d.rig",
    "media.3d.animate", "media.3d.retarget", "media.3d.export",
    "media.3d.scene.compose",
    # Audio / voice / music
    "media.audio.sfx", "media.audio.music", "media.audio.tts", "media.audio.stt",
    "media.audio.realtime_voice", "media.audio.dubbing", "media.audio.cleanup",
    # Video / film
    "media.video.generate", "media.video.edit", "media.video.lipsync",
    "media.video.captions", "media.video.upscale", "media.film.storyboard",
    "media.film.shot_plan", "media.film.render",
    # AI/data
    "ai.embedding", "ai.rag.ingest", "ai.rag.retrieve", "ai.agent.tools",
    "ai.agent.memory", "ai.agent.eval",
    # Integrations
    "integration.payment", "integration.email", "integration.sms",
    "integration.messaging", "integration.maps", "integration.storage",
    "integration.database", "integration.source_control", "integration.oauth",
    "integration.analytics", "integration.webhook",
    # Publishing/ecosystem
    "publish.web", "publish.android", "publish.ios", "publish.asset",
    "ecosystem.discover", "ecosystem.creator_profile", "ecosystem.like",
    "ecosystem.comment", "ecosystem.follow", "ecosystem.remix",
    "ecosystem.marketplace", "ecosystem.revenue_share", "game.multiplayer",
    "game.matchmaking",
}


class CapabilityContractTests(unittest.TestCase):
    def test_status_vocabulary_is_exact(self):
        self.assertEqual(
            [item.value for item in CapabilityStatus],
            ["LIVE", "PARTIAL", "NOT_CONFIGURED", "NOT_IMPLEMENTED", "BLOCKED"],
        )

    def test_requirement_quantity_must_be_positive(self):
        with self.assertRaises(ValueError):
            CapabilityRequirement(
                id="r1", key="software.build", purpose="build", required=True, quantity=0
            )


class CapabilityRegistryTests(unittest.TestCase):
    def test_canonical_registry_contains_every_spec_taxonomy_key(self):
        registry = CapabilityRegistry()
        self.assertEqual(set(CANONICAL_CAPABILITY_KEYS), EXPECTED_KEYS)
        self.assertEqual({item.key for item in registry.all()}, EXPECTED_KEYS)

    def test_duplicate_definition_keys_are_rejected(self):
        duplicate = CapabilityDefinition("x", "test", "one")
        with self.assertRaisesRegex(ValueError, "duplicate capability key"):
            CapabilityRegistry((duplicate, duplicate))

    def test_unknown_get_is_explicit(self):
        registry = CapabilityRegistry()
        self.assertFalse(registry.contains("does.not.exist"))
        with self.assertRaisesRegex(KeyError, "does.not.exist"):
            registry.get("does.not.exist")

    def test_dependency_closure_is_dependency_first_and_deterministic(self):
        registry = CapabilityRegistry(
            (
                CapabilityDefinition("a", "test", "a"),
                CapabilityDefinition("b", "test", "b", dependency_keys=("a",)),
                CapabilityDefinition("c", "test", "c", dependency_keys=("b",)),
            )
        )
        self.assertEqual(registry.dependency_closure(("c",)), ("a", "b", "c"))
        self.assertEqual(registry.dependency_closure(("c", "b")), ("a", "b", "c"))

    def test_definition_dependency_cycle_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "cycle"):
            CapabilityRegistry(
                (
                    CapabilityDefinition("a", "test", "a", dependency_keys=("b",)),
                    CapabilityDefinition("b", "test", "b", dependency_keys=("a",)),
                )
            )

    def test_validate_plan_rejects_unknown_capability(self):
        registry = CapabilityRegistry()
        plan = CapabilityPlan(
            requirements=(
                CapabilityRequirement(
                    id="r1", key="missing.capability", purpose="x", required=True
                ),
            ),
            target_keys=(),
        )
        with self.assertRaisesRegex(ValueError, "unknown capability"):
            registry.validate_plan(plan)

    def test_validate_plan_rejects_unknown_dependency_id(self):
        registry = CapabilityRegistry()
        plan = CapabilityPlan(
            requirements=(
                CapabilityRequirement(
                    id="r1", key="software.plan", purpose="x", required=True,
                    dependency_ids=("missing-id",),
                ),
            ),
            target_keys=(),
        )
        with self.assertRaisesRegex(ValueError, "unknown dependency id"):
            registry.validate_plan(plan)

    def test_validate_plan_rejects_requirement_cycle(self):
        registry = CapabilityRegistry()
        plan = CapabilityPlan(
            requirements=(
                CapabilityRequirement(
                    id="r1", key="software.plan", purpose="a", required=True,
                    dependency_ids=("r2",),
                ),
                CapabilityRequirement(
                    id="r2", key="software.architecture", purpose="b", required=True,
                    dependency_ids=("r1",),
                ),
            ),
            target_keys=("target.web",),
        )
        with self.assertRaisesRegex(ValueError, "cycle"):
            registry.validate_plan(plan)

    def test_validate_plan_rejects_unknown_target_key(self):
        registry = CapabilityRegistry()
        plan = CapabilityPlan(requirements=(), target_keys=("target.nope",))
        with self.assertRaisesRegex(ValueError, "unknown target capability"):
            registry.validate_plan(plan)


if __name__ == "__main__":
    unittest.main()
