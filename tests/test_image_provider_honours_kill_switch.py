"""#93 C32_SCOPE_BYPASS: the image provider itself refuses a paid request while the kill switches are closed.

Matt's site: build_image_provider -> PredictionImageProvider.submit -> _json reached the transport with
OMNI_ZERO_COST_MODE=1 / OMNI_ALLOW_EXTERNAL_FALLBACK=0. The check now sits at that boundary, so every caller (the
capability stage, the Replicate image test, anything later) is covered. Synthetic transport only; no paid call.
"""
import io
import unittest

from omni_prod.capabilities import CapabilityRequirement
from omni_prod.model_policy import ModelPolicyViolation
from omni_prod.provider_contracts import ProviderTaskHandle
from omni_prod.providers.image_provider import MemorySubmissionJournal, build_image_provider

TOKEN = {'REPLICATE_API_TOKEN': 'test-only-synthetic'}
REQ = CapabilityRequirement(id='audit', key='media.image.generate', purpose='synthetic audit',
                            required=True, quantity=1, constraints={'prompt': 'test'})
CLOSED = [
    {'OMNI_ZERO_COST_MODE': '1', 'OMNI_ALLOW_EXTERNAL_FALLBACK': '0'},
    {'OMNI_ZERO_COST_MODE': '1', 'OMNI_ALLOW_EXTERNAL_FALLBACK': '1'},
    {'OMNI_ZERO_COST_MODE': '0', 'OMNI_ALLOW_EXTERNAL_FALLBACK': '0'},
    {},                                                    # not set at all: closed by default
]
OPEN = {'OMNI_ZERO_COST_MODE': '0', 'OMNI_ALLOW_EXTERNAL_FALLBACK': '1'}


class Transport:
    def __init__(self):
        self.calls = []

    def __call__(self, req, timeout=None):
        self.calls.append((req.get_method(), req.full_url))
        return io.BytesIO(b'{"id":"synthetic-prediction","status":"starting"}')


def provider(switches, transport, journal=None):
    return build_image_provider({**TOKEN, **switches}, journal=journal or MemorySubmissionJournal(), urlopen=transport)


class ImageProviderHonoursTheSwitches(unittest.TestCase):
    def test_closed_switches_refuse_before_any_request_and_leave_no_intent(self):
        for switches in CLOSED:
            with self.subTest(switches=switches):
                t, journal = Transport(), MemorySubmissionJournal()
                with self.assertRaises(ModelPolicyViolation):
                    provider(switches, t, journal).submit(REQ, idempotency_key='k')
                self.assertEqual(t.calls, [])
                self.assertIsNone(journal.find('k'))       # no INTENT: reopening the switches is not "ambiguous"

    def test_open_switches_submit_exactly_once(self):
        t = Transport()
        handle = provider(OPEN, t).submit(REQ, idempotency_key='k')
        self.assertEqual(handle.provider_task_id, 'synthetic-prediction')
        self.assertEqual([m for m, _ in t.calls], ['POST'])

    def test_the_lower_boundary_is_default_deny_for_any_non_get(self):
        t = Transport()
        p = provider(CLOSED[0], t)
        with self.assertRaises(ModelPolicyViolation):
            p._json('POST', p.config.base_url + p.config.submit_path, body={})
        self.assertEqual(t.calls, [])

    def test_a_cancel_still_goes_out_with_the_switches_closed(self):
        t = Transport()                                    # stopping spend must never be blocked by the spend switch
        provider(CLOSED[0], t).cancel(ProviderTaskHandle('replicate', 'p1', 'audit', 'k'))
        self.assertEqual(t.calls, [('POST', 'https://api.replicate.com/v1/predictions/p1/cancel')])


if __name__ == '__main__':
    unittest.main()
