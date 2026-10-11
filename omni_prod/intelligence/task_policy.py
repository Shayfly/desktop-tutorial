"""Task classes and model eligibility (Wave A §2, §5.3, §6.3, §11).

Before Wave A only codegen/repair/modification/review had a quality floor;
every other task (including `architecture`) defaulted to floor 0, so with
cost-first routing the cheapest model won the architecture call. Every task
class is now explicit:

  preferred_floor   models at or above it are tried first (cheapest first)
  mandatory_floor   models below it are NEVER used for this task, not even as
                    escalation: the call fails instead of silently degrading
  allow_models      optional allow-list (model ids), e.g. intake conversation
  require_independent_of   tasks whose authoring models must not review

Unknown task names get the strictest generic policy ('general'), never 0.
OMNI_MODEL_TASK_MIN_QUALITY (JSON) still overrides preferred floors (ops knob);
mandatory floors are not overridable by environment.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskClass:
    key: str
    description: str
    preferred_floor: int
    mandatory_floor: int
    allow_models: tuple[str, ...] = ()
    require_independent_of: tuple[str, ...] = ()
    deterministic_first: bool = False   # a parser/validator answers it when possible

    def __post_init__(self):
        if not 0 <= self.mandatory_floor <= self.preferred_floor <= 100:
            raise ValueError(f'{self.key}: floors must satisfy 0 <= mandatory <= preferred <= 100')


TASK_CLASSES: dict[str, TaskClass] = {t.key: t for t in (
    TaskClass('general', 'unclassified call (strict default)', 70, 70),
    TaskClass('classification', 'route a change request / intent', 70, 70),
    TaskClass('conversation', 'customer intake dialogue (Hebrew/English)', 70, 70),
    TaskClass('intake_extraction', 'structured requirements from the dialogue', 70, 70, deterministic_first=True),
    TaskClass('architecture', 'architecture + plan for the build', 85, 70),
    TaskClass('codegen', 'write the product code', 85, 70),
    TaskClass('repair', 'fix failing checks', 85, 70),
    TaskClass('modification', 'change an existing product', 85, 70),
    TaskClass('review', 'QA review of generated code', 85, 70, require_independent_of=('codegen', 'repair', 'modification')),
    TaskClass('security_review', 'security review', 85, 85, require_independent_of=('codegen', 'repair', 'modification')),
)}

# The floors that existed before Wave A (codegen/repair/modification/review
# 85, preferred) are unchanged; the mandatory 70 equals the catalog minimum
# quality the worker already enforced (OMNI_MODEL_MIN_QUALITY=70), so builds
# keep exactly their verified routing while escalation stays explicit.


def task_class(task: str | None) -> TaskClass:
    return TASK_CLASSES.get(task or 'general', TASK_CLASSES['general'])


def eligible(task: str, *, model_id: str, quality: int) -> bool:
    tc = task_class(task)
    if quality < tc.mandatory_floor:
        return False
    return not tc.allow_models or model_id in tc.allow_models


def describe() -> list[dict]:
    return [{'task': t.key, 'description': t.description, 'preferred_floor': t.preferred_floor,
             'mandatory_floor': t.mandatory_floor, 'allow_models': list(t.allow_models),
             'independent_of': list(t.require_independent_of), 'deterministic_first': t.deterministic_first}
            for t in TASK_CLASSES.values()]
