import os, shutil, unittest

@unittest.skipUnless(os.getenv('OMNI_RUN_SIGNED_ANDROID')=='1','requires Android signing credentials')
class AndroidSigningLiveTests(unittest.TestCase):
    def test_android_signing_environment(self):
        for k in ('ANDROID_KEYSTORE','ANDROID_KEYSTORE_PASSWORD','ANDROID_KEY_ALIAS','ANDROID_KEY_PASSWORD'): self.assertTrue(os.getenv(k),k)
        self.assertTrue(shutil.which('java'))

@unittest.skipUnless(os.getenv('OMNI_RUN_SIGNED_IOS')=='1','requires macOS/Xcode/App Store credentials')
class IOSSigningLiveTests(unittest.TestCase):
    def test_ios_signing_environment(self):
        for k in ('APPLE_TEAM_ID','APP_STORE_CONNECT_KEY_ID','APP_STORE_CONNECT_ISSUER_ID','APP_STORE_CONNECT_PRIVATE_KEY'): self.assertTrue(os.getenv(k),k)
        self.assertTrue(shutil.which('xcodebuild'))
