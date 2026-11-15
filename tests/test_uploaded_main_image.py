"""The customer's uploaded photo is used AS IS, never dropped (production 2026-11-15, bld_09482b26, "סבא שמעון").

The customer uploaded his grandfather's photo with the message "לא ישמרו פרטים". Only "one image + the word logo" was
ever bound into the brief, so the photo went nowhere, the sentence "תמונה ראשית: סבא שמעון בסינר..." was filed as
"Visual references (inspiration only)", and a different man was generated. The assistant also said the image "goes
with the change as context" -- it went nowhere.

Tier 1 (Michael 2026-11-15): an uploaded image chosen as the main image is used as is, with no generation; the customer
is asked what an uploaded image is for (never delegated). Tier 2 (generation with a reference) is not offered yet.
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


class TheUploadIsBoundAndAsked(unittest.TestCase):
    def test_the_production_upload_is_bound_and_the_customer_is_asked(self):
        s, briefs = _conversation()
        t = s.turn(project_id='p', account_id='a', message='לא ישמרו פרטים', attachments=[PHOTO], lang='he')
        brief = briefs.latest('p').brief
        self.assertEqual(brief.assets['image']['sha256'], PHOTO['sha256'])
        self.assertIn('image_use', [q.id for q in d.must_ask(brief)])
        self.assertFalse(d.complete(brief))                      # no build before the customer says what it is for
        self.assertNotIn('מועברת כהקשר', t.reply)                 # the untrue sentence of 2026-11-15
        self.assertIn('שמרתי תמונה אחת בבקשה של הפרויקט', t.reply)

    def test_the_question_is_asked_before_the_spec_and_the_answer_reaches_the_build_text(self):
        s, briefs = _conversation()
        t = s.turn(project_id='p', account_id='a', message='לא ישמרו פרטים', attachments=[PHOTO], lang='he')
        asked = []
        for _ in range(12):                                     # bounded: the production flow has 6 questions
            if not t.questions:
                break
            q = t.questions[0]
            asked.append(q.id)
            if q.id != 'image_use':
                self.assertFalse(briefs.latest('p').complete)
            t = s.turn(project_id='p', account_id='a', lang='he',
                       answers={q.id: 'as_is' if q.id == 'image_use' else (q.options[0].value if q.options else 'x')})
        self.assertIn('image_use', asked)
        row = briefs.latest('p')
        self.assertTrue(row.complete)
        self.assertIn(d.MAIN_IMAGE_MARKER, d.requirements_text(row.brief))

    def test_the_role_is_never_delegated_or_assumed(self):
        q = d.BY_ID['image_use']
        self.assertFalse(q.delegable)
        self.assertEqual({o.value for o in q.options}, {'as_is', 'inspiration'})   # tier 2 not offered yet

    def test_an_image_alone_before_any_build_is_bound_too(self):
        s, briefs = _conversation()
        s.turn(project_id='p', account_id='a', attachments=[PHOTO], lang='he')
        self.assertEqual(briefs.latest('p').brief.assets['image']['id'], PHOTO['id'])

    def test_the_same_bytes_twice_are_one_image(self):
        s, briefs = _conversation()
        twin = {**PHOTO, 'id': 'att_5a469bdf79f4494184a579aa4852af0d'}
        s.turn(project_id='p', account_id='a', message='התמונה', attachments=[PHOTO, twin], lang='he')
        self.assertEqual(briefs.latest('p').brief.assets['image']['sha256'], PHOTO['sha256'])

    def test_a_new_image_asks_again(self):
        s, briefs = _conversation()
        s.turn(project_id='p', account_id='a', message='התמונה', attachments=[PHOTO], lang='he')
        s.turn(project_id='p', account_id='a', answers={'image_use': 'as_is'}, lang='he')
        self.assertEqual(briefs.latest('p').brief.values()['image_use'], 'as_is')
        other = {**PHOTO, 'id': 'att_' + 'e' * 32, 'sha256': 'f' * 64}
        s.turn(project_id='p', account_id='a', message='תמונה אחרת', attachments=[other], lang='he')
        self.assertNotIn('image_use', briefs.latest('p').brief.fields)

    def test_the_logo_path_is_unchanged(self):
        s, briefs = _conversation()
        s.turn(project_id='p', account_id='a', message='זה הלוגו', attachments=[PHOTO], lang='he')
        brief = briefs.latest('p').brief
        self.assertEqual(brief.assets['logo']['id'], PHOTO['id'])
        self.assertNotIn('image', brief.assets)


class AsIsMeansAsIs(unittest.TestCase):
    def _brief(self, use):
        b = d.start(SHIMON)
        b.assets['image'] = {k: PHOTO[k] for k in ('id', 'sha256', 'mime', 'size_bytes', 'width', 'height')}
        return d.answer(b, {'image_use': use})

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
