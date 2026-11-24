"""Prepare a bounded Gemini design comparison from rights-cleared reference cards.

No Google Grounding, network, payment, database writes, customer prose, or raw
third-party assets. The caller must obtain rights for this exact card revision
and bind the model call to the existing metered gateway before enabling it.
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone

from ..reference_catalog import check
from ..reference_store import card_sha256, checked_card

MODEL = 'gemini-3.8-flash'
MIN_REFERENCES, MAX_REFERENCES = 3, 8
CRITERIA = ('hierarchy', 'air', 'typography', 'mobile_390', 'originality')


class ResearchEvidenceError(ValueError):
    pass


@dataclass(frozen=True)
class RightsGrant:
    card_sha256: str
    evidence_id: str
    allow_model_analysis: bool
    # Only independently licensed or owned material. A human-approved reference
    # card alone does not imply rights to reuse provider search results.
    origin: str


def _hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def prepare(store, *, category: str, grants: Mapping[str, RightsGrant], now: datetime | None = None) -> dict:
    """Use the existing library; accept rights grants only from trusted server code.

    No rights grant may come from the model or customer. This function checks
    scope and identity, not the underlying license document or authenticity of
    the supplied grant. The caller must verify those separately.
    """
    check(category)
    now = now or datetime.now(timezone.utc)
    refs, evidence, seen_ids, seen_urls = [], [], set(), set()
    for row in store.approved_for(category, now=now):
        card = checked_card(row.card)
        cid = card['card_id']
        grant = grants.get(cid)
        sha = card_sha256(card)
        if (row.retired or card['vertical'] != category or row.category != category
                or row.effective_status(now) != 'fresh' or card['decision']['status'] != 'approved'
                or card['judge']['total'] < 8 or any(card['judge']['scores'][k] == 0 for k in CRITERIA)
                or not isinstance(grant, RightsGrant) or grant.allow_model_analysis is not True
                or grant.origin not in ('owned', 'independently_licensed')
                or grant.card_sha256 != sha or not grant.evidence_id.strip()):
            continue
        url = card['source']['url']
        if cid in seen_ids or url in seen_urls:
            continue
        seen_ids.add(cid)
        seen_urls.add(url)
        # Explicitly project only the schema's closed-vocabulary design traits.
        # No URLs, copy, image files, titles, reviewer prose or customer inputs.
        refs.append({'id': cid, 'structure': copy.deepcopy(card['skeleton']),
                     'measured_scores': {k: card['judge']['scores'][k] for k in CRITERIA}})
        evidence.append({'id': cid, 'card_sha256': sha, 'rights_evidence_id': grant.evidence_id,
                         'source_url': url, 'captured_at': card['source']['captured_at']})
        if len(refs) == MAX_REFERENCES:
            break
    if len(refs) < MIN_REFERENCES:
        return {'status': 'INSUFFICIENT_APPROVED_REFERENCES', 'eligible_count': len(refs),
                'model_request': None, 'evidence': []}
    model_input = {'category': category, 'references': refs, 'criteria': list(CRITERIA)}
    return {'status': 'READY_FOR_METERED_COMPARISON', 'model': MODEL,
            'input_sha256': _hash(model_input), 'evidence_sha256': _hash(evidence),
            'model_request': model_input, 'evidence': evidence}


def validate_comparison(prepared: dict, response: dict) -> dict:
    """Validate structured recommendations against the exact prepared input.

    The model may recommend or rank existing evidence; it cannot invent sites,
    scores or facts. A judgment is not a verified finding or a build approval.
    """
    if prepared.get('status') != 'READY_FOR_METERED_COMPARISON' or prepared.get('model') != MODEL:
        raise ResearchEvidenceError('comparison has no admitted input')
    model_input = prepared['model_request']
    if _hash(model_input) != prepared['input_sha256']:
        raise ResearchEvidenceError('comparison input was modified')
    if _hash(prepared['evidence']) != prepared['evidence_sha256']:
        raise ResearchEvidenceError('comparison source evidence was modified')
    refs = {r['id']: r for r in model_input['references']}
    if [e['id'] for e in prepared['evidence']] != list(refs):
        raise ResearchEvidenceError('source evidence does not match input references')
    if not isinstance(response, dict) or set(response) != {'input_sha256', 'recommendations'} or response['input_sha256'] != prepared['input_sha256']:
        raise ResearchEvidenceError('wrong comparison identity or unexpected output')
    recommendations = response['recommendations']
    if not isinstance(recommendations, list) or len(recommendations) != MIN_REFERENCES:
        raise ResearchEvidenceError('exactly three ranked references required')
    selected = set()
    for item in recommendations:
        if not isinstance(item, dict) or set(item) != {'reference_id', 'strengths'}:
            raise ResearchEvidenceError('unexpected recommendation field')
        cid, strengths = item['reference_id'], item['strengths']
        if not isinstance(cid, str) or cid not in refs or cid in selected:
            raise ResearchEvidenceError('unknown or duplicate reference')
        selected.add(cid)
        if (not isinstance(strengths, list) or not strengths or len(strengths) > len(CRITERIA)
                or any(not isinstance(k, str) or k not in CRITERIA for k in strengths)
                or len(set(strengths)) != len(strengths)
                or any(refs[cid]['measured_scores'][k] != 2 for k in strengths)):
            raise ResearchEvidenceError('strength lacks supporting measured score')
    return {'status': 'MODEL_RECOMMENDATIONS_VALIDATED', 'model': MODEL,
            'input_sha256': prepared['input_sha256'], 'evidence_sha256': prepared['evidence_sha256'],
            'recommendations': copy.deepcopy(recommendations),
            'evidence': [copy.deepcopy(e) for e in prepared['evidence'] if e['id'] in selected],
            'build_approval': False, 'cost_state': 'NOT_MEASURED_HERE'}
