"""Infisical generated-app secret contract. No live credentials are used."""
import io
import json
import unittest
from urllib import error, parse
from unittest.mock import patch

from omni_prod import secrets_manager
from omni_prod.providers.managed_web_saas import (
    ManagedWebSaaSConfig, build_managed_web_saas_provisioner,
)
from omni_prod.infrastructure_contracts import InfrastructureKind

BASE = "https://eu.infisical.com"
REF = "vault:secret/data/148ai/generated-apps/project/preview/auth_session/signing"
ENV = {
    "OMNI_GENAPP_SECRET_STORE_PROVIDER": "infisical",
    "OMNI_INFISICAL_BASE_URL": BASE,
    "OMNI_INFISICAL_PROJECT_ID": "project-id",
    "OMNI_INFISICAL_CLIENT_ID": "client-id-test",
    "OMNI_INFISICAL_CLIENT_SECRET": "client-secret-test",
}

class Response(io.BytesIO):
    def __init__(self, payload):
        super().__init__(json.dumps(payload).encode())

class Api:
    """Small transport fixture for the documented Universal Auth/v4 API."""
    def __init__(self):
        self.values = {}
        self.calls = []
        self.login_count = 0
        self.fail_status = None
        self.bad_response = None

    def __call__(self, req, timeout):
        url = parse.urlsplit(req.full_url)
        body = json.loads(req.data) if req.data else {}
        self.calls.append((req.get_method(), url, body))
        assert url.scheme == "https" and url.netloc == "eu.infisical.com"
        if url.path == "/api/v1/auth/universal-auth/login":
            assert body == {"clientId": ENV["OMNI_INFISICAL_CLIENT_ID"],
                            "clientSecret": ENV["OMNI_INFISICAL_CLIENT_SECRET"]}
            self.login_count += 1
            return Response({"accessToken": "access-token-test", "expiresIn": 60})
        assert req.get_header("Authorization") == "Bearer access-token-test"
        scope = dict(parse.parse_qsl(url.query)) if req.get_method() == "GET" else body
        assert scope["projectId"] == "project-id"
        assert scope["environment"] == "dev"
        assert scope["secretPath"] == "/" and scope["type"] == "shared"
        if self.fail_status:
            raise error.HTTPError(req.full_url, self.fail_status,
                                  "sensitive-response-test", {}, None)
        name = url.path.rsplit("/", 1)[1]
        assert url.path.startswith("/api/v4/secrets/")
        key = (scope["environment"], name)
        method = req.get_method()
        if method == "GET":
            if key not in self.values:
                raise error.HTTPError(req.full_url, 404, "not found", {}, None)
            return Response(self.bad_response if self.bad_response is not None
                            else {"secret": {"secretValue": self.values[key]}})
        if method == "POST":
            assert key not in self.values
            self.values[key] = body["secretValue"]
        elif method == "PATCH":
            assert key in self.values
            self.values[key] = body["secretValue"]
        elif method == "DELETE":
            if key not in self.values:
                raise error.HTTPError(req.full_url, 404, "not found", {}, None)
            del self.values[key]
        else:
            raise AssertionError(method)
        return Response({})

class InfisicalTests(unittest.TestCase):
    def store(self, api, **kwargs):
        self.assertTrue(hasattr(secrets_manager, "InfisicalHttpSecretWriter"),
                        "Infisical writer has not been implemented")
        return secrets_manager.InfisicalHttpSecretWriter(
            base_url=BASE, project_id="project-id", environment="dev",
            client_id=ENV["OMNI_INFISICAL_CLIENT_ID"],
            client_secret=ENV["OMNI_INFISICAL_CLIENT_SECRET"],
            urlopen=api, **kwargs)

    def test_create_read_rotate_delete_and_missing_delete(self):
        api = Api()
        store = self.store(api)
        store.write(REF, "first-value-test")
        self.assertEqual(store.resolve(REF), "first-value-test")
        store.write(REF, "rotated-value-test")
        self.assertEqual(store.resolve(REF), "rotated-value-test")
        self.assertEqual(len(api.values), 1)
        store.delete(REF)
        store.delete(REF)
        with self.assertRaises(secrets_manager.SecretResolutionError):
            store.resolve(REF)
        self.assertEqual(api.login_count, 1)

    def test_references_do_not_collide_across_projects_or_environments(self):
        api = Api()
        store = self.store(api)
        refs = [REF, REF.replace("/preview/", "/production/"),
                REF.replace("/project/", "/another-project/")]
        for i, ref in enumerate(refs):
            store.write(ref, str(i))
        self.assertEqual([store.resolve(ref) for ref in refs], ["0", "1", "2"])
        self.assertEqual(len(api.values), 3)
        for method, url, body in api.calls:
            self.assertNotIn(ENV["OMNI_INFISICAL_CLIENT_SECRET"], url.geturl())

    def test_permission_failure_is_not_treated_as_missing_secret(self):
        api = Api()
        api.fail_status = 403
        store = self.store(api)
        with self.assertRaises(secrets_manager.SecretResolutionError) as caught:
            store.write(REF, "private-value-test")
        self.assertNotIn("sensitive-response-test", str(caught.exception))
        self.assertNotIn("private-value-test", str(caught.exception))
        self.assertFalse(any(method == "POST" and "/secrets/" in url.path
                             for method, url, body in api.calls))

    def test_empty_or_malformed_response_is_rejected(self):
        api = Api()
        store = self.store(api)
        store.write(REF, "private-value-test")
        for payload in ({}, {"secret": {"secretValue": ""}},
                        {"secret": {"secretValue": 42}}):
            api.bad_response = payload
            with self.assertRaises(secrets_manager.SecretResolutionError):
                store.resolve(REF)

    def test_invalid_references_and_empty_values_make_no_requests(self):
        api = Api()
        store = self.store(api)
        for ref in ("env:SOME_KEY", "vault:secret/data/../key",
                    "vault:secret/data/key?query", "vault:secret/data/key/"):
            with self.assertRaises(secrets_manager.SecretResolutionError):
                store.write(ref, "value-test")
        with self.assertRaises(secrets_manager.SecretResolutionError):
            store.write(REF, "")
        self.assertEqual(api.calls, [])

    def test_token_is_refreshed_before_expiry(self):
        api = Api()
        now = [0.0]
        store = self.store(api, clock=lambda: now[0])
        store.write(REF, "value-test")
        now[0] = 61.0
        self.assertEqual(store.resolve(REF), "value-test")
        self.assertEqual(api.login_count, 2)

class InfisicalConfigTests(unittest.TestCase):
    def test_infisical_is_opt_in_and_readiness_never_claims_live(self):
        config = ManagedWebSaaSConfig.from_env(ENV)
        self.assertTrue(config.secret_store_configured)
        status, reason = config.config_status(InfrastructureKind.AUTH_SESSION, ENV)
        self.assertEqual(status, "PARTIAL")
        self.assertFalse(ManagedWebSaaSConfig.from_env(
            {k: v for k, v in ENV.items() if k != "OMNI_GENAPP_SECRET_STORE_PROVIDER"}
        ).secret_store_configured)

    def test_missing_credentials_fail_closed_with_actionable_reason(self):
        for key in ("OMNI_INFISICAL_CLIENT_ID", "OMNI_INFISICAL_CLIENT_SECRET",
                    "OMNI_INFISICAL_PROJECT_ID", "OMNI_INFISICAL_BASE_URL"):
            env = {k: v for k, v in ENV.items() if k != key}
            config = ManagedWebSaaSConfig.from_env(env)
            self.assertFalse(config.secret_store_configured)
            status, reason = config.config_status(InfrastructureKind.AUTH_SESSION, env)
            self.assertEqual(status, "NOT_CONFIGURED")
            self.assertIn("Infisical", reason)

    def test_factory_uses_supplied_environment_without_network_at_startup(self):
        api = Api()
        with patch("omni_prod.secrets_manager.request.urlopen", api):
            provisioner = build_managed_web_saas_provisioner(ENV)
            self.assertTrue(hasattr(provisioner, "secret_store"))
            provisioner.secret_store.write(REF, "value-test")
            self.assertEqual(provisioner.secret_store.resolve(REF), "value-test")

    def test_vault_configuration_stays_supported(self):
        env = {"OMNI_GENAPP_SECRET_STORE_URL": "https://vault.example.com",
               "OMNI_GENAPP_VAULT_TOKEN": "vault-token-test"}
        config = ManagedWebSaaSConfig.from_env(env)
        self.assertTrue(config.secret_store_configured)
        provisioner = build_managed_web_saas_provisioner(env)
        self.assertIsInstance(provisioner.secret_store,
                              secrets_manager.VaultHttpSecretWriter)

if __name__ == "__main__":
    unittest.main()
