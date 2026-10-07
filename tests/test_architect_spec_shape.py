"""The architect is told the exact spec shape and gets one corrective round.

Golden E2E #1 on Preview (2026-10-07): with a real Gemini answer the build
failed with "ValueError: requirement id/text required": the architect prompt
named the top-level fields but not the requirement/acceptance keys, so the
model invented its own.
"""
import json
import unittest

from omni_prod.autonomous_agents import _ARCHITECT_SYSTEM, ArchitectAgent

GOOD = {"title": "Team tasks", "summary": "Track team tasks", "stack": ["python", "sqlite"],
        "requirements": [{"id": "R1", "text": "Users sign up and log in", "kind": "functional", "mandatory": True}],
        "acceptance": [{"id": "A1", "requirement_id": "R1", "text": "A new user can sign up and log in"}]}
INVENTED_KEYS = {**GOOD, "requirements": [{"requirement_id": "REQ-1", "description": "Users sign up and log in"}],
                 "acceptance": [{"criterion_id": "AC-1", "requirement": "REQ-1", "description": "..."}]}


class _Gateway:
    def __init__(self, *answers):
        self.answers, self.calls = list(answers), []

    def complete_json(self, *, system, user, max_tokens):
        self.calls.append({"system": system, "user": user})
        return self.answers.pop(0)


class ArchitectShapeTests(unittest.TestCase):
    def test_prompt_names_every_key_the_validator_reads(self):
        for key in ('"requirements"', '"id"', '"text"', '"kind"', '"mandatory"', '"acceptance"', '"requirement_id"'):
            self.assertIn(key, _ARCHITECT_SYSTEM)
        for kind in ("functional", "quality", "security", "data", "deployment"):
            self.assertIn(kind, _ARCHITECT_SYSTEM)

    def test_valid_answer_needs_one_call(self):
        gw = _Gateway(GOOD)
        self.assertEqual(ArchitectAgent(gw).create_spec("Build a team task tracker").requirements[0].id, "R1")
        self.assertEqual(len(gw.calls), 1)

    def test_invented_keys_get_one_corrective_round_with_the_error(self):
        gw = _Gateway(INVENTED_KEYS, GOOD)
        spec = ArchitectAgent(gw).create_spec("Build a team task tracker")
        self.assertEqual(spec.acceptance[0].requirement_id, "R1")
        self.assertEqual(len(gw.calls), 2)
        correction = json.loads(gw.calls[1]["user"])
        self.assertEqual(correction["validation_error"], "requirement id/text required")
        self.assertEqual(correction["original_request"], "Build a team task tracker")
        self.assertEqual(correction["invalid_specification"], INVENTED_KEYS)

    def test_second_invalid_answer_fails_explicitly(self):
        gw = _Gateway(INVENTED_KEYS, {**GOOD, "requirements": [{"id": "R1", "text": "x", "kind": "performance"}]})
        with self.assertRaises(ValueError) as ctx:
            ArchitectAgent(gw).create_spec("Build a team task tracker")
        self.assertIn("invalid specification twice", str(ctx.exception))
        self.assertIn("invalid requirement kind: performance", str(ctx.exception))
        self.assertEqual(len(gw.calls), 2)


if __name__ == "__main__":
    unittest.main()
