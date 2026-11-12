"""Mutation tests for omni_prod/intake/decision.py (Michael 2026-11-11: build the mutants, do not describe them).

Each mutant is a one-line change to the REAL source, executed as a throw-away module. The probe for each rule must
pass on the real module and FAIL on its mutant: if a refactor makes a probe blind, this file goes red.
"""
from __future__ import annotations

import sys
import types
import unittest
from dataclasses import replace
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / 'omni_prod' / 'intake' / 'decision.py').read_text(encoding='utf-8')
RAW = 'תבנה לי דף לחנות הפרחים שלי'


def load(mutation: tuple[str, str] | None = None, name: str = 'real'):
    src = SOURCE
    if mutation is not None:
        old, new = mutation
        assert src.count(old) == 1, f'mutation anchor not found exactly once: {old!r}'
        src = src.replace(old, new)
    mod = types.ModuleType(f'_decision_mutant_{name}')
    sys.modules[mod.__name__] = mod             # dataclasses look their module up while the class is created
    try:
        exec(compile(src, f'<decision {name}>', 'exec'), mod.__dict__)
    finally:
        sys.modules.pop(mod.__name__, None)
    return mod


def site(D, **art_over):
    aid = D.new_artifact_id(now_ms=1_762_860_000_000, randomness=bytes(range(10)))
    art = D.ArtifactIntent(id=aid, kind=D.from_button('site'), purpose=D.from_text('דף'), audience=D.from_text('לקוחות'),
                           must_include=D.from_text(['שעות']), persistence=D.from_button('none'),
                           requires_auth=D.from_button(False), personal_data=D.from_button('no'))
    art = replace(art, **art_over)
    return D.IntakeDecision(raw_brief=RAW, raw_brief_sha256=D.sha256(RAW), artifacts=(art,),
                            shared=D.Shared(tone=D.from_text('חם'), brand_name=D.from_text('שושנת')))


def stops(D, dec):
    return [v for v in D.validate(dec) if v.stop]


# probe: True when the rule holds
PROBES = {
    'gaps are derived (G1)': (
        ('    return tuple(out)\n', '    return ()  # MUTANT\n'),
        lambda D: bool(D.derive_gaps(site(D, persistence=D.MISSING)))),
    'a decision is stated only by a button (G2)': (
        ("elif f.via != 'button' or f.src != 'customer':", 'elif False:  # MUTANT'),
        lambda D: bool(stops(D, site(D, persistence=D.from_text('none'))))),
    'the library exception is an allow-list (F5)': (
        ('if (kind, name) not in LIBRARY_FIXED:', 'if False:  # MUTANT'),
        lambda D: bool(stops(D, site(D, persistence=D.from_library('none'))))),
    'three asks stop (F6)': (
        ('elif g.asked_count >= 3:', 'elif False:  # MUTANT'),
        lambda D: any(v.code == 'GapStuck' and v.stop for v in D.validate(
            replace(site(D), gaps=(D.Gap(site(D).artifacts[0].id + '.persistence', 'build', 'customer', asked_count=3),))))),
    'src and via cannot contradict (14:12)': (
        ('if f.src in SRC and f.via in VIA and (f.src, f.via) not in VALID_PAIRS:', 'if False:  # MUTANT'),
        lambda D: bool(stops(D, site(D, audience=D.Field('x', 'inferred', 'rawBrief', 'text'))))),
    'a fact is never set by a button (§0)': (
        ("    if f.via == 'button':", '    if False:  # MUTANT'),
        lambda D: bool(stops(D, site(D, purpose=D.from_button('דף'))))),
    'rawBrief is bound to its revision (F2)': (
        ("if revision_raw_brief is not None and decision.raw_brief_sha256 != sha256(revision_raw_brief):",
         'if False:  # MUTANT'),
        lambda D: any(v.where == 'raw_brief' for v in D.validate(site(D), revision_raw_brief=RAW + ' אחר'))),
}


class Mutants(unittest.TestCase):
    def test_every_probe_holds_on_the_real_module(self):
        real = load()
        for rule, (_, probe) in PROBES.items():
            with self.subTest(rule):
                self.assertTrue(probe(real), f'{rule}: the probe fails on the REAL module')

    def test_every_mutant_is_caught(self):
        for i, (rule, (mutation, probe)) in enumerate(PROBES.items()):
            with self.subTest(rule):
                self.assertFalse(probe(load(mutation, f'm{i}')), f'{rule}: the mutant SURVIVED -- the probe is blind')


if __name__ == '__main__':
    unittest.main()
