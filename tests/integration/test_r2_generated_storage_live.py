"""Explicitly opted-in real R2 CRUD and cross-app/environment denial proof.

Run only against the generated-app staging bucket. Does not need a scheduler
or Vault; never skip R2 because an unrelated infrastructure service is absent.
"""
import os
import unittest
import uuid

from omni_prod.providers.managed_web_saas import ManagedWebSaaSConfig, scoped_object_policy
from omni_prod.providers.r2_credentials import R2CredentialIssuer

_REQUIRED = ("OMNI_GENAPP_S3_ENDPOINT", "OMNI_GENAPP_S3_BUCKET",
             "OMNI_GENAPP_S3_ACCESS_KEY_REF", "OMNI_GENAPP_S3_SECRET_KEY_REF")


def _skip_reason():
    if os.environ.get("M5_R2_LIVE") != "1":
        return "M5_R2_LIVE=1 not set; real R2 staging credentials not supplied"
    for name in _REQUIRED:
        if not os.environ.get(name):
            return "missing R2 staging setting: " + name
    for name in _REQUIRED[2:]:
        ref = os.environ[name]
        if not ref.startswith("env:") or not os.environ.get(ref[4:]):
            return "R2 live test requires a populated env: reference for " + name
    return None


@unittest.skipIf(_skip_reason() is not None, _skip_reason() or "")
class R2LiveTests(unittest.TestCase):
    def test_crud_listing_and_existing_cross_app_environment_objects_denied(self):
        import boto3
        from botocore.exceptions import ClientError

        cfg = ManagedWebSaaSConfig.from_env()
        access = os.environ[cfg.s3_access_key_ref[4:]]
        secret = os.environ[cfg.s3_secret_key_ref[4:]]
        self.assertNotEqual(cfg.s3_bucket, os.environ.get("OMNI_S3_BUCKET"))
        self.assertNotEqual(access, os.environ.get("OMNI_S3_ACCESS_KEY"))
        app = uuid.uuid4().hex
        prefix = f"generated-apps/{app}/preview/"
        keys = [prefix + "probe", f"generated-apps/{app}/production/sentinel",
                f"generated-apps/{uuid.uuid4().hex}/preview/sentinel"]
        parent = boto3.client("s3", endpoint_url=cfg.s3_endpoint, region_name="auto",
                              aws_access_key_id=access, aws_secret_access_key=secret)
        try:
            for key in keys:
                parent.put_object(Bucket=cfg.s3_bucket, Key=key, Body=b"148ai-r2-live")
            creds = R2CredentialIssuer(endpoint=cfg.s3_endpoint).issue(
                operator_access_key=access, operator_secret_key=secret, role_arn="",
                policy=scoped_object_policy(cfg.s3_bucket, prefix), session_name=app, ttl_seconds=900)
            client = boto3.client("s3", endpoint_url=cfg.s3_endpoint, region_name="auto",
                                  aws_access_key_id=creds["access_key_id"],
                                  aws_secret_access_key=creds["secret_access_key"],
                                  aws_session_token=creds["session_token"])
            client.put_object(Bucket=cfg.s3_bucket, Key=keys[0], Body=b"scoped")
            body = client.get_object(Bucket=cfg.s3_bucket, Key=keys[0])["Body"]
            try:
                self.assertEqual(body.read(), b"scoped")
            finally:
                body.close()
            listing = client.list_objects_v2(Bucket=cfg.s3_bucket, Prefix=prefix)
            self.assertIn(keys[0], [x["Key"] for x in listing.get("Contents", [])])
            for key in keys[1:]:
                for method, extra in (("get_object", {}), ("put_object", {"Body": b"forbidden"}),
                                      ("delete_object", {})):
                    with self.subTest(key=key, method=method):
                        with self.assertRaises(ClientError) as denied:
                            getattr(client, method)(Bucket=cfg.s3_bucket, Key=key, **extra)
                        self.assertEqual(denied.exception.response["ResponseMetadata"]["HTTPStatusCode"], 403)
            for key in keys[1:]:
                body = parent.get_object(Bucket=cfg.s3_bucket, Key=key)["Body"]
                try:
                    self.assertEqual(body.read(), b"148ai-r2-live")
                finally:
                    body.close()
            client.delete_object(Bucket=cfg.s3_bucket, Key=keys[0])
            with self.assertRaises(ClientError) as gone:
                parent.get_object(Bucket=cfg.s3_bucket, Key=keys[0])
            self.assertEqual(gone.exception.response["ResponseMetadata"]["HTTPStatusCode"], 404)
        finally:
            for key in keys:
                parent.delete_object(Bucket=cfg.s3_bucket, Key=key)
