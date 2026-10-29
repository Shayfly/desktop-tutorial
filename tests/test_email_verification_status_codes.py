"""POST /api/v28/auth/email-verification/request keeps the right status codes.

Bug (found by tests/test_pr39_cookie_fallback_real_routes.py, PR #50): a broad
`except Exception` turned the 401 from _v28_bearer into 400 with detail
"401: authentication required", and the 503 from _m5_identity_service into 400.
"""
import os
import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from omni_prod import investor_app

PATH = '/api/v28/auth/email-verification/request'
SAME_ORIGIN = {'Origin': 'http://testserver'}


class EmailVerificationStatusCodeTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(investor_app.app)

    def test_anonymous_is_401_not_400(self):
        r = self.client.post(PATH, headers=SAME_ORIGIN)
        self.assertEqual(r.status_code, 401, r.text[:200])
        self.assertEqual(r.json()['detail'], 'authentication required')

    def test_anonymous_is_401_in_production_too(self):
        with patch.dict(os.environ, {'OMNI_ENV': 'production'}):
            r = self.client.post(PATH, headers=SAME_ORIGIN)
        self.assertEqual(r.status_code, 401, r.text[:200])

    def test_invalid_session_is_401(self):
        v28 = MagicMock()
        v28.account.side_effect = PermissionError('invalid session')
        with patch.object(investor_app, '_v28', v28):
            r = self.client.post(PATH, headers={'Authorization': 'Bearer invalid', **SAME_ORIGIN})
        self.assertEqual(r.status_code, 401, r.text[:200])

    def test_identity_service_unavailable_stays_503(self):
        v28 = MagicMock()
        v28.account.return_value = MagicMock(id='usr_1')
        unavailable = HTTPException(503, 'durable identity lifecycle requires PostgreSQL creator persistence')
        with patch.object(investor_app, '_v28', v28), \
             patch.object(investor_app, '_m5_identity_service', side_effect=unavailable):
            r = self.client.post(PATH, headers={'Authorization': 'Bearer t', **SAME_ORIGIN})
        self.assertEqual(r.status_code, 503, r.text[:200])

    def test_other_failures_are_still_400(self):
        v28 = MagicMock()
        v28.account.return_value = MagicMock(id='usr_1')
        identity = MagicMock()
        identity.request_email_verification.side_effect = ValueError('email already verified')
        with patch.object(investor_app, '_v28', v28), \
             patch.object(investor_app, '_m5_identity_service', return_value=identity):
            r = self.client.post(PATH, headers={'Authorization': 'Bearer t', **SAME_ORIGIN})
        self.assertEqual(r.status_code, 400, r.text[:200])
        self.assertEqual(r.json()['detail'], 'email already verified')


if __name__ == '__main__':
    unittest.main()
