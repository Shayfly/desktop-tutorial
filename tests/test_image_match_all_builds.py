"""Michael 2026-11-15: lens 11 on every build (OMNI_IMAGE_MATCH=all) -- prepared, reported, then switched on; the
first real customer build with it is watched, and a good build blocked means back to founder (a calibration finding).

The worker reads the flag from its compose environment: the default there is now 'all', and an operator can go back
to 'founder' through WORKER_ENV_OVERRIDES (the .env compose interpolates) without a code change. The default in code
stays 'founder', so any process that does not set the flag keeps the old behaviour."""
import os
import unittest
from pathlib import Path
from unittest import mock

import yaml

from omni_prod.image_match import enabled_for

COMPOSE = Path(__file__).resolve().parents[1] / 'infra' / 'worker-host' / 'docker-compose.yml'
CUSTOMER = {'user_id': 'usr_customer_x'}
FOUNDER = {'user_id': 'usr_GCWlMxENgr9vpwph'}


class TheWorkerChecksEveryBuild(unittest.TestCase):
    def test_the_build_worker_sets_all_with_an_override_path(self):
        env = yaml.safe_load(COMPOSE.read_text())['services']['worker']['environment']
        self.assertEqual(env['OMNI_IMAGE_MATCH'], '${OMNI_IMAGE_MATCH:-founder}')   # rolled back to founder

    def test_all_runs_the_check_on_a_customer_build(self):
        with mock.patch.dict(os.environ, {'OMNI_IMAGE_MATCH': 'all'}):
            self.assertTrue(enabled_for(CUSTOMER))
            self.assertTrue(enabled_for(FOUNDER))

    def test_founder_is_the_way_back(self):
        with mock.patch.dict(os.environ, {'OMNI_IMAGE_MATCH': 'founder'}):
            self.assertFalse(enabled_for(CUSTOMER))
            self.assertTrue(enabled_for(FOUNDER))

    def test_code_default_is_unchanged(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('OMNI_IMAGE_MATCH', None)
            self.assertFalse(enabled_for(CUSTOMER))


if __name__ == '__main__':
    unittest.main()
