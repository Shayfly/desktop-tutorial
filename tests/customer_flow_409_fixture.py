"""Prints, as JSON, what the REAL build-admission gate answers (409 capability_not_feasible) and what the plan tab's
blocker list carries, for a request the gate cannot build: sign-in with roles, and a calendar integration.

Why this exists (warehouse 132, 2026-11-27): tests/customer_flow_browser.cjs used to hand-write these two bodies as
{item: 'sign-in (roles)', outcome: 'BLOCKED'} -- a finding with no `words`, which the real server never sends since
feasibility_words.attach. The screen (rightly) says the general sentence for a finding with no words, so the test failed
on a body that does not exist. Here the bodies come from the real functions: the brief, the contract, ChiefArchitect.plan,
the REAL investor_app._bind_execution_plan and _apply_execution_plan_gate. Only the database (the conversation store, the
schema check, the brief row) is replaced."""
import dataclasses
import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.getcwd())
from omni_prod import discovery as D
from omni_prod import investor_app
from omni_prod.brief_repository import BriefRow
from omni_prod.intake import contract as C
from omni_prod.planning.architect import ChiefArchitect

brief = D.start('אתר לעסק שלי, קוראים לו קפה נועה, בחיפה')
contract = dataclasses.replace(
    C.from_brief(brief), authentication_requirements={'mode': 'roles', 'source': 'probe'},
    integrations=[{'kind': 'calendar', 'detected_from': 'q', 'status': 'probe'}])
plan = ChiefArchitect().plan(contract)
assert not plan.get('executable'), 'the probe request must be one the gate refuses'
row = BriefRow('brf_1', 'prj_1', 1, brief, D.complete(brief), brief.fingerprint())
repo = MagicMock()
repo.latest.return_value = row
store = MagicMock()
store.plan_for.return_value = {'plan': plan}
with patch.object(investor_app, '_brief_repo', return_value=repo), \
        patch('omni_prod.conversation.store.schema_ready', return_value=True), \
        patch.object(investor_app, '_conversation_store', return_value=store):
    try:
        investor_app._bind_execution_plan('prj_1', row.fingerprint)
        raise SystemExit('the gate did not refuse')
    except investor_app.HTTPException as exc:
        detail = exc.detail
        assert exc.status_code == 409 and detail['error'] == 'capability_not_feasible', detail
    preview = {'can_build': True, 'blockers': []}
    investor_app._apply_execution_plan_gate(preview, 'prj_1', SimpleNamespace(fingerprint=row.fingerprint))
print(json.dumps({'detail': detail, 'blocker': preview['blockers'][0],
                  'items': [f['item'] for f in detail['findings']]}, ensure_ascii=False))
