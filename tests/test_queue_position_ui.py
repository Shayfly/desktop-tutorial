"""2026-11-15: the build track says how many jobs are ahead of a queued build (app.js queuedNote, run in node)."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / 'omni_prod' / 'assets' / 'app.js'


def notes(builds, lang):
    src = APP.read_text()
    js = (src[src.index('const T ='):src.index('const S =')] + f'\nconst S={{lang:{json.dumps(lang)}}};\n'
          'function t(k){return T[S.lang][k];}\n' + re.search(r'function queuedNote\(.*?\n\}', src, re.S).group() +
          f'\nconsole.log(JSON.stringify({json.dumps(builds)}.map(queuedNote)));')
    return json.loads(subprocess.run(['node', '-e', js], capture_output=True, text=True, check=True).stdout)


@unittest.skipUnless(shutil.which('node'), 'node runs app.js')
class QueuedNote(unittest.TestCase):
    def test_the_count_from_the_server_is_shown(self):
        self.assertEqual(notes([{'queue_ahead': 1}, {'queue_ahead': 3}, {'queue_ahead': 0}], 'he'),
                         ['ממתין בתור: עבודה אחת לפני הבנייה שלך', 'ממתין בתור: 3 עבודות לפני הבנייה שלך',
                          'ממתין בתור: הבנייה שלך הבאה בתור'])
        self.assertEqual(notes([{'queue_ahead': 2}], 'en'), ['Waiting in queue: 2 jobs ahead of your build'])

    def test_no_count_is_the_plain_line_never_a_guess(self):
        self.assertEqual(notes([{}, {'queue_ahead': None}, {'queue_ahead': -1}, {'queue_ahead': 1.5}, None], 'he'),
                         ['ממתין בתור'] * 5)

    def test_the_track_uses_it_for_a_queued_build(self):
        self.assertIn("if (status === 'queued') return push(t(key), 'pending', idx === 0 ? queuedNote(b) : note);",
                      APP.read_text())


if __name__ == '__main__':
    unittest.main()
