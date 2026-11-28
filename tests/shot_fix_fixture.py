"""Prints, as JSON, what the conversation shows after a customer's screenshot round, built by the REAL round (omni_prod/shot_fix.round_of)
on a real PNG, a real site and the model's answer (an edit block), in the three languages -- with no database and no network.
tests/shot_fix_browser.cjs serves these to the real app.js and uploads this very PNG, so the card, the upload and what comes back are
checked against the server's own code. Needs Pillow (as the server does)."""
import base64
import json
import os
import sys

sys.path.insert(0, os.getcwd())
from omni_prod import shot_fix as SF
from omni_prod.conversation.store import MemoryConversationStore
from tests.shot_fix_support import FIX_ANSWER, WORK, MemoryAttachments, Reader, png

DATA = png(1500, 900)                                # long side 1,500: the round must bring it down to 1,400


def message(m):
    """One stored message as the customer's screen gets it (investor_app._conversation_message; tests/test_shot_fix.py keeps them equal)."""
    meta = m.get('interpretation') or {}
    return {'id': m.get('id'), 'role': m['role'], 'content': m['content'], 'brief_revision': m['brief_revision'],
            'intent': meta.get('intent'), 'actions': meta.get('actions') or [], 'attachments': meta.get('attachments') or [],
            'notices': meta.get('notices') or [], 'ai_status': 'ok'}


EARLIER = {'he': ('אתר למספרה שלי', 'האתר נבנה. אפשר לראות אותו כאן, ולצלם כל דבר שלא נראה נכון.'),
           'ar': ('موقع لصالوني', 'بُني الموقع. يمكنكم رؤيته هنا والتقاط لقطة لأي شيء لا يبدو صحيحا.'),
           'en': ('A site for my salon', 'The site is built. You can see it here and take a screenshot of anything that looks wrong.')}
out = {'png_b64': base64.b64encode(DATA).decode('ascii'), 'build_id': 'bld_abc123', 'version_id': 'ver_1', 'views': {}}
for lang in SF.LANGS:
    store, repo = MemoryConversationStore(), MemoryAttachments()
    for role, text in (('customer', EARLIER[lang][0]), ('assistant', EARLIER[lang][1])):
        store.add_message(project_id='p1', account_id='u', role=role, content=text, interpretation={})
    before = [message(m) for m in store.messages_for('p1', limit=50)]
    record = SF.round_of(project_id='p1', account_id='u', build_id='bld_abc123', version_id='ver_1', work=dict(WORK), data=DATA,
                         width=390, note='', lang=lang, repo=repo, reader=Reader(FIX_ANSWER), store=store, request_key='k')
    after = [message(m) for m in store.messages_for('p1', limit=50)]
    last = after[-1]
    out['views'][lang] = {'before': {'messages': before, 'turn': {'actions': []}},
                          'after': {'messages': after, 'turn': {'actions': last['actions']}},
                          'reply': last['content'], 'button': SF.BUTTON[lang], 'fingerprint': record['fix']['fingerprint'],
                          'evidence_stages': [line['stage'] for line in record['evidence']]}
out['site'] = {'html': WORK['index.html'].replace('<link rel="stylesheet" href="style.css">', '<style>' + WORK['style.css'] + '</style>')
               .replace('<script src="app.js"></script>', '')}
print(json.dumps(out, ensure_ascii=False))
