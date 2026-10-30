import json
from pathlib import Path
import re
import subprocess
import unittest

from tests.test_m5_build_economics import DurableBuildRouteReservationTests


class BuildAllowanceMessageTests(unittest.TestCase):
    def test_refusal_is_structured_and_does_not_expose_provider_reason(self):
        _, _, enqueue, _, exc = DurableBuildRouteReservationTests()._run(reserve_allowed=False)
        self.assertEqual(exc.status_code, 402)
        self.assertIsInstance(exc.detail, dict)
        self.assertEqual(exc.detail['error'], 'build_allowance_exhausted')
        self.assertNotIn('paid-provider', json.dumps(exc.detail))
        self.assertIn('allowance', exc.detail['message'])
        enqueue.assert_not_called()

    def test_real_ui_explains_allowance_in_hebrew_and_english(self):
        source = (Path(__file__).resolve().parents[1] / 'omni_prod/assets/app.js').read_text()
        translations = source[source.index('const T ='):source.index('const S =')]
        explain = re.search(r'function explain\(err\) \{.*?\n\}', source, re.S).group()
        error = re.search(r'class ApiError extends Error \{.*?\n\}', source, re.S).group()
        js = translations + '\nconst S={lang:"he",signedIn:true};\nfunction t(k){return T[S.lang][k];}\n' + error + '\n' + explain
        js += '\nconst e=new ApiError(402,{error:"build_allowance_exhausted",message:"INTERNAL_SENTINEL"}); console.log(JSON.stringify([explain(e),(S.lang="en",explain(e))]));'
        p = subprocess.run(['node', '-e', js], capture_output=True, text=True, check=True)
        he, en = json.loads(p.stdout)
        self.assertIn('יתרה', he)
        self.assertIn('allowance', en)
        for message in (he, en):
            self.assertNotIn('paid-provider', message)
            self.assertNotIn('INTERNAL_SENTINEL', message)
