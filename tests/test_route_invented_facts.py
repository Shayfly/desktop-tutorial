"""Route honesty, cause 3: a build that died on one sentence.

The owner's build bld_3938e570 (the production row, redacted: tests/fixtures/site_content_bld_3938e570.json) failed
"SiteContentInvalid: 1 problem(s) after the one correction: sections.process.lead PRICE_NOT_GIVEN": one sentence with a
price the customer never gave, in an optional field, failed the whole build after two paid calls.

After the one correction, a document whose only blocking problems are invented facts (agents.INVENTED) loses exactly
the sentences that state them (agents.strip_invented), deterministically, recorded in the evidence ('stripped'); an
optional field left with no sentence is removed; a required field that would be left empty, or any other problem,
still fails loudly, as before. Nothing is ever written in place of what is removed.

The real route, validator, section library, gates and generator on the owner's brief (the one-page check bypassed, so
the content route is reached exactly as production reached it); only the model gateway is scripted (AGENTS.md rule 2).
The shop's copy below is NOT from production: production does not store the model's document."""
import copy
import json
import unittest

from tests.test_route_honesty import GOA, LAW, decide, one_page_only
from tests.test_site_content_engine import CONTENT, ScriptedGateway

from omni_prod import site_content as SC
from omni_prod.site_content import agents as A
from omni_prod.site_content import facts as Fx
from omni_prod.site_content import schema as K
from omni_prod.site_content import validate as V


class Scripted(ScriptedGateway):
    """The content model: its first document, then its corrected one (the production run's two calls)."""

    def __init__(self, first, corrected):
        super().__init__(content=first)
        self.docs = [first, corrected]

    def complete_json(self, *, system, user, max_tokens=4096, images=(), **kw):
        if system == A._CONTENT_SYSTEM:
            self.calls.append(('content', user))
            return copy.deepcopy(self.docs[min(len([c for c in self.calls if c[0] == 'content']), 2) - 1])
        return super().complete_json(system=system, user=user, max_tokens=max_tokens, images=images, **kw)


ITEMS = [('נרגילות', 'נרגילות בגדלים ובסגנונות שונים, לבית ולאירוח.'), ('סיגריות', 'מבחר סיגריות ממותגים שונים.'),
         ('טבק לנרגילה', 'טבק לנרגילה בטעמים שונים.'),
         ('מוצרים נלווים לנרגילות', 'פחמים, צינורות, ראשים ואביזרים לנרגילה.'),
         ('באנגים', 'באנגים מזכוכית ומחומרים נוספים.'), ('ניירות גלגול', 'ניירות גלגול ופילטרים.'),
         ('גרינדרים', 'גרינדרים בגדלים שונים.'), ('קופסאות אחסון', 'קופסאות לשמירה על הטבק והאביזרים.'),
         ('מצתים', 'מצתים ומציתים לכל שימוש.')]
SHOP = {
    'schema': K.SCHEMA, 'tagline': 'מוצרי עישון ואביזרים בירושלים',
    'description': 'GOA - מוצרי עישון: נרגילות, טבק, סיגריות ואביזרים במקום אחד.',
    'sections': {
        'hero': {'title': 'GOA - מוצרי עישון', 'lead': 'נרגילות, טבק, סיגריות וכל האביזרים שמסביב, במקום אחד.',
                 'cta': 'התקשרו אלינו'},
        'services': {'title': 'מה אנחנו מוכרים', 'nav': 'מוצרים', 'items': [{'title': t, 'desc': d} for t, d in ITEMS]},
        'about': {'title': 'על החנות', 'nav': 'עלינו',
                  'paragraphs': ['GOA היא חנות למוצרי עישון: נרגילות, טבק לנרגילה, סיגריות ואביזרים.']},
        'cta': {'title': 'רוצים לשאול על מוצר?', 'text': 'התקשרו אלינו ונשמח לעזור.'},
        'contact': {'title': 'צרו קשר', 'nav': 'צור קשר'},
    },
}
PRICE = 'משלוח עד הבית ב-30 ₪.'          # the invented fact: a price and a number the customer never gave


def shop(items=8, process_lead=None):
    doc = copy.deepcopy(SHOP)
    doc['sections']['services']['items'] = doc['sections']['services']['items'][:items]
    if process_lead is not None:
        doc['sections']['process'] = {'title': 'איך מזמינים', 'nav': 'איך מזמינים', 'lead': process_lead,
                                      'steps': [{'title': 'בוחרים', 'desc': 'בוחרים את המוצרים מהרשימה.'},
                                                {'title': 'מתקשרים', 'desc': 'מתקשרים לחנות ומזמינים.'}]}
    return doc


def generate_shop(first, corrected):
    from tests.test_site_content_agents import routed
    gw = Scripted(first, corrected)
    with one_page_only():
        engine = routed(gw, prompt=GOA)
    files = engine.generator.generate(engine.architect.create_spec(GOA))
    return gw, engine, {f.path: f.content for f in files}


class AnInventedFactAfterTheOneCorrection(unittest.TestCase):
    maxDiff = None

    def test_the_production_shape_needs_no_lawyer_sections_now(self):
        # production's first document lacked process and FAQ (SCHEMA_SHAPE x2) and had 9 items; now only the 9 items
        gw, engine, files = generate_shop(shop(items=9), shop(items=8))
        self.assertEqual([p['code'] for p in engine.site_report['corrected']], ['TOO_MANY'])
        self.assertNotIn('stripped', engine.site_report)
        self.assertIn('process: offered, the model left it out', engine.site_report['skipped'])
        self.assertEqual([r for r, _ in gw.calls].count('content'), 2)

    def test_one_invented_sentence_is_removed_and_the_build_goes_on(self):
        lead = 'בוחרים מוצר ומתקשרים אלינו. ' + PRICE
        gw, engine, files = generate_shop(shop(items=9), shop(process_lead=lead))
        stored = json.loads(files['content/site.json'])['document']
        self.assertEqual(stored['sections']['process']['lead'], 'בוחרים מוצר ומתקשרים אלינו.')    # the rest, as written
        [entry] = engine.site_report['stripped']
        self.assertEqual((entry['path'], entry['codes'], entry['removed'], entry['field_removed']),
                         ('sections.process.lead', ['INVENTED_NUMBER', 'PRICE_NOT_GIVEN'], [PRICE], False))
        self.assertNotIn('₪', files['public/index.html'])
        self.assertEqual(SC.report(engine)['stripped'], engine.site_report['stripped'])        # in the evidence

    def test_an_optional_field_left_empty_is_removed(self):
        gw, engine, files = generate_shop(shop(items=9), shop(process_lead=PRICE))
        stored = json.loads(files['content/site.json'])['document']
        self.assertNotIn('lead', stored['sections']['process'])
        self.assertTrue(engine.site_report['stripped'][0]['field_removed'])

    def test_a_required_field_left_empty_still_fails_loudly(self):
        corrected = shop()
        corrected['sections']['hero']['lead'] = PRICE                  # hero.lead is required
        with self.assertRaises(A.SiteContentInvalid) as caught:
            generate_shop(shop(items=9), corrected)
        self.assertIn('sections.hero.lead PRICE_NOT_GIVEN', str(caught.exception))

    def test_another_problem_beside_it_still_fails_loudly(self):
        corrected = shop(items=9, process_lead='בוחרים מוצר. ' + PRICE)            # TOO_MANY is not invented
        with self.assertRaises(A.SiteContentInvalid):
            generate_shop(shop(items=9), corrected)

    def test_strip_invented_alone(self):
        sheet = Fx.fact_sheet(LAW)
        route = decide(LAW)
        offered, _ = K.offered_sections(sheet, route.palette_entry, route.order, route.outline_titles)

        def check(d):
            return V.validate(d, sheet, offered, route.outline_titles)
        doc = copy.deepcopy(CONTENT)
        steps = doc['sections']['process']['steps']
        steps[0]['desc'] = steps[0]['desc'] + ' הפגישה עולה 400 ₪.'
        out, removed, why = A.strip_invented(doc, check(doc), check, route.outline_titles)
        self.assertIsNone(why)
        self.assertEqual(out['sections']['process']['steps'][0]['desc'],
                         CONTENT['sections']['process']['steps'][0]['desc'])
        self.assertEqual(removed[0]['removed'], ['הפגישה עולה 400 ₪.'])
        self.assertEqual(V.blocking(check(out)), [])
        # one sentence in a required list item's field: refused, nothing removed
        steps[0]['desc'] = 'הפגישה עולה 400 ₪.'
        out, removed, why = A.strip_invented(doc, check(doc), check, route.outline_titles)
        self.assertEqual((out, removed), (None, []))
        self.assertIn('is required', why)
        # a fact in the wrong place is the customer's fact, not an invented one: refused
        steps[0]['desc'] = 'מספרים לנו מה קרה. התקשרו 03-5551234.'
        out, _, why = A.strip_invented(doc, check(doc), check, route.outline_titles)
        self.assertIsNone(out)
        self.assertIn('FACT_IN_COPY', why)

    def test_the_family_is_the_validators(self):
        self.assertLessEqual(set(A.INVENTED), set(V.CODES))
        self.assertNotIn('FACT_IN_COPY', A.INVENTED)
        self.assertNotIn('PRICE_CONTEXT', A.INVENTED)


if __name__ == '__main__':
    unittest.main()
