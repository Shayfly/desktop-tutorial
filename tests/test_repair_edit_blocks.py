"""Exact edit blocks in agentic repair (wf_309a64e1-002, the repair-JSON root cause).

Three founder builds on 2026-11-17 failed in repair: with the strong routes out of credit, the agentic edit step fell
to the two routes whose output is limited to 8,192 tokens, and a whole app.py (~9.4-9.8K output tokens, estimate) was
cut at 8,188 tokens 14 of 14 times. An edit block is a few hundred tokens whatever the file's size.

The working copy here is SYNTHETIC (a 20,000+ character app.py built in the test): the round zips of those builds
were not read. The real AgenticRepairAgent and resolve_edits run; only the model is scripted.
"""
import json
import unittest

from omni_prod.agentic_repair import WHOLE_FILE_MAX_CHARS, AgenticRepairAgent, _SYSTEM
from omni_prod.build_control import BuildCancelled, BuildDeadline
from omni_prod.repair_edits import resolve_edits

ROUTES = ''.join(f'\n@app.get("/r{i}")\ndef r{i}():\n    return {{"n": {i}}}\n' for i in range(700))
BIG = 'from fastapi import FastAPI\napp = FastAPI()\n' + ROUTES + '\ndef total():\n    return sum([1, 2])\n'
BASE = {'app.py': BIG, 'api.py': 'def handle():\n    return 1\n'}


class _Spec:
    def to_dict(self):
        return {'title': 't'}


class _Fallback:
    calls = 0

    def repair(self, **kw):
        self.calls += 1
        return ('fallback',)


class _Gw:
    def __init__(self, answers):
        self.answers, self.prompts = list(answers), []

    def complete_json(self, **kw):
        self.prompts.append(json.loads(kw['user']))
        a = self.answers.pop(0)
        if isinstance(a, BaseException):
            raise a
        return a


def run(answers, repo=BASE, steps=6):
    gw, fb = _Gw(answers), _Fallback()
    agent = AgenticRepairAgent(gw, fallback=fb, max_steps=steps)
    out = agent.repair(spec=_Spec(), repo_summary={'_repository': dict(repo), 'candidate_files': []},
                       failures=[{'acceptance_id': 'A1', 'message': 'total is wrong', 'evidence': ''}])
    return out, gw, fb


class ResolveEdits(unittest.TestCase):
    def test_an_exact_unique_block_applies(self):
        texts, misses = resolve_edits(BASE, [{'path': 'app.py', 'old': 'return sum([1, 2])', 'new': 'return 3'}])
        self.assertEqual(misses, [])
        self.assertTrue(texts['app.py'].endswith('return 3\n'))
        self.assertEqual(len(texts['app.py']), len(BIG) - len('sum([1, 2])') + 1)

    def test_whitespace_counts_and_the_hint_is_never_applied(self):
        texts, misses = resolve_edits(BASE, [{'path': 'app.py', 'old': 'return  sum([1, 2])', 'new': 'x'}])
        self.assertEqual(texts, {})
        self.assertEqual(misses[0]['code'], 'NOT_FOUND')
        self.assertIn('return sum([1, 2])', misses[0]['closest_line'])

    def test_an_ambiguous_block_names_its_lines(self):
        texts, misses = resolve_edits(BASE, [{'path': 'app.py', 'old': 'return {"n": 1', 'new': 'x'}])
        self.assertEqual((texts, misses[0]['code']), ({}, 'AMBIGUOUS'))
        self.assertGreater(len(misses[0]['lines']), 1)

    def test_overlapping_occurrences_count_as_two(self):
        self.assertEqual(resolve_edits({'a.txt': 'aaa'}, [{'path': 'a.txt', 'old': 'aa', 'new': 'b'}])[1][0]['code'],
                         'AMBIGUOUS')

    def test_all_or_nothing_and_edits_see_the_earlier_ones(self):
        good = {'path': 'api.py', 'old': 'return 1', 'new': 'return 2'}
        texts, misses = resolve_edits(BASE, [good, {'path': 'api.py', 'old': 'return 9', 'new': 'x'}])
        self.assertEqual(texts, {})
        self.assertEqual([m['code'] for m in misses], ['NOT_FOUND'])
        texts, misses = resolve_edits(BASE, [good, {'path': 'api.py', 'old': 'return 2', 'new': 'return 3'}])
        self.assertEqual(texts['api.py'], 'def handle():\n    return 3\n')

    def test_bad_inputs_are_refused_loudly(self):
        for edits, code in (('x', 'BAD_SHAPE'), ([{'path': 'api.py', 'old': 1, 'new': 'x'}], 'BAD_SHAPE'),
                            ([{'path': '../etc/passwd', 'old': 'a', 'new': 'b'}], 'UNSAFE_PATH'),
                            ([{'path': 'nope.py', 'old': 'a', 'new': 'b'}], 'NO_SUCH_FILE'),
                            ([{'path': 'api.py', 'old': '', 'new': 'b'}], 'EMPTY_OLD'),
                            ([{'path': 'api.py', 'old': 'return 1', 'new': 'b'}] * 41, 'TOO_MANY')):
            with self.subTest(code=code):
                texts, misses = resolve_edits(BASE, edits)
                self.assertEqual((texts, misses[0]['code']), ({}, code))


class TheAgentEditsWithBlocks(unittest.TestCase):
    def test_a_large_file_is_repaired_with_a_small_answer(self):
        self.assertGreater(len(BIG), WHOLE_FILE_MAX_CHARS)
        out, gw, fb = run([
            {'action': 'edit', 'edits': [{'path': 'app.py', 'old': 'return sum([1, 2])', 'new': 'return 3'}]},
            {'action': 'submit', 'note': 'total was wrong'}])
        self.assertEqual(fb.calls, 0)
        [patch] = list(out)
        self.assertEqual(patch.path, 'app.py')
        self.assertIn('return 3', patch.content)
        self.assertEqual(gw.prompts[1]['history'][0]['result']['applied'], ['app.py'])
        self.assertEqual(gw.prompts[1]['history'][0]['request']['edits'], ['app.py'])   # the block, not the file

    def test_a_large_existing_file_is_never_rewritten_whole(self):
        out, gw, fb = run([
            {'action': 'edit', 'files': [{'path': 'app.py', 'content': BIG.replace('sum([1, 2])', '3')}]},
            {'action': 'edit', 'edits': [{'path': 'app.py', 'old': 'sum([1, 2])', 'new': '3'}]},
            {'action': 'submit'}])
        refused = gw.prompts[1]['history'][0]['result']
        self.assertEqual(refused['applied'], [])
        self.assertEqual(refused['edit_misses'][0]['code'], 'WHOLE_FILE_TOO_LARGE')
        self.assertEqual(gw.prompts[1]['edited'], [])                              # nothing changed yet
        self.assertIn('return 3', list(out)[0].content)

    def test_a_small_or_new_file_may_still_be_sent_whole(self):
        out, _, fb = run([
            {'action': 'edit', 'files': [{'path': 'api.py', 'content': 'def handle():\n    return 2\n'},
                                         {'path': 'util.py', 'content': 'X = 1\n'}]},
            {'action': 'submit'}])
        self.assertEqual(sorted(p.path for p in out), ['api.py', 'util.py'])
        self.assertEqual(fb.calls, 0)

    def test_a_submit_whose_edits_miss_does_not_end_the_round(self):
        out, gw, fb = run([
            {'action': 'submit', 'edits': [{'path': 'app.py', 'old': 'return  sum', 'new': 'x'}]},
            {'action': 'submit', 'edits': [{'path': 'app.py', 'old': 'return sum([1, 2])', 'new': 'return 3'}]}])
        self.assertEqual(gw.prompts[1]['history'][0]['result']['edit_misses'][0]['code'], 'NOT_FOUND')
        self.assertIn('return 3', list(out)[0].content)
        self.assertEqual(fb.calls, 0)

    def test_misses_on_every_step_fall_back_to_the_classic_repair(self):
        miss = {'action': 'edit', 'edits': [{'path': 'app.py', 'old': 'nowhere', 'new': 'x'}]}
        out, _, fb = run([miss, miss], steps=2)
        self.assertEqual((out, fb.calls), (('fallback',), 1))

    def test_the_deadline_and_the_owners_stop_are_never_swallowed(self):
        for exc in (BuildDeadline('time'), BuildCancelled('stop')):
            with self.subTest(exc=type(exc).__name__), self.assertRaises(type(exc)):
                run([exc])

    def test_the_prompt_asks_for_blocks_and_forbids_function_calls(self):
        self.assertIn('"edits"', _SYSTEM)
        self.assertIn('never a function call', _SYSTEM)
        self.assertIn(str(WHOLE_FILE_MAX_CHARS), _SYSTEM)


if __name__ == '__main__':
    unittest.main()
