"""The page-type typology of a website (warehouse 123, released by the owner 2026-11-27, inbox/004).

An output profile says WHAT the engine builds (website, web_app). For a website this module says WHICH KIND of page:
business or service, portfolio, event, community, documentation, product, personal page, landing. One typed registry
(page_types.json, data, read here), one deterministic detector from the approved brief, and one skeleton per type that
section_library consumes: the sections, their order, the image-to-text ratio, and the threshold table the gates use.

The stable key is `page_type` (a key of `TYPES`). Item 122 (required fields per type) keys onto it.

Honesty rules, the same as the rest of the output platform:
  * The detector reads only the customer's own words in the approved prompt (site_content.facts.customer_text) and
    never guesses. No signal, or two types with the same score, is `page_type=None` with `found` saying which: the
    caller asks the customer; nothing is defaulted. A family that is not a page (web_app) is `not_a_page`.
  * Every skeleton is source 'seed' until a corpus run replaces it; `check` refuses a 'corpus' entry with no pages.
  * A skeleton names only keys the section library has. A section the type needs and the library lacks is listed in
    `not_in_library`, never faked. An unknown type or a None page_type raises UnknownPageType.
"""
from __future__ import annotations

import copy
import html as _html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

DATA = Path(__file__).resolve().parent / 'page_types.json'
SOURCES = ('seed', 'corpus')
METRICS = ('sections', 'text_chars', 'images', 'image_text', 'ctas', 'h1')
FOUND = ('named', 'none', 'tie', 'not_a_page')
_WEIGHTS = ('3', '2', '1')
_NEGATIONS = frozenset({'בלי', 'ללא', 'אין', 'לא', 'without', 'no'})


class UnknownPageType(LookupError):
    """A page type the registry does not have (or None). Never defaulted."""


def _load() -> dict:
    return json.loads(DATA.read_text(encoding='utf-8'))


def check(data: dict, section_keys=None) -> None:
    """The data tells the truth, or the module does not load. `section_keys` (the section library's keys) is given by
    the library at its own import, so a skeleton can never name a section the library does not render."""
    if data.get('schema') != '148ai.page_types/1':
        raise RuntimeError(f"page_types.json: unknown schema {data.get('schema')!r}")
    types = data.get('types') or {}
    if len(types) != 8:
        raise RuntimeError(f'page_types.json: the typology has eight types, not {sorted(types)}')
    for key in ('weak_cap', 'min_score'):
        if not isinstance(data.get(key), int) or data[key] < 1:
            raise RuntimeError(f'page_types.json: {key} must be a positive integer')
    for name, t in types.items():
        where = f'page type {name!r}'
        if t.get('source') not in SOURCES:
            raise RuntimeError(f"{where}: source must be one of {SOURCES}, not {t.get('source')!r}")
        pages = t.get('corpus_pages') or []
        if t['source'] == 'corpus' and not 5 <= len(pages) <= 8:
            raise RuntimeError(f'{where}: a corpus skeleton is extracted from five to eight pages, not {len(pages)}')
        sections = t.get('sections') or []
        if not sections or sections[0] != 'hero' or len(set(sections)) != len(sections):
            raise RuntimeError(f'{where}: sections must start with hero and repeat nothing: {sections}')
        if not set(t.get('required_sections') or ()) <= set(sections) or not t.get('required_sections'):
            raise RuntimeError(f'{where}: required_sections must be a non-empty subset of sections')
        if section_keys is not None:
            unknown = sorted(set(sections) - set(section_keys))
            if unknown:
                raise RuntimeError(f'{where}: sections {unknown} are not in the section library')
            faked = sorted(set(t.get('not_in_library') or ()) & set(section_keys))
            if faked:
                raise RuntimeError(f'{where}: {faked} are listed as missing from the library but it has them')
        if not isinstance(t.get('image_text_target'), (int, float)) or t['image_text_target'] < 0:
            raise RuntimeError(f'{where}: image_text_target must be a number >= 0')
        th = t.get('thresholds') or {}
        if set(th) != set(METRICS):
            raise RuntimeError(f'{where}: thresholds must be exactly {METRICS}, not {sorted(th)}')
        for metric, pair in th.items():
            if not (isinstance(pair, list) and len(pair) == 2 and all(isinstance(x, (int, float)) for x in pair)
                    and 0 <= pair[0] <= pair[1]):
                raise RuntimeError(f'{where}: threshold {metric} must be [min, max] with 0 <= min <= max, not {pair!r}')
        cues = t.get('cues') or {}
        if set(cues) != set(_WEIGHTS) or not cues['3']:
            raise RuntimeError(f'{where}: cues must have the weights {_WEIGHTS}, with at least one strong cue')
        for label in ('label_he', 'label_en'):
            if not str(t.get(label) or '').strip():
                raise RuntimeError(f'{where}: {label} is empty')


_DATA = _load()
check(_DATA)
TYPES: tuple[str, ...] = tuple(_DATA['types'])
UNIT: dict = _DATA['unit']


def skeleton(page_type) -> dict:
    """The skeleton of one type (a copy: nobody edits the registry through it). None or an unknown type raises."""
    if page_type not in _DATA['types']:
        raise UnknownPageType(f'no page type {page_type!r}; the registry has {list(TYPES)}')
    t = copy.deepcopy(_DATA['types'][page_type])
    t.pop('cues')
    return {'page_type': page_type, **t}


def thresholds(page_type) -> dict:
    return skeleton(page_type)['thresholds']


# --- the detector ----------------------------------------------------------------------------------------------

_HEB = '֐-׿'


def _norm(text: str) -> str:
    t = _html.unescape(text or '').lower()
    for a, b in (('׳', "'"), ('’', "'"), ('‘', "'"), ('״', '"'), ('”', '"'), ('“', '"'), ('–', '-'), ('—', '-')):
        t = t.replace(a, b)
    return re.sub(r'\s+', ' ', t)


def _pattern(cue: str) -> re.Pattern:
    # a whole word or phrase, after at most two Hebrew prefix letters ("לעסק", "בבלוג"), never inside another word
    body = r'\s+'.join(re.escape(w) for w in cue.lower().split(' '))
    return re.compile(r'(?<![\w' + _HEB + r'])[הובשלמכ]{0,2}' + body + r'(?![\w' + _HEB + r'])')


_PATTERNS = {name: {w: [(c, _pattern(c)) for c in sorted(cues, key=lambda c: (-len(c), c))] for w, cues in t['cues'].items()}
             for name, t in _DATA['types'].items()}


def _negated(text: str, start: int) -> bool:
    words = re.findall(r'[\w' + _HEB + r"']+", text[max(0, start - 30):start])[-3:]
    return any(w in _NEGATIONS for w in words)


@dataclass(frozen=True)
class Detection:
    """`page_type` is the stable key (a key of TYPES) or None; `found` says why: named (one type scored highest), none
    (no type reached the minimum score), tie (the top score is shared; `candidates` lists them), not_a_page."""
    page_type: str | None
    found: str
    scores: dict = field(default_factory=dict)
    matched: dict = field(default_factory=dict)       # type -> the cues that counted
    candidates: tuple = ()

    def to_dict(self) -> dict:
        return {'page_type': self.page_type, 'found': self.found, 'scores': dict(self.scores),
                'matched': {k: list(v) for k, v in self.matched.items()}, 'candidates': list(self.candidates)}


def detect_text(text: str) -> Detection:
    """The page type the customer's words name. Deterministic: the same text always gives the same answer."""
    t = _norm(text)
    scores, matched = {}, {}
    for name, by_weight in _PATTERNS.items():
        total, weak, covered, hits = 0, 0, [], []
        for w in _WEIGHTS:
            for cue, pat in by_weight[w]:
                # the first occurrence that is not negated ("בלי גלריה") and not inside a longer cue already counted
                # ("קפה" inside "בית קפה"): one cue, one count
                spans = [m.span() for m in pat.finditer(t) if not _negated(t, m.start())
                         and not any(a <= m.start() and m.end() <= b for a, b in covered)]
                if not spans:
                    continue
                covered.extend(spans)
                hits.append(cue)
                if w == '1':
                    weak += 1
                else:
                    total += int(w)
        scores[name] = total + min(weak, _DATA['weak_cap'])
        if hits:
            matched[name] = hits
    top = max(scores.values())
    if top < _DATA['min_score']:
        return Detection(None, 'none', scores, matched)
    leaders = tuple(n for n in TYPES if scores[n] == top)
    if len(leaders) > 1:
        return Detection(None, 'tie', scores, matched, leaders)
    return Detection(leaders[0], 'named', scores, matched, leaders)


def detect(prompt: str) -> Detection:
    """The page type of an APPROVED prompt: the customer's request and the brief lines that quote the customer
    (site_content.facts.customer_text), never 148AI's own wording of the brief."""
    from ..site_content import facts as Fx
    return detect_text(Fx.customer_text(prompt))


# --- the gates' measure ----------------------------------------------------------------------------------------

def measure(doc: str) -> dict:
    """What the threshold table is judged on, read from the rendered page (<main> only)."""
    body = re.sub(r'<(script|style)\b.*?</\1>', '', doc, flags=re.S | re.I)
    m = re.search(r'<main\b.*?</main>', body, flags=re.S | re.I)
    main = m.group(0) if m else body
    text = re.sub(r'\s+', ' ', _html.unescape(re.sub(r'<[^>]+>', ' ', main))).strip()
    images = len(re.findall(r'<img\b', main, flags=re.I))
    chars = len(text)
    return {'sections': len(re.findall(r'<section\b', main, flags=re.I)), 'text_chars': chars, 'images': images,
            'image_text': round(images * 1000 / chars, 3) if chars else 0.0,
            'ctas': len(re.findall(r'<(?:a|button)\b[^>]*\bclass="[^"]*\bbtn\b', main, flags=re.I)),
            'h1': len(re.findall(r'<h1\b', body, flags=re.I))}


def judge(page_type, doc: str) -> list[str]:
    """The metrics of a rendered page that fall outside its type's threshold table, one sentence each (empty: inside)."""
    table, got = thresholds(page_type), measure(doc)
    return [f'{metric}={got[metric]} is outside {page_type}\'s [{lo}, {hi}]'
            for metric, (lo, hi) in table.items() if not lo <= got[metric] <= hi]
