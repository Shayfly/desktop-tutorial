"""The new engine (the content route) is on for the owner's account only (the owner, 2026-11-21, inbox/001).

The production worker's compose file is read as deployed (its defaults, no overrides) and the route's own decision
code is asked: the owner's account takes the route, any other account does not, and the flag is never the global 'on'.
Mutations: tests/negative_controls/engine_on_for_the_owner.json.
"""
import os
import re
import unittest
from pathlib import Path
from unittest import mock

import yaml

from omni_prod import site_content

ROOT = Path(__file__).resolve().parents[1]
OWNER = 'usr_GCWlMxENgr9vpwph'
DEFAULT = re.compile(r'^\$\{([A-Z0-9_]+):-(.*)\}$')


def deployed_defaults(service='worker'):
    env = yaml.safe_load((ROOT / 'infra/worker-host/docker-compose.yml').read_text(encoding='utf-8'))['services'][service]['environment']
    out = {}
    for key, value in env.items():
        m = DEFAULT.match(str(value))
        out[key] = m.group(2) if m else str(value)
    return out


class OnForTheOwnerOnly(unittest.TestCase):
    def setUp(self):
        d = deployed_defaults()
        self.env = {site_content.FLAG: d[site_content.FLAG], site_content.ACCOUNTS: d[site_content.ACCOUNTS]}

    def test_the_worker_is_deployed_with_the_flag_on_accounts_and_the_owner_listed(self):
        self.assertEqual(self.env, {site_content.FLAG: 'accounts', site_content.ACCOUNTS: OWNER})

    def test_the_routes_own_code_reads_it_that_way(self):
        with mock.patch.dict(os.environ, self.env):
            self.assertEqual(site_content.mode(), 'accounts')
            self.assertEqual(site_content.accounts(), {OWNER})

    def test_another_account_stays_on_the_existing_path_and_the_owner_gets_past_the_account_check(self):
        with mock.patch.dict(os.environ, self.env):
            other = site_content.decide('anything', {'user_id': 'usr_someone_else'})
            self.assertEqual((other.route, other.reason), (site_content.LEGACY, 'account_not_listed'))
            anonymous = site_content.decide('anything', {})
            self.assertEqual(anonymous.reason, 'account_not_listed')
            owner = site_content.decide('anything', {'user_id': OWNER})
            self.assertNotIn(owner.reason, ('account_not_listed', 'flag_off'))

    def test_both_values_can_be_overridden_from_the_host_without_a_code_change(self):
        raw = yaml.safe_load((ROOT / 'infra/worker-host/docker-compose.yml').read_text(encoding='utf-8'))['services']['worker']['environment']
        for key in (site_content.FLAG, site_content.ACCOUNTS):
            m = DEFAULT.match(str(raw[key]))
            self.assertTrue(m and m.group(1) == key, raw[key])


if __name__ == '__main__':
    unittest.main()
