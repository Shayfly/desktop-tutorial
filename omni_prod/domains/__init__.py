"""The 30 domain files as something the engine reads, not only a document (warehouse 127, acceptance 1).

docs/domains/<slug>.md is written by hand against docs/domains/README.md's template. `check()` reads every file and
says, per domain and per field, what is missing: a heading of the template, the mandatory facts with their question,
the declared defaults, the failure modes, the professional language, the legal section, and 5 to 8 references each
with a URL and the date it was checked. A domain that does not pass fails loudly, naming the domain and the field --
never a silent default (CLAUDE.md §3).

This module reads; it decides nothing about a build. Which domain a build gets, and what the builder does with it,
are acceptance 2 and later, and are not built here.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / 'docs' / 'domains'

# the template's headings, in the template's order (README.md: "Do not rename, reorder or drop one")
HEADINGS = ['1. Objects', '2. Rules', '3. Mandatory facts', '4. Declared defaults', '5. Failure modes',
            '6. Professional language', '7. Legal', '8. Site vs app', '9. References', '10. Skeletons',
            '11. Not verified']
MIN_REFERENCES, MAX_REFERENCES = 5, 8
_URL = re.compile(r'https?://[^\s)\]|,]+')
_DATE = re.compile(r'\b20\d\d-\d\d-\d\d\b')
_NOTHING = re.compile(r'nothing for this domain', re.I)
# the rejected list is introduced by its own label line, not by the word appearing in a sentence about it
_REJECTED = re.compile(r'^\**\s*(loaded and not used|rejected|not used)\b', re.I)


@dataclass
class Domain:
    slug: str
    name: str
    sections: dict[str, str]
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems

    def section(self, heading: str) -> str:
        return self.sections.get(heading, '')

    def references(self) -> tuple[list[str], list[str]]:
        """(verified, rejected): section 9 lists the references it uses and then, under "Loaded and not used", the
        sites that were fetched and rejected (README rule 2). Both carry a URL and a checked date, so the rejected
        ones are counted separately -- counting them as references would let a domain pass on dead sites."""
        verified, rejected, in_rejected = [], [], False
        for line in self.section('9. References').splitlines():
            if _REJECTED.search(line):
                in_rejected = True
            url = _URL.search(line)
            if url and _DATE.search(line) and not line.lstrip().startswith('>'):
                (rejected if in_rejected else verified).append(url.group(0))
        return verified, rejected


def _split(text: str) -> tuple[str, dict[str, str]]:
    name, sections, current = '', {}, None
    for line in text.splitlines():
        if line.startswith('# ') and not name:
            name = line[2:].strip()
        elif line.startswith('## '):
            current = line[3:].strip()
            sections[current] = ''
        elif current is not None:
            sections[current] += line + '\n'
    return name, sections


def read(path: Path) -> Domain:
    name, sections = _split(path.read_text(encoding='utf-8'))
    d = Domain(slug=path.stem, name=name, sections=sections)
    if not d.name:
        d.problems.append('no domain name (the "# " line)')
    present = [h for h in sections if h in HEADINGS]
    for heading in HEADINGS:
        if heading not in sections:
            d.problems.append(f'missing heading "{heading}"')
    if present != [h for h in HEADINGS if h in sections]:
        d.problems.append('the headings are not in the template\'s order')
    # a section may say "Nothing for this domain" with a reason, but it may never be empty
    for heading in HEADINGS:
        body = d.section(heading).strip()
        if heading in sections and not body:
            d.problems.append(f'"{heading}" is empty')
    # the sections a product cannot be built without: these may never be waived
    for heading in ('3. Mandatory facts', '5. Failure modes', '6. Professional language', '7. Legal'):
        body = d.section(heading)
        if body.strip() and _NOTHING.search(body):
            d.problems.append(f'"{heading}" says "Nothing for this domain"; this section is never empty')
    facts = d.section('3. Mandatory facts')
    if facts.strip() and '?' not in facts:
        d.problems.append('"3. Mandatory facts" has no question to ask the customer (rule: one plain question each)')
    refs, rejected = d.references()
    if not MIN_REFERENCES <= len(refs) <= MAX_REFERENCES:
        d.problems.append(f'{len(refs)} verified references, not {MIN_REFERENCES}-{MAX_REFERENCES} '
                          f'(each needs a URL and the date it was checked)')
    if len(set(refs)) != len(refs):
        d.problems.append('the same reference is listed twice')
    both = set(refs) & set(rejected)
    if both:
        d.problems.append(f'listed as used and as rejected: {", ".join(sorted(both))}')
    return d


def all_domains(docs: Path | None = None) -> list[Domain]:
    folder = docs or DOCS
    return [read(p) for p in sorted(folder.glob('*.md')) if p.stem != 'README']


def check(docs: Path | None = None) -> list[str]:
    """Every problem, each naming its domain and its field. An empty list means every domain passes."""
    out = []
    for d in all_domains(docs):
        out += [f'{d.slug}: {p}' for p in d.problems]
    return out
