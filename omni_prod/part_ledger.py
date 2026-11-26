"""Every build carries a per-part provenance ledger (a vision slice, not a warehouse item; the owner, 2026-11-22
16:00: "start developing ... toward the vision").

NORTH_STAR principle 1: every requirement has a source -- approval, a default or an inference -- marked and bound to the
build, and nothing the customer did not say is attributed to them. The ledger says, for each part of a build, where it
came from: the facts, the copy, the page, the code, the design, the images and the platform's own records.

`ledger(repository)` is pure and deterministic: no I/O, no model, no clock. It reads only the repository dict
({path: text}; an image is the repository_assets envelope) and returns schema '148ai.parts/1':
  parts       facts, copy, page, code, design, images, platform_records; each {'source', 'items'}, and every item has an
              `origin` from the closed set ORIGINS (an unknown value raises ValueError)
  files       every claimed file, once: {'path', 'part'}
  unresolved  every file nobody claims, every generated image with no verified manifest artifact, every verified
              artifact with no file, every image whose bytes are not what the brief or the manifest bound: {'path',
              'reason'}. Any entry makes complete=false. Nothing defaults silently.

Where each origin is read from:
  * the approved brief: rights/rights-manifest.json `original_prompt` (rights_ip.RightsEngine.repository_files) -- the
    same approved prompt the worker builds and judges from;
  * the customer's own words: the request (the text before the brief block) and the brief's 'Customer facts' line --
    the verbatim part of site_content.facts.customer_text. customer_text also carries the 'Audience:', 'Main action:',
    'Screens:' and 'Initial content:' lines; those are intake's summaries of the customer's answers (an option label
    such as "Customers / the public" is not the customer's sentence), so a value found ONLY there, or anywhere else
    in the approved brief, is customer_approved, never customer_words. customer_words is therefore always a subset of
    customer_text, and of the truth gate's rule;
  * facts: content/facts.json `spans` (site_content/render.facts_json), each value credited by the rule above;
  * the route: .omni/project.json `site_route`. 'section_library/1': the page is platform_rendered, content/site.json
    (the model's copy) ai_written, the fixed files (app.py, tests/test_site.py, .omni/project.json, README.md,
    content/facts.json) platform_fixed. No site_route: the legacy route, where the page and the code are ai_written.
    Any other site_route value raises;
  * design: the brief's Design line (discovery.requirements_text). "requested colour description" is customer_words
    when every word of the description is in the customer's own words, else customer_approved; "choose a palette"
    is ai_chosen; "the customer stated no colour" is platform_default (vertical_palettes.design_colours). The values
    are the page's CSS colour custom properties;
  * images: assets/148ai-logo.<ext> is customer_upload when its bytes' sha256 is the brief's 'Uploaded logo
    attachment ... sha256='; assets/148ai-upload-N.<ext> is customer_upload bound to the brief's uploaded-image line N
    (byte for byte, or a web rendition: since the image weight change of 2026-11-26 every carried photo is one --
    WebP or JPEG, web_rendition.OUTPUT_MIMES);
    assets/148ai-image-N.<ext> is ai_generated, linked to the N-th VERIFIED media.image.generate artifact of the asset
    manifest in generated_images.collect order (byte for byte, or a web rendition of the artifact -- every one, since
    2026-11-26).

`customer_view(ledger)` is what the customer may read (decision #29, VISION_LAW rule 7): every key
customer_views.is_internal_key matches is dropped, and so are the provider and routing keys it does not match
(provider, selected_provider, model, capability_key, requirement_id, artifact_key, prompt). It raises if one remains.
`owner_view(repository)` is the ledger plus each generated image's provider, pricing version, estimated / maximum /
actual cost and cost truth from the asset manifest. The text parts carry cost null: build spend is not split per part.

    python -m omni_prod.part_ledger <version.zip> [--owner]

reads an exported version (repository_assets.zip_bytes: images as real files; their sha256 is taken from the bytes)
and prints the customer view, or with --owner the owner view. Read-only. Exit 0 when complete, 1 when not.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import PurePosixPath

SCHEMA = '148ai.parts/1'
PARTS_PATH = '.148ai/parts.json'
ORIGINS = frozenset({'customer_words', 'customer_approved', 'customer_upload', 'ai_written', 'ai_generated',
                     'platform_rendered', 'platform_fixed', 'platform_default', 'ai_chosen', 'platform_record'})
PARTS = ('facts', 'copy', 'page', 'code', 'design', 'images', 'platform_records')

# The content-document route's files (site_content/render.py PAGE, SITE_JSON, FACTS_JSON, PLATFORM_FILES; a test asserts
# they are equal -- render computes its version from library files at import, and this module does no I/O).
SITE_ROUTE = 'section_library/1'
PROJECT_JSON = '.omni/project.json'
PAGE = 'public/index.html'
SITE_JSON = 'content/site.json'
FACTS_JSON = 'content/facts.json'
PLATFORM_FILES = ('app.py', 'tests/test_site.py', '.omni/project.json', 'README.md', FACTS_JSON)

# The platform's records (rights_ip.RightsEngine.repository_files, media_pipeline.CreativeDirector.repository_files).
RIGHTS_MANIFEST = 'rights/rights-manifest.json'
ASSET_MANIFEST = 'assets/148ai-asset-manifest.json'
ASSET_MANIFEST_ALIAS = 'assets/omni-asset-manifest.json'
RECORD_FILES = (RIGHTS_MANIFEST, 'rights/README.md', 'rights/jurisdictions.json', ASSET_MANIFEST, ASSET_MANIFEST_ALIAS,
                'assets/README.md', 'docs/CREATIVE_RIGHTS.md')
# Written by branding.BrandingEngine.decorate_repository AFTER the ledger (the ledger is one of them): never claimed,
# never unresolved, so the ledger of a decorated repository equals the ledger written into it.
SIGNING_FILES = ('.148ai/brand-manifest.json', '.148ai/provenance.json', PARTS_PATH, 'public/148ai-badge.svg')

BRIEF_MARKER = '--- Approved project brief'
VERBATIM_LINE = 'Customer facts'          # of site_content.facts.CUSTOMER_LINES: the one line that quotes the customer
IMAGE_CAPABILITY = 'media.image.generate'  # generated_images.IMAGE_CAPABILITY
TEXT_COST_BASIS = 'not attributed per part (build-level spend only)'
UPLOAD_COST_BASIS = "the customer's own file: no generation spend"
CUSTOMER_HIDDEN = frozenset({'provider', 'selected_provider', 'model', 'capability_key', 'requirement_id',
                             'artifact_key', 'prompt'})
COST_TRUTHS = ('ACTUAL', 'ESTIMATE_ONLY')

_PAGE_SUFFIXES = ('.html', '.htm', '.css')
_IMAGE_PATH = re.compile(r'assets/148ai-(logo|upload|image)(?:-(\d{1,3}))?\.(webp|jpg|jpeg|png)')
_COLOUR_PROP = re.compile(r'(--[A-Za-z0-9_-]+)\s*:\s*(#[0-9a-fA-F]{3,8}\b|(?:rgba?|hsla?)\([^)]{1,80}\))')
_DESIGN_LINE = re.compile(r'(?m)^Design: (.+)$')
_DESCRIPTION = re.compile(r'''requested colour description (?:'([^'\n]*)'|"([^"\n]*)")''')
_PRIMARY = re.compile(r'primary colour (#[0-9a-fA-F]{3,6})\b')
_WORD = re.compile(r'[^\W\d_]{2,}')


class LedgerError(ValueError):
    """The ledger cannot be built from this repository (an unknown route value, a non-dict). Raised, never guessed."""


def check_origin(origin: str) -> str:
    """The origin itself, when it is one of ORIGINS; anything else raises ValueError."""
    if origin not in ORIGINS:
        raise ValueError(f'unknown origin {origin!r}; the closed set is {sorted(ORIGINS)}')
    return origin


def _norm(text: str) -> str:
    from .fact_canon import decode_entities
    return ' '.join(decode_entities(text or '').split())


# ---- the brief ------------------------------------------------------------------------------------------------------
class _Brief:
    """The approved prompt and the texts the credit rule reads."""

    def __init__(self, prompt: str):
        from .site_content.facts import customer_text, request_text
        self.prompt = prompt
        self.sha256 = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
        head, sep, block = prompt.partition(BRIEF_MARKER)
        self.block = block if sep else ''
        self.request = _norm(request_text(prompt))
        self.facts_line = _norm('\n'.join(ln for ln in self.block.splitlines() if ln.strip().startswith(VERBATIM_LINE)))
        self.whole = _norm(prompt)
        self.customer_text = _norm(customer_text(prompt))     # the truth gate's rule: customer_words is a subset of it

    def credit(self, value: str) -> tuple[str, str] | None:
        """(origin, basis) of one value: customer_words when it is in the customer's own words, customer_approved when
        it is only in the approved brief; None when the brief does not hold it at all."""
        v = _norm(value)
        if not v:
            return None
        if v in self.request:
            return 'customer_words', 'request'
        if v in self.facts_line:
            return 'customer_words', 'customer_facts_line'
        if v in self.whole:
            return 'customer_approved', 'approved_brief'
        return None

    def said(self, text: str) -> bool:
        """Every word of `text` is in the customer's own words (a Hebrew word may carry a one-letter prefix there:
        'לבן' is in 'ולבן')."""
        own = (self.request + '\n' + self.facts_line).lower()
        words = _WORD.findall(_norm(text).lower())
        return bool(words) and all(w in own for w in words)


# ---- the ledger -----------------------------------------------------------------------------------------------------
class _Ledger:
    def __init__(self, repository: dict):
        if not isinstance(repository, dict):
            raise LedgerError(f'a repository is a dict of path -> text, not {type(repository).__name__}')
        self.repo = repository
        self.parts = {p: {'source': '', 'items': []} for p in PARTS}
        self.claims: dict[str, str] = {}
        self.unresolved: list[dict] = []
        self.image_rows: dict[str, tuple[dict, int]] = {}     # generated image path -> (manifest row, images of its row)
        self.result: dict = {}

    def item(self, part: str, origin: str, **fields) -> None:
        if part not in self.parts:
            raise ValueError(f'unknown part {part!r}')
        entry = {'origin': check_origin(origin), **fields}
        path = fields.get('path')
        if path is not None:
            if path in self.claims:
                self.unresolve(path, f'claimed by both {self.claims[path]} and {part}')
                return
            self.claims[path] = part
        self.parts[part]['items'].append(entry)

    def unresolve(self, path: str, reason: str) -> None:
        self.unresolved.append({'path': path, 'reason': reason})

    def text(self, path: str) -> str | None:
        value = self.repo.get(path)
        return value if isinstance(value, str) else None

    def json_file(self, path: str):
        """The parsed file, or None (absent, or unresolved with the reason when it is not JSON)."""
        text = self.text(path)
        if text is None:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            self.unresolve(path, f'not valid JSON ({exc.msg})')
            return None


def _brief(L: _Ledger) -> _Brief | None:
    manifest = L.json_file(RIGHTS_MANIFEST)
    if manifest is None:
        if RIGHTS_MANIFEST not in L.repo:
            L.unresolve(RIGHTS_MANIFEST, 'missing: there is no approved brief to read origins from')
        return None
    prompt = manifest.get('original_prompt') if isinstance(manifest, dict) else None
    if not isinstance(prompt, str) or not prompt.strip():
        L.unresolve(RIGHTS_MANIFEST, 'carries no original_prompt: there is no approved brief to read origins from')
        return None
    return _Brief(prompt)


def _route(L: _Ledger) -> str:
    """'section_library/1' or 'legacy'. A site_route of any other value raises: an unknown value is never a default."""
    data = L.json_file(PROJECT_JSON)
    if not isinstance(data, dict) or 'site_route' not in data:
        return 'legacy'
    if data['site_route'] != SITE_ROUTE:
        raise LedgerError(f"unknown site_route {data['site_route']!r} in {PROJECT_JSON} (known: {SITE_ROUTE!r})")
    return SITE_ROUTE


# ---- images ---------------------------------------------------------------------------------------------------------
def _manifest_artifacts(L: _Ledger) -> list[dict] | None:
    """The asset manifest's VERIFIED media.image.generate artifacts in generated_images.collect order; None when there
    is no readable manifest."""
    manifest = L.json_file(ASSET_MANIFEST)
    alias = L.text(ASSET_MANIFEST_ALIAS)
    if alias is not None and ASSET_MANIFEST in L.repo and alias != L.text(ASSET_MANIFEST):
        L.unresolve(ASSET_MANIFEST_ALIAS, f'differs from {ASSET_MANIFEST}; they are written as one manifest')
    if not isinstance(manifest, dict):
        return None
    found = []
    for row in manifest.get('materialized') or ():
        if not isinstance(row, dict) or row.get('capability_key') != IMAGE_CAPABILITY or row.get('status') != 'VERIFIED':
            continue
        verification = row.get('verification') or {}
        arts = [a for a in (verification.get('artifacts') or ()) if isinstance(a, dict)]
        mine = []
        for position, art in enumerate(arts):
            key = art.get('artifact_key') or (row.get('artifact_key') if position == 0 else None)
            if key and art.get('verified', True):
                mine.append({'key': key, 'sha256': art.get('sha256'), 'size_bytes': art.get('size_bytes')})
        if not arts and row.get('artifact_key'):
            mine.append({'key': row['artifact_key'], 'sha256': row.get('sha256') or verification.get('sha256'),
                         'size_bytes': row.get('size_bytes') or verification.get('size_bytes')})
        for art in mine:
            found.append({**art, 'row': row, 'of': len(mine)})
    return found


def _bytes_state(file_sha: str, mime: str, bound_sha: str) -> str | None:
    """'identical', 'web_rendition' (a file of a type the converter makes, web_rendition.OUTPUT_MIMES: since the image
    weight change of 2026-11-26 EVERY photo and generated image the platform carries is a conversion -- no image is
    carried byte for byte, whatever its size), or None (the file is not what was bound)."""
    from .web_rendition import OUTPUT_MIMES
    if file_sha == bound_sha:
        return 'identical'
    if mime in OUTPUT_MIMES:
        return 'web_rendition'
    return None


def _images(L: _Ledger, brief: _Brief | None) -> None:
    from .repository_assets import EXT_MIME, AssetCarryError, decode, is_envelope
    from .uploaded_assets import _BINDING, _IMAGE_BINDING
    L.parts['images']['source'] = ('assets/148ai-*: the logo and photos bound by the approved brief, generated images '
                                   'linked to the asset manifest')
    files, carried = {}, {}
    for path in sorted(L.repo):
        m = _IMAGE_PATH.fullmatch(path)
        if not m:
            if path.startswith('assets/') and is_envelope(L.repo[path]):
                L.unresolve(path, 'an image file of no kind the platform carries')
            continue
        kind, index = m.group(1), m.group(2)
        if (kind == 'logo') != (index is None):
            L.unresolve(path, 'an image file of no kind the platform carries')
            continue
        try:
            data = decode(path, L.repo[path])
        except AssetCarryError as exc:
            L.unresolve(path, f'not a verified image file: {exc}')
            continue
        n = int(index) if index else None
        if (kind, n) in carried:
            L.unresolve(path, f'a second file for the same image (the first is {carried[(kind, n)]})')
            continue
        carried[(kind, n)] = path
        mime = EXT_MIME[PurePosixPath(path).suffix.lower()]
        files[path] = (kind, n, hashlib.sha256(data).hexdigest(), mime, len(data))

    block = brief.block if brief else ''
    logo = _BINDING.search(block)
    uploads = {int(x[1]): x for x in _IMAGE_BINDING.finditer(block)}
    generated = {}
    for path, (kind, n, sha, mime, size) in files.items():
        if kind == 'logo':
            if logo is None:
                L.unresolve(path, 'a logo file, and the approved brief binds no uploaded logo')
            elif sha != logo[2]:
                L.unresolve(path, "the logo file's sha256 is not the one the approved brief bound")
            else:
                L.item('images', 'customer_upload', path=path, sha256=sha, bound_to='uploaded_logo', bytes='identical')
        elif kind == 'upload':
            line = uploads.get(n)
            state = _bytes_state(sha, mime, line[3]) if line else None
            if line is None:
                L.unresolve(path, f'an uploaded photo file, and the approved brief has no uploaded-image line {n}')
            elif state is None:
                L.unresolve(path, f'the file is not the photo of uploaded-image line {n} (sha256 differs and it is not '
                                  'a web rendition)')
            else:
                L.item('images', 'customer_upload', path=path, index=n, sha256=sha, bound_to=f'uploaded_image_{n}',
                       place=line[5], original_sha256=line[3], bytes=state)
        else:
            generated[n] = (path, sha, mime, size)
    if logo is not None and not any(k == 'logo' for k, *_ in files.values()):
        L.unresolve('assets/148ai-logo.*', 'the approved brief binds an uploaded logo and the repository has no logo file')
    for n in sorted(uploads):
        if not any(k == 'upload' and i == n for k, i, *_ in files.values()):
            L.unresolve(f'assets/148ai-upload-{n}.*', f'the approved brief places uploaded image {n} and the repository '
                                                      'has no file for it')

    artifacts = _manifest_artifacts(L)
    if artifacts is None:
        for n, (path, *_rest) in sorted(generated.items()):
            L.unresolve(path, 'a generated image, and there is no readable asset manifest to attest it')
        artifacts, generated = [], {}
    for n in range(1, max([len(artifacts), *generated], default=0) + 1):
        art = artifacts[n - 1] if n <= len(artifacts) else None
        if n not in generated:
            if art is not None:
                L.unresolve(f'assets/148ai-image-{n}.*', f'verified generated image {n} of the asset manifest has no '
                                                         'file in the repository')
            continue
        path, sha, mime, size = generated[n]
        if art is None:
            L.unresolve(path, 'a generated image with no verified artifact in the asset manifest')
            continue
        if not art.get('sha256'):
            L.unresolve(path, 'its verified artifact records no sha256, so the file cannot be attested')
            continue
        state = _bytes_state(sha, mime, art['sha256'])
        if state is None:
            L.unresolve(path, 'the file is not its verified artifact (sha256 differs and it is not a web rendition)')
            continue
        row = art['row']
        L.item('images', 'ai_generated', path=path, index=n, sha256=sha, artifact_sha256=art['sha256'], bytes=state,
               requirement_id=str(row.get('requirement_id')), capability_key=IMAGE_CAPABILITY, artifact_key=art['key'])
        L.image_rows[path] = (row, art['of'])


# ---- the route's files ----------------------------------------------------------------------------------------------
def _records(L: _Ledger) -> None:
    L.parts['platform_records']['source'] = 'the rights and creative records the platform writes into every build'
    L.parts['platform_records']['written_at_signing'] = list(SIGNING_FILES)
    for path in RECORD_FILES:
        if path in L.repo and path not in L.claims:
            L.item('platform_records', 'platform_record', path=path)


def _facts(L: _Ledger, brief: _Brief | None) -> None:
    L.parts['facts']['source'] = FACTS_JSON
    data = L.json_file(FACTS_JSON)
    if data is None:
        return                                   # a missing facts.json is said by _section_files
    spans = data.get('spans') if isinstance(data, dict) else None
    if not isinstance(spans, list) or not all(isinstance(s, str) for s in spans):
        L.unresolve(FACTS_JSON, "carries no 'spans' list of texts")
        return
    for value in dict.fromkeys(spans):
        credit = brief.credit(value) if brief else None
        if credit is None:
            L.unresolve(FACTS_JSON, f'the page shows the fact {value!r}, which is not in the approved brief' if brief
                        else f'the page shows the fact {value!r}, and there is no approved brief to credit it against')
            continue
        origin, basis = credit
        L.item('facts', origin, value=value, basis=basis)


def _section_files(L: _Ledger) -> list[str]:
    L.parts['page']['source'] = 'the section library renders the page from the content document'
    L.parts['copy']['source'] = "the model's copy, in the content document"
    L.parts['code']['source'] = 'the fixed files of the section_library/1 route'
    for path, part, origin in ((PAGE, 'page', 'platform_rendered'), (SITE_JSON, 'copy', 'ai_written'),
                               *((p, 'code', 'platform_fixed') for p in PLATFORM_FILES)):
        if path in L.repo:
            L.item(part, origin, path=path)
        else:
            L.unresolve(path, 'the section_library/1 route writes this file and it is missing')
    return [PAGE]


def _legacy_files(L: _Ledger) -> list[str]:
    """Page and code are the model's: every file no other part claimed, the page by its suffix."""
    L.parts['facts']['source'] = 'legacy route: the facts are inside the AI-written page and are not itemised'
    L.parts['code']['source'] = 'legacy route: the code is written by the model'
    from .repository_assets import is_envelope
    judged = {u['path'] for u in L.unresolved}
    pages, code = [], []
    for path in sorted(L.repo):
        if path in L.claims or path in SIGNING_FILES or path in judged or not isinstance(L.repo[path], str):
            continue                             # claimed, written at signing, or already said (an image judged)
        if is_envelope(L.repo[path]):
            continue                             # an image file is never code: _leftovers says it
        (pages if path.lower().endswith(_PAGE_SUFFIXES) else code).append(path)
    for path in code:
        L.item('code', 'ai_written', path=path)
    if pages:
        L.parts['page']['source'] = 'legacy route: the page is written by the model'
        for path in pages:
            L.item('page', 'ai_written', path=path)
        holders = pages
    else:
        holders = [p for p in code if re.search(r'<html\b|<!doctype html', L.repo[p], re.I)]
        L.parts['page']['source'] = 'legacy route: the page is written by the model inside its code'
        if holders:
            L.item('page', 'ai_written', inside=holders)
    L.parts['copy']['source'] = 'legacy route: the copy is written by the model inside the page'
    if holders:
        L.item('copy', 'ai_written', inside=holders)
    return holders


def _design(L: _Ledger, brief: _Brief | None, page_files: list[str]) -> None:
    L.parts['design']['source'] = "the approved brief's Design line; values from the page's CSS colour properties"
    if brief is None:
        return                                   # the missing brief is already unresolved
    m = _DESIGN_LINE.search(brief.block)
    if not m:
        L.unresolve(RIGHTS_MANIFEST, 'the approved brief has no Design line: the design has no known origin')
        return
    line = m.group(1)
    described = _DESCRIPTION.search(line)
    if described:
        said = described.group(1) if described.group(1) is not None else described.group(2)
        origin = 'customer_words' if brief.said(said) else 'customer_approved'
        fields = {'basis': 'requested colour description', 'customer_said': said}
    elif 'choose a palette' in line:
        origin, fields = 'ai_chosen', {'basis': 'choose a palette'}
    elif 'the customer stated no colour' in line:
        origin, fields = 'platform_default', {'basis': 'the customer stated no colour'}
    else:
        L.unresolve(RIGHTS_MANIFEST, 'the Design line names no colour source the ledger knows')
        return
    values, seen, source = [], set(), []
    for path in sorted(page_files):
        text = L.text(path) or ''
        for prop, value in _COLOUR_PROP.findall(text):
            if prop not in seen:
                seen.add(prop)
                values.append({'property': prop, 'value': value.lower()})
                if path not in source:
                    source.append(path)
    primary = _PRIMARY.search(line)
    if primary:
        fields.update(brief_primary=primary.group(1).lower(),
                      brief_primary_on_page=any(v['value'] == primary.group(1).lower() for v in values))
    L.item('design', origin, values=values, values_from=source, **fields)


def _leftovers(L: _Ledger) -> None:
    judged = {u['path'] for u in L.unresolved}
    for path in sorted(L.repo):
        if path in L.claims or path in SIGNING_FILES or path in judged:
            continue
        L.unresolve(path, 'no producer the ledger knows writes this file' if isinstance(L.repo[path], str)
                    else 'not a text entry: a repository holds text (an image is an envelope under assets/)')


def _build(repository: dict) -> _Ledger:
    L = _Ledger(repository)
    route = _route(L)
    brief = _brief(L)
    _images(L, brief)
    _records(L)
    if route == SITE_ROUTE:
        _facts(L, brief)
        page_files = _section_files(L)
    else:
        page_files = _legacy_files(L)
    _design(L, brief, page_files)
    _leftovers(L)
    for part in L.parts.values():
        part['items'].sort(key=lambda i: (i.get('path') or '', json.dumps(i, sort_keys=True, ensure_ascii=False)))
    L.parts['facts']['items'].sort(key=lambda i: i['value'])
    unresolved = sorted(L.unresolved, key=lambda u: (u['path'], u['reason']))
    L.result = {
        'schema': SCHEMA, 'route': route, 'brief_sha256': brief.sha256 if brief else None,
        'complete': not unresolved, 'parts': L.parts,
        'files': [{'path': p, 'part': L.claims[p]} for p in sorted(L.claims)],
        'unresolved': unresolved,
    }
    return L


def ledger(repository: dict) -> dict:
    """The provenance ledger of one repository (schema '148ai.parts/1'). Pure: reads only `repository`."""
    return _build(repository).result


# ---- views ----------------------------------------------------------------------------------------------------------
def _hidden(key) -> bool:
    from .customer_views import is_internal_key
    return is_internal_key(key) or str(key) in CUSTOMER_HIDDEN


def _strip(value):
    if isinstance(value, dict):
        return {k: _strip(v) for k, v in value.items() if not _hidden(k)}
    if isinstance(value, list):
        return [_strip(v) for v in value]
    return value


def _remaining(value, at='') -> list[str]:
    if isinstance(value, dict):
        return [f'{at}/{k}' for k in value if _hidden(k)] + [x for k, v in value.items() for x in _remaining(v, f'{at}/{k}')]
    if isinstance(value, list):
        return [x for i, v in enumerate(value) for x in _remaining(v, f'{at}[{i}]')]
    return []


def customer_view(led: dict) -> dict:
    """The ledger as the customer may read it: no internal economics, no provider or routing keys. Raises ValueError
    when one remains (decision #29, VISION_LAW rule 7)."""
    view = _strip(copy.deepcopy(led))
    left = _remaining(view)
    if left:
        raise ValueError(f'internal keys remain in the customer view: {left[:10]}')
    return view


def owner_view(repository: dict) -> dict:
    """The ledger plus, for each generated image, what the asset manifest records of its spend. The text parts carry
    cost null: build-level spend is not split per part, and no split is invented."""
    L = _build(repository)
    out = copy.deepcopy(L.result)
    out['view'] = 'owner'
    for name in PARTS:
        if name != 'images':
            out['parts'][name].update(cost=None, cost_basis=TEXT_COST_BASIS)
    for entry in out['parts']['images']['items']:
        if entry['origin'] != 'ai_generated':
            entry.update(cost=None, cost_basis=UPLOAD_COST_BASIS)
            continue
        row, shared = L.image_rows[entry['path']]
        truth = row.get('cost_truth')
        if truth not in COST_TRUTHS:
            raise ValueError(f"asset manifest row {row.get('requirement_id')!r}: unknown cost_truth {truth!r}")
        entry.update(provider=row.get('provider') or row.get('selected_provider'),
                     pricing_version=row.get('pricing_version'), estimated_cost_usd=row.get('estimated_cost_usd'),
                     maximum_cost_usd=row.get('maximum_cost_usd'), actual_cost_usd=row.get('actual_cost_usd'),
                     cost_truth=truth, cost_scope=f'the whole requirement ({shared} image(s))')
    return out


def item_count(view: dict) -> int:
    return sum(len(p.get('items') or ()) for p in (view.get('parts') or {}).values())


# ---- an exported version --------------------------------------------------------------------------------------------
def read_zip(data: bytes) -> dict[str, str]:
    """An export zip back as a repository: text as text, an image under assets/ as its envelope (its sha256 computed
    from the file's bytes, its type checked against its extension -- repository_assets.envelope raises otherwise)."""
    from .repository_assets import ASSET_DIR, EXT_MIME, envelope
    repo = {}
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            if info.filename in repo:
                raise ValueError(f'{info.filename}: the zip holds this path twice')
            raw = zf.read(info)
            p = PurePosixPath(info.filename)
            if p.parts[:1] == (ASSET_DIR,) and p.suffix.lower() in EXT_MIME:
                repo[info.filename] = envelope(raw, EXT_MIME[p.suffix.lower()])
            else:
                repo[info.filename] = raw.decode('utf-8')
    return repo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='python -m omni_prod.part_ledger',
                                     description='The provenance ledger of an exported 148AI version (read-only).')
    parser.add_argument('zip', help='the version zip (repository_assets.zip_bytes)')
    parser.add_argument('--owner', action='store_true', help='the owner view: adds each generated image\'s spend')
    args = parser.parse_args(argv)
    with open(args.zip, 'rb') as fh:
        repo = read_zip(fh.read())
    view = owner_view(repo) if args.owner else customer_view(ledger(repo))
    sys.stdout.write(json.dumps(view, ensure_ascii=False, indent=2, sort_keys=True) + '\n')
    return 0 if view['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
