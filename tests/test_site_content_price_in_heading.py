"""A heading that carries a price reference is measured as the page shows it (the release review of 2026-11-25).

The fault, reproduced by two reviewers: the validator counted a field's length on the model's text, where "@price:1" is
8 characters (validate._shape, TOO_LONG); the renderer writes the customer's own span in its place (render._sub:
"1,250 שקלים" is 11), and the section library's heading check (typography.check_headings, Hebrew h3/h4: 40) counts
the shown text. A services item title of 38-39 characters passed validation, failed the render with HeadingTooLong,
and the build ended as site_render_defect after the content call was spent, with no correction. Now the validator
counts every field the renderer substitutes on its shown text (validate.too_long: render.shown, typography.visible),
so the same title is a TOO_LONG problem whose 'why' gives the shown length, and the one correction round fixes it.

The brief is the owner's production row (tests/fixtures/site_content_bld_b0eb47a5.json, read-only; its fingerprint is
asserted in test_site_content_render.py) with the price written "1,250 שקלים". The generate path is the route's own
(site_content.install with OMNI_SITE_LIBRARY=on: the real validator, renderer, section library and pre-pass gates);
only the model is scripted (AGENTS.md rule 2). No browser.

  the reproduction          the 39-character title is corrected before the render, the model told the shown length
  no correction             the same title returned again is site_content_invalid, never site_render_defect
  it fits                   a substituted heading of exactly 40 shown characters renders with one content call
  shorter as shown          a title longer as written than as shown (the 5-character "250 ₪") is not refused
  the boundary              validation and the render refuse the same heading, at the same length
  one notion of the limit   every field the library renders as h1-h4 is bound by that heading's script limit
"""
import copy
import json
import re
import unittest
from html import unescape

from tests.test_site_content_agents import routed
from tests.test_site_content_engine import CONTENT, PROMPT, ScriptedGateway

from omni_prod import typography as T
from omni_prod.site_content import agents as A
from omni_prod.site_content import facts as Fx
from omni_prod.site_content import render as R
from omni_prod.site_content import schema as K
from omni_prod.site_content import validate as V

PRICED = PROMPT.replace('250 ₪', '1,250 שקלים')       # the customer's price in words: 11 characters, "@price:1" is 8
PATH = 'sections.services.items[0].title'
LONG = 'פגישת ייעוץ ראשון בדיני עבודה: @price:1'           # 39 as written, 42 as the page shows it
LONG_38 = 'פגישת ייעוץ ראשון בדיני עבודה @price:1'           # 38 as written, 41 as shown
SHORT = 'ייעוץ ראשון בדיני עבודה: @price:1'                # the correction: 36 as shown
FITS = 'ייעוץ ראשון בתיק דיני עבודה: @price:1'             # 37 as written, exactly 40 as shown
LONGER_WRITTEN = 'פגישת ייעוץ ראשון בתיק דיני עבודה: @price:1'     # 43 as written, 40 as shown with "250 ₪"
H3 = T.script('hebrew')['heading_max_chars']['h3']


def doc(title: str) -> dict:
    out = copy.deepcopy(CONTENT)
    out['sections']['services']['items'][0]['title'] = title
    return out


class Answers(ScriptedGateway):
    """The model's first document, then its corrected one: one answer per content call, in order."""

    def __init__(self, *documents):
        super().__init__(content=documents[0])
        self.documents = list(documents)

    def complete_json(self, **kw):
        out = super().complete_json(**kw)
        if self.calls[-1][0] == 'content':
            return copy.deepcopy(self.documents[self.roles().count('content') - 1])
        return out


def generate(gw, prompt=PRICED):
    engine = routed(gw, prompt=prompt)
    files = engine.generator.generate(engine.architect.create_spec(prompt))
    return engine, {f.path: f.content for f in files}


def headings(html: str) -> list[tuple[str, str]]:
    return [(tag.lower(), T.visible(unescape(re.sub(r'<[^>]+>', '', inner))))
            for tag, inner in re.findall(r'<(h[1-6])\b[^>]*>(.*?)</\1\s*>', html, re.S | re.I)]


class APriceInAHeading(unittest.TestCase):
    maxDiff = None

    def test_the_title_that_failed_the_build_is_corrected_before_the_render(self):
        sheet = Fx.fact_sheet(PRICED)
        self.assertEqual([(p['id'], p['span']) for p in sheet.prices], [('@price:1', '1,250 שקלים')])
        self.assertEqual((len(LONG), len(R.shown(LONG, sheet))), (39, 42))
        gw = Answers(doc(LONG), doc(SHORT))
        engine, files = generate(gw)
        self.assertEqual(gw.roles().count('content'), 2)                  # the call and its one correction
        corrected = engine.site_report['corrected']
        self.assertEqual([(p['path'], p['code'], p['severity']) for p in corrected], [(PATH, 'TOO_LONG', 'block')])
        self.assertEqual(corrected[0]['why'], '42 characters as the page shows it, where @price:1 is "1,250 שקלים" '
                                              '(11 characters); at most 40: shorten the words around the reference')
        self.assertEqual(json.loads(gw.calls[1][1])['problems'], corrected)  # what the model was told
        self.assertIn(('h3', 'ייעוץ ראשון בדיני עבודה: 1,250 שקלים'), headings(files[R.PAGE]))
        self.assertEqual(json.loads(files[R.SITE_JSON])['document'], doc(SHORT))

    def test_a_title_still_too_long_after_its_correction_is_invalid_content_not_a_render_defect(self):
        from omni_prod.worker_tasks import failure_code
        for title in (LONG, LONG_38):
            with self.subTest(written=len(title)):
                gw = ScriptedGateway(content=doc(title))               # the correction returns the same document
                with self.assertRaises(A.SiteContentInvalid) as caught:
                    generate(gw)
                self.assertEqual(failure_code(caught.exception), 'site_content_invalid')
                self.assertIn((PATH, 'TOO_LONG'), {(p['path'], p['code']) for p in caught.exception.problems})
                self.assertEqual(gw.roles().count('content'), 1 + A.MAX_CORRECTIONS)    # caps-a 1: up to three

    def test_a_substituted_heading_that_fits_is_rendered_with_one_content_call(self):
        self.assertEqual(len(R.shown(FITS, Fx.fact_sheet(PRICED))), H3)
        gw = ScriptedGateway(content=doc(FITS))
        engine, files = generate(gw)
        self.assertEqual(gw.roles().count('content'), 1)
        self.assertNotIn('corrected', engine.site_report)
        self.assertIn(('h3', 'ייעוץ ראשון בתיק דיני עבודה: 1,250 שקלים'), headings(files[R.PAGE]))

    def test_a_title_longer_as_written_than_as_shown_is_not_refused(self):
        sheet = Fx.fact_sheet(PROMPT)                                    # the owner's own price: "250 ₪", 5 characters
        self.assertEqual((len(LONGER_WRITTEN), len(R.shown(LONGER_WRITTEN, sheet))), (43, H3))
        gw = ScriptedGateway(content=doc(LONGER_WRITTEN))
        engine, files = generate(gw, prompt=PROMPT)
        self.assertEqual(gw.roles().count('content'), 1)
        self.assertNotIn('corrected', engine.site_report)
        self.assertIn(('h3', 'פגישת ייעוץ ראשון בתיק דיני עבודה: 250 ₪'), headings(files[R.PAGE]))


class TheBoundary(unittest.TestCase):
    """Validation and the render refuse the same heading at the same length: 40 shown characters pass both, 41 fail
    both -- the validator as TOO_LONG, the render as HeadingTooLong (raised as SiteRenderDefect)."""

    def test_validation_and_the_render_refuse_the_same_heading(self):
        from tests.test_site_content_render import ORDER, TITLES, contract
        from omni_prod.section_library import DIRECTIONS
        c = contract()
        cases = (
            (PRICED, FITS, True),                       # 40 as shown
            (PRICED, LONG_38, False),                   # 38 as written, 41 as shown
            (PROMPT, LONGER_WRITTEN, True),             # 43 as written, 40 as shown
            (PROMPT, 'א' * 20 + '  ' + 'ב' * 19, True),  # 41 as written, 40 as read: white space is one space
            (PROMPT, 'א' * 20 + ' ' + 'ב' * 20, False),  # 41 as read
        )
        for prompt, title, fits in cases:
            with self.subTest(title=title):
                sheet = Fx.fact_sheet(prompt)
                offered, _ = K.offered_sections(sheet, DIRECTIONS['palettes']['counsel'], ORDER, TITLES)
                found = {(p.path, p.code) for p in V.validate(doc(title), sheet, offered, TITLES, claim_mode='warn')}
                self.assertEqual((PATH, 'TOO_LONG') not in found, fits, found)
                render = lambda: R.render(doc(title), sheet, c, expect_fp=c['fingerprint'], direction='formal',  # noqa: E731
                                          year='2026', outline_titles=TITLES, order=ORDER, windows=())
                if fits:
                    render()
                else:
                    with self.assertRaises(R.SiteRenderDefect) as caught:
                        render()
                    self.assertIn('HeadingTooLong: h3 of 41 characters', str(caught.exception))


class OneNotionOfTheLimit(unittest.TestCase):
    """Every field the section library renders inside <h1>..<h4> has a schema bound equal to that heading's limit in
    scripts.json: the schema never lets the model write a heading the render refuses, and never refuses one it
    renders. Derived from a render, not listed: each string of a document built from the schema is a marker, and the
    page says which marker landed in which heading."""

    def test_every_field_rendered_as_a_heading_is_bound_by_that_headings_limit(self):
        from tests.test_site_content_render import contract
        bound: dict[str, tuple[str, int]] = {}

        def fill(spec, path):
            if isinstance(spec, K.Str):
                marker = f'שדה {len(bound) + 1}'
                bound[marker] = (path, spec.max)
                return marker
            if isinstance(spec, K.Num):
                return str(len(bound) + 2)
            if isinstance(spec, K.Ref):
                return f'{spec.prefix}:1'
            if isinstance(spec, K.Lst):
                return [fill(spec.item, f'{path}[{i}]') for i in range(max(spec.min, 1))]
            return {k: fill(v, f'{path}.{k}') for k, v in spec.fields.items()}
        sections = {key: fill(K.Obj(K.spec_for(key, {})), f'sections.{key}') for key in K.SECTIONS}
        document = {'schema': K.SCHEMA, 'name': 'כהן ושות׳', 'tagline': fill(K.TOP['tagline'], 'tagline'),
                    'description': fill(K.TOP['description'], 'description'), 'sections': sections}
        sheet = copy.copy(Fx.fact_sheet(PROMPT))
        sheet.reviews = [{'id': '@review:1', 'text': 'ביקורת', 'author': 'לקוחה'}]
        # visual plan S3: the gallery and the services cards' item references are sections and fields of the schema too
        sheet.gallery_images = [{'src': '148ai-asset://image/9', 'alt': 'עבודה'}]
        sheet.items = [{'id': '@item:1', 'text': 'נושא'}, {'id': '@item:2', 'text': 'עוד נושא'}]
        sheet.item_images = {i['id']: {'src': f'148ai-asset://image/{n}', 'alt': i['text']} for n, i in enumerate(sheet.items, 1)}
        c = contract()
        html, _ = R.render(document, sheet, c, expect_fp=c['fingerprint'], direction='formal', year='2026',
                           outline_titles={}, order=None, windows=())
        limits = T.script('hebrew')['heading_max_chars']
        seen = {}
        for tag, text in headings(html):
            self.assertIn(text, bound, f'a {tag} that is not the model\'s copy: {text!r}')
            seen[bound[text][0]] = (tag, bound[text][1])
        self.assertEqual({tag for tag, _ in seen.values()}, {'h1', 'h2', 'h3', 'h4'})
        wrong = {path: f'bound {limit}, {tag} limit {limits[tag]}' for path, (tag, limit) in seen.items()
                 if limit != limits[tag]}
        self.assertEqual(wrong, {})
        # each section's own title, every item title and the price list's names are among them
        for path in ('sections.hero.title', 'sections.cta.title', 'sections.process.steps[0].title',
                     'sections.pricelist.groups[0].title', 'sections.pricelist.groups[0].items[0].name',
                     *(f'sections.{k}.title' for k in K.NAV_SECTIONS)):
            self.assertIn(path, seen)


if __name__ == '__main__':
    unittest.main()
