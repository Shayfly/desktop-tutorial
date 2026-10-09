"""Commercial provider safety (autonomous completion directive §19).

Approval is per provider + model + endpoint + plan. States:
  COMMERCIAL_APPROVED  paid API plan whose terms allow commercial use of outputs
                       and do not use prompts to train (as of the basis date)
  CONDITIONAL          allowed only when the stated condition holds
  DEV_ONLY             free/experimental plans -- never customer traffic
  BLOCKED              never

The model router drops DEV_ONLY and BLOCKED catalog entries before routing
(`filter_routable`), so customer work can never reach them. The basis notes
say what the status rests on; re-check them when a plan or term changes.
"""
from __future__ import annotations

COMMERCIAL_APPROVED, CONDITIONAL, DEV_ONLY, BLOCKED = 'COMMERCIAL_APPROVED', 'CONDITIONAL', 'DEV_ONLY', 'BLOCKED'

# prefix of the catalog entry name -> (status, plan, basis)
RULES: tuple[tuple[str, str, str, str], ...] = (
    ('gemini-', COMMERCIAL_APPROVED, 'Gemini API paid tier (billing enabled by the founder, Tier 1, 2026-10-08)',
     'paid-tier terms: outputs usable commercially; paid-tier prompts are not used to improve products'),
    ('openai-', COMMERCIAL_APPROVED, 'OpenAI API (pay-as-you-go)', 'API terms: customer owns outputs; API data not used for training by default'),
    ('anthropic-', COMMERCIAL_APPROVED, 'Anthropic API (commercial terms)', 'commercial terms: outputs owned by the customer; no training on API data by default'),
    ('replicate-', CONDITIONAL, 'Replicate per-model licence', 'allowed only for models whose licence permits commercial use (checked per model)'),
    ('local-', DEV_ONLY, 'self-hosted development model', 'not part of the customer path'),
)


def commercial_status(name: str) -> tuple[str, str, str]:
    """(status, plan, basis) for a catalog entry name; unknown -> CONDITIONAL."""
    low = (name or '').lower()
    for prefix, status, plan, basis in RULES:
        if low.startswith(prefix):
            return status, plan, basis
    return CONDITIONAL, 'unknown plan', 'no rule: allowed only after a manual terms check'


def filter_routable(entries, name_of=lambda e: getattr(getattr(e, 'endpoint', None), 'name', '')) -> tuple:
    """Catalog entries customer work may use (drops DEV_ONLY and BLOCKED)."""
    return tuple(e for e in entries if commercial_status(name_of(e))[0] not in (DEV_ONLY, BLOCKED))
