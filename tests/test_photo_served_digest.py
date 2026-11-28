"""The digest the spec demands for the customer's photo is the digest of the file the page serves (rehearsal
46016272646, 2026-11-27).

Found: the pilates rehearsal's photo path worked (file carried, hero kept, /assets/148ai-upload-1.webp served 200) and
the build still failed after 4 repair rounds. The spec said the served image has SHA-256 d03a2af3... (the digest of the
customer's ORIGINAL jpeg, from the brief's binding line, discovery.py), while the generated test expected 31d4cafd...
(the digest of the web rendition the page carries, which the model read from the file header). The image-weight
converter (uploaded_assets._MainImage, web_rendition) always writes a different file than the one uploaded, so no file
could satisfy the spec. A bug of Claude's, in the converter's merge: it left the digest in the prompt as it was.

Real path: the fixture photo of the rehearsal (tests/fixtures/rehearsal/customer_photo.jpg), the real
install_main_image, the real a4.install with its page fit, and the repository transform that writes assets/.
"""
import hashlib
import re
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from omni_prod import a4
from omni_prod import discovery as d
from omni_prod import uploaded_assets as U
from omni_prod.repository_assets import file_bytes

PHOTO = Path(__file__).parent / 'fixtures' / 'rehearsal' / 'customer_photo.jpg'
ORIGINAL = PHOTO.read_bytes()
ORIGINAL_SHA = hashlib.sha256(ORIGINAL).hexdigest()
PATH = 'assets/148ai-upload-1.webp'


def _prompt():
    return ('Build a pilates studio site.\n'
            f'Uploaded image 1 attachment: att_{1:032x}; sha256={ORIGINAL_SHA}; src="{d.UPLOAD_MARKER}1"; '
            'placement: hero; role place: "חזית העסק". The customer\'s own photo: use it AS IS.')


def _installed(budget=None):
    engine = SimpleNamespace(executor=SimpleNamespace(), repository_transform=None)
    row = {'sha256': ORIGINAL_SHA, 'mime': 'image/jpeg', 'width': 1080, 'height': 1920}
    with mock.patch.object(U, 'AttachmentRepository') as Repo:
        Repo.return_value.get.return_value = row
        Repo.return_value.read.return_value = ORIGINAL
        prompt = U.install_main_image(engine, prompt=_prompt(), pool=object(), store=object(), project_id='p',
                                      account_id='a')
    if budget is not None:
        with mock.patch.object(a4, 'PAGE_IMAGE_BUDGET_BYTES', budget), mock.patch.dict('os.environ', {}, clear=False):
            prompt = a4.install(engine, prompt=prompt)
    return engine, prompt


def _served(engine) -> str:
    """sha256 of the file the page serves: the repository the build writes, as the sandbox and the export write it."""
    repo = engine.repository_transform({'app.py': f'<img src="{d.UPLOAD_MARKER}1" alt="x">'})
    return hashlib.sha256(file_bytes(PATH, repo[PATH])).hexdigest()


def _digests(prompt: str) -> set:
    return set(re.findall(r'sha256=([0-9a-f]{64})', prompt))


class TheSpecNamesTheServedFile(unittest.TestCase):
    def test_the_converter_really_changes_the_bytes(self):          # the premise: original and served differ
        engine, _ = _installed()
        self.assertNotEqual(_served(engine), ORIGINAL_SHA)

    def test_the_prompt_the_spec_is_built_from_names_only_the_served_digest(self):
        engine, prompt = _installed()
        self.assertEqual(_digests(prompt), {_served(engine)})
        self.assertNotIn(ORIGINAL_SHA, prompt)

    def test_after_the_page_fit_changes_the_bytes_again_the_prompt_follows_them(self):
        plain, _ = _installed()
        engine, prompt = _installed(budget=len(file_bytes(PATH, plain.repository_transform(
            {'app.py': f'<img src="{d.UPLOAD_MARKER}1" alt="x">'})[PATH])) // 2)
        self.assertNotEqual(_served(engine), _served(plain))        # the fit really re-encoded it
        self.assertEqual(_digests(prompt), {_served(engine)})

    def test_a_digest_that_is_not_the_stored_files_still_fails_loudly(self):
        row = {'sha256': '0' * 64, 'mime': 'image/jpeg', 'width': 1080, 'height': 1920}
        with mock.patch.object(U, 'AttachmentRepository') as Repo:
            Repo.return_value.get.return_value = row
            with self.assertRaises(ValueError):
                U.install_main_image(SimpleNamespace(executor=SimpleNamespace(), repository_transform=None),
                                     prompt=_prompt(), pool=object(), store=object(), project_id='p', account_id='a')


if __name__ == '__main__':
    unittest.main()
