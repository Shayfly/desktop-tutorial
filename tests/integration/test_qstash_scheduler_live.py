"""Opt-in QStash administrative API verification, NOT delivery proof."""
import os
import unittest
import uuid

from omni_prod.providers.qstash_scheduler import QStashClient

_REASON = None
if os.environ.get("M5_QSTASH_LIVE") != "1":
    _REASON = "M5_QSTASH_LIVE=1 not set; no real QStash administrative test"
elif not os.environ.get("QSTASH_URL") or not os.environ.get("QSTASH_TOKEN"):
    _REASON = "QSTASH_URL / QSTASH_TOKEN not configured"


@unittest.skipIf(_REASON is not None, _REASON or "")
class QStashLiveApiTests(unittest.TestCase):
    def test_authenticated_api_access(self):
        client = QStashClient(base_url=os.environ["QSTASH_URL"], token=os.environ["QSTASH_TOKEN"])
        self.assertTrue(client.check_access())

    @unittest.skipUnless(os.environ.get("QSTASH_TEST_DESTINATION"),
                         "QSTASH_TEST_DESTINATION must be an operator-owned harmless probe receiver")
    def test_create_get_cancel_schedule(self):
        destination = os.environ["QSTASH_TEST_DESTINATION"]
        client = QStashClient(base_url=os.environ["QSTASH_URL"], token=os.environ["QSTASH_TOKEN"],
                              allowed_destinations=[destination])
        sid = "148ai-probe-" + uuid.uuid4().hex
        try:
            client.create(destination=destination, cron="0 0 29 2 *", schedule_id=sid,
                          payload={"probe": True, "id": sid})
            record = client.get(sid)
            self.assertIsInstance(record, dict)
            self.assertEqual(record.get("scheduleId"), sid)
        finally:
            client.cancel(sid)
        self.assertIsNone(client.get(sid))
        # This verifies administration only, not receipt, retries or signature verification.
