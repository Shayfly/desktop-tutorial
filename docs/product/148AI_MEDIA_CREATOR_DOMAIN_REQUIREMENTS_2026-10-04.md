# 148AI Media / Creator Studio Domain Requirements

Date: 2026-10-04
Status: canonical requirement draft pending repository integration

## Product objective

148AI must support a provider-neutral Media Company / Creator Studio in a Box. It should benchmark against OpenArt, FacelessReels, Buzzy AI, HeyGen, Renoise.ai, AITuber, AutoShorts.ai, Captions, Suno, and BigMotion without copying proprietary code or content.

## Required capability set

- `MEDIA.BRIEF` — brief-to-production planning — current explicit registry coverage: **MISSING**
- `MEDIA.IDEA` — ideation / series concepts — current explicit registry coverage: **MISSING**
- `MEDIA.SCRIPT` — script generation — current explicit registry coverage: **MISSING**
- `MEDIA.STORYBOARD` — storyboard generation — current explicit registry coverage: **YES/PARTIAL**
- `MEDIA.CHARACTER_BIBLE` — persistent character bible — current explicit registry coverage: **MISSING**
- `MEDIA.BRAND_BIBLE` — persistent brand bible — current explicit registry coverage: **MISSING**
- `IMAGE.GENERATE` — image generation — current explicit registry coverage: **YES/PARTIAL**
- `IMAGE.EDIT` — image editing — current explicit registry coverage: **YES/PARTIAL**
- `VIDEO.TEXT_TO_VIDEO` — text-to-video explicit mode — current explicit registry coverage: **MISSING**
- `VIDEO.IMAGE_TO_VIDEO` — image-to-video explicit mode — current explicit registry coverage: **MISSING**
- `VIDEO.VIDEO_TO_VIDEO` — video-to-video explicit mode — current explicit registry coverage: **MISSING**
- `VIDEO.CONTINUITY` — cross-shot continuity — current explicit registry coverage: **MISSING**
- `VIDEO.LIPSYNC` — lip-sync — current explicit registry coverage: **YES/PARTIAL**
- `AUDIO.TTS` — text-to-speech — current explicit registry coverage: **YES/PARTIAL**
- `AUDIO.VOICE_CONSISTENCY` — persistent voice identity — current explicit registry coverage: **MISSING**
- `AUDIO.MUSIC` — music generation — current explicit registry coverage: **YES/PARTIAL**
- `AUDIO.SFX` — sound effects — current explicit registry coverage: **YES/PARTIAL**
- `VIDEO.COMPOSE` — timeline composition/editor — current explicit registry coverage: **MISSING**
- `VIDEO.CAPTIONS` — captions — current explicit registry coverage: **YES/PARTIAL**
- `VIDEO.LOCALIZE` — localization/dubbing orchestration — current explicit registry coverage: **MISSING**
- `VIDEO.THUMBNAIL` — thumbnail/cover generation — current explicit registry coverage: **MISSING**
- `MEDIA.QA` — media-specific QA — current explicit registry coverage: **MISSING**
- `MEDIA.IP_SAFETY` — IP/safety checks — current explicit registry coverage: **MISSING**
- `SOCIAL.PUBLISH` — social publishing — current explicit registry coverage: **MISSING**
- `SOCIAL.SCHEDULE` — scheduled/autopilot publishing — current explicit registry coverage: **MISSING**
- `SOCIAL.ANALYTICS` — social analytics feedback — current explicit registry coverage: **MISSING**
- `SOCIAL.EXPERIMENT` — A/B hooks/titles/covers — current explicit registry coverage: **MISSING**
- `MEDIA.OPTIMIZE` — optimization feedback loop — current explicit registry coverage: **MISSING**
- `COST.ROUTE` — provider cost/quality routing — current explicit registry coverage: **YES/PARTIAL**
- `COST.BUDGET_GUARD` — hard budget guard — current explicit registry coverage: **YES/PARTIAL**

## Governance rule

Every capability above must have explicit Capability/Skill/Agent registry coverage, dependency closure, providers/tools, cost model, permissions/security/legal constraints, implementation location, verification tests, quality metrics, last verified version/date, and truthful status. Generic nearby capability names are not sufficient when the workflow semantics are materially different.

## Required execution chain

`Brief -> Creative Director -> Script -> Storyboard -> Character/Brand Bible -> Provider Routing -> Image/Video/Voice/Music/SFX -> Continuity -> Editor/Composer -> Captions/Localization -> QA/IP Safety -> Publish/Schedule -> Analytics/A-B -> Optimization`
