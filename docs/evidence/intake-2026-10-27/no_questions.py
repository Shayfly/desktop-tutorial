"""Experiment: the same conversation with and without the fixed question catalog (discovery.QUESTIONS)."""
import sys, json
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[3]))
from omni_prod import discovery as d
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from tests.test_conversation_os import MemoryBriefs

MSGS = ['אני רוצה אתר לתיירים שמגיעים לעיר', 'תחליט אתה', 'תחליט אתה']

def run(label):
    sup = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore())
    print(f'=== {label}: QUESTIONS={len(d.QUESTIONS)}')
    for m in MSGS:
        t = sup.turn(project_id='p', account_id='a', message=m)
        row = t.brief_row
        print(f'> {m}\n< {t.reply}\n  complete={row.complete} asked={[q.field for q in t.questions]} '
              f'detector_q={(t.gaps or {}).get("question", {}) and t.gaps["question"]["field"] if t.gaps and t.gaps.get("question") else None} '
              f'actions={[a["type"] for a in t.actions]}')

run('with catalog')
saved = d.QUESTIONS
d.QUESTIONS = ()
d.BY_ID.clear()
run('catalog deleted')
