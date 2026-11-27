"""Prints, as JSON, what the sketch routes answer for one brief: built by the REAL service functions (omni_prod/direction_sketch)
on a Sketch row, with no database. tests/direction_sketch_browser.cjs serves these to the real app.js and the real frame."""
import datetime
import json
import os
import sys

sys.path.insert(0, os.getcwd())
os.environ.update({'OMNI_DIRECTION_SKETCH': 'on', 'OMNI_SITE_LIBRARY': 'on'})
from omni_prod import direction_sketch as DS
from omni_prod import discovery as D
from omni_prod.direction_sketch import service as SK
from omni_prod.direction_sketch import store as S

TEXT = 'אני רוצה אתר תדמית למספרה שלי בחיפה, קוראים לה "סטודיו נועה". טלפון 04-5551234'
WORDS = {'schema': '148ai.site_content/1', 'name': 'סטודיו נועה', 'tagline': 'מספרה בחיפה', 'description': 'מספרה בחיפה, סטודיו נועה.',
         'sections': {'hero': {'title': 'תספורת שמתאימה לכם', 'lead': 'מספרה בחיפה, עם תור שנוח לכם.', 'cta': 'לקביעת תור'},
                      'services': {'title': 'מה אנחנו עושים', 'nav': 'שירותים',
                                   'items': [{'title': 'תספורת', 'desc': 'תספורת לנשים ולגברים.'}, {'title': 'צבע', 'desc': 'צבע לשיער.'}]}}}
brief = D.start(TEXT)
d = DS.ready(brief, account_id='u', has_version=False, has_open_build=False).direction
assert d is not None
prompt = DS.prompt_of(brief)


def row(state, copy):
    return S.Sketch(id='skt_' + 'a' * 24, project_id='p1', account_id='u', brief_revision=1, brief_fingerprint='f' * 16,
                    direction_fp=DS.direction_fp(d), copy_fp=DS.copy_fp(d), seq=0, funding='company_first' if state != 'none' else 'none',
                    copy_state=state, copy_reason=None, copy=copy, copy_from=None, reservation_id=None, credits=0,
                    record={'direction': d.to_dict(), 'prompt': prompt, 'placeholders': []},
                    created_at=datetime.datetime(2026, 11, 27, 10, 0, 0))


out = {'direction_fp': DS.direction_fp(d), 'brief_revision': 1}
for name, state, copy in (('pending', 'pending', None), ('written', 'written', WORDS), ('failed', 'failed', None)):
    r = row(state, copy)
    out[name] = {'view': SK.view(None, None, r), 'page': SK.page(None, r)}
print(json.dumps(out, ensure_ascii=False))
