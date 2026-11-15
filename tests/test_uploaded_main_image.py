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
        brief = briefs.latest('p').brief
        self.assertIn(f'{d.MAIN_IMAGE_ALT_PREFIX}person: "{WHO}"', d.requirements_text(brief))
        self.assertIn(f'תמונה שהעלית (אדם): {WHO} — תופיע בדף כמו שהיא.', d.gate_canon(brief)['lines'])
        from omni_prod.uploaded_assets import main_image_alt
        self.assertEqual(main_image_alt(brief.prompt + '\n' + d.requirements_text(brief)), WHO)

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
        b = self._brief('as_is')
        text = d.requirements_text(b)
        self.assertIn(f'{d.MAIN_IMAGE_PREFIX}{PHOTO["id"]}; sha256={PHOTO["sha256"]}.', text)
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
    DATA = b'\xff\xd8\xff' + b'grandfather' * 200

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

    def test_the_worker_installs_it_from_the_brief_line(self):
        from unittest.mock import MagicMock, patch
        from omni_prod import uploaded_assets as U
        digest = hashlib.sha256(self.DATA).hexdigest()
        prompt = SHIMON + f'\n{d.MAIN_IMAGE_PREFIX}{PHOTO["id"]}; sha256={digest}. This is the customer\'s own photo.'
        row = {'sha256': digest, 'mime': 'image/jpeg', 'width': 1080, 'height': 1920}
        engine = MagicMock(spec=['executor', 'repository_transform'])
        engine.repository_transform = None
        with patch.object(U, 'AttachmentRepository') as Repo:
            Repo.return_value.get.return_value = row
            Repo.return_value.read.return_value = self.DATA
            out = U.install_main_image(engine, prompt=prompt, pool=object(), store=object(), project_id='p',
                                       account_id='a')
        self.assertIn('1080x1920 px', out)
        self.assertIsInstance(engine.executor, U.MainImageExecutor)
        self.assertEqual(U.install_main_image(engine, prompt=SHIMON, pool=None, store=None, project_id='p',
                                              account_id='a'), SHIMON)   # no photo line: nothing changes
        row['sha256'] = '0' * 64
        with patch.object(U, 'AttachmentRepository') as Repo, self.assertRaises(ValueError):
            Repo.return_value.get.return_value = row
            U.install_main_image(engine, prompt=prompt, pool=object(), store=object(), project_id='p', account_id='a')


if __name__ == '__main__':
    unittest.main()
