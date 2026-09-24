from __future__ import annotations
from dataclasses import dataclass, asdict
import shutil
from .integrations import REGISTRY
from .i18n import SUPPORTED_LOCALES
from .benchmark_suite import CASES
from .deployment_runtime import international_default_topology
from .game_pipeline import engine_plan
from .mobile_pipeline import build_plan

@dataclass(frozen=True)
class CapabilityGate:
    capability: str
    implemented: bool
    live_verified: bool
    evidence: str


def international_gates() -> tuple[CapabilityGate,...]:
    android=build_plan('android')
    ios=build_plan('ios')
    godot=engine_plan('godot')
    unity=engine_plan('unity')
    unreal=engine_plan('unreal')
    return (
        CapabilityGate('autonomous_core',True,False,'Prompt→Spec→Generate→Sandbox→Repair is implemented; arbitrary-app success requires live benchmark'),
        CapabilityGate('model_routing',True,False,'Local-first + paid fail-closed fallback implemented; no GPU endpoint verified in this environment'),
        CapabilityGate('benchmark_catalog',len(CASES)>=200,False,f'{len(CASES)} cases catalogued; live autonomous pass rate not measured here'),
        CapabilityGate('mobile_android',True,android.live_toolchain_available,'AAB build contract and signing secret contract'),
        CapabilityGate('mobile_ios',True,ios.live_toolchain_available,'IPA archive/signing contract; requires macOS/Xcode credentials'),
        CapabilityGate('games_godot',True,godot.executable_available,'Godot headless verification plan'),
        CapabilityGate('games_unity',True,unity.executable_available,'Unity batch verification plan'),
        CapabilityGate('games_unreal',True,unreal.executable_available,'Unreal commandlet verification plan'),
        CapabilityGate('integrations',len(REGISTRY)>=8,False,f'{len(REGISTRY)} provider contracts; credentials required for live verification'),
        CapabilityGate('internationalization',len(SUPPORTED_LOCALES)>=10,True,f'{len(SUPPORTED_LOCALES)} locale contracts including RTL'),
        CapabilityGate('production_runtime',True,bool(shutil.which('docker')),'Postgres/Redis/S3/queue/autoscaling contracts exist; live stack depends on Docker/services'),
        CapabilityGate('security',True,False,'Static hostile-repository scan + hardened sandbox; penetration/sandbox-escape suite needs live Docker'),
        CapabilityGate('commercial_platform',True,True,'Teams/RBAC, credits/free-repair policy, workspace/versioning implemented as domain layer'),
    )


def payload() -> dict:
    gates=international_gates()
    return {
        'implemented': sum(x.implemented for x in gates),
        'total': len(gates),
        'live_verified': sum(x.live_verified for x in gates),
        'gates':[asdict(x) for x in gates],
        'topology': international_default_topology().to_dict(),
    }
