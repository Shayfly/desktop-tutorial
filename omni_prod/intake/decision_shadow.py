"""SHADOW producer of the IntakeDecision (docs/design/persistence-migration.md, signed with C1-C3, 2026-11-11).

Builds the decision from the brief that exists today, validates it, stores it next to the brief
(`project_briefs.brief_json["decision"]`) and LOGS every violation. It changes nothing else:

  * C3: no gap, question, `asked`, contract, status or fingerprint changes. The brief fingerprint is computed from
    `Brief.to_dict()`, which never contains `decision`; `requirements_text` does not read it; no `Product decisions
    v2` line is written (the generated block is part of the fingerprinted contract prompt).
  * C1: there is no enforce mode here. Enforcement is a separate, signed flip after the §3 decision card exists.
  * It never raises: a bug here is a log line, never a stopped conversation.

The channel is DERIVED from where the brief value was written (checked in the code): a quick-reply chip arrives as
`turn(answers=...)` and is stored with source "answer" -> button; typed text goes through the interpreter and is
stored with source "message" -> text; a pre-selection in `hints` -> inferred.
"""
from __future__ import annotations

import logging
import os
from dataclasses import replace

from . import decision as D

_LOG = logging.getLogger('omni_prod.intake.decision_shadow')
MODE_ENV = 'OMNI_INTAKE_DECISION_MODE'          # "shadow" (default) | "off"

_PERSISTENCE = {'yes': 'none', 'no': 'records'}  # content_only answer -> persistence
_REQUIRES_AUTH = {'none': False, 'simple': True, 'roles': True}


def mode() -> str:
    return 'off' if os.getenv(MODE_ENV, 'shadow').strip().lower() == 'off' else 'shadow'


def _field(brief, name: str, mapping: dict | None = None) -> D.Field:
    """One brief value as a typed Field, its channel derived from the stored source."""
    def conv(v):
        return v if mapping is None else mapping.get(v)
    f = brief.fields.get(name)
    if f is not None:
        v = conv(f.get('value'))
        if v is None:
            return D.MISSING                      # an unmappable value is "no decision", never a guessed one
        src = f.get('source')
        if src == 'answer':
            return D.from_button(v)
        if src == 'message':
            return D.from_text(v)
        return D.inferred(v)                      # default / delegated / implied: the system chose it
    hint = conv((brief.hints or {}).get(name))
    if hint is not None:
        return D.inferred(hint, by_model=True)
    return D.MISSING


def decision_from_brief(brief, *, artifact_id: str) -> D.IntakeDecision:
    from .families import classify_family
    fam = classify_family(brief.prompt)
    kind = {'website': 'site', 'web_app': 'app', 'game': 'game'}.get(fam)
    v = brief.values()
    art = D.ArtifactIntent(
        id=artifact_id,
        kind=D.inferred(kind) if kind else D.MISSING,            # §12: a kind is never stated by the classifier
        purpose=_text_field(brief, 'goal'),
        audience=_text_field(brief, 'audience'),
        must_include=D.inferred([v['screens']]) if v.get('screens') else D.MISSING,
        persistence=_field(brief, 'content_only', _PERSISTENCE),
        requires_auth=_field(brief, 'login', _REQUIRES_AUTH),
        personal_data=_field(brief, 'personal_data'),
        game=D.GameIntent() if kind == 'game' else None,
    )
    dec = D.IntakeDecision(raw_brief=brief.prompt, raw_brief_sha256=D.sha256(brief.prompt), artifacts=(art,),
                           mode='free')
    return replace(dec, gaps=D.derive_gaps(dec))


def _text_field(brief, name: str) -> D.Field:
    f = brief.fields.get(name)
    if not f or f.get('value') in (None, ''):
        return D.MISSING
    return D.from_text(f['value']) if f.get('source') in ('answer', 'message') else D.inferred(f['value'])


def stored_payload(brief, *, project_id: str, previous_artifact_id: str | None = None) -> dict:
    """What a brief revision stores: `brief.to_dict()` plus, in shadow mode, `decision`. Never raises."""
    payload = brief.to_dict()
    if mode() != 'shadow':
        return payload
    try:
        aid = previous_artifact_id if D.is_artifact_id(previous_artifact_id or '') else D.new_artifact_id()
        dec = decision_from_brief(brief, artifact_id=aid)
        for v in D.validate(dec, revision_raw_brief=brief.prompt):
            _LOG.warning('intake_decision_violation project=%s code=%s where=%s detail=%s stop=%s',
                         project_id, v.code, v.where, v.detail, v.stop)
        payload['decision'] = D.to_dict(dec)
    except Exception as exc:   # shadow must never stop a conversation
        _LOG.warning('intake_decision_violation project=%s code=SHADOW_ERROR detail=%s: %s',
                     project_id, type(exc).__name__, str(exc)[:200])
    return payload


def previous_artifact_id(stored: dict | None) -> str | None:
    try:
        return ((stored or {}).get('decision') or {}).get('artifacts', [{}])[0].get('id')
    except (AttributeError, IndexError, TypeError):
        return None
