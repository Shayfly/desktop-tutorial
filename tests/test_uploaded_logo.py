import hashlib
import unittest
from unittest.mock import MagicMock, patch
from omni_prod import discovery as d
from omni_prod.attachments import AttachmentRepository
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from tests.test_conversation_os import MemoryBriefs

# warehouse 118: a carried logo is sniffed, so the test bytes start with the real PNG signature
SIG=b'\x89PNG\r\n\x1a\n'


class UploadedLogoTests(unittest.TestCase):
    def test_truncated_image_diagnostics_are_also_redacted(self):
        from omni_prod.uploaded_assets import logo_transform
        import base64
        data=SIG+bytes(range(256))*50
        t=logo_transform(data,'image/png',hashlib.sha256(data).hexdigest())
        fragment=base64.b64encode(data).decode()[-2900:]
        self.assertNotIn(fragment,t.redact_text('error: '+fragment+'\nnext line'))
        self.assertIn('next line',t.redact_text('error: '+fragment+'\nnext line'))

    def test_explicit_no_logo_removes_the_uploaded_binding(self):
        b=d.start('אתר תדמית')
        b.assets['logo']={'id':'att_'+'a'*32,'sha256':'b'*64}
        b=d.answer(b,{'logo':'none'})
        self.assertNotIn('logo',b.assets)
        self.assertNotIn('Uploaded logo attachment:',d.requirements_text(b))

    def test_comment_only_logo_does_not_satisfy_source_gate(self):
        from omni_prod.uploaded_assets import LogoExecutor
        from tests.test_repair_stop_loss import _Executor
        ex=LogoExecutor(_Executor(passing={'# original data:image/png;base64,abc'}),'data:image/png;base64,abc')
        self.assertFalse(ex.execute(repository={'app.py':'# original data:image/png;base64,abc'},spec='s').passed)
        self.assertTrue(ex._image_reference('index.html','<img src="data:image/png;base64,abc" alt="Logo">'))

    def test_executor_diagnostics_are_redacted_before_the_repair_call(self):
        from omni_prod.uploaded_assets import logo_transform
        from omni_prod.autonomous_core import ExecutionReport, AcceptanceFailure
        from tests.test_repair_stop_loss import _engine, _Repairer
        t=logo_transform(SIG+b'original image','image/png',hashlib.sha256(SIG+b'original image').hexdigest())
        class Echo:
            def execute(self, **kw):   # a diagnostic that echoes the image file itself (its envelope: the bytes)
                return ExecutionReport(False,(AcceptanceFailure('source',t.carried.envelope,t.carried.envelope),))
        class Recorder(_Repairer):
            def repair(self, **kw):
                self.seen=kw
                return super().repair(**kw)
        repair=Recorder(['v1'])
        engine=_engine(repair,Echo(),rounds=1)
        engine.repository_transform=t
        engine.build('p')
        self.assertNotIn(t.carried.encoded,str(repair.seen))
        self.assertIn('148ai-asset://logo',str(repair.seen))

    def test_missing_attachment_table_is_a_known_not_ready_state(self):
        pool=MagicMock()
        pool.connection.return_value.__enter__.return_value.execute.return_value.fetchone.return_value=(None,)
        repo=AttachmentRepository(pool,MagicMock())
        self.assertFalse(repo.schema_ready())

    def test_logo_attachment_is_bound_to_brief_fingerprint(self):
        briefs=MemoryBriefs()
        s=ConversationSupervisor(briefs=briefs,store=MemoryConversationStore())
        s.turn(project_id='p',account_id='a',message='אתר תדמית למטפחות ללא התחברות וללא פרטים אישיים',lang='he')
        s.turn(project_id='p',account_id='a',answers={'content_only':'yes'},lang='he')
        old=briefs.latest('p').fingerprint
        a={'id':'att_'+'a'*32,'kind':'image','mime':'image/png','sha256':'b'*64,'size_bytes':42}
        t=s.turn(project_id='p',account_id='a',message='תשתמש בזה כלוגו באתר',attachments=[a],lang='he')
        self.assertNotEqual(old,t.brief_row.fingerprint)
        text=d.requirements_text(t.brief_row.brief)
        self.assertIn(a['id'],text)
        self.assertIn('148ai-asset://logo',text)

    def test_materialization_uses_verified_bytes_and_cannot_leak_other_attachments(self):
        from omni_prod.uploaded_assets import logo_transform
        from omni_prod.repository_assets import file_bytes
        data=SIG+b'verified image bytes'
        digest=hashlib.sha256(data).hexdigest()
        transform=logo_transform(data,'image/png',digest)
        repo=transform({'index.html':'<img src="148ai-asset://logo" alt="Logo">'})
        # warehouse 118: the page references the logo FILE, and the file holds exactly the verified bytes
        self.assertEqual(repo['index.html'],'<img src="assets/148ai-logo.png" alt="Logo">')
        self.assertEqual(file_bytes('assets/148ai-logo.png',repo['assets/148ai-logo.png']),data)
        self.assertNotIn('148ai-asset://logo',repo['index.html'])
        with self.assertRaises(ValueError):logo_transform(data,'image/png','0'*64)

    def test_uploaded_image_bytes_are_not_sent_back_to_repair_model(self):
        from omni_prod.uploaded_assets import logo_transform
        from tests.test_repair_stop_loss import _engine, _Repairer, _Executor
        data=SIG+b'image bytes'*10000
        t=logo_transform(data,'image/png',hashlib.sha256(data).hexdigest())
        engine=_engine(_Repairer([]),_Executor())
        engine.repository_transform=t
        repo=t({'app.py':'<img src="148ai-asset://logo">'})
        summary=engine._repair_summary(repo)
        file=summary['files'][0]
        self.assertIn('content',file)
        self.assertIn('148ai-asset://logo',file['content'])
        self.assertNotIn('base64,',file['content'])
        self.assertEqual([f['path'] for f in summary['files']],['app.py'])      # 118: the image file is not shown


if __name__=='__main__':unittest.main()


class TheUploadedLogoShowsInTheSummary(unittest.TestCase):
    """The owner, 2026-11-23 (prj_5wRH_CceL2aSeQ): "רשמת שאין לוגו והעליתי בתמונה לוגו". A logo that was uploaded
    must read in the summary as the uploaded logo, not "I have one -- will upload later"."""

    def brief_with_logo(self):
        b = d.start('אתר לסוכן נסיעות')
        b.assets['image'] = {'id': 'att_' + 'a' * 32, 'sha256': 'b' * 64, 'mime': 'image/png', 'size_bytes': 100}
        return d.answer(b, {'image_kind': 'logo'})

    def test_an_uploaded_logo_sets_the_field_to_uploaded_and_keeps_the_asset(self):
        b = self.brief_with_logo()
        self.assertEqual(b.values().get('logo'), 'uploaded')
        self.assertEqual(b.assets.get('logo', {}).get('sha256'), 'b' * 64)
        self.assertNotIn('image', b.assets)                 # the image became the logo

    def test_the_summary_names_the_uploaded_logo_in_every_language(self):
        from omni_prod.conversation.supervisor import _label
        self.assertEqual(_label('logo', 'uploaded', 'he'), 'לוגו: הלוגו שהעליתם')
        self.assertEqual(_label('logo', 'uploaded', 'en'), 'logo: The logo you uploaded')

    def test_the_build_still_gets_the_uploaded_logo(self):
        self.assertIn('Uploaded logo attachment:', d.requirements_text(self.brief_with_logo()))

    def test_resaying_i_have_a_logo_never_downgrades_the_uploaded_one(self):
        from omni_prod.intake import agent as A
        from omni_prod.intake.interpreter import DeterministicInterpreter
        b = self.brief_with_logo()
        interp = DeterministicInterpreter().interpret('יש לי לוגו', b)       # proposes logo='later'
        res = A.apply(b, interp, infer_defaults=False)
        self.assertEqual(res.brief.values().get('logo'), 'uploaded')        # unchanged
        self.assertFalse([c for c in res.conflicts if c['field'] == 'logo'])  # and no "what is right?"
