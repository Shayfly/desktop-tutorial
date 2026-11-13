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
            self.assertEqual(D.problems(entry), [], entry.get('id'))


if __name__ == '__main__':
    unittest.main()
