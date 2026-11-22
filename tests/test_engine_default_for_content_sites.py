"""The new engine is the default for content sites (the owner, 2026-11-22, DECISIONS.md).

The production worker's compose file is read as deployed (its defaults, no overrides) and the route's own decision code
is asked: every account's content site takes the new engine; an app never does (it keeps the existing path, with the
reason named); the fall-back switch (OMNI_SITE_LIBRARY=off from the host) sends everything back to the old path without a
code change. Mutations: tests/negative_controls/engine_default.json.
"""
import os
import re
import unittest
from pathlib import Path
from unittest import mock

import yaml

from omni_prod import site_content

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = re.compile(r'^\$\{([A-Z0-9_]+):-(.*)\}$')
APP = 'אפליקציה לניהול משמרות לעובדים: התחברות, טבלת משמרות, החלפות בין עובדים ואישור מנהל.'


def worker_env():
    return yaml.safe_load((ROOT / 'infra/worker-host/docker-compose.yml').read_text(encoding='utf-8'))['services']['worker']['environment']


def deployed(key):
    m = DEFAULT.match(str(worker_env()[key]))
    return m.group(2) if m else str(worker_env()[key])


class DefaultForContentSites(unittest.TestCase):
    def test_the_worker_is_deployed_with_the_new_engine_on(self):
        self.assertEqual(deployed(site_content.FLAG), 'on')
        self.assertNotIn(site_content.ACCOUNTS, worker_env())              # no account list: it is every account

    def test_no_account_is_turned_away_by_the_flag(self):
        with mock.patch.dict(os.environ, {site_content.FLAG: deployed(site_content.FLAG)}):
            for request in ({'user_id': 'usr_someone'}, {'user_id': 'usr_GCWlMxENgr9vpwph'}, {}):
                r = site_content.decide(APP, request)
                self.assertNotIn(r.reason, ('flag_off', 'account_not_listed'), request)

    def test_an_app_keeps_the_existing_path_and_says_why(self):
        with mock.patch.dict(os.environ, {site_content.FLAG: deployed(site_content.FLAG)}):
            r = site_content.decide(APP, {'user_id': 'usr_someone'})
        self.assertEqual((r.route, r.reason), (site_content.LEGACY, 'not_content_only'))

    def test_the_fall_back_switch_is_one_host_override_away(self):
        m = DEFAULT.match(str(worker_env()[site_content.FLAG]))
        self.assertTrue(m and m.group(1) == site_content.FLAG)            # WORKER_ENV_OVERRIDES can set it
        with mock.patch.dict(os.environ, {site_content.FLAG: 'off'}):
            self.assertEqual(site_content.decide(APP, {'user_id': 'usr_someone'}).reason, 'flag_off')


if __name__ == '__main__':
    unittest.main()
