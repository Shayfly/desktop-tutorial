"""Offline classification of a failed build from its STORED evidence export (no model call, no network, no DB, no spend).

    python -m omni_prod.failure_replay export.json [--files-dir DIR]

Input: the JSON written by `omni_prod.evidence_export` (and, optionally, the extracted generated files). It separates, per
failure, three causes that are easy to confuse:

  WRONG_CRUD_REQUIREMENT  a failed check or an unmet acceptance criterion demands records/accounts/forms that the
                          APPROVED brief excludes (content-only site): the requirement is wrong, not the generated app;
  MISSING_COVERAGE        an acceptance criterion has no passing check although nothing failed for it (no step was mapped
                          to it, or it is mapped only to a kind the contract waives): a coverage-mapping problem;
  REAL_DEFECT             a check the contract really requires (responsive, api_smoke, data_read ...) failed on the
                          generated app; static signals from the files are listed as corroboration, never as proof.

It states the limits: this classifies stored artifacts; it does not re-run the app (the sandbox acceptance runner on the
worker host does), and it never says a build is "fixed".
"""
from __future__ import annotations

import json
import os
import re
import sys

CRUD_KINDS = {'data_create', 'data_update', 'data_delete', 'auth', 'role', 'integration'}
_CRUD_TEXT = re.compile(r'(?i)\b(create|creates|save|saves|saved|record|records|add|adds|submit|sign[- ]?in|log[- ]?in|account|edit|delete|update)\b'
                        r'|שמור|שמירה|שומר|הוסף|הוספ|רשומ|טופס|התחבר|חשבון|עריכ|מחיק|עדכון')


def _content_only(exp: dict) -> bool:
    brief = exp.get('approved_brief') if isinstance(exp.get('approved_brief'), dict) else {}
    contract = exp.get('approved_contract') if isinstance(exp.get('approved_contract'), dict) else {}
    value = ((brief.get('fields') or {}).get('content_only') or {}).get('value')
    return value == 'yes' or 'static_content_site' in (contract.get('defaults_applied') or [])


def _static_signals(files_dir: str | None) -> dict | None:
    if not files_dir or not os.path.isdir(files_dir):
        return None
    html, css = [], []
    for root, _, names in os.walk(files_dir):
        for n in names:
            p = os.path.join(root, n)
            try:
                txt = open(p, encoding='utf-8', errors='replace').read()
            except OSError:
                continue
            (html if n.lower().endswith(('.html', '.htm', '.py', '.js')) else css if n.lower().endswith('.css') else []).append(txt)
    blob_html, blob_css = '\n'.join(html), '\n'.join(css)
    return {'has_viewport_meta': bool(re.search(r'<meta[^>]+name=["\']viewport', blob_html, re.I)),
            'has_media_query': '@media' in blob_css or '@media' in blob_html,
            'fixed_width_over_480px': bool(re.search(r'(?<![-\w])width\s*:\s*(?:[5-9]\d\d|\d{4,})px', blob_css + blob_html))}


def classify(exp: dict, files_dir: str | None = None) -> dict:
    missing_inputs = [k for k in ('approved_contract', 'approved_brief', 'behavior_failed_checks', 'product_spec_acceptance')
                      if k not in exp or (isinstance(exp[k], str) and exp[k].startswith('MISSING'))]
    content_only = _content_only(exp)
    scope = ((exp.get('approved_contract') or {}).get('acceptance_scope_by_deployed_code')
             if isinstance(exp.get('approved_contract'), dict) else None)
    not_required = set((scope or {}).get('not_required') or [])
    spec = {a.get('id'): a for a in exp.get('product_spec_acceptance') or [] if isinstance(a, dict)}
    rounds = (exp.get('behavior_acceptance') or {}).get('per_round') or []
    last_missing = list((rounds[-1] or {}).get('missing_acceptance_ids') or []) if rounds else []
    findings = []
    seen_failed_ids = set()
    for c in exp.get('behavior_failed_checks') or []:
        kind, ids = c.get('kind'), c.get('acceptance_ids') or []
        seen_failed_ids.update(ids)
        if kind in CRUD_KINDS and content_only:
            findings.append({'cause': 'WRONG_CRUD_REQUIREMENT', 'round': c.get('round'), 'step': c.get('step_id'), 'kind': kind,
                             'acceptance_ids': ids, 'why': f'a {kind} check failed but the approved brief is a content-only site '
                             '(no accounts, nothing saved); the requirement itself contradicts the approval',
                             'waived_by_deployed_code': kind in not_required, 'evidence': c.get('evidence')})
        elif kind in ('responsive', 'api_smoke', 'data_read') or kind in CRUD_KINDS:
            findings.append({'cause': 'REAL_DEFECT', 'round': c.get('round'), 'step': c.get('step_id'), 'kind': kind,
                             'acceptance_ids': ids, 'why': f'a required {kind} check failed on the generated app',
                             'evidence': c.get('evidence')})
    for aid in last_missing:
        text = (spec.get(aid) or {}).get('text') or ''
        if aid in seen_failed_ids:
            continue                                            # already explained by its failed check above
        if content_only and _CRUD_TEXT.search(text):
            findings.append({'cause': 'WRONG_CRUD_REQUIREMENT', 'acceptance_id': aid, 'text': text,
                             'why': 'the criterion asks for saving/accounts/forms but the approved brief is content-only'})
        else:
            findings.append({'cause': 'MISSING_COVERAGE', 'acceptance_id': aid, 'text': text,
                             'why': 'no passing check is mapped to this criterion and none failed for it; '
                                    'if it maps only to a waived kind it can never be covered'})
    signals = _static_signals(files_dir)
    if signals is not None:
        for f in findings:
            if f['cause'] == 'REAL_DEFECT' and f.get('kind') == 'responsive':
                f['static_signals'] = signals
                f['corroborated_by_static_signals'] = not signals['has_viewport_meta'] or signals['fixed_width_over_480px']
    causes = sorted({f['cause'] for f in findings})
    return {'build': (exp.get('build') or {}).get('id'), 'content_only_by_approval': content_only,
            'approval_status': exp.get('approval_status'), 'inputs_missing': missing_inputs,
            'findings': findings, 'causes': causes,
            'verdict': ('NOT_ENOUGH_EVIDENCE: ' + ', '.join(missing_inputs)) if missing_inputs and not findings else
                       ('NO_FAILURE_FOUND_IN_STORED_EVIDENCE' if not findings else 'CLASSIFIED'),
            'limits': ['stored artifacts only: the app was not re-run', 'no model was called',
                       'a classification is not a fix: nothing here says the build now passes']}


def main(argv: list[str]) -> int:
    paths = [a for i, a in enumerate(argv) if not a.startswith('--') and (i == 0 or argv[i - 1] != '--files-dir')]
    if not paths:
        print('usage: python -m omni_prod.failure_replay export.json [--files-dir DIR]', file=sys.stderr)
        return 2
    exp = json.load(open(paths[0], encoding='utf-8'))
    out = classify(exp, argv[argv.index('--files-dir') + 1] if '--files-dir' in argv else None)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
