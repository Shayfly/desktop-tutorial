"""Michael 2026-11-13: an intended flag-off identity change passes only with ONE signed declaration matching it
exactly; an undeclared change still blocks. Every rule of scripts/identity_declared.py has a case that must refuse."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import identity_declared as D  # noqa: E402

BASE = {'files': {'omni_prod/fact_canon.py': 'a1', 'omni_prod/skills_runtime.py': 'b1', 'omni_prod/x.py': 'c1'},
        'data': {'omni_prod/assets/app.js': 'd1'}}
HEAD = {'files': {'omni_prod/fact_canon.py': 'a2', 'omni_prod/skills_runtime.py': 'b2', 'omni_prod/x.py': 'c1',
                  'omni_prod/opening_hours.py': 'e1'}, 'data': {'omni_prod/assets/app.js': 'd1'}}
FROM, TO = '728eb139' + '0' * 56, '9eac2891' + '0' * 56
ENTRY = {'id': '335-part-1', 'from_digest': FROM, 'to_digest': TO, 'added': ['omni_prod/opening_hours.py'],
         'removed': [], 'changed': ['omni_prod/fact_canon.py', 'omni_prod/skills_runtime.py'], 'data_changed': [],
         'reason': 'hours become canon facts', 'author': 'claude', 'reviewer': 'michael', 'reviewed_at': '2026-11-13'}


def ok(entry, base_digest=FROM, head_digest=TO, head=HEAD):
    return D.match([entry], base_digest, head_digest, D.diff(BASE, head))[0] is not None


class ExactSignedDeclaration(unittest.TestCase):
    def test_the_diff_is_exact(self):
        self.assertEqual(D.diff(BASE, HEAD), {'added': ['omni_prod/opening_hours.py'], 'removed': [],
                                              'changed': ['omni_prod/fact_canon.py', 'omni_prod/skills_runtime.py'],
                                              'data_changed': []})

    def test_the_exact_signed_entry_passes(self):
        self.assertTrue(ok(ENTRY))

    def test_an_undeclared_digest_is_refused(self):
        self.assertFalse(ok(ENTRY, head_digest='f' * 64))
        self.assertFalse(ok(ENTRY, base_digest='e' * 64))

    def test_an_unsigned_or_self_signed_entry_is_refused(self):
        for reviewer in ('', 'claude', 'pending', 'author'):
            self.assertFalse(ok({**ENTRY, 'reviewer': reviewer}), reviewer)
        self.assertFalse(ok({**ENTRY, 'author': 'michael'}))           # reviewer == author
        self.assertFalse(ok({**ENTRY, 'reason': ''}))
        self.assertFalse(ok({**ENTRY, 'reviewed_at': ''}))

    def test_one_path_more_or_less_is_refused(self):
        self.assertFalse(ok({**ENTRY, 'changed': ['omni_prod/fact_canon.py']}))               # one missing
        self.assertFalse(ok({**ENTRY, 'changed': ENTRY['changed'] + ['omni_prod/x.py']}))     # one extra
        self.assertFalse(ok({**ENTRY, 'added': []}))
        more = {**HEAD, 'files': {**HEAD['files'], 'omni_prod/x.py': 'c2'}}                   # an undeclared edit
        self.assertFalse(ok(ENTRY, head=more))

    def test_a_new_digest_is_declared_once(self):
        # Michael 2026-11-13: declarations accumulate in main; a consumed entry is never used twice
        again = {**ENTRY, 'id': 'later-copy'}
        self.assertEqual(D.duplicates([ENTRY, again]), [TO])
        entry, why = D.match([ENTRY, again], FROM, TO, D.diff(BASE, HEAD))
        self.assertIsNone(entry)
        self.assertIn('to_digest declared more than once', why[0])
        other = {**ENTRY, 'id': 'other', 'from_digest': TO, 'to_digest': 'a' * 64}
        self.assertTrue(D.match([ENTRY, other], FROM, TO, D.diff(BASE, HEAD))[0])   # distinct digests: fine

    def test_wildcards_are_refused(self):
        # the exact match alone already refuses a wildcard path; the explicit rule names the reason
        self.assertIn('changed has a wildcard', D.problems({**ENTRY, 'changed': ['omni_prod/*.py']}))
        self.assertFalse(ok({**ENTRY, 'changed': ['omni_prod/*.py']}))
        self.assertFalse(ok({**ENTRY, 'added': ['omni_prod/opening_hours.py'], 'changed': ['omni_prod/fact_canon.p?',
                                                                                         'omni_prod/skills_runtime.py']}))

    def test_the_cli_blocks_and_passes_loudly(self):
        with tempfile.TemporaryDirectory() as tmp:
            b, h, decl = Path(tmp, 'b.json'), Path(tmp, 'h.json'), Path(tmp, 'd.json')
            b.write_text(json.dumps(BASE)); h.write_text(json.dumps(HEAD))
            for entries, code, title in (([], 1, 'identity change not declared'), ([ENTRY], 0, 'identity change declared')):
                decl.write_text(json.dumps({'changes': entries}))
                out = subprocess.run([sys.executable, '-c', (
                    'import sys; sys.path.insert(0, sys.argv[1]); import identity_declared as D; from pathlib import Path; '
                    'D.DECLARATIONS = Path(sys.argv[2]); sys.exit(D.main(sys.argv[3:]))'),
                    str(ROOT / 'scripts'), str(decl), FROM, TO, str(b), str(h)], capture_output=True, text=True)
                self.assertEqual(out.returncode, code, out.stdout + out.stderr)
                self.assertIn(f'title={title}', out.stdout)

    def test_the_repository_file_is_well_formed(self):
        entries = D.load()
        self.assertEqual(D.duplicates(entries), [], 'a to_digest is declared twice in the repository file')
        for entry in entries:
            self.assertEqual(D.problems(entry) + D.revert_problems(entry, entries), [], entry.get('id'))


# Release review 2026-11-26: deploy-worker deploys only main, so a worker rollback is a fix-forward PR whose identity
# change B -> A undoes an entry A -> B; A is already a to_digest. Only the EXACT revert of one named entry may repeat it.
INTRO = {**ENTRY, 'id': 'introduces-from', 'from_digest': 'd1655f30' + '0' * 56, 'to_digest': FROM,
         'added': [], 'changed': ['omni_prod/x.py']}                       # the earlier entry whose to_digest is FROM
REVERT = {**ENTRY, 'id': '335-part-1-revert', 'revert_of': '335-part-1', 'from_digest': TO, 'to_digest': FROM,
          'added': [], 'removed': ['omni_prod/opening_hours.py'],
          'changed': ['omni_prod/fact_canon.py', 'omni_prod/skills_runtime.py'], 'data_changed': [],
          'reason': 'roll the worker back to before 335-part-1', 'author': 'claude', 'reviewer': 'shai'}


def back(entries, base_digest=TO, head_digest=FROM):
    """Match the change HEAD -> BASE (the revert) against a declarations list."""
    return D.match(entries, base_digest, head_digest, D.diff(HEAD, BASE))


class RevertEntries(unittest.TestCase):
    def test_a_to_b_then_b_to_a_with_revert_of_passes(self):
        # step 1: A -> B is declared by ENTRY, after INTRO introduced A
        self.assertEqual(D.match([ENTRY, INTRO], FROM, TO, D.diff(BASE, HEAD))[0], ENTRY)
        # step 2: B -> A, declared by an exact revert of ENTRY; FROM is now INTRO's and REVERT's to_digest
        entries = [INTRO, ENTRY, REVERT]
        self.assertEqual(D.duplicates(entries), [])
        self.assertEqual(D.revert_problems(REVERT, entries), [])
        entry, why = back(entries)
        self.assertEqual(entry, REVERT, why)

    def test_a_repeat_without_revert_of_is_refused(self):
        plain = {k: v for k, v in REVERT.items() if k != 'revert_of'}
        entry, why = back([INTRO, ENTRY, plain])
        self.assertIsNone(entry)
        self.assertEqual(why, ['to_digest declared more than once: ' + FROM[:12]])

    def test_revert_of_naming_a_missing_entry_is_refused(self):
        for target, said in (('no-such-entry', 'revert_of no-such-entry: names 0 entries, not exactly one'),
                             ('', 'revert_of is empty'),
                             ('335-part-1-revert', 'revert_of 335-part-1-revert: that entry is not earlier in the file '
                                                   'than this revert')):                      # missing, empty, itself
            bad = {**REVERT, 'revert_of': target}
            self.assertEqual(D.revert_problems(bad, [INTRO, ENTRY, bad]), [said], target)
            entry, why = back([INTRO, ENTRY, bad])
            self.assertIsNone(entry, target)
            self.assertIn('to_digest declared more than once', why[0])
        twice = {**ENTRY, 'id': '335-part-1', 'to_digest': 'b' * 64}       # an ambiguous id names no single entry
        self.assertIn('revert_of 335-part-1: names 2 entries, not exactly one',
                      D.revert_problems(REVERT, [INTRO, ENTRY, twice, REVERT]))

    def test_mismatched_digests_are_refused(self):
        for bad in ({**REVERT, 'from_digest': 'f' * 64}, {**REVERT, 'to_digest': INTRO['from_digest']},
                    {**REVERT, 'from_digest': FROM, 'to_digest': TO}):     # another B, another A, not swapped
            self.assertTrue(any('not the swap' in p for p in D.revert_problems(bad, [INTRO, ENTRY, bad])), bad)
            self.assertIsNone(D.match([INTRO, ENTRY, bad], bad['from_digest'], bad['to_digest'],
                                      D.diff(HEAD, BASE))[0])

    def test_mismatched_path_sets_are_refused(self):
        for key, value in (('removed', []), ('added', ['omni_prod/opening_hours.py']),
                           ('changed', ['omni_prod/fact_canon.py']), ('data_changed', ['omni_prod/assets/app.js'])):
            bad = {**REVERT, key: value}
            self.assertTrue(any(p.startswith(f'revert_of 335-part-1: {key} ') for p in
                                D.revert_problems(bad, [INTRO, ENTRY, bad])), key)
            entry, why = back([INTRO, ENTRY, bad])
            self.assertIsNone(entry, key)
            self.assertIn('to_digest declared more than once', why[0])

    def test_a_revert_is_signed_like_any_entry(self):
        for reviewer in ('', 'claude', 'pending', 'author'):
            entry, why = back([INTRO, ENTRY, {**REVERT, 'reviewer': reviewer}])
            self.assertIsNone(entry, reviewer)
            self.assertIn('to_digest declared more than once', why[0])       # an unsigned revert is a plain repeat

    def test_a_reverted_entry_is_consumed(self):
        # one revert per entry: two reverts of the same entry refuse the file
        again = {**REVERT, 'id': 'second-revert'}
        self.assertIn('revert_of 335-part-1: that entry is reverted by more than one entry',
                      D.revert_problems(REVERT, [INTRO, ENTRY, REVERT, again]))
        self.assertIsNone(back([INTRO, ENTRY, REVERT, again])[0])
        # re-landing A -> B after the revert: the consumed ENTRY never matches again ...
        entry, why = D.match([INTRO, ENTRY, REVERT], FROM, TO, D.diff(BASE, HEAD))
        self.assertIsNone(entry)
        self.assertIn('335-part-1: reverted by 335-part-1-revert, consumed (never matches again)', why)
        # ... only a revert of the revert does, and it consumes the revert in turn
        reland = {**ENTRY, 'id': 'reland', 'revert_of': '335-part-1-revert', 'reviewer': 'shai'}
        entries = [INTRO, ENTRY, REVERT, reland]
        self.assertEqual(D.duplicates(entries), [])
        self.assertEqual(D.match(entries, FROM, TO, D.diff(BASE, HEAD))[0], reland)
        self.assertIsNone(back(entries)[0])

    def test_revert_of_is_the_id_exactly(self):
        # review of #537: " 335-part-1" and "335-part-1 " were two exact reverts of one entry
        for spaced in (' 335-part-1', '335-part-1 ', '\t335-part-1'):
            bad = {**REVERT, 'id': 'spaced', 'revert_of': spaced}
            self.assertEqual(D.revert_problems(bad, [INTRO, ENTRY, bad]),
                             [f'revert_of {spaced!r} is not an id exactly (a string without surrounding white space)'])
        two = [INTRO, ENTRY, {**REVERT, 'id': 'r1', 'revert_of': '335-part-1 '}, {**REVERT, 'id': 'r2', 'revert_of': ' 335-part-1'}]
        self.assertIsNone(back(two)[0])
        # an exact revert sees a spaced second revert of the same entry (compared stripped)
        spaced = {**REVERT, 'id': 'spaced', 'revert_of': '335-part-1 '}
        self.assertIn('revert_of 335-part-1: that entry is reverted by more than one entry',
                      D.revert_problems(REVERT, [INTRO, ENTRY, REVERT, spaced]))
        self.assertIsNone(back([INTRO, ENTRY, REVERT, spaced])[0])

    def test_the_reverted_entry_must_be_valid_and_earlier(self):
        # review of #537: the target was never validated
        unsigned = {**ENTRY, 'reviewer': 'claude'}
        self.assertIn('revert_of 335-part-1: the reverted entry is not a valid signed entry (no reviewer other than '
                      'the author)', D.revert_problems(REVERT, [INTRO, unsigned, REVERT]))
        self.assertIsNone(back([INTRO, unsigned, REVERT])[0])
        # a target that is a revert must be the exact revert of its own target
        badrev = {**REVERT, 'changed': ['omni_prod/fact_canon.py']}               # not the swap of ENTRY
        reland = {**ENTRY, 'id': 'reland', 'revert_of': '335-part-1-revert', 'reviewer': 'shai',
                  'changed': ['omni_prod/fact_canon.py']}                           # the exact swap of badrev
        entries = [INTRO, ENTRY, badrev, reland]
        self.assertEqual(D.revert_problems(reland, entries), ['revert_of 335-part-1-revert: the reverted entry is a '
                                                              'revert but not the exact revert of its own target'])
        self.assertIsNone(D.match(entries, FROM, TO, {**D.diff(BASE, HEAD), 'changed': ['omni_prod/fact_canon.py']})[0])
        # the target stands earlier in the file: a revert above its target is refused
        self.assertEqual(D.revert_problems(REVERT, [INTRO, REVERT, ENTRY]),
                         ['revert_of 335-part-1: that entry is not earlier in the file than this revert'])
        self.assertIsNone(back([INTRO, REVERT, ENTRY])[0])

    def test_only_an_exact_revert_consumes(self):
        # review of #537: reverted_by() reading any revert_of passed every test. A revert that is not exact (here: not
        # the swap, and a digest of its own, so the file is not refused whole) consumes nothing: ENTRY still matches.
        stray = {**REVERT, 'id': 'stray', 'to_digest': 'c' * 64}
        entries = [INTRO, ENTRY, stray]
        self.assertEqual(D.duplicates(entries), [])
        self.assertTrue(D.revert_problems(stray, entries))
        self.assertEqual(D.reverted_by(entries), {})
        self.assertEqual(D.match(entries, FROM, TO, D.diff(BASE, HEAD))[0], ENTRY)

    def test_a_plain_entry_may_not_repeat_a_reverts_digest(self):
        # review of #537: with no plain entry introducing FROM, a plain entry below the revert repeated its to_digest
        self.assertEqual(D.duplicates([ENTRY, REVERT]), [])                     # FROM predates the file: fine
        self.assertEqual(back([ENTRY, REVERT])[0], REVERT)
        plain = {**ENTRY, 'id': 'plain-to-from', 'from_digest': 'e' * 64, 'to_digest': FROM}
        self.assertEqual(D.duplicates([ENTRY, REVERT, plain]), [FROM])
        self.assertIsNone(back([ENTRY, REVERT, plain])[0])

    def test_the_cli_passes_a_revert_and_refuses_it_without_revert_of(self):
        plain = {k: v for k, v in REVERT.items() if k != 'revert_of'}
        with tempfile.TemporaryDirectory() as tmp:
            b, h, decl = Path(tmp, 'b.json'), Path(tmp, 'h.json'), Path(tmp, 'd.json')
            b.write_text(json.dumps(HEAD)); h.write_text(json.dumps(BASE))   # base is B, head is A
            for entries, code, title in (([INTRO, ENTRY, REVERT], 0, 'identity change declared'),
                                         ([INTRO, ENTRY, plain], 1, 'identity change not declared')):
                decl.write_text(json.dumps({'changes': entries}))
                out = subprocess.run([sys.executable, '-c', (
                    'import sys; sys.path.insert(0, sys.argv[1]); import identity_declared as D; from pathlib import Path; '
                    'D.DECLARATIONS = Path(sys.argv[2]); sys.exit(D.main(sys.argv[3:]))'),
                    str(ROOT / 'scripts'), str(decl), TO, FROM, str(b), str(h)], capture_output=True, text=True)
                self.assertEqual(out.returncode, code, out.stdout + out.stderr)
                self.assertIn(f'title={title}', out.stdout)
            self.assertIn('to_digest declared more than once', out.stdout)


if __name__ == '__main__':
    unittest.main()


SAME = FROM
SRC = {'id': '570-source-only', 'kind': 'source_only', 'from_digest': SAME, 'to_digest': SAME,
       'added': ['omni_prod/opening_hours.py'], 'removed': [],
       'changed': ['omni_prod/fact_canon.py', 'omni_prod/skills_runtime.py'], 'data_changed': [],
       'reason': 'flag-only branches; the flag-off pipeline is unchanged', 'author': 'claude', 'reviewer': 'shai',
       'reviewed_at': '2026-11-28'}


class SourceOnly(unittest.TestCase):
    """The owner, 2026-11-28 (#570, option 1): the gate code changed, the flag-off digest did not."""

    def test_the_exact_signed_source_only_entry_passes_when_the_digest_is_unchanged(self):
        self.assertTrue(ok(SRC, base_digest=SAME, head_digest=SAME))

    def test_it_may_repeat_a_digest_another_entry_declared(self):
        # the anchor's digest is the to_digest of the entry that introduced it: that is not a repeat here
        entry, _ = D.match([{**ENTRY, 'to_digest': SAME, 'from_digest': TO}, SRC], SAME, SAME, D.diff(BASE, HEAD))
        self.assertEqual(entry['id'], SRC['id'])

    def test_it_never_matches_a_change_of_behaviour(self):
        self.assertFalse(ok(SRC, base_digest=SAME, head_digest=TO))
        self.assertFalse(ok({**SRC, 'to_digest': TO}, base_digest=SAME, head_digest=TO))   # two digests: refused
        self.assertTrue(D.problems({**SRC, 'to_digest': TO}))

    def test_the_path_sets_are_exact(self):
        self.assertFalse(ok({**SRC, 'changed': ['omni_prod/fact_canon.py']}, base_digest=SAME, head_digest=SAME))
        more = {**HEAD, 'files': {**HEAD['files'], 'omni_prod/x.py': 'c2'}}
        self.assertFalse(ok(SRC, base_digest=SAME, head_digest=SAME, head=more))

    def test_it_is_signed_like_any_entry(self):
        for reviewer in ('', 'claude', 'pending'):
            self.assertFalse(ok({**SRC, 'reviewer': reviewer}, base_digest=SAME, head_digest=SAME), reviewer)

    def test_the_same_source_only_change_is_declared_once(self):
        again = {**SRC, 'id': 'copy'}
        self.assertTrue(D.duplicates([SRC, again]))
        self.assertIsNone(D.match([SRC, again], SAME, SAME, D.diff(BASE, HEAD))[0])

    def test_an_unknown_kind_an_empty_change_or_a_revert_is_refused(self):
        self.assertFalse(ok({**SRC, 'kind': 'source-only'}, base_digest=SAME, head_digest=SAME))
        self.assertFalse(ok({**SRC, 'revert_of': '335-part-1'}, base_digest=SAME, head_digest=SAME))
        self.assertTrue(D.problems({**SRC, 'revert_of': '335-part-1'}))
        empty = {**SRC, 'added': [], 'changed': []}
        self.assertTrue(D.problems(empty))
