from __future__ import annotations
from dataclasses import dataclass
from .unified_engine import UnifiedPromptPlanner, UnifiedPlan
from .agent_team import plan_team
from .media_pipeline import CreativeDirector, CreativePlan
from .rights_ip import RightsEngine, RightsAssessment

@dataclass(frozen=True)
class BrainDecision:
    plan: UnifiedPlan
    agents: dict
    creative: CreativePlan
    rights: RightsAssessment
    principles: tuple[str, ...]

    def to_dict(self):
        return {
            'plan': self.plan.to_dict(),
            'agents': self.agents,
            'creative': self.creative.to_dict(),
            'rights': self.rights.to_dict(),
            'principles': list(self.principles),
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

    def decide(self, prompt: str, *, target_markets: tuple[str, ...] = ('US', 'EU', 'IL')) -> BrainDecision:
        plan = self.planner.plan(prompt)
        agents = plan_team(
            target='web', has_ui=True,
            has_mobile=('android' in plan.targets or 'ios' in plan.targets),
            has_game=('game3d' in plan.targets),
        ).to_dict()
        creative = self.creative.plan(prompt, targets=plan.targets)
        low = prompt.lower()
        synthetic_person_media = any(x in low for x in ('voice of', 'face of', 'likeness of', 'digital replica', 'בקול של', 'פנים של', 'דמות של'))
        rights = self.rights.assess(prompt, target_markets=target_markets, synthetic_person_media=synthetic_person_media)
        return BrainDecision(
            plan, agents, creative, rights,
            (
                'user-owns-project', 'tenant-isolation', 'local-first-models',
                'verify-before-claim', 'version-every-change', 'accessibility-by-default',
                'rights-aware-assets', 'provenance-by-default', 'no-small-change-evasion',
            ),
        )
