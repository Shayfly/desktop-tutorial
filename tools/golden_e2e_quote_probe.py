"""Golden E2E probe: would admission price a typical Web/SaaS build?

Runs the real ProductArchitect and the real production infrastructure
provisioner wiring against the given environment (default: the current
process environment), without network, database or provider calls, and
prints which contract requirements cannot be priced. A non-empty "unknown"
list means POST /api/v28/projects/{id}/builds answers 402 cost_quote_unknown
(Plan -> Quote fails) before any reservation or queue step.

    python3 tools/golden_e2e_quote_probe.py                       # Golden E2E #1 test product
    python3 tools/golden_e2e_quote_probe.py --prompt "Build ... with Postgres and email"

Infrastructure is demand-driven: the contract includes only what the product
asks for, so the default task tracker needs no managed infrastructure.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from omni_prod.build_cost_plan import CostQuoteUnknown, collect_build_cost_inputs  # noqa: E402
from omni_prod.infrastructure_provisioner import (  # noqa: E402
    InfrastructureProvisioningService, MemoryInfrastructureBindingRepository)
from omni_prod.product_architect import ProductArchitect  # noqa: E402
from omni_prod.providers.managed_web_saas import build_managed_web_saas_provisioner  # noqa: E402

PROMPT = ("Build a team task tracker web app: users sign up and log in, create projects, add tasks with "
          "title, due date and status, assign tasks to teammates, and see a dashboard of overdue tasks.")


def probe(env=None, prompt: str = PROMPT) -> dict:
    env = dict(os.environ if env is None else env)
    contract = ProductArchitect().compile(prompt, project_id='proj_probe', contract_version=1)
    service = InfrastructureProvisioningService(provisioner=build_managed_web_saas_provisioner(env=env),
                                                repository=MemoryInfrastructureBindingRepository())
    out = {
        'infrastructure_profile': contract.product_family,
        'contract_status': getattr(contract.status, 'value', str(contract.status)),
        'required_infrastructure': [f'{r.kind}:{r.connection_mode}' for r in contract.infrastructure if r.required],
        'required_capabilities': [r.key for r in contract.capability_plan.requirements if r.required],
    }
    try:
        from omni_prod.providers.image_provider import build_image_quote_resolver
        collect_build_cost_inputs(   # same arguments as admission (_m5_cost_inputs)
            contract, capability_assignments=build_image_quote_resolver(env)(contract.capability_plan),
            infrastructure_quotes=service.cost_quotes(contract, tenant_id='probe', project_id='proj_probe',
                                                      environment=env.get('OMNI_GENAPP_BUILD_ENVIRONMENT', 'preview')),
            require_capability_quotes=True, require_infrastructure_quotes=True)
        out['quote'] = 'PRICED'
        out['unknown'] = []
    except CostQuoteUnknown as exc:
        out['quote'] = 'UNKNOWN'
        out['unknown'] = list(exc.unknown)
    return out


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--prompt', default=PROMPT)
    print(json.dumps(probe(prompt=parser.parse_args().prompt), indent=2))
