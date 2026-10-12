"""Agent & Skill Router (Wave A §2, §6.1).

For one plan task: confirm the agent is registered and executable, that it is
permitted every required skill (the same rules the AgentRuntime
PermissionEngine enforces at execution), which department owns it, and which
models may serve its model task right now (Provider Matrix: in the worker
catalog, AVAILABLE, eligible for the task class -- cheapest first, but never
below the mandatory floor). The router does not call models; the routed
gateway makes the final per-call choice with live health and budget.
"""
from __future__ import annotations

from ..agent_os.departments import department_of
from . import registry_view as R


class AgentSkillRouter:
    def assign(self, task) -> dict:
        problems = []
        agent = task.responsible_agent
        status = R.agent_status(agent)
        allowed = R.allowed_skills().get(agent)
        if allowed is None:
            problems.append(f'agent {agent} not registered')
        else:
            problems += [f'skill {s} not allowed to {agent}' for s in task.required_skills if s not in allowed]
        skill_status = {s: R.skill_status(s) for s in task.required_skills}
        problems += [f'skill {s} is {st}' for s, st in skill_status.items() if st not in R.EXECUTABLE]
        if status not in R.EXECUTABLE:
            problems.append(f'agent {agent} is {status}')
        models = []
        if task.model_task:
            ms = R.models_for(task.model_task)
            ms.sort(key=lambda m: (-(m.get('catalog_quality') or 0) if task.model_task in ('architecture', 'codegen', 'repair',
                                                                                            'modification', 'review', 'security_review')
                                   else 0, float((m.get('price_in_force') or {}).get('output_per_million') or 1e9)))
            models = [m['provider_model_id'] for m in ms]
            if not models:
                problems.append(f'no available model for task class {task.model_task}')
        return {
            'task_id': task.task_id, 'department': department_of(agent) or 'UNASSIGNED', 'agent': agent,
            'agent_status': status, 'skills': skill_status, 'tools': list(task.required_tools),
            'model_task': task.model_task, 'model_candidates': models,
            'executable': task.executable and not problems, 'problems': problems + ([task.gap] if task.gap else []),
        }

