from __future__ import annotations
from dataclasses import dataclass,asdict
from enum import Enum
import json, re

class AssetKind(str,Enum):
    IMAGE='image'; ICON='icon'; AUDIO='audio'; MUSIC='music'; VOICE='voice'; VIDEO='video'; MODEL3D='model3d'; TEXTURE='texture'

@dataclass(frozen=True)
class AssetRequest:
    id:str; kind:AssetKind; purpose:str; prompt:str; required:bool=True
    def to_dict(self):
        d=asdict(self); d['kind']=self.kind.value; return d

@dataclass(frozen=True)
class CreativePlan:
    requests:tuple[AssetRequest,...]
    accessibility:dict
    rights_policy:dict
    def to_dict(self): return {'requests':[r.to_dict() for r in self.requests],'accessibility':self.accessibility,'rights_policy':self.rights_policy}

class CreativeDirector:
    """Plans multimodal assets without pretending generation occurred.

    Generation providers can consume this manifest. The plan always includes
    rights/accessibility constraints so generated products remain reviewable.
    """
    def plan(self,prompt:str,*,targets:tuple[str,...]=('web',))->CreativePlan:
        text=' '.join(prompt.split())
        low=text.lower(); req=[]
        def add(kind,purpose,suffix,required=True):
            req.append(AssetRequest(f'asset-{len(req)+1:03d}',kind,purpose,f'{text}. {suffix}',required))
        add(AssetKind.ICON,'product icon','Create a distinctive accessible app icon; no third-party trademarks.')
        add(AssetKind.IMAGE,'hero/brand visual','Create a premium original hero visual with no copyrighted logos or characters.',False)
        if any(t in low for t in ('game','3d','unreal','unity','godot','משחק','תלת')) or 'game3d' in targets:
            add(AssetKind.MODEL3D,'primary 3D environment','Create an original optimized 3D environment with LOD-ready topology.')
            add(AssetKind.TEXTURE,'PBR material set','Create original PBR texture specifications suitable for realtime rendering.')
            add(AssetKind.AUDIO,'gameplay SFX','Create original gameplay sound effects with clear licensing metadata.')
            add(AssetKind.MUSIC,'adaptive soundtrack','Create original loopable adaptive music; no imitation of living artists.',False)
        if any(t in low for t in ('video','reel','movie','סרט','וידאו')):
            add(AssetKind.VIDEO,'video sequence','Create an original shot plan/video asset with captions and safe-area variants.')
        if any(t in low for t in ('voice','narration','assistant','קריינ','קול')):
            add(AssetKind.VOICE,'voice/narration','Generate neutral synthetic narration; never impersonate a real person without authorization.')
        return CreativePlan(tuple(req),{'alt_text_required':True,'captions_for_video':True,'transcripts_for_voice':True},
            {'original_or_licensed_only':True,'trademark_review':True,'music_rights_review':True,'real_person_consent_required':True})

    def repository_files(self,plan:CreativePlan)->dict[str,str]:
        data=plan.to_dict()
        manifest=json.dumps(data,ensure_ascii=False,indent=2)
        return {
            'assets/148ai-asset-manifest.json':manifest,
            'assets/omni-asset-manifest.json':manifest, # compatibility alias
            'assets/README.md':'# 148AI Creative Assets\nThis manifest is a generation contract. Files are materialized only by configured media providers. Never mark planned assets as generated.\n',
            'docs/CREATIVE_RIGHTS.md':'# Creative rights gate\nOnly original, licensed, public-domain, or otherwise authorized assets may ship. Trademark, likeness, music and dataset rights require review.\n',
        }
