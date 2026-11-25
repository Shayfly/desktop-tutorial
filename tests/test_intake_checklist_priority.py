"""Advisory conversation guidance cannot displace expert topics in a full intake brief."""

import json
import unittest
from unittest.mock import patch

from omni_prod.discovery import start
from omni_prod.intake.conversation_agent import FLAG
from omni_prod.intake.interpreter import CONTEXT_CHARS, contextual_user


class IntakeChecklistPriority(unittest.TestCase):
    def test_long_website_context_preserves_actionable_expert_topics(self):
        brief = start('Build a website. ' + 'g' * 600)
        brief.family = 'website'
        brief.fields = {f'fixture{i}': {'value': 'f' * 120, 'source': 'message'} for i in range(6)}
        history = [{'role': 'user', 'content': 'x' * 107}] * 4
        with patch.dict('os.environ', {FLAG: '0'}):
            text = contextual_user('OK', brief, history).splitlines()[1]

        context = json.loads(text)
        self.assertLessEqual(len(text), CONTEXT_CHARS)
        self.assertEqual(context['confirmed'], {name: 'f' * 120 for name in brief.fields})
        self.assertEqual(context['expert_checklist'][:2], [
            'who uses it (customer, staff, the owner) and what each one does',
            'the one thing it must do on day one (the core flow, step by step)',
        ])
