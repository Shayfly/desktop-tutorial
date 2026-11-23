"""Warehouse 134, stage 1: the game runtime, the definition schema, the assembler and game_probe.

The schema tests run everywhere. The browser tests play every sample game in a real Chromium at a computer's width
and at a phone's width, and plant the faults game_probe exists to catch: each planted fault must be reported, or the
probe is the bug. They run in browser-python (tests/test_game_kit_in_ci.py keeps them there), where a skip fails.
"""
from __future__ import annotations

import copy
import json
import os
import unittest
from pathlib import Path

from omni_prod.game_kit import InvalidGame, KINDS, build_html, validate
from omni_prod.game_kit import assemble

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = {k: json.loads((ROOT / 'omni_prod/game_kit/samples' / f'{k}.json').read_text(encoding='utf-8')) for k in KINDS}

try:
    import playwright  # noqa: F401
    HAVE_BROWSER = True
except ImportError:          # pragma: no cover - v24-ci installs no Python playwright; browser-python does
    HAVE_BROWSER = False


def broken(kind, change):
    d = copy.deepcopy(SAMPLES[kind])
    change(d)
    return d


class TheSchema(unittest.TestCase):
    def test_every_sample_is_valid_and_comes_back_unchanged(self):
        for kind, d in SAMPLES.items():
            before = copy.deepcopy(d)
            self.assertIs(validate(d), d, kind)
            self.assertEqual(d, before, f'{kind}: validate changed the definition')

    def problems(self, d):
        with self.assertRaises(InvalidGame) as e:
            validate(d)
        return ' | '.join(e.exception.problems)

    def test_an_unknown_key_is_refused_not_ignored(self):
        self.assertIn("unknown key 'gravity'", self.problems(broken('platformer', lambda d: d['player'].update(gravity=3))))
        self.assertIn("unknown key 'script'", self.problems(broken('runner', lambda d: d.update(script='alert(1)'))))

    def test_a_missing_key_is_refused_not_defaulted(self):
        self.assertIn("missing 'lives'", self.problems(broken('shooter', lambda d: d['player'].pop('lives'))))
        self.assertIn("missing 'lose'", self.problems(broken('match', lambda d: d['texts'].pop('lose'))))

    def test_out_of_range_and_wrong_types(self):
        self.assertIn('player.lives must be', self.problems(broken('runner', lambda d: d['player'].update(lives=9))))
        self.assertIn('time_limit_s must be', self.problems(broken('runner', lambda d: d.update(time_limit_s=True))))
        self.assertIn('palette.bg must be a colour', self.problems(broken('match', lambda d: d['palette'].update(bg='red'))))
        self.assertIn('kind must be one of', self.problems(broken('match', lambda d: d.update(kind='rpg'))))
        self.assertIn('lang must be one of', self.problems(broken('match', lambda d: d.update(lang='fr'))))

    def test_a_platformer_level_that_cannot_be_played_is_refused(self):
        rows = SAMPLES['platformer']['levels'][0]['rows']
        self.assertIn("exactly one start tile 'P', found 2",
                      self.problems(broken('platformer', lambda d: d['levels'][0].update(rows=[rows[0].replace('.', 'P', 1)] + rows[1:]))))
        self.assertIn("exactly one flag tile 'F', found 0",
                      self.problems(broken('platformer', lambda d: d['levels'][0].update(rows=[r.replace('F', '.') for r in rows]))))
        self.assertIn('different widths', self.problems(broken('platformer', lambda d: d['levels'][0].update(rows=rows[:-1] + [rows[-1] + '#']))))
        self.assertIn("unknown tiles ['X']", self.problems(broken('platformer', lambda d: d['levels'][0].update(rows=rows[:-1] + ['X' + rows[-1][1:]]))))
        r0 = next(i for i, r in enumerate(rows) if 'P' in r)
        c = rows[r0].index('P')
        no_floor = [r if i <= r0 else r[:c] + '.' + r[c + 1:] for i, r in enumerate(rows)]
        self.assertIn('no ground under the start tile', self.problems(broken('platformer', lambda d: d['levels'][0].update(rows=no_floor))))

    def test_a_run_longer_than_the_time_limit_is_refused(self):
        self.assertIn('can never be finished', self.problems(broken('runner', lambda d: d.update(time_limit_s=30))))


class TheAssembler(unittest.TestCase):
    def test_the_page_carries_the_tested_runtime_byte_for_byte(self):
        html = build_html(SAMPLES['match'])
        self.assertIn(assemble.RUNTIME, html)
        self.assertIn('<html lang="he" dir="rtl">', html)

    def test_an_invalid_definition_never_becomes_a_page(self):
        with self.assertRaises(InvalidGame):
            build_html(broken('match', lambda d: d.update(kind='rpg')))

    def test_text_cannot_close_the_script(self):
        d = broken('runner', lambda d: d.update(title='</script><script>alert(1)</script>'))
        html = build_html(d)
        self.assertEqual(html.count('</script>'), 2)
        self.assertIn('&lt;/script&gt;', html)


@unittest.skipUnless(HAVE_BROWSER, 'playwright is required to play the games')
class TheGamesPlay(unittest.TestCase):
    """Every sample, at both widths, in a real Chromium. A failure prints what a player would meet."""

    def probe(self, kind, runtime=None):
        from omni_prod.game_kit.probe import probe_html
        saved = assemble.RUNTIME
        try:
            if runtime is not None:
                assemble.RUNTIME = runtime
            d = SAMPLES[kind]
            return probe_html(build_html(d), d)
        finally:
            assemble.RUNTIME = saved

    def test_every_sample_passes_the_probe_on_the_computer_and_the_phone(self):
        for kind in KINDS:
            r = self.probe(kind)
            self.assertTrue(r['ok'], f'{kind}: {r["findings"]}')
            for where in ('computer', 'phone'):
                m = r['measures'][where]
                self.assertGreater(m['score'], 0, f'{kind} {where}')
                self.assertIn(m['end'], ('won', 'lost'), f'{kind} {where}')

    def plant(self, old, new):
        self.assertEqual(assemble.RUNTIME.count(old), 1, old)
        return assemble.RUNTIME.replace(old, new)

    def kinds_of(self, r):
        return {(f['kind'], f['where']) for f in r['findings']}

    def test_a_blank_canvas_is_caught(self):
        r = self.probe('runner', self.plant('    background();\n    if (G.world) KIND.draw();',
                                            '    if (false) { background(); KIND.draw(); }'))
        self.assertIn(('blank_canvas', 'computer'), self.kinds_of(r), r['findings'])

    def test_keys_that_do_nothing_are_caught(self):
        r = self.probe('platformer', self.plant("    press(k, true);\n  });", "  });"))
        self.assertIn(('input_ignored', 'computer'), self.kinds_of(r), r['findings'])

    def test_a_phone_with_no_buttons_is_caught(self):
        r = self.probe('shooter', self.plant('    pad.hidden = false;\n', ''))
        self.assertIn(('no_touch_controls', 'phone'), self.kinds_of(r), r['findings'])

    def test_a_board_too_small_for_a_finger_is_caught(self):
        r = self.probe('match', self.plant("  if (DEF.kind === 'match' && window.innerHeight > window.innerWidth) { W = 540; H = 960; }", ''))
        self.assertIn(('no_touch_controls', 'phone'), self.kinds_of(r), r['findings'])

    def test_a_page_error_is_caught(self):
        r = self.probe('match', self.plant('    G.frames += 1; render();', '    G.frames += 1; render(); if (G.frames === 30) undefinedName();'))
        self.assertIn(('page_error', 'computer'), self.kinds_of(r), r['findings'])

    def test_a_game_that_never_ends_is_caught(self):
        r = self.probe('match', self.plant("    if (G.status === 'playing' && G.time >= DEF.time_limit_s) end(DEF.kind === 'runner');", ''))
        self.assertIn(('never_ends', 'computer'), self.kinds_of(r), r['findings'])

    def test_a_runner_played_to_the_end_shows_the_win_screen(self):
        """The probe accepts a loss as an end; here the win itself is reached through real keys, and its words shown."""
        from playwright.sync_api import sync_playwright
        from omni_prod.game_kit.probe import _launch
        import tempfile
        d = SAMPLES['runner']
        with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
            f = Path(tmp) / 'index.html'
            f.write_text(build_html(d), encoding='utf-8')
            b = _launch(p)
            page = b.new_page(viewport={'width': 1280, 'height': 720})
            page.goto(f.as_uri())
            page.wait_for_function('() => window.__game && window.__game.state().frames > 3')
            page.keyboard.press('Enter')
            status = 'playing'
            for _ in range(int(d['levels'][0]['length_s'] / 0.05) + 40):
                if page.evaluate('() => window.__game.sense()').get('obstacleAhead'):
                    page.keyboard.press('Space')
                status = page.evaluate('() => window.__game.fastForward(0.05)')
                if status != 'playing':
                    break
            text = page.locator('#screen').inner_text()
            b.close()
        self.assertEqual(status, 'won', f'the run ended {status!r}')
        self.assertIn(d['texts']['win'], text)


if __name__ == '__main__':
    unittest.main()
