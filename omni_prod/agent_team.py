from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum

class AgentRole(str, Enum):
    PRODUCT='product'
    ARCHITECT='architect'
    UX='ux'
    FRONTEND='frontend'
    BACKEND='backend'
    DATABASE='database'
    MOBILE='mobile'
    GAME='game'
    QA='qa'
    SECURITY='security'
    DEVOPS='devops'
    COST='cost'

DEFAULT_TEAM = tuple(AgentRole)

@dataclass(frozen=True)
class AgentTask:
    role: AgentRole
    objective: str
    required_inputs: tuple[str,...]=()
    outputs: tuple[str,...]=()

@dataclass(frozen=True)
class TeamPlan:
    tasks: tuple[AgentTask,...]
    reviewers: tuple[AgentRole,...]
    def to_dict(self): return {'tasks':[{'role':x.role.value,'objective':x.objective,'required_inputs':list(x.required_inputs),'outputs':list(x.outputs)} for x in self.tasks],'reviewers':[x.value for x in self.reviewers]}

def plan_team(*, target: str, has_ui: bool=True, has_mobile: bool=False, has_game: bool=False) -> TeamPlan:
    tasks=[
        AgentTask(AgentRole.PRODUCT,'turn intent into measurable product outcomes',(),('spec',)),
        AgentTask(AgentRole.ARCHITECT,'design system boundaries and stack',('spec',),('architecture',)),
    ]
    if has_ui: tasks.append(AgentTask(AgentRole.UX,'design accessible responsive experience',('spec',),('design-system','user-flows')))
    tasks.extend([
        AgentTask(AgentRole.BACKEND,'implement service/domain APIs',('architecture',),('backend',)),
        AgentTask(AgentRole.DATABASE,'design migrations and data integrity',('architecture',),('schema',)),
        AgentTask(AgentRole.FRONTEND,'implement product UI',('design-system','backend'),('frontend',)),
    ])
    if has_mobile: tasks.append(AgentTask(AgentRole.MOBILE,'produce Android/iOS source and build contracts',('architecture',),('mobile',)))
    if has_game: tasks.append(AgentTask(AgentRole.GAME,'produce gameplay/engine architecture and assets contract',('architecture',),('game',)))
    tasks.extend([
        AgentTask(AgentRole.QA,'verify acceptance criteria and regressions',('spec',),('test-report',)),
        AgentTask(AgentRole.SECURITY,'threat-model and attack generated output',('architecture',),('security-report',)),
        AgentTask(AgentRole.DEVOPS,'prepare deployment/rollback/observability',('architecture',),('delivery-plan',)),
        AgentTask(AgentRole.COST,'enforce compute and model budget',('spec',),('cost-plan',)),
    ])
    return TeamPlan(tuple(tasks),(AgentRole.ARCHITECT,AgentRole.QA,AgentRole.SECURITY))
