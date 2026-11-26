"""The customer's uploaded photo is used AS IS, never dropped (production 2026-11-15, bld_09482b26, "סבא שמעון").

The customer uploaded his grandfather's photo with the message "לא ישמרו פרטים". Only "one image + the word logo" was
ever bound into the brief, so the photo went nowhere, the sentence "תמונה ראשית: סבא שמעון בסינר..." was filed as
"Visual references (inspiration only)", and a different man was generated. The assistant also said the image "goes
with the change as context" -- it went nowhere.

Tier 1 (Michael 2026-11-15): an uploaded image chosen as the main image is used as is, with no generation. Every image
gets an explicit role from the customer, never delegated (16:15): what it is (person / product / place / logo / other),
who or what exactly, and only then what to do with it. Changing it (tier 2) is said as not available yet.
"""
import hashlib
import unittest

from omni_prod import discovery as d
from omni_prod.conversation.store import MemoryConversationStore
from tests import real_images
from omni_prod.conversation.supervisor import ConversationSupervisor
from tests.test_conversation_os import MemoryBriefs

# the production request of bld_09482b26, verbatim (intake_messages 2026-11-15 11:47:28Z)
SHIMON = ('האטליז של סבא שמעון, רחוב נתיב המזלות 22, ירושלים, טלפון 0504000162. שעות: א׳–ה׳ 07:00–19:00, '
          'ו׳ 07:00–14:00, שבת סגור. בשר בקר טרי, עוף, הודו, קציצות מוכנות, שיפודים להזמנה. כפתור להתקשרות. '
          'תמונה ראשית: סבא שמעון בסינר מאחורי הדלפק, בסצנת אטליז, עם סכין קצבים ביד.')
PHOTO = {'id': 'att_3faab1998b724bbcaf3e67d74d76c9e1', 'kind': 'image', 'mime': 'image/jpeg', 'size_bytes': 157491,
         'width': 1080, 'height': 1920, 'sha256': 'c4b4d78ba1d1982107eb22b88fe7076754939241218ebe88325e687adf731b9f'}


def _conversation():
    briefs = MemoryBriefs()
    s = ConversationSupervisor(briefs=briefs, store=MemoryConversationStore())
    s.turn(project_id='p', account_id='a', message=SHIMON, lang='he')
    return s, briefs


def _asked(turn):
    return [q.id for q in turn.questions]


WHO = 'סבא שמעון, הבעלים'


class TheUploadIsBoundAndAsked(unittest.TestCase):
    """Michael 2026-11-15 16:15: every image gets an explicit role -- WHAT it is first, then what to do with it."""

    def test_the_production_upload_is_bound_and_asked_what_it_is_first(self):
        s, briefs = _conversation()
        t = s.turn(project_id='p', account_id='a', message='לא ישמרו פרטים', attachments=[PHOTO], lang='he')
        brief = briefs.latest('p').brief
        self.assertEqual(brief.assets['image']['sha256'], PHOTO['sha256'])
        self.assertEqual(_asked(t), ['image_kind'])               # in context: right after the upload, and kind first
        self.assertNotIn('image_use', [q.id for q in d.pending(brief)])   # no blind "what to do" before the role
        self.assertFalse(d.complete(brief))
        self.assertNotIn('מועברת כהקשר', t.reply)                 # the untrue sentence of 2026-11-15
        self.assertIn('שמרתי תמונה אחת בבקשה של הפרויקט', t.reply)

    def test_kind_then_who_then_what_to_do_and_the_role_reaches_alt_and_canon(self):
        s, briefs = _conversation()
        t = s.turn(project_id='p', account_id='a', message='לא ישמרו פרטים', attachments=[PHOTO], lang='he')
        t = s.turn(project_id='p', account_id='a', answers={'image_kind': 'person'}, lang='he')
        self.assertEqual(_asked(t), ['image_who_person'])
        t = s.turn(project_id='p', account_id='a', message=WHO, lang='he')       # typed: the answer, not a request
        self.assertEqual(briefs.latest('p').brief.values()['image_identity'], WHO)
        self.assertEqual(_asked(t), ['image_use'])
        self.assertEqual(d.BY_ID['image_use'].recommended, 'as_is')          # suggested by kind
        t = s.turn(project_id='p', account_id='a', answers={'image_use': 'as_is'}, lang='he')
        self.assertEqual(_asked(t), ['image_place_person'])                 # then: where on the page
        self.assertEqual(d.BY_ID['image_place_person'].recommended, 'hero')
        t = s.turn(project_id='p', account_id='a', answers={'image_place_person': 'hero'}, lang='he')
        brief = briefs.latest('p').brief
        self.assertIn(f'role person: "{WHO}"', d.requirements_text(brief))
        self.assertIn(f'תמונה שהעלית (אדם): {WHO} — תופיע בדף כמו שהיא, התמונה הראשית בראש הדף.',
                      d.gate_canon(brief)['lines'])

    def test_the_whole_conversation_reaches_the_spec_with_the_photo(self):
        s, briefs = _conversation()
        t = s.turn(project_id='p', account_id='a', message='לא ישמרו פרטים', attachments=[PHOTO], lang='he')
        answer = {'image_kind': 'person', 'image_who_person': WHO, 'image_use': 'as_is'}
        asked = []
        for _ in range(14):                                     # bounded: the production flow has 8 questions
            if not t.questions:
                break
            q = t.questions[0]
            asked.append(q.id)
            self.assertFalse(briefs.latest('p').complete)
            t = s.turn(project_id='p', account_id='a', lang='he',
                       answers={q.id: answer.get(q.id) or (q.options[0].value if q.options else 'x')})
        self.assertEqual(asked[:3], ['image_kind', 'image_who_person', 'image_use'])
        row = briefs.latest('p')
        self.assertTrue(row.complete)
        self.assertIn(d.MAIN_IMAGE_MARKER, d.requirements_text(row.brief))

    def test_each_kind_asks_its_own_question(self):
        b = d.start(SHIMON)
        b.assets['image'] = dict(PHOTO)
        for kind, qid in (('person', 'image_who_person'), ('product', 'image_who_product'),
                          ('place', 'image_who_place'), ('other', 'image_who_other')):
            self.assertEqual(d.next_image_question(d.answer(b, {'image_kind': kind})).id, qid)
        other = d.answer(d.answer(b, {'image_kind': 'other'}), {'image_who_other': 'תעודת כשרות, בתחתית הדף'})
        self.assertEqual(d.next_image_question(other).id, 'image_use_other')
        self.assertEqual(d.BY_ID['image_use_other'].recommended, 'inspiration')

    def test_my_logo_takes_the_existing_logo_path(self):
        b = d.start(SHIMON)
        b.assets['image'] = dict(PHOTO)
        b = d.answer(b, {'image_kind': 'logo'})
        self.assertEqual(b.assets['logo']['id'], PHOTO['id'])
        self.assertNotIn('image', b.assets)
        self.assertIsNone(d.next_image_question(b))
        self.assertIn('148ai-asset://logo', d.requirements_text(b))

    def test_change_is_said_unavailable_and_never_becomes_as_is(self):
        s, briefs = _conversation()
        s.turn(project_id='p', account_id='a', message='התמונה', attachments=[PHOTO], lang='he')
        s.turn(project_id='p', account_id='a', answers={'image_kind': 'person'}, lang='he')
        s.turn(project_id='p', account_id='a', answers={'image_who_person': WHO}, lang='he')
        t = s.turn(project_id='p', account_id='a', answers={'image_use': 'change'}, lang='he')
        brief = briefs.latest('p').brief
        self.assertNotIn('image_use', brief.fields)
        self.assertIsNone(d.main_image(brief))
        self.assertIn('עוד לא זמין', t.reply)
        self.assertEqual(_asked(t), ['image_use'])

    def test_the_role_is_never_delegated_or_assumed(self):
        for q in d.IMAGE_QUESTIONS:
            self.assertFalse(q.delegable, q.id)
        self.assertEqual({o.value for o in d.BY_ID['image_use'].options}, {'as_is', 'change', 'inspiration'})

    def test_an_image_alone_before_any_build_is_bound_too(self):
        s, briefs = _conversation()
        t = s.turn(project_id='p', account_id='a', attachments=[PHOTO], lang='he')
        self.assertEqual(briefs.latest('p').brief.assets['image']['id'], PHOTO['id'])
        self.assertEqual(_asked(t), ['image_kind'])

    def test_the_same_bytes_twice_are_one_image(self):
        s, briefs = _conversation()
        twin = {**PHOTO, 'id': 'att_5a469bdf79f4494184a579aa4852af0d'}
        s.turn(project_id='p', account_id='a', message='התמונה', attachments=[PHOTO, twin], lang='he')
        self.assertEqual(briefs.latest('p').brief.assets['image']['sha256'], PHOTO['sha256'])

    def test_a_new_image_asks_its_role_again(self):
        s, briefs = _conversation()
        s.turn(project_id='p', account_id='a', message='התמונה', attachments=[PHOTO], lang='he')
        for a in ({'image_kind': 'person'}, {'image_who_person': WHO}, {'image_use': 'as_is'}):
            s.turn(project_id='p', account_id='a', answers=a, lang='he')
        self.assertEqual(briefs.latest('p').brief.values()['image_use'], 'as_is')
        other = {**PHOTO, 'id': 'att_' + 'e' * 32, 'sha256': 'f' * 64}
        t = s.turn(project_id='p', account_id='a', message='תמונה אחרת', attachments=[other], lang='he')
        for f in d.IMAGE_FIELDS:
            self.assertNotIn(f, briefs.latest('p').brief.fields)
        self.assertEqual(_asked(t), ['image_kind'])

    def test_the_logo_path_is_unchanged(self):
        s, briefs = _conversation()
        s.turn(project_id='p', account_id='a', message='זה הלוגו', attachments=[PHOTO], lang='he')
        brief = briefs.latest('p').brief
        self.assertEqual(brief.assets['logo']['id'], PHOTO['id'])
        self.assertNotIn('image', brief.assets)


class AsIsMeansAsIs(unittest.TestCase):
    def _brief(self, use, kind='person', who=WHO):
        b = d.start(SHIMON)
        b.assets['image'] = {k: PHOTO[k] for k in ('id', 'sha256', 'mime', 'size_bytes', 'width', 'height')}
        b = d.answer(b, {'image_kind': kind})
        b = d.answer(b, {f'image_who_{kind}': who})
        return d.answer(b, {'image_use' if kind != 'other' else 'image_use_other': use})

    def test_as_is_binds_the_photo_and_generates_nothing(self):
        from omni_prod.product_architect import ProductArchitect
        b = d.answer(self._brief('as_is'), {'image_place_person': 'hero'})
        text = d.requirements_text(b)
        self.assertIn(f'{d.UPLOADED_IMAGE_PREFIX}1 attachment: {PHOTO["id"]}; sha256={PHOTO["sha256"]}; '
                      f'src="{d.MAIN_IMAGE_MARKER}"; placement: hero;', text)
        self.assertIn(d.MAIN_IMAGE_MARKER, text)
        keys = [r.key for r in ProductArchitect().compile(b.prompt + '\n' + text, project_id='p',
                                                          contract_version=1).capability_plan.requirements]
        self.assertNotIn('media.image.generate', keys)

    def test_without_the_photo_the_same_request_still_generates(self):
        from omni_prod.product_architect import ProductArchitect
        b = d.start(SHIMON)
        keys = [r.key for r in ProductArchitect().compile(b.prompt + '\n' + d.requirements_text(b), project_id='p',
                                                          contract_version=1).capability_plan.requirements]
        self.assertIn('media.image.generate', keys)

    def test_inspiration_shows_nothing_and_keeps_generation(self):
        b = self._brief('inspiration')
        text = d.requirements_text(b)
        self.assertNotIn(d.MAIN_IMAGE_MARKER, text)
        self.assertIn('inspiration only', text)
        self.assertEqual(d.image_exclusions(b), [])

    def test_a_quote_in_the_role_cannot_break_the_alt(self):
        b = self._brief('as_is', who='המוצר "הכי טוב" שלנו')
        self.assertEqual(d.image_role(b)['alt'], 'המוצר ״הכי טוב״ שלנו')

    def test_a_typed_as_is_is_not_the_customers_button(self):
        b = d.start(SHIMON)
        b.assets['image'] = dict(PHOTO)
        b.fields['image_use'] = {'value': 'as_is', 'source': 'message', 'question_id': 'image_use'}
        self.assertIsNone(d.main_image(b))

    def test_briefs_without_an_upload_keep_their_fingerprint(self):
        b = d.start(SHIMON)
        before = b.fingerprint()
        self.assertNotIn('image_use', [q.id for q in d.pending(b)])
        self.assertEqual(before, d.Brief.from_dict(b.to_dict()).fingerprint())
        self.assertNotIn('Uploaded main image', d.requirements_text(b))


class TheWorkerUsesTheBytes(unittest.TestCase):
    DATA = real_images.jpeg(7, (1080, 1920))      # a real photo: every photo is converted (image weight, 2026-11-26)

    def _image(self):
        from omni_prod.uploaded_assets import _MainImage
        return _MainImage(self.DATA, 'image/jpeg', hashlib.sha256(self.DATA).hexdigest(), 'סבא שמעון', 1080, 1920)

    def test_the_marker_becomes_the_verified_bytes(self):
        from omni_prod.generated_images import _Transform
        img = self._image()
        out = _Transform(None, [img])({'index.html': f'<img src="{d.MAIN_IMAGE_MARKER}" alt="סבא שמעון">'})
        self.assertIn(img.uri, out['index.html'])
        self.assertNotIn(d.MAIN_IMAGE_MARKER, out['index.html'])

    def test_wrong_bytes_fail_loudly(self):
        from omni_prod.uploaded_assets import _MainImage
        with self.assertRaises(ValueError):
            _MainImage(self.DATA, 'image/jpeg', '0' * 64, 'x')

    def test_a_page_without_the_photo_is_not_accepted(self):
        from omni_prod.uploaded_assets import MAIN_ACCEPTANCE_ID, MainImageExecutor
        from tests.test_repair_stop_loss import _Executor
        img = self._image()
        page = '<img src="generated.png" alt="גבר מבוגר">'
        ex = MainImageExecutor(_Executor(passing={page}), img)
        report = ex.execute(repository={'app.py': page}, spec='s')
        self.assertFalse(report.passed)
        self.assertIn(MAIN_ACCEPTANCE_ID, [f.acceptance_id for f in report.failures])
        good = f'<img src="{img.uri}" alt="סבא שמעון">'
        self.assertTrue(MainImageExecutor(_Executor(passing={good}), img).execute(
            repository={'app.py': good}, spec='s').passed)

    def test_the_worker_installs_every_placed_photo_from_the_brief(self):
        from unittest.mock import MagicMock, patch
        from omni_prod import uploaded_assets as U
        digest = hashlib.sha256(self.DATA).hexdigest()
        b = d.start(SHIMON)
        for n, (kind, who, place) in enumerate((('person', WHO, 'hero'), ('product', 'שיפודי פרגית', 'products')), 1):
            b.assets['image'] = {**PHOTO, 'id': f'att_{n:032x}', 'sha256': digest}
            for a in ({'image_kind': kind}, {f'image_who_{kind}': who}, {'image_use': 'as_is'},
                      {f'image_place_{kind}': place}):
                b = d.answer(b, a)
        prompt = b.prompt + '\n' + d.requirements_text(b)
        row = {'sha256': digest, 'mime': 'image/jpeg', 'width': 1080, 'height': 1920}
        engine = MagicMock(spec=['executor', 'repository_transform'])
        engine.repository_transform = None
        with patch.object(U, 'AttachmentRepository') as Repo:
            Repo.return_value.get.return_value = row
            Repo.return_value.read.return_value = self.DATA
            out = U.install_main_image(engine, prompt=prompt, pool=object(), store=object(), project_id='p',
                                       account_id='a')
        # image weight (2026-11-26): the model is told the size and type of the file the page carries -- the photo
        # converted for its place (a 1080x1920 upload: 1600 px high as the hero, 1024 px in the products)
        first, second = engine.executor.images
        self.assertEqual((first.height, second.height), (1600, 1024))
        self.assertIn(f'- image 1: src="148ai-asset://upload/1"; place: hero; {first.width}x1600 px; {first.mime}; '
                      f'alt="{WHO}"', out)
        self.assertIn(f'- image 2: src="148ai-asset://upload/2"; place: products; {second.width}x1024 px; '
                      f'{second.mime}; alt="שיפודי פרגית"', out)
        self.assertEqual([i.alt for i in engine.executor.images], [WHO, 'שיפודי פרגית'])
        self.assertEqual(U.install_main_image(engine, prompt=SHIMON, pool=None, store=None, project_id='p',
                                              account_id='a'), SHIMON)   # no photo line: nothing changes
        row['sha256'] = '0' * 64
        with patch.object(U, 'AttachmentRepository') as Repo, self.assertRaises(ValueError):
            Repo.return_value.get.return_value = row
            U.install_main_image(engine, prompt=prompt, pool=object(), store=object(), project_id='p', account_id='a')

    def test_every_placed_photo_must_be_on_the_page(self):
        from omni_prod.uploaded_assets import MAIN_ACCEPTANCE_ID, MainImageExecutor, _MainImage
        from tests.test_repair_stop_loss import _Executor
        a = _MainImage(self.DATA, 'image/jpeg', hashlib.sha256(self.DATA).hexdigest(), WHO, index=1, place='hero')
        other = self.DATA + b'skewers'
        b = _MainImage(other, 'image/jpeg', hashlib.sha256(other).hexdigest(), 'שיפודים', index=2, place='products')
        only_first = f'<img src="{a.uri}" alt="{WHO}">'
        report = MainImageExecutor(_Executor(passing={only_first}), [a, b]).execute(
            repository={'app.py': only_first}, spec='s')
        self.assertFalse(report.passed)
        self.assertEqual([f.acceptance_id for f in report.failures], [MAIN_ACCEPTANCE_ID])
        self.assertIn('148ai-asset://upload/2', report.failures[0].message)


class ThePlaceIsChecked(unittest.TestCase):
    """The owner, 2026-11-16 00:18 / 00:49: the same photo may sit in two places, each checked in its own place; a
    photo for a place the page does not have fails with what is missing and what to add."""
    DATA = real_images.jpeg(8)                     # a real photo: every photo is converted (image weight, 2026-11-26)

    def _run(self, page, images):
        from omni_prod.uploaded_assets import MainImageExecutor
        from tests.test_repair_stop_loss import _Executor
        return MainImageExecutor(_Executor(passing={page}), images).execute(repository={'app.py': page}, spec='s')

    def _img(self, index, place, data=None):
        from omni_prod.uploaded_assets import _MainImage
        data = data or self.DATA
        return _MainImage(data, 'image/jpeg', hashlib.sha256(data).hexdigest(), WHO, index=index, place=place)

    def test_the_same_photo_in_two_places_is_checked_in_each(self):
        hero, gallery = self._img(1, 'hero'), self._img(2, 'gallery')          # same bytes, two markers
        self.assertEqual(hero.sha256, gallery.sha256)
        both = (f'<header><img src="{hero.marker}" alt="{WHO}"></header>'
                f'<section id="gallery"><h2>גלריה</h2><img src="{gallery.marker}" alt="{WHO}"></section>')
        self.assertTrue(self._run(both, [hero, gallery]).passed)
        only_hero = f'<header><img src="{hero.marker}" alt="{WHO}"></header><section><h2>גלריה</h2></section>'
        report = self._run(only_hero, [hero, gallery])
        self.assertFalse(report.passed)
        self.assertIn('148ai-asset://upload/2', report.failures[0].message)

    def test_a_place_the_page_does_not_have_says_what_is_missing_and_what_to_add(self):
        story = self._img(1, 'story')
        page = f'<main><h1>אטליז</h1></main><footer><img src="{story.marker}" alt="{WHO}"></footer>'
        report = self._run(page, [story])
        self.assertFalse(report.passed)
        msg = report.failures[0].message
        self.assertIn('the page has no such section', msg)
        self.assertIn('Add <section> with the heading "הסיפור שלנו"', msg)

    def test_a_photo_outside_its_section_is_told_to_move_into_it(self):
        story = self._img(1, 'story')
        page = (f'<section><h2>הסיפור שלנו</h2><p>25 שנה</p></section>'
                f'<footer><img src="{story.marker}" alt="{WHO}"></footer>')
        msg = self._run(page, [story]).failures[0].message
        self.assertIn('not inside the story section', msg)
        inside = f'<section class="about"><h2>הסיפור שלנו</h2><img src="{story.marker}" alt="{WHO}"></section>'
        self.assertTrue(self._run(inside, [story]).passed)


class SeveralPlaces(unittest.TestCase):
    """Michael 2026-11-15, step 3: a page holds several images, and "where" decides the place."""

    def _decide(self, b, n, kind, who, place):
        b.assets['image'] = {**PHOTO, 'id': f'att_{n:032x}', 'sha256': f'{n:x}' * 64}
        for a in ({'image_kind': kind}, {f'image_who_{kind}': who}, {'image_use': 'as_is'}):
            b = d.answer(b, a)
        return d.answer(b, {f'image_place_{kind}': place})

    def test_two_photos_two_places_two_markers(self):
        b = self._decide(d.start(SHIMON), 1, 'person', WHO, 'hero')
        b = self._decide(b, 2, 'product', 'שיפודי פרגית', 'products')
        self.assertEqual([(i['place'], i['marker']) for i in d.placed_images(b)],
                         [('hero', '148ai-asset://upload/1'), ('products', '148ai-asset://upload/2')])
        self.assertNotIn('image', b.assets)                                    # decided: ready for the next one
        self.assertEqual(len(d.image_canon_lines(b)), 2)

    def test_one_main_image_per_page_said_and_asked_again(self):
        b = self._decide(d.start(SHIMON), 1, 'person', WHO, 'hero')
        b = self._decide(b, 2, 'place', 'הדלפק', 'hero')
        self.assertEqual(len(d.placed_images(b)), 1)
        self.assertEqual(b.hints.get('image_hero_taken'), 'yes')
        self.assertEqual(d.next_image_question(b).id, 'image_place_place')
        b = d.answer(b, {'image_place_place': 'gallery'})
        self.assertEqual([i['place'] for i in d.placed_images(b)], ['hero', 'gallery'])

    def test_the_place_is_suggested_by_kind(self):
        self.assertEqual({k: d.BY_ID[f'image_place_{k}'].recommended for k in ('person', 'product', 'place', 'other')},
                         {'person': 'hero', 'product': 'products', 'place': 'hero', 'other': 'gallery'})

    def test_only_a_photo_in_the_main_place_replaces_generation(self):
        b = self._decide(d.start(SHIMON), 1, 'product', 'שיפודים', 'products')
        self.assertEqual(d.image_exclusions(b), [])                 # the generated main image is still made
        b = self._decide(b, 2, 'person', WHO, 'hero')
        self.assertEqual(d.image_exclusions(b), ['media.image.generate'])

    def test_a_decided_photo_uploaded_again_is_not_asked_again(self):
        s, briefs = _conversation()
        s.turn(project_id='p', account_id='a', message='התמונה', attachments=[PHOTO], lang='he')
        for a in ({'image_kind': 'person'}, {'image_who_person': WHO}, {'image_use': 'as_is'},
                  {'image_place_person': 'hero'}):
            s.turn(project_id='p', account_id='a', answers=a, lang='he')
        t = s.turn(project_id='p', account_id='a', message='שוב התמונה', attachments=[PHOTO], lang='he')
        self.assertNotIn('image', briefs.latest('p').brief.assets)
        self.assertNotIn('image_kind', _asked(t))


if __name__ == '__main__':
    unittest.main()
