"""Prints, as JSON, the plan view the conversation route sends for a request the gate cannot build (a phone app with sign-in and
payments): built by the REAL functions -- the brief, the contract, ChiefArchitect.plan and the supervisor's _plan_view -- with no
database. tests/feasibility_words_browser.cjs serves it to the real app.js."""
import dataclasses
import json
import os
import sys

sys.path.insert(0, os.getcwd())
from omni_prod import discovery as D
from omni_prod.conversation.supervisor import _plan_view
from omni_prod.intake import contract as C
from omni_prod.planning import feasibility_words as FW
from omni_prod.planning.architect import ChiefArchitect

brief = D.start('אתר לעסק שלי, קוראים לו קפה נועה, בחיפה')
base = C.from_brief(brief)
probe = dataclasses.replace(base, product_family='mobile_app',
                            authentication_requirements={'mode': 'simple', 'source': 'probe'},
                            integrations=[{'kind': 'payments', 'detected_from': 'q', 'status': 'probe'},
                                          {'kind': 'email', 'detected_from': 'q', 'status': 'probe'}])
view = _plan_view(ChiefArchitect().plan(probe))
findings = [f for f in view['feasibility']['findings'] if f['outcome'] != 'FEASIBLE']
out = {'plan': view,
       'blocker': {'code': 'capability_not_feasible', 'findings': FW.attach(findings)},
       'items': sorted({f['item'] for f in findings}),
       'sentences': {lang: [FW.sentence(f, lang) for f in FW.unique(findings)] for lang in FW.LANGS},
       # what a finding that arrives with no words (an older server) says: the general sentence, never its item or reason
       'general': {lang: '{}: {}. {}.'.format(*getattr(FW.GENERAL, lang)) for lang in FW.LANGS}}
print(json.dumps(out, ensure_ascii=False))
