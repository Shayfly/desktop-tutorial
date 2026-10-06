from __future__ import annotations
from dataclasses import dataclass,asdict
from enum import Enum
from decimal import Decimal
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

# Founder decision 2026-10-07 #28: generated visual assets are requested only
# when the product asks for them. A plain SaaS/internal tool gets no image
# request at all (build evidence reports NOT_REQUIRED); bare "image"/"photo"
# are not triggers because they usually mean user uploads, not generation.
_ICON_TERMS = ('logo', 'app icon', 'favicon', 'brand identity', 'branding', 'mascot',
               'לוגו', 'סמליל', 'אייקון', 'מיתוג')
_HERO_TERMS = ('hero image', 'hero visual', 'hero banner', 'hero section image', 'illustration', 'banner',
               'poster', 'artwork', 'key art', 'cover image', 'cover art', 'generated image', 'ai image',
               'ai-generated image', 'imagery', 'איור', 'באנר', 'פוסטר', 'תמונה ראשית', 'תמונת הירו')
_GAME_TERMS = ('game', '3d', 'unreal', 'unity', 'godot', 'משחק', 'תלת')


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
        game = any(t in low for t in _GAME_TERMS) or 'game3d' in targets
        wants_icon = any(t in low for t in _ICON_TERMS)
        wants_hero = any(t in low for t in _HERO_TERMS)
        if wants_icon or game:
            add(AssetKind.ICON,'product icon','Create a distinctive accessible app icon; no third-party trademarks.')
        if wants_hero or game:
            add(AssetKind.IMAGE,'hero/brand visual','Create a premium original hero visual with no copyrighted logos or characters.',wants_hero)
        if game:
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

    @staticmethod
    def _export_safe(value):
        sensitive=('secret','token','api_key','apikey','authorization','password','credential')
        if isinstance(value,dict):
            return {str(k): ('[REDACTED]' if any(x in str(k).lower() for x in sensitive)
                             else CreativeDirector._export_safe(v)) for k,v in value.items()}
        if isinstance(value,(list,tuple)):
            return [CreativeDirector._export_safe(v) for v in value]
        if isinstance(value,Decimal):
            return str(value)
        return value

    def repository_files(
        self, plan:CreativePlan, *, capability_evidence:dict|None=None,
        materialized_evidence:list[dict]|tuple[dict,...]|None=None,
    )->dict[str,str]:
        data=plan.to_dict()
        data['schema_version']=2
        materialized=[]
        if materialized_evidence is not None:
            source_rows=list(materialized_evidence)
        elif capability_evidence is not None:
            usage_by_req={str(u.get('requirement_id')):u for u in capability_evidence.get('usage',())}
            source_rows=[]
            for row in capability_evidence.get('requirements',()):
                if row.get('status')!='VERIFIED' or not row.get('artifact_key'):
                    continue
                item=dict(row)
                usage=usage_by_req.get(str(row.get('requirement_id')), {})
                for key in ('estimated_cost_usd','maximum_cost_usd','actual_cost_usd'):
                    if key in usage:
                        item[key]=usage.get(key)
                if usage.get('pricing_version') and not item.get('pricing_version'):
                    item['pricing_version']=usage['pricing_version']
                usage_evidence=dict(usage.get('evidence') or {})
                if usage_evidence and not item.get('provenance'):
                    item['provenance']=dict(usage_evidence.get('provenance') or usage_evidence)
                verification=dict(item.get('verification') or {})
                # Normalize the most useful integrity fields to the row while
                # preserving the full verification evidence as an additive field.
                for key in ('sha256','size_bytes'):
                    if key not in item and key in verification:
                        item[key]=verification[key]
                if 'provider' not in item and item.get('selected_provider'):
                    item['provider']=item.get('selected_provider')
                source_rows.append(item)
        else:
            source_rows=[]

        for raw in source_rows:
            item=dict(raw)
            actual=item.get('actual_cost_usd')
            item['cost_truth']='ACTUAL' if actual is not None else 'ESTIMATE_ONLY'
            materialized.append(self._export_safe(item))
        data['materialized']=materialized
        if capability_evidence is not None:
            data['capability_materializations']=materialized
            data['materialization_truth']='VERIFIED_ONLY'
        manifest=json.dumps(self._export_safe(data),ensure_ascii=False,indent=2)
        return {
            'assets/148ai-asset-manifest.json':manifest,
            'assets/omni-asset-manifest.json':manifest, # compatibility alias
            'assets/README.md':'# 148AI Creative Assets\nThis manifest is a generation contract. Files are materialized only by configured media providers. Never mark planned assets as generated.\n',
            'docs/CREATIVE_RIGHTS.md':'# Creative rights gate\nOnly original, licensed, public-domain, or otherwise authorized assets may ship. Trademark, likeness, music and dataset rights require review.\n',
        }
