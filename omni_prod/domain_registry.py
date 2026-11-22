"""The 30 domains as data the platform reads (warehouse 127, the owner 2026-11-22).

A domain file (`docs/domains/<slug>.md`) is written for people. This module turns each one into a record the engine
can use: the mandatory facts (each with the one question to ask the customer and the human reason), the verified
references, and whether the legal and site-vs-app sections say anything. The records are generated, never written by
hand (AGENTS.md rule 3), and the committed file must equal what the generator produces:

    python -m omni_prod.domain_registry --write      # regenerate omni_prod/domain_registry.json
    python -m omni_prod.domain_registry --check      # exit 1 on drift or on a domain that breaks the schema

A domain that breaks the schema fails loudly, naming the domain and the field. Nothing is filled in.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs' / 'domains'
DATA = Path(__file__).with_name('domain_registry.json')

HEADINGS = ('1. Objects', '2. Rules', '3. Mandatory facts', '4. Declared defaults', '5. Failure modes',
            '6. Professional language', '7. Legal', '8. Site vs app', '9. References', '10. Skeletons',
            '11. Not verified')
MIN_REFERENCES, MAX_REFERENCES = 5, 8           # docs/domains/README.md, reference rules 1 and 10

# The engine's business categories (vertical_palettes.json) and the domain file each one reads. None: no domain file
# yet -- said out loud in the build evidence (domain_for returns None and the caller records it), never a neighbour.
CATEGORY_DOMAIN = {
    'accountants': 'accountant', 'aesthetics': 'beauty-cosmetics', 'alcohol': None, 'bakeries': 'cafe-bakery',
    'butcher': 'butcher-deli', 'cabins': 'hotel-guesthouse', 'cafes': 'cafe-bakery', 'catering': None,
    'clinics_physio': 'clinic', 'cosmetics': 'beauty-cosmetics', 'delis': 'butcher-deli', 'dental': 'dentist',
    'design_branding': 'portfolio', 'digital_marketing': None, 'electrical': 'craftsman-renovation',
    'fashion': 'clothing-shop', 'furniture_interior': None, 'gyms': 'fitness-trainer', 'hair_salons': 'hair-salon',
    'hvac': 'craftsman-renovation', 'jewelry': None, 'lawyers': 'lawyer', 'locksmiths': 'craftsman-renovation',
    'moving': None, 'nails': 'beauty-cosmetics', 'personal_training': 'fitness-trainer',
    'photographers': 'photographer', 'plumbing': 'craftsman-renovation', 'realty': 'real-estate-agent',
    'renovation': 'craftsman-renovation', 'restaurants': 'restaurant', 'vets': None,
}


class DomainError(ValueError):
    """A domain file breaks the schema. The message names the domain and the field."""


_SECTION = re.compile(r'^## (\d+\. .+?)\s*$', re.M)
_ROW = re.compile(r'^\|(.+)\|\s*$')
_URL = re.compile(r'https?://[^\s|)]+')


def _sections(text: str) -> dict[str, str]:
    marks = list(_SECTION.finditer(text))
    return {m.group(1): text[m.end():(marks[i + 1].start() if i + 1 < len(marks) else len(text))]
            for i, m in enumerate(marks)}


def _cells(line: str) -> list[str]:
    return [c.strip() for c in _ROW.match(line).group(1).split('|')]


def _facts(body: str, slug: str) -> list[dict]:
    """Every numbered row of every table in section 3. The first table is always needed; a later table is needed only
    under the condition written in the line above it ("Needed only when the product takes online bookings:")."""
    out, condition, tables, last_text, in_table = [], None, 0, '', False
    for line in body.splitlines():
        if _ROW.match(line):
            if not in_table:
                in_table, tables = True, tables + 1
                condition = None if tables == 1 else (last_text.rstrip(':').strip() or None)
            cells = _cells(line)
            if not cells or not re.fullmatch(r'\d+', cells[0]):
                continue                                     # header or separator row
            if len(cells) < 4 or not all(cells[1:4]):
                raise DomainError(f'{slug}: mandatory fact {cells[0]} must have a fact, a question and a reason')
            out.append({'n': int(cells[0]), 'fact': cells[1], 'question': cells[2].strip('"“”'),
                        'why': cells[3], 'when': condition})
        else:
            in_table = False
            if line.strip():
                last_text = line.strip()
    return out


def _references(body: str) -> list[str]:
    urls = []
    for line in body.splitlines():
        if _ROW.match(line):
            cells = _cells(line)
            if cells and re.fullmatch(r'\d+', cells[0]) and len(cells) > 1:
                m = _URL.search(cells[1])
                if m:
                    urls.append(m.group(0).rstrip('.,'))
    return urls


def _terms(body: str, slug: str) -> list[dict]:
    """Section 6: the trade's words. `he_verified` is False when the author marked the Hebrew "not verified" (or left
    it empty): such a word is never handed to a model as the trade's word."""
    out, header = [], None
    for line in body.splitlines():
        if not _ROW.match(line):
            continue
        cells = _cells(line)
        if header is None:
            header = [c.lower() for c in cells]
            if header[:4] != ['english', 'meaning', 'hebrew', 'arabic']:
                raise DomainError(f'{slug}: section "6. Professional language" table must be English | Meaning | '
                                  f'Hebrew | Arabic; found {cells}')
            continue
        if set(''.join(cells)) <= set('-: '):
            continue                                         # the separator row
        en, meaning, he, ar = (cells + ['', '', '', ''])[:4]
        verified = bool(he) and 'not verified' not in he.lower()
        out.append({'en': en, 'meaning': meaning, 'he': he, 'ar': ar, 'he_verified': verified})
    if not out:
        raise DomainError(f'{slug}: section "6. Professional language" has no terms')
    return out


def parse(text: str, slug: str) -> dict:
    """One domain file -> one record. Raises DomainError naming the domain and the field."""
    first = text.splitlines()[0] if text.strip() else ''
    if not first.startswith('# ') or not first[2:].strip():
        raise DomainError(f'{slug}: the first line must be "# <domain name>"')
    sections = _sections(text)
    if tuple(sections) != HEADINGS:
        missing = [h for h in HEADINGS if h not in sections]
        raise DomainError(f'{slug}: headings must be exactly {list(HEADINGS)} in order; '
                          + (f'missing {missing}' if missing else f'found {list(sections)}'))
    for h in ('7. Legal', '8. Site vs app'):
        if not sections[h].strip():
            raise DomainError(f'{slug}: section "{h}" is empty')
    facts = _facts(sections['3. Mandatory facts'], slug)
    if not facts:
        raise DomainError(f'{slug}: no mandatory facts')
    if not any(f['when'] is None for f in facts):
        raise DomainError(f'{slug}: no mandatory fact is needed always')
    refs = _references(sections['9. References'])
    if not MIN_REFERENCES <= len(refs) <= MAX_REFERENCES:
        raise DomainError(f'{slug}: {len(refs)} references; {MIN_REFERENCES} to {MAX_REFERENCES} are required')
    if len(set(refs)) != len(refs):
        raise DomainError(f'{slug}: a reference is listed twice')
    terms = _terms(sections['6. Professional language'], slug)
    return {'slug': slug, 'name': first[2:].strip(), 'mandatory_facts': facts, 'references': refs, 'terms': terms}


def build(docs: Path = DOCS) -> dict:
    files = sorted(p for p in docs.glob('*.md') if p.name != 'README.md')
    if not files:
        raise DomainError(f'no domain files in {docs}')
    domains = {p.stem: parse(p.read_text(encoding='utf-8'), p.stem) for p in files}
    for category, slug in CATEGORY_DOMAIN.items():
        if slug is not None and slug not in domains:
            raise DomainError(f'category {category} points at domain {slug}, which has no file')
    return {'_about': 'Generated by python -m omni_prod.domain_registry --write from docs/domains/*.md. Do not edit.',
            'categories': dict(sorted(CATEGORY_DOMAIN.items())), 'domains': domains}


def load() -> dict:
    return json.loads(DATA.read_text(encoding='utf-8'))


def domain_for(category: str | None) -> dict | None:
    """The domain record for an engine category; None when the category has no domain file (the caller records
    that). An unknown category is an error, never a silent None."""
    if category is None:
        return None
    data = load()
    if category not in data['categories']:
        raise DomainError(f'unknown category {category!r}')
    slug = data['categories'][category]
    return None if slug is None else data['domains'][slug]


MAX_TRADE_WORDS = 40


def trade_words(domain: dict | None) -> list[str]:
    """The trade's Hebrew words a model may be given: only those the author did not mark 'not verified', at most 40."""
    if not domain:
        return []
    return [t['he'] for t in domain['terms'] if t['he_verified']][:MAX_TRADE_WORDS]


def _render(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1) + '\n'


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--write', action='store_true')
    g.add_argument('--check', action='store_true')
    a = ap.parse_args(argv)
    try:
        text = _render(build())
    except DomainError as exc:
        print(f'::error title=domain registry::{exc}')
        return 1
    if a.write:
        DATA.write_text(text, encoding='utf-8')
        print(f'::notice title=domain registry::{len(json.loads(text)["domains"])} domains written')
        return 0
    if not DATA.exists() or DATA.read_text(encoding='utf-8') != text:
        print('::error title=domain registry::omni_prod/domain_registry.json differs from docs/domains; '
              'run python -m omni_prod.domain_registry --write')
        return 1
    print(f'::notice title=domain registry::{len(json.loads(text)["domains"])} domains, in step with docs/domains')
    return 0


if __name__ == '__main__':
    sys.exit(main())
