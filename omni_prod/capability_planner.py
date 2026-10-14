from __future__ import annotations

from collections import OrderedDict

from .capabilities import CapabilityPlan, CapabilityRequirement
from .capability_registry import CapabilityRegistry
from .intent_terms import ai_agent_intent, has_term
from .media_pipeline import AssetKind


# Asset-generation capabilities: activated only when the creative plan requests
# them (decision 2026-10-07 #28).
ASSET_CAPABILITY_KEYS = {
    AssetKind.ICON: "media.image.generate",
    AssetKind.IMAGE: "media.image.generate",
    AssetKind.AUDIO: "media.audio.sfx",
    AssetKind.MUSIC: "media.audio.music",
    AssetKind.VOICE: "media.audio.tts",
    AssetKind.VIDEO: "media.video.generate",
    AssetKind.MODEL3D: "media.3d.mesh.generate",
    AssetKind.TEXTURE: "media.3d.texture",
}


def asset_capability_status(plan) -> dict[str, str]:
    """Build-level status per asset capability: REQUIRED, OPTIONAL or
    NOT_REQUIRED. NOT_REQUIRED is neither a failure nor a pass; it means the
    product did not ask for that asset and no provider is called for it."""
    in_plan = {r.key: r.required for r in getattr(plan, "requirements", ())}
    out = {}
    for key in sorted(set(ASSET_CAPABILITY_KEYS.values())):
        if key not in in_plan:
            out[key] = "NOT_REQUIRED"
        else:
            out[key] = "REQUIRED" if in_plan[key] else "OPTIONAL"
    return out


class CapabilityPlanner:
    """Compile deterministic product intent into a capability DAG.

    Model output may enrich constraints later, but this layer owns the minimum
    requirements that may never be silently removed.
    """

    def __init__(self, registry: CapabilityRegistry | None = None) -> None:
        self.registry = registry or CapabilityRegistry()

    def plan(self, *, prompt: str, unified_plan, creative_plan, semantic_decisions=()) -> CapabilityPlan:
        low = " ".join(prompt.lower().split())
        requested: OrderedDict[str, tuple[str, bool]] = OrderedDict()

        def add(key: str, purpose: str, required: bool = True) -> None:
            if not self.registry.contains(key):
                raise ValueError(f"planner requested unknown capability: {key}")
            if key in requested:
                old_purpose, old_required = requested[key]
                requested[key] = (old_purpose, old_required or required)
            else:
                requested[key] = (purpose, required)

        # Every real product build gets the same minimum software lifecycle.
        for key in (
            "software.plan",
            "software.architecture",
            "software.code.generate",
            "software.dependencies.install",
            "software.build",
            "software.test",
            "software.repair",
            "software.preview",
            "software.export",
        ):
            add(key, "minimum real-product build lifecycle")

        explicit_2d = any(term in low for term in ("2d game", "2-d game", "משחק 2d", "משחק דו ממד"))
        for target in unified_plan.targets:
            if target == "web":
                add("target.web", "web product target")
            elif target == "android":
                add("target.android.source", "Android source target")
                if self._has_any(low, "publish", "release", "signed", "play store", "aab", "פרסום", "חתום"):
                    add("target.android.build", "Android release/build target")
            elif target == "ios":
                add("target.ios.source", "iOS source target")
                if self._has_any(low, "publish", "release", "signed", "app store", "ipa", "פרסום", "חתום"):
                    add("target.ios.build", "iOS release/build target")
            elif target == "game3d" and not explicit_2d:
                add("target.game.3d", "3D game target")

        if explicit_2d:
            add("target.game.2d", "2D game target")
        if "saas" in low:
            add("target.saas", "SaaS product target")
        if self._has_any(low, "backend", "api", "rest api", "graphql", "שרת", "ממשק api"):
            add("target.backend", "backend/API target")
        if self._has_any(low, "database", "postgres", "mysql", "sqlite", "db", "מסד נתונים"):
            add("target.database", "database target")
        if self._has_any(low, "desktop", "windows app", "mac app", "electron", "תוכנת מחשב"):
            add("target.desktop.source", "desktop product target")
        if ai_agent_intent(low):
            add("target.agent", "AI agent product target")
            add("ai.agent.tools", "agent tool execution")
            if self._has_any(low, "memory", "persistent context", "long-term memory", "זיכרון"):
                add("ai.agent.memory", "agent persistent memory")
            add("ai.agent.eval", "agent evaluation", required=False)
        if self._has_any(low, "automation", "workflow", "zapier", "אוטומציה", "תהליך אוטומטי"):
            add("target.automation", "automation product target")

        asset_map = ASSET_CAPABILITY_KEYS
        for asset in creative_plan.requests:
            capability_key = asset_map.get(asset.kind)
            if capability_key:
                add(capability_key, asset.purpose, asset.required)

        if self._has_any(low, "speech to text", "stt", "transcrib", "microphone", "listens", "listen to", "תמלול", "מיקרופון", "מאזין"):
            add("media.audio.stt", "speech input/transcription")
        if self._has_any(low, "realtime voice", "real-time voice", "live voice", "voice chat", "שיחה קולית", "קול בזמן אמת"):
            add("media.audio.realtime_voice", "real-time bidirectional voice")

        if self._has_any(low, "multiplayer", "multi-player", "online multiplayer", "רב משתתפים", "מרובה משתתפים"):
            add("game.multiplayer", "multiplayer gameplay")
        if self._has_any(low, "matchmaking", "match making", "lobby", "שידוך שחקנים", "לובי"):
            add("game.matchmaking", "player matchmaking")

        unified_capability_map = {
            "maps": "integration.maps",
            "payments": "integration.payment",
            "messaging": "integration.messaging",
        }
        for capability in unified_plan.capabilities:
            mapped = unified_capability_map.get(capability)
            if mapped:
                add(mapped, f"integration required by {capability}")

        if self._has_any(low, "github", "gitlab", "source control", "git repo"):
            add("integration.source_control", "source control integration")
        if self._has_any(low, "oauth", "google login", "google sign-in", "apple login", "sign in with apple"):
            add("integration.oauth", "OAuth identity integration")
        if self._has_any(low, "analytics", "telemetry", "product analytics"):
            add("integration.analytics", "analytics integration")

        if self._has_any(low, "publish", "deploy", "go live", "production url", "פרסם", "העלה לאוויר"):
            add("software.deploy.web", "requested production web deployment")
            add("publish.web", "requested public web publishing")

        # Only the confirmed, evidence-validated semantic decisions bound into
        # the approved Brief may amend ambiguous keyword interpretations.
        # This acts BEFORE DAG dependency closure and keeps the same registries.
        from .semantic_capabilities import overrides
        semantic = overrides(semantic_decisions, prompt=prompt)
        for key, outcome in semantic.items():
            if not self.registry.contains(key):
                continue
            if outcome == "not_required":
                requested.pop(key, None)
            elif outcome == "required":
                add(key, "approved semantic customer intent")
        # An agent requirement cannot survive removing its whole target.
        if semantic.get("target.agent") == "not_required":
            for key in ("ai.agent.tools", "ai.agent.eval", "ai.agent.memory"):
                if semantic.get(key) != "required":
                    requested.pop(key, None)

        # Requiredness propagates backwards through definition dependencies so an
        # optional child never makes a dependency mandatory unless another required
        # request needs it.
        required_by_key = {key: required for key, (_, required) in requested.items()}
        changed = True
        while changed:
            changed = False
            for key, required in tuple(required_by_key.items()):
                for dependency in self.registry.get(key).dependency_keys:
                    previous = required_by_key.get(dependency, False)
                    next_value = previous or required
                    if dependency not in required_by_key or next_value != previous:
                        required_by_key[dependency] = next_value
                        changed = True

        ordered_keys = self.registry.dependency_closure(tuple(requested))
        id_by_key = {key: self._requirement_id(key) for key in ordered_keys}
        requirements = []
        for key in ordered_keys:
            definition = self.registry.get(key)
            purpose, explicit_required = requested.get(
                key, (f"dependency required by capability DAG for {key}", False)
            )
            requirements.append(
                CapabilityRequirement(
                    id=id_by_key[key],
                    key=key,
                    purpose=purpose,
                    required=required_by_key.get(key, explicit_required),
                    dependency_ids=tuple(id_by_key[dep] for dep in definition.dependency_keys),
                )
            )

        target_keys = tuple(key for key in ordered_keys if key.startswith("target."))
        result = CapabilityPlan(
            requirements=tuple(requirements),
            target_keys=target_keys,
            notes=("deterministic-minimum-requirements",) + (("approved-semantic-evidence",) if semantic else ()),
        )
        self.registry.validate_plan(result)
        return result

    @staticmethod
    def _has_any(text: str, *terms: str) -> bool:
        # Token-aware: "api" must not match "rapid", "db" must not match "feedback".
        return has_term(text, *terms)

    @staticmethod
    def _requirement_id(key: str) -> str:
        return "cap-" + key.replace(".", "-")
