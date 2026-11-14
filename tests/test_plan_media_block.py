"""Michael 2026-11-14 (b3): the plan shows the media the build will make in its own block, from the contract -- not
from fields.goal.

Real rows: the butcher's brief exported from production (tests/fixtures/butcher_prj_fV8kB7FwuNimGw.json, revision 8;
the export reproduces the stored fingerprint, checked below). The customer asked for "תמונה ראשית גדולה: נתחי בקר
טריים על נייר קצבים על דלפק שיש, אור קר של בוקר"; the contract compiled from the brief requires that image, but the
plan's goal line (the intake model's free text) dropped it. Path: brief -> the same prompt the plan endpoint compiles
(investor_app._brief_prompt) -> creator_plan.build_plan_preview -> app.js mediaLines() in node."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from decimal import Decimal
from pathlib import Path

from omni_prod import discovery as d
from omni_prod.build_contract_repository import MemoryBuildContractRepository
from omni_prod.creator_plan import build_plan_preview
from omni_prod.product_architect import ProductArchitect

ROOT = Path(__file__).resolve().parents[1]
FX = json.loads((ROOT / 'tests' / 'fixtures' / 'butcher_prj_fV8kB7FwuNimGw.json').read_text(encoding='utf-8'))
SUBJECT = 'נתחי בקר טריים על נייר קצבים על דלפק שיש, אור קר של בוקר'


class _Quote:
    total_estimated_variable_usd = Decimal('0.40')
    total_authorized_variable_usd = Decimal('1.25')

    def to_dict(self):
        return {}


def brief():
    return d.Brief.from_dict(FX['brief'])


def preview():
    b = brief()
    prompt = (b.prompt + '\n' + d.requirements_text(b))[:12000]        # = investor_app._brief_prompt
    return build_plan_preview(
        architect=ProductArchitect(), repository=MemoryBuildContractRepository(), project_id=FX['project_id'],
        prompt=prompt, economics=lambda: _Quote(), durable_backend=True,
        infrastructure_readiness={'kinds': {}}, image_readiness={'status': 'PARTIAL', 'reason': 'configured'})


def media_lines(p, lang):
    source = (ROOT / 'omni_prod' / 'assets' / 'app.js').read_text()
    translations = source[source.index('const T ='):source.index('const S =')]
    fn = re.search(r'function mediaLines\(p\) \{.*?\n\}', source, re.S).group()
    js = (translations + f'\nconst S={{lang:{json.dumps(lang)}}};\nfunction t(k){{return T[S.lang][k];}}\n' + fn +
          f'\nconsole.log(JSON.stringify(mediaLines({json.dumps(p, ensure_ascii=False)})));')
    return json.loads(subprocess.run(['node', '-e', js], capture_output=True, text=True, check=True).stdout)


class MediaInThePlan(unittest.TestCase):
    def test_the_export_is_faithful(self):
        self.assertEqual(brief().fingerprint(), FX["fingerprint"])

    def test_the_goal_line_cannot_be_relied_on(self):
        """The reason for the separate block: the goal is the model's sentence and has no image in it."""
        goal = d.summary(brief(), 'he')['goal']
        self.assertNotIn('תמונה', goal)
        self.assertIn('תמונה ראשית גדולה', brief().prompt)

    def test_the_plan_carries_the_image_from_the_contract(self):
        media = preview()['media']
        self.assertEqual([(m['key'], m['required'], m['subject']) for m in media],
                         [('media.image.generate', True, SUBJECT)])

    @unittest.skipUnless(shutil.which('node'), 'node is required to execute app.js mediaLines()')
    def test_the_plan_tab_shows_the_image_in_its_own_block(self):
        p = preview()
        self.assertEqual(media_lines(p, 'he'), [f'תמונה ראשית: {SUBJECT}'])
        self.assertEqual(media_lines(p, 'en'), [f'Main image: {SUBJECT}'])
        from tests.evidence_notice import notice
        notice('plan media', f"butcher plan tab: {media_lines(p, 'he')[0]}")

    @unittest.skipUnless(shutil.which('node'), 'node is required to execute app.js mediaLines()')
    def test_optional_media_says_so_and_no_media_shows_nothing(self):
        self.assertEqual(media_lines({'media': [{'key': 'media.image.generate', 'purpose': 'hero/brand visual',
                                                 'required': False, 'subject': ''}]}, 'he'), ['תמונה ראשית (אופציונלי)'])
        self.assertEqual(media_lines({'media': []}, 'he'), [])

    def test_the_plan_tab_renders_the_block(self):
        # mediaLines is tested above; this guards only that renderPlan still renders it after the brief block.
        source = (ROOT / 'omni_prod' / 'assets' / 'app.js').read_text()
        self.assertIn("...(mediaLines(p).length ? [h('h3', {}, t('mediaTitle'))", source)


if __name__ == '__main__':
    unittest.main()
