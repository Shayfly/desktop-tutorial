"""No conversation ends in a question nobody can answer (2026-11-16).

Every way of clicking through the cards of four real kinds of request is walked (bounded). Before the fix 80 of 252
walks ended on a question with no card and no answer the chat could take:
- "האם האתר שומר מידע?" after the customer had already said personal details are stored;
- "What is the primary business workflow and who will use it?" -- in English, for a short Hebrew request whose
  approved brief already named the audience and the goal.
A walk may end only at the summary (gate 1) or at a stated blocker. The real supervisor, discovery and contract
compile run; only the stores are in memory."""
import unittest

from omni_prod import discovery as d
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.product_architect import ProductArchitect
from tests.test_conversation_os import MemoryBriefs

PROMPTS = ('אני רוצה אתר לתיירים שמגיעים לעיר', 'אתר לחנות דלתות עם גלריה ומבצע',
           'אני צריך מערכת תורים למספרה, הלקוחות ישאירו טלפון', 'דף נחיתה למאפייה שלי')
MAX_TURNS, MAX_WALKS = 16, 400


def walk(prompt, choices):
    sup = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore())
    say = lambda message='', answers=None: sup.turn(project_id='p', account_id='a', message=message, answers=answers, lang='he')
    turn, path, pick = say(prompt), [], iter(choices)
    for _ in range(MAX_TURNS):
        if any(a['type'] == 'approve_spec' for a in turn.actions):
            return 'summary', path, turn
        if turn.blocked:
            return 'blocked', path, turn
        q = turn.questions[0] if turn.questions else None
        if q is None:
            return 'dead_end', path, turn
        options = [o.value for o in q.options] if q.kind == 'choice' else [d.DELEGATE]
        try:
            k = next(pick)
        except StopIteration:
            return 'more', path, len(options)
        path.append((q.id, options[k]))
        turn = say(answers={q.id: options[k]})
    return 'loop', path, turn


def every_walk(prompt):
    frontier, done = [()], 0
    while frontier:
        done += 1
        if done > MAX_WALKS:
            raise AssertionError(f'more than {MAX_WALKS} walks for {prompt!r}: the bound must be raised knowingly')
        choices = frontier.pop()
        outcome, path, last = walk(prompt, choices)
        if outcome == 'more':
            frontier.extend(choices + (k,) for k in range(last))
        else:
            yield outcome, path, last


class NoDeadEnd(unittest.TestCase):
    def test_every_way_through_the_cards_ends_at_the_summary_or_a_stated_blocker(self):
        total = 0
        for prompt in PROMPTS:
            for outcome, path, last in every_walk(prompt):
                total += 1
                self.assertIn(outcome, ('summary', 'blocked'), (prompt, path, getattr(last, 'reply', '')[-120:]))
        self.assertGreater(total, 200)                       # the walk really covered the tree (252 on 2026-11-16)

    def test_stored_personal_details_are_a_persistence_decision(self):
        outcome, path, turn = walk(PROMPTS[0], (0, 0, 0, 0, 0))   # content only: yes; then personal details: yes
        self.assertEqual(dict(path).get('personal_data'), 'yes')
        self.assertEqual(outcome, 'summary')
        brief = turn.brief_row.brief
        self.assertEqual(d.stores_by_own_answer(brief), 'personal_data=yes')
        self.assertIn('"persistence":"records"', d.requirements_text(brief))

    def test_a_delegated_value_decides_nothing(self):
        brief = d.Brief.from_dict({'prompt': 'אתר', 'fields': {'personal_data': {'value': 'yes', 'source': 'delegated'}}})
        self.assertIsNone(d.stores_by_own_answer(brief))
        brief.fields['personal_data']['source'] = 'answer'
        self.assertEqual(d.stores_by_own_answer(brief), 'personal_data=yes')
        brief.fields['access_scope'] = {'value': 'no_personal', 'source': 'answer'}   # the customer took it back
        self.assertIsNone(d.stores_by_own_answer(brief))

    def test_a_brief_that_names_audience_and_goal_is_not_asked_for_the_workflow(self):
        ask = ProductArchitect._material_questions
        self.assertEqual([q.id for q in ask('דף נחיתה למאפייה שלי', ())], ['clarify-primary-workflow'])
        block = d.BRIEF_MARKER + ' (binding; fingerprint 0123456789abcdef) --- Audience: the public Main action: order a cake'
        self.assertEqual(ask('דף נחיתה למאפייה שלי', (), approved='דף נחיתה למאפייה שלי ' + block), ())
        # only the server's block counts, and only with both lines
        self.assertEqual(len(ask('דף נחיתה למאפייה שלי', (), approved='Audience: x Main action: y')), 1)
        self.assertEqual(len(ask('דף נחיתה למאפייה שלי', (), approved=d.BRIEF_MARKER + ' --- Audience: the public')), 1)


if __name__ == '__main__':
    unittest.main()
