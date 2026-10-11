"""Execution Graph Engine (Wave A §6.1-6.2, §12).

A plan is a DAG of PlanTasks. `ExecutionGraph` validates it before anything
runs or is paid for:

  * unique ids, known dependencies, no cycles (a bounded iterative step is ONE
    node with `max_iterations`, never a back edge)
  * dependency closure: every required skill exists in the skills registry and
    is allowed to the assigned agent (Agent OS PermissionEngine rules)
  * aggregate budget: the sum of every task's maximum authorized cost (times
    its iterations) must fit the graph budget; fan-out is capped, so a graph
    cannot authorize unbounded spend through many cheap tasks
  * missing prices are not zero: a task whose cost is unknown blocks the graph

It also answers the scheduling questions: which tasks can run now, which
layers may run in parallel, and which downstream tasks a failure invalidates
(only those; unaffected tasks are never rerun).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from decimal import Decimal

MAX_TASKS = 60          # fan-out cap per graph
SCHEMA = 'execution-graph/1'


@dataclass(frozen=True)
class PlanTask:
    task_id: str
    task_type: str
    department: str
    responsible_agent: str
    required_skills: tuple[str, ...]
    required_tools: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    dependencies: tuple[str, ...]
    inputs: tuple[str, ...]
    expected_outputs: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    verification_strategy: str
    complexity: str                       # low | medium | high
    estimated_cost_usd: Decimal
    maximum_authorized_cost_usd: Decimal | None   # None = unknown -> blocks
    retry_policy: str
    timeout_policy: str
    failure_policy: str                   # block_dependents | continue_advisory
    rollback_policy: str
    escalation_policy: str
    stage: str                            # binding to the build engine stage that performs it
    model_task: str | None = None         # task class for model routing (None = deterministic)
    max_iterations: int = 1               # >1 only for a bounded iterative node (repair)
    conditional: bool = False             # runs only when its trigger happens (repair)
    executable: bool = True               # False = capability gap: no engine can perform it today
    gap: str = ''

    def to_dict(self) -> dict:
        d = asdict(self)
        for k in ('estimated_cost_usd', 'maximum_authorized_cost_usd'):
            d[k] = None if d[k] is None else str(d[k])
        for k, v in d.items():
            if isinstance(v, tuple):
                d[k] = list(v)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> 'PlanTask':
        d = dict(d)
        for k in ('estimated_cost_usd', 'maximum_authorized_cost_usd'):
            d[k] = None if d.get(k) is None else Decimal(str(d[k]))
        for k in ('required_skills', 'required_tools', 'required_capabilities', 'dependencies', 'inputs',
                  'expected_outputs', 'acceptance_criteria'):
            d[k] = tuple(d.get(k) or ())
        return cls(**d)


class GraphInvalid(ValueError):
    def __init__(self, problems: list[str]):
        super().__init__('; '.join(problems))
        self.problems = problems


@dataclass
class ExecutionGraph:
    tasks: tuple[PlanTask, ...]
    budget_usd: Decimal
    schema: str = SCHEMA
    by_id: dict = field(init=False, repr=False)

    def __post_init__(self):
        self.by_id = {t.task_id: t for t in self.tasks}

    # ------------------------------------------------------------ validation
    def problems(self, *, agents=None, skills=None) -> list[str]:
        """agents: {agent_key: allowed_skills set}; skills: set of known skill keys."""
        out = []
        if len(self.by_id) != len(self.tasks):
            out.append('duplicate task ids')
        if len(self.tasks) > MAX_TASKS:
            out.append(f'{len(self.tasks)} tasks exceed the fan-out cap {MAX_TASKS}')
        for t in self.tasks:
            for d in t.dependencies:
                if d not in self.by_id:
                    out.append(f'{t.task_id}: unknown dependency {d}')
                if d == t.task_id:
                    out.append(f'{t.task_id}: depends on itself')
            if t.max_iterations < 1 or (t.max_iterations > 1 and t.max_iterations > 10):
                out.append(f'{t.task_id}: max_iterations must be 1..10')
            if t.maximum_authorized_cost_usd is None:
                out.append(f'{t.task_id}: maximum cost unknown (missing price is never zero)')
            elif t.estimated_cost_usd > t.maximum_authorized_cost_usd:
                out.append(f'{t.task_id}: estimate above its authorized maximum')
            if skills is not None:
                for s in t.required_skills:
                    if s not in skills:
                        out.append(f'{t.task_id}: skill {s} is not in the skills registry')
            if agents is not None:
                allowed = agents.get(t.responsible_agent)
                if allowed is None:
                    out.append(f'{t.task_id}: unknown agent {t.responsible_agent}')
                else:
                    for s in t.required_skills:
                        if s not in allowed:
                            out.append(f'{t.task_id}: agent {t.responsible_agent} may not use skill {s}')
        try:
            self.layers()
        except GraphInvalid as exc:
            out.extend(exc.problems)
        total = self.authorized_total()
        if total is not None and total > self.budget_usd:
            out.append(f'graph authorizes {total} > budget {self.budget_usd}')
        return out

    def validate(self, **kw) -> 'ExecutionGraph':
        problems = self.problems(**kw)
        if problems:
            raise GraphInvalid(problems)
        return self

    def authorized_total(self) -> Decimal | None:
        total = Decimal('0')
        for t in self.tasks:
            if t.maximum_authorized_cost_usd is None:
                return None
            total += t.maximum_authorized_cost_usd * t.max_iterations
        return total

    # ------------------------------------------------------------ scheduling
    def layers(self) -> list[list[str]]:
        """Kahn layers: tasks in one layer have all dependencies in earlier
        layers and may run concurrently."""
        indeg = {t.task_id: len([d for d in t.dependencies if d in self.by_id]) for t in self.tasks}
        children: dict[str, list[str]] = {t.task_id: [] for t in self.tasks}
        for t in self.tasks:
            for d in t.dependencies:
                if d in children:
                    children[d].append(t.task_id)
        layer = sorted(k for k, v in indeg.items() if v == 0)
        out, seen = [], 0
        while layer:
            out.append(layer)
            seen += len(layer)
            nxt = []
            for k in layer:
                for c in children[k]:
                    indeg[c] -= 1
                    if indeg[c] == 0:
                        nxt.append(c)
            layer = sorted(nxt)
        if seen != len(self.tasks):
            cyc = sorted(k for k, v in indeg.items() if v > 0)
            raise GraphInvalid([f'dependency cycle among {", ".join(cyc)}'])
        return out

    def order(self) -> list[str]:
        return [t for layer in self.layers() for t in layer]

    def ready(self, done: set[str], failed: set[str] = frozenset(), running: set[str] = frozenset()) -> list[str]:
        blocked = self.invalidated_by(failed)
        return [t.task_id for t in self.tasks if t.task_id not in done | set(failed) | set(running) | blocked
                and all(d in done for d in t.dependencies)]

    def descendants(self, task_id: str) -> set[str]:
        out, stack = set(), [task_id]
        while stack:
            cur = stack.pop()
            for t in self.tasks:
                if cur in t.dependencies and t.task_id not in out:
                    out.add(t.task_id)
                    stack.append(t.task_id)
        return out

    def invalidated_by(self, failed) -> set[str]:
        """Downstream tasks a failure invalidates (only through blocking edges)."""
        out = set()
        for f in failed:
            if f in self.by_id and self.by_id[f].failure_policy == 'block_dependents':
                out |= self.descendants(f)
        return out

    def critical_path(self) -> list[str]:
        """Longest dependency chain (by task count): the minimum sequential depth."""
        best: dict[str, list[str]] = {}
        for tid in self.order():
            t = self.by_id[tid]
            prev = max((best[d] for d in t.dependencies), key=len, default=[])
            best[tid] = prev + [tid]
        return max(best.values(), key=len, default=[])

    # ------------------------------------------------------------ identity
    def to_dict(self) -> dict:
        return {'schema': self.schema, 'budget_usd': str(self.budget_usd),
                'tasks': [t.to_dict() for t in self.tasks]}

    @classmethod
    def from_dict(cls, d: dict) -> 'ExecutionGraph':
        return cls(tuple(PlanTask.from_dict(t) for t in d['tasks']), Decimal(str(d['budget_usd'])), d.get('schema', SCHEMA))

    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()
