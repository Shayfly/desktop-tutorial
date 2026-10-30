import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[3]))
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from tests.test_conversation_os import MemoryBriefs
for m in ['أريد موقعًا لصالون الحلاقة الخاص بي', 'I want a website for my barbershop', 'אני רוצה אתר למספרה שלי']:
    t = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore()).turn(project_id='p', account_id='a', message=m)
    print('>', m, '\n< lang=%s | %s\n' % (t.language, t.reply))
