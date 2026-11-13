"""The prompt a generated image is made from (#324, Michael 2026-11-13).

The image is made from the brief: the clause of the approved request that describes it (constraints.subject, in the
customer's language -- it is also the image's alt), with the plan's style direction (constraints.style /
constraints.colours). The image model understands English best, so that source is translated ONCE into one English
line, the translation is saved next to the image (`.../capabilities/<requirement>/prompt-en.txt`) and reused on every
retry or recovery -- never translated again. The negative list is fixed text appended here, not left to a model:
no text, no letters, no logos, no watermark, no user-interface elements.

The translation is a model call through the build's own gateway: the build's model budget, the kill switches and the
write-ahead attempt ledger apply to it like any other call. A translation that does not come back as one plain English
line stops the image (fail closed): no paid image request goes out from an untranslated or malformed prompt.
"""
from __future__ import annotations

import re
from dataclasses import replace

from .artifact_keys import build_capability_artifact_key
from .capabilities import CapabilityPlan

IMAGE_CAPABILITY = 'media.image.generate'
NEGATIVE = 'No text, no letters, no logos, no watermark, no user interface elements.'
FILENAME = 'prompt-en.txt'
MAX_CHARS = 400
_NON_LATIN = re.compile(r'[֐-׿؀-ۿ]')

SYSTEM = ('You write prompts for an image generation model. Translate the description below into ONE line of plain '
          'English that describes the image to draw: its subject, then its style and colours. Keep every concrete '
          'detail; add nothing the description does not say. Output only that line: no quotes, no labels, no '
          'explanations.')


class ImagePromptError(RuntimeError):
    """The English prompt could not be made; no image request is sent."""


def source_text(constraints) -> str:
    """What is translated: the brief's own words for the image and the plan's style direction."""
    parts = [str(constraints.get('subject') or '').strip()]
    style = str(constraints.get('style') or '').strip()
    colours = str(constraints.get('colours') or '').strip()
    if style:
        parts.append(f'Style: {style}')
    if colours:
        parts.append(f'Colours: {colours}')
    return '. '.join(p for p in parts if p)


def validate_english(text: str) -> str:
    line = ' '.join((text or '').split()).strip(' "\'')
    if not line:
        raise ImagePromptError('the translation came back empty')
    if _NON_LATIN.search(line):
        raise ImagePromptError('the translation is not English')
    if len(line) > MAX_CHARS:
        raise ImagePromptError(f'the translation is longer than {MAX_CHARS} characters')
    return line


def final_prompt(english: str, purpose: str) -> str:
    """The English description, the page purpose, and the fixed negative list."""
    return f'{english.rstrip(".")}. Original {purpose} for a web page; realistic, high quality. {NEGATIVE}'


def _cached(store, key):
    if store is None:
        return None
    try:
        return bytes(store.get_bytes(key)).decode('utf-8')
    except Exception:   # missing object: not translated yet
        return None


def english_for(constraints, *, translate, store, key) -> str:
    """The saved translation when there is one; otherwise translate once and save it."""
    saved = _cached(store, key)
    if saved is not None:
        return validate_english(saved)
    source = source_text(constraints)
    english = validate_english(source if not _NON_LATIN.search(source) else translate(source))
    if store is not None:
        try:
            store.put_bytes(key, english.encode('utf-8'))
        except KeyError:   # another worker saved it first: use the saved one
            return validate_english(_cached(store, key) or english)
    return english


def prepare_image_prompts(plan: CapabilityPlan, *, translate, store, build_id: str, project_id: str,
                          only=None) -> CapabilityPlan:
    """Every image requirement with a subject from the brief gets its final English prompt (constraints.prompt,
    which the image provider sends as is). The Hebrew subject stays for the alt. Other requirements: unchanged.
    `only`: the requirement ids a provider is assigned to -- nothing is translated for an image that will not be
    generated (a NOT_CONFIGURED one blocks the build without a translation call)."""
    if plan is None:
        return plan
    changed = []
    for req in plan.requirements:
        constraints = dict(req.constraints or {})
        if (req.key != IMAGE_CAPABILITY or not constraints.get('subject') or constraints.get('prompt')
                or (only is not None and req.id not in only)):
            changed.append(req)
            continue
        key = build_capability_artifact_key(project_id=project_id, build_id=build_id, requirement_id=req.id,
                                            filename=FILENAME)
        english = english_for(constraints, translate=translate, store=store, key=key)
        constraints['prompt_en'] = english
        constraints['prompt'] = final_prompt(english, req.purpose)
        changed.append(replace(req, constraints=constraints))
    return replace(plan, requirements=tuple(changed))


def gateway_translator(gateway):
    """One call through the build gateway (budget, kill switches, ledger)."""
    def translate(text: str) -> str:
        try:
            return gateway.complete(system=SYSTEM, user=text, temperature=0.0, max_tokens=200, task='general')
        except Exception as exc:
            raise ImagePromptError(f'the image prompt could not be translated: {type(exc).__name__}') from exc
    return translate
