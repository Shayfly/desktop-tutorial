"""148AI Intelligence Control Plane (Wave A, 2026-10-11).

One governed layer over the existing execution adapters:

    inventory / prices / lifecycle  -> what models exist, what they cost, when they retire
    states                          -> separate credential / connection / verification / availability axes
    health                          -> durable provider circuit breakers (credit, auth, rate limit)
    task_policy                     -> which task class may use which model (quality floors)
    matrix                          -> generated PROVIDER_MATRIX.json + docs/PROVIDER_MATRIX.md

It does not replace `routed_gateway` (the working LLM router) or
`provider_router` (capability/media routing); both consume it.
"""
