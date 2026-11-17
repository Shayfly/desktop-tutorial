"""Which edits the repairer may make to a test the builder wrote (DECISIONS 8, the owner 2026-11-17).

"148 doors" (bld_77899122): the builder's test looked for the phone in the customer's form and the app stored it
normalised; the repairer was told never to touch tests, so three rounds burned. The owner's decision, restricted:

1. A test whose changed line carries a CUSTOMER FACT (phone, price, address, opening hours) is never edited by the
   repairer: the customer's words are the truth, so the code changes, not the test.
2. Any other edit to a test the builder wrote IN THIS BUILD may only change an EXPECTED VALUE: the same assert line
   with different literals. No assert is removed, added or rewritten; no other line of the test changes.
3. Every allowed edit is counted in the build report (`test_edits`).
4. The same expected value fixed twice in one build escalates: the loop stops (`test_value_fixed_twice`).

Anything else is reverted to the round's version of the file, and the repairer is told why.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

from .repair_contracts import _TEST_FILE

_STRING = re.compile(r'''(?:[rbuf]{0,2})("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')''', re.I)
_NUMBER = re.compile(r'(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])')
_ASSERTS = re.compile(r'^\s*(?:assert\b|self\.assert\w*\(|expect\()')

_PHONE_DIGITS = re.compile(r'(?<!\d)(?:\+?972|0)[\d\-\s]{7,12}\d(?!\d)')
_HOURS = re.compile(r'\b\d{1,2}:\d{2}\b')
_PRICE = re.compile(r'(?:₪\s*(\d[\d,.]*)|(\d[\d,.]*)\s*(?:₪|ש"ח|ש״ח|שקלים|שקל|ils|nis))', re.I)
_STREET = re.compile(r"(?:רחוב|רח['׳]|שדרות|שד['׳]|דרך|סמטת|כיכר)\s+((?:[֐-׿\"'׳״-]+\s+){0,3}?)(\d{1,4})")


@dataclass
class CustomerFacts:
    phones: set = field(default_factory=set)       # national digits, e.g. 048123456
    hours: set = field(default_factory=set)        # HH:MM, zero-padded
    prices: set = field(default_factory=set)       # digits only
    streets: set = field(default_factory=set)      # street-name words (3+ letters)

    def found_in(self, line: str) -> str:
        """The kind of customer fact `line` carries, or ''."""
        digits = re.sub(r'\D', '', line)
        if any(p in digits or p.lstrip('0') in digits for p in self.phones):
            return 'phone'
        if any(_pad(h) in self.hours for h in _HOURS.findall(line)):
            return 'hours'
        nums = {re.sub(r'\D', '', n) for n in _NUMBER.findall(line)}
        if self.prices & nums:
            return 'price'
        if any(w in line for w in self.streets):
            return 'address'
        return ''


def _pad(h: str) -> str:
    a, b = h.split(':')
    return f'{int(a):02d}:{b}'


def customer_facts(text: str) -> CustomerFacts:
    """The facts the customer gave, from the request and the approved brief they confirmed."""
    text = text or ''
    facts = CustomerFacts()
    for m in _PHONE_DIGITS.finditer(text):
        d = re.sub(r'\D', '', m.group(0))
        if d.startswith('972'):
            d = '0' + d[3:]
        if 9 <= len(d) <= 10:
            facts.phones.add(d)
    facts.hours = {_pad(h) for h in _HOURS.findall(text)}
    for m in _PRICE.finditer(text):
        d = re.sub(r'\D', '', (m.group(1) or m.group(2) or '').split('.')[0])
        if d:
            facts.prices.add(d)
    for m in _STREET.finditer(text):
        facts.streets |= {w.strip('"\'׳״') for w in m.group(1).split() if len(w.strip('"\'׳״')) >= 3}
    return facts


def _skeleton(line: str) -> str:
    return _NUMBER.sub('N', _STRING.sub('S', line)).strip()


def _literals(line: str) -> tuple:
    return tuple(_STRING.findall(line)) + tuple(_NUMBER.findall(_STRING.sub('S', line)))


@dataclass(frozen=True)
class Verdict:
    allowed: bool
    reason: str
    edits: tuple = ()      # ((skeleton, old literals, new literals), ...)


def judge(old: str, new: str, facts: CustomerFacts) -> Verdict:
    """May the repairer turn test file `old` into `new`?"""
    a, b = old.splitlines(), new.splitlines()
    edits = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag == 'equal':
            continue
        if tag != 'replace' or (i2 - i1) != (j2 - j1):
            return Verdict(False, 'a line of the test was added or removed; only an expected value may change')
        for x, y in zip(a[i1:i2], b[j1:j2]):
            if not _ASSERTS.match(x):
                return Verdict(False, f'a non-assert line changed: {x.strip()[:80]}')
            if _skeleton(x) != _skeleton(y):
                return Verdict(False, f'an assert was rewritten, not just its expected value: {x.strip()[:80]}')
            kind = facts.found_in(x)
            if kind:
                return Verdict(False, f'the assert checks the customer\'s {kind}; the code must show it as given')
            edits.append((_skeleton(x), _literals(x), _literals(y)))
    return Verdict(True, 'expected value only', tuple(edits))


@dataclass
class TestEditLedger:
    """One build: what the repairer changed in the builder's tests, and whether a value came back twice."""
    builder_tests: frozenset
    facts: CustomerFacts
    counted: list = field(default_factory=list)       # build report: every allowed edit
    refused: list = field(default_factory=list)
    _seen: dict = field(default_factory=dict)
    escalate: str = ''

    def review(self, before: dict, after: dict) -> tuple[dict, list[str]]:
        """Returns the candidate with every refused test edit reverted, and a note per refusal."""
        out, notes = dict(after), []
        for path in sorted(set(before) | set(after)):
            if not _TEST_FILE.search(path) or before.get(path) == after.get(path):
                continue
            old, new = before.get(path), after.get(path)
            if old is None:
                continue                                     # a new test file only adds checks
            if new is None or path not in self.builder_tests:
                verdict = Verdict(False, 'deleted' if new is None else 'not a test the builder wrote in this build')
            else:
                verdict = judge(old, new, self.facts)
            if not verdict.allowed:
                out[path] = old
                self.refused.append({'path': path, 'reason': verdict.reason})
                notes.append(f'{path}: your change to this test was reverted ({verdict.reason}). Fix the product code.')
                continue
            for skel, was, now in verdict.edits:
                key = (path, skel)
                self._seen[key] = self._seen.get(key, 0) + 1
                self.counted.append({'path': path, 'assert': skel[:160], 'old': list(was), 'new': list(now),
                                     'times': self._seen[key]})
                if self._seen[key] >= 2 and not self.escalate:
                    self.escalate = f'{path}: the same expected value was fixed twice ({skel[:120]})'
        return out, notes

    def evidence(self) -> dict:
        return {'counted': len(self.counted), 'edits': self.counted[-40:], 'refused': self.refused[-40:],
                'escalated': self.escalate or None}
