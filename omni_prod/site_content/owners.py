"""Who owns a failed check on the content-document route (the CTO's decision 5; Proposal 3's OWNER table, judges 1-3).

Every acceptance id the executor chain can produce has exactly one owner, written out below -- no default bucket:
  content   the model's copy: a narrow rewrite of the JSON paths the finding points at (agents.ContentSiteRepairer)
  platform  the library, the fact sheet, the fixed app/tests/manifest, or a check that crashed: the build stops on its
            best version through RepairDeclined('platform_render_defect'), with no paid round; it is a library bug
  customer  a fact only the customer can give (fact_canon.needs_customer_input): needs_customer_input, as today
  advisory  the design critic's must_fix, the model reviewer's free text, the engine's own notes to a repairer:
            recorded as library feedback in the evidence, never a decline and never a repair
tests/test_site_content_owners.py fails when an id the chain can produce (every WORKER_GATES unit, every failure-id
constant in omni_prod, every layer suffix, every spec requirement id) has no owner here. An id that reaches the
route at run time with no owner stops the build loudly (RepairDeclined('unowned_finding')), never a guess.

REVIEW holds two kinds of finding under one id: the static truth gate and other static checks (skills_runtime) and
the model reviewer. The model reviewer is advisory. A static finding is owned by REVIEW_RULES, read in order.
"""
from __future__ import annotations

import re

OWNERS = ('content', 'platform', 'customer', 'advisory')
BY_FINDING = 'by_finding'          # REVIEW: owned per finding (REVIEW_RULES / the reviewer)

OWNER = {
    # threshold: consistency, dependency, sandbox build and the fixed tests (their failures carry the spec's ids)
    'CONSISTENCY': 'platform',
    'UNSUPPORTED_DEPENDENCY': 'platform',
    # the spec's own acceptance ids (the deterministic architect and its wrappers); prefixes end with '-'
    'accept-': 'platform',
    'CUSTOMER-FACTS': 'platform',
    'DESIGN-CONTRACT': 'platform',
    'CUSTOMER-PAGE-STRUCTURE': 'platform',
    'PLATFORM-CHECKS': 'platform',
    # the post-build group (investor_app._verification_executor)
    'PREVIEW': 'platform',
    'BEHAVIOR': 'platform',
    'BROWSER': 'platform',
    'VISUAL': 'platform',
    'AUTH_FORM': 'platform',
    'REVIEW': BY_FINDING,
    'QUALITY': 'platform',
    'DESIGN': 'advisory',                     # design_review: the critic's must_fix (blocks once in the legacy loop)
    # the skill gates (skill_units/gate.WORKER_GATES), one entry per unit
    'gate-G3-a11y_alt_text': 'platform',
    'gate-G3-a11y_contrast': 'platform',
    'gate-G3-a11y_focus': 'platform',
    'gate-G3-a11y_heading_order': 'platform',
    'gate-G3-a11y_labels': 'platform',
    'gate-G4-perf_blocking_script': 'platform',
    'gate-G4-perf_font_display': 'platform',
    'gate-G4-perf_font_preconnect': 'platform',
    'gate-G4-perf_hero_eager': 'platform',
    'gate-G4-perf_inline_image_weight': 'platform',
    'gate-G4-perf_lazy_images': 'platform',
    'gate-G6-secrets_api_keys': 'platform',
    'gate-G6-secrets_assignment': 'platform',
    'gate-G6-secrets_bearer': 'platform',
    'gate-G6-secrets_db_url': 'platform',
    'gate-G6-secrets_private_key': 'platform',
    'gate-HE-he_gender': 'content',
    'gate-HE-he_grammar': 'content',
    'gate-HE-he_translationese': 'content',
    'gate-G10-copy_filler': 'content',
    'gate-G10-copy_placeholder': 'content',
    'gate-G11-links_address': 'platform',
    'gate-G11-links_anchor': 'platform',
    'gate-G11-links_tel': 'platform',
    'gate-G1-blocks_empty': 'platform',
    'gate-BRAND-brand_name': 'platform',
    'gate-SHARE-share_meta': 'platform',
    'gate-G5-rights_font_source': 'platform',
    'gate-G5-rights_image_source': 'platform',
    'gate-G5-rights_media_source': 'platform',
    'gate-PRO-design_minimum': 'platform',
    # the other gates and checks the worker installs
    'gate-APPLE': 'platform',
    'gate-G8-runtime-load': 'platform',
    'gate-GAME-runtime': 'platform',
    'gate-SITE_CLAIMS': 'content',
    'gate-SITE_PARITY': 'platform',
    'window-': 'platform',
    'asset-plan': 'platform',
    'asset-marker': 'platform',
    'generated-image': 'platform',
    'uploaded-logo': 'platform',
    'uploaded-main-image': 'platform',
    # the engine's own entries (autonomous_core): a summary line and notes to the repairer carry no defect
    'ALSO_FAILING': 'advisory',
    'ROUND_unspecified': 'platform',
    'REPAIR_REGRESSION': 'advisory',
    'NO_PROGRESS': 'advisory',
    'TEST_EDIT_REVERTED': 'advisory',
    'REPAIR_PLAN_WEAKENED': 'advisory',
}
# A layer's check that crashed, said nothing, contradicted itself or judged nothing (verification_group,
# verification_verdict): the check did not judge the copy, so the platform owns it.
LAYER_SUFFIXES = ('_EXCEPTION', '_unspecified', '_contradictory', '_NO_CHECKS', '_UNVERIFIED')
PREFIXES = tuple(k for k in OWNER if k.endswith('-'))

# REVIEW static findings, in order (skills_runtime._invented_contact and the other static checks). 'customer' holds
# only when the approved prompt lists that fact as missing from the customer (fact_canon.needs_customer_input);
# otherwise the platform filled that slot and owns it.
REVIEW_RULES = (
    (re.compile(r'facts the customer gave are missing from the page'), 'platform'),
    (re.compile(r'contact details not in the approved request \(invented\)'), 'customer'),
    (re.compile(r'opening hours the customer never gave \(invented\)'), 'customer'),
    (re.compile(r'opening hours contradict what the customer wrote'), 'platform'),
    (re.compile(r'review/rating counts not in the approved request'), 'content'),
    (re.compile(r'testimonials with no source in the approved request'), 'platform'),
    (re.compile(r'placeholder text in the product'), 'content'),
    # every other static check reads the markup, which the platform wrote (dir, alt, labels, ranges, escaping)
    (re.compile(r''), 'platform'),
)


class Unowned(LookupError):
    """An acceptance id with no owner: the route stops loudly instead of guessing."""


def owner_of(acceptance_id: str) -> str:
    """The owner of an acceptance id (BY_FINDING for REVIEW). Raises Unowned when the table has no entry."""
    aid = str(acceptance_id or '')
    if aid in OWNER:
        return OWNER[aid]
    for suffix in LAYER_SUFFIXES:
        if aid.endswith(suffix) and aid[:-len(suffix)] in OWNER:
            return 'platform'
    for prefix in PREFIXES:
        if aid.startswith(prefix):
            return OWNER[prefix]
    raise Unowned(f'no owner for acceptance id {aid!r} (site_content/owners.OWNER)')


def review_owner(message: str, *, source: str, missing_listed: bool) -> str:
    """The owner of one REVIEW finding: the model reviewer is advisory; a static one by REVIEW_RULES."""
    if source == 'reviewer':
        return 'advisory'
    if source != 'static':
        raise Unowned(f'a REVIEW finding of unknown source {source!r}: {message[:160]}')
    for pattern, owner in REVIEW_RULES:
        if pattern.search(message or ''):
            if owner == 'customer' and not missing_listed:
                return 'platform'
            return owner
    raise Unowned(f'no REVIEW rule for {message[:160]!r}')          # unreachable: the last rule matches every text
