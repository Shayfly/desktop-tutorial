from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from .unified_engine import UnifiedPromptPlanner, UnifiedPlan
from .agent_team import plan_team
from .media_pipeline import CreativeDirector, CreativePlan
from .rights_ip import RightsEngine, RightsAssessment
from .capabilities import CapabilityPlan
from .capability_planner import CapabilityPlanner
from .capability_registry import CapabilityRegistry

@dataclass(frozen=True)
class BrainDecision:
    plan: UnifiedPlan
    agents: dict
    creative: CreativePlan
    rights: RightsAssessment
    principles: tuple[str, ...]
    capabilities: CapabilityPlan

    @property
    def capability_plan_fingerprint(self) -> str:
        payload = json.dumps(self.capabilities.to_dict(), sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        return 'sha256:' + sha256(payload.encode('utf-8')).hexdigest()

    def to_dict(self):
        return {
            'plan': self.plan.to_dict(),
            'agents': self.agents,
            'creative': self.creative.to_dict(),
            'rights': self.rights.to_dict(),
            'principles': list(self.principles),
            'capabilities': self.capabilities.to_dict(),
            'capability_plan_fingerprint': self.capability_plan_fingerprint,
        }

class OmniUniversalBrain:
    """Deterministic safety/coverage brain in front of model-driven generation.

    A live model may enrich implementation detail, but cannot silently remove
    explicit requested targets, security requirements, asset obligations or
    rights/IP blockers discovered by deterministic policy.
    """
    def __init__(self):
        self.planner = UnifiedPromptPlanner()
        self.creative = CreativeDirector()
        self.rights = RightsEngine()
        self.capability_planner = CapabilityPlanner(CapabilityRegistry())

    def decide(self, prompt: str, *, target_markets: tuple[str, ...] = ('US', 'EU', 'IL'), semantic_decisions=()) -> BrainDecision:
        plan = self.planner.plan(prompt)
        agents = plan_team(
            target='web', has_ui=True,
            has_mobile=('android' in plan.targets or 'ios' in plan.targets),
            has_game=('game3d' in plan.targets),
        ).to_dict()
        creative = self.creative.plan(prompt, targets=plan.targets)
        # Honor semantic disambiguation in the asset manifest as well as the
        # provider/capability DAG: no unrequested narration from a font name.
        from .semantic_capabilities import overrides
        from .media_pipeline import AssetKind, CreativePlan
        denied = overrides(semantic_decisions)
        suppressed = {"media.audio.tts": AssetKind.VOICE,
                      "media.image.generate": AssetKind.IMAGE,
                      "media.video.generate": AssetKind.VIDEO}
        banned_kinds = {kind for key, kind in suppressed.items()
                        if denied.get(key) == "not_required"}
        if banned_kinds:
            creative = CreativePlan(
                tuple(a for a in creative.requests if a.kind not in banned_kinds),
                creative.accessibility, creative.rights_policy)
        low = prompt.lower()
        synthetic_person_media = any(x in low for x in ('voice of', 'face of', 'likeness of', 'digital replica', 'בקול של', 'פנים של', 'דמות של'))
        rights = self.rights.assess(prompt, target_markets=target_markets, synthetic_person_media=synthetic_person_media)
        capabilities = self.capability_planner.plan(
            prompt=prompt, unified_plan=plan, creative_plan=creative,
            semantic_decisions=semantic_decisions
        )
        return BrainDecision(
            plan, agents, creative, rights,
            (
                'user-owns-project', 'tenant-isolation', 'local-first-models',
                'verify-before-claim', 'version-every-change', 'accessibility-by-default',
                'rights-aware-assets', 'provenance-by-default', 'no-small-change-evasion',
            ),
            capabilities,
        )
