import hashlib
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from omni_prod.auth import verify_token
from omni_prod.identity_lifecycle import (
    IdentityService,
    MemoryIdentityRepository,
    IdentityError,
)


SECRET = "m5-identity-secret-" + "x" * 40


class MutableClock:
    def __init__(self):
        self.value = datetime(2026, 10, 4, 15, 0, tzinfo=timezone.utc)

    def now(self):
        return self.value

    def advance(self, **kwargs):
        self.value += timedelta(**kwargs)


class IdentityLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.clock = MutableClock()
        self.repo = MemoryIdentityRepository()
        self.identity = IdentityService(token_secret=SECRET, repository=self.repo, now_fn=self.clock.now)

    def test_register_is_unverified_and_session_token_is_only_hashed_at_rest(self):
        account, token = self.identity.register(email="User@Example.com", password="StrongPass123!")
        state = self.repo.account_by_id(account.id)
        self.assertEqual(state.status, "PENDING_VERIFICATION")
        self.assertIsNone(state.email_verified_at)
        self.assertEqual(self.identity.account_state(account.id), {
            "status": "PENDING_VERIFICATION", "email_verified": False, "email_verified_at": None
        })
        claims = verify_token(token, secret=SECRET, now=int(self.clock.now().timestamp()))
        self.assertTrue(claims.session_id)
        session = self.repo.session_by_id(claims.session_id)
        self.assertEqual(session.token_hash, hashlib.sha256(token.encode()).hexdigest())
        self.assertNotEqual(session.token_hash, token)
        self.assertNotIn(token, repr(self.repo.__dict__))

    def test_email_verification_token_is_hashed_and_one_time(self):
        account, _ = self.identity.register(email="verify@example.com", password="StrongPass123!")
        token = self.identity.request_email_verification(account.id)
        self.assertNotIn(token, repr(self.repo.__dict__))
        verified = self.identity.verify_email(token)
        self.assertEqual(verified.status, "ACTIVE")
        self.assertIsNotNone(verified.email_verified_at)
        with self.assertRaisesRegex(IdentityError, "invalid or expired"):
            self.identity.verify_email(token)

    def test_password_reset_token_is_hashed_expires_and_success_revokes_sessions(self):
        account, session_token = self.identity.register(email="reset@example.com", password="StrongPass123!")
        reset = self.identity.request_password_reset(account.email)
        self.assertIsNotNone(reset)
        self.assertNotIn(reset, repr(self.repo.__dict__))
        self.clock.advance(hours=2)
        with self.assertRaisesRegex(IdentityError, "invalid or expired"):
            self.identity.reset_password(reset, "NewStrongPass123!")

        self.clock.value = datetime(2026, 10, 4, 18, 0, tzinfo=timezone.utc)
        reset2 = self.identity.request_password_reset(account.email)
        self.identity.reset_password(reset2, "NewStrongPass123!")
        with self.assertRaisesRegex(PermissionError, "session revoked"):
            self.identity.authenticate(session_token)
        logged, _ = self.identity.login(email=account.email, password="NewStrongPass123!")
        self.assertEqual(logged.id, account.id)

    def test_revocation_is_visible_across_service_instances_sharing_repository(self):
        account, token = self.identity.register(email="sessions@example.com", password="StrongPass123!")
        second = IdentityService(token_secret=SECRET, repository=self.repo, now_fn=self.clock.now)
        self.assertEqual(second.authenticate(token).id, account.id)
        session_id = verify_token(token, secret=SECRET, now=int(self.clock.now().timestamp())).session_id
        second.revoke_session(account.id, session_id)
        with self.assertRaisesRegex(PermissionError, "session revoked"):
            self.identity.authenticate(token)

    def test_consent_versions_and_privacy_requests_are_durable_records(self):
        account, _ = self.identity.register(email="privacy@example.com", password="StrongPass123!")
        one = self.identity.record_consent(account.id, consent_type="terms", version="2026-10-04")
        two = self.identity.record_consent(account.id, consent_type="privacy", version="2026-10-04")
        self.assertEqual(one.user_id, account.id)
        self.assertEqual(two.version, "2026-10-04")
        self.assertEqual(len(self.repo.consents_for(account.id)), 2)

        export = self.identity.request_data_export(account.id)
        deletion = self.identity.request_account_deletion(account.id)
        self.assertEqual(export.request_type, "DATA_EXPORT")
        self.assertEqual(deletion.request_type, "ACCOUNT_DELETION")
        self.assertEqual(export.status, "REQUESTED")
        self.assertEqual(self.repo.account_by_id(account.id).status, "DELETION_PENDING")

    def test_list_sessions_never_exposes_token_hash(self):
        account, _ = self.identity.register(email="list@example.com", password="StrongPass123!")
        payload = self.identity.list_sessions(account.id)
        self.assertEqual(len(payload), 1)
        self.assertNotIn("token_hash", payload[0].to_dict())




class IdentitySchemaContractTests(unittest.TestCase):
    def test_migration_has_durable_sessions_hashed_one_time_tokens_consent_and_privacy_requests(self):
        migration = (Path(__file__).resolve().parents[1] / "infra/postgres/018_identity_lifecycle.sql").read_text()
        for table in ("creator_sessions", "creator_identity_tokens", "creator_consents", "creator_privacy_requests"):
            self.assertIn(table, migration)
        self.assertIn("token_hash", migration)
        self.assertNotIn("raw_token", migration)
        self.assertIn("account_status", migration)
        self.assertIn("email_verified_at", migration)

class IdentityApiSecrecyTests(unittest.TestCase):
    def test_password_reset_request_never_returns_raw_token(self):
        import omni_prod.investor_app as appmod

        class FakeIdentity:
            def request_password_reset(self, email):
                self.email = email
                return "raw-reset-secret-that-must-not-leak"

        fake = FakeIdentity()
        client = TestClient(appmod.app)
        with patch.object(appmod, "_m5_identity_service", return_value=fake):
            response = client.post("/api/v28/auth/password-reset/request", json={"email": "person@example.com"})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), {"accepted": True})
        self.assertNotIn("raw-reset-secret", response.text)


if __name__ == "__main__":
    unittest.main()
