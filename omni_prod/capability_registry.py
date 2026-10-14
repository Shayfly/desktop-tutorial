from __future__ import annotations

from collections.abc import Iterable

from .capabilities import CapabilityDefinition, CapabilityPlan


CANONICAL_CAPABILITY_KEYS: tuple[str, ...] = (
    # Software lifecycle
    "software.plan",
    "software.architecture",
    "software.code.generate",
    "software.code.modify",
    "software.dependencies.install",
    "software.build",
    "software.test",
    "software.repair",
    "software.preview",
    "software.export",
    "software.deploy.web",
    # Product targets
    "target.web",
    "target.saas",
    "target.backend",
    "target.database",
    "target.android.source",
    "target.android.build",
    "target.ios.source",
    "target.ios.build",
    "target.desktop.source",
    "target.agent",
    "target.automation",
    "target.game.2d",
    "target.game.3d",
    # Image / 2D
    "media.image.generate",
    "media.image.edit",
    "media.image.remove_background",
    "media.image.upscale",
    "media.vector.generate",
    "media.texture.generate",
    "media.sprite.generate",
    # 3D / animation
    "media.3d.mesh.generate",
    "media.3d.texture",
    "media.3d.multiview",
    "media.3d.retopology",
    "media.3d.optimize",
    "media.3d.rig",
    "media.3d.animate",
    "media.3d.retarget",
    "media.3d.export",
    "media.3d.scene.compose",
    # Audio / voice / music
    "media.audio.sfx",
    "media.audio.music",
    "media.audio.tts",
    "media.audio.stt",
    "media.audio.realtime_voice",
    "media.audio.dubbing",
    "media.audio.cleanup",
    # Video / film
    "media.video.generate",
    "media.video.edit",
    "media.video.lipsync",
    "media.video.captions",
    "media.video.upscale",
    "media.film.storyboard",
    "media.film.shot_plan",
    "media.film.render",
    # AI/data product capabilities
    "ai.embedding",
    "ai.rag.ingest",
    "ai.rag.retrieve",
    "ai.agent.tools",
    "ai.agent.memory",
    "ai.agent.eval",
    # Integrations
    "integration.payment",
    "integration.email",
    "integration.sms",
    "integration.messaging",
    "integration.maps",
    "integration.storage",
    "integration.database",
    "integration.source_control",
    "integration.oauth",
    "integration.analytics",
    "integration.webhook",
    # Publishing / ecosystem
    "publish.web",
    "publish.android",
    "publish.ios",
    "publish.asset",
    "ecosystem.discover",
    "ecosystem.creator_profile",
    "ecosystem.like",
    "ecosystem.comment",
    "ecosystem.follow",
    "ecosystem.remix",
    "ecosystem.marketplace",
    "ecosystem.revenue_share",
    "game.multiplayer",
    "game.matchmaking",
)


_SOFTWARE_DEPS: dict[str, tuple[str, ...]] = {
    "software.architecture": ("software.plan",),
    "software.code.generate": ("software.architecture",),
    "software.dependencies.install": ("software.code.generate",),
    "software.build": ("software.dependencies.install",),
    "software.test": ("software.build",),
    "software.repair": ("software.test",),
    "software.preview": ("software.build",),
    "software.export": ("software.test",),
    "software.deploy.web": ("software.export",),
}

_3D_DEPS: dict[str, tuple[str, ...]] = {
    "media.3d.texture": ("media.3d.mesh.generate",),
    "media.3d.multiview": ("media.3d.mesh.generate",),
    "media.3d.retopology": ("media.3d.mesh.generate",),
    "media.3d.optimize": ("media.3d.mesh.generate",),
    "media.3d.rig": ("media.3d.mesh.generate",),
    "media.3d.animate": ("media.3d.rig",),
    "media.3d.retarget": ("media.3d.rig",),
    "media.3d.export": ("media.3d.mesh.generate",),
    "media.3d.scene.compose": ("media.3d.mesh.generate", "media.3d.texture"),
}

_OTHER_DEPS: dict[str, tuple[str, ...]] = {
    "ai.rag.retrieve": ("ai.rag.ingest",),
    "game.matchmaking": ("game.multiplayer",),
}


def _family_for(key: str) -> str:
    if key.startswith("media.3d."):
        return "media.3d"
    if key.startswith("media.image.") or key.startswith("media.vector.") or key.startswith("media.texture.") or key.startswith("media.sprite."):
        return "media.2d"
    if key.startswith("media.audio."):
        return "media.audio"
    if key.startswith("media.video.") or key.startswith("media.film."):
        return "media.video"
    return key.split(".", 1)[0]


def _provider_backed(key: str) -> bool:
    return key.startswith(("media.", "ai.")) or key in {
        "software.plan",
        "software.architecture",
        "software.code.generate",
        "software.code.modify",
        "software.repair",
    }


def _canonical_definitions() -> tuple[CapabilityDefinition, ...]:
    dependencies = {**_SOFTWARE_DEPS, **_3D_DEPS, **_OTHER_DEPS}
    return tuple(
        CapabilityDefinition(
            key=key,
            family=_family_for(key),
            description=key.replace(".", " "),
            dependency_keys=dependencies.get(key, ()),
            provider_backed=_provider_backed(key),
        )
        for key in CANONICAL_CAPABILITY_KEYS
    )


class CapabilityRegistry:
    def __init__(self, definitions: Iterable[CapabilityDefinition] | None = None) -> None:
        source = tuple(definitions) if definitions is not None else _canonical_definitions()
        by_key: dict[str, CapabilityDefinition] = {}
        for definition in source:
            if definition.key in by_key:
                raise ValueError(f"duplicate capability key: {definition.key}")
            by_key[definition.key] = definition
        self._definitions = source
        self._by_key = by_key
        self._validate_definition_dependencies()

    def get(self, key: str) -> CapabilityDefinition:
        try:
            return self._by_key[key]
        except KeyError as exc:
            raise KeyError(f"unknown capability key: {key}") from exc

    def contains(self, key: str) -> bool:
        return key in self._by_key

    def all(self) -> tuple[CapabilityDefinition, ...]:
        return self._definitions

    def dependency_closure(self, keys: tuple[str, ...]) -> tuple[str, ...]:
        result: list[str] = []
        emitted: set[str] = set()
        visiting: set[str] = set()

        def visit(key: str) -> None:
            if key in emitted:
                return
            if key in visiting:
                raise ValueError(f"capability dependency cycle at {key}")
            definition = self.get(key)
            visiting.add(key)
            for dependency in definition.dependency_keys:
                visit(dependency)
            visiting.remove(key)
            emitted.add(key)
            result.append(key)

        for key in keys:
            visit(key)
        return tuple(result)

    def validate_plan(self, plan: CapabilityPlan) -> None:
        for target_key in plan.target_keys:
            if not self.contains(target_key):
                raise ValueError(f"unknown target capability: {target_key}")

        by_id = {}
        for requirement in plan.requirements:
            if requirement.id in by_id:
                raise ValueError(f"duplicate capability requirement id: {requirement.id}")
            if not self.contains(requirement.key):
                raise ValueError(f"unknown capability: {requirement.key}")
            by_id[requirement.id] = requirement

        for requirement in plan.requirements:
            for dependency_id in requirement.dependency_ids:
                if dependency_id not in by_id:
                    raise ValueError(
                        f"unknown dependency id {dependency_id} for requirement {requirement.id}"
                    )

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(requirement_id: str) -> None:
            if requirement_id in visited:
                return
            if requirement_id in visiting:
                raise ValueError(f"capability requirement cycle at {requirement_id}")
            visiting.add(requirement_id)
            for dependency_id in by_id[requirement_id].dependency_ids:
                visit(dependency_id)
            visiting.remove(requirement_id)
            visited.add(requirement_id)

        for requirement_id in by_id:
            visit(requirement_id)

    def _validate_definition_dependencies(self) -> None:
        for definition in self._definitions:
            for dependency in definition.dependency_keys:
                if dependency not in self._by_key:
                    raise ValueError(
                        f"unknown dependency capability {dependency} for {definition.key}"
                    )
        # This also rejects cycles in definition-level dependencies.
        self.dependency_closure(tuple(self._by_key))
