from __future__ import annotations
from dataclasses import dataclass, asdict
import shutil

@dataclass(frozen=True)
class MobileBuildPlan:
    platform: str
    framework: str
    build_commands: tuple[tuple[str,...],...]
    required_secrets: tuple[str,...]
    store_artifact: str
    live_toolchain_available: bool

    def to_dict(self): return asdict(self)

def build_plan(platform: str, framework: str='react-native') -> MobileBuildPlan:
    p=platform.lower()
    f=framework.lower()
    if p == 'android':
        cmd=(('./gradlew','bundleRelease'),) if f in {'native','react-native'} else (('flutter','build','appbundle','--release'),)
        return MobileBuildPlan('android',f,cmd,('ANDROID_KEYSTORE','ANDROID_KEYSTORE_PASSWORD','ANDROID_KEY_ALIAS','ANDROID_KEY_PASSWORD'),'aab', bool(shutil.which('java')))
    if p == 'ios':
        cmd=(('xcodebuild','-scheme','OmniApp','-configuration','Release','archive'),) if f in {'native','react-native'} else (('flutter','build','ipa','--release'),)
        return MobileBuildPlan('ios',f,cmd,('APPLE_TEAM_ID','APP_STORE_CONNECT_KEY_ID','APP_STORE_CONNECT_ISSUER_ID','APP_STORE_CONNECT_PRIVATE_KEY'),'ipa', bool(shutil.which('xcodebuild')))
    raise ValueError('platform must be android or ios')
