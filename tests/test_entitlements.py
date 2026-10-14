"""Explicit, audited INTERNAL_QA / staging entitlement grants (decision 2026-10-07 #24)."""
import unittest

from omni_prod.entitlements import EntitlementError, grant, list_entitlements, revoke


class _Cur:
    def __init__(self, *, accounts, active=None, returning=None):
        self.accounts, self.active, self.returning, self.calls = accounts, active, returning, []
        self._last = None

    def execute(self, sql, params=None):
        self.calls.append((" ".join(sql.split()), params))
        self._last = sql

    def fetchall(self):
        if "FROM creator_accounts" in self._last:
            return [(a,) for a in self.accounts]
        return []

    def fetchone(self):
        if "RETURNING id" in self._last:
            return self.returning
        if "FROM internal_entitlements" in self._last:
            return self.active
        return None


class GrantTests(unittest.TestCase):
    def test_grant_binds_account_id_and_scope(self):
        cur = _Cur(accounts=["acc_1"])
        out = grant(cur, email=" Founder@Example.com ", reason="Golden E2E #1", granted_by="github:shay")
        self.assertEqual((out["action"], out["account_id"], out["entitlement"], out["environment"]),
                         ("granted", "acc_1", "INTERNAL_QA", "staging"))
        self.assertRegex(out["entitlement_id"], r"^ent_[0-9a-f]{32}$")
        self.assertEqual(cur.calls[0][1], ("Founder@Example.com",))           # case-insensitive lookup
        insert = cur.calls[-1]
        self.assertIn("INSERT INTO internal_entitlements", insert[0])
        self.assertEqual(insert[1][1:], ("acc_1", "INTERNAL_QA", "staging", "Golden E2E #1", "github:shay"))
        self.assertNotIn("example.com", str(out).lower())                        # output carries ids, not emails

    def test_grant_is_idempotent(self):
        cur = _Cur(accounts=["acc_1"], active=("ent_existing",))
        out = grant(cur, email="a@b.c", reason="r", granted_by="g")
        self.assertEqual((out["action"], out["entitlement_id"]), ("already_active", "ent_existing"))
        self.assertFalse(any("INSERT" in s for s, _ in cur.calls))

    def test_unknown_or_ambiguous_account_refused(self):
        with self.assertRaisesRegex(EntitlementError, "not found"):
            grant(_Cur(accounts=[]), email="a@b.c", reason="r", granted_by="g")
        with self.assertRaisesRegex(EntitlementError, "more than one"):
            grant(_Cur(accounts=["x", "y"]), email="a@b.c", reason="r", granted_by="g")

    def test_reason_and_actor_required(self):
        for kw in ({"reason": " ", "granted_by": "g"}, {"reason": "r", "granted_by": ""}):
            with self.assertRaises(EntitlementError):
                grant(_Cur(accounts=["acc_1"]), email="a@b.c", **kw)


class RevokeTests(unittest.TestCase):
    def test_revoke_keeps_audit_row(self):
        cur = _Cur(accounts=["acc_1"], returning=("ent_1",))
        out = revoke(cur, email="a@b.c", reason="done", revoked_by="github:shay")
        self.assertEqual(out, {"action": "revoked", "entitlement_id": "ent_1", "account_id": "acc_1"})
        self.assertTrue(cur.calls[-1][0].startswith("UPDATE internal_entitlements SET revoked_at = now()"))
        self.assertFalse(any("DELETE" in s for s, _ in cur.calls))

    def test_revoke_without_active_grant(self):
        out = revoke(_Cur(accounts=["acc_1"], returning=None), email="a@b.c", reason="r", revoked_by="g")
        self.assertEqual(out["action"], "none_active")

    def test_list_returns_ids_only(self):
        cur = _Cur(accounts=[])
        self.assertEqual(list_entitlements(cur), [])
        self.assertNotIn("email", cur.calls[0][0])


if __name__ == "__main__":
    unittest.main()
